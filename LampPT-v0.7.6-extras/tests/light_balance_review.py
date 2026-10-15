"""GPU source-radiance regression, plus reference-calibrated held torches."""
import json
from pathlib import Path
import numpy as np
import gl_runtime as rt
from world_runtime import fragment
p=fragment(Path(__file__).with_name('source_probe.fsh'))
def source(id,texel=(1.,1.,1.),native=0):
 return rt.draw(p,{},1,1,full_precision=(0,),value_overrides={'sourceId':float(id),'sourceNative':float(native),'sourceColor':texel})[1][0][0,0,:3]
Y=np.array([.2126,.7152,.0722]);result={}
ids={'normal_torch':10200,'soul_torch':10312,'redstone_torch':10313,'copper_torch':10300,'copper_lantern':10311}
for value in [.25,.55,.7,.8,1.]:
 ref=source(10200,(value,)*3)@Y;group={}
 for name,id in ids.items():
  rgb=source(id,(value,)*3,native=7 if 'redstone' in name else 14)
  luma=rgb@Y
  assert np.isfinite(rgb).all() and np.isclose(luma,ref,rtol=1e-5,atol=1e-5),(name,value,luma,ref)
  group[name]={'rgb':rgb.tolist(),'luminance':float(luma)}
 result[str(value)]=group
# Every copper oxidation/wax state must resolve once into the dedicated group.
props=(rt.ROOT/'block.properties').read_text()
line=next(x for x in props.splitlines() if x.startswith('block.10311='))
assert len(line.split('=',1)[1].split())==8
assert 'minecraft:soul_lantern' in next(x for x in props.splitlines() if x.startswith('block.10201='))
assert 'minecraft:lantern' in next(x for x in props.splitlines() if x.startswith('block.10200='))
# Emitters are additive: equality is per source, not a global scene clamp.
assert source(10313)[0]>source(10313)[1]*2
assert source(10300)[1]>source(10300)[0]*2
out=Path(__file__).parent/'ptgi-evidence'
(out/'v075-light-balance.json').write_text(json.dumps({'passed':True,'scope':'Equal shader radiance luminance for matched source textures/geometry; not a Minecraft exposure/FPS test.','samples':result},indent=2)+'\n')
print('PASS 25 source/texture cases; 8 copper lantern mappings; reference lantern IDs preserved')
