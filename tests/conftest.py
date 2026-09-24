import os
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
os.environ["QT_API"] = "pyside6"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from database import Database


def pytest_configure(config):
    """pytest creates --basetemp itself but not its parents, so the documented
    `--basetemp .\\work\\pytest-manual` failed every tmp_path test on a checkout
    without the ignored work/ directory. Create the parent here instead."""
    basetemp = config.option.basetemp
    if basetemp:
        Path(os.path.abspath(basetemp)).parent.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def database(tmp_path):
    db = Database(tmp_path / "test.sqlite3")
    db.initialize_database()
    return db
