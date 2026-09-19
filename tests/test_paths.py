import sys
from pathlib import Path
import pytest
from paths import data_directory


def test_data_path_independent_of_working_directory(monkeypatch,tmp_path):
    monkeypatch.setenv("LOCALAPPDATA",str(tmp_path/"local"))
    expected = tmp_path/"local"/"Cashing"
    monkeypatch.chdir(tmp_path)
    assert data_directory() == expected
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path/"unpacked"), raising=False)
    assert data_directory() == expected


def test_override_and_missing_environment(monkeypatch,tmp_path):
    assert data_directory(str(tmp_path)) == tmp_path
    with pytest.raises(ValueError):
        data_directory("relative")
    monkeypatch.delenv("LOCALAPPDATA",raising=False)
    with pytest.raises(ValueError):
        data_directory()
