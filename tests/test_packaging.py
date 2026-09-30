"""Exercise publication safety with a fake runtime, never a real user ledger."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
import pytest
from scripts import package_release as package

SHA = 'a' * 40
NAME = 'Cashing-test-candidate'


@pytest.fixture
def root(tmp_path, monkeypatch):
    for name in ['Cashing.exe', f'_internal/python{sys.version_info.major}{sys.version_info.minor}.dll',
                 '_internal/PySide6/plugins/platforms/qwindows.dll',
                 '_internal/PySide6/translations/qtbase_zh_CN.qm']:
        path = tmp_path / 'dist/Cashing' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'synthetic runtime')
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'dist/Cashing/BUILD_SOURCE.json').write_text(json.dumps(
        {'source_commit': SHA, 'tracked_changes': False}))
    (tmp_path / 'docs/USER_GUIDE.md').write_text('Synthetic guide')
    monkeypatch.setattr(package, 'collect_notices', lambda root, target: (target / 'LICENSES').mkdir())
    return tmp_path


def test_package_identity_and_archive_manifest(root):
    archive = package.build_package(root, NAME, SHA)
    with zipfile.ZipFile(archive) as z:
        info = json.loads(z.read('Cashing/BUILD_INFO.json'))
        assert info['source_commit'] == SHA and info['candidate_only']
        manifest = z.read('Cashing/MANIFEST.sha256').decode().splitlines()
        listed = set()
        for line in manifest:
            digest, name = line.split('  ', 1)
            assert hashlib.sha256(z.read('Cashing/' + name)).hexdigest() == digest
            listed.add('Cashing/' + name)
        assert set(z.namelist()) == listed | {'Cashing/MANIFEST.sha256'}
    assert archive.with_suffix('.zip.sha256').read_text().split()[0] == package.sha256(archive)


@pytest.mark.parametrize('commit,dirty', [('b' * 40, False), (SHA, True)])
def test_stale_or_uncommitted_build_cannot_claim_current_source(root, commit, dirty):
    (root / 'dist/Cashing/BUILD_SOURCE.json').write_text(json.dumps(
        {'source_commit': commit, 'tracked_changes': dirty}))
    with pytest.raises(RuntimeError, match='rebuild first'):
        package.build_package(root, NAME, SHA)
    assert not (root / 'release').exists()


@pytest.mark.parametrize('suffix', ['', '.zip', '.zip.sha256'])
def test_existing_delivery_is_never_overwritten(root, suffix):
    release = root / 'release'
    release.mkdir()
    existing = release / (NAME + suffix)
    existing.write_bytes(b'keep existing delivery')
    with pytest.raises(FileExistsError):
        package.build_package(root, NAME, SHA)
    assert existing.read_bytes() == b'keep existing delivery'
    assert list(release.iterdir()) == [existing]


@pytest.mark.parametrize('name', ['ledger.sqlite3', 'ledger.sqlite3-wal', 'old.db-journal',
                                 'draft.json', 'cashing.log', '.env', '.env.local', 'secrets.json'])
def test_runtime_private_data_is_rejected(root, name):
    (root / 'dist/Cashing' / name).write_bytes(b'synthetic private fixture')
    with pytest.raises(RuntimeError, match='data, logs'):
        package.build_package(root, NAME, SHA)
    assert not (root / 'release').exists()


def test_failed_license_collection_leaves_no_delivery(root, monkeypatch):
    def fail(*args):
        raise RuntimeError('missing required license')
    monkeypatch.setattr(package, 'collect_notices', fail)
    with pytest.raises(RuntimeError, match='license'):
        package.build_package(root, NAME, SHA)
    assert not list((root / 'release').iterdir())


def test_failed_publication_cleans_only_its_own_outputs(root, monkeypatch):
    release = root / 'release'
    release.mkdir()
    old = release / 'older.zip'
    old.write_bytes(b'keep')
    real_link = package.os.link
    calls = 0
    def fail_second(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError('synthetic publication failure')
        real_link(source, destination)
    monkeypatch.setattr(package.os, 'link', fail_second)
    with pytest.raises(OSError):
        package.build_package(root, NAME, SHA)
    assert list(release.iterdir()) == [old]
    assert old.read_bytes() == b'keep'


def test_upstream_license_provenance_matches_repository():
    root = Path(__file__).resolve().parents[1] / 'third_party'
    sources = json.loads((root / 'sources.json').read_text())
    assert len(sources) >= 100
    for item in sources:
        assert package.sha256(root / item['file']) == item['sha256']
        assert '/blob/' in item['source']


@pytest.mark.parametrize('tamper', ['extra', 'changed', 'traversal', 'duplicate'])
def test_verifier_rejects_extra_modified_or_unsafe_package_files(root, tamper):
    from scripts.verify_release import verify_manifest
    package.build_package(root, NAME, SHA)
    install = root / 'release' / NAME / 'Cashing'
    verify_manifest(install)
    manifest = install / 'MANIFEST.sha256'
    if tamper == 'extra':
        (install / 'unexpected.txt').write_text('synthetic addition')
    elif tamper == 'changed':
        (install / 'Cashing.exe').write_bytes(b'changed')
    elif tamper == 'traversal':
        manifest.write_text('0' * 64 + '  ../../outside.txt\n')
    else:
        manifest.write_text(manifest.read_text() * 2)
    with pytest.raises(ValueError):
        verify_manifest(install)
