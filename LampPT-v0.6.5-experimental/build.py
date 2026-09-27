#!/usr/bin/env python3
"""Build an installable ZIP with shaders at its root; Python standard library only."""
import argparse
import hashlib
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path, help='Destination ZIP path')
args = parser.parse_args()
destination = args.output.resolve()
destination.parent.mkdir(parents=True, exist_ok=True)

paths = list((root / 'shaders').rglob('*'))
paths += list(root.glob('*.md')) + list(root.glob('*.txt')) + [root/'build.py']
paths += list((root/'tests').glob('*.py')) + list((root/'tests').glob('*.fsh'))
paths += [p for p in (root/'tests'/'ptgi-evidence').rglob('*') if p.suffix in ('.json','.png','.txt')]
paths = sorted(set(p for p in paths if p.is_file() and p != destination))
assert root / 'shaders' / 'shaders.properties' in paths
with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in paths:
        archive.write(path, path.relative_to(root).as_posix())
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None, 'ZIP CRC validation failed'
    assert 'shaders/shaders.properties' in archive.namelist()
    assert not any('__pycache__' in p or p.endswith('.pyc') for p in archive.namelist())
print(destination)
print(f'{len(paths)} files; {destination.stat().st_size} bytes; ZIP CRC PASS')
print('SHA256', hashlib.sha256(destination.read_bytes()).hexdigest())
