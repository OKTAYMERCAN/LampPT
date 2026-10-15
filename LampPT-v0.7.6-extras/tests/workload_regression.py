#!/usr/bin/env python3
"""Count real production BVH queries, using a test-only SSBO instrumentation.
No profiling buffer or atomics are included in the shipped runtime shaders.
"""
import ctypes as C,json
from pathlib import Path
import numpy as np
import gl_runtime as rt
from world_runtime import gl
from pipeline_routing import Pipeline
import scene_review as s
out=Path(__file__).parent/'ptgi-evidence';records={}
original=rt.source
marker='SceneHit traceWorld(vec3 origin,vec3 direction,float maxDistance,ivec3 unused,bool anyHit){'
def instrument(path,options=None):
 text=original(path,options)
 if marker in text:
  text=text.replace(marker,'layout(std430,binding=5) buffer LampPTTestCounter { uint queryCount; uint visitCount; uint cameraCount; uint padding; };\n'+marker+'atomicAdd(queryCount,1u);')
  text=text.replace('SceneNode current=sceneNodes[node];','atomicAdd(visitCount,1u);SceneNode current=sceneNodes[node];')
  text=text.replace('PtRadiance ptIntegrateComponent(PtGuide guide,inout uint rng,int component){','PtRadiance ptIntegrateComponent(PtGuide guide,inout uint rng,int component){atomicAdd(cameraCount,1u);')
 return text
rt.source=instrument
counter=rt.U();gl['GenBuffers'](1,C.byref(counter));gl['BindBuffer'](0x90D2,counter.value)
gl['BufferData'](0x90D2,16,np.zeros(4,np.uint32).ctypes.data,0x88E8)
gl['BindBufferBase'](0x90D2,5,counter.value)
oldpass=Pipeline.pass_
def measured(self,name,options):
 if name=='composite1':
  gl['BindBuffer'](0x90D2,counter.value);gl['BufferData'](0x90D2,16,np.zeros(4,np.uint32).ctypes.data,0x88E8)
 values=oldpass(self,name,options)
 if name=='composite1':
  gl['MemoryBarrier'](0x2000);gl['Finish']();a=np.empty(4,np.uint32)
  gl['BindBuffer'](0x90D2,counter.value);gl['GetBufferSubData'](0x90D2,0,a.nbytes,a.ctypes.data)
  assert gl['GetError']()==0,'OpenGL error in attached compute/draw flow'
  frame_records.append(a[:3].tolist())
 return values
Pipeline.pass_=measured
s.W,s.H=127,75;s.P=np.array(rt.projection,copy=True);s.P[0,0]*=s.H/s.W
rt.uniforms.update(gbufferProjection=s.P,gbufferProjectionInverse=np.linalg.inv(s.P))
for hrr in [0,1]:
 frame_records=[]
 opts={'GEOMETRY_BUDGET':65536,'shadowMapResolution':128,'PT_RESOLUTION':40,'DITHER':0,'BLOOM_ENABLED':0,'CLOUD_WIND_SPEED':'0.0',**{k:hrr for k in ['HRR_SHADOWS','HRR_GI','HRR_REFLECTIONS','HRR_CLOUDS']}}
 result,*_=s.render(opts,sun=(.3,.9,.2),frames=4)
 records[str(hrr)]=dict(zip(['rays','node_visits','camera_estimators'],np.mean(frame_records,axis=0).tolist()))
 print('WORKLOAD',hrr,records[str(hrr)],flush=True)
assert records['1']['rays']<records['0']['rays']*.7,records
assert records['1']['node_visits']<records['0']['node_visits']*.7,records
(out/'workload_v066.json').write_text(json.dumps({'all_passed':True,'counts':records,'scope':'Instrumented production camera compute and merge on synthetic Mesa scene. Excludes BVH build and filtering.'},indent=2)+'\n')
