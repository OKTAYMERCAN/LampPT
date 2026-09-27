#!/usr/bin/env python3
"""Whole-pipeline dark-room and water renders, including underwater raster input."""
import argparse,json,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).parent;OUT=HERE/'ptgi-evidence';OUT.mkdir(exist_ok=True)
p=argparse.ArgumentParser();p.add_argument('--case',choices=['torch-room','water-above','water-below']);p.add_argument('--baseline',type=Path);args=p.parse_args()
if args.case:
 import scene_review as s
 if args.baseline:s.rt.ROOT=args.baseline.resolve()
 s.faces.clear();s.W,s.H=193,113;s.OUT=OUT
 opts={'GEOMETRY_BUDGET':65536,'shadowMapResolution':256,'DITHER':0,'BLOOM_ENABLED':0}
 if args.case=='torch-room':
  s.eye=np.array([3.,2.,4.],np.float32);s.center=np.array([0.,.6,-1.],np.float32)
  s.floor(-4,4,-6,5)
  s.box((-4,0,-6.2),(4,4,-6),(.7,.7,.7));s.box((-4.2,0,-6),(-4,4,5),(.7,.7,.7))
  s.box((4,0,-6),(4.2,4,5),(.7,.7,.7));s.box((-4,4,-6),(4,4.2,5),(.7,.7,.7))
  s.box((-.0625,0,-1.0625),(.0625,.625,-.9375),(1.,1.,1.),10200)
  opts.update(PT_SUNLIGHT=0,PT_SKYLIGHT=0)
  s.rt.values['isEyeInWater']=0
 else:
  s.eye=np.array([3.,3.2,5.] if args.case=='water-above' else [0.,-.8,3.],np.float32)
  s.center=np.array([0.,-1.,-1.] if args.case=='water-above' else [0.,-.1,-3.],np.float32)
  for x in range(-6,6):
   for z in range(-8,5):
    s.floor(x,x+1,z,z+1,-3.,(.65,.6,.4) if (x+z)%2==0 else (.35,.45,.5))
    s.floor(x,x+1,z,z+1,0.,(1.,1.,1.),True)
  s.box((-6,-3,-8.2),(6,2.,-8),(.7,.7,.7))
  s.rt.values['isEyeInWater']=int(args.case=='water-below')
 s.V=s.look(s.eye,s.center);s.V[:3,3]=0
 s.P=np.array(s.rt.projection,copy=True);s.P[0,0]*=s.H/s.W
 s.rt.uniforms.update(gbufferProjection=s.P,gbufferProjectionInverse=np.linalg.inv(s.P),gbufferModelView=s.V,gbufferModelViewInverse=np.linalg.inv(s.V))
 result,passes,gray,water,_=s.render(opts,sun=(.15,.95,.1),frames=32)
 label=('v061-' if args.baseline else 'v065-')+args.case
 s.save(label,result)
 frame=passes['composite5'][0][:,:,:3]
 region=water if args.case=='water-above' else gray|water
 if not region.any():region=np.ones(frame.shape[:2],bool)
 report={'mean_display_rgb':result[region,:3].mean(0).tolist(),'mean_linear_rgb':frame[region].mean(0).tolist(),
  'mean_history_age':float(passes['composite2'][2][:,:,3].mean()),
  'fraction_visible':float((result[region,:3].max(-1)>.05).mean()),'finite':bool(np.isfinite(result).all()),
  'frames':32,'resolution':[s.W,s.H],'scope':'Synthetic Mesa render, not Minecraft'}
 assert report['finite'] and report['fraction_visible']>.5,report
 report['all_passed']=True
 (OUT/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n')
 print(label,json.dumps(report),flush=True)
else:
 for case in ['torch-room','water-above','water-below']:
  subprocess.run([sys.executable,__file__,'--case',case,*(['--baseline',str(args.baseline)] if args.baseline else [])],check=True)
