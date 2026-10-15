#!/usr/bin/env python3
"""Link changed reconstruction branches and preserve the NVIDIA fix contract."""
import json,re
from pathlib import Path
import gl_runtime as rt
props=(rt.ROOT/'shaders.properties').read_text()
variants={k:dict(v.split(':',1) for v in vals.split()) for k,vals in re.findall(r'^profile\.(\w+)=(.*)$',props,re.M)}
variants.update(OPTICS_ECONOMY={'PT_OPTICAL_DETAIL':0},OFF={'PT_TEMPORAL':0,'PT_DENOISE':0,'PT_OUTLIER_FILTER':0},
                NO_SPARSE={'PT_OUTLIER_FILTER':0}, RAW={'DEBUG_VIEW':9},
                PBR={'NORMAL_MAPS':1,'POM':1}, HRR_MIXED={'HRR_GI':0,'HRR_REFLECTIONS':0})
count=0
for name,options in variants.items():
    for program in ['composite2','composite3','composite4','composite5','composite6','composite7']:
        p=rt.program(program,options);rt.gl['DeleteProgram'](p);count+=1
    print('RECONSTRUCTION LINK PASS',name,flush=True)
trace=(rt.ROOT/'lib/scene/trace.glsl').read_text()
merge=(rt.ROOT/'lib/ptgi/merge.glsl').read_text()
assert not re.search(r'\bstack\s*\[',trace)
assert len(re.findall(r'ptIntegrateComponent\s*\(',merge))==1
report={'all_passed':True,'program_links':count,'variants':list(variants),'no_private_bvh_stack':True,
        'one_merge_integrator_call':True,'scope':'Mesa OpenGL 4.5; not the NVIDIA compiler or Minecraft/Iris'}
(Path(__file__).parent/'ptgi-evidence/v076-reconstruction-compile.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
