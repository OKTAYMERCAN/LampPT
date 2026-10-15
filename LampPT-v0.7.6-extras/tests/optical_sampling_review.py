"""Compare production sampling, with no denoiser, in fixed optical fixtures."""
import argparse,json
from pathlib import Path
import numpy as np
import gl_runtime as rt
ap=argparse.ArgumentParser();ap.add_argument('--pack',type=Path);ap.add_argument('--label',default='v073');ap.add_argument('--case',choices=['sun','cloud'],required=True);args=ap.parse_args()
if args.pack:rt.ROOT=args.pack.resolve()
from ptgi_runtime import Fixture,box
if args.case=='sun':
 f=Fixture({'PT_VOLUMETRICS':0,'WATER_ABSORPTION':'0.0','WATER_SCATTERING':'0.0','SUN_INTENSITY':'1.0','PT_BOUNCES':2})
 direction=np.array([0.,1.,-2.]);direction/=np.linalg.norm(direction)
 a=f.draw(size=(128,128),probePosition=(0.,-1.,-2.),probeNormal=(0.,1.,0.),probeMaterial=(.05,.02,0.),probeKind=1.,sunPosition=tuple(direction),shadowLightPosition=tuple(direction),probeAlbedo=(1.,1.,1.))[:,:,:3]
else:
 f=Fixture({'VOLUMETRIC_CLOUDS':1,'PT_VOLUMETRICS':1,'CLOUD_HEIGHT':'-4.0','CLOUD_THICKNESS':'12.0','CLOUD_DENSITY':'0.02','CLOUD_COVERAGE':'1.0','CLOUD_WIND_SPEED':'0.0','SUN_INTENSITY':'1.0','PT_BOUNCES':2,'HAND_LIGHT':0})
 f.capture(box((-20,-20,-5.2),(20,20,-5.0)))
 a=f.draw(size=(96,96),probeMode=16,probePosition=(0.,0.,-5.),probeNormal=(0.,0.,1.),probeAlbedo=(.7,.7,.7),sunPosition=(0.,1.,0.),shadowLightPosition=(0.,1.,0.))[:,:,:3]
l=a@np.array([.2126,.7152,.0722]);assert np.isfinite(a).all()
r={'all_finite':True,'mean':a.mean((0,1)).tolist(),'luminance_variance':float(l.var()),'zero_fraction':float((l==0).mean()),'p99':float(np.quantile(l,.99)),'maximum':float(l.max()),'samples':int(l.size),'scope':__doc__+' Mesa, not Minecraft.'}
out=Path(__file__).parent/'ptgi-evidence';(out/(args.label+'-'+args.case+'-sampling.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
