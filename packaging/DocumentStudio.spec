# PyInstaller one-folder build. Qt DLLs remain separate for LGPL replacement.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH).parent
datas = [(str(root / 'LICENSE'), '.'), (str(root / 'README.md'), '.'),
         (str(root / 'docs'), 'docs'), (str(root / 'build/third_party'), 'third_party')]
for package in ('pdf2docx', 'pymupdf'):
    datas += collect_data_files(package)
for package in ('keyring', 'jaraco.classes', 'jaraco.functools', 'jaraco.context'):
    datas += copy_metadata(package)
a = Analysis([str(root / 'scripts/launcher.py')], pathex=[str(root / 'src')],
    binaries=[], datas=datas, hiddenimports=['keyring.backends.Windows', 'win32timezone', 'win32com.client'],
    hookspath=[], runtime_hooks=[], excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
    'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtPdf', 'PySide6.QtMultimedia',
    'tkinter', 'pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='DocumentStudio',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='DocumentStudio')
