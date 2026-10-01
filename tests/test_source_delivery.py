import hashlib
import json
import pytest
from scripts.package_release import collect_sources


def test_corresponding_source_delivery_is_checked_and_complete(tmp_path):
    source = tmp_path / "work/upstream-sources/library.tar.gz"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"synthetic source archive")
    inventory = tmp_path / "third_party/source_archives.json"
    inventory.parent.mkdir()
    inventory.write_text(json.dumps([{"file": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}]))
    guide = tmp_path / "docs/LIBRARY_REPLACEMENT.md"
    guide.parent.mkdir()
    guide.write_text("Synthetic replacement instructions")
    target = tmp_path / "delivery"
    target.mkdir()
    collect_sources(tmp_path, target)
    assert (target / "SOURCES/library.tar.gz").read_bytes() == source.read_bytes()
    assert (target / "SOURCES/README.md").read_bytes() == guide.read_bytes()
    source.write_bytes(b"changed")
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(RuntimeError, match="missing or changed"):
        collect_sources(tmp_path, other)
    assert not (other / "SOURCES/library.tar.gz").exists()


def test_source_inventory_prohibits_escape(tmp_path):
    inventory = tmp_path / "third_party/source_archives.json"
    inventory.parent.mkdir()
    inventory.write_text(json.dumps([{"file": "../../private.tar.gz", "sha256": "0" * 64}]))
    target = tmp_path / "delivery"
    target.mkdir()
    with pytest.raises(RuntimeError, match="Unsafe"):
        collect_sources(tmp_path, target)
