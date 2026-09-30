"""Read-only reachable Git blob audit. Reports locations/counts, never matched values.

Heuristic triage, not a secret-scanner certification or image/OCR inspection.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'private_key_header': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'github_token_shape': re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b'),
    'aws_access_key_shape': re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'home_directory_path': re.compile(rb'(?:[A-Za-z]:[\\/]+Users[\\/]+[^\s\\/"\']+|/home/[^\s/"\']+)'),
    'sqlite_file_header': re.compile(rb'\ASQLite format 3\x00'),
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def audit():
    objects = {}
    for line in git('rev-list', '--objects', '--all').decode().splitlines():
        oid, _, name = line.partition(' ')
        objects[oid] = name
    request = ''.join(oid + '\n' for oid in objects).encode()
    proc = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT, input=request, capture_output=True, check=True)
    data, offset, count, images = proc.stdout, 0, 0, 0
    findings = []
    kinds = Counter()
    for oid, path in objects.items():
        end = data.index(b'\n', offset)
        _, kind, length = data[offset:end].split()
        length = int(length)
        payload = data[end + 1:end + 1 + length]
        offset = end + length + 2
        if kind != b'blob':
            continue
        count += 1
        if payload.startswith(b'\x89PNG') or payload.startswith(b'\xff\xd8'):
            images += 1
        for label, pattern in PATTERNS.items():
            matches = len(pattern.findall(payload))
            if matches:
                kinds[label] += matches
                findings.append({'kind': label, 'blob': oid, 'path': path, 'count': matches})
    return {'head': git('rev-parse', 'HEAD').decode().strip(),
            'shallow': git('rev-parse', '--is-shallow-repository').decode().strip() == 'true',
            'reachable_blobs': count, 'image_blobs_not_ocr_checked': images,
            'counts': dict(kinds), 'findings': findings,
            'limits': ['reachable local refs only', 'pattern scan is not exhaustive',
                       'Git author identities and upstream license credits are not secrets',
                       'image contents need separate visual review']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('head', 'reachable_blobs', 'counts', 'image_blobs_not_ocr_checked')}))


if __name__ == '__main__':
    main()
