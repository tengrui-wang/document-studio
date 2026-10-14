import re
import httpx
from packaging.version import Version, InvalidVersion
from . import __version__


def check_update(repository):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository.strip()):
        raise ValueError("请在设置中填写 GitHub 仓库，格式：owner/repository。")
    repository = repository.strip()
    try:
        response = httpx.get(f"https://api.github.com/repos/{repository}/releases/latest", timeout=20,
                             headers={"Accept": "application/vnd.github+json"}, follow_redirects=False)
        if response.status_code == 404:
            return {"message": "仓库尚无正式 Release，或仓库为私有。", "url": f"https://github.com/{repository}/releases"}
        if response.status_code != 200:
            raise ValueError(f"GitHub 更新检查失败（HTTP {response.status_code}），请稍后重试。")
        data = response.json()
        tag = data["tag_name"]
        newer = Version(tag.lstrip("v")) > Version(__version__)
        return {"message": f"发现新版本 {tag}。" if newer else f"当前版本 {__version__} 已是最新正式版。",
                "url": f"https://github.com/{repository}/releases"}
    except (httpx.HTTPError, KeyError, InvalidVersion):
        raise ValueError("无法检查更新，请检查网络或 Release 版本号格式。") from None
