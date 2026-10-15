#!/usr/bin/env python3
"""History feedback toggles and optical-normal responsiveness use real GLSL."""
import json
from pathlib import Path
import numpy as np
import gl_runtime as rt
from pipeline_routing import Pipeline
from buffer_encoding import normal24
w,h=96,64
const=lambda v:rt.texture(np.broadcast_to(v,(h,w,len(v))).copy())
rt.uniforms.update(gbufferPreviousModelView=np.eye(4),gbufferPreviousProjection=rt.projection)
rt.values.update(cameraPosition=(0.,0.,0.),previousCameraPosition=(0.,0.,0.),isEyeInWater=0)
records={}
for feedback in ['0.0','0.25']:
 opts={'PT_RESOLUTION':50,'PT_HISTORY_STABILIZATION':feedback,'PT_DENOISE':1,'PT_TEMPORAL':1,'VOLUMETRIC_CLOUDS':0}
 p=Pipeline({'depthtex1':rt.texture(np.ones((h,w))*rt.depth_for_z(-4)),
  'colortex1':const([.5,.5,1,1]),'colortex3':const([1,1,1,1]),'colortex4':const([.75,.04,0,0])},w,h,opts)
 lw,lh=p.size(2);d=np.zeros((lh,lw,4));d[lh//2,lw//2,:3]=[.7,.25,.08]
 p.bank[2][p.front[2]]=rt.texture(d)
 rt.values['frameCounter']=0;p.seed_guides(opts);raw=p.pass_('composite2',opts);out=p.pass_('composite3',opts)
 delta=float(abs(out[2][:,:,:3]-raw[2][:,:,:3]).max())
 if feedback=='0.0':assert delta==0
 else:assert delta>.001 and delta<.25
 records['feedback_'+feedback+'_history_change']=delta
opts={'PT_RESOLUTION':50,'PT_HISTORY':64,'WATER_HISTORY':16,'PT_TEMPORAL':1,'VOLUMETRIC_CLOUDS':0}
p=Pipeline({'depthtex1':rt.texture(np.ones((h,w))*rt.depth_for_z(-10)),
 'colortex1':const([.5,.5,1,1]),'colortex3':const([1,1,1,1]),'colortex4':const([.75,.04,0,0]),
 'colortex14':const([normal24((0,0,1)),normal24((0,0,1)),4,1])},w,h,opts)
lw,lh=p.size(2)
for frame in range(20):
 rt.values['frameCounter']=frame
 p.bank[8][p.front[8]]=rt.texture(np.broadcast_to([.4,.4,.4,0],(lh,lw,4)).copy())
 p.seed_guides(opts);p.pass_('composite2',opts)
# A moving optical normal with identical physical plane must refresh radiance,
# rather than drag a many-frame-old refracted image across the water surface.
n=np.array([.25,0,1.]);n/=np.linalg.norm(n)
p.bank[14][p.front[14]]=const([normal24(n),normal24((0,0,1)),4,1])
p.bank[8][p.front[8]]=rt.texture(np.broadcast_to([.2,.2,.2,0],(lh,lw,4)).copy())
rt.values['frameCounter']=20;p.seed_guides(opts);out=p.pass_('composite2',opts)
value=float(out[1][lh//2,lw//2,0]);assert abs(value-.3)<.001,value
assert out[2][lh//2,lw//2,3]>10,'Physical-plane history was discarded instead of optical response changing'
records['wave_normal_change_first_response']=value
records.update(all_passed=True,scope='Production temporal and first-filter GLSL; synthetic inputs on Mesa')
print(json.dumps(records,indent=2),flush=True)
(Path(__file__).parent/'ptgi-evidence/v072-history-controls.json').write_text(json.dumps(records,indent=2)+'\n')
