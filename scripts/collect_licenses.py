"""Include installed dependency license texts and exact versions in release."""
import importlib.metadata
import json
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "build/third_party"
target.mkdir(parents=True, exist_ok=True)
records = []
python_notices = [Path(sys.base_prefix) / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE_PYTHON.txt"]
for path in python_notices:
    if path.is_file():
        destination = target / "Python" / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
for distribution in importlib.metadata.distributions():
    name = distribution.metadata["Name"]
    if name.lower() == "document-studio":
        continue
    license_files = []
    for entry in distribution.files or []:
        if any(word in Path(str(entry)).name.lower() for word in ("license", "copying", "notice", "copyright")):
            path = Path(distribution.locate_file(entry))
            if path.is_file():
                destination = target / name / str(entry).replace("../", "").replace("..\\", "")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, destination)
                license_files.append(str(destination.relative_to(target)))
    records.append({"name": name, "version": distribution.version,
                    "license": distribution.metadata.get("License-Expression") or distribution.metadata.get("License", "See license files"),
                    "files": license_files})
(target / "DEPENDENCIES.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Collected license metadata for {len(records)} installed distributions")
