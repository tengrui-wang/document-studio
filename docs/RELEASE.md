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

4. main 推送 / PR / 手动 dispatch 构建 Actions artifacts；v* 标签成功构建后自动创建 Release，附件包含便携 ZIP、Setup EXE、对应源码 ZIP、二进制 SHA256 文件。Release job 单独最小化 contents:write 权限。发布前检查 tag 和 pyproject 中版本一致。
5. 在软件设置填 `YOUR_ACCOUNT/document-studio`，检查正式版更新。无 Release 或私有仓库会明确提示，不自动下载或执行更新。

没有可用 GitHub 仓库创建/推送凭据时，本地代码和工作流仍完整可用；按上述步骤授权后即可发布。API 密钥与 GitHub 发布凭据相互独立。本机 Git 提交不代表已经发布远端。

注意：默认未签名；真实云服务、不同 Word/LibreOffice 环境和完整安装器验收待最终版本进行。首次版本定位为可用核心预览。
