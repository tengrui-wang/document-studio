"""Real install/upgrade/uninstall tests, restricted to disposable GitHub Windows runners.

Uses the published v0.1.0 installer, synthetic private data and a random vault entry.
Does not run on a user's normal Windows account; writes a compact JSON report.
"""
import argparse
import hashlib
import json
import os
import subprocess
import uuid
import winreg
from dataclasses import asdict
from pathlib import Path

import httpx
from document_studio import __version__
from document_studio.jobs import Task
from document_studio.storage import Credentials, atomic_json, backup_user_data

REGISTRY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{D7474072-9006-45D3-AD1B-8457879F216A}_is1"


def execute(executable, arguments, success=True):
    flags = subprocess.CREATE_NO_WINDOW
    result = subprocess.run([str(executable), *arguments], timeout=240, creationflags=flags)
    if success and result.returncode != 0:
        raise RuntimeError(f"{Path(executable).name} failed with exit code {result.returncode}")
    if not success and result.returncode == 0:
        raise RuntimeError("Injected failure unexpectedly succeeded")
    return result.returncode


def installed_info():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY) as key:
            return {name: winreg.QueryValueEx(key, name)[0] for name in ("DisplayVersion", "InstallLocation", "UninstallString")}
    except FileNotFoundError:
        return None


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_OS") != "Windows":
        raise RuntimeError("Run only on the disposable GitHub Windows runner; local installation is intentionally disabled.")
    parser = argparse.ArgumentParser()
    parser.add_argument("--installer", required=True)
    parser.add_argument("--compiler", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    test_root = root / "build/lifecycle"
    test_root.mkdir(parents=True, exist_ok=True)
    app_dir = test_root / "installed-program"
    user_data = Path(os.environ["LOCALAPPDATA"]) / "DocumentStudio"
    if installed_info() or (user_data.exists() and any(user_data.iterdir())):
        raise RuntimeError("Existing installation or personal data detected; refusing to alter it.")
    installer = Path(args.installer).resolve()
    quiet = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/NOICONS", "/TASKS="]
    report = {"version": __version__, "passed": [], "limitations": ["Disposable Windows Server 2022 runner; Windows 10/11 user-machine acceptance and power-loss rollback unverified."]}
    credential = Credentials()
    identifier = "lifecycle-" + uuid.uuid4().hex

    def record(name):
        report["passed"].append(name)
        print("PASS", name, flush=True)

    def seed_data():
        credential.set(identifier, "DocumentStudio-lifecycle-synthetic")
        atomic_json(user_data / "settings.json", {"profiles": [{"id": identifier, "name": "synthetic profile", "provider": "openai",
            "base_url": "https://example.com/v1", "models": ["synthetic-model"]}], "output_dir": str(test_root / "outputs"),
            "repository": "tengrui-wang/document-studio", "soffice": "", "usage": {identifier + "/synthetic-model": {"input": 7, "output": 3}},
            "glossary": "machine learning = 机器学习", "lifecycle_test_profile": identifier})
        task = Task("synthetic history", "word_format", [], str(test_root / "outputs"), {"glossary": "term = 术语"}, status="完成", progress=100)
        atomic_json(user_data / "tasks.json", {"tasks": [asdict(task)]})
        atomic_json(user_data / "checkpoints/synthetic.json", {"translations": {"p0": "合成断点译文"}})

    def hashes():
        files = [user_data / "settings.json", user_data / "tasks.json", user_data / "checkpoints/synthetic.json"]
        return {str(file.relative_to(user_data)): hashlib.sha256(file.read_bytes()).hexdigest() for file in files}

    def retained(expected):
        assert hashes() == expected, "Personal state changed unexpectedly"
        assert credential.get(identifier) == "DocumentStudio-lifecycle-synthetic", "Credential was removed or changed"

    try:
        # Fresh new install on an empty profile, standard Installed Apps registry entry.
        execute(installer, quiet + [f"/DIR={app_dir}", f"/LOG={test_root / 'fresh.log'}"])
        assert installed_info()["DisplayVersion"] == __version__
        assert (app_dir / "DocumentStudio.exe").is_file()
        record("fresh_new_install_and_registered_uninstaller")
        seed_data()
        original = hashes()
        execute(app_dir / "unins000.exe", ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
        retained(original)
        assert installed_info() is None and not (app_dir / "DocumentStudio.exe").exists()
        record("normal_uninstall_preserves_settings_models_glossary_history_checkpoints_credentials")

        # Download exactly the old released installer and verify its published SHA256.
        old_name = "DocumentStudio-0.1.0-Setup.exe"
        old_installer = test_root / old_name
        base = "https://github.com/tengrui-wang/document-studio/releases/download/v0.1.0/"
        with httpx.Client(timeout=90, follow_redirects=True) as client:
            check = client.get(base + old_name + ".sha256")
            check.raise_for_status()
            with client.stream("GET", base + old_name) as response:
                response.raise_for_status()
                with old_installer.open("wb") as stream:
                    for block in response.iter_bytes(1024 * 1024):
                        stream.write(block)
            assert hashlib.sha256(old_installer.read_bytes()).hexdigest() == check.text.split()[0].lower()
        execute(old_installer, quiet + [f"/DIR={app_dir}", f"/LOG={test_root / 'old.log'}"])
        assert installed_info()["DisplayVersion"] == "0.1.0"
        retained(original)
        record("real_v010_install_on_retained_data")
        backup = backup_user_data(user_data, "before-update-test")
        assert (backup / "manifest.json").is_file()
        record("upgrade_backup_verified")

        # Compile a fault-only installer OUTSIDE Release assets; missing external payload.
        execute(args.compiler, [f"/DAppVersion={__version__}", "/DLifecycleFault=1", f"/O{test_root}", "/FLifecycleFailure", str(root / "packaging/installer.iss")])
        failure_code = execute(test_root / "LifecycleFailure.exe", quiet + [f"/LOG={test_root / 'failure.log'}"], success=False)
        retained(original)
        report["injected_failure_exit"] = failure_code
        record("missing_payload_upgrade_failure_preserves_all_personal_data")
        execute(installer, quiet + [f"/DIR={user_data}", f"/LOG={test_root / 'overlap.log'}"], success=False)
        retained(original)
        record("program_data_directory_overlap_rejected")

        # No /DIR: exercise UsePreviousAppDir rather than hardcoding the new location.
        execute(installer, quiet + [f"/LOG={test_root / 'upgrade.log'}"])
        info = installed_info()
        assert Path(info["InstallLocation"]).resolve() == app_dir.resolve()
        assert info["DisplayVersion"] == __version__
        retained(original)
        execute(app_dir / "DocumentStudio.exe", ["--verify-state", f"--state-report={test_root / 'state.json'}"])
        state = json.loads((test_root / "state.json").read_text(encoding="utf-8"))
        assert state["credential_retained"] and state["model_retained"] and state["glossary_retained"] and state["tasks"] == 1
        retained(original)
        record("v010_to_new_cover_upgrade_retains_directory_state_and_native_credentials")
        execute(app_dir / "DocumentStudio.exe", ["--smoke-test"])
        retained(original)
        record("upgraded_installed_app_starts_and_leaves_existing_state_unchanged")
        execute(app_dir / "unins000.exe", ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
        retained(original)
        assert installed_info() is None
        record("upgraded_app_uninstall_preserves_personal_data_and_backup")
        report["success"] = True
    except Exception as exc:
        report["success"], report["error"] = False, str(exc)
        raise
    finally:
        # Delete only this random synthetic test credential, never user credentials.
        credential.delete(identifier)
        (root / "release/INSTALLER-VERIFICATION.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
