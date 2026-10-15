#!/usr/bin/env python3
"""Animated Snell-window/water optics in the real mesh + production PT pipeline."""
import argparse,json
from pathlib import Path
import numpy as np
import gl_runtime as rt
ap=argparse.ArgumentParser();ap.add_argument('--pack',type=Path);ap.add_argument('--label',default='v072')
ap.add_argument('--case',choices=['above','below'],default='below');ap.add_argument('--frames',type=int,default=48)
ap.add_argument('--flat',action='store_true');args=ap.parse_args()
if args.pack:rt.ROOT=args.pack.resolve()
import scene_review as s
from pipeline_routing import Pipeline
from world_runtime import fragment
OUT=Path(__file__).parent/'ptgi-evidence'
s.faces.clear();s.W,s.H=257,145;s.OUT=OUT
s.eye=np.array([3.,3.,6.] if args.case=='above' else [0.,-1.4,2.],np.float32)
s.center=np.array([0.,-1.,-1.] if args.case=='above' else [0.,.4,-2.],np.float32)
for x in range(-8,8):
 for z in range(-10,6):
  c=(.7,.59,.32) if (x+z)%2==0 else (.29,.46,.59)
  s.floor(x,x+1,z,z+1,-4.,c)
  s.floor(x,x+1,z,z+1,0.,(1,1,1),True)
# Identifiable geometry above water makes genuine refracted scenery measurable.
for x in range(-6,7):
 s.box((x,0,-7.4),(x+.8,3+(x%2),-6.8),(.8,.22,.10) if x%2 else (.22,.58,.8))
s.box((-8,-4,-10.3),(8,1,-10),(.65,.7,.7))
s.box((-3,-3,-5),(-2,-1,-4),(.9,.7,.4))
s.V=s.look(s.eye,s.center);s.V[:3,3]=0
s.P=np.array(rt.projection,copy=True);s.P[0,0]*=s.H/s.W
rt.uniforms.update(gbufferProjection=s.P,gbufferProjectionInverse=np.linalg.inv(s.P),gbufferModelView=s.V,gbufferModelViewInverse=np.linalg.inv(s.V))
rt.values['isEyeInWater']=int(args.case=='below')
opts={'GEOMETRY_BUDGET':65536,'shadowMapResolution':128,'PT_RESOLUTION':50,
 'VOLUMETRIC_CLOUDS':0,'DITHER':0,'BLOOM_ENABLED':0,'WATER_WAVES':0 if args.flat else 1}
old=Pipeline.pass_;records=[];last=None
program=None

def step(self,name,options):
 global program,last
 if name=='composite1':
  rt.values['frameTimeCounter']=3.+rt.values['frameCounter']/30
  if program is None:program=fragment(Path(__file__).with_name('water_animate.fsh'),options)
  tex,_=rt.draw(program,self.inputs(),s.W,s.H,outputs=1,full_precision=(0,))
  self.bank[14][self.front[14]]=tex[0]
 out=old(self,name,options)
 if name=='composite7':
  a=out[0][:,:,:3]
  assert np.isfinite(a).all()
  if last is not None and rt.values['frameCounter']>=args.frames//2:
   records.append(float(np.sqrt(np.mean((a-last)**2))))
  last=a.copy()
 return out
Pipeline.pass_=step
image,passes,gray,water,_=s.render(opts,sun=(.2,.94,.2),frames=args.frames)
label=args.label+'-water-'+args.case+('-flat' if args.flat else '')
s.save(label,image)
region=water if water.any() else np.ones((s.H,s.W),bool)
report={'all_passed':bool(np.isfinite(image).all()),'mean_display_rgb':image[region,:3].mean(0).tolist(),
 'mean_linear_rgb':last[region].mean(0).tolist(),'visible_fraction':float((image[region,:3].max(1)>.05).mean()),
 'animated_frame_difference_rmse':float(np.mean(records)),'frames':args.frames,'resolution':[s.W,s.H],
 'base_PT_scale':50,'HRR':True,'scope':__doc__+' Software Mesa, no Minecraft FPS. Both animation and Monte Carlo noise affect frame difference.'}
assert report['all_passed'] and report['visible_fraction']>.75,report
print(label,json.dumps(report,indent=2),flush=True)
(OUT/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n')
