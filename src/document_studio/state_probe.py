"""Read-only state probe used on the disposable Windows installer test runner."""
import json
from .storage import Settings, Credentials
from . import __version__


def probe(report_path):
    settings = Settings()
    profiles = settings.data["profiles"]
    # Test-only fixture has a random identifier; never put credential values in reports.
    test_id = settings.data.get("lifecycle_test_profile")
    if not test_id or not any(p["id"] == test_id for p in profiles):
        raise ValueError("Lifecycle test fixture is missing.")
    credential_ok = Credentials().get(test_id) == "DocumentStudio-lifecycle-synthetic"
    tasks = json.loads((settings.root / "tasks.json").read_text(encoding="utf-8"))["tasks"]
    result = {"version": __version__, "profiles": len(profiles), "model_retained": profiles[0]["models"] == ["synthetic-model"],
              "glossary_retained": settings.data["glossary"] == "machine learning = 机器学习", "tasks": len(tasks),
              "credential_retained": credential_ok, "schema": settings.data["schema_version"]}
    from pathlib import Path
    Path(report_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if credential_ok and result["model_retained"] and result["glossary_retained"] else 1
