"""Stable data paths, independent of checkout, installation and frozen extraction."""
import os
from pathlib import Path

SMOKE_SENTINEL = "Cashing isolated smoke test v2"


def data_directory(override=None):
    if override:
        path = Path(override).expanduser()
        if not path.is_absolute():
            raise ValueError("数据目录必须使用绝对路径。")
        return path.resolve()
    base = os.environ.get("LOCALAPPDATA")
    if not base or not Path(base).is_absolute():
        raise ValueError("找不到 Windows 用户数据目录 LOCALAPPDATA。")
    return Path(base) / "Cashing"


def prepare_smoke_directory(directory):
    directory = Path(directory).resolve()
    # Even an explicitly supplied path may not point at the real default ledger.
    if directory == data_directory().resolve() or (directory / "ledger.sqlite3").exists():
        raise ValueError("自动验收不能使用正式账单目录，请指定新的独立目录。")
    sentinel = directory / ".cashing-smoke-only"
    if directory.exists() and any(directory.iterdir()):
        if not sentinel.is_file() or sentinel.read_text("utf-8") != SMOKE_SENTINEL:
            raise ValueError("自动验收只能使用空目录或已标记的验收目录。")
    directory.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(SMOKE_SENTINEL, encoding="utf-8")


def prepare_runtime(directory):
    directory.mkdir(parents=True, exist_ok=True)
    os.environ["QT_API"] = "pyside6"
