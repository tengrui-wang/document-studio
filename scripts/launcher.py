"""PyInstaller entry point; freeze support must run before importing GUI code."""
import multiprocessing
import sys
from pathlib import Path

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if not getattr(sys, "frozen", False):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    if "--verify-state" in sys.argv:
        from document_studio.state_probe import probe
        report = next(arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("--state-report="))
        raise SystemExit(probe(report))
    if "--self-test" in sys.argv:
        from document_studio.selftest import run
        report = next((arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("--self-test-report=")), None)
        raise SystemExit(run(report))
    from document_studio.app import main
    main()
