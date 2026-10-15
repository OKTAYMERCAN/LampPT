#!/usr/bin/env python3
"""Production final pass: neutral ramp, finite HDR and chroma preservation."""
import json
from pathlib import Path
import numpy as np
import gl_runtime as rt
options={'BLOOM_ENABLED':0,'DITHER':0,'VIGNETTE':0,'EXPOSURE':'1.00',
         'SATURATION':'1.00','CONTRAST':'1.0','GAMMA_ADJUST':'1.0'}
neutral=np.geomspace(.001,100,64)
colors=np.array([[.12,.25,.65],[.1,.45,.15],[.45,.08,.025],[1000,100,30],[0,0,0]])
inputs=np.concatenate([np.repeat(neutral[:,None],3,axis=1),colors])
tex=rt.texture(np.dstack([inputs[None,:,:],np.ones((1,len(inputs)))]))
results={}
for mode in [0,1,2]:
    program=rt.program('final',{**options,'TONEMAP':mode})
    _,value=rt.draw(program,{'colortex7':tex},len(inputs),1,full_precision=(0,))
    result=value[0][0,:,:3]
    assert np.isfinite(result).all() and result.min()>=0 and result.max()<=1
    linear=np.where(result<=.04045,result/12.92,((result+.055)/1.055)**2.4)
    assert np.min(np.diff(linear[:64,0]))>=-1e-6
    assert np.max(np.ptp(linear[:64],axis=1))<1e-5
    results[mode]=linear
    rt.gl['DeleteProgram'](program)
# Neutral brightness is intentionally the same fitted curve as legacy ACES.
assert np.max(abs(results[2][:64]-results[1][:64]))<1e-5
# These colors fit the display gamut and should retain their linear RGB ratios.
expected=colors[:3]/colors[:3].sum(axis=1,keepdims=True)
actual=results[2][64:67];actual/=actual.sum(axis=1,keepdims=True)
ratio_error=float(np.max(abs(actual-expected)))
assert ratio_error<1e-5,ratio_error
report={'all_passed':True,'ungamutclipped_rgb_ratio_error':ratio_error,
        'neutral_ramp_matches_legacy_fit':True,'hdr_samples_finite':True,'scope':__doc__}
(Path(__file__).parent/'ptgi-evidence/v076-display-color.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
