#!/usr/bin/env python3
"""Whole-pipeline sky/ground/mirror fixture using production shaders."""
import json
from pathlib import Path
import numpy as np
import scene_review as s
s.OUT=Path(__file__).parent/'ptgi-evidence'
s.faces.clear();s.W,s.H=257,145
s.eye=np.array([0.,68.,4.],np.float32);s.center=np.array([0.,80.,-76.],np.float32)
s.V=s.look(s.eye,s.center);s.V[:3,3]=0
s.P=np.array(s.rt.projection,copy=True);s.P[0,0]*=s.H/s.W
s.rt.uniforms.update(gbufferProjection=s.P,gbufferProjectionInverse=np.linalg.inv(s.P),gbufferModelView=s.V,gbufferModelViewInverse=np.linalg.inv(s.V))
s.floor(-32,32,-64,24,64.,(.5,.6,.3))
# A vertical metallic reflector faces the camera. Its cloud response uses
# continuation rays, not the primary sky raster path or a sampled scene color.
s.box((-8.,64.,-16.),(-2.,72.,-15.5),(.9,.9,.9),10011)
s.box((3.,64.,-20.),(4.,71.,-19.),(.6,.6,.6))
opts={'GEOMETRY_BUDGET':65536,'shadowMapResolution':128,'DITHER':0,'BLOOM_ENABLED':0,
      'CLOUD_WIND_SPEED':'0.0'}
result,passes,gray,water,_=s.render(opts,sun=(.3,.8,-.25),frames=32)
s.save('v065-cloud-scene',result)
frame=passes['composite5'][0][:,:,:3]
record={'all_passed':bool(np.isfinite(result).all()),'mean_display_rgb':result[:,:,:3].mean((0,1)).tolist(),
        'mean_linear_rgb':frame.mean((0,1)).tolist(),'frames':32,'resolution':[s.W,s.H],
        'scope':'Synthetic Mesa whole-pipeline render, not Minecraft. Default Med cloud settings; wind frozen.'}
assert record['all_passed'] and float(frame.mean())>.01,record
(s.OUT/'v065-cloud-scene.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record),flush=True)
