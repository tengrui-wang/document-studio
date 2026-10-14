from __future__ import annotations

import multiprocessing as mp
import queue
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from .common import Cancelled, check_cancel, publish
from .storage import Credentials, Settings, atomic_json


@dataclass
class Task:
    title: str
    operation: str
    sources: list[str]
    output: str
    options: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: str = "等待"
    progress: int = 0
    message: str = ""
    outputs: list[str] = field(default_factory=list)
    result: dict = field(default_factory=dict)


def worker(task_data, events, cancel, cache_root, stage_name):
    """Spawned process: no Qt objects, credentials loaded only inside this process."""
    import logging
    logging.disable(logging.CRITICAL)  # document libraries can otherwise print private content
    task = Task(**task_data)
    stage = Path(stage_name) if stage_name else None
    def progress(value, message):
        check_cancel(cancel)
        events.put(("progress", int(value), message))
    def usage(incoming, outgoing):
        events.put(("usage", incoming, outgoing))
    client = None
    try:
        check_cancel(cancel)
        if task.operation in ("models", "test_api", "translate"):
            from .api import APIClient
            profile = task.options["profile"]
            client = APIClient(profile, Credentials().get(profile["id"]), cancel=cancel, usage=usage)
        if task.operation == "models":
            events.put(("done", [], {"models": client.models()}))
            return
        if task.operation == "test_api":
            client.complete(task.options["model"], "Reply with OK only.", "Connection test.")
            events.put(("done", [], {"message": "连接及所选模型调用成功。"}))
            return
        if task.operation == "updates":
            from .updates import check_update
            events.put(("done", [], check_update(task.options["repository"])))
            return
        stage.mkdir(parents=True, exist_ok=False)
        if task.operation in ("pdf_to_word", "word_to_pdf", "word_format", "translate"):
            from .pdf_tools import pdf_to_word
            from .word_tools import word_format, word_to_pdf
            source = Path(task.sources[0])
            if task.operation == "pdf_to_word":
                target = stage / f"{source.stem}_converted.docx"
                pdf_to_word(source, target, progress, cancel)
            elif task.operation == "word_to_pdf":
                target = stage / f"{source.stem}_converted.pdf"
                word_to_pdf(source, target, task.options, progress, cancel)
            elif task.operation == "word_format":
                target = stage / f"{source.stem}_formatted.docx"
                word_format(source, target, task.options, progress, cancel)
            else:
                from .translation import translate_docx
                original = source
                if source.suffix.lower() == ".pdf":
                    original = stage / "translation-source.docx"
                    pdf_to_word(source, original, progress, cancel)
                target = stage / f"{source.stem}_translated.docx"
                translate_docx(original, target, task.options, client, Path(cache_root), progress, cancel)
            produced = [target]
        else:
            from .pdf_tools import process_pdf
            produced = process_pdf(task.operation, task.sources, stage, task.options, progress, cancel)
        # Cancellation is accepted before publishing. Publishing is a short final phase.
        check_cancel(cancel)
        outputs = []
        for path in produced:
            outputs.append(str(publish(path, Path(task.output), path.stem, path.suffix)))
            events.put(("output", outputs[-1]))
        events.put(("done", outputs, {}))
    except Cancelled as exc:
        events.put(("cancelled", str(exc)))
    except Exception as exc:
        # Never include arbitrary provider exception text, response bodies or tracebacks.
        if isinstance(exc, (ValueError, RuntimeError)):
            message = str(exc)
        elif isinstance(exc, PermissionError):
            message = "没有文件访问权限，或输出文件正被其他程序占用。"
        elif isinstance(exc, FileNotFoundError):
            message = "源文件不存在或已移动，请重新选择。"
        else:
            message = f"处理失败（{type(exc).__name__}）。请检查文件是否损坏、加密或格式不受支持。"
        events.put(("failed", message))
    finally:
        if client is not None:
            client.close()
        if stage and stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


class TaskManager(QObject):
    changed = Signal()
    finished = Signal(object)

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.tasks = []
        self.active = None
        self.ctx = mp.get_context("spawn")
        self.process = self.events = self.cancel_event = None
        self.stage = None
        self.cancel_time = None
        self.history = settings.root / "tasks.json"
        self.stopping = False
        if self.history.exists():
            import json
            try:
                for row in json.loads(self.history.read_text(encoding="utf-8")).get("tasks", []):
                    task = Task(**row)
                    if task.status in ("等待", "运行", "取消中"):
                        task.status = "中断"
                        task.message = "上次退出时未完成；点击重试，翻译可恢复断点。"
                    self.tasks.append(task)
            except (ValueError, TypeError, OSError):
                pass
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(150)

    def save(self):
        atomic_json(self.history, {"tasks": [asdict(task) for task in self.tasks[-200:]]})

    def add(self, task: Task):
        self.tasks.append(task)
        self.save()
        self.changed.emit()
        return task

    def retry(self, task):
        if task.status not in ("失败", "取消", "中断"):
            raise ValueError("只有失败、取消或中断的任务可重试。")
        task.status, task.progress, task.message = "等待", 0, ""
        task.outputs, task.result = [], {}
        self.save()
        self.changed.emit()

    def cancel(self, task):
        if task.status == "等待":
            task.status, task.message = "取消", "未开始的任务已取消。"
        elif task is self.active and task.status == "运行":
            task.status = "取消中"
            self.cancel_event.set()
            self.cancel_time = time.monotonic()
        self.save()
        self.changed.emit()

    def poll(self):
        if self.active:
            self.drain()
            if self.cancel_time and self.process.is_alive() and time.monotonic() - self.cancel_time > 8:
                self.process.terminate()
            if not self.process.is_alive():
                self.process.join()
                self.drain()
                task = self.active
                if task.status in ("运行", "取消中"):
                    task.status = "取消" if self.cancel_time else "失败"
                    task.message = ("任务已停止；长时间外部转换可能需要关闭隐藏的 Word/LibreOffice。"
                                    if self.cancel_time else "处理进程异常结束，可重试或检查源文件。")
                if self.stage and self.stage.exists():
                    shutil.rmtree(self.stage, ignore_errors=True)
                self.process.close()
                self.events.close()
                self.events.join_thread()
                self.active, self.process = None, None
                self.cancel_time = None
                self.save()
                self.changed.emit()
                self.finished.emit(task)
        if not self.active and not self.stopping:
            task = next((t for t in self.tasks if t.status == "等待"), None)
            if task:
                self.start(task)

    def start(self, task):
        self.active = task
        self.events, self.cancel_event = self.ctx.Queue(), self.ctx.Event()
        self.stage = Path(task.output) / f".document-studio-{task.id}" if task.output else None
        self.process = self.ctx.Process(target=worker, args=(asdict(task), self.events, self.cancel_event,
                                          str(self.settings.root / "checkpoints"), str(self.stage) if self.stage else ""))
        task.status = "运行"
        try:
            self.process.start()
        except Exception:
            task.status, task.message = "失败", "无法启动处理进程。"
            self.active = None
            self.process = None
        self.save()
        self.changed.emit()

    def drain(self):
        task = self.active
        while True:
            try:
                item = self.events.get_nowait()
            except queue.Empty:
                break
            kind = item[0]
            if kind == "progress":
                task.progress, task.message = item[1:]
            elif kind == "usage":
                profile = task.options["profile"]
                self.settings.record_usage(profile["id"], task.options.get("model", ""), item[1], item[2])
            elif kind == "output":
                task.outputs.append(item[1])
                self.save()
            elif kind == "done":
                task.status, task.progress = "完成", 100
                task.outputs, task.result = item[1:]
                task.message = "处理完成。" if not task.result else task.result.get("message", "请求完成。")
            elif kind in ("failed", "cancelled"):
                task.status = "失败" if kind == "failed" else "取消"
                task.message = item[1]
            self.changed.emit()

    def shutdown(self):
        self.stopping = True
        if self.active:
            self.cancel(self.active)
        else:
            self.timer.stop()
