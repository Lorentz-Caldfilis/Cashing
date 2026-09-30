"""Build a local Windows candidate; never overwrite an existing delivery.

No upload or publication. All inputs must be synthetic/runtime files. Package
identity and license provenance are included for reviewers, not legal approval.
"""
import argparse
from importlib import metadata
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def check_runtime(source):
    if source.is_symlink() or (hasattr(source, 'is_junction') and source.is_junction()):
        raise RuntimeError('Runtime root must not be a filesystem link')
    required = ['Cashing.exe', f'_internal/python{sys.version_info.major}{sys.version_info.minor}.dll',
                '_internal/PySide6/plugins/platforms/qwindows.dll',
                '_internal/PySide6/translations/qtbase_zh_CN.qm']
    for name in required:
        if not (source / name).is_file():
            raise RuntimeError(f'Missing runtime file: {name}')
    for path in source.rglob('*'):
        name = path.name.lower()
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise RuntimeError('Runtime must not contain filesystem links')
        if (re.search(r'\.(db|db3|sqlite|sqlite3)(-|$)', name)
                or name.endswith(('.log', '.bak', '.pem', '.key', '.pfx', '.p12'))
                or name in {'draft.json', '.env'} or name.startswith(('.env.', 'credentials', 'secrets'))):
            raise RuntimeError('Runtime contains data, logs or private configuration')


def collect_notices(root, target):
    licenses = target / 'LICENSES'
    licenses.mkdir()
    provenance_root = root / 'third_party'
    # Reject links even when unlisted: never follow local additions into a package.
    for path in [provenance_root, *provenance_root.rglob('*')]:
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise RuntimeError('Upstream license inputs must not contain links')
    sources = json.loads((provenance_root / 'sources.json').read_text('utf-8'))
    if not sources:
        raise RuntimeError('Missing upstream license inventory')
    validated, names = [], set()
    for item in sources:
        name = item['file']
        relative = PurePosixPath(name)
        if (not name or relative.is_absolute() or relative.as_posix() != name
                or any(part in {'.', '..'} for part in relative.parts)
                or any(char in name for char in ('\\', ':', '\x00', '\n', '\r'))
                or name.casefold() in names or name.casefold() == 'sources.json'):
            raise RuntimeError('Unsafe or duplicate upstream license path')
        names.add(name.casefold())
        source = provenance_root / name
        payload = source.read_bytes()
        if not source.resolve().is_relative_to(provenance_root.resolve()) or hashlib.sha256(payload).hexdigest() != item['sha256']:
            raise RuntimeError('Upstream license inventory does not match files')
        validated.append((name, payload))
    # Copy only the checked bytes, not the directory (which may contain local notes).
    upstream = licenses / 'upstream'
    upstream.mkdir()
    for name, payload in validated:
        destination = upstream / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
    (upstream / 'sources.json').write_text(json.dumps(sources, indent=2) + '\n', encoding='utf-8')
    inventory = []
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata['Name'].lower()):
        name = dist.metadata['Name']
        inventory.append({'name': name, 'version': dist.version,
                          'license': dist.metadata.get('License-Expression') or dist.metadata.get('License'),
                          'scope': 'build environment; not all packages are bundled'})
        for path in dist.files or []:
            if any(p.lower() in {'license', 'licenses'} for p in path.parts) or path.name.upper().startswith(('LICENSE', 'COPYING')):
                source = Path(dist.locate_file(path))
                if source.is_file():
                    # Flatten metadata paths; never permit a wheel ../ path to escape LICENSES.
                    relative = Path(*[part for part in path.parts if part not in {'.', '..'}])
                    destination = licenses / name / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
    python_license = next((Path(sys.base_prefix) / name for name in ('LICENSE.txt', 'LICENSE')
                           if (Path(sys.base_prefix) / name).is_file()), None)
    if python_license is None:
        raise RuntimeError('Python license not found; candidate not packaged')
    shutil.copy2(python_license, licenses / 'Python-LICENSE.txt')
    if not any((licenses / 'pyinstaller').rglob('COPYING*')):
        # importlib metadata normally spells this distribution pyinstaller.
        if not any(p.name.upper().startswith('COPYING') for p in licenses.rglob('*') if 'pyinstaller' in str(p).lower()):
            raise RuntimeError('PyInstaller license/bootloader exception not found')
    (target / 'DEPENDENCIES.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copy2(root / 'docs/THIRD_PARTY.md', target / 'THIRD_PARTY.md')


def build_package(root, name, commit):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', name):
        raise ValueError('Package name must be a single safe filename')
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('A full source commit SHA is required')
    source, release = root / 'dist/Cashing', root / 'release'
    check_runtime(source)
    build_source = json.loads((source / 'BUILD_SOURCE.json').read_text('utf-8-sig'))
    if build_source.get('source_commit') != commit or build_source.get('tracked_changes') is not False:
        raise RuntimeError('Runtime was not built from this clean source commit; rebuild first')
    release.mkdir(exist_ok=True)
    bundle, archive, checksum = release / name, release / (name + '.zip'), release / (name + '.zip.sha256')
    for path in (bundle, archive, checksum):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f'Refusing to overwrite: {path.name}')
    created = []
    try:
        with tempfile.TemporaryDirectory(prefix='.cashing-package-', dir=release) as temporary:
            stage = Path(temporary)
            target = stage / 'Cashing'
            shutil.copytree(source, target)
            # A standalone guide has no broken repository-relative links.
            shutil.copy2(root / 'docs/USER_GUIDE.md', target / 'README.md')
            collect_notices(root, target)
            (target / 'BUILD_INFO.json').write_text(json.dumps({
                'source_commit': commit, 'package': name, 'python': sys.version,
                'pyside6': metadata.version('PySide6'), 'candidate_only': True,
                'source_license': 'No public source license granted by this candidate',
            }, indent=2) + '\n', encoding='utf-8')
            check_runtime(target)  # Includes collected notices and every other staged input.
            files = sorted(p for p in target.rglob('*') if p.is_file() and p.name != 'MANIFEST.sha256')
            (target / 'MANIFEST.sha256').write_text(''.join(
                f'{sha256(p)}  {p.relative_to(target).as_posix()}\n' for p in files), encoding='utf-8')
            stage_zip = stage / 'candidate.zip'
            with zipfile.ZipFile(stage_zip, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as output:
                for path in sorted(target.rglob('*')):
                    if path.is_file():
                        output.write(path, path.relative_to(stage).as_posix())
            with zipfile.ZipFile(stage_zip) as output:
                if output.testzip():
                    raise RuntimeError('ZIP CRC verification failed')
            stage_checksum = stage / 'checksum.txt'
            stage_checksum.write_text(f'{sha256(stage_zip)}  {archive.name}\n', encoding='utf-8')
            # Reserve the directory and exclusively publish files on the same filesystem.
            bundle.mkdir()
            created.append(bundle)
            target.rename(bundle / 'Cashing')
            os.link(stage_zip, archive)
            created.append(archive)
            os.link(stage_checksum, checksum)
            created.append(checksum)
    except BaseException:
        for path in reversed(created):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
        raise
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', help='Candidate name; defaults to the exact commit prefix')
    args = parser.parse_args()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if subprocess.run(['git', 'diff', '--quiet', 'HEAD'], cwd=ROOT).returncode:
        parser.error('Commit tracked source changes before packaging')
    archive = build_package(ROOT, args.name or f'Cashing-candidate-{commit[:12]}-windows', commit)
    print(json.dumps({'archive': str(archive), 'sha256': sha256(archive), 'source_commit': commit}))


if __name__ == '__main__':
    main()
