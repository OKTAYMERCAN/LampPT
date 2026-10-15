#!/usr/bin/env python3
"""GI reaches a receiver after bouncing off a colored wall behind a baffle.

Runs the production world-space integrator, then the production merge,
temporal, spatial and resolve passes. No constant ambient term is supplied.
"""
import json
from pathlib import Path
import numpy as np
from ptgi_runtime import Fixture,box,rt
from pipeline_routing import Pipeline
from buffer_encoding import normal24,material24,rgb24

OUT=Path(__file__).parent/'ptgi-evidence';records={}
options={'PT_BOUNCES':2,'PT_SKYLIGHT':0,'PT_SUNLIGHT':0,'PT_REFLECTIONS':0,'PT_RESOLUTION':100,
         'PT_TEMPORAL':1,'PT_DENOISE':1,'HRR_GI':0,'HRR_SHADOWS':0,'HRR_REFLECTIONS':0,'HRR_CLOUDS':0}
f=Fixture(options)
lamp=box((-2,2,-3),(-1,3,-2),block=10204,color=(1,1,1))
wall=box((1,-1,-4),(1.3,3,-1),color=(.95,.035,.015))
baffle=box((-1.05,.05,-3.5),(-.65,1.9,-1.5),color=(.01,.01,.01))
f.capture(lamp+wall+baffle)
direct=f.draw(size=(256,128),probeMode=13)[:,:,:3]
gi=f.draw(size=(256,128),probeMode=14)[:,:,:3]
gmean=gi.mean((0,1));dmean=direct.mean((0,1))
records['two_event_gi_rgb']=gmean.tolist();records['direct_rgb']=dmean.tolist()
assert gmean[0]>.005 and gmean[0]>10*max(gmean[1],gmean[2]),records
# A complete blocker between the receiver and wall must remove those paths.
f.capture(lamp+wall+baffle+box((.7,-2,-5),(.9,4,0),color=(.0,.0,.0)))
blocked=f.draw(size=(256,128),probeMode=14)[:,:,:3].mean((0,1))
records['blocked_gi_rgb']=blocked.tolist();assert blocked[0]<gmean[0]*.1,records
# Relay actual Monte Carlo GI samples through the production component merge.
# A constant first-surface fixture isolates the wiring and reconstruction.
f.capture(lamp+wall+baffle)
rt.uniforms.update(gbufferPreviousModelView=np.eye(4),gbufferPreviousProjection=rt.projection)
rt.values.update(cameraPosition=(0.,0.,0.),previousCameraPosition=(0.,0.,0.),isEyeInWater=0)
n=48;const=lambda v:rt.texture(np.broadcast_to(v,(n,n,len(v))))
albedo=np.array([.7,.7,.7]);srgb=np.where(albedo<=.0031308,albedo*12.92,1.055*albedo**(1/2.4)-.055)
data={'depthtex1':rt.texture(np.ones((n,n))*rt.depth_for_z(-4)), 'colortex1':const([.5,.5,1,1]),
      'colortex3':const([*srgb,1]),'colortex4':const([.75,.04,0,0]),'colortex10':const([0,1,.5,.5])}
p=Pipeline(data,n,n,f.options)
# Deliberately supply the captured component image: avoid running unrelated
# first-surface estimators at the synthetic plane's different raster position.
p.dispatch_attached=lambda *args:None
guide=const([normal24([0,0,1]),normal24([0,0,1]),4,material24([.75,.04,0,0])])
zero=const([0,0,0,rgb24(albedo)])
for frame in range(32):
    rt.values['frameCounter']=frame
    samples=f.draw(size=(n,n),probeMode=14,frameCounter=frame)[:,:,:3]/albedo
    for image,(sampler,obj,w,h) in list(p.images.items()):
        value=guide if 'Guide' in image else rt.texture(np.dstack([samples,np.ones((n,n))*rgb24(albedo)])) if image=='ptGIImage' else zero
        p.images[image]=(sampler,value,w,h)
    for stage in ['composite1','composite2','composite3','composite4','composite5','composite6','composite7']:
        result=p.pass_(stage,f.options)
final=result[0][:,:,:3].mean((0,1))
records['resolved_gi_rgb']=final.tolist()
assert .8<final[0]/gmean[0]<1.2 and final[0]>10*max(final[1],final[2]),records
# The GI switch also zeroes the actual transport component.
off=Fixture({**options,'PT_GI':0});off.capture(lamp+wall+baffle)
records['gi_off_max']=float(off.draw(probeMode=14)[:,:,:3].max());assert records['gi_off_max']==0
records.update(all_passed=True,scope='Synthetic Mesa transport and production post passes; not Minecraft')
(OUT/'v068-gi-visibility.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records,indent=2),flush=True)
