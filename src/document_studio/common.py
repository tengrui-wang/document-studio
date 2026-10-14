from __future__ import annotations

import os
from pathlib import Path


class Cancelled(Exception):
    pass


def check_cancel(event):
    if event is not None and event.is_set():
        raise Cancelled("任务已取消，已保存的翻译分块可在重试时恢复。")


def publish(temp: Path, folder: Path, stem: str, suffix: str) -> Path:
    """Atomically link a completed file; exclusive fallback for non-NTFS volumes."""
    folder.mkdir(parents=True, exist_ok=True)
    for index in range(10000):
        dest = folder / f"{stem}{'' if index == 0 else f'_{index}'}{suffix}"
        try:
            os.link(temp, dest)
            return dest
        except FileExistsError:
            continue
        except OSError:
            # Reserve a unique name before copying on file systems without hardlinks.
            try:
                with dest.open("xb") as out:
                    try:
                        import shutil
                        with temp.open("rb") as source:
                            shutil.copyfileobj(source, out)
                        out.flush()
                        os.fsync(out.fileno())
                    except BaseException:
                        dest.unlink(missing_ok=True)
                        raise
                return dest
            except FileExistsError:
                continue
    raise ValueError("输出目录中同名文件过多，请选择其他目录。")


def page_numbers(expression: str, count: int) -> list[int]:
    """One-based inclusive ranges, retaining requested order; forbid duplicates."""
    if not expression.strip():
        return list(range(count))
    result = []
    try:
        for part in expression.split(","):
            bounds = part.strip().split("-")
            if len(bounds) == 1:
                values = [int(bounds[0])]
            elif len(bounds) == 2:
                start, end = map(int, bounds)
                if start > end:
                    raise ValueError()
                values = range(start, end + 1)
            else:
                raise ValueError()
            for value in values:
                if value < 1 or value > count or value - 1 in result:
                    raise ValueError()
                result.append(value - 1)
    except ValueError:
        raise ValueError(f"页码格式错误、重复或越界。共 {count} 页，示例：1-3,5,8。") from None
    return result
