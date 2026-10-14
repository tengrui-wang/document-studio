"""Avoid PowerShell 5 native argument quoting differences in build metadata."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from packaging.version import Version
from document_studio import __version__

if "--numeric" in sys.argv:
    print(".".join(map(str, (list(Version(__version__).release) + [0, 0, 0, 0])[:4])))
else:
    print(__version__)
