# Document Studio 开发进度

## 当前目标
完成 Windows 10/11 可运行 0.1.0 核心版本，不做全面 UI 验收。需求见 docs/REQUIREMENTS.md。

## 2026-10-14
- 干净项目初始化；采用 Python/PySide6、独立子进程任务、Windows Credential Manager。
- 已调研 PDFMathTranslate、pdf2docx、PyMuPDF、python-docx，见 docs/RESEARCH.md。
- 项目使用 AGPL-3.0-or-later；不内置本地 AI 模型。
- 已完成八个中文页面、拖拽/批量、另存、独立进程任务、取消/重试/历史与输出打开。
- 已完成 PDF/Word 基础处理、PDF 转 Word、Word/LibreOffice 导出接口、白化/黑白打印与预览。
- 已完成 OpenAI 兼容与 Claude 协议、多服务/多模型、模型列表/测试、Windows 安全凭据与 Token 统计。
- 已完成 DOCX 正文/表格/页眉页脚/脚注/尾注翻译，保留 XML 图片/公式，分块校验/术语提示/断点；PDF 翻译为 DOCX。
- 已完成 PyInstaller、Inno Setup、标签 Release 的 GitHub Actions，以及对应源码/许可分发。
- 验证：18 个必要自动测试通过；源码 UI 启动与八页构造通过；真实本机 Word 导出合成 DOCX 成功；Windows Credential Manager 合成凭据保存/读取/删除成功；EXE UI 启动返回 0。
- 固定 PySide6 6.8.3，修复本机新版 Qt DLL 加载失败。固定依赖见 requirements-lock.txt。
- 本机检测到非交互 GitHub 授权，拟发布到 tengrui-wang/document-studio；实际仓库/Release 状态稍后补记。

## 未完成 / 待优化（不假称已完成）
- OCR 与扫描文档翻译；科学论文原版式 PDF 翻译 / PDFMathTranslate 或 BabelDOC 可选后端。
- 翻译语义质量与术语一致性的真实服务验收；没有真实 API Key，使用模拟接口验证协议/重试/校验。
- 翻译图表内部文字/评论/目录等域，旧 DOC 支持；复杂 PDF 公式、表格和排版仍需人工复核。
- 白化目前栅格输出，丢失可搜索文字、交互信息；后续可评估保留文字层和选择性矢量背景处理。
- 完整安装器验收、Windows 10 独立机验收、代码签名、多分辨率验收留到最终版本。
- 外部办公程序卡住后强制取消可能留下本软件启动的隐藏实例；不终止用户已有办公进程。
- LibreOffice 引擎尚未在本机验证（本机 Word 引擎已通过）。

## 恢复工作
先读取本文件、README.md 和 docs/REQUIREMENTS.md，检查 git status。只按未完成事项继续，避免重新搭建。
