# Document Studio

Windows 10/11 的中文 Word/PDF 文档工作台，当前版本 **0.2.0b1 / v0.2.0-beta.1（预览版）**。离线工具本地执行，翻译使用您主动配置的云端 API。项目采用 AGPL-3.0-or-later。

[GitHub 仓库](https://github.com/tengrui-wang/document-studio) · [Releases 下载](https://github.com/tengrui-wang/document-studio/releases) · [更新记录](CHANGELOG.md)

## 普通用户

从 GitHub Releases 下载 `DocumentStudio-0.2.0b1-Setup.exe` 安装，或解压对应 Windows x64 ZIP 后双击 `DocumentStudio/DocumentStudio.exe`。无需安装 Python。已有 v0.1.0 用户直接运行新版安装包，无需先卸载。

## 安装、升级、卸载与数据

- 程序默认安装在 `%LOCALAPPDATA%/Programs/Document Studio`；个人配置、模型、术语表、任务历史与断点位于 `%LOCALAPPDATA%/DocumentStudio`；API Key 留在 Windows 凭据管理器。
- 固定 AppId `{D7474072-9006-45D3-AD1B-8457879F216A}`，沿用原安装目录与凭据服务 `DocumentStudio/API`。新版安装直接覆盖程序，保留个人数据。安装器拒绝把程序安装到个人数据目录或其父目录。
- 新版“设置 → 检查新版本”显示更新说明；默认正式版通道，可主动勾选预览版。公开仓库无需 GitHub Token；下载到用户数据的 updates 目录，校验大小和 SHA256，通过后才能安装。
- 点击“备份数据并安装”前需结束/取消任务。程序保存术语偏好与任务、备份配置/任务/断点，然后退出，由隐藏的交接程序等待退出并再次校验，最后显示正常安装向导。校验或备份失败不会启动安装。
- 可在 Windows“已安装的应用”中正常卸载。**默认保留全部个人数据、备份和 API Key**，不提供自动彻底清理。重装可继续使用原配置。
- 备份位于用户数据的 backups 子目录，附 SHA256 清单。API Key 不导出到备份。需恢复时关闭软件，把有效备份中的 settings.json、tasks.json 和 checkpoints 内容复制回对应位置；凭据仍由 Windows 管理。不要把这些私人文件上传 GitHub。
- 配置加载兼容 v0.1.0，首次保存前创建迁移备份。损坏配置、任务历史或不兼容的新 schema 不会被自动覆盖，软件会提示恢复。
- 实际安装生命周期检查在独立 GitHub Windows runner 上运行，报告 `INSTALLER-VERIFICATION.json` 随 Release 提供。Windows 10/11 用户机器、完整图形安装流程、断电和磁盘故障恢复仍须后续验收，不能将合成故障测试当作所有故障的完整回滚保证。

1. 左侧选择功能，添加或拖入文件，按需调整参数和输出目录。
2. 点击执行，在任务中心查看进度、取消、失败重试，并打开结果。
3. 翻译前在“AI 模型管理”选择服务商，填 API Key，保存配置。获取模型列表或逐行添加模型 ID。
4. 在翻译页明确选择服务配置、模型与目标语言，执行后生成新 DOCX；可选同时导出 PDF（需要 Word/LibreOffice）。术语表与语言/分块偏好可单独保存。没有密钥时离线工具照常使用。

项目状态见 [PROJECT_STATUS.md](PROJECT_STATUS.md)，详细进度见 [PROGRESS.md](PROGRESS.md)。可使用本地 `dist/DocumentStudio/DocumentStudio.exe` 或 `release/` 中便携包。

## 已实现

- PDF → Word：pdf2docx；原生文字、常见图片和表格，检测明显扫描页并提示。
- Word → PDF：优先 Microsoft Word 自动化，或 LibreOffice。**需安装任一软件**，它们不随包分发。
- 批量输入、自定义输出目录、同名自动编号，原文件不覆盖。
- PDF 合并、按页数拆分、指定页提取与旋转、文本/嵌入位图提取。
- PDF 浅色背景白化、深色文字增强、黑白打印优化、处理前后预览、旋转页图片保护，可选保留原始可搜索文字层。
- DOCX 字体、字号、行距、段前/段后、统一页边距、现有标题格式、跨文字运行的文本替换。
- Word 中英文与其他指定语言翻译，保留图片、表格、公式 XML；PDF 转换后译为 DOCX。
- 分块 ID/顺序/数量/非空及数字遗漏校验、术语表提示、限流/超时重试、校验失败自动减小批量、失败后断点恢复。PDF 导出失败仍保存译文 DOCX。
- OpenAI、DeepSeek、通义千问、Gemini 的 OpenAI 兼容接口，以及 Claude Messages 协议；多配置/多模型、手动地址、模型获取、连接测试。
- Windows Credential Manager 保存密钥；Token 累计与服务/模型分项统计，无密钥明文日志。
- 独立进程串行队列、任务历史、取消、重试、重启后恢复入口；公开 GitHub 更新检查、下载、校验与升级交接。
- PyInstaller 便携包、Inno Setup 安装脚本、GitHub Actions 构建和标签自动发布。

## 真实限制 / 待优化

- 不含 OCR。扫描检测是启发式，混合扫描页、图片内文字仍需人工检查。
- PDF 的复杂公式、多栏、跨页表格与排版不能保证完全还原。
- 当前 PDF 翻译先转 DOCX，可再由 Word/LibreOffice 导出 PDF；未集成 PDFMathTranslate/BabelDOC 的科学论文原版式 PDF 翻译，不使用本地大模型或布局模型。
- 翻译会改变行数、分页和局部字符样式；JSON 校验保障分块映射，不保证模型语义上绝对无漏译。术语一致性依赖提示与模型，请复核。
- DOCX 域（目录/页码等）、公式、图片、图表内部文字保留原样；带修订的文档要求先接受/拒绝修订。未处理评论的翻译。
- 背景白化默认输出图像 PDF。保留文字层模式是在原 PDF 上覆盖处理图像，因此可搜索/复制原文字，但文件较大，原始底层内容仍存在，不用于敏感内容删改。扫描页没有文字层时明确拒绝此模式；图片保护会保留扫描背景，扫描白化需关闭图片保护。
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

沿用现有仓库，推送 main 后自动构建和安装生命周期验证；通过后发布 v* 标签。含连字符的预览标签（例如 v0.2.0-beta.1）自动标记 prerelease，不替换 latest 正式版。Release 提供安装包、便携包、源码、SHA256 与安装验证报告。步骤见 [docs/RELEASE.md](docs/RELEASE.md)。

## 架构与后续开发

`app.py` 中文 UI；`jobs.py` 子进程任务/历史；`pdf_tools.py` 和 `word_tools.py` 离线工具；`api.py` 服务协议；`translation.py` XML 翻译与断点；`storage.py` 本机配置/凭据；`updates.py` 更新检查。开发需求、调研、验证和待办见 `docs/` 与 `PROGRESS.md`。

依赖许可见 [docs/THIRD_PARTY.md](docs/THIRD_PARTY.md)，发行包附安装依赖的许可原文和版本清单。Qt DLL 采用独立目录分发，允许按 LGPL 条款替换；发布时须同时提供匹配版本源码。
