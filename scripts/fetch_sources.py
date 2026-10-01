"""Fetch checksum-pinned LGPL corresponding source archives for redistribution."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path
import os
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def fetch(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    items = json.loads((ROOT / "third_party/source_archives.json").read_text("utf-8"))
    def obtain(item):
        destination = directory / item["file"]
        if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() == item["sha256"]:
            return destination.name
        temporary = directory / (item["file"] + ".download")
        try:
            with urllib.request.urlopen(item["url"], timeout=120) as response, temporary.open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != item["sha256"]:
                raise RuntimeError("Upstream source checksum mismatch: " + item["file"])
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination.name
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(obtain, items))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "work/upstream-sources")
    print(json.dumps({"sources": fetch(parser.parse_args().directory)}))
