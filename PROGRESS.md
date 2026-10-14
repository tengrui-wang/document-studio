# Document Studio 开发进度

## 当前目标
完成 Windows 10/11 可运行 0.1.0 核心版本，不做全面 UI 验收。需求见 docs/REQUIREMENTS.md。

## 2026-10-14
- 干净项目初始化；采用 Python/PySide6、独立子进程任务、Windows Credential Manager。
- 已调研 PDFMathTranslate、pdf2docx、PyMuPDF、python-docx，见 docs/RESEARCH.md。
- 项目使用 AGPL-3.0-or-later；不内置本地 AI 模型。
- 正在实现离线工具、云端适配与翻译断点缓存；后续记录实际验证结果。

## 恢复工作
先读取本文件、README.md 和 docs/REQUIREMENTS.md，检查 git status。只按未完成事项继续，避免重新搭建。
