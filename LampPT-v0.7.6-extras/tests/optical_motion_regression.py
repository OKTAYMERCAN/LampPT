#!/usr/bin/env python3
"""Moving camera behind a clear pane: analytic receiver, production GLSL.

Tests parallax, texture history, low-FPS response and packed guide persistence.
The pane is 2 blocks away; the colored receiver is 16 blocks away. A fixed
pane-depth reprojection is a negative control. This is not Minecraft footage.
"""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
import gl_runtime as rt
from pipeline_routing import Pipeline
from buffer_encoding import normal24,rgb24,material24

ap=argparse.ArgumentParser();ap.add_argument('--baseline',type=Path);args=ap.parse_args()
native=rt.ROOT;out=Path(__file__).parent/'ptgi-evidence';out.mkdir(exist_ok=True)
w,h=192,112
options={'PT_RESOLUTION':50,'PT_TEMPORAL':1,'PT_HISTORY':64,'DITHER':0,
         'VOLUMETRIC_CLOUDS':0,'PT_AIR_DENSITY':'0.000','PT_VOLUMETRICS':0}
const=lambda v:rt.texture(np.broadcast_to(v,(h,w,len(v))).copy())
normal=normal24((0,0,1))

def run(root,label,with_noise=False):
    rt.ROOT=root
    initial={'depthtex1':rt.texture(np.ones((h,w))*rt.depth_for_z(-16)),
             'colortex1':const([.5,.5,1,1]),'colortex3':const([1,1,1,1]),
             'colortex4':const([.75,.04,0,0]),
             'colortex5':const([material24([.001,.04,0,2]),0,normal,1]),
             'colortex15':const([rgb24([1,1,1]),2,normal,1])}
    p=Pipeline(initial,w,h,options);lw,lh=p.size(2)
    yy,xx=np.mgrid[:lh,:lw]
    anchors_x=np.floor((xx+.5)*w/lw);anchors_y=np.floor((yy+.5)*h/lh)
    rays=np.stack([((anchors_x+.5)/w*2-1)/rt.scale,
                   ((anchors_y+.5)/h*2-1)/rt.scale,-np.ones((lh,lw))],-1)
    length=np.linalg.norm(rays,axis=-1)*16
    rt.uniforms.update(gbufferPreviousModelView=np.eye(4),gbufferPreviousProjection=rt.projection,
                       gbufferModelViewInverse=np.eye(4),gbufferProjectionInverse=np.linalg.inv(rt.projection))
    rng=np.random.default_rng(20261007);errors=[];raw_errors=[];contrast=[];flicker=[];last_error=None
    previous=0.0
    for frame in range(48):
        camera=max(0,frame-15)*.075
        x=rays[:,:,0]*16+camera;y=rays[:,:,1]*16
        pattern=.5+.5*np.sin(x*3.0)*np.cos(y*2.0)
        color=np.stack([.09+.55*pattern,.15+.10*pattern,.65-.55*pattern],-1)
        # Quantization is the actual runtime guide representation.
        quant=np.rint(color*255).astype(np.uint32)
        packed=quant[:,:,0]+(quant[:,:,1]<<8)+(quant[:,:,2]<<16)
        color=quant/255.0
        expected=color*.7
        signal=expected.copy()
        if with_noise:signal*=rng.exponential(1.0,(lh,lw,1))
        guide=np.dstack([np.full((lh,lw),normal),packed,length,
                         np.full((lh,lw),material24([.001,.04,0,2]))])
        rt.values.update(frameCounter=frame,frameTime=1/12,cameraPosition=(camera,0.,0.),
                         previousCameraPosition=(previous,0.,0.),isEyeInWater=0)
        p.bank[2][p.front[2]]=rt.texture(np.zeros((lh,lw,4)))
        p.bank[8][p.front[8]]=rt.texture(np.dstack([signal,np.zeros((lh,lw))]))
        p.bank[6][p.front[6]]=rt.texture(guide)
        temp=p.pass_('composite2',options)
        if label=='current':
            assert np.array_equal(temp[2][:,:,:3],guide[:,:,:3].astype(np.float32)), 'Optical history lost packed precision'
            assert np.max(np.abs(temp[0][:,:,:3]))==0, 'Guide metadata leaked into diffuse radiance'
        for stage in ['composite3','composite4','composite5','composite6']:result=p.pass_(stage,options)
        filtered=result[1][:,:,:3]
        assert np.isfinite(filtered).all()
        if frame>=24:
            error=(filtered-expected)[4:-4,5:-5]
            errors.append(float(np.mean(error*error)))
            raw_errors.append(float(np.mean((signal-expected)[4:-4,5:-5]**2)))
            contrast.append(float(np.std(filtered[:,:,0])/np.std(expected[:,:,0])))
            if last_error is not None:flicker.append(float(np.mean((error-last_error)**2)))
            last_error=error
        previous=camera
    for name,data in [('result',filtered),('reference',expected)]:
        Image.fromarray(np.uint8(np.clip(data[::-1],0,1)**(1/2.2)*255+.5)).save(out/f'v076-optical-{label}-{with_noise}-{name}.png')
    return {'rmse':float(np.sqrt(np.mean(errors))),'raw_rmse':float(np.sqrt(np.mean(raw_errors))),
            'contrast_retention':float(np.mean(contrast)),'flicker_rmse':float(np.sqrt(np.mean(flicker)))}

report={'scope':__doc__,'moving_camera_fps':12}
if args.baseline:report['old']=run(args.baseline.resolve(),'old')
report['current']=run(native,'current')
report['current_noisy']=run(native,'current',True)
assert report['current']['rmse']<.008,report
assert .95<report['current']['contrast_retention']<1.05,report
assert report['current_noisy']['rmse']<report['current_noisy']['raw_rmse']*.7,report
if 'old' in report:assert report['current']['rmse']<report['old']['rmse']*.35,report
report['all_passed']=True
(out/'v076-optical-motion.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
