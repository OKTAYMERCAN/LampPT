#!/usr/bin/env python3
"""Sparse RGB samples on the HRR grid and moving textured diffuse surfaces.

The input has a known mean. Correlated 2x2 footprints model HRR reconstruction,
unlike the older independent exponential-noise fixture. No image is retouched.
Run both releases with --pack /absolute/path/to/shaders and distinct --label.
"""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
import gl_runtime as rt
from pipeline_routing import Pipeline

ap=argparse.ArgumentParser();ap.add_argument('--pack',type=Path);ap.add_argument('--label',default='v072')
ap.add_argument('--frames',type=int,default=64);args=ap.parse_args()
if args.pack:rt.ROOT=args.pack.resolve()
OUT=Path(__file__).parent/'ptgi-evidence';OUT.mkdir(exist_ok=True)
w,h=240,144;report={}
rt.uniforms.update(gbufferPreviousModelView=np.eye(4),gbufferPreviousProjection=rt.projection)
rt.values.update(cameraPosition=(0.,0.,0.),previousCameraPosition=(0.,0.,0.),isEyeInWater=0)
const=lambda v:rt.texture(np.broadcast_to(v,(h,w,len(v))).copy())
def save(name,a):
    # Same display curve on reference and result, never an extra denoiser.
    a=np.maximum(a[::-1,:,:3],0);a=np.clip(a*(2.51*a+.03)/(a*(2.43*a+.59)+.14),0,1)
    a=np.where(a<=.0031308,a*12.92,1.055*a**(1/2.4)-.055)
    Image.fromarray(np.uint8(a*255+.5)).save(OUT/(args.label+'-'+name+'.png'))

for name,moving,slanted in [('static',False,False),('moving',True,False),('slanted',True,True)]:
    options={'PT_RESOLUTION':40,'PT_TEMPORAL':1,'PT_DENOISE':1,'VOLUMETRIC_CLOUDS':0,
             'PT_AIR_DENSITY':'0.000','PT_VOLUMETRICS':0,'PT_SHARPEN':0}
    normal=np.array([.58,.21,.787] if slanted else [0.,0.,1.]);normal/=np.linalg.norm(normal)
    initial={'depthtex1':rt.texture(np.ones((h,w))*rt.depth_for_z(-4)),
             'colortex1':const([*(normal*.5+.5),1]),'colortex4':const([.75,.04,0,0]),'colortex10':const([0,1,.5,.5])}
    p=Pipeline(initial,w,h,options);lw,lh=p.size(2);cw,ch=lw//2,lh//2
    rng=np.random.default_rng(279);errors=[];retentions=[];ages=[];raw_errors=[];temporal_means=[];spatial_means=[]
    yy,xx=np.mgrid[:h,:w]
    # Independent rare colored source events, with nonzero probability in
    # every direction. Expected irradiance is their linear RGB sum.
    colors=np.array([[.55,.025,.008],[.012,.22,.55],[.025,.33,.025]])
    probability=.025;target=colors.sum(0)*.23
    for frame in range(args.frames):
        rt.values['frameCounter']=frame
        shift=frame*.37 if moving else 0.
        # A static textured plane seen under lateral camera translation.
        move=shift*8/(w*rt.scale)
        dirs=np.stack([((xx+.5)/w*2-1)/rt.scale,((yy+.5)/h*2-1)/rt.scale,-np.ones((h,w))],-1)
        t=-(4*normal[2]+move*(normal[0]+.4*normal[1]))/(dirs@normal)
        p.initial['depthtex1']=rt.texture(rt.depth_for_z(-t))
        worldx=dirs[:,:,0]*t+move;worldy=dirs[:,:,1]*t+move*.4
        tex=.45+.25*np.sin(worldx*w*rt.scale/8*.3)*np.cos(worldy*h*rt.scale/8*.27)
        albedo=np.stack([tex,tex*.9,tex*.8],-1)
        linear=np.where(albedo<=.04045,albedo/12.92,((albedo+.055)/1.055)**2.4)
        p.bank[3][p.front[3]]=rt.texture(np.dstack([albedo,np.ones((h,w))]))
        move=shift*8/(w*rt.scale)
        prior=(frame-1)*.37*8/(w*rt.scale) if moving and frame>0 else move
        rt.values.update(cameraPosition=(move,move*.4,0.),previousCameraPosition=(prior,prior*.4,0.))
        hits=rng.random((ch,cw,3))<probability
        coarse=np.einsum('hwc,cd->hwd',hits,colors)*(.23/probability)
        # Use bilinear HRR footprints with the same depth-snapped anchors.
        def anchor(n,full):return np.floor((np.arange(n)+.5)*full/n)
        dx=np.interp(anchor(lw,w),anchor(cw,w),np.arange(cw));dy=np.interp(anchor(lh,h),anchor(ch,h),np.arange(ch))
        bx=dx.astype(int);by=dy.astype(int);fx=(dx-bx)[None,:,None];fy=(dy-by)[:,None,None]
        q0=coarse[by[:,None],bx];q1=coarse[by[:,None],np.minimum(bx+1,cw-1)]
        q2=coarse[np.minimum(by+1,ch-1)[:,None],bx];q3=coarse[np.minimum(by+1,ch-1)[:,None],np.minimum(bx+1,cw-1)]
        raw=(q0*(1-fx)+q1*fx)*(1-fy)+(q2*(1-fx)+q3*fx)*fy
        for buf,data in [(2,raw),(8,raw*.08)]:
            p.bank[buf][p.front[buf]]=rt.texture(np.dstack([data,np.zeros((lh,lw))]))
        p.seed_guides(options)
        temporal=p.pass_('composite2',options)
        for stage in ['composite3','composite4','composite5','composite6']:
            filtered=p.pass_(stage,options)
            if filtered is not None:spatial=filtered[0]
        result=p.pass_('composite7',options)[0][:,:,:3]
        expected=target*linear+target*.08
        if frame==0:save(name+'-first',result)
        if frame>=args.frames//2:
            errors.append(float(np.sqrt(np.mean((result-expected)**2))))
            retentions.append((result.mean((0,1))/expected.mean((0,1))).tolist())
            ages.append(float(temporal[2][3:-3,3:-3,3].mean()))
            temporal_means.append(temporal[0][:,:,:3].mean((0,1))/target)
            spatial_means.append(spatial[:,:,:3].mean((0,1))/target)
            raw_errors.append(float(np.sqrt(np.mean((raw-target)**2))))
    report[name]={'mean_rmse':float(np.mean(errors)),'mean_energy_retention_rgb':np.mean(retentions,0).tolist(),
                  'mean_history_age':float(np.mean(ages)),'raw_irradiance_rmse':float(np.mean(raw_errors)),
                  'temporal_retention_rgb':np.mean(temporal_means,0).tolist(),'spatial_retention_rgb':np.mean(spatial_means,0).tolist(),
                  'frames':args.frames,'display_size':[w,h],'base_grid':[lw,lh],'component_grid':[cw,ch]}
    save(name+'-filtered',result);save(name+'-reference',expected)
    print(name,report[name],flush=True)
if args.pack is None:
    for case in ['static','moving','slanted']:
        assert report[case]['mean_history_age']>24,report[case]
        assert all(.94<v<1.06 for v in report[case]['mean_energy_retention_rgb']),report[case]
        assert report[case]['mean_rmse']<.009,report[case]
    report['all_passed']=True
report['scope']='Synthetic correlated rare-path reconstruction; Mesa OpenGL, not Minecraft'
(OUT/(args.label+'-sparse-noise.json')).write_text(json.dumps(report,indent=2)+'\n')
