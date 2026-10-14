# 2026-10-14 简要技术调研

- [PDFMathTranslate](https://github.com/PDFMathTranslate/PDFMathTranslate)：科学 PDF 保留公式与排版的成熟翻译工具，AGPL-3.0；当前主线 Python 3.11/3.12 且依赖较重。参考其文档分块与布局保留思路，本版不复制代码、不内置布局/本地 AI 模型，后续评估可选独立后端。
- [pdf2docx](https://github.com/ArtifexSoftware/pdf2docx)：从 PyMuPDF 提取文字/图片/绘图，规则解析布局并由 python-docx 写入 DOCX，现为 MIT。上游说明不再主动维护，因此固定测试版本，保留升级/替换后端接口，复杂排版明确提示限制。
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF)：成熟 PDF 操作、提取、渲染库，AGPL/商业双许可。应用按 AGPL 开源。其官方文档明确不支持多线程共享调用；本版文档任务隔离在单独进程内串行处理，预览仅在主进程执行。
- [python-docx](https://github.com/python-openxml/python-docx)：MIT，适合 Word 结构/样式处理。翻译直接改 DOCX XML 的文字节点并保留其余 ZIP 成员，避免把整段替换成纯文本而删除图像和公式。
- Word → PDF 使用本机 Microsoft Word 的 ExportAsFixedFormat 或 LibreOffice 无界面模式；不重造分页/排版引擎。
- [OpenAI Chat API](https://developers.openai.com/api/reference/resources/chat) / [模型列表](https://developers.openai.com/api/reference/resources/models/methods/list)：Bearer 凭据，Chat Completions 与 /models；无默认模型。只列模型，不假设全部具备聊天能力。
- [DeepSeek API](https://api-docs.deepseek.com/)、[千问兼容协议](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope)、[Gemini 兼容协议](https://ai.google.dev/gemini-api/docs/openai)：采用 HTTPS OpenAI 兼容路径预设，用户可修改区域端点。
- [Claude Messages](https://platform.claude.com/docs/en/api/messages/create)：独立 x-api-key / anthropic-version 及 Messages 请求结构，使用原生适配。

已在实现前核对上述项目及官方 API 资料；不针对最新/特定模型编写硬编码默认值。
