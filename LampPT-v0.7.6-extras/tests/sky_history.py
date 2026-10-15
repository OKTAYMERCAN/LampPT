#!/usr/bin/env python3
"""Sky has directional history, not a finite floor plane or camera parallax."""
import json
from pathlib import Path
import numpy as np
import gl_runtime as rt
from pipeline_routing import Pipeline
w,h=127,75
opts={'PT_RESOLUTION':33,'PT_TEMPORAL':1,'VOLUMETRIC_CLOUDS':0}
const=lambda v:rt.texture(np.broadcast_to(v,(h,w,len(v))).copy())
p=Pipeline({'depthtex1':rt.texture(np.ones((h,w))),
 'colortex1':const([.5,.5,1,0]),'colortex3':const([0,0,0,1]),'colortex4':const([0,0,0,0])},w,h,opts)
lw,lh=p.size(2);prev=np.eye(4);prior=(0.,0.,0.)
for frame in range(32):
    angle=frame*.004;c,s=np.cos(angle),np.sin(angle)
    inv=np.eye(4);inv[:3,:3]=[[c,0,s],[0,1,0],[-s,0,c]];cam=(frame*.1,0.,0.)
    rt.uniforms.update(gbufferModelViewInverse=inv,gbufferPreviousModelView=prev,gbufferPreviousProjection=rt.projection)
    rt.values.update(frameCounter=frame,cameraPosition=cam,previousCameraPosition=prior)
    p.bank[2][p.front[2]]=rt.texture(np.zeros((lh,lw,4)))
    p.bank[8][p.front[8]]=rt.texture(np.broadcast_to([.2,.3,.5,0],(lh,lw,4)).copy())
    p.seed_guides(opts);result=p.pass_('composite2',opts)
    prev=np.linalg.inv(inv);prior=cam
age=float(result[2][4:-4,4:-4,3].mean());assert age>25,age
assert np.all(result[5][:,:,2]==-1),'Sky needs a distinct validity key'
# Replace infinite sky with a forward facing surface using otherwise identical
# material. No accumulated sky radiance is allowed into the new surface.
p.initial['depthtex1']=rt.texture(np.ones((h,w))*rt.depth_for_z(-8))
p.bank[1][p.front[1]]=const([.5,.5,1,1])
p.bank[8][p.front[8]]=rt.texture(np.zeros((lh,lw,4)))
rt.uniforms['gbufferPreviousModelView']=prev;rt.values['previousCameraPosition']=prior;rt.values['frameCounter']=32
p.seed_guides(opts);changed=p.pass_('composite2',opts)
assert changed[2][:,:,3].max()==1
assert changed[1][:,:,:3].max()==0
report={'sky_motion_history_age':age,'replacement_surface_max_age':1,'sky_leak_into_surface':0,'all_passed':True,'scope':'Synthetic production temporal GLSL on Mesa'}
print(json.dumps(report,indent=2),flush=True)
(Path(__file__).parent/'ptgi-evidence/v072-sky-history.json').write_text(json.dumps(report,indent=2)+'\n')
