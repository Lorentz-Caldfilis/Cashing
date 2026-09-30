"""Bind a generated runtime to the source and environment that actually built it.

Local verification, not signed supply-chain attestation. No network or credentials.
"""
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'BUILD_SOURCE.json'


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def environment_snapshot():
    packages = []
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata['Name'].lower()):
        licenses = {}
        for entry in dist.files or []:
            if (any(p.lower() in {'license', 'licenses'} for p in entry.parts)
                    or entry.name.upper().startswith(('LICENSE', 'COPYING'))):
                path = Path(dist.locate_file(entry))
                if path.is_file():
                    licenses[str(entry)] = file_hash(path)
        packages.append({'name': dist.metadata['Name'], 'version': dist.version,
                         'metadata_sha256': hashlib.sha256((dist.read_text('METADATA') or '').encode()).hexdigest(),
                         'record_sha256': hashlib.sha256((dist.read_text('RECORD') or '').encode()).hexdigest(),
                         'license_files': licenses})
    python_license = next((Path(sys.base_prefix) / n for n in ('LICENSE.txt', 'LICENSE')
                           if (Path(sys.base_prefix) / n).is_file()), None)
    return {'python': sys.version, 'implementation': platform.python_implementation(),
            'platform': sys.platform, 'machine': platform.machine(),
            'python_license_sha256': file_hash(python_license) if python_license else None,
            'distributions': packages}


def runtime_inventory(runtime):
    result = {}
    for path in sorted(runtime.rglob('*')):
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise RuntimeError('Runtime provenance cannot follow filesystem links')
        if path.is_file() and path.relative_to(runtime).as_posix() != MARKER:
            result[path.relative_to(runtime).as_posix()] = file_hash(path)
    return result


def write_record(runtime, commit, dirty, environment):
    record = {'format_version': 2, 'source_commit': commit, 'tracked_changes': dirty,
              'build_environment': environment, 'runtime_files': runtime_inventory(runtime)}
    (runtime / MARKER).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record


def verify_record(runtime, record):
    if record.get('format_version') != 2:
        raise RuntimeError('Build provenance is missing environment data; rebuild first')
    if record.get('build_environment') != environment_snapshot():
        raise RuntimeError('Packaging environment differs from build environment; rebuild first')
    if record.get('runtime_files') != runtime_inventory(runtime):
        raise RuntimeError('Built runtime files changed; rebuild first')


def source_context():
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    diff = subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=ROOT)
    return {'source_commit': commit, 'tracked_changes': bool(diff),
            'tracked_diff_sha256': hashlib.sha256(diff).hexdigest(),
            'environment': environment_snapshot()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--begin', type=Path)
    mode.add_argument('--finish', type=Path)
    parser.add_argument('--runtime', type=Path)
    args = parser.parse_args()
    context = source_context()
    if args.begin:
        args.begin.parent.mkdir(parents=True, exist_ok=True)
        args.begin.write_text(json.dumps(context, indent=2) + '\n', encoding='utf-8')
    else:
        if args.runtime is None:
            parser.error('--runtime is required with --finish')
        before = json.loads(args.finish.read_text('utf-8'))
        if context != before:
            raise RuntimeError('Source or environment changed during build; rebuild first')
        write_record(args.runtime, context['source_commit'], context['tracked_changes'], context['environment'])


if __name__ == '__main__':
    main()
