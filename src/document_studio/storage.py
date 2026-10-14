from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path


def data_dir() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local/share")))
    path = root / "DocumentStudio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class Settings:
    def __init__(self, root: Path | None = None):
        self.root = root or data_dir()
        self.path = self.root / "settings.json"
        self.data = {"profiles": [], "output_dir": "", "repository": "", "soffice": "", "usage": {}}
        if self.path.exists():
            try:
                saved = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(saved, dict):
                    raise ValueError()
                self.data.update({k: saved[k] for k in self.data if k in saved})
            except (ValueError, OSError):
                # Keep damaged configuration for manual recovery, never silently discard it.
                self.path.rename(self.root / f"settings-damaged-{uuid.uuid4().hex}.json")

    def save(self):
        # Explicit whitelist: credentials never enter the JSON configuration.
        profiles = []
        for profile in self.data["profiles"]:
            profiles.append({k: profile[k] for k in ("id", "name", "provider", "base_url", "models")})
        self.data["profiles"] = profiles
        atomic_json(self.path, self.data)

    def record_usage(self, profile_id: str, model: str, incoming: int, outgoing: int):
        key = f"{profile_id}/{model}"
        counters = self.data["usage"].setdefault(key, {"input": 0, "output": 0})
        counters["input"] += incoming
        counters["output"] += outgoing
        self.save()


class Credentials:
    """Force Windows Credential Manager. No plaintext or fallback backend."""
    service = "DocumentStudio/API"

    @staticmethod
    def backend():
        if os.name != "nt":
            raise RuntimeError("API 密钥存储仅支持 Windows 安全凭据管理器。")
        from keyring.backends.Windows import WinVaultKeyring
        return WinVaultKeyring()

    def get(self, profile_id: str) -> str:
        try:
            value = self.backend().get_password(self.service, profile_id)
        except Exception:
            raise RuntimeError("无法读取 Windows 凭据管理器，请重新保存 API Key。") from None
        if not value:
            raise ValueError("此服务配置尚未保存 API Key。请在 AI 模型管理中配置。")
        return value

    def set(self, profile_id: str, key: str):
        if not key.strip():
            raise ValueError("API Key 不能为空。")
        try:
            self.backend().set_password(self.service, profile_id, key.strip())
        except Exception:
            raise RuntimeError("Windows 安全凭据存储失败；未写入任何明文密钥。") from None

    def delete(self, profile_id: str):
        try:
            backend = self.backend()
            if backend.get_password(self.service, profile_id):
                backend.delete_password(self.service, profile_id)
        except Exception:
            raise RuntimeError("无法删除 Windows 凭据。") from None
