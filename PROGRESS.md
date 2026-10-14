# Document Studio 开发进度

## 当前目标
第二轮目标：在原项目上完成更新/覆盖升级/默认保留数据卸载，优先验证真实安装生命周期；发布 0.2.0-beta.1 预览版。需求见 docs/REQUIREMENTS.md，旧版记录保留如下。

## 第二轮（2026-10-14，进行中）
- 已实现：公开 Release 说明、稳定/预览通道、无 Token 安装包下载、限定 HTTPS 重定向、SHA256 与大小校验、取消/失败安全、关闭程序后安装交接。
- 已实现：旧配置只读加载、schema 校验、保存前迁移备份、手工/升级备份、保留未知兼容字段，术语表和语言/分块偏好持久化；损坏配置/历史不覆盖。
- 安装器沿用原 AppId/路径/凭据服务名，默认不删除个人数据；程序/数据重叠拒绝，运行 mutex 与版本资源已加入。
- 38 项必要测试已通过：更新通道/无 Token/下载校验与失败安全、配置兼容/备份/原子失败、白化搜索层与旋转图片保护、数字遗漏与自动拆批、PDF 导出失败保留 DOCX 与断点、付费 API 前检查导出依赖、原有回归。
- 已写 Windows CI 实际安装验证：新装、旧 v0.1.0、复制后故障注入、数据目录拒绝、覆盖升级、安装后的原生凭据/模型/术语/历史读取、卸载保留。**尚未运行，不能标记测试通过。**
- PDF 转 Word 严格报错；Word 导出检测/错误清理；译文 PDF 已通过本机真实 Word 合成文档验证（1 页，数字与表格数字保留，未使用 API）。
- 本机 0.2.0b1 EXE 启动和打包子进程自测通过，FileVersion=0.2.0.0、ProductVersion=0.2.0b1，便携 ZIP 已生成。
- 首次 CI run 38518833871 在构建阶段发现 Windows PowerShell 5 引号差异，导致数字版本命令错误；没有执行安装验证。已改为独立 version.py 避免 shell 引号问题。
- 下一步：再次运行实际安装 CI；只修复实际失败。全部必要验证通过后再打 v0.2.0-beta.1 标签，标记 preview 发布。

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
- 本机便携包已构建：release/DocumentStudio-0.1.0-Windows-x64.zip（137,978,399 字节），附 SHA256。
- 打包后的真实 EXE 启动成功，离线自测成功：安全凭据后端导入、独立子进程 PDF 文本提取/PDF 转 Word/Word 替换并生成输出。报告在 build/packaged-selftest.json（不提交构建目录）。
- GitHub 仓库已创建并推送：[tengrui-wang/document-studio](https://github.com/tengrui-wang/document-studio)，标签 v0.1.0 已推送。
- 标签自动构建：[run 38496679605](https://github.com/tengrui-wang/document-studio/actions/runs/38496679605)，Windows 构建与 Release 两个作业均 **success**。
- [v0.1.0 Release](https://github.com/tengrui-wang/document-studio/releases/tag/v0.1.0) 已发布，包含 DocumentStudio-0.1.0-Setup.exe、便携 ZIP、两份 SHA256 与 DocumentStudio-Source.zip。
- 已将 Release 安装包下载至本机 release/DocumentStudio-0.1.0-Setup.exe（98,658,180 字节）；SHA256 与发布附件一致：9b6b4e14898b23fcfef2eac135e01606bde34d92406bdca86fffc2cd4f60650b。未进行系统安装；完整安装验收留待最终版。
- 本机源码对应标签归档：release/DocumentStudio-0.1.0-Source.zip。源码只包含 Git 跟踪的程序/文档/测试/许可，不包含私人文档、密钥、断点或构建目录。
- 已按后续用户 AGENTS 规则补充 AGENTS.md 和 PROJECT_STATUS.md；依赖安装与修改仅在项目 .venv 内，未改变共享环境或系统软件。

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
