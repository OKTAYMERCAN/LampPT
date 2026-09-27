"""Real GL image atomics, SSBO and compute dispatch for the world-space pack."""
import ctypes as C
import re
from pathlib import Path
import numpy as np
import gl_runtime as rt

gl=rt.gl
for name,sig in {
 'TexImage3D':(None,rt.U,rt.I,rt.I,rt.I,rt.I,rt.I,rt.I,rt.U,rt.U,rt.P),
 'GetTexImage':(None,rt.U,rt.I,rt.U,rt.U,rt.P),
 'BindImageTexture':(None,rt.U,rt.U,rt.I,rt.U,rt.I,rt.U,rt.U),
 'GenBuffers':(None,rt.I,rt.P), 'BindBuffer':(None,rt.U,rt.U),
 'BufferData':(None,rt.U,C.c_ssize_t,rt.P,rt.U), 'BindBufferBase':(None,rt.U,rt.U,rt.U),
 'GetBufferSubData':(None,rt.U,C.c_ssize_t,C.c_ssize_t,rt.P),
 'DispatchComputeIndirect':(None,C.c_ssize_t),
 'MemoryBarrier':(None,rt.U), 'DispatchCompute':(None,rt.U,rt.U,rt.U),
}.items():gl[name]=rt.function(rt.G,'gl'+name,*sig)

def link(shaders):
 p=gl['CreateProgram']()
 for s in shaders:gl['AttachShader'](p,s)
 gl['LinkProgram'](p);ok=rt.I();gl['GetProgramiv'](p,0x8B82,C.byref(ok))
 if not ok.value:
  log=C.create_string_buffer(32768);gl['GetProgramInfoLog'](p,len(log),None,log);raise AssertionError(log.value.decode())
 for s in shaders:gl['DeleteShader'](s)
 return p

def compute(name,options):return link([rt.shader(rt.ROOT/(name+'.csh'),0x91B9,options)])

def fragment(path,options=None):
 return link([rt.shader(rt.ROOT/'final.vsh',0x8B31,options or {}),rt.shader(path,0x8B30,options or {})])

class WorldGPU:
 """Production BVH build and terrain capture; size is a legacy fixture argument."""
 def __init__(self,size=64,options=None):
  self.options={'GEOMETRY_BUDGET':65536,**(options or {})}
  self.budget=int(self.options['GEOMETRY_BUDGET']);self.capacity=1<<(self.budget-1).bit_length()
  self.buffers=[]
  for size_bytes in [self.budget*20+((self.budget+255)//256)*32,16+80*self.budget,32*(2*self.budget-1),20*self.budget,16]:
   b=rt.U();gl['GenBuffers'](1,C.byref(b));self.buffers.append(b.value)
   gl['BindBuffer'](0x90D2,b.value);gl['BufferData'](0x90D2,size_bytes,None,0x88E8)
  self.geometry_buffers=self.buffers[1:]
  gl['ActiveTexture'](0x84C0+28);self.atlas=rt.texture(rt.constant([1,1,1,1],4))
  self.programs={name:compute(name,self.options) for name in ['begin']+[p.stem for p in sorted(rt.ROOT.glob('shadowcomp*.csh'),key=lambda p:(int(re.match(r'shadowcomp(\d*)',p.stem)[1] or 0),'_' in p.stem))]}
  rt.resource_binders[:]=[self.bind];self.clear()
 def bind(self,p):
  for i,b in enumerate(self.buffers):gl['BindBufferBase'](0x90D2,i,b)
  gl['ActiveTexture'](0x84C0+28);gl['BindTexture'](rt.TEX,self.atlas)
  gl['Uniform1i'](gl['GetUniformLocation'](p,b'sceneAtlas'),28)
 def dispatch(self,name):
  p=self.programs[name];gl['UseProgram'](p);self.bind(p)
  # Exercise real GL indirect commands, including the command-memory barrier.
  source=(rt.ROOT/(name+'.csh')).read_text()
  indirect=re.search(r'^indirect\.'+re.escape(name)+r'=4 0$',(rt.ROOT/'shaders.properties').read_text(),re.M)
  if indirect:
   gl['BindBuffer'](0x90EE,self.buffers[4]);gl['DispatchComputeIndirect'](0)
  else:
   match=re.search(r'const ivec3 workGroups=ivec3\((\d+),1,1\)',source)
   groups=int(match[1]) if match else 1
   gl['DispatchCompute'](groups,1,1)
  gl['MemoryBarrier'](0x20|0x8|0x2000|0x40)

 def clear(self):self.dispatch('begin')
 def collect(self):
  for name in self.programs:
   if name!='begin':self.dispatch(name)
  gl['Finish']();return self.geometry_stats()
 def geometry_stats(self):
  a=np.empty(4,np.uint32);gl['BindBuffer'](0x90D2,self.buffers[1]);gl['GetBufferSubData'](0x90D2,0,a.nbytes,a.ctypes.data);return a
 def voxelize_vertices(self,vertices,camera=(0.,0.,0.),atlas=None,specular=(0.,0.,0.,1.),render_stage=7):
  rt.resource_binders[:]=[self.bind];self.clear();rt.values['cameraPosition']=tuple(camera)
  rt.uniforms['shadowModelViewInverse']=np.eye(4)
  for mode in [0x1700,0x1701]:gl['MatrixMode'](mode);gl['LoadIdentity']()
  if atlas is not None:self.atlas=atlas
  p=rt.program('shadow',self.options)
  gl['ActiveTexture'](0x84C0+30);spec=rt.texture(rt.constant(specular,4))
  rt.draw(p,{'texture':self.atlas,'specular':spec},width=4,height=4,vertices=vertices,value_overrides={'renderStage':render_stage})
  gl['DeleteProgram'](p);return self.collect()
 def voxelize(self,blocks,camera=(0.,0.,0.),specular=(0.,0.,0.,1.),render_stage=7):
  self.clear();rt.values['cameraPosition']=tuple(camera)
  rt.uniforms['shadowModelViewInverse']=np.eye(4)
  for mode in [0x1700,0x1701]:gl['MatrixMode'](mode);gl['LoadIdentity']()
  vertices=[]
  for position,color,id in blocks:
   lo=np.asarray(position,float);hi=lo+1;center=lo+.5
   x,y,z=lo;X,Y,Z=hi
   faces=[([(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],(0,0,1)),
          ([(X,y,z),(x,y,z),(x,Y,z),(X,Y,z)],(0,0,-1)),
          ([(X,y,Z),(X,y,z),(X,Y,z),(X,Y,Z)],(1,0,0)),
          ([(x,y,z),(x,y,Z),(x,Y,Z),(x,Y,z)],(-1,0,0)),
          ([(x,Y,Z),(X,Y,Z),(X,Y,z),(x,Y,z)],(0,1,0)),
          ([(x,y,z),(X,y,z),(X,y,Z),(x,y,Z)],(0,-1,0))]
   for points,normal in faces:
    for i in [0,1,2,0,2,3]:
     pos=np.asarray(points[i]);mid=(center-pos)*64
     vertices.append({'position':pos-np.array(camera),'normal':normal,'color':(*color,1.),'uv':[(0,0),(1,0),(1,1),(0,1)][i],
      'attributes':{'mc_Entity':(id,0,0,0),'at_midBlock':(*mid,0.),'mc_midTexCoord':(.5,.5)}})
  return self.voxelize_vertices(vertices,camera,specular=specular,render_stage=render_stage)
