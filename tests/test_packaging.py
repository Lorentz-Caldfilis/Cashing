"""Exercise publication safety with a fake runtime, never a real user ledger."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
import pytest
from scripts import package_release as package
from scripts import build_provenance as provenance

SHA = 'a' * 40
NAME = 'Cashing-test-candidate'
REAL_COLLECT_NOTICES = package.collect_notices


@pytest.fixture
def root(tmp_path, monkeypatch):
    for name in ['Cashing.exe', f'_internal/python{sys.version_info.major}{sys.version_info.minor}.dll',
                 '_internal/PySide6/plugins/platforms/qwindows.dll',
                 '_internal/PySide6/translations/qtbase_zh_CN.qm']:
        path = tmp_path / 'dist/Cashing' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'synthetic runtime')
    (tmp_path / 'docs').mkdir()
    provenance.write_record(tmp_path / 'dist/Cashing', SHA, False, provenance.environment_snapshot())
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


@pytest.fixture
def notice_root(root, monkeypatch):
    """Real collector, real installed metadata; only Python license location is synthetic."""
    monkeypatch.setattr(package, 'collect_notices', REAL_COLLECT_NOTICES)
    (root / 'docs/THIRD_PARTY.md').write_text('Synthetic notice fixture')
    upstream = root / 'third_party'
    upstream.mkdir()
    license_file = upstream / 'LICENSE.txt'
    license_file.write_text('Synthetic upstream license fixture')
    (upstream / 'sources.json').write_text(json.dumps([{
        'file': 'LICENSE.txt', 'sha256': package.sha256(license_file),
        'source': 'https://example.invalid/synthetic-license'}]))
    python = root / 'synthetic-python'
    python.mkdir()
    (python / 'LICENSE').write_text('Synthetic Python license fixture')
    monkeypatch.setattr(package.sys, 'base_prefix', str(python))
    provenance.write_record(root / 'dist/Cashing', SHA, False, provenance.environment_snapshot())
    return root


def test_real_collector_excludes_unlisted_private_files(notice_root):
    root = notice_root
    (root / 'third_party/draft.json').write_text('synthetic private draft')
    (root / 'third_party/private-notes.txt').write_text('synthetic private notes')
    archive = package.build_package(root, NAME, SHA)
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        assert not any('draft.json' in n or 'private-notes.txt' in n for n in names)
        assert 'Cashing/LICENSES/upstream/LICENSE.txt' in names
        assert 'Cashing/LICENSES/Python-LICENSE.txt' in names
        assert any('pyinstaller' in n.lower() and 'COPYING' in n for n in names)


@pytest.mark.parametrize('path', ['../outside.txt', '/absolute.txt', 'C:/absolute.txt', 'a\\b.txt', 'a/../b.txt'])
def test_real_collector_rejects_unsafe_allowlist_paths(notice_root, path):
    inventory = notice_root / 'third_party/sources.json'
    inventory.write_text(json.dumps([{'file': path, 'sha256': '0' * 64}]))
    with pytest.raises(RuntimeError, match='Unsafe'):
        package.build_package(notice_root, NAME, SHA)
    assert not list((notice_root / 'release').iterdir())


def test_real_collector_rejects_casefold_duplicates(notice_root):
    inventory = notice_root / 'third_party/sources.json'
    item = json.loads(inventory.read_text())[0]
    inventory.write_text(json.dumps([item, dict(item, file='license.TXT')]))
    with pytest.raises(RuntimeError, match='duplicate'):
        package.build_package(notice_root, NAME, SHA)


def test_final_scan_rejects_private_data_even_if_allowlisted(notice_root):
    upstream = notice_root / 'third_party'
    draft = upstream / 'draft.json'
    draft.write_text('synthetic private data')
    (upstream / 'sources.json').write_text(json.dumps([
        {'file': 'draft.json', 'sha256': package.sha256(draft)}]))
    with pytest.raises(RuntimeError, match='data, logs'):
        package.build_package(notice_root, NAME, SHA)
    assert not list((notice_root / 'release').iterdir())


@pytest.mark.parametrize('listed', [True, False])
def test_real_collector_rejects_links(notice_root, listed):
    root = notice_root
    link = root / 'third_party' / ('LICENSE.txt' if listed else 'unlisted.txt')
    if listed:
        link.unlink()
    outside = root / 'outside.txt'
    outside.write_text('synthetic outside data')
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip('Host does not permit creation of filesystem links')
    with pytest.raises(RuntimeError, match='links'):
        package.build_package(root, NAME, SHA)
    assert not list((root / 'release').iterdir())


@pytest.mark.parametrize('change', ['python', 'dependency_version', 'license_digest'])
def test_changed_build_environment_is_rejected_before_packaging(root, change):
    marker = root / 'dist/Cashing/BUILD_SOURCE.json'
    record = json.loads(marker.read_text())
    environment = record['build_environment']
    if change == 'python':
        environment['python'] = 'synthetic other interpreter'
    elif change == 'dependency_version':
        next(d for d in environment['distributions'] if d['name'].lower() == 'pyside6')['version'] = '0.0.synthetic'
    else:
        environment['python_license_sha256'] = 'synthetic old license digest'
    marker.write_text(json.dumps(record))
    with pytest.raises(RuntimeError, match='environment differs'):
        package.build_package(root, NAME, SHA)
    assert not (root / 'release').exists()


@pytest.mark.parametrize('change', ['modified', 'extra', 'missing'])
def test_changed_runtime_cannot_reuse_build_provenance(root, change):
    runtime = root / 'dist/Cashing'
    if change == 'modified':
        (runtime / 'Cashing.exe').write_bytes(b'synthetic replacement')
    elif change == 'extra':
        (runtime / 'unexpected.dll').write_bytes(b'synthetic addition')
    else:
        record = json.loads((runtime / 'BUILD_SOURCE.json').read_text())
        record['runtime_files']['missing-original.dll'] = '0' * 64
        (runtime / 'BUILD_SOURCE.json').write_text(json.dumps(record))
    with pytest.raises(RuntimeError, match='runtime files changed'):
        package.build_package(root, NAME, SHA)
    assert not (root / 'release').exists()


def test_package_separates_build_environment_and_actual_bundled_files(root):
    archive = package.build_package(root, NAME, SHA)
    with zipfile.ZipFile(archive) as z:
        environment = json.loads(z.read('Cashing/BUILD_ENVIRONMENT.json'))
        bundled = json.loads(z.read('Cashing/BUNDLED_FILES.json'))
        assert any(d['name'].lower() == 'pytest' for d in environment['distributions'])
        assert not any('pytest' in p.lower() for p in bundled['files'])
        for name, digest in bundled['files'].items():
            assert hashlib.sha256(z.read('Cashing/' + name)).hexdigest() == digest


def test_runtime_with_old_package_metadata_is_rejected(root):
    (root / 'dist/Cashing/README.md').write_text('stale package guide')
    with pytest.raises(RuntimeError, match='old package outputs'):
        package.build_package(root, NAME, SHA)


def test_copied_runtime_is_verified_before_adding_notices(root, monkeypatch):
    real_copy = package.shutil.copytree
    def corrupt(source, target, *args, **kwargs):
        result = real_copy(source, target, *args, **kwargs)
        (Path(target) / 'Cashing.exe').write_bytes(b'synthetic copy corruption')
        return result
    monkeypatch.setattr(package.shutil, 'copytree', corrupt)
    with pytest.raises(RuntimeError, match='runtime files changed'):
        package.build_package(root, NAME, SHA)
    assert not list((root / 'release').iterdir())
