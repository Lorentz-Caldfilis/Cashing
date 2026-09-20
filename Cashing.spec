# -*- mode: python ; coding: utf-8 -*-
# Onedir avoids extraction at startup; scripts/package_release.py adds dependency license files.
from pathlib import Path
from PySide6.QtCore import QLibraryInfo

translation = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)) / "qtbase_zh_CN.qm"
datas = [(str(translation), "PySide6/translations")] if translation.exists() else []
a = Analysis(
    ["main.py"], pathex=[], binaries=[], datas=datas,
    hiddenimports=[],
    hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=["tkinter", "PyQt5", "PyQt6", "PySide2"], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Cashing",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False, version="version_info.txt")
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Cashing")
