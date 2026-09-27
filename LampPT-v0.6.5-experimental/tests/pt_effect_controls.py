#!/usr/bin/env python3
"""Functional effect controls use the production path integrator, not menu parsing."""
import json
from pathlib import Path
import numpy as np
from ptgi_runtime import Fixture,box,rt
from world_runtime import fragment
checks={}
def check(name,ok,value):
    assert ok,(name,value)
    checks[name]=value;print('CONTROL PASS',name,value,flush=True)
def toggle(f,options):
    rt.gl['DeleteProgram'](f.program)
    f.program=fragment(Path(__file__).with_name('ptgi_probe.fsh'),{**f.options,**options})
def mean(a):return a[:,:,:3].mean((0,1))
f=Fixture({'PT_BOUNCES':4})
geometry=box((-2,2,-3),(-1,3,-2),block=10204,color=(1.,1.,1.))
for y in range(-1,3):
    for z in range(-4,-1):geometry+=box((1,y,z),(2,y+1,z+1),color=(.95,.02,.01))
f.capture(geometry);on=mean(f.draw(size=(256,128)))
toggle(f,{'PT_GI':0});off=mean(f.draw(size=(256,128)))
check('GI control removes color bounce and retains direct light',on[0]>off[0]*1.12 and off.min()>.03,{'on':on.tolist(),'off':off.tolist()})
f.capture(box((-1,-1,1),(1,1,2),block=10002,color=(1.,1.,1.)))
args=dict(probePosition=(0.,0.,-2.),probeNormal=(0.,0.,1.),probeMaterial=(.025,-1.,0.),probeAlbedo=(.8,.8,.8))
toggle(f,{});on=mean(f.draw(**args));toggle(f,{'PT_REFLECTIONS':0});off=mean(f.draw(**args))
check('reflection control removes offscreen mirror contribution',on[2]>.1 and off.max()==0,{'on':on.tolist(),'off':off.tolist()})
f.capture([])
args=dict(size=(256,64),probeMode=2,probeMaterial=(.001,.04,0.),probeKind=2.,probeDirection=(.5,-np.sqrt(.75),0.))
toggle(f,{});a=f.draw(**args);bent=a[a[:,:,3]>.5,:3].mean(0)
toggle(f,{'PT_REFRACTION':0});a=f.draw(**args);straight=a[a[:,:,3]>.5,:3].mean(0)
check('refraction toggle selects Snell or straight transmission',abs(bent[0]-1/3)<.003 and abs(straight[0]-.5)<.003,{'bent':bent.tolist(),'straight':straight.tolist()})
args=dict(probePosition=(0.,0.,-4.),probeNormal=(0.,0.,1.),probeMaterial=(.75,.04,1.),probeKind=24.,probeAlbedo=(1.,1.,1.),isEyeInWater=1)
toggle(f,{});on=mean(f.draw(**args));toggle(f,{'WATER_ENABLED':0});off=mean(f.draw(**args))
check('water toggle disables camera medium attenuation',on[0]<off[0]*.7 and abs(off[0]-24)<.001,{'on':on.tolist(),'off':off.tolist()})
# A neutral optical interface must preserve the same lamp through dyed glass.
f.capture(box((-1,-1,-3),(1,1,-2),block=10013,color=(1.,.12,.04))+box((-1,-1,-5),(1,1,-4),block=10204,color=(1.,1.,1.)))
args=dict(size=(256,128),probePosition=(.01,.01,-2.),probeNormal=(0.,0.,1.),probeMaterial=(.001,.04,0.),probeKind=2.,probeAlbedo=(1.,.012,.003))
toggle(f,{'GLASS_ROUGHNESS':'0.001'});on=mean(f.draw(**args))
toggle(f,{'PT_GLASS':0});off=mean(f.draw(**args))
check('glass control removes dielectric tint and Fresnel',on[1]<off[1]*.2 and np.ptp(off)<.001,{'on':on.tolist(),'off':off.tolist()})
# Direct visibility switch: only the source connection ignores the slab.
f.capture(box((0,2,-3),(1,3,-2),block=10001,color=(1.,1.,1.))+box((-1,1,-4),(2,1.25,-1)))
toggle(f,{});on=mean(f.draw(probeMode=4));toggle(f,{'PT_SHADOWS':0});off=mean(f.draw(probeMode=4))
check('direct shadow control changes occluded lamp visibility',on.max()==0 and off[0]>.03,{'on':on.tolist(),'off':off.tolist()})
# Caustic control follows the diffuse -> dielectric -> sun path classification.
f=Fixture({'PT_BOUNCES':4,'SUN_INTENSITY':'1.0','WATER_ROUGHNESS':'0.001','WATER_ABSORPTION':'0.0','WATER_WAVES':0,'PT_SUN_ANGLE':'0.0186'})
surface=[]
for x in range(-4,4):
    for z in range(-5,4):surface+=box((x,.5,z),(x+1,.5,z+1),owner=(x,0,z),block=10000)[24:30]
f.capture(surface)
args=dict(size=(128,128),probePosition=(-1.,-1.,-3.),probeU=(2.,0.,0.),probeV=(0.,0.,2.),sunPosition=(0.,1.,0.),shadowLightPosition=(0.,1.,0.),isEyeInWater=1)
on=mean(f.draw(**args));toggle(f,{'PT_CAUSTICS':0});off=mean(f.draw(**args))
check('caustic toggle removes refractive receiver paths',on.min()>.2 and off.max()<.001,{'on':on.tolist(),'off':off.tolist()})
(Path(__file__).parent/'ptgi-evidence/controls.json').write_text(json.dumps({'checks':checks,'all_passed':True},indent=2)+'\n')
