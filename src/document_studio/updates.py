"""Public GitHub updates, bounded verified downloads and explicit installer handoff."""
from __future__ import annotations
import base64
import hashlib
import os
import re
import subprocess
import uuid
from pathlib import Path
from urllib.parse import urlsplit, quote
import httpx
from packaging.version import Version, InvalidVersion
from . import __version__, DEFAULT_REPOSITORY
from .common import check_cancel, publish

DOWNLOAD_HOSTS = {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}
MAX_INSTALLER = 512 * 1024 * 1024


def repository_name(value):
    value = value.strip() or DEFAULT_REPOSITORY
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ValueError("GitHub 仓库格式应为 owner/repository。")
    return value


def release_info(data, repository):
    tag = data["tag_name"]
    if not isinstance(tag, str) or not re.fullmatch(r"v?[0-9][A-Za-z0-9.+-]*", tag):
        raise ValueError("Release 版本号格式无效。")
    version = Version(tag.lstrip("v"))
    name = f"DocumentStudio-{version}-Setup.exe"
    prefix = f"https://github.com/{repository}/releases/download/{quote(tag, safe='')}/"
    assets = {a["name"]: a for a in data.get("assets", []) if isinstance(a, dict) and isinstance(a.get("name"), str)}
    asset, checksum = assets.get(name), assets.get(name + ".sha256")
    if asset is not None:
        if asset.get("browser_download_url") != prefix + name or not isinstance(asset.get("size"), int) or not 0 < asset["size"] <= MAX_INSTALLER:
            raise ValueError("安装包地址或大小不可信，已停止更新。")
        digest = asset.get("digest") or ""
        if digest and not re.fullmatch(r"sha256:[a-fA-F0-9]{64}", digest):
            raise ValueError("安装包摘要格式无效。")
        asset = {"name": name, "url": prefix + name, "size": asset["size"], "digest": digest}
    if checksum is not None:
        if checksum.get("browser_download_url") != prefix + name + ".sha256":
            raise ValueError("校验文件地址不可信。")
        checksum = prefix + name + ".sha256"
    return {"repository": repository, "tag": tag, "version": str(version),
            "notes": str(data.get("body") or "此版本没有提供更新说明。")[:50000],
            "prerelease": bool(data.get("prerelease")) or version.is_prerelease,
            "url": f"https://github.com/{repository}/releases/tag/{quote(tag, safe='')}",
            "asset": asset, "checksum_url": checksum}


def check_update(repository=DEFAULT_REPOSITORY, include_preview=False, *, client=None, current=__version__):
    repository = repository_name(repository)
    own_client = client is None
    client = client or httpx.Client(timeout=20, follow_redirects=False)
    try:
        response = client.get(f"https://api.github.com/repos/{repository}/releases?per_page=100",
                              headers={"Accept": "application/vnd.github+json"})
        if response.status_code == 404:
            return {"message": "仓库不存在、为私有或尚无 Release。", "url": f"https://github.com/{repository}/releases", "newer": False}
        if response.status_code != 200:
            raise ValueError(f"GitHub 更新检查失败（HTTP {response.status_code}），无需 Token，请稍后重试。")
        rows = response.json()
        if not isinstance(rows, list):
            raise ValueError("GitHub Release 响应格式错误。")
        candidates = []
        for row in rows:
            if not isinstance(row, dict) or row.get("draft"):
                continue
            try:
                info = release_info(row, repository)
            except (KeyError, TypeError, InvalidVersion):
                continue
            if include_preview or not info["prerelease"]:
                candidates.append(info)
        if not candidates:
            return {"message": "所选更新通道暂无 Release。", "url": f"https://github.com/{repository}/releases", "newer": False}
        newest = max(candidates, key=lambda entry: Version(entry["version"]))
        newer = Version(newest["version"]) > Version(current)
        return {"message": f"发现{'预览版' if newest['prerelease'] else '正式版'} {newest['tag']}。" if newer else f"当前 {current}，所选通道无更新版本。",
                "newer": newer, "release": newest, "url": newest["url"]}
    except (httpx.HTTPError, InvalidVersion, TypeError, KeyError):
        raise ValueError("无法检查更新，请检查网络、代理或 Release 版本格式。") from None
    finally:
        if own_client:
            client.close()


def safe_download_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in DOWNLOAD_HOSTS or parsed.username or parsed.password
        or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError("下载重定向离开可信 GitHub 域名，已停止下载。")


def stream_download(client, url, output, limit, cancel, progress=None):
    for _ in range(6):
        check_cancel(cancel)
        safe_download_url(url)
        with client.stream("GET", url, follow_redirects=False) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                url = str(response.url.join(response.headers.get("location", "")))
                continue
            if response.status_code != 200:
                raise ValueError(f"下载失败（HTTP {response.status_code}），可重试；未修改个人配置。")
            count = 0
            for block in response.iter_bytes(128 * 1024):
                check_cancel(cancel)
                count += len(block)
                if count > limit:
                    raise ValueError("下载大小超过允许范围，已停止。")
                output.write(block)
                if progress:
                    progress(min(95, int(count * 95 / limit)), f"已下载 {count // 1024:,} KB")
            return count
    raise ValueError("下载重定向次数过多。")


def download_update(info, root: Path, progress, cancel, *, client=None):
    repository = repository_name(info["repository"])
    tag, asset = info["tag"], info.get("asset")
    if not asset:
        raise ValueError("该 Release 没有兼容的 Windows 安装包。")
    name = f"DocumentStudio-{Version(info['version'])}-Setup.exe"
    prefix = f"https://github.com/{repository}/releases/download/{quote(tag, safe='')}/"
    if asset.get("name") != name or asset.get("url") != prefix + name or not isinstance(asset.get("size"), int) or not 0 < asset["size"] <= MAX_INSTALLER:
        raise ValueError("安装包元数据校验失败。")
    digest = asset.get("digest") or ""
    expected = digest[7:].lower() if re.fullmatch(r"sha256:[a-fA-F0-9]{64}", digest) else None
    own_client = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(60, connect=15))
    root.mkdir(parents=True, exist_ok=True)
    part = root / f".download-{uuid.uuid4().hex}.part"
    try:
        if expected is None:
            import io
            checksum_url = info.get("checksum_url")
            if checksum_url != prefix + name + ".sha256":
                raise ValueError("缺少可信 SHA256 校验，禁止安装。")
            buffer = io.BytesIO()
            stream_download(client, checksum_url, buffer, 4096, cancel)
            words = buffer.getvalue().decode("ascii").strip().split()
            if len(words) != 2 or not re.fullmatch(r"[a-fA-F0-9]{64}", words[0]) or words[1].lstrip("*") != name:
                raise ValueError("SHA256 文件格式或安装包名称不匹配。")
            expected = words[0].lower()
        with part.open("xb") as output:
            count = stream_download(client, asset["url"], output, asset["size"], cancel, progress)
            output.flush()
            os.fsync(output.fileno())
        if count != asset["size"]:
            raise ValueError("安装包下载不完整，请重试。")
        with part.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError("SHA256 校验失败，禁止运行此安装包，请重新下载。")
        check_cancel(cancel)
        target = publish(part, root, Path(name).stem, ".exe")
        return {"message": "安装包已下载并通过 SHA256 校验。", "installer": str(target), "sha256": actual, "release": info}
    except httpx.HTTPError:
        raise ValueError("更新下载网络中断，可重试；未修改原有设置。") from None
    finally:
        part.unlink(missing_ok=True)
        if own_client:
            client.close()


def installer_handoff_script(installer: Path, sha256: str, pid: int, error_path: Path):
    def literal(value):
        return "'" + str(value).replace("'", "''") + "'"
    return (f"$ErrorActionPreference='Stop'; try {{ Wait-Process -Id {int(pid)} -Timeout 45 -ErrorAction SilentlyContinue; "
            f"if (Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue) {{ throw 'Application still running' }}; "
            f"if ((Get-FileHash -LiteralPath {literal(installer)} -Algorithm SHA256).Hash.ToLower() -ne {literal(sha256)}) {{ throw 'Checksum mismatch' }}; "
            f"Start-Process -FilePath {literal(installer)} }} catch {{ Set-Content -LiteralPath {literal(error_path)} -Value 'Installer launch failed. Close Document Studio and retry the verified download.' }}")


def launch_installer(installer: Path, sha256: str):
    if os.name != "nt" or installer.suffix.lower() != ".exe" or not re.fullmatch(r"[a-f0-9]{64}", sha256):
        raise ValueError("仅支持已校验的 Windows EXE 安装包。")
    with installer.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != sha256:
            raise ValueError("安装包在下载后发生变化，禁止运行，请重新下载。")
    script = installer_handoff_script(installer.resolve(), sha256, os.getpid(), installer.parent / "installer-launch-error.txt")
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    executable = Path(os.environ.get("SYSTEMROOT", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    return subprocess.Popen([str(executable), "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand", encoded],
                            creationflags=subprocess.CREATE_NO_WINDOW)
