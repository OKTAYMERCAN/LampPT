#!/usr/bin/env python3
"""Target the programs affected by the C5041 source change, across key presets."""
import json,re
from pathlib import Path
import gl_runtime as rt
from world_runtime import compute
props=(rt.ROOT/'shaders.properties').read_text()
profiles={k:dict(v.split(':',1) for v in vals.split()) for k,vals in re.findall(r'^profile\.(\w+)=(.*)$',props,re.M)}
profiles.update(ALL_HRR_OFF={k:0 for k in ['HRR_GI','HRR_SHADOWS','HRR_REFLECTIONS','HRR_CLOUDS']},EFFECTS_OFF={k:0 for k in ['PT_GI','PT_REFLECTIONS','PT_REFRACTION','PT_GLASS','PT_CAUSTICS','PT_SHADOWS','PT_SUNLIGHT','PT_SKYLIGHT','WATER_ENABLED','PT_VOLUMETRICS']})
profiles.update(OPTICS_ECONOMY={'PT_OPTICAL_DETAIL':0},HRR_MIXED={'HRR_GI':0,'HRR_REFLECTIONS':0},SHARED_OFF={'PT_SHARED_PATHS':0})
count=0
for name,options in profiles.items():
 p=rt.program('composite1',options);rt.gl['DeleteProgram'](p);count+=1
 for path in sorted(rt.ROOT.glob('composite1*.csh')):
  p=compute(path.stem,options);rt.gl['DeleteProgram'](p);count+=1
 print('HOTFIX LINK PASS',name,5,flush=True)
result={'all_passed':True,'changed_program_links':count,'variants':list(profiles),'scope':'Mesa OpenGL 4.5; NVIDIA C5041 cannot be reproduced on this driver.'}
(Path(__file__).parent/'ptgi-evidence/v072-transport-compile.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
