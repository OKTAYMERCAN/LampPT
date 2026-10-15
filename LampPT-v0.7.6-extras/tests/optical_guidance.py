#!/usr/bin/env python3
"""Known colored optical image: preserve edges while removing rare sample noise.

The production reconstruction receives ideal secondary-hit guide data. Actual
capture of those guides is independently checked in glass_review.py.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
import gl_runtime as rt
from pipeline_routing import Pipeline
from buffer_encoding import normal24,rgb24,material24
w,h=192,108
opts={'PT_RESOLUTION':50,'PT_TEMPORAL':1,'PT_HISTORY':64,'DITHER':0,'VOLUMETRIC_CLOUDS':0}
rt.uniforms.update(gbufferPreviousModelView=np.eye(4),gbufferPreviousProjection=rt.projection)
rt.values.update(isEyeInWater=0,cameraPosition=(0.,0.,0.),previousCameraPosition=(0.,0.,0.))
const=lambda v:rt.texture(np.broadcast_to(v,(h,w,len(v))).copy())
p=Pipeline({'depthtex1':rt.texture(np.ones((h,w))*rt.depth_for_z(-10)),
 'colortex1':const([.5,.5,1,1]),'colortex3':const([1,1,1,1]),'colortex4':const([.75,.04,0,0]),
 'colortex5':const([material24([.001,.04,0,2]),0,normal24((0,0,1)),1]),
 'colortex15':const([rgb24([1,1,1]),4,normal24((0,0,1)),1])},w,h,opts)
lw,lh=p.size(2);yy,xx=np.mgrid[:lh,:lw];colors=np.array([[.60,.08,.025],[.025,.15,.55]])
index=(xx//6+yy//6)%2;known=colors[index]
guide=np.zeros((lh,lw,4));guide[:,:,0]=normal24((0,0,1));guide[:,:,1]=np.array([rgb24(c) for c in colors])[index]
guide[:,:,2]=10;guide[:,:,3]=material24([.001,.04,0,2])
rng=np.random.default_rng(672)
for frame in range(64):
 rt.values['frameCounter']=frame
 s=(rng.random((lh,lw,1))<.20)*known/.20
 p.bank[2][p.front[2]]=rt.texture(np.zeros((lh,lw,4)))
 p.bank[8][p.front[8]]=rt.texture(np.dstack([s,np.zeros((lh,lw))]))
 p.bank[6][p.front[6]]=rt.texture(guide)
 temporal=p.pass_('composite2',opts)
 assert np.array_equal(temporal[6],guide)
 for stage in ['composite3','composite4','composite5','composite6']:out=p.pass_(stage,opts)
filtered=out[1][:,:,:3]
rmse=float(np.sqrt(np.mean((filtered-known)**2)));raw=float(np.sqrt(np.mean((s-known)**2)))
contrast=float(np.std(filtered[:,:,0]-filtered[:,:,2])/np.std(known[:,:,0]-known[:,:,2]))
energy=filtered.mean((0,1))/known.mean((0,1))
assert rmse<raw*.20 and contrast>.85 and np.all((energy>.90)&(energy<1.10)),(rmse,raw,contrast,energy)
report={'all_passed':True,'raw_rmse':raw,'filtered_rmse':rmse,'contrast_retention':contrast,'energy_retention_rgb':energy.tolist(),'frames':64,'scope':__doc__}
print(json.dumps(report,indent=2),flush=True)
e=Path(__file__).parent/'ptgi-evidence';(e/'v076-optical-guidance.json').write_text(json.dumps(report,indent=2)+'\n')
Image.fromarray(np.uint8(np.clip(filtered[::-1],0,1)**(1/2.2)*255+.5)).save(e/'v076-optical-guidance.png')
