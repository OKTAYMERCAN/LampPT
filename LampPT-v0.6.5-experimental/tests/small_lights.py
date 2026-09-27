#!/usr/bin/env python3
"""Tiny source energy, importance-resampling variance and real occlusion."""
import json
from pathlib import Path
import numpy as np
from ptgi_runtime import Fixture,box,rt
from world_runtime import fragment
out=Path(__file__).parent/'ptgi-evidence';out.mkdir(exist_ok=True)
f=Fixture({'PT_BOUNCES':2,'PT_LIGHT_CANDIDATES':1})
mesh=box((-.0625,0.,-2.0625),(.0625,.625,-1.9375),owner=(0,0,-2),color=(1,1,1),block=10200)
# Brown stem below a bright tip. Source capture may sample the stem midpoint.
atlas=np.ones((16,16,4),np.float32);atlas[:12,:,:3]=[.32,.18,.07]
f.capture(mesh,rt.texture(atlas))
args=dict(size=(256,128),probeMode=4,probePosition=(1.,.01,-2.),probeNormal=(0,1,0),probeDirection=(0,-1,0))
def variant(options):
 rt.gl['DeleteProgram'](f.program)
 f.program=fragment(Path(__file__).with_name('ptgi_probe.fsh'),{**f.options,**options})
 return f.draw(**args)[:,:,:3]
one=variant({'PT_LIGHT_CANDIDATES':1});four=variant({'PT_LIGHT_CANDIDATES':4})
m1,m4=one.mean((0,1)),four.mean((0,1));v1,v4=one[:,:,0].std(),four[:,:,0].std()
assert m4[0]>.05,(m1,m4)
# Resampling changes variance, not expected emitted energy. Use an MC tolerance.
assert abs(m1[0]-m4[0])<.04*max(m1[0],m4[0])+.001,(m1,m4)
assert v4<v1*.65,(v1,v4)
half=variant({'PT_LIGHT_CANDIDATES':4,'SMALL_LIGHT_BOOST':'0.5'})
assert np.max(abs(half-four*.5))<1e-5
zero=variant({'PT_LIGHT_CANDIDATES':4,'EMISSIVE_ENABLED':0});assert zero.max()==0
# A wall between the receiver and the torch must stop all selected samples.
f.capture(mesh+box((.4,-1.,-4.),(.6,2.,0.)),rt.texture(atlas))
blocked=variant({'PT_LIGHT_CANDIDATES':4});assert blocked.max()==0
report={'all_passed':True,'one_candidate_rgb':m1.tolist(),'four_candidates_rgb':m4.tolist(),
 'relative_stddev_ratio':float(v4/v1),'power_half_max_error':float(np.max(abs(half-four*.5))),
 'blocked_max':float(blocked.max()),'emission_off_max':float(zero.max())}
print(json.dumps(report,indent=2),flush=True)
(out/'small-lights.json').write_text(json.dumps(report,indent=2)+'\n')
