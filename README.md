# Document Studio

Windows 10/11 的中文 Word/PDF 文档工作台，当前版本 **0.1.0**。离线工具本地执行，翻译使用您主动配置的云端 API。项目采用 AGPL-3.0-or-later。

[GitHub 仓库](https://github.com/tengrui-wang/document-studio) · [v0.1.0 下载](https://github.com/tengrui-wang/document-studio/releases/tag/v0.1.0)

## 普通用户

从 GitHub Releases 下载 `DocumentStudio-0.1.0-Setup.exe` 安装，或解压 `DocumentStudio-0.1.0-Windows-x64.zip` 后双击 `DocumentStudio/DocumentStudio.exe`。无需安装 Python。

1. 左侧选择功能，添加或拖入文件，按需调整参数和输出目录。
2. 点击执行，在任务中心查看进度、取消、失败重试，并打开结果。
3. 翻译前在“AI 模型管理”选择服务商，填 API Key，保存配置。获取模型列表或逐行添加模型 ID。
4. 在翻译页明确选择服务配置、模型与目标语言，执行后生成新 DOCX。没有密钥时离线工具照常使用。

项目状态见 [PROJECT_STATUS.md](PROJECT_STATUS.md)，详细进度见 [PROGRESS.md](PROGRESS.md)。可使用本地 `dist/DocumentStudio/DocumentStudio.exe` 或 `release/` 中便携包。

## 已实现

- PDF → Word：pdf2docx；原生文字、常见图片和表格，检测明显扫描页并提示。
- Word → PDF：优先 Microsoft Word 自动化，或 LibreOffice。**需安装任一软件**，它们不随包分发。
- 批量输入、自定义输出目录、同名自动编号，原文件不覆盖。
- PDF 合并、按页数拆分、指定页提取与旋转、文本/嵌入位图提取。
- PDF 浅色背景白化、黑白打印优化、处理前后预览及嵌入图片保留。
- DOCX 字体、字号、行距、段前/段后、统一页边距、现有标题格式、跨文字运行的文本替换。
- Word 中英文与其他指定语言翻译，保留图片、表格、公式 XML；PDF 转换后译为 DOCX。
- 分块 ID/顺序/数量/非空校验、术语表提示、限流/超时重试、失败后断点恢复。
- OpenAI、DeepSeek、通义千问、Gemini 的 OpenAI 兼容接口，以及 Claude Messages 协议；多配置/多模型、手动地址、模型获取、连接测试。
- Windows Credential Manager 保存密钥；Token 累计与服务/模型分项统计，无密钥明文日志。
- 独立进程串行队列、任务历史、取消、重试、重启后恢复入口；GitHub 正式版更新检查。
- PyInstaller 便携包、Inno Setup 安装脚本、GitHub Actions 构建和标签自动发布。

## 真实限制 / 待优化

- 不含 OCR。扫描检测是启发式，混合扫描页、图片内文字仍需人工检查。
- PDF 的复杂公式、多栏、跨页表格与排版不能保证完全还原。
- 当前 PDF 翻译输出 DOCX；未集成 PDFMathTranslate/BabelDOC 的科学论文原版式 PDF 翻译，不使用本地大模型或布局模型。
- 翻译会改变行数、分页和局部字符样式；JSON 校验保障分块映射，不保证模型语义上绝对无漏译。术语一致性依赖提示与模型，请复核。
- DOCX 域（目录/页码等）、公式、图片、图表内部文字保留原样；带修订的文档要求先接受/拒绝修订。未处理评论的翻译。
- 背景白化输出为**图像 PDF**，丢失可搜索文字、书签及交互；浅色文字/矢量图可能受损。图片保留会保留扫描页背景；处理扫描页需关闭保留选项。
- 输入 Word 仅支持 DOCX，不支持老式 DOC/DOCM。Word/LibreOffice 排版取决于本机字体。
- 外部转换卡住后强制取消可能留下隐藏的 Word/LibreOffice 实例；不主动终止用户已有办公进程。
- 尚无真实 API 翻译质量验收和完整安装/多分辨率验收；没有真实密钥也可开发与测试。
- 安装包未代码签名；首次启动 Windows 可能提示未知发布者。后续可接入签名证书。

## 隐私与安全

所有常规操作本地执行。仅主动翻译、获取模型、连接测试和更新检查联网。翻译把文字与术语表发送给所选服务商；测试模型可能产生少量费用。

API Key 强制使用 Windows 安全凭据管理器，不降级到明文存储。地址必须 HTTPS，不跟随重定向；HTTP 错误不会展示响应体或密钥。自定义地址须为可信服务。配置、任务历史和断点位于 `%LOCALAPPDATA%/DocumentStudio`，历史含文件路径和术语表，断点含译文；请保护 Windows 账户，可在设置中清除断点。程序不自动上传私人文件至 GitHub。

Word 导出前拒绝外部模板、链接图片和 OLE 资源（普通超链接允许），并禁用宏和自动更新 OLE 链接，以避免打开文件时下载外部内容。翻译分块策略若改变到需要重新切片，缓存隔离并重新翻译；相同切片策略的失败重试会续传。

## 开发运行

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
.\.venv\Scripts\python.exe scripts/launcher.py
```

测试：`.\.venv\Scripts\python.exe -m pytest -q`。本机构建：`./scripts/build.ps1`。安装 Inno Setup 6 后同时生成 Setup EXE；未安装时生成便携 ZIP，GitHub Actions 会安装编译器并生成安装包。测试只使用合成文档与模拟 API，不需要密钥。

## GitHub 发布

创建自己的 GitHub 仓库，推送 `main`，Actions 每次推送构建并提供 Actions artifact。确认版本后推送 `v0.1.0` 标签，会生成含安装包、便携包和对应源码的 Release。步骤见 [docs/RELEASE.md](docs/RELEASE.md)。设置中填 `owner/repository` 后可检查正式版更新。

## 架构与后续开发

`app.py` 中文 UI；`jobs.py` 子进程任务/历史；`pdf_tools.py` 和 `word_tools.py` 离线工具；`api.py` 服务协议；`translation.py` XML 翻译与断点；`storage.py` 本机配置/凭据；`updates.py` 更新检查。开发需求、调研、验证和待办见 `docs/` 与 `PROGRESS.md`。

依赖许可见 [docs/THIRD_PARTY.md](docs/THIRD_PARTY.md)，发行包附安装依赖的许可原文和版本清单。Qt DLL 采用独立目录分发，允许按 LGPL 条款替换；发布时须同时提供匹配版本源码。
