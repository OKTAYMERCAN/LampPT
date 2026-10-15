"""Closest ray-hit PBR sampling and disabled-option regression."""
from pathlib import Path
import json
import numpy as np
import gl_runtime as rt
from world_runtime import WorldGPU,fragment
from ptgi_runtime import box
out=Path(__file__).parent/'ptgi-evidence'
w=WorldGPU(options={'GEOMETRY_BUDGET':65536})
w.voxelize_vertices(box((-1,-1,-.2),(1,1,0)))
w.normal_atlas=rt.texture(rt.constant([.8,.5,1,1],4))
w.specular_atlas=rt.texture(rt.constant([.8,.04,0,1],4))
results={}
for enabled in [0,1]:
 p=fragment(Path(__file__).with_name('ray_pbr_probe.fsh'),{'GEOMETRY_BUDGET':65536,'NORMAL_MAPS':enabled,'SPECULAR_MAPS':enabled})
 for mode in [0,1]:
  a=rt.draw(p,{},1,1,full_precision=(0,),value_overrides={'probeMode':mode})[1][0][0,0]
  results[f'{enabled}:{mode}']=a.tolist()
 assert results[f'{enabled}:0'][3]==1
assert abs(results['0:0'][0])<.001 and results['1:0'][0]>.25
assert abs(results['1:1'][0]-.04)<.001
assert abs(results['0:1'][0]-.75)<.01
(out/'v074-ray-pbr.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results),flush=True)
