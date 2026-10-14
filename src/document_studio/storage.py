from __future__ import annotations

import json
import os
import tempfile
import uuid
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from . import DEFAULT_REPOSITORY

SCHEMA_VERSION = 1


class SettingsError(ValueError):
    pass


def backup_user_data(root: Path, reason="manual") -> Path:
    """Only copy app-owned state. Credentials remain in Windows Credential Manager."""
    destination = root / "backups" / f"{reason}-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": 1, "reason": reason, "files": {}}
    files = [root / "settings.json", root / "tasks.json"] + list((root / "checkpoints").glob("*.json"))
    for source in files:
        if not source.exists():
            continue
        if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
            raise SettingsError("数据文件含外部链接，已停止备份；原始数据未修改。")
        target = destination / source.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        with target.open("rb") as stream:
            manifest["files"][source.relative_to(root).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    atomic_json(destination / "manifest.json", manifest)
    return destination


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
        self.data = {"profiles": [], "output_dir": "", "repository": DEFAULT_REPOSITORY,
                     "soffice": "", "usage": {}, "glossary": "", "translation_preferences": {},
                     "update_channel": "stable", "schema_version": SCHEMA_VERSION}
        self.needs_migration = False
        if self.path.exists():
            try:
                saved = json.loads(self.path.read_text(encoding="utf-8"))
                self.validate(saved)
                if saved.get("schema_version", 0) > SCHEMA_VERSION:
                    raise SettingsError("配置来自更新版本，请安装对应版本；原始配置保持不变。")
                self.needs_migration = saved.get("schema_version", 0) < SCHEMA_VERSION
                self.data.update(saved)
                self.data["schema_version"] = SCHEMA_VERSION
                if not self.data["repository"]:
                    self.data["repository"] = DEFAULT_REPOSITORY
            except (ValueError, OSError) as exc:
                if isinstance(exc, SettingsError):
                    raise
                raise SettingsError(f"无法安全读取配置，请从 {self.root / 'backups'} 恢复备份；原始文件未改动。") from None

    @staticmethod
    def validate(saved):
        if not isinstance(saved, dict) or not isinstance(saved.get("schema_version", 0), int) or not isinstance(saved.get("profiles", []), list):
            raise SettingsError("配置格式错误，原始文件未改动。")
        ids = set()
        for profile in saved.get("profiles", []):
            if (not isinstance(profile, dict) or any(not isinstance(profile.get(k), str) for k in ("id", "name", "provider", "base_url"))
                or not isinstance(profile.get("models"), list) or any(not isinstance(m, str) for m in profile["models"])
                or not profile["id"] or profile["id"] in ids):
                raise SettingsError("服务配置不完整或 ID 重复，原始文件未改动。")
            ids.add(profile["id"])
        for key in ("output_dir", "repository", "soffice", "glossary", "update_channel"):
            if key in saved and not isinstance(saved[key], str):
                raise SettingsError("软件设置格式错误，原始文件未改动。")
        for key in ("usage", "translation_preferences"):
            if key in saved and not isinstance(saved[key], dict):
                raise SettingsError("统计或翻译设置格式错误，原始文件未改动。")
        for counters in saved.get("usage", {}).values():
            if not isinstance(counters, dict) or any(not isinstance(counters.get(k), int) or counters[k] < 0 for k in ("input", "output")):
                raise SettingsError("Token 统计格式错误，原始文件未改动。")
        preferences = saved.get("translation_preferences", {})
        if "chunk_size" in preferences and (not isinstance(preferences["chunk_size"], int) or not 200 <= preferences["chunk_size"] <= 6000):
            raise SettingsError("翻译分块设置格式错误，原始文件未改动。")
        if any(key in preferences and not isinstance(preferences[key], str) for key in ("source_lang", "target_lang")):
            raise SettingsError("翻译语言设置格式错误，原始文件未改动。")

    def save(self):
        self.validate(self.data)
        if self.needs_migration:
            backup_user_data(self.root, "before-migration")
        # Explicit whitelist: credentials never enter the JSON configuration.
        profiles = []
        for profile in self.data["profiles"]:
            profiles.append({k: profile[k] for k in ("id", "name", "provider", "base_url", "models")})
        self.data["profiles"] = profiles
        atomic_json(self.path, self.data)
        self.needs_migration = False

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
