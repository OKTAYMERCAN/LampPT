#!/usr/bin/env python3
"""Rare transmission samples must keep their energy during temporal filtering.

The known radiance is estimated with 15%-probability nonzero samples. A 3x3
neighborhood is often entirely black, but that is not proof that history is
stale. This was a systematic darkening case absent from the old noise fixture.
"""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
import gl_runtime as rt
from pipeline_routing import Pipeline
from buffer_encoding import normal24
p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path);args=p.parse_args()
if args.baseline:rt.ROOT=args.baseline.resolve()
w,h=96,64
options={'PT_RESOLUTION':50,'PT_HISTORY':32,'PT_DENOISE':1,'PT_TEMPORAL':1,'DITHER':0}
rt.uniforms.update(gbufferPreviousModelView=np.eye(4),gbufferPreviousProjection=rt.projection)
rt.values.update(cameraPosition=(0.,0.,0.),previousCameraPosition=(0.,0.,0.),isEyeInWater=0)
const=lambda v:rt.texture(np.broadcast_to(v,(h,w,len(v))).copy())
initial={'depthtex1':rt.texture(np.ones((h,w))*rt.depth_for_z(-10)),
 'colortex1':const([.5,.5,1,1]),'colortex3':const([1,1,1,1]),'colortex4':const([.5,.04,0,0]),
 'colortex14':const([.5,.5,4,1] if args.baseline else [normal24((0,0,1)),normal24((0,0,1)),4,1]),'colortex15':const([0,0,0,0])}
pipeline=Pipeline(initial,w,h,options);lw,lh=pipeline.size(2)
expected=np.array([.20,.35,.50]);rng=np.random.default_rng(501)
for frame in range(64):
 rt.values['frameCounter']=frame
 s=(rng.random((lh,lw,1))<.15)*expected/.15
 pipeline.bank[2][pipeline.front[2]]=rt.texture(np.zeros((lh,lw,4)))
 pipeline.bank[8][pipeline.front[8]]=rt.texture(np.dstack([s,np.zeros((lh,lw))]))
 temporal=pipeline.pass_('composite2',options)
 for name in ['composite3','composite4']:pipeline.pass_(name,options)
 result=pipeline.pass_('composite5',options)[0][:,:,:3]
raw_error=float(np.sqrt(np.mean((s-expected)**2)))
error=float(np.sqrt(np.mean((result-expected)**2)))
retention=float((result.mean((0,1))/expected).mean())
report={'energy_retention':retention,'raw_rmse':raw_error,'filtered_rmse':error,'rmse_ratio':error/raw_error,'frames':64,'expected_rgb':expected.tolist(),'actual_rgb':result.mean((0,1)).tolist()}
print(json.dumps(report,indent=2),flush=True)
if args.baseline:assert retention<.65,report
else:assert .8<retention<1.15 and error<raw_error*.3,report
report['all_passed']=True
label='v061' if args.baseline else 'v063';out=Path(__file__).parent/'ptgi-evidence';out.mkdir(exist_ok=True)
(out/(label+'-transmission-history.json')).write_text(json.dumps(report,indent=2)+'\n')
Image.fromarray(np.uint8(np.clip(result[::-1],0,1)**(1/2.2)*255+.5)).save(out/(label+'-transmission-history.png'))
