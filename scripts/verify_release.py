"""Run real Windows source/frozen GUI processes without touching a real ledger."""
import argparse
from contextlib import closing
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(install):
    expected = {}
    for line in (install / 'MANIFEST.sha256').read_text('utf-8').splitlines():
        hash_value, name = line.split('  ', 1)
        path = install / name
        if (not re.fullmatch(r'[0-9a-f]{64}', hash_value) or name in expected
                or not path.resolve().is_relative_to(install.resolve())
                or path.is_symlink() or Path(name).is_absolute()):
            raise ValueError('Unsafe or duplicate manifest entry')
        expected[name] = hash_value
    actual = {p.relative_to(install).as_posix() for p in install.rglob('*') if p.is_file()}
    if actual != set(expected) | {'MANIFEST.sha256'}:
        raise ValueError('Installation file set differs from manifest')
    for name, hash_value in expected.items():
        if digest(install / name) != hash_value:
            raise ValueError(f'Installation hash mismatch: {name}')
    return expected


def environment():
    env=os.environ.copy()
    env.update(TEMP=str(ROOT/"work"),TMP=str(ROOT/"work"),PYTHONUTF8="1",
               PATH=os.environ["SystemRoot"]+"\\System32;"+os.environ["SystemRoot"],
               QT_QPA_PLATFORM="windows")
    for key in ("PYTHONPATH","PYTHONHOME","QT_SCALE_FACTOR","QT_PLUGIN_PATH","QT_QPA_PLATFORM_PLUGIN_PATH"):
        env.pop(key,None)
    return env


def run_smoke(command,directory,scale="1",clipboard_mode="system"):
    env=environment()
    env["QT_SCALE_FACTOR"]=scale
    env["CASHING_SMOKE_CLIPBOARD_MODE"]=clipboard_mode
    directory.parent.mkdir(parents=True,exist_ok=True)
    stdout=directory.parent/(directory.name+".stdout.log")
    stderr=directory.parent/(directory.name+".stderr.log")
    with stdout.open("wb") as out,stderr.open("wb") as err:
        result=subprocess.run([*command,"--data-dir",str(directory),"--smoke-test"],
                              cwd=ROOT/"work",env=env,stdout=out,stderr=err,timeout=45,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(f"GUI failed ({result.returncode}); inspect {stderr}")
    payload=json.loads((directory/"smoke-result.json").read_text("utf-8"))
    assert payload["status"]=="PASS",payload
    assert not stderr.read_bytes(),f"Unexpected startup warnings: {stderr}"
    return payload


def close_window(process):
    user=ctypes.WinDLL("user32",use_last_error=True)
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    matched=[]
    @callback
    def visit(hwnd,_):
        pid=wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        title=ctypes.create_unicode_buffer(512)
        user.GetWindowTextW(hwnd,title,len(title))
        if pid.value==process.pid and "Cashing" in title.value:
            matched.append(title.value)
            user.PostMessageW(hwnd,0x0010,0,0)
        return True
    user.EnumWindows(visit,0)
    assert matched,"No Cashing main window"
    assert process.wait(timeout=10)==0


def default_path(exe,folder):
    folder.mkdir(parents=True,exist_ok=True)
    env=environment()
    env["LOCALAPPDATA"]=str(folder)
    db=folder/"Cashing"/"ledger.sqlite3"
    assert not db.exists(),"Use a new verification directory"
    for index in range(2):
        with (folder/f"default-{index}.stdout.log").open("wb") as out, (folder/f"default-{index}.stderr.log").open("wb") as err:
            startup=subprocess.STARTUPINFO()
            startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow=0
            process=subprocess.Popen([str(exe)],cwd=ROOT/"work",env=env,stdout=out,stderr=err,startupinfo=startup)
            try:
                time.sleep(3)
                assert process.poll() is None and db.is_file(),"Default startup failed"
                close_window(process)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
        assert not (folder/f"default-{index}.stderr.log").read_bytes()
        with closing(sqlite3.connect(db)) as con,con:
            assert con.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
            if index==0:
                assert con.execute("SELECT COUNT(*) FROM records").fetchone()[0]==0
                con.execute("INSERT INTO records (amount_cents,datetime,category,description,created_at,updated_at,"
                            "category_by_user) VALUES(4321,'2030-01-01 00:00','工具','isolated validation','','',1)")
            else:
                assert con.execute("SELECT amount_cents FROM records").fetchone()[0]==4321
    return {"status":"PASS","restart_preserves_data":True,"default_path":str(db)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--phase",choices=["source","frozen"],required=True)
    parser.add_argument("--install",type=Path)
    parser.add_argument("--label",default="release-verification")
    parser.add_argument("--clipboard-mode",choices=["system","parser"],default="system",
                        help="parser is limited verification for hosts without system clipboard permission")
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', args.label):
        parser.error('--label must be a simple directory name')
    work=ROOT/"work"/args.label
    work.mkdir(parents=True,exist_ok=False)
    results={"phase":args.phase,"clipboard_mode":args.clipboard_mode,"runs":[]}
    if args.phase=="source":
        command=[str(ROOT/".venv/Scripts/python.exe"),str(ROOT/"main.py")]
    else:
        if args.install is None:
            parser.error("--install is required")
        install=args.install.resolve()
        if not install.is_relative_to(ROOT):
            parser.error("Verification installation must be inside this project")
        command=[str(install/"Cashing.exe")]
        expected=verify_manifest(install)
        results["manifest_files"]=len(expected)
    for index in range(2):
        result=run_smoke(command,work/"中文 用户 带空格"/"smoke",clipboard_mode=args.clipboard_mode)
        if index==1:
            assert "previous_process_persistence" in result["checks"]
        results["runs"].append(result)
    for scale in ("1.25","1.5","2"):
        results["runs"].append(run_smoke(command,work/("scale-"+scale),scale, args.clipboard_mode))
    if args.phase=="frozen":
        results["default_mode"]=default_path(Path(command[0]),work/"本地 用户 AppData")
        assert verify_manifest(install)==expected, 'Manifest changed during execution'
        forbidden=[p for p in install.rglob("*") if p.suffix.lower() in {".db",".sqlite",".sqlite3",".log"}]
        assert not forbidden,forbidden
        results["install_unchanged"]=True
    results["status"]="PASS"
    (work/"verification.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":"PASS","phase":args.phase,"gui_processes":len(results["runs"]),
                      "report":str(work/"verification.json")},ensure_ascii=False))


if __name__=="__main__":
    main()
