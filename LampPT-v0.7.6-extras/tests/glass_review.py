#!/usr/bin/env python3
"""Actual finite glass slab and colored emissive bars through production PT.

No screen-color refraction. Shadow capture, real ray intersections, medium
entry/exit and full post pipeline run in Mesa; this is not Minecraft footage.
"""
import argparse,json
from pathlib import Path
import numpy as np
import gl_runtime as rt
ap=argparse.ArgumentParser();ap.add_argument('--pack',type=Path);ap.add_argument('--label',default='v072');ap.add_argument('--economy',action='store_true');ap.add_argument('--hrr-off',action='store_true');ap.add_argument('--shared-off',action='store_true');ap.add_argument('--frames',type=int,default=32);args=ap.parse_args()
if args.pack:rt.ROOT=args.pack.resolve()
import scene_review as s
s.faces.clear();s.W,s.H=257,145;s.OUT=Path(__file__).parent/'ptgi-evidence'
s.eye=np.array([0.,1.5,5.],np.float32);s.center=np.array([0.,1.5,-5.],np.float32)
s.box((-3.,-.5,-.12),(3.,3.5,0.),(1,1,1),10010)
s.faces=[(*face[:-1],True) for face in s.faces]
for i in range(24):
 x=-3+i*.25;c=(.75,.10,.025) if i%2 else (.025,.20,.75)
 s.box((x,-.5,-4.2),(x+.22,3.5,-4.),c,10100)
s.V=s.look(s.eye,s.center);s.V[:3,3]=0
s.P=np.array(rt.projection,copy=True);s.P[0,0]*=s.H/s.W
rt.uniforms.update(gbufferProjection=s.P,gbufferProjectionInverse=np.linalg.inv(s.P),gbufferModelView=s.V,gbufferModelViewInverse=np.linalg.inv(s.V))
rt.values['isEyeInWater']=0
opts={'GEOMETRY_BUDGET':65536,'shadowMapResolution':128,'PT_RESOLUTION':50,
 'VOLUMETRIC_CLOUDS':0,'PT_AIR_DENSITY':'0.0','DITHER':0,'BLOOM_ENABLED':0,
 'PT_SUNLIGHT':0,'PT_SKYLIGHT':0,'POWDER_EMISSION':1,'POWDER_STRENGTH':'1.0'}
if args.economy:opts['PT_OPTICAL_DETAIL']=0
if args.hrr_off:opts['HRR_REFLECTIONS']=0
if args.shared_off:opts['PT_SHARED_PATHS']=0
image,passes,gray,glass,_=s.render(opts,frames=args.frames)
a=passes['composite7'][0][:,:,:3]
# Optical-hit metadata must survive the temporal pass without being replaced
# by a flat primary-plane guide. Background guide packing is unchanged.
if not args.pack and not args.economy:
 before=passes['composite1'][2];after=passes['composite2'][6]
 assert np.array_equal(before,after),'Temporal overwrote optical hit guidance'
 assert (before[:,:,2]>0).sum()>100,'Missing actual secondary hit distances'
region=a[50:95,85:172,:]
assert np.isfinite(a).all()
report={'all_passed':True,'central_linear_rgb':region.mean((0,1)).tolist(),
 'central_red_blue_contrast':float(np.std(region[:,:,0]-region[:,:,2])),
 'resolution':[s.W,s.H],'frames':args.frames,'scope':__doc__}
assert .7<float(region.mean((0,1)).sum())<1.2,region.mean((0,1))
label=args.label+('-economy' if args.economy else '')+('-full-optics' if args.hrr_off else '')+('-separate' if args.shared_off else '')+'-glass'
s.save(label,image);(s.OUT/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(label,json.dumps(report,indent=2),flush=True)
