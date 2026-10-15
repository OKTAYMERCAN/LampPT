#!/usr/bin/env python3
"""Secondary-image contrast through a clear interface, using production filters.

Known optical radiance isolates reconstruction blur from stochastic transport.
A separate real-mesh glass review exercises the actual transmitted rays.
"""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
import gl_runtime as rt
from pipeline_routing import Pipeline
from buffer_encoding import normal24
ap=argparse.ArgumentParser();ap.add_argument('--pack',type=Path);ap.add_argument('--label',default='v072');args=ap.parse_args()
if args.pack:rt.ROOT=args.pack.resolve()
w,h=257,145
opts={'PT_RESOLUTION':50,'PT_TEMPORAL':1,'PT_HISTORY':64,'DITHER':0,'VOLUMETRIC_CLOUDS':0}
rt.uniforms.update(gbufferPreviousModelView=np.eye(4),gbufferPreviousProjection=rt.projection)
rt.values.update(isEyeInWater=0,cameraPosition=(0.,0.,0.),previousCameraPosition=(0.,0.,0.))
const=lambda v:rt.texture(np.broadcast_to(v,(h,w,len(v))).copy())
p=Pipeline({'depthtex1':rt.texture(np.ones((h,w))*rt.depth_for_z(-10)),
 'colortex1':const([.5,.5,1,1]),'colortex3':const([1,1,1,1]),'colortex4':const([.75,.04,0,0]),
 'colortex14':const([normal24((0,0,1)),normal24((0,0,1)),4,1])},w,h,opts)
lw,lh=p.size(2);yy,xx=np.mgrid[:lh,:lw]
known=np.where(((xx//4+yy//6)%2)[...,None]==0,np.array([.65,.12,.04]),np.array([.03,.15,.55]))
# Perfect known energy lets an image filter's lost contrast be measured exactly.
rt.values['frameCounter']=0
p.bank[2][p.front[2]]=rt.texture(np.zeros((lh,lw,4)))
p.bank[8][p.front[8]]=rt.texture(np.dstack([known,np.zeros((lh,lw))]))
p.seed_guides(opts);p.pass_('composite2',opts)
ref=p.pass_('composite7',opts)[0][:,:,:3]
for stage in ['composite3','composite4','composite5','composite6']:p.pass_(stage,opts)
filtered=p.pass_('composite7',opts)[0][:,:,:3]
error=float(np.sqrt(np.mean((filtered-ref)**2)))
contrast=float(filtered[:,:,0].std()/ref[:,:,0].std())
assert np.isfinite(filtered).all()
if not args.pack:assert contrast>.80 and error<.06,(contrast,error)
report={'all_passed':True,'rgb_rmse_vs_unfiltered':error,'red_contrast_retention':contrast,'scope':__doc__}
print(json.dumps(report,indent=2),flush=True)
out=Path(__file__).parent/'ptgi-evidence'
(out/(args.label+'-optical-detail.json')).write_text(json.dumps(report,indent=2)+'\n')
for name,a in [('reference',ref),('filtered',filtered)]:
 Image.fromarray(np.uint8(np.clip(a[::-1],0,1)**(1/2.2)*255+.5)).save(out/(args.label+'-optical-'+name+'.png'))
