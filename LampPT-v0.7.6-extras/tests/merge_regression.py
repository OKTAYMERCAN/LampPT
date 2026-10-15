#!/usr/bin/env python3
"""Check the one-call HRR repair against the delivered four-call formula."""
import json
from pathlib import Path
import numpy as np
from ptgi_runtime import Fixture,box,rt
from world_runtime import fragment
from buffer_encoding import normal24,material24,rgb24
HERE=Path(__file__).parent;records={}
f=Fixture({'PT_SHARED_PATHS':0,'PT_BOUNCES':3,'SUN_INTENSITY':'1.0'})
f.capture(box((-.6,.6,-2.2),(.6,1.8,-1.4),block=10204,color=(1,1,1))+box((1,-2,-5),(1.2,2,-1),color=(.8,.05,.01)))
new=rt.program('composite1',f.options);old=fragment(HERE/'merge_reference.fsh',f.options)
rt.values.update(cameraPosition=(0.,0.,0.),previousCameraPosition=(0.,0.,0.),isEyeInWater=0,skyColor=(.4,.5,.6),sunPosition=(0.,1.,0.),shadowLightPosition=(0.,1.,0.))
rt.uniforms.update(gbufferModelViewInverse=np.eye(4))
N=16;L=8
const=lambda value,n=N:rt.texture(np.broadcast_to(value,(n,n,len(value))))
data={'depthtex1':rt.texture(np.ones((N,N))*rt.depth_for_z(-4.)),
      'colortex0':const([.1,.1,.1,1]),'colortex1':const([.5,.5,1,1]),'colortex3':const([.7,.5,.3,1]),
      'colortex4':const([.75,.04,0,0]),'colortex10':const([0,1,.5,.5]),'colortex2':const([0,0,0,0],L)}
normal=normal24([0,0,1]);material=material24([.75,.04,0,0]);wrong=material24([.75,.04,0,2])
for label,pending,size in [('none',0,4),('direct',1,4),('gi',2,4),('reflection',4,4),('cloud',8,4),('mixed',5,4),('all',15,4),('base scale',0,8)]:
 inputs=dict(data)
 for component,name in enumerate(['Direct','GI','Reflect','Cloud']):
  inputs['pt'+name+'Tex']=const([.11*(component+1),.07*(component+1),.03*(component+1),rgb24([.4,.3,.2])],size)
  inputs['pt'+name+'GuideTex']=const([normal,normal,4,wrong if pending&(1<<component) else material],size)
 errors=[]
 for frame in [0,7]:
  rt.values['frameCounter']=frame
  a=rt.draw(new,inputs,L,L,outputs=2,full_precision=(0,1))[1]
  b=rt.draw(old,inputs,L,L,outputs=2,full_precision=(0,1))[1]
  error=max(float(np.max(np.abs(x-y))) for x,y in zip(a,b))
  assert all(np.isfinite(x).all() for x in a) and error<.0001,(label,error)
  errors.append(error)
 records[label]=errors;print('MERGE PASS',label,errors,flush=True)
(HERE/'ptgi-evidence/v072-independent-merge.json').write_text(json.dumps({'all_passed':True,'max_abs_error_by_case':records,'scope':'Production GLSL vs delivered 0.6.6 merge, with forced HRR repair masks. Mesa, not NVIDIA.'},indent=2)+'\n')
