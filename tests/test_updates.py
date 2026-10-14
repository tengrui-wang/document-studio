import hashlib
import json
from pathlib import Path
from threading import Event
import httpx
import pytest
from document_studio.common import Cancelled
from document_studio.updates import (check_update, release_info, download_update,
    installer_handoff_script, launch_installer)
from document_studio.storage import Settings, SettingsError, atomic_json, backup_user_data

REPO = "tengrui-wang/document-studio"


def release(version="0.3.0", payload=b"synthetic-installer", preview=False, digest=True):
    tag = "v" + version
    from packaging.version import Version
    name = f"DocumentStudio-{Version(version)}-Setup.exe"
    url = f"https://github.com/{REPO}/releases/download/{tag}/{name}"
    sha = hashlib.sha256(payload).hexdigest()
    return {"tag_name": tag, "body": "更新说明：保留配置", "prerelease": preview,
            "assets": [{"name": name, "browser_download_url": url, "size": len(payload), "digest": "sha256:" + sha if digest else None},
                       {"name": name + ".sha256", "browser_download_url": url + ".sha256", "size": 100}]}


def test_version_channels_notes_and_no_token():
    def handle(request):
        assert "authorization" not in request.headers
        return httpx.Response(200, json=[release("0.4.0-beta.1", preview=True), release("0.3.0"), release("0.2.0")])
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        stable = check_update(REPO, client=client, current="0.2.0")
        assert stable["newer"] and stable["release"]["version"] == "0.3.0"
        assert "保留配置" in stable["release"]["notes"]
        preview = check_update(REPO, True, client=client, current="0.2.0")
        assert preview["release"]["version"] == "0.4.0b1"


@pytest.mark.parametrize("digest", [True, False])
def test_download_checksum_fallback_and_redirect(tmp_path, digest):
    payload = b"synthetic-installer"
    info = release_info(release(payload=payload, digest=digest), REPO)
    def handle(request):
        assert "authorization" not in request.headers
        if request.url.path.endswith(".sha256"):
            return httpx.Response(200, text=hashlib.sha256(payload).hexdigest() + "  " + info["asset"]["name"])
        if request.url.host == "github.com":
            return httpx.Response(302, headers={"location": "https://release-assets.githubusercontent.com/asset?signed=yes"})
        return httpx.Response(200, content=payload)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = download_update(info, tmp_path, lambda *a: None, Event(), client=client)
    assert Path(result["installer"]).read_bytes() == payload
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.parametrize("case", ["hash", "truncated", "redirect", "cancel", "size"])
def test_update_failure_never_changes_configuration(tmp_path, case):
    atomic_json(tmp_path / "settings.json", {"private": "untouched"})
    original = (tmp_path / "settings.json").read_bytes()
    payload = b"synthetic-installer"
    info = release_info(release(payload=payload), REPO)
    event = Event()
    if case == "cancel":
        event.set()
    def handle(request):
        if case == "redirect":
            return httpx.Response(302, headers={"location": "https://untrusted.example/install.exe"})
        content = b"x" * len(payload) if case == "hash" else payload[:-1] if case == "truncated" else payload + b"extra" if case == "size" else payload
        return httpx.Response(200, content=content)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises((ValueError, Cancelled)):
            download_update(info, tmp_path / "updates", lambda *a: None, event, client=client)
    assert (tmp_path / "settings.json").read_bytes() == original
    assert not list((tmp_path / "updates").glob("*.exe"))
    assert not list((tmp_path / "updates").glob("*.part"))


def test_launch_rechecks_hash_and_quotes_paths(tmp_path):
    target = tmp_path / "name with ' quote.exe"
    target.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="发生变化"):
        launch_installer(target, "0" * 64)
    script = installer_handoff_script(target, "0" * 64, 123, tmp_path / "error.txt")
    assert "name with '' quote.exe" in script
    assert script.index("Wait-Process") < script.index("Get-FileHash") < script.index("Start-Process")


def legacy_settings():
    return {"profiles": [{"id": "legacy-id", "name": "Legacy", "provider": "openai", "base_url": "https://example.com/v1", "models": ["my-model"]}],
            "output_dir": "D:/output", "repository": REPO, "soffice": "", "usage": {"legacy-id/my-model": {"input": 9, "output": 4}},
            "glossary": "term = 术语", "extension_field": {"keep": True}}


def test_old_settings_migrate_only_when_saved_and_backup(tmp_path):
    atomic_json(tmp_path / "settings.json", legacy_settings())
    atomic_json(tmp_path / "tasks.json", {"tasks": []})
    atomic_json(tmp_path / "checkpoints/one.json", {"translations": {"p0": "译文"}})
    original = (tmp_path / "settings.json").read_bytes()
    settings = Settings(tmp_path)
    assert settings.needs_migration
    assert (tmp_path / "settings.json").read_bytes() == original
    settings.save()
    backup = next((tmp_path / "backups").glob("before-migration-*/settings.json"))
    assert backup.read_bytes() == original
    reloaded = Settings(tmp_path)
    assert reloaded.data["profiles"][0]["id"] == "legacy-id"
    assert reloaded.data["glossary"] == "term = 术语"
    assert reloaded.data["extension_field"] == {"keep": True}
    assert reloaded.data["usage"]["legacy-id/my-model"]["input"] == 9
    assert (tmp_path / "checkpoints/one.json").exists()
    manual = backup_user_data(tmp_path)
    assert (manual / "tasks.json").read_bytes() == (tmp_path / "tasks.json").read_bytes()


@pytest.mark.parametrize("content", ['{bad', '{"profiles":null}', '{"schema_version":999}'])
def test_corrupt_or_future_settings_untouched(tmp_path, content):
    path = tmp_path / "settings.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(SettingsError):
        Settings(tmp_path)
    assert path.read_text(encoding="utf-8") == content


def test_atomic_write_failure_retains_original(tmp_path, monkeypatch):
    settings = Settings(tmp_path)
    settings.save()
    original = settings.path.read_bytes()
    settings.data["glossary"] = "new terminology"
    def fail(*args):
        raise PermissionError("injected")
    monkeypatch.setattr("document_studio.storage.os.replace", fail)
    with pytest.raises(PermissionError):
        settings.save()
    assert settings.path.read_bytes() == original
