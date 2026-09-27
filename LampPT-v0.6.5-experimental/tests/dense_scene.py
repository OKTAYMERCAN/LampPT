#!/usr/bin/env python3
"""Daylight and heavy BVH regression on 178,272 actual triangle records.

The exact same procedural mesh can run against the previous release. Uploading
known captured records isolates build/traversal from the game's chunk streamer.
Small physical fixtures separately exercise the production geometry capture.
"""
import argparse,ctypes as C,json,time
from pathlib import Path
import numpy as np
from ptgi_runtime import Fixture,rt
from world_runtime import gl
parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path);args=parser.parse_args()
if args.baseline:rt.ROOT=args.baseline.resolve()
f=Fixture({'GEOMETRY_BUDGET':262144,'SUN_INTENSITY':'1.0','PT_BOUNCES':1,'PT_SKYLIGHT':0,'EMISSIVE_ENABLED':0})
triangles=[]
def panel(origin,u,v,nu,nv):
    yy,xx=np.mgrid[:nv,:nu];base=np.array(origin)+xx[...,None]*np.array(u)+yy[...,None]*np.array(v)
    a=base.reshape(-1,3);b=a+u;c=b+v;d=a+v
    triangles.extend([np.stack([a,b,c],1),np.stack([a,c,d],1)])
panel((-96,0,-96),(1,0,0),(0,0,1),192,192)
for x in range(-80,81,16):
 for z in range(-80,81,16):
    panel((x,0,z),(1,0,0),(0,1,0),6,12)
    panel((x,0,z+8),(0,1,0),(1,0,0),12,6)
    panel((x,0,z),(0,1,0),(0,0,1),12,8)
    panel((x+6,0,z),(0,0,1),(0,1,0),8,12)
    panel((x,12,z),(1,0,0),(0,0,1),6,8)
    panel((x,0,z),(0,0,1),(1,0,0),8,6)
triangles=np.concatenate(triangles).astype(np.float32)
np.random.default_rng(918).shuffle(triangles)
n=len(triangles);data=np.zeros((n,20),np.float32)
data[:,:3]=triangles[:,0];data[:,4:7]=triangles[:,1];data[:,8:11]=triangles[:,2]
data[:,3]=0;data[:,7]=0;data[:,11]=1;data[:,12]=0;data[:,13:15]=(1,1);data[:,15]=1
packed=data.view(np.uint32);packed[:,16]=0x80b2b2b2;packed[:,18]=0xffffffff;packed[:,19]=191|(10<<8)
subdata=rt.function(rt.G,'glBufferSubData',None,rt.U,C.c_ssize_t,C.c_ssize_t,rt.P)
gl['BindBuffer'](0x90D2,f.world.buffers[1]);header=np.array([n,0,0,0],np.uint32)
subdata(0x90D2,0,16,header.ctypes.data);subdata(0x90D2,16,data.nbytes,data.ctypes.data)
start=time.perf_counter();f.world.collect();build_ms=(time.perf_counter()-start)*1000
kwargs=dict(size=(96,96),probeMode=4,probePosition=(-90.,.01,-90.),probeU=(180.,0.,0.),probeV=(0.,0.,180.),sunPosition=(0.,1.,0.),shadowLightPosition=(0.,1.,0.))
start=time.perf_counter();a=f.draw(**kwargs)[:,:,:3];render_ms=(time.perf_counter()-start)*1000
warm_times=[]
for _ in range(3):
 start=time.perf_counter();f.draw(**kwargs);warm_times.append((time.perf_counter()-start)*1000)
# Independent box footprint oracle: a vertical sun ray is blocked exactly when
# it starts under one of the buildings, and is clear on the outdoor streets.
x=(np.arange(96)+.5)/96*180-90;xx,zz=np.meshgrid(x,x)
blocked=np.zeros((96,96),bool)
for bx in range(-80,81,16):
 for bz in range(-80,81,16):blocked|=(xx>bx)&(xx<bx+6)&(zz>bz)&(zz<bz+8)
open_pixels=~blocked
complete_mean=float(a[open_pixels].mean());occluded_max=float(a[blocked].max())
# Same retained geometry, but report one dropped triangle. The former global
# predicate forced all misses to zero, including every open outdoor street.
flag=np.array([1],np.uint32);gl['BindBuffer'](0x90D2,f.world.buffers[1]);subdata(0x90D2,4,4,flag.ctypes.data)
b=f.draw(**kwargs)[:,:,:3]
overflow_mean=float(b[open_pixels].mean());overflow_wall_max=float(b[blocked].max())
label='v060' if args.baseline else 'v063'
result={'release':label,'triangles':n,'build_dispatches':len(f.world.programs)-1,'complete_daylight_mean':complete_mean,'occluded_max':occluded_max,'overflow_daylight_mean':overflow_mean,'overflow_occluded_max':overflow_wall_max,'software_build_ms':build_ms,'software_first_draw_ms':render_ms,'software_warm_draw_median_ms':float(np.median(warm_times)),'timing_scope':'Mesa CPU software renderer; not GPU/Minecraft FPS'}
print(json.dumps(result,indent=2),flush=True)
assert complete_mean>.4 and occluded_max<.0001,result
if args.baseline:assert overflow_mean==0,result
else:assert abs(overflow_mean-complete_mean)<.0001 and overflow_wall_max<.0001,result
result['all_passed']=True
out=Path(__file__).parent/'ptgi-evidence';out.mkdir(exist_ok=True)
(out/(label+'-dense.json')).write_text(json.dumps(result,indent=2)+'\n')
from PIL import Image
for name,frame in [('complete',a),('overflow',b)]:
 display=np.clip(frame,0,1)**(1/2.2)
 Image.fromarray(np.uint8(display[::-1]*255+.5)).save(out/(label+'-dense-'+name+'.png'))
