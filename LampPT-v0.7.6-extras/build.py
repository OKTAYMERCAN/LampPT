#!/usr/bin/env python3
"""Build separate installable runtime and development extras archives.

Edit release.json for every release; the version tooltip and visible changelog
are generated from that metadata. Extract both archives into one directory to
recreate the development tree. The supplied LICENSE.txt is copied unchanged.
"""
import argparse,hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('output',type=Path,help='Runtime ZIP destination')
parser.add_argument('--extras',type=Path,required=True,help='Development extras ZIP destination')
args=parser.parse_args()
release=json.loads((root/'release.json').read_text())
assert len(release['changes'])==3
# Single-source version/changelog metadata prevents stale About information.
for p in (root/'shaders/lang').glob('*.lang'):
 values={'screen.ABOUT_VERSION':'Version: '+release['version']+' experimental',
         'screen.ABOUT_VERSION.comment':release['version']+': '+release['changelog']}
 values.update({f'screen.CHANGE_{i+1}':v for i,v in enumerate(release['changes'])})
 lines=p.read_text().splitlines();seen=set()
 for i,line in enumerate(lines):
  key=line.split('=',1)[0]
  if key in values:lines[i]=key+'='+values[key];seen.add(key)
 lines.extend(k+'='+v for k,v in values.items() if k not in seen)
 p.write_text('\n'.join(lines)+'\n')
runtime=sorted(p for p in (root/'shaders').rglob('*') if p.is_file())+[root/'LICENSE.txt']
extras=list(root.glob('*.md'))+list(root.glob('*.txt'))+[root/'build.py',root/'release.json']
extras+=list((root/'tests').glob('*.py'))+list((root/'tests').glob('*.fsh'))
extras+=[p for p in (root/'tests/ptgi-evidence').rglob('*') if p.suffix in ('.json','.png','.txt')]
for destination,paths,kind in [(args.output,runtime,'runtime'),(args.extras,sorted(set(extras)),'extras')]:
 destination=destination.resolve();destination.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in paths:z.write(p,p.relative_to(root).as_posix())
 with zipfile.ZipFile(destination) as z:
  assert z.testzip() is None
  names=z.namelist()
  assert all('__pycache__' not in n and not n.endswith('.pyc') for n in names)
  if kind=='runtime':
   assert all(n.startswith('shaders/') or n=='LICENSE.txt' for n in names)
   assert 'shaders/shaders.properties' in names
  else:assert not any(n.startswith('shaders/') for n in names)
  assert z.read('LICENSE.txt')==(root/'LICENSE.txt').read_bytes()
 print(json.dumps({'kind':kind,'path':str(destination),'files':len(names),'bytes':destination.stat().st_size,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'crc':'PASS'}))
