#!/usr/bin/env python3
"""Small emitter and finite-water path probes using the production integrator."""
import argparse,json,re
from pathlib import Path
import numpy as np
from ptgi_runtime import Fixture,box,rt
p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path);a=p.parse_args()
if a.baseline:rt.ROOT=a.baseline.resolve()
records={}
settings=(rt.ROOT/'lib/settings.glsl').read_text()
rough=float(re.search(r'^#define WATER_ROUGHNESS (\S+)',settings,re.M)[1])
def measure(name,frame):
 rgb=frame[:,:,:3];lum=rgb@np.array([.2126,.7152,.0722]);records[name]={'rgb':rgb.mean((0,1)).tolist(),'mean':float(lum.mean()),'std':float(lum.std()),'black_fraction':float((lum<1e-5).mean())};print(name,records[name],flush=True)
# The torch is 2/16 wide and 10/16 tall, not an entire glowing cube.
f=Fixture({'PT_BOUNCES':2})
mesh=box((-.0625,0.,-2.0625),(.0625,.625,-1.9375),owner=(0,0,-2),color=(1,1,1),block=10200)
f.capture(mesh)
measure('torch_1m',f.draw(size=(128,128),probeMode=4,probePosition=(1.,.01,-2.),probeNormal=(0,1,0),probeDirection=(0,-1,0)))
measure('torch_3m',f.draw(size=(128,128),probeMode=4,probePosition=(3.,.01,-2.),probeNormal=(0,1,0),probeDirection=(0,-1,0)))
for b in [2,4]:
 opts={'PT_BOUNCES':b,'PT_SKYLIGHT':1,'CUSTOM_SKY':1,'SUN_INTENSITY':'1.0','PT_VOLUMETRICS':1}
 f=Fixture(opts)
 surface=box((-32,-2,-32),(32,-2,32),block=10000)[24:30]
 bottom=box((-32,-5,-32),(32,-4.9,32),color=(.7,.7,.7))
 f.capture(surface+bottom)
 kw=dict(size=(128,128),sunPosition=(0,1,0),shadowLightPosition=(0,1,0))
 measure(f'above_water_{b}',f.draw(probePosition=(.2,-2.,-1.),probeNormal=(0,1,0),probeKind=1.,probeAlbedo=(1,1,1),probeMaterial=(rough,.02,0),**kw))
 # Camera in the same three-block-deep water, looking toward the sky or floor.
 f.capture([dict(v,position=v['position']+np.array([0,3,0])) for v in surface+bottom])
 measure(f'underwater_sky_{b}',f.draw(probePosition=(.2,1.,-.2),probeNormal=(0,1,0),probeKind=1.,probeAlbedo=(1,1,1),probeMaterial=(rough,.02,0),isEyeInWater=1,**kw))
 measure(f'underwater_floor_{b}',f.draw(probePosition=(.2,-1.9,-1.),probeNormal=(0,1,0),probeKind=0.,probeAlbedo=(.7,.7,.7),isEyeInWater=1,**kw))
if a.baseline:
 assert records['underwater_floor_2']['mean']<1e-12,records
else:
 assert records['torch_1m']['rgb'][0]>.5 and records['torch_3m']['rgb'][0]>.025,records
 for b in [2,4]:
  assert records[f'above_water_{b}']['mean']>.04,records
  assert records[f'underwater_sky_{b}']['mean']>.1,records
  assert records[f'underwater_floor_{b}']['mean']>.04,records
  assert records[f'above_water_{b}']['std']<5,records
records['all_passed']=True
records['scope']='Actual production GLSL on synthetic geometry; not Minecraft or GPU FPS'
label='v061' if a.baseline else 'v063' 
out=Path(__file__).parent/'ptgi-evidence';out.mkdir(exist_ok=True)
(out/(label+'-water-lights.json')).write_text(json.dumps(records,indent=2)+'\n')
