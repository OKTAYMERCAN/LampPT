"""Lit opaque scenery through glass; optional fog/cloud occlusion regression."""
import argparse,json
from pathlib import Path
import numpy as np
import gl_runtime as rt
ap=argparse.ArgumentParser();ap.add_argument('--pack',type=Path);ap.add_argument('--case',default='glass');ap.add_argument('--frames',type=int,default=12);args=ap.parse_args()
if args.pack:rt.ROOT=args.pack.resolve()
import scene_review as s
s.faces.clear();s.W,s.H=127,75;s.OUT=Path(__file__).parent/'ptgi-evidence'
s.eye=np.array([0.,2.,5.],np.float32);s.center=np.array([0.,1.,-5.],np.float32)
if args.case=='glass':
 s.box((-3.,-.5,-.12),(3.,4.,0.),(1,1,1),10010)
 s.faces=[(*face[:-1],True) for face in s.faces]
s.floor(-8,8,-12,4,0,(.6,.6,.6))
for i in range(8):
 c=(.75,.10,.025) if i%2 else (.025,.20,.75)
 s.box((-4+i,0,-5),(-3.1+i,2,-4.5),c)
s.V=s.look(s.eye,s.center);s.V[:3,3]=0
s.P=np.array(rt.projection,copy=True);s.P[0,0]*=s.H/s.W
rt.uniforms.update(gbufferProjection=s.P,gbufferProjectionInverse=np.linalg.inv(s.P),gbufferModelView=s.V,gbufferModelViewInverse=np.linalg.inv(s.V))
rt.values['isEyeInWater']=0
opts={'GEOMETRY_BUDGET':65536,'shadowMapResolution':64,'PT_RESOLUTION':50,
 'VOLUMETRIC_CLOUDS':0,'PT_AIR_DENSITY':'0.0','DITHER':0,'BLOOM_ENABLED':0}
if args.case=='cloud':opts.update(VOLUMETRIC_CLOUDS=1,CLOUD_HEIGHT='-4.0',CLOUD_THICKNESS='12.0',CLOUD_DENSITY='0.02',CLOUD_COVERAGE='1.0',CLOUD_WIND_SPEED='0.0')
image,passes,gray,glass,_=s.render(opts,frames=args.frames)
a=passes['composite7'][0][:,:,:3]
report={'case':args.case,'finite':bool(np.isfinite(a).all()),'center':a[25:55,40:90].mean((0,1)).tolist()}
s.save('v073-lit-'+args.case,image)
assert report['finite'] and sum(report['center'])>.05,report
(s.OUT/('v073-lit-'+args.case+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
