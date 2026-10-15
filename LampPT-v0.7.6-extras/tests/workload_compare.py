#!/usr/bin/env python3
"""Count production ray queries in a fixed real-mesh synthetic frame.

Instrumentation exists only in this harness. Counts are deterministic work
metrics, not FPS. Use --pack to compare the delivered baseline sequentially.
"""
import argparse,ctypes as C,json,re
from pathlib import Path
import numpy as np
import gl_runtime as rt
ap=argparse.ArgumentParser();ap.add_argument('--pack',type=Path);ap.add_argument('--label',default='v072');ap.add_argument('--shared',type=int,choices=[0,1]);ap.add_argument('--profile',choices=['LOW','MED','HIGH','ULTRA']);ap.add_argument('--frames',type=int,default=8);args=ap.parse_args()
if args.pack:rt.ROOT=args.pack.resolve()/'shaders'
from world_runtime import gl
from pipeline_routing import Pipeline
import scene_review as s
out=Path(__file__).parent/'ptgi-evidence'
original=rt.source
marker='SceneHit traceWorld(vec3 origin,vec3 direction,float maxDistance,ivec3 unused,bool anyHit){'
def instrument(path,options=None):
    text=original(path,options)
    if marker in text:
        text=text.replace(marker,'layout(std430,binding=5) buffer LampPTTestCounter { uint queryCount; uint visitCount; uint cameraCount; uint padding; };\n'+marker+'atomicAdd(queryCount,1u);')
        assert 'visits++;' in text
        text=text.replace('visits++;','visits++;atomicAdd(visitCount,1u);')
        text=text.replace('PtRadiance ptIntegrateComponent(PtGuide guide,inout uint rng,int component){','PtRadiance ptIntegrateComponent(PtGuide guide,inout uint rng,int component){atomicAdd(cameraCount,1u);')
    return text
rt.source=instrument
counter=rt.U();gl['GenBuffers'](1,C.byref(counter));gl['BindBuffer'](0x90D2,counter.value)
gl['BufferData'](0x90D2,16,np.zeros(4,np.uint32).ctypes.data,0x88E8)
gl['BindBufferBase'](0x90D2,5,counter.value)
oldpass=Pipeline.pass_;frame_records=[]
def measured(self,name,options):
    if name=='composite1':
        gl['BindBuffer'](0x90D2,counter.value);gl['BufferData'](0x90D2,16,np.zeros(4,np.uint32).ctypes.data,0x88E8)
    values=oldpass(self,name,options)
    if name=='composite1':
        gl['MemoryBarrier'](0x2000);gl['Finish']();a=np.empty(4,np.uint32)
        gl['BindBuffer'](0x90D2,counter.value);gl['GetBufferSubData'](0x90D2,0,a.nbytes,a.ctypes.data)
        assert gl['GetError']()==0
        frame_records.append(a[:3].tolist())
    return values
Pipeline.pass_=measured
s.W,s.H=127,75;s.P=np.array(rt.projection,copy=True);s.P[0,0]*=s.H/s.W
rt.uniforms.update(gbufferProjection=s.P,gbufferProjectionInverse=np.linalg.inv(s.P))
opts={'GEOMETRY_BUDGET':65536,'shadowMapResolution':128,'PT_RESOLUTION':40,'DITHER':0,'BLOOM_ENABLED':0,'CLOUD_WIND_SPEED':'0.0'}
if args.profile:
    profile=dict(v.split(':',1) for v in re.search(r'^profile\.'+args.profile+r'=(.*)$',(rt.ROOT/'shaders.properties').read_text(),re.M)[1].split())
    # Equal tiny fixture storage isolates transport from memory/capture costs.
    opts={**profile,**{k:v for k,v in opts.items() if k!='PT_RESOLUTION'}}
if args.shared is not None:opts['PT_SHARED_PATHS']=args.shared
result,*_=s.render(opts,sun=(.3,.9,.2),frames=args.frames)
assert np.isfinite(result).all()
records=dict(zip(['ray_queries','node_entries','camera_estimators'],np.mean(frame_records,axis=0).tolist()))
report={'profile':args.profile,'options':opts,'label':args.label,'mean_work_per_frame':records,'frame_counts':frame_records,'all_finite':True,'scope':'Instrumented camera computes + HRR repair in actual synthetic mesh. Excludes BVH construction and post filters. Not Minecraft FPS.'}
(out/(args.label+'-workload.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
