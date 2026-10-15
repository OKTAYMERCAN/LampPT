#!/usr/bin/env python3
"""Compare shared-surface + primary medium against the unsplit PT estimator.

Actual production GLSL, finite synthetic mesh. Statistical tolerances account
for independent Monte Carlo realizations; this is not an in-game benchmark.
"""
import json
from pathlib import Path
import numpy as np
from ptgi_runtime import Fixture,box,rt

records={}
def compare(f,name,**kw):
    a=f.draw(size=(128,64),probeMode=0,**kw)[:,:,:3]
    b=f.draw(size=(128,64),probeMode=17,**kw)[:,:,:3]
    se=np.sqrt((a.var((0,1))+b.var((0,1)))/(128*64))
    error=np.abs(a.mean((0,1))-b.mean((0,1)))
    assert np.isfinite(b).all() and np.all(error<5*se+.025*np.maximum(a.mean((0,1)),.03)),(name,a.mean((0,1)),b.mean((0,1)),error,se)
    records[name]={'reference':a.mean((0,1)).tolist(),'shared':b.mean((0,1)).tolist(),'absolute_error':error.tolist(),'five_standard_errors':(5*se).tolist()}
    print('SHARED PASS',name,records[name],flush=True)

f=Fixture({'PT_BOUNCES':3,'PT_SKYLIGHT':1,'VOLUMETRIC_CLOUDS':0})
compare(f,'diffuse and specular sky',skyColor=(.5,.5,.5))
lamp=box((0,2,-3),(1,3,-2),color=(1,1,1),block=10001)
wall=box((1,-1,-4),(1.5,3,-1),color=(.8,.08,.025))
f.capture(lamp+wall)
compare(f,'area emitter and red bounce')
compare(f,'metal',probeMaterial=(.18,-1.,0.),probeAlbedo=(.8,.5,.2))
f.capture(box((-2,-2,-5),(2,2,-4.5),block=10204,color=(1,1,1)))
compare(f,'dielectric camera interface',probeKind=2.,probeMaterial=(.01,.04,0.),probeAlbedo=(.8,.95,1.))
f=Fixture({'PT_BOUNCES':3,'VOLUMETRIC_CLOUDS':0,'PT_REFLECTIONS':0,'PT_GI':0})
f.capture(lamp+wall);compare(f,'GI and reflections disabled')
f=Fixture({'PT_BOUNCES':3,'VOLUMETRIC_CLOUDS':0,'PT_VOLUMETRICS':1,'PT_AIR_DENSITY':'0.008'})
f.capture(lamp+wall);compare(f,'camera homogeneous volume')
f=Fixture({'PT_BOUNCES':3,'VOLUMETRIC_CLOUDS':0,'PT_VOLUMETRICS':1,'WATER_SCATTERING':'0.04'})
f.capture(lamp+wall);compare(f,'underwater camera',isEyeInWater=1)
out=Path(__file__).parent/'ptgi-evidence/v072-shared-paths.json'
out.write_text(json.dumps({'all_passed':True,'cases':records,'scope':'Production GLSL Monte Carlo mean checks on Mesa. Not an Iris or GPU benchmark.'},indent=2)+'\n')
