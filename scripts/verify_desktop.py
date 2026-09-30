"""Portable real-process Qt acceptance with synthetic data and honest platform reporting.

Use verify_release.py for Windows frozen/package acceptance. This tool also supports
Linux X11 or offscreen, neither of which certifies Windows hardware behavior.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--platform", choices=("windows", "xcb", "offscreen"),
                        default="windows" if sys.platform == "win32" else "offscreen")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.label):
        parser.error("label must contain only letters, digits, underscore or hyphen")
    folder = ROOT / "work" / args.label
    folder.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(QT_QPA_PLATFORM=args.platform, LOCALAPPDATA=str(folder / "synthetic-localappdata"),
               XDG_CACHE_HOME=str(folder / "cache"))
    reports = []
    for label, scale in (("100", "1"), ("100-restart", "1"), ("125", "1.25"),
                         ("150", "1.5"), ("200", "2")):
        directory = folder / ("100" if label == "100-restart" else label)
        run_env = dict(env, QT_SCALE_FACTOR=scale)
        with (folder / f"{label}.stdout.txt").open("w") as out, (folder / f"{label}.stderr.txt").open("w") as err:
            run = subprocess.run([sys.executable, str(ROOT / "main.py"), "--smoke-test",
                                  "--data-dir", str(directory)], env=run_env, cwd=ROOT,
                                 stdout=out, stderr=err, timeout=60)
        result_path = directory / "smoke-result.json"
        result = json.loads(result_path.read_text("utf-8")) if result_path.exists() else {"status": "FAIL"}
        result.update(label=label, returncode=run.returncode)
        (folder / f"{label}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
        reports.append(result)
        if run.returncode or result["status"] != "PASS":
            break
    success = len(reports) == 5 and all(r["status"] == "PASS" and r["returncode"] == 0 for r in reports)
    summary = {"status": "PASS" if success else "FAIL", "python": sys.version,
               "platform": sys.platform, "qt_platform": args.platform, "runs": reports,
               "limitations": ["Synthetic data only", "Python sockets blocked, no physical offline test",
                               "No real IME, touchpad, multi-monitor or clean Windows machine test"]}
    (folder / "verification.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), "utf-8")
    print(f"{summary['status']}: {folder / 'verification.json'}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
