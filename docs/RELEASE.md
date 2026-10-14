# 构建与发布

1. 使用 Python 3.13 x64 建立虚拟环境并安装 requirements-lock.txt，然后 `pip install --no-deps --no-build-isolation -e .`。
2. `scripts/build.ps1` 运行必要测试、收集许可、PyInstaller 构建并启动冒烟验证，打包 release ZIP。安装 Inno Setup 6 会同步生成每用户 Setup EXE。
3. GitHub 创建标准仓库 `document-studio`，在本项目目录执行：

```powershell
git remote add origin https://github.com/YOUR_ACCOUNT/document-studio.git
git push -u origin main
git tag v0.1.0
git push origin v0.1.0
```

4. main 推送 / PR / 手动 dispatch 构建 Actions artifacts；v* 标签成功构建后自动创建 Release，附件包含便携 ZIP、Setup EXE、对应源码 ZIP、二进制 SHA256 与 INSTALLER-VERIFICATION.json。Release job 单独最小化 contents:write 权限。发布前检查 tag 与应用/pyproject 版本规范化后一致；预览版本使用 Python 0.2.0b1、Git tag v0.2.0-beta.1，自动标记 prerelease，不修改 latest 正式版。
5. 默认更新仓库为 tengrui-wang/document-studio；软件可显示说明、主动下载和校验后安装，无 GitHub Token。正式/预览通道由用户选择；不会自动执行安装。私有仓库不支持无 Token 更新。

固定 AppId、凭据服务和数据路径不得随版本改名。程序目录与用户数据分离；普通卸载永远不删除用户数据或凭据。新增配置字段应兼容原 schema 并在首次保存前备份，不能通过重置配置解决迁移问题。

安装验证脚本 scripts/verify_installer_lifecycle.py **只允许在 GitHub 独立 Windows runner 上执行**，避免改动用户现有安装和配置。它实际运行新安装、已发布 v0.1.0 安装、复制后故障注入、覆盖升级、注册卸载入口和卸载，并比对合成配置/模型/术语表/任务/断点的 SHA256 及 Windows 原生凭据。故障测试安装包只在 build/lifecycle 内，不作为 Release 附件。

没有可用 GitHub 仓库创建/推送凭据时，本地代码和工作流仍完整可用；按上述步骤授权后即可发布。API 密钥与 GitHub 发布凭据相互独立。本机 Git 提交不代表已经发布远端。

注意：默认未签名；真实云服务、不同 Word/LibreOffice 环境和完整安装器验收待最终版本进行。首次版本定位为可用核心预览。
