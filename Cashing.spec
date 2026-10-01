# -*- mode: python ; coding: utf-8 -*-
# Onedir avoids extraction at startup; scripts/package_release.py adds dependency license files.
from pathlib import Path
from PySide6.QtCore import QLibraryInfo

translation = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)) / "qtbase_zh_CN.qm"
datas = [(str(translation), "PySide6/translations")] if translation.exists() else []
datas += [("assets/cashing-icon.ico", "assets"), ("assets/cashing-icon.png", "assets")]
a = Analysis(
    ["main.py"], pathex=[], binaries=[], datas=datas,
    hiddenimports=[],
    hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=["tkinter", "PyQt5", "PyQt6", "PySide2",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf", "PySide6.QtSvg"], noarchive=False,
)
# Keep only the plugins used by this Widgets application; do not ship optional
# VirtualKeyboard/QML/PDF plugins and their unused runtime dependencies.
allowed_plugins = {"qwindows.dll", "qmodernwindowsstyle.dll", "qjpeg.dll", "qgif.dll", "qico.dll", "qwebp.dll"}
allowed_qt = {"Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll", "Qt6Network.dll", "Qt6OpenGL.dll", "Qt6Test.dll"}
a.binaries = [entry for entry in a.binaries
    if ("/plugins/" not in entry[0].replace("\\", "/") or Path(entry[0]).name in allowed_plugins)
    and (not Path(entry[0]).name.startswith("Qt6") or Path(entry[0]).name in allowed_qt)]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Cashing",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False, version="version_info.txt", icon="assets/cashing-icon.ico")
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Cashing")
