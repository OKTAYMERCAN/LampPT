#!/usr/bin/env python3
"""Production transport reconstruction against full-resolution analytic fields."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
import gl_runtime as rt
from pipeline_routing import Pipeline
OUT=Path(__file__).parent/'ptgi-evidence';records={}
rt.uniforms.update(gbufferPreviousModelView=np.eye(4),gbufferPreviousProjection=rt.projection)
rt.values.update(cameraPosition=(0.,0.,0.),previousCameraPosition=(0.,0.,0.),isEyeInWater=0,frameCounter=0)

def run(scale,detail=1,field='constant',sharp=0,noise=0.,w=127,h=75):
    yy,xx=np.mgrid[:h,:w]
    texture=np.where(((xx//2+yy//3)%2)[...,None],np.array([.72,.38,.15]),np.array([.22,.08,.025]))
    linear=np.where(texture<=.04045,texture/12.92,((texture+.055)/1.055)**2.4)
    D=np.ones((h,w,3))*np.array([.8,.6,.4]);S=np.zeros((h,w,3))
    depth=np.full((h,w),-4.)
    if field=='smooth':D*= (.9+.65*np.sin((xx+.5)*.13)*np.cos((yy+.5)*.09))[...,None]
    if field=='edge':
        edge=xx>w*.45+yy*.28
        D[edge]=[.07,.08,.10];depth[edge]=-6.
    if field=='specular':
        texture[:]=.7;linear[:]=((.7+.055)/1.055)**2.4;D[:]=0
        S[:]=(.07+.4*np.exp(-((xx-w*.53)/2.2)**2))[...,None]
    data={
        'depthtex1':rt.texture(rt.depth_for_z(depth)),
        'colortex0':rt.texture(np.dstack([texture,np.ones((h,w))])),
        'colortex1':rt.texture(np.broadcast_to([.5,.5,1,1],(h,w,4))),
        'colortex3':rt.texture(np.dstack([texture,np.ones((h,w))])),
        'colortex4':rt.texture(np.broadcast_to([.2,.04,0,0],(h,w,4))),
        'colortex10':rt.texture(np.broadcast_to([0,1,0,1],(h,w,4)))}
    opts={'PT_RESOLUTION':scale,'PT_UPSCALE_FILTER':detail,'PT_SHARPEN':sharp,'PT_SHARPNESS':'0.8',
          'PT_TEMPORAL':0,'PT_DENOISE':0,'PT_VOLUMETRICS':0,'PT_AIR_DENSITY':'0.0'}
    p=Pipeline(data,w,h,opts);lw,lh=p.size(2)
    ly,lx=np.mgrid[:lh,:lw];fx=np.minimum(((lx+.5)/lw*w).astype(int),w-1);fy=np.minimum(((ly+.5)/lh*h).astype(int),h-1)
    for target,values in [(2,D[fy,fx]),(8,S[fy,fx])]:
        p.bank[target][p.front[target]]=rt.texture(np.dstack([values,np.full((lh,lw),noise)]))
    p.pass_('composite2',opts)
    if noise:
        # Explicit known uncertainty to check the sharpen guard independently
        # of one-sample temporal variance bootstrapping.
        for target in [2,8]:
            values=D[fy,fx] if target==2 else S[fy,fx]
            p.bank[target][p.front[target]]=rt.texture(np.dstack([values,np.full((lh,lw),noise)]))
    assert p.pass_('composite3',opts) is None and p.pass_('composite4',opts) is None
    image=p.pass_('composite5',opts)[0][:,:,:3]
    after=p.pass_('composite6',opts)
    if sharp:image=after[0][:,:,:3]
    else:assert after is None
    return image,D*linear+S,p

def check(name,ok,info):
    assert ok,(name,info)
    records[name]=info;print('UPSCALE PASS',name,info,flush=True)
for scale in [33,40,50,59,67,77,100]:
    a,ref,p=run(scale);error=float(abs(a-ref).max())
    check('constant texture '+str(scale),error<.003,{'max_error':error,'transport_size':p.size(2)})
    a,ref,_=run(scale,field='edge');yy,xx=np.mgrid[:75,:127]
    distance=np.abs(xx-127*.45-yy*.28)
    # No upscale can recover a surface that has no nearby traced sample.
    # This fixture has samples on both sides of a large depth discontinuity.
    interior=distance>4
    check('depth edge isolation '+str(scale),float(abs(a-ref)[interior].max())<.004,float(abs(a-ref)[interior].max()))
    low,ref,_=run(scale,detail=0,field='smooth');hi,_,_=run(scale,detail=1,field='smooth')
    crop=np.s_[4:-4,4:-4]
    e0=float(np.sqrt(np.mean((low[crop]-ref[crop])**2)));e1=float(np.sqrt(np.mean((hi[crop]-ref[crop])**2)))
    check('smooth-field reconstruction '+str(scale),e1<=e0*1.05+1e-5,{'fast_rmse':e0,'detail_rmse':e1})
    if scale==40:
        rgb=np.concatenate([ref,low,hi],axis=1);rgb=rgb/(1+rgb)
        Image.fromarray(np.uint8(np.clip(rgb**(1/2.2),0,1)*255)).save(OUT/'v065-upscale-comparison.png')
base,_,_=run(40,field='specular');sharp,_,_=run(40,field='specular',sharp=1);guarded,_,_=run(40,field='specular',sharp=1,noise=20.)
change=float(np.max(abs(sharp-base)));noise_change=float(np.max(abs(guarded-base)))
check('adaptive sharpen changes signal',change>.001,change)
check('sharpen remains in signal bounds',sharp.min()>=base.min()-.001 and sharp.max()<=base.max()+.001,[float(sharp.min()),float(sharp.max())])
check('noise guard suppresses sharpening',noise_change<change*.15,{'clean_delta':change,'noisy_delta':noise_change})
(OUT/'upscale_v065.json').write_text(json.dumps({'all_passed':True,'checks':records,'scope':'Actual Mesa GLSL on analytic input fields; not Minecraft'},indent=2)+'\n')
