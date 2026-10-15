#!/usr/bin/env python3
"""Static glass must integrate random reflection/transmission branch changes.

Changing the path's secondary guide is not proof that a stationary scene moved.
Known branch probabilities/radiances isolate unwanted history resets.
"""
import json
from pathlib import Path
import numpy as np
import gl_runtime as rt
from pipeline_routing import Pipeline
from buffer_encoding import normal24,rgb24,material24
w,h=96,64;normal=normal24((0,0,1));const=lambda v:rt.texture(np.broadcast_to(v,(h,w,len(v))).copy())
opts={'PT_RESOLUTION':50,'PT_TEMPORAL':1,'PT_DENOISE':0,'PT_HISTORY':64,
      'GLASS_HISTORY':32,'VOLUMETRIC_CLOUDS':0}
rt.uniforms.update(gbufferModelViewInverse=np.eye(4),gbufferPreviousModelView=np.eye(4),gbufferPreviousProjection=rt.projection)
rt.values.update(cameraPosition=(0.,0.,0.),previousCameraPosition=(0.,0.,0.),isEyeInWater=0)
p=Pipeline({'depthtex1':rt.texture(np.ones((h,w))*rt.depth_for_z(-16)),
 'colortex1':const([.5,.5,1,1]),'colortex3':const([1,1,1,1]),'colortex4':const([.75,.04,0,0]),
 'colortex5':const([material24([.001,.04,0,2]),0,normal,1]),
 'colortex15':const([rgb24([1,1,1]),2,normal,1])},w,h,opts)
lw,lh=p.size(2);yy,xx=np.mgrid[:lh,:lw];diffuse=np.array([.2,.35,.5]);reflected=np.array([2.,1.,.6])
expected=diffuse*.875+reflected*.125;errors=[];raw_errors=[];means=[]
for frame in range(64):
    reflection=(xx+yy*3+frame)%8==0
    signal=np.where(reflection[:,:,None],reflected,diffuse)
    guide=np.dstack([np.full((lh,lw),normal),np.where(reflection,rgb24([1,1,1]),rgb24(diffuse)),
                     np.where(reflection,-1.,16.),np.full((lh,lw),material24([.001,.04,0,2]))])
    p.bank[2][p.front[2]]=rt.texture(np.zeros((lh,lw,4)))
    p.bank[8][p.front[8]]=rt.texture(np.dstack([signal,np.zeros((lh,lw))]))
    p.bank[6][p.front[6]]=rt.texture(guide)
    rt.values['frameCounter']=frame
    value=p.pass_('composite2',opts)[1][:,:,:3]
    if frame>=32:
        errors.append(float(np.mean((value-expected)**2)));raw_errors.append(float(np.mean((signal-expected)**2)))
        means.append(value.mean((0,1)))
ratio=float(np.sqrt(np.mean(errors)/np.mean(raw_errors)))
retention=np.mean(means,0)/expected
assert ratio<.15 and np.max(abs(retention-1))<.03,(ratio,retention)
report={'all_passed':True,'filtered_to_raw_rmse':ratio,'energy_retention_rgb':retention.tolist(),'scope':__doc__}
(Path(__file__).parent/'ptgi-evidence/v076-optical-mixture.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
