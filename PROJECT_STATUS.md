# Document Studio 项目状态

开发版本：0.2.0b1 / v0.2.0-beta.1（预览）。旧版 v0.1.0 保留。详细开发记录与待办见 [PROGRESS.md](PROGRESS.md)，需求见 [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)。

## 第二轮状态
- 已实现更新说明、正式/预览通道、无需 Token 的安装包下载与 SHA256 校验、退出后安装交接、升级前备份和旧配置兼容。
- 沿用 AppId/安装目录/数据目录/凭据服务；默认卸载保留个人数据。CI 已通过新装/注册卸载/卸载保留合成数据与凭据/旧版安装/备份；故障注入测试正在修正，**完整覆盖升级验证尚未通过**。
- 38 项必要测试、本机打包启动/子进程自测、真实 Word 合成译文 PDF 输出通过。
- 新增白化文字层保留和旋转页图片修复；严格 PDF 转 Word 页错误；数字遗漏检查与自动拆批；术语持久化与 PDF 导出失败保留 DOCX。
- 下一步见 PROGRESS.md；OCR、原版式 PDF 翻译不交付，方案见 docs/ADVANCED_ROUND2.md。无真实付费 API 使用、无用户机器安装/卸载测试。

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
