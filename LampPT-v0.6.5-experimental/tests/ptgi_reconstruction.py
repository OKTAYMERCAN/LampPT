#!/usr/bin/env python3
"""Image-quality regression using production GLSL and known lighting fields.

Synthetic noisy irradiance is intentional: its exact answer is known, so noise
reduction cannot pass by blurring texture or losing real illumination edges.
The optional prior-release run is a negative control, not a Minecraft screenshot.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image
import gl_runtime as rt
from pipeline_routing import Pipeline

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline',type=Path)
parser.add_argument('--evidence',type=Path,default=Path(__file__).parent/'ptgi-evidence')
args=parser.parse_args()
if args.baseline:rt.ROOT=args.baseline.resolve()
args.evidence.mkdir(exist_ok=True,parents=True)
split='ptIntegrateParts' in (rt.ROOT/'lib/ptgi/render.glsl').read_text()
label='current' if split else 'v050'
rt.uniforms.update(gbufferPreviousModelView=np.eye(4),gbufferPreviousProjection=rt.projection)
rt.values.update(cameraPosition=(0.,0.,0.),previousCameraPosition=(0.,0.,0.),isEyeInWater=0)
metrics={}

def save(name,a):
    # Display conversion only, with no sharpening or image editing.
    a=np.clip(a[::-1,:,:3],0,1)
    a=np.where(a<=.0031308,a*12.92,1.055*np.power(a,1/2.4)-.055)
    Image.fromarray(np.uint8(a*255+.5)).save(args.evidence/(label+'-'+name+'.png'))

def run(w,h,frames=1,noise=False,denoise=True,temporal=True,texture=False,emitter=False,
        edge=False,specular=False,full=False,disocclusion=False):
    yy,xx=np.mgrid[:h,:w]
    albedo=np.ones((h,w,3))*.7
    if texture:
        # Pixel-scale detail on a smooth dielectric used to be blurred with HDR.
        grain=((xx//2+yy//3)%2)[...,None]
        albedo=np.array([.32,.13,.045])*(1-grain)+np.array([.85,.57,.22])*grain
    linear=np.where(albedo<=.04045,albedo/12.92,((albedo+.055)/1.055)**2.4)
    material=np.empty((h,w,4));material[:]=[.15,.04,0,0]
    emission=np.zeros((h,w,3))
    if emitter:
        # Arbitrary emissive PBR artwork: no block-wide constant color shortcut.
        material[:,:,2]=.2;material[:,:,3]=8
        emission=linear*.2*4.0  # EMISSIVE_STRENGTH overridden below.
    D=np.ones((h,w,3))*np.array([.7,.55,.4])
    if edge:D[xx>=w//2]*=3
    S=np.ones((h,w,3))*.015
    if specular:
        D[:]=0;S[:]=.03;S[(xx>=w//2)&(xx<w//2+4)]=[1.2,.7,.3]
    if emitter:D[:]=0;S[:]=0
    expected=D*linear+S+emission
    options={'PT_TEMPORAL':int(temporal),'PT_DENOISE':int(denoise),'PT_AIR_DENSITY':'0.000',
             'PT_VOLUMETRICS':0,'PT_RESOLUTION':100 if full else 50,'PT_HISTORY':32,'EMISSIVE_STRENGTH':'4.0',
             'LIGHT_SATURATION':'1.0','DITHER':0,'NORMAL_MAPS':0}
    const=lambda v:rt.texture(np.broadcast_to(v,(h,w,len(v))).copy())
    data={'depthtex1':rt.texture(np.ones((h,w))*rt.depth_for_z(-4.)),
          'colortex0':rt.texture(np.dstack([albedo,np.ones((h,w))])),
          'colortex1':const([.5,.5,1,1]),'colortex3':rt.texture(np.dstack([albedo,np.ones((h,w))])),
          'colortex4':rt.texture(material),'colortex10':const([0,1,0,1])}
    pipeline=Pipeline(data,w,h,options)
    lw,lh=pipeline.size(2)
    ly,lx=np.mgrid[:lh,:lw];fx=np.minimum(((lx+.5)/lw*w).astype(int),w-1);fy=np.minimum(((ly+.5)/lh*h).astype(int),h-1)
    rng=np.random.default_rng(317)
    first=None;raw_error=None;history=None
    for frame in range(frames):
        rt.values['frameCounter']=frame
        d=D[fy,fx].copy();s=S[fy,fx].copy()
        if noise:
            d*=rng.exponential(1.,(lh,lw,1));s*=rng.exponential(1.,(lh,lw,1))
        if disocclusion and frame==frames-1:
            # A newly exposed surface at a different depth must reject old light.
            pipeline.initial['depthtex1']=rt.texture(np.ones((h,w))*rt.depth_for_z(-2.))
            d[:]=0;s[:]=0;expected[:]=0
        if split:
            raw={2:np.dstack([d,np.zeros((lh,lw))]),8:np.dstack([s,np.zeros((lh,lw))])}
        else:raw={2:np.dstack([d*linear[fy,fx]+s+emission[fy,fx],np.ones((lh,lw))])}
        if frame==0:
            raw_error=float(np.sqrt(np.mean(((d*linear[fy,fx]+s)-(D[fy,fx]*linear[fy,fx]+S[fy,fx]))**2)))
        for target,value in raw.items():pipeline.bank[target][pipeline.front[target]]=rt.texture(value)
        temporal_result=pipeline.pass_('composite2',options)
        history=temporal_result[2 if split else 1]
        for stage in ('composite3','composite4'):pipeline.pass_(stage,options)
        result=pipeline.pass_('composite5',options)[0][:,:,:3]
        if first is None:first=result.copy()
    return result,expected,first,raw_error,history

# Texture and visible emission must survive independently of the light filter.
for name,kw in [('texture',{'texture':True}),('emission',{'texture':True,'emitter':True})]:
    result,expected,_,_,_=run(96,64,frames=16,**kw)
    error=float(np.max(abs(result-expected)));metrics[name+'_max_error']=error
    save(name,result);save(name+'-reference',expected)
    if split:assert error<.003,(name,error)

# Static reprojection may not gradually diffuse thin reflection features.
# Spatial reconstruction is off here to isolate history from all denoisers.
for w,h in [(96,64),(127,75)]:
    result,expected,first,_,history=run(w,h,frames=32,denoise=False,specular=True)
    drift=float(np.max(abs(result-first)));metrics['stationary_drift_'+str((w,h))]=drift
    save('stationary-'+str(w),result)
    if split:assert drift<.003,(w,h,drift)

# A known shadow edge with independent exponential Monte Carlo-like noise.
result,expected,first,raw_error,history=run(96,64,frames=32,noise=True,edge=True,texture=True)
error=float(np.sqrt(np.mean((result-expected)**2)))
metrics.update(noisy_raw_rmse=raw_error,filtered_rmse=error,noise_rmse_ratio=error/raw_error,
               first_frame_rmse=float(np.sqrt(np.mean((first-expected)**2))))
save('noisy-frame-1',first);save('filtered-frame-32',result);save('lighting-reference',expected)
if split:assert error<raw_error*.3,metrics

result,expected,_,_,history=run(96,64,frames=8,disocclusion=True)
metrics['disocclusion_max_error']=float(abs(result-expected).max())
metrics['disocclusion_history_age']=float(history[:,:,3].max())
if split:assert metrics['disocclusion_max_error']<.003 and metrics['disocclusion_history_age']==1

if split:
    result,expected,_,_,_=run(95,63,frames=4,texture=True,full=True)
    metrics['full_resolution_texture_max_error']=float(abs(result-expected).max())
    assert metrics['full_resolution_texture_max_error']<.003
    # Controls really bypass filters; this also catches accidental preset forcing.
    a,_,_,_,_=run(96,64,noise=True,denoise=False,temporal=False)
    b,_,_,_,_=run(96,64,noise=True,denoise=True,temporal=False)
    metrics['spatial_toggle_difference']=float(abs(a-b).max())
    assert metrics['spatial_toggle_difference']>.02
if not split:
    assert metrics['texture_max_error']>.1 and metrics['stationary_drift_(96, 64)']>.01, 'Prior-release negative control did not reproduce blur'
metrics['comparison_role']='corrected implementation' if split else 'negative control reproducing known blur'
metrics.update(all_passed=True,renderer='synthetic Mesa OpenGL; not Minecraft',release=label)
(args.evidence/(label+'-reconstruction.json')).write_text(json.dumps(metrics,indent=2)+'\n')
print(json.dumps(metrics,indent=2),flush=True)
