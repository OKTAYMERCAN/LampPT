#!/usr/bin/env python3
"""Night-like rare paths on a grazing floor during translation and rotation.

Runs production temporal/spatial GLSL with analytically known first-hit guides.
This isolates reconstruction, not the path sampler or Minecraft performance.
The old front-facing-plane test did not exercise floor depth variation.
"""
import argparse,json,re
from pathlib import Path
import numpy as np
from PIL import Image
import gl_runtime as rt
from pipeline_routing import Pipeline
ap=argparse.ArgumentParser();ap.add_argument('--pack',type=Path);ap.add_argument('--label',default='v072')
ap.add_argument('--frames',type=int,default=80);ap.add_argument('--resolution',type=int,default=40)
args=ap.parse_args()
if args.pack:rt.ROOT=args.pack.resolve()
OUT=Path(__file__).parent/'ptgi-evidence';OUT.mkdir(exist_ok=True)
w,h=240,144;yy,xx=np.mgrid[:h,:w]
dirs=np.stack([((xx+.5)/w*2-1)/rt.scale,((yy+.5)/h*2-1)/rt.scale,-np.ones((h,w))],-1)
const=lambda v:rt.texture(np.broadcast_to(v,(h,w,len(v))).copy())
options={'PT_RESOLUTION':args.resolution,'PT_HISTORY':64,'PT_TEMPORAL':1,'PT_DENOISE':1,
         'PT_DENOISE_PASSES':4,'PT_DENOISE_RADIUS':1,'VOLUMETRIC_CLOUDS':0,
         'PT_AIR_DENSITY':'0.000','PT_VOLUMETRICS':0,'PT_SHARPEN':0}
p=Pipeline({'colortex4':const([.75,.04,0,0]),'colortex10':const([0,1,.5,.5])},w,h,options)
lw,lh=p.size(2);cw,ch=lw//2,lh//2
anchor=lambda n,full:np.floor((np.arange(n)+.5)*full/n).astype(int)
dx=np.interp(anchor(lw,w),anchor(cw,w),np.arange(cw));dy=np.interp(anchor(lh,h),anchor(ch,h),np.arange(ch))
bx=dx.astype(int);by=dy.astype(int);fx=(dx-bx)[None,:,None];fy=(dy-by)[:,None,None]
rng=np.random.default_rng(1071);errors=[];flicker=[];energy=[];ages=[];prior_error=None
colors=np.array([[.6,.05,.01],[.012,.3,.6],[.07,.35,.03]])*.11
probability=.025;target=colors.sum(0);spec_fraction=.3
prior_cam=np.zeros(3);prior_matrix=np.eye(4)

def camera(frame):
    # Combined walking + yaw/pitch; projected motion varies over the floor.
    yaw=np.deg2rad(4*np.sin(frame*.045));pitch=np.deg2rad(-12+2*np.sin(frame*.08))
    ry=np.array([[np.cos(yaw),0,np.sin(yaw)],[0,1,0],[-np.sin(yaw),0,np.cos(yaw)]])
    rx=np.array([[1,0,0],[0,np.cos(pitch),-np.sin(pitch)],[0,np.sin(pitch),np.cos(pitch)]])
    inv=np.eye(4);inv[:3,:3]=ry@rx
    return np.array([frame*.018,0.,-frame*.035]),inv

def guides(frame,floor_height=-1.6):
    cam,inv=camera(frame);rd=dirs@inv[:3,:3].T
    with np.errstate(divide='ignore',invalid='ignore'):
        floor=(floor_height-cam[1])/rd[:,:,1]
    floor=np.where(floor>0,floor,np.inf);wall=(-25-cam[2])/rd[:,:,2]
    isfloor=floor<wall;t=np.minimum(floor,wall);pos=cam+rd*t[:,:,None]
    normals=np.where(isfloor[:,:,None],np.array([0.,1.,0.]),np.array([0.,0.,1.]))@inv[:3,:3]
    # Dark stone texture; sharp albedo must survive demodulated filtering.
    tex=.27+.08*np.sin(pos[:,:,0]*5)*np.cos(pos[:,:,2]*5)
    albedo=np.stack([tex,tex*.92,tex*.78],-1)
    linear=np.where(albedo<=.04045,albedo/12.92,((albedo+.055)/1.055)**2.4)
    p.initial['depthtex1']=rt.texture(rt.depth_for_z(-t))
    p.bank[1][p.front[1]]=rt.texture(np.dstack([normals*.5+.5,np.ones((h,w))]))
    p.bank[3][p.front[3]]=rt.texture(np.dstack([albedo,np.ones((h,w))]))
    return cam,inv,isfloor,linear

def save(name,a):
    a=np.maximum(a[::-1,:,:3]*8,0);a=a/(1+a);a=np.clip(a,0,1)**(1/2.2)
    Image.fromarray(np.uint8(a*255+.5)).save(OUT/(args.label+'-night-motion-'+name+'.png'))

for frame in range(args.frames):
    cam,inv,floor,linear=guides(frame)
    if frame==0:prior_cam=cam;prior_matrix=np.linalg.inv(inv)
    rt.uniforms.update(gbufferModelViewInverse=inv,gbufferPreviousModelView=prior_matrix,gbufferPreviousProjection=rt.projection)
    rt.values.update(frameCounter=frame,cameraPosition=tuple(cam),previousCameraPosition=tuple(prior_cam),isEyeInWater=0)
    coarse=np.einsum('hwc,cd->hwd',rng.random((ch,cw,3))<probability,colors)/probability
    q0=coarse[by[:,None],bx];q1=coarse[by[:,None],np.minimum(bx+1,cw-1)]
    q2=coarse[np.minimum(by+1,ch-1)[:,None],bx];q3=coarse[np.minimum(by+1,ch-1)[:,None],np.minimum(bx+1,cw-1)]
    raw=(q0*(1-fx)+q1*fx)*(1-fy)+(q2*(1-fx)+q3*fx)*fy
    for buf,data in [(2,raw),(8,raw*spec_fraction)]:p.bank[buf][p.front[buf]]=rt.texture(np.dstack([data,np.zeros((lh,lw))]))
    p.seed_guides(options);temporal=p.pass_('composite2',options)
    for stage in ['composite3','composite4','composite5','composite6']:p.pass_(stage,options)
    result=p.pass_('composite7',options)[0][:,:,:3];expected=target*linear+target*spec_fraction
    error=result-expected
    # Stay away from edges/disocclusions for a fair stationary-world metric.
    mask=floor&(xx>24)&(xx<w-24)&(yy>12)&(yy<h*.58)
    lowmask=mask[anchor(lh,h)[:,None],anchor(lw,w)]
    if frame>=args.frames//2:
        errors.append(float(np.sqrt(np.mean(error[mask]**2))))
        energy.append((result[mask].mean(0)/expected[mask].mean(0)).tolist())
        ages.append(float(temporal[2][:,:,3][lowmask].mean()))
        if prior_error is not None:flicker.append(float(np.sqrt(np.mean((error-prior_error)[mask]**2))))
    prior_error=error;prior_cam=cam;prior_matrix=np.linalg.inv(inv)
save('filtered',result);save('reference',expected)
report={'frames':args.frames,'resolution':args.resolution,'mean_rmse':float(np.mean(errors)),
 'temporal_flicker_rmse':float(np.mean(flicker)),'energy_retention_rgb':np.mean(energy,0).tolist(),
 'mean_history_age':float(np.mean(ages)),'display_size':[w,h],'base_size':[lw,lh],
 'scope':'Analytic grazing geometry + synthetic rare night paths; production GLSL on Mesa, not Minecraft'}
# A parallel floor displaced toward the camera must NOT borrow old radiance.
cam,inv,floor,linear=guides(args.frames-1,floor_height=-1.0)
rt.uniforms['gbufferPreviousModelView']=np.linalg.inv(inv)
rt.values.update(cameraPosition=tuple(cam),previousCameraPosition=tuple(cam),frameCounter=args.frames)
for buf in [2,8]:p.bank[buf][p.front[buf]]=rt.texture(np.zeros((lh,lw,4)))
p.seed_guides(options);changed=p.pass_('composite2',options)
mask=floor[anchor(lh,h)[:,None],anchor(lw,w)]
report['displaced_floor_history_max']=float(changed[2][:,:,3][mask].max())
if args.pack is None:
    assert report['mean_history_age']>40,report
    assert report['mean_rmse']<.012,report
    assert all(.85<x<1.15 for x in report['energy_retention_rgb']),report
    assert report['displaced_floor_history_max']==1,report
    report['all_passed']=True
print(json.dumps(report,indent=2),flush=True)
(OUT/(args.label+'-night-motion.json')).write_text(json.dumps(report,indent=2)+'\n')
