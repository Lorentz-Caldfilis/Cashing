"""Create one clearly named, manifest-checked Windows release from dist/Cashing."""
from importlib import metadata
from pathlib import Path
import hashlib
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = "Cashing-v1.0.0-windows"
SOURCE = ROOT / "dist" / "Cashing"
RELEASE = ROOT / "release"
TARGET = RELEASE / NAME / "Cashing"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    required = ["Cashing.exe", "_internal/python314.dll",
                "_internal/PySide6/plugins/platforms/qwindows.dll",
                "_internal/PySide6/translations/qtbase_zh_CN.qm"]
    for name in required:
        if not (SOURCE/name).is_file():
            raise RuntimeError(f"Missing runtime file: {name}")
    forbidden = [p for p in SOURCE.rglob("*") if p.suffix.lower() in {".db",".sqlite",".sqlite3",".log"}]
    if forbidden:
        raise RuntimeError("Release directory contains data or logs")
    if TARGET.parent.exists():
        raise FileExistsError(f"Refusing to overwrite an existing release: {TARGET.parent}")
    shutil.copytree(SOURCE, TARGET)
    # Replace any old copied documentation with the current user guide.
    shutil.copy2(ROOT/"README.md", TARGET/"README.md")
    old_report = TARGET/"VALIDATION.md"
    if old_report.exists():
        old_report.unlink()  # Only the just-created release copy, never user data.
    licenses = TARGET/"LICENSES"
    licenses.mkdir(exist_ok=True)
    notices = ["Cashing v1.0.0 third-party dependency notices",
               "The following license declarations are copied from installed package metadata.",
               "Python and Qt are bundled as separate runtime libraries; do not remove _internal.",
               ""]
    packages = ["PySide6","PySide6_Essentials","PySide6_Addons","shiboken6"]
    for name in packages:
        dist = metadata.distribution(name)
        license_text = dist.metadata.get("License-Expression") or dist.metadata.get("License") or "See supplied license files"
        notices.append(f"{dist.metadata['Name']} {dist.version}: {license_text}")
        for path in dist.files or []:
            if any(part.lower() in {"licenses","license"} for part in path.parts) or path.name.upper().startswith(("LICENSE","COPYING")):
                source = Path(dist.locate_file(path))
                if source.is_file():
                    target = licenses/name/Path(*path.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source,target)
    python_license=Path(sys.base_prefix)/"LICENSE.txt"
    if not python_license.exists():
        python_license=Path(sys.base_prefix)/"LICENSE"
    if python_license.exists():
        shutil.copy2(python_license,licenses/"Python-LICENSE.txt")
    (TARGET/"THIRD_PARTY_NOTICES.txt").write_text("\n".join(notices)+"\n",encoding="utf-8")
    (TARGET/"打开程序.txt").write_text(
        "双击 Cashing.exe。请保留整个 Cashing 文件夹和 _internal。\n"
        "无需安装 Python，start.bat 仅用于源码开发。\n"
        "账单保存于 %LOCALAPPDATA%\\Cashing\\ledger.sqlite3。\n",encoding="utf-8")
    files=sorted(p for p in TARGET.rglob("*") if p.is_file())
    manifest="".join(f"{sha256(p)}  {p.relative_to(TARGET).as_posix()}\n" for p in files)
    (TARGET/"MANIFEST.sha256").write_text(manifest,encoding="utf-8")
    archive=RELEASE/(NAME+".zip")
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as output:
        for p in sorted(TARGET.rglob("*")):
            if p.is_file():
                output.write(p,p.relative_to(TARGET.parent).as_posix())
    with zipfile.ZipFile(archive) as output:
        if output.testzip():
            raise RuntimeError("ZIP CRC verification failed")
    checksum=RELEASE/(NAME+".zip.sha256")
    checksum.write_text(f"{sha256(archive)}  {archive.name}\n",encoding="utf-8")
    print("EXE:",TARGET/"Cashing.exe")
    print("ZIP:",archive)
    print("SHA256:",sha256(archive))


if __name__ == "__main__":
    main()
