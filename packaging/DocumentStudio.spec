# PyInstaller one-folder build. Qt DLLs remain separate for LGPL replacement.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
from packaging.version import Version
import sys

root = Path(SPECPATH).parent
sys.path.insert(0, str(root / 'src'))
from document_studio import __version__
release = Version(__version__).release
numeric = tuple((list(release) + [0, 0, 0, 0])[:4])
version_resource = VSVersionInfo(ffi=FixedFileInfo(filevers=numeric, prodvers=numeric, mask=0x3f,
    flags=2 if Version(__version__).is_prerelease else 0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable('040904B0', [StringStruct('FileDescription', 'Document Studio'),
        StringStruct('FileVersion', '.'.join(map(str, numeric))), StringStruct('ProductVersion', __version__),
        StringStruct('ProductName', 'Document Studio')])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])
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
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False, version=version_resource)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='DocumentStudio')
