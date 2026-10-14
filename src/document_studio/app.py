from __future__ import annotations

import multiprocessing
import os
import sys
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLabel, QPushButton, QFileDialog, QLineEdit, QComboBox,
    QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QScrollArea, QAbstractItemView, QDialog)

from . import __version__
from .api import PRESETS, validate_base_url
from .jobs import Task, TaskManager
from .storage import Settings, Credentials, backup_user_data


def button(text, callback):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    return widget


def combo(items):
    widget = QComboBox()
    for label, value in items:
        widget.addItem(label, value)
    return widget


def number(value, low, high, decimals=0):
    widget = QDoubleSpinBox() if decimals else QSpinBox()
    widget.setRange(low, high)
    if decimals:
        widget.setDecimals(decimals)
    widget.setValue(value)
    return widget


def note(text):
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("color:#526176; padding:8px 0;")
    return label


class FileList(QListWidget):
    def __init__(self, extensions):
        super().__init__()
        self.extensions = extensions
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setMinimumHeight(110)

    def add_paths(self, paths):
        existing = {self.item(i).text().casefold() for i in range(self.count())}
        for path in paths:
            path = Path(path)
            if path.is_file() and path.suffix.lower() in self.extensions and str(path.resolve()).casefold() not in existing:
                self.addItem(str(path.resolve()))
                existing.add(str(path.resolve()).casefold())

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.add_paths([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()


class WorkPage(QWidget):
    def __init__(self, window, title, extensions):
        super().__init__()
        self.window = window
        self.layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName("heading")
        self.layout.addWidget(heading)
        self.files = FileList(extensions)
        self.layout.addWidget(note("拖入文件或批量选择。合并时按列表顺序；可用上移/下移调整。"))
        self.layout.addWidget(self.files)
        row = QHBoxLayout()
        row.addWidget(button("添加文件", self.select_files))
        row.addWidget(button("移除选中", self.remove_files))
        row.addWidget(button("清空", self.files.clear))
        row.addWidget(button("上移", lambda: self.move(-1)))
        row.addWidget(button("下移", lambda: self.move(1)))
        row.addStretch()
        self.layout.addLayout(row)
        self.form = QFormLayout()
        self.layout.addLayout(self.form)
        self.output = QLineEdit(window.settings.data["output_dir"] or str(Path.home() / "Documents/Document Studio 输出"))
        outrow = QHBoxLayout()
        outrow.addWidget(self.output)
        outrow.addWidget(button("浏览…", self.choose_output))
        self.form.addRow("输出目录", outrow)

    def select_files(self):
        filters = "文档 (" + " ".join("*" + ext for ext in self.files.extensions) + ")"
        paths, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", filters)
        self.files.add_paths(paths)

    def remove_files(self):
        for item in self.files.selectedItems():
            self.files.takeItem(self.files.row(item))

    def move(self, direction):
        row = self.files.currentRow()
        target = row + direction
        if row >= 0 and 0 <= target < self.files.count():
            item = self.files.takeItem(row)
            self.files.insertItem(target, item)
            self.files.setCurrentRow(target)

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output.text())
        if path:
            self.output.setText(path)

    def advanced(self):
        group = QGroupBox("高级参数")
        group.setCheckable(True)
        group.setChecked(False)
        outer = QVBoxLayout(group)
        content = QWidget()
        form = QFormLayout(content)
        outer.addWidget(content)
        content.setVisible(False)
        group.toggled.connect(content.setVisible)
        self.layout.addWidget(group)
        return form

    def submit(self, operation, options=None, allowed=None, merge=False):
        try:
            paths = [self.files.item(i).text() for i in range(self.files.count())]
            if not paths:
                raise ValueError("请先选择文件。")
            if allowed and any(Path(path).suffix.lower() not in allowed for path in paths):
                raise ValueError("列表中存在不适合当前操作的文件，请移除或切换操作。")
            if any(not Path(path).is_file() for path in paths):
                raise ValueError("部分源文件已移动或删除，请重新选择。")
            if not self.output.text().strip():
                raise ValueError("请选择输出目录。")
            output = Path(self.output.text().strip()).resolve()
            output.mkdir(parents=True, exist_ok=True)
            self.window.settings.data["output_dir"] = str(output)
            self.window.settings.save()
            groups = [paths] if merge else [[path] for path in paths]
            for group in groups:
                self.window.manager.add(Task(f"{operation} · {Path(group[0]).name}", operation, group, str(output), options or {}))
            self.window.nav.setCurrentRow(5)
            self.window.statusBar().showMessage(f"已添加 {len(groups)} 个任务", 5000)
        except Exception as exc:
            self.window.error(exc)


class ConvertPage(WorkPage):
    def __init__(self, window):
        super().__init__(window, "格式转换", (".pdf", ".docx"))
        self.mode = combo([("PDF → Word", "pdf_to_word"), ("Word → PDF", "word_to_pdf")])
        self.backend = combo([("自动：优先 Microsoft Word", "auto"), ("Microsoft Word", "word"), ("LibreOffice", "libreoffice")])
        self.form.addRow("转换方式", self.mode)
        self.form.addRow("Word 导出引擎", self.backend)
        self.engine_status = note("")
        self.layout.addWidget(self.engine_status)
        self.layout.addWidget(button("重新检测 Word / LibreOffice", self.refresh_engines))
        self.refresh_engines()
        self.layout.addWidget(note("PDF → Word 适用于含原生文字的 PDF；扫描页需先 OCR。复杂公式、多栏和表格不能保证完全还原。Word → PDF 需要本机安装 Word 或 LibreOffice。"))
        self.layout.addWidget(button("开始批量转换", self.run))
        self.layout.addStretch()

    def run(self):
        operation = self.mode.currentData()
        self.submit(operation, {"backend": self.backend.currentData(), "soffice": self.window.settings.data["soffice"]},
                    (".pdf",) if operation == "pdf_to_word" else (".docx",))

    def refresh_engines(self):
        from .word_tools import detect_engines
        engines = detect_engines(self.window.settings.data["soffice"])
        self.engine_status.setText(f"Microsoft Word：{'已检测到' if engines['word'] else '未检测到'}；LibreOffice：{'已检测到' if engines['libreoffice'] else '未检测到'}。不会自动安装依赖。")


class TranslatePage(WorkPage):
    def __init__(self, window):
        super().__init__(window, "文档翻译", (".docx", ".pdf"))
        self.profile = QComboBox()
        self.model = QComboBox()
        self.source = combo([("中文", "Chinese"), ("英语", "English"), ("自动识别", "auto")])
        self.target = combo([("英语", "English"), ("中文", "Chinese"), ("日语", "Japanese"), ("德语", "German"), ("法语", "French")])
        self.source.setEditable(True)
        self.target.setEditable(True)
        self.output_pdf = QCheckBox("同时输出译文 PDF（需要 Word 或 LibreOffice）")
        self.form.addRow("服务配置", self.profile)
        self.form.addRow("翻译模型", self.model)
        self.form.addRow("原文语言", self.source)
        self.form.addRow("目标语言", self.target)
        self.form.addRow(self.output_pdf)
        advanced = self.advanced()
        self.chunk = number(2500, 200, 6000)
        preferences = window.settings.data["translation_preferences"]
        self.chunk.setValue(preferences.get("chunk_size", 2500))
        for widget, key in ((self.source, "source_lang"), (self.target, "target_lang")):
            if key in preferences:
                index = widget.findData(preferences[key])
                if index >= 0:
                    widget.setCurrentIndex(index)
                else:
                    widget.setEditText(preferences[key])
        self.glossary = QTextEdit()
        self.glossary.setPlaceholderText("每行一个术语，例如：machine learning = 机器学习")
        self.glossary.setMaximumHeight(100)
        self.glossary.setPlainText(window.settings.data["glossary"])
        advanced.addRow(button("保存术语表及翻译偏好", self.save_preferences))
        advanced.addRow("每批字符预算", self.chunk)
        advanced.addRow("术语表", self.glossary)
        self.layout.addWidget(note("将文档文本发送至所选云服务，会产生该服务的费用。Word 保留图片、公式及 XML 结构，译文可能改变分页和局部字体样式。PDF 先转 Word，输出 DOCX；当前不提供原版式 PDF 翻译。图片内文字、目录等域和公式保留原样。断点译文保存在本机，可在设置中清除。"))
        self.layout.addWidget(button("开始翻译并另存", self.run))
        self.layout.addStretch()
        self.profile.currentIndexChanged.connect(self.refresh_models)
        self.refresh_profiles()

    def refresh_profiles(self):
        previous = self.profile.currentData()
        self.profile.clear()
        self.profile.addItem("请选择服务配置", None)
        for profile in self.window.settings.data["profiles"]:
            self.profile.addItem(profile["name"], profile["id"])
        index = self.profile.findData(previous)
        self.profile.setCurrentIndex(max(0, index))
        self.refresh_models()

    def selected_profile(self):
        return next((p for p in self.window.settings.data["profiles"] if p["id"] == self.profile.currentData()), None)

    def refresh_models(self):
        previous = self.model.currentText()
        self.model.clear()
        self.model.addItem("请选择模型", None)
        profile = self.selected_profile()
        if profile:
            for model in profile["models"]:
                self.model.addItem(model, model)
            index = self.model.findText(previous)
            self.model.setCurrentIndex(max(0, index))

    def run(self):
        try:
            profile = self.selected_profile()
            if not profile or not self.model.currentData():
                raise ValueError("请在 AI 模型管理保存服务和模型，然后明确选择翻译模型。")
            if self.output_pdf.isChecked():
                from .word_tools import detect_engines
                engines = detect_engines(self.window.settings.data["soffice"])
                if not engines["word"] and not engines["libreoffice"]:
                    raise ValueError("译文 PDF 输出需要 Word 或 LibreOffice；尚未开始 API 请求，请安装导出引擎或只输出 DOCX。")
            source = self.source.currentData() or self.source.currentText()
            target = self.target.currentData() or self.target.currentText()
            if not source.strip() or not target.strip() or source == target:
                raise ValueError("原文和目标语言必须非空且不同。")
            if not self.save_preferences():
                return
            self.submit("translate", {"profile": dict(profile), "model": self.model.currentData(),
                        "source_lang": source, "target_lang": target, "chunk_size": self.chunk.value(),
                        "glossary": self.glossary.toPlainText(), "output_pdf": self.output_pdf.isChecked(),
                        "soffice": self.window.settings.data["soffice"]}, (".pdf", ".docx"))
        except Exception as exc:
            self.window.error(exc)

    def save_preferences(self):
        try:
            self.window.settings.data["glossary"] = self.glossary.toPlainText()
            self.window.settings.data["translation_preferences"] = {"chunk_size": self.chunk.value(),
                "source_lang": self.source.currentData() or self.source.currentText(),
                "target_lang": self.target.currentData() or self.target.currentText()}
            self.window.settings.save()
            self.window.statusBar().showMessage("术语表和翻译偏好已保存", 4000)
            return True
        except Exception as exc:
            self.window.error(exc)
            return False


class PDFPage(WorkPage):
    def __init__(self, window):
        super().__init__(window, "PDF 工具", (".pdf",))
        self.operation = combo([("合并", "merge"), ("拆分", "split"), ("提取页面", "extract_pages"),
            ("旋转页面", "rotate"), ("提取文本", "extract_text"), ("提取嵌入图片", "extract_images"), ("背景白化 / 打印优化", "whiten")])
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("留空表示全部，例如 1-3,5,8；旋转仅改变指定页")
        self.split_size = number(1, 1, 10000)
        self.angle = combo([("90°", 90), ("180°", 180), ("270°", 270)])
        self.form.addRow("操作", self.operation)
        self.form.addRow("页码", self.pages)
        self.form.addRow("每份页数（拆分）", self.split_size)
        self.form.addRow("顺时针旋转", self.angle)
        advanced = self.advanced()
        self.dpi = number(144, 72, 300)
        self.threshold = number(180, 120, 245)
        self.monochrome = QCheckBox("转换为黑白")
        self.enhance = QCheckBox("增强深色文字（必要图片仍按保护选项处理）")
        self.keep_text = QCheckBox("保留原始可搜索文字层（预览功能，仅原生文字 PDF）")
        self.preserve = QCheckBox("保留嵌入图片原色（扫描页整页图片也会被保留）")
        self.preserve.setChecked(True)
        advanced.addRow("白化 DPI", self.dpi)
        advanced.addRow("白化阈值（越低越强）", self.threshold)
        advanced.addRow(self.monochrome)
        advanced.addRow(self.enhance)
        advanced.addRow(self.keep_text)
        advanced.addRow(self.preserve)
        self.layout.addWidget(note("白化默认输出图像 PDF。可选“保留文字层”会在原页面上覆盖处理后的图像，以保留搜索和复制，文件较大且不提供 OCR；原始内容仍保存在文件中，不适合敏感内容删改。浅色文字可能受影响，请先预览。扫描 PDF 白化需关闭图片保护。"))
        self.layout.addWidget(button("预览白化效果", self.preview))
        self.layout.addWidget(button("执行 PDF 操作", self.run))
        self.layout.addStretch()

    def options(self):
        return {"pages": self.pages.text(), "split_size": self.split_size.value(), "angle": self.angle.currentData(),
                "dpi": self.dpi.value(), "threshold": self.threshold.value(), "monochrome": self.monochrome.isChecked(),
                "preserve_images": self.preserve.isChecked(), "enhance_text": self.enhance.isChecked(), "keep_text": self.keep_text.isChecked()}

    def run(self):
        operation = self.operation.currentData()
        self.submit(operation, self.options(), (".pdf",), operation == "merge")

    def preview(self):
        try:
            if not self.files.count():
                raise ValueError("请先添加 PDF。预览使用当前选中文件或列表第一份。")
            from .pdf_tools import open_pdf, render_processed
            from .common import page_numbers
            path = (self.files.currentItem() or self.files.item(0)).text()
            dialog = QDialog(self)
            dialog.setWindowTitle("白化预览 · 首个指定页面")
            layout = QVBoxLayout(dialog)
            row = QHBoxLayout()
            with open_pdf(path) as doc:
                page = doc[page_numbers(self.pages.text(), len(doc))[0]]
                import pymupdf as fitz
                for title, pix in (("处理前", page.get_pixmap(matrix=fitz.Matrix(1, 1), colorspace=fitz.csRGB, alpha=False)),
                    ("处理后", render_processed(page, min(self.dpi.value(), 144), self.threshold.value(), self.monochrome.isChecked(), self.preserve.isChecked(), self.enhance.isChecked()))):
                    column = QVBoxLayout()
                    column.addWidget(QLabel(title))
                    image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                    label = QLabel()
                    label.setPixmap(QPixmap.fromImage(image).scaled(430, 580, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    column.addWidget(label)
                    row.addLayout(column)
            layout.addLayout(row)
            layout.addWidget(note("此预览最多 144 DPI；最终输出按设置 DPI 生成。请检查浅色文字和必要图像。"))
            layout.addWidget(button("关闭", dialog.accept))
            dialog.exec()
        except Exception as exc:
            self.window.error(exc)


class WordPage(WorkPage):
    def __init__(self, window):
        super().__init__(window, "Word 工具", (".docx",))
        self.font = QLineEdit()
        self.font.setPlaceholderText("留空保持原字体，例如 宋体 / 等线")
        self.size = number(0, 0, 200, 1)
        self.line = number(0, 0, 5, 1)
        self.before = number(-1, -1, 100, 1)
        self.after = number(-1, -1, 100, 1)
        self.margin = number(0, 0, 10, 1)
        self.heading_size = number(0, 0, 200, 1)
        self.find = QLineEdit()
        self.replace = QLineEdit()
        for label, widget in (("字体", self.font), ("字号（0 保持）", self.size), ("行距倍数（0 保持）", self.line),
                              ("段前 pt（-1 保持）", self.before), ("段后 pt（-1 保持）", self.after),
                              ("统一页边距 cm（0 保持）", self.margin), ("现有标题字号（0 保持）", self.heading_size),
                              ("查找文本", self.find), ("替换为（可为空）", self.replace)):
            self.form.addRow(label, widget)
        self.layout.addWidget(note("仅修改 DOCX；保留图片、表格和公式节点。文本替换支持跨文字运行，不跨公式、图片和域。标题处理针对现有 Heading 样式。原文件不覆盖。"))
        self.layout.addWidget(button("批量处理 Word", self.run))
        self.layout.addStretch()

    def run(self):
        self.submit("word_format", {"font": self.font.text().strip(), "font_size": self.size.value(),
            "line_spacing": self.line.value(), "space_before": None if self.before.value() < 0 else self.before.value(),
            "space_after": None if self.after.value() < 0 else self.after.value(), "margin_cm": self.margin.value(),
            "heading_size": self.heading_size.value(), "find": self.find.text(), "replace": self.replace.text()}, (".docx",))


class AIPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        heading = QLabel("AI 模型管理")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        form = QFormLayout()
        layout.addLayout(form)
        self.profiles = QComboBox()
        self.name = QLineEdit()
        self.provider = QComboBox()
        self.provider.addItems(list(PRESETS))
        self.base = QLineEdit()
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("留空保持已存密钥；不会显示或写入普通配置")
        self.models = QTextEdit()
        self.models.setPlaceholderText("每行一个模型 ID，可手动添加。模型列表不保证均可用于翻译。")
        self.models.setMaximumHeight(160)
        self.test_model = QComboBox()
        for label, widget in (("已有配置", self.profiles), ("配置名称", self.name), ("服务商预设", self.provider),
                              ("API 基础地址", self.base), ("API Key", self.key), ("模型 ID 列表", self.models),
                              ("连接测试模型", self.test_model)):
            form.addRow(label, widget)
        row = QHBoxLayout()
        row.addWidget(button("保存配置", self.save_profile))
        row.addWidget(button("获取模型列表", lambda: self.request("models")))
        row.addWidget(button("测试所选模型", lambda: self.request("test_api")))
        row.addWidget(button("删除配置及密钥", self.delete_profile))
        layout.addLayout(row)
        layout.addWidget(note("API Key 仅存入当前 Windows 用户的安全凭据管理器。可以创建多个账号或服务配置；不指定默认模型。自定义地址将接收您的密钥和译文请求，请填写可信服务商的 HTTPS 地址。获取模型通常不收费，模型测试可能消耗少量 Token。"))
        self.usage_label = note("")
        layout.addWidget(self.usage_label)
        layout.addStretch()
        self.profiles.currentIndexChanged.connect(self.load_profile)
        self.provider.currentTextChanged.connect(self.preset)
        self.models.textChanged.connect(self.refresh_test_models)
        self.refresh_profiles()

    def refresh_profiles(self, selected=None):
        self.profiles.blockSignals(True)
        self.profiles.clear()
        self.profiles.addItem("新建配置", None)
        for profile in self.window.settings.data["profiles"]:
            self.profiles.addItem(profile["name"], profile["id"])
        self.profiles.setCurrentIndex(max(0, self.profiles.findData(selected)))
        self.profiles.blockSignals(False)
        self.load_profile()
        self.refresh_usage()

    def preset(self):
        self.base.setText(PRESETS[self.provider.currentText()][1])

    def load_profile(self):
        profile = next((p for p in self.window.settings.data["profiles"] if p["id"] == self.profiles.currentData()), None)
        self.key.clear()
        self.provider.blockSignals(True)
        if profile:
            self.name.setText(profile["name"])
            selected = next((name for name, (protocol, url) in PRESETS.items() if protocol == profile["provider"] and url == profile["base_url"]),
                            "Anthropic Claude" if profile["provider"] == "anthropic" else "自定义 OpenAI 兼容")
            self.provider.setCurrentText(selected)
            self.base.setText(profile["base_url"])
            self.models.setPlainText("\n".join(profile["models"]))
        else:
            self.name.clear()
            self.provider.setCurrentIndex(0)
            self.preset()
            self.models.clear()
        self.provider.blockSignals(False)
        self.refresh_test_models()

    def refresh_test_models(self):
        previous = self.test_model.currentText()
        self.test_model.clear()
        self.test_model.addItem("请选择测试模型", None)
        for name in dict.fromkeys(line.strip() for line in self.models.toPlainText().splitlines() if line.strip()):
            self.test_model.addItem(name, name)
        self.test_model.setCurrentIndex(max(0, self.test_model.findText(previous)))

    def save_profile(self):
        try:
            name = self.name.text().strip()
            if not name:
                raise ValueError("请填写配置名称。")
            base = validate_base_url(self.base.text())
            ident = self.profiles.currentData() or uuid.uuid4().hex
            if self.key.text().strip():
                Credentials().set(ident, self.key.text())
            elif self.profiles.currentData() is None:
                raise ValueError("新配置需要填写 API Key；若暂未准备，请继续使用离线工具。")
            models = list(dict.fromkeys(line.strip() for line in self.models.toPlainText().splitlines() if line.strip()))
            profile = {"id": ident, "name": name, "provider": PRESETS[self.provider.currentText()][0], "base_url": base, "models": models}
            profiles = self.window.settings.data["profiles"]
            self.window.settings.data["profiles"] = [p for p in profiles if p["id"] != ident] + [profile]
            self.window.settings.save()
            self.refresh_profiles(ident)
            self.window.translate.refresh_profiles()
            self.window.statusBar().showMessage("服务配置已保存，密钥存储在 Windows 凭据管理器", 5000)
            return profile
        except Exception as exc:
            self.key.clear()
            self.window.error(exc)
            return None

    def request(self, operation):
        model = self.test_model.currentData()
        if operation == "test_api" and not model:
            self.window.error(ValueError("请先添加并选择测试模型。"))
            return
        profile = self.save_profile()
        if profile:
            self.window.manager.add(Task("获取模型" if operation == "models" else "连接测试", operation, [], "", {"profile": profile, "model": model or ""}))
            self.window.nav.setCurrentRow(5)

    def delete_profile(self):
        try:
            ident = self.profiles.currentData()
            if not ident:
                return
            Credentials().delete(ident)
            self.window.settings.data["profiles"] = [p for p in self.window.settings.data["profiles"] if p["id"] != ident]
            self.window.settings.save()
            self.refresh_profiles()
            self.window.translate.refresh_profiles()
        except Exception as exc:
            self.window.error(exc)

    def refresh_usage(self):
        total_in = sum(value["input"] for value in self.window.settings.data["usage"].values())
        total_out = sum(value["output"] for value in self.window.settings.data["usage"].values())
        self.usage_label.setText(f"累计服务商返回用量：输入 {total_in:,} / 输出 {total_out:,} Token（不估算费用；未返回用量的接口计为 0）。配置文件中保留按服务/模型分项统计。")


class TasksPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        heading = QLabel("任务中心")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["任务", "状态", "进度", "信息"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        row.addWidget(button("取消选中", lambda: self.act("cancel")))
        row.addWidget(button("重试选中", lambda: self.act("retry")))
        row.addWidget(button("打开输出文件", self.open_output))
        row.addWidget(button("打开输出目录", self.open_folder))
        row.addWidget(button("查看详细信息", self.details))
        layout.addLayout(row)
        layout.addWidget(note("任务依次处理；进度为阶段估计。取消耗时操作最多等待约 8 秒后停止处理进程。重试翻译会复用已校验的分块；重启后未完成任务可手动重试。"))
        window.manager.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        selected = self.table.currentRow()
        tasks = self.window.manager.tasks
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            for col, value in enumerate((task.title, task.status, f"{task.progress}%", task.message)):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.table.setItem(row, col, item)
        if 0 <= selected < len(tasks):
            self.table.selectRow(selected)
        elif tasks:
            self.table.selectRow(len(tasks) - 1)

    def selected(self):
        row = self.table.currentRow()
        return self.window.manager.tasks[row] if 0 <= row < len(self.window.manager.tasks) else None

    def act(self, name):
        try:
            task = self.selected()
            if task:
                getattr(self.window.manager, name)(task)
        except Exception as exc:
            self.window.error(exc)

    def open_output(self):
        task = self.selected()
        if task and task.outputs:
            QDesktopServices.openUrl(QUrl.fromLocalFile(task.outputs[0]))
        elif task and task.result.get("url"):
            QDesktopServices.openUrl(QUrl(task.result["url"]))

    def open_folder(self):
        task = self.selected()
        if task and task.output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(task.output))

    def details(self):
        task = self.selected()
        if task:
            text = task.message + "\n\n" + "\n".join(task.outputs)
            if task.result.get("models"):
                text += "\n获取到的模型：\n" + "\n".join(task.result["models"])
            QMessageBox.information(self, task.title, text)


class SettingsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        heading = QLabel("设置")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        form = QFormLayout()
        self.repository = QLineEdit(window.settings.data["repository"])
        self.repository.setPlaceholderText("owner/document-studio")
        self.soffice = QLineEdit(window.settings.data["soffice"])
        self.soffice.setPlaceholderText("可选：自定义 soffice.exe 绝对路径；默认自动查找")
        self.preview_channel = QCheckBox("包含预览版（正式版通道不会自动推荐预览版）")
        self.preview_channel.setChecked(window.settings.data["update_channel"] == "preview")
        form.addRow("GitHub 更新仓库", self.repository)
        form.addRow("LibreOffice 路径", self.soffice)
        form.addRow("更新通道", self.preview_channel)
        layout.addLayout(form)
        layout.addWidget(button("保存设置", self.save))
        layout.addWidget(button("检查新版本", self.updates))
        self.update_label = note("更新无需 GitHub Token；只有点击安装后才退出应用并启动安装向导。")
        layout.addWidget(self.update_label)
        self.release_notes = QTextEdit()
        self.release_notes.setReadOnly(True)
        self.release_notes.setMaximumHeight(150)
        self.release_notes.setPlaceholderText("检查更新后在此显示版本说明")
        layout.addWidget(self.release_notes)
        self.available_release = None
        self.downloaded = None
        self.download_button = button("下载新版本安装包", self.download)
        self.install_button = button("备份数据并安装已下载更新", self.install)
        self.download_button.setEnabled(False)
        self.install_button.setEnabled(False)
        layout.addWidget(self.download_button)
        layout.addWidget(self.install_button)
        layout.addWidget(button("备份个人配置、任务及翻译断点", self.backup))
        layout.addWidget(button("打开本机数据目录", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(window.settings.root)))))
        layout.addWidget(button("清除本机翻译断点", self.clear_cache))
        layout.addWidget(note(f"Document Studio {__version__} · AGPL-3.0-or-later\n设置、任务历史与断点译文位于：{window.settings.root}\n断点包含译文，任务历史包含文件路径及术语表；请按私人文档保护本机账户。仅主动翻译、模型测试/获取和更新检查访问网络。清除断点后无法续传。"))
        layout.addStretch()
        for task in reversed(window.manager.tasks):
            if task.operation == "download_update" and task.status == "完成":
                self.receive_update(task)
                break

    def save(self):
        try:
            self.window.settings.data["repository"] = self.repository.text().strip()
            self.window.settings.data["soffice"] = self.soffice.text().strip()
            self.window.settings.data["update_channel"] = "preview" if self.preview_channel.isChecked() else "stable"
            self.window.settings.save()
            self.window.statusBar().showMessage("设置已保存", 4000)
            return True
        except Exception as exc:
            self.window.error(exc)
            return False

    def updates(self):
        if not self.save():
            return
        self.window.manager.add(Task("检查新版本", "updates", [], "", {"repository": self.repository.text().strip(), "include_preview": self.preview_channel.isChecked()}))
        self.window.nav.setCurrentRow(5)

    def receive_update(self, task):
        from packaging.version import Version
        if task.operation == "updates":
            self.available_release = task.result.get("release") if task.result.get("newer") else None
            self.update_label.setText(task.result.get("message", ""))
            self.release_notes.setPlainText(task.result.get("release", {}).get("notes", ""))
            self.download_button.setEnabled(bool(self.available_release and self.available_release.get("asset")))
        elif task.operation == "download_update" and task.result.get("installer"):
            self.downloaded = task.result
            self.update_label.setText(f"{task.result['release']['tag']} 已下载并校验。安装将保留个人数据，首先创建备份。")
            self.release_notes.setPlainText(task.result["release"]["notes"])
            self.install_button.setEnabled(Path(task.result["installer"]).is_file() and Version(task.result["release"]["version"]) > Version(__version__))

    def download(self):
        if self.available_release:
            if any(t.operation == "download_update" and t.status in ("运行", "等待", "取消中") for t in self.window.manager.tasks):
                self.window.error(ValueError("更新下载已经在进行。"))
                return
            self.window.manager.add(Task("下载更新安装包", "download_update", [], "", {"release": self.available_release}))
            self.window.nav.setCurrentRow(5)

    def backup(self):
        try:
            if self.window.manager.active or any(t.status == "等待" for t in self.window.manager.tasks):
                raise ValueError("请先完成或取消任务，以生成一致的数据备份。")
            self.window.settings.save()
            self.window.manager.save()
            path = backup_user_data(self.window.settings.root)
            self.window.statusBar().showMessage(f"备份已完成：{path}", 10000)
            return path
        except Exception as exc:
            self.window.error(exc)
            return None

    def install(self):
        try:
            if not self.downloaded:
                raise ValueError("请先下载并校验更新安装包。")
            if self.window.manager.active or any(t.status == "等待" for t in self.window.manager.tasks):
                raise ValueError("请先完成或取消任务后再安装更新。")
            if not self.window.translate.save_preferences() or not self.save():
                return
            path = self.backup()
            if path is None:
                return
            from .updates import launch_installer
            launch_installer(Path(self.downloaded["installer"]), self.downloaded["sha256"])
            self.window.close()
        except Exception as exc:
            self.window.error(exc)

    def clear_cache(self):
        try:
            if any(task.operation == "translate" and task.status in ("等待", "运行", "取消中") for task in self.window.manager.tasks):
                raise ValueError("翻译任务正在进行或排队，请先取消或等待完成。")
            # Delete only named checkpoint files inside the app's own data folder.
            cache = self.window.settings.root / "checkpoints"
            if cache.exists():
                answer = QMessageBox.question(self, "清除翻译断点", "这会删除本机保存的断点译文，之后不能续传。确认清除？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes:
                    return
                for path in cache.glob("*.json"):
                    path.unlink()
            self.window.statusBar().showMessage("已清除翻译断点", 4000)
        except Exception as exc:
            self.window.error(exc)


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings or Settings()
        self.manager = TaskManager(self.settings, self)
        self.setWindowTitle(f"Document Studio {__version__}")
        self.resize(1100, 820)
        self.setMinimumSize(850, 640)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        self.nav = QListWidget()
        self.nav.addItems(["首页", "格式转换", "文档翻译", "PDF 工具", "Word 工具", "任务中心", "AI 模型管理", "设置"])
        self.nav.setFixedWidth(155)
        layout.addWidget(self.nav)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        home = QWidget()
        h = QVBoxLayout(home)
        heading = QLabel("Document Studio")
        heading.setObjectName("heading")
        h.addWidget(heading)
        h.addWidget(note("Word / PDF 文档工作台\n本地转换与批量工具 · 云端文档翻译"))
        h.addWidget(note("使用顺序：选择功能 → 添加或拖入文件 → 选择输出目录 → 执行 → 在任务中心打开结果。\n没有 API Key 也可使用全部离线工具。翻译前到 AI 模型管理添加服务配置和模型。\n这是核心预览版本，复杂 PDF 排版和翻译质量需要人工复核。"))
        for index, text in ((1, "转换 Word / PDF"), (3, "处理 PDF"), (4, "批量调整 Word"), (6, "配置翻译 API")):
            h.addWidget(button(text, lambda checked=False, i=index: self.nav.setCurrentRow(i)))
        h.addStretch()
        self.translate = TranslatePage(self)
        self.ai = AIPage(self)
        self.preferences = SettingsPage(self)
        pages = [home, ConvertPage(self), self.translate, PDFPage(self), WordPage(self), TasksPage(self), self.ai, self.preferences]
        for page in pages:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setWidget(page)
            self.stack.addWidget(scroll)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        self.manager.finished.connect(self.task_finished)
        self.closing = False

    def error(self, exc):
        QMessageBox.warning(self, "操作未完成", str(exc))

    def task_finished(self, task):
        if task.status == "完成" and task.operation in ("updates", "download_update"):
            self.preferences.receive_update(task)
            self.nav.setCurrentRow(7)
        if task.operation == "models" and task.status == "完成":
            snapshot = task.options["profile"]
            for profile in self.settings.data["profiles"]:
                if profile["id"] == snapshot["id"] and profile["base_url"] == snapshot["base_url"]:
                    profile["models"] = sorted(set(profile["models"] + task.result["models"]))
            self.settings.save()
            self.ai.refresh_profiles(snapshot["id"])
            self.translate.refresh_profiles()
        self.ai.refresh_usage()
        self.statusBar().showMessage(f"{task.title}：{task.status} · {task.message}", 10000)
        if self.closing:
            self.close()

    def closeEvent(self, event):
        if self.manager.active:
            self.closing = True
            self.manager.shutdown()
            self.statusBar().showMessage("正在停止当前任务并保存断点…")
            event.ignore()
        else:
            self.manager.shutdown()
            event.accept()


def main():
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setApplicationName("Document Studio")
    app.setOrganizationName("DocumentStudio")
    from .lifecycle import create_app_mutex
    try:
        mutex_handle, already_running = create_app_mutex()
        if already_running:
            QMessageBox.information(None, "Document Studio", "Document Studio 已在运行，请切换到已有窗口。")
            return
    except RuntimeError as exc:
        QMessageBox.warning(None, "启动失败", str(exc))
        return
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget { font-family: 'Microsoft YaHei UI', 'Segoe UI'; font-size: 13px; }
        QMainWindow, QScrollArea, QStackedWidget { background: #f5f7fb; }
        QLabel#heading { font-size: 26px; font-weight: 600; color: #16345e; padding: 14px 0; }
        QPushButton { background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 14px; }
        QPushButton:hover { background: #e8f0fe; border-color: #5383cf; }
        QPushButton:pressed { background: #dce8fc; }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit { background: #fff; padding: 5px; border: 1px solid #cbd5e1; border-radius: 4px; }
        QListWidget { background: #fff; border: 1px solid #dce2eb; border-radius: 6px; }
        QListWidget::item { padding: 10px; }
        QListWidget::item:selected { background: #e6efff; color: #153e75; }
        QGroupBox { border: 1px solid #dce2eb; border-radius: 6px; margin-top: 14px; padding: 12px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; }
    """)
    try:
        window = MainWindow()
    except (ValueError, OSError) as exc:
        QMessageBox.warning(None, "配置读取失败", str(exc))
        return
    window.show()
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(1200, app.quit)
    sys.exit(app.exec())
