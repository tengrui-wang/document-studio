# Document Studio 项目状态

版本：0.1.0 核心预览版。详细开发记录与待办见 [PROGRESS.md](PROGRESS.md)，需求见 [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)。

## 已交付
- Python/PySide6 源码、八个中文功能页、离线 Word/PDF 处理、批量任务及云端翻译管理。
- API 密钥存入 Windows Credential Manager；无默认模型，离线功能不依赖 API。
- 分块翻译、术语提示、校验/重试/断点恢复；PDF 翻译目前输出 DOCX。
- 本机独立 EXE 与便携 ZIP 已构建并通过启动和子进程输出验证。
- 18 项必要测试通过，本机 Word 导出 PDF 和安全凭据存储真实验证通过。
- 已创建并推送 [GitHub 仓库](https://github.com/tengrui-wang/document-studio)，标签 v0.1.0 自动构建及 Release 发布**成功**。
- [v0.1.0 Release](https://github.com/tengrui-wang/document-studio/releases/tag/v0.1.0) 已提供 Setup EXE、便携 ZIP、SHA256 与对应源码。详细验证记录在 PROGRESS.md。

## 后续重点
OCR、科学论文原版式 PDF 翻译、保留文字层的白化、翻译质量验收、LibreOffice 实机验证、Windows 10 独立机与完整安装验收、代码签名。当前功能的限制均在 README 中明示。

## 开发约定
改动限定本项目，使用已有 Python/Conda 与项目内 .venv，不修改共享环境或其他项目，不重复安装已有软件。重要变化及时本机 Git 提交；仅在用户授权范围内推送。中间阶段只做必要测试；完整验收留到最终版本。不绕过权限或启用 Full Access。删除文件、升级共享环境或系统级变更前须另获授权。
