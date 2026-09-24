"""The documented test command works on a fresh checkout, before any ignored work/ exists."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_basetemp_parents_need_not_exist(tmp_path):
    basetemp = tmp_path / "fresh checkout" / "work" / "pytest-manual"
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONUTF8="1")
    result = subprocess.run(
        [sys.executable, "-W", "error", "-m", "pytest", "tests/test_draft.py", "-q", "-p", "no:cacheprovider",
         "--basetemp", str(basetemp)],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    assert basetemp.is_dir()
