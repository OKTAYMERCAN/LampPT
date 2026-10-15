#!/usr/bin/env python3
"""Actual GLSL medium statistics and traced caustic focusing; not a game test."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from ptgi_runtime import Fixture, box, rt
from world_runtime import fragment
OUT=Path(__file__).parent/'ptgi-evidence'
checks={}
def check(name,ok,value):
    print(name,value,flush=True)
    assert ok,(name,value)
    checks[name]=value

def fixture(options):
    f=Fixture(options);rt.gl['DeleteProgram'](f.program)
    f.program=fragment(Path(__file__).with_name('atmosphere_probe.fsh'),f.options)
    return f

def recompile(f,options):
    rt.gl['DeleteProgram'](f.program)
    f.program=fragment(Path(__file__).with_name('atmosphere_probe.fsh'),{**f.options,**options})

def mean(a):return a[:,:,:3].mean((0,1))
def save_image(name,rows):
    # Standard deterministic tone mapping of real GLSL renders, never a mockup.
    panels=[np.asarray(a[:,:,:3],np.float64) for a in rows]
    rgb=np.concatenate(panels,axis=1);rgb=rgb/(1+rgb)
    rgb=np.where(rgb<=.0031308,rgb*12.92,1.055*rgb**(1/2.4)-.055)
    Image.fromarray(np.uint8(np.clip(rgb,0,1)*255)).save(OUT/name)

def clouds():
    opts={'VOLUMETRIC_CLOUDS':1,'PT_VOLUMETRICS':1,'CLOUD_HEIGHT':'8.0','CLOUD_THICKNESS':'16.0',
          'CLOUD_SCALE':'24.0','CLOUD_COVERAGE':'0.85','CLOUD_DENSITY':'0.15',
          'CLOUD_STEPS':64,'CLOUD_SHADOW_STEPS':64,'CLOUD_WIND_SPEED':'0.0',
          'PT_AIR_DENSITY':'0.0','PT_DISTANCE':'256.0','CLOUD_DISTANCE':'256.0'}
    f=fixture(opts)
    p=f.draw(size=(256,128),probeMode=20,probeDirection=(0.,1.,0.))
    check('HG mean cosine equals anisotropy',abs(float(p[:,:,1].mean())-.6)<.015,float(p[:,:,1].mean()))
    check('HG samples finite and unit length',np.isfinite(p).all() and float(np.max(abs(np.linalg.norm(p[:,:,:3],axis=2)-1)))<1e-5, float(p[:,:,3].max()))
    args=dict(size=(256,128),probeMode=21,probePosition=(0.,0.,0.),probeDirection=(0.,1.,0.))
    a=f.draw(**args);T=float(a[0,0,0]);survival=1-float(a[:,:,2].mean())
    check('sampled free flight matches Beer transmittance',.02<T<.95 and abs(T-survival)<.012,{'quadrature_T':T,'MC_survival':survival})
    b=f.draw(**{**args,'probePosition':(-10.,-3.,4.),'cameraPosition':(10.,3.,-4.)})
    check('density is world anchored',float(np.max(abs(a-b)))<1e-5,float(np.max(abs(a-b))))
    recompile(f,{'CLOUD_SHADOW_STEPS':128})
    high=f.draw(**args)
    check('medium quadrature converges',abs(float(high[0,0,0])-T)<.01,{'64':T,'128':float(high[0,0,0])})
    recompile(f,{'VOLUMETRIC_CLOUDS':0});off=f.draw(**args)
    check('cloud toggle removes extinction and collisions',off[:,:,0].min()==1 and off[:,:,2].max()==0,[float(off[:,:,0].min()),float(off[:,:,2].max())])
    recompile(f,{'PT_VOLUMETRICS':0});off=f.draw(**args)
    check('volume master disables clouds',off[:,:,0].min()==1 and off[:,:,2].max()==0,True)
    recompile(f,{});off=f.draw(**args,hasCeiling=1)
    check('ceiling dimensions have no cloud layer',off[:,:,0].min()==1 and off[:,:,2].max()==0,True)
    # This emitter lies behind the cloud slab. Primary analytic emission must
    # not bypass stochastic medium visibility in the resolve path.
    a=f.draw(size=(256,128),probePosition=(0.,30.,0.),probeNormal=(0.,-1.,0.),probeAlbedo=(1.,1.,1.),probeMaterial=(.75,.04,1.),probeKind=24.)
    expected=24*T
    check('primary emitter is attenuated once by clouds',abs(float(a[:,:,0].mean())-expected)<.35,{'actual':float(a[:,:,0].mean()),'Beer':expected})
    # Compare clear sky, cloud sky and the same clouded directions in a mirror.
    recompile(f,{'SUN_INTENSITY':'1.0','CUSTOM_SKY':1,'PT_BOUNCES':6})
    view=dict(size=(96,64),probeMode=22,probeValid=0,probePosition=(-1.4,.18,-1.),probeU=(2.8,0.,0.),probeV=(0.,1.2,0.),sunPosition=(0.,1.,0.),shadowLightPosition=(0.,1.,0.))
    sky=f.draw(**view)
    recompile(f,{'SUN_INTENSITY':'1.0','CUSTOM_SKY':1,'PT_BOUNCES':6,'VOLUMETRIC_CLOUDS':0});clear=f.draw(**view)
    difference=float(np.mean(abs(sky[:,:,:3]-clear[:,:,:3])))
    check('cloud scattering changes actual camera transport',np.isfinite(sky).all() and difference>.015,{'mean_difference':difference,'cloud_mean':mean(sky).tolist()})
    recompile(f,{'SUN_INTENSITY':'1.0','CUSTOM_SKY':1,'PT_BOUNCES':6})
    mirror=f.draw(size=(96,64),probeMode=22,probePosition=(0.,-2.,-1.),probeNormal=(0.,1.,0.),probeAlbedo=(.95,.95,.95),probeMaterial=(.025,-1.,0.))
    recompile(f,{'SUN_INTENSITY':'1.0','CUSTOM_SKY':1,'PT_BOUNCES':6,'VOLUMETRIC_CLOUDS':0})
    mirror_clear=f.draw(size=(96,64),probeMode=22,probePosition=(0.,-2.,-1.),probeNormal=(0.,1.,0.),probeAlbedo=(.95,.95,.95),probeMaterial=(.025,-1.,0.))
    check('cloud medium is visible to reflected rays',abs(float(mean(mirror)[0]-mean(mirror_clear)[0]))>.01,{'cloud':mean(mirror).tolist(),'clear':mean(mirror_clear).tolist()})
    save_image('cloud_transport.png',[clear,sky])
    # Opaque geometry must occlude sunlight even when the cloud medium exists.
    f.capture(box((-30.,2.,-30.),(30.,3.,30.)))
    recompile(f,{'SUN_INTENSITY':'1.0','PT_SKYLIGHT':0,'CLOUD_COVERAGE':'1.0'})
    dark=f.draw(size=(128,64),probeMode=4,probePosition=(0.,0.,0.),sunPosition=(0.,1.,0.),shadowLightPosition=(0.,1.,0.))
    check('cloud shadows never bypass opaque occluders',dark[:,:,:3].max()==0,float(dark[:,:,:3].max()))

def caustics():
    opts={'PT_BOUNCES':3,'PT_SKYLIGHT':0,'SUN_INTENSITY':'1.0','PT_REFLECTIONS':0,
          'WATER_ROUGHNESS':'0.001','WATER_ABSORPTION':'0.0','WATER_SCATTERING':'0.0',
          'PT_SUN_ANGLE':'0.0093','WAVE_STRENGTH':'0.10','PT_CAUSTIC_SOLVER_STEPS':4}
    f=fixture(opts)
    water=box((-16.,1.,-16.),(16.,1.,16.),owner=(0,0,0),block=10000)[24:30]
    f.capture(water)
    args=dict(size=(64,64),probePosition=(-3.,-3.,-6.),probeU=(6.,0.,0.),probeV=(0.,0.,6.),
              sunPosition=(0.,1.,0.),shadowLightPosition=(0.,1.,0.),isEyeInWater=1,probeEtaI=1.333)
    guide=f.draw(probeMode=23,**args)
    solved=float(np.mean(guide[:,:,0]<.005))
    check('wave guide solves Snell at captured surface',solved>.90,{'fraction_with_direction_error_below_0.005':solved,'median_error':float(np.median(guide[:,:,0]))})
    # 256 independent paths per pixel, no temporal/spatial filter. A real focus
    # remains after averaging; single-sample grain alone cannot pass this test.
    waves=sum(f.draw(probeMode=22,frameCounter=i,**args) for i in range(8))/8
    recompile(f,{'WATER_WAVES':0})
    flat=sum(f.draw(probeMode=22,frameCounter=i,**args) for i in range(8))/8
    cv=lambda a:float(a[:,:,0].std()/a[:,:,0].mean())
    check('wave curvature focuses sunlight spatially',cv(waves)>cv(flat)*2.5 and cv(waves)>.12,{'wave_CV':cv(waves),'flat_CV':cv(flat),'wave_mean':mean(waves).tolist(),'flat_mean':mean(flat).tolist()})
    ratio=float(mean(waves)[0]/mean(flat)[0]);peak=float(waves[:,:,0].max()/waves[:,:,0].mean())
    check('focusing redistributes energy without isolated blowouts',.8<ratio<1.2 and peak<6,{'wave_to_flat_mean':ratio,'peak_to_mean':peak})
    recompile(f,{'PT_CAUSTICS':0});off=f.draw(probeMode=22,**args)
    check('caustic switch removes focused transport',off[:,:,:3].max()<1e-7,float(off[:,:,:3].max()))
    recompile(f,{});f.capture([dict(v,attributes={**v['attributes'],'mc_Entity':(0,0,0,0)}) for v in water])
    blocked=f.draw(probeMode=22,**args)
    check('opaque replacement blocks caustic light',blocked[:,:,:3].max()<1e-7,float(blocked[:,:,:3].max()))
    np.savez(OUT/'water_focusing_raw.npz',flat=flat,waves=waves)
    save_image('water_focusing.png',[flat,waves,off])

if __name__=='__main__':
    mode=sys.argv[1];globals()[mode]()
    (OUT/(mode+'_v064.json')).write_text(json.dumps({'all_passed':True,'checks':checks,'renderer':'Mesa llvmpipe OpenGL 4.5; not Minecraft'},indent=2)+'\n')
