#!/usr/bin/env python3
"""Production sampler: temporal variance and known 1D/2D integral means."""
import json
from pathlib import Path
import numpy as np
import gl_runtime as rt
from world_runtime import fragment
out=Path(__file__).parent/'ptgi-evidence';report={};truth=np.array([.5,.13,.25])
for setting in [0,1]:
    program=fragment(Path(__file__).with_suffix('.fsh'),{'PT_STRATIFIED_SAMPLING':setting})
    blocks=[]
    for block in range(4):
        samples=[]
        for frame in range(block*8,block*8+8):
            _,value=rt.draw(program,{},128,64,full_precision=(0,),value_overrides={'frameCounter':frame})
            samples.append(value[0][:,:,:3])
        blocks.append(np.mean(samples,axis=0))
    a=np.array(blocks);means=a.mean((0,1,2));mse=((a-truth)**2).mean((0,1,2))
    assert np.isfinite(a).all() and np.max(abs(means-truth))<.007,(setting,means)
    report[str(setting)]={'mean':means.tolist(),'eight_frame_mse':mse.tolist()}
    rt.gl['DeleteProgram'](program)
ratio=np.array(report['1']['eight_frame_mse'])/np.array(report['0']['eight_frame_mse'])
assert np.all(ratio<.65),ratio
report.update(all_passed=True,mse_ratio=ratio.tolist(),scope=__doc__,extra_paths=0)
(out/'v076-sampling-sequence.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
