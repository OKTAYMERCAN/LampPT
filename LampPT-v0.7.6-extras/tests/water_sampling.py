#!/usr/bin/env python3
"""Ballistic light through absorbing/scattering water: Beer-Lambert ground truth.

Production integrator, geometry, Fresnel and medium paths. NEE is disabled and
one scatter terminates the path to isolate the unscattered radiance component.
This tests sampling, NOT a denoised picture or changed artistic water defaults.
"""
import argparse,json,re
from pathlib import Path
import numpy as np
from ptgi_runtime import Fixture,box,rt
ap=argparse.ArgumentParser();ap.add_argument('--pack',type=Path);ap.add_argument('--label',default='v072');args=ap.parse_args()
if args.pack:rt.ROOT=args.pack.resolve()
opts={'PT_BOUNCES':1,'PT_LIGHT_SAMPLES':0,'PT_SKYLIGHT':0,'PT_SUNLIGHT':0,
 'PT_VOLUMETRICS':1,'WATER_WAVES':0,'WATER_ROUGHNESS':'0.001','WATER_SCATTERING':'0.04',
 'WATER_ABSORPTION':'0.16','WATER_R':'0.08','WATER_G':'0.42','WATER_B':'0.55'}
f=Fixture(opts)
distance=48.
f.capture(box((-64,-64,-distance-.5),(64,64,-distance-.25),block=10204,color=(1,1,1)))
# End rod uses calibrated radiance 8 * 3 = 24. The normal-incidence transmitted
# radiance includes (1-F) * etaI^2/etaT^2, independently evaluated in Python.
settings=(rt.ROOT/'lib/settings.glsl').read_text()
val=lambda k:float(re.search(r'^#define '+k+r' (\S+)',settings,re.M)[1])
eta=val('WATER_IOR');F=((1-eta)/(1+eta))**2
source=8*val('SMALL_LIGHT_BOOST')*val('EMISSIVE_STRENGTH')
expected=source*(1-F)/(eta*eta)*np.exp(-(np.array([.92,.58,.45])*.16+.04)*distance)
values=[]
for frame in range(8):
 a=f.draw(size=(256,128),probePosition=(0.,0.,-.25),probeNormal=(0.,0.,1.),
   probeMaterial=(.001,.02,0.),probeKind=1.,probeAlbedo=(1.,1.,1.),frameCounter=frame)
 values.append(a[:,:,:3].reshape(-1,3))
a=np.concatenate(values);mean=a.mean(0);se=a.std(0)/np.sqrt(len(a))
assert np.isfinite(a).all()
assert np.all(abs(mean-expected)<6*se+.025*expected),(mean,expected,se)
report={'mean':mean.tolist(),'expected':expected.tolist(),'standard_error':se.tolist(),
 'variance_rgb':a.var(0).tolist(),'maximum_rgb':a.max(0).tolist(),'nonzero_fraction':float((a.max(1)>0).mean()),
 'samples':len(a),'all_passed':True,'scope':__doc__}
print(json.dumps(report,indent=2),flush=True)
(Path(__file__).parent/'ptgi-evidence'/(args.label+'-water-sampling.json')).write_text(json.dumps(report,indent=2)+'\n')
