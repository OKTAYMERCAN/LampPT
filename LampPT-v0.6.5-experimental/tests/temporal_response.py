#!/usr/bin/env python3
"""Keep rare steady light, reject stale light, and invalidate changed materials."""
import json
from pathlib import Path
import numpy as np
import gl_runtime as rt
from pipeline_routing import Pipeline
w,h=96,64
options={'PT_RESOLUTION':50,'PT_HISTORY':32,'PT_DENOISE':1,'PT_TEMPORAL':1,'PT_OUTLIER_FILTER':0}
rt.uniforms.update(gbufferPreviousModelView=np.eye(4),gbufferPreviousProjection=rt.projection)
rt.values.update(cameraPosition=(0.,0.,0.),previousCameraPosition=(0.,0.,0.),isEyeInWater=0)
const=lambda v:rt.texture(np.broadcast_to(v,(h,w,len(v))).copy())
initial={'depthtex1':rt.texture(np.ones((h,w))*rt.depth_for_z(-4)),
 'colortex1':const([.5,.5,1,1]),'colortex10':const([0,1,.5,.5]),'colortex3':const([1,1,1,1]),'colortex4':const([.75,.04,0,0])}
p=Pipeline(initial,w,h,options);lw,lh=p.size(2);rng=np.random.default_rng(501)
expected=np.array([.20,.35,.50]);retention=[];remaining={}
def frame(i,s):
 rt.values['frameCounter']=i
 for buffer in [2,8]:
  old=p.bank[buffer][p.front[buffer]]
  p.bank[buffer][p.front[buffer]]=rt.texture(np.dstack([s,np.zeros((lh,lw))]))
  rt.gl['DeleteTextures'](1,rt.C.byref(rt.U(old)))
 return p.pass_('composite2',options)
for i in range(96):
 out=frame(i,(rng.random((lh,lw,1))<.15)*expected/.15)
 if i>=64:retention.append(float((out[1][:,:,:3].mean((0,1))/expected).mean()))
before=out[1][:,:,:3].mean()
for i in range(1,33):
 out=frame(96+i,np.zeros((lh,lw,3)))
 if i in [1,8,16,32]:remaining[str(i)]=float(out[1][:,:,:3].mean()/before)
assert .90<np.mean(retention)<1.10,retention
assert remaining['8']<.25 and remaining['16']<.05 and remaining['32']<.02,remaining
# A stationary replacement keeps normal and depth but must drop the old BSDF.
for i in range(32):out=frame(140+i,np.broadcast_to(expected,(lh,lw,3)))
p.bank[4][p.front[4]]=const([.10,.04,0,0])
out=frame(173,np.broadcast_to(expected*2,(lh,lw,3)))
assert np.all(out[2][:,:,3]==1),np.unique(out[2][:,:,3])
report={'steady_rare_energy_retention':float(np.mean(retention)),'remaining_after_switch_off':remaining,
 'changed_material_history_age':float(out[2][lh//2,lw//2,3]),'all_passed':True,'scope':'Synthetic temporal GLSL; not in-game motion validation'}
print(json.dumps(report,indent=2),flush=True)
(Path(__file__).parent/'ptgi-evidence/v063-temporal-response.json').write_text(json.dumps(report,indent=2)+'\n')
