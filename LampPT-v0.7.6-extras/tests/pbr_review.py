#!/usr/bin/env python3
"""Functional raster PBR/POM and colored candle checks in Mesa, not Minecraft."""
import ctypes as C
import json
from pathlib import Path
import numpy as np
import scene_review as s
import gl_runtime as rt
from PIL import Image
import os
if os.environ.get('PBR_BASELINE_ROOT'):rt.ROOT=Path(os.environ['PBR_BASELINE_ROOT'])
G=rt.gl
s.W=s.H=96
s.eye=np.array([1.5,.2,3.],dtype=np.float32)
s.V=s.look(s.eye,[0,0,0]);s.V[:3,3]=0
s.P=np.array(rt.projection,copy=True)
rt.uniforms.update(gbufferProjection=s.P,gbufferProjectionInverse=np.linalg.inv(s.P),gbufferModelView=s.V,gbufferModelViewInverse=np.linalg.inv(s.V))
s.faces=[]
s.quad([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)],(0,0,1),(1,1,1),0,(1,1))
y,x=np.mgrid[:64,:64]
tex=np.stack([.15+.8*(x%8<4),.15+.7*(y%8<4),np.full_like(x,.4,dtype=float),np.ones_like(x)],axis=-1)
normal=np.empty((64,64,4));normal[:]=[.5,.5,1,.2]
normal[:,:,0]=.5+.3*np.sin(x*np.pi/8);normal[:,:,3]=.15+.7*(x%16<8)
s.diffuse=rt.texture(tex);s.neutralnormal=rt.texture(normal)
s.neutralspec=rt.texture(np.tile([.75,.04,0,1],(64,64,1)))
lm=rt.texture(rt.constant([1,1,1,1],16))
def raster(opts):
 s.new_fbo();s.color_targets();dep=s.depth_texture(s.W,s.H)
 G['FramebufferTexture2D'](rt.FB,0x8D00,rt.TEX,dep,0)
 G['ClearDepth'](1);G['Clear'](0x100);G['Enable'](0x0B71);G['DepthFunc'](0x0201);G['DepthMask'](1)
 G['Viewport'](0,0,s.W,s.H);s.fixed(s.P,s.V)
 p=rt.program('gbuffers_terrain',opts)
 s.bind(p,{'texture':s.diffuse,'normals':s.neutralnormal,'specular':s.neutralspec,'lightmap':lm});s.draw_faces(p)
 result=[]
 for i in [1,2,3]:
  G['ReadBuffer'](rt.ATT+i);a=np.zeros((s.H,s.W,4),np.float32)
  G['ReadPixels'](0,0,s.W,s.H,rt.RGBA,rt.FLOAT,a.ctypes.data);result.append(a)
 G['DeleteProgram'](p);G['Disable'](0x0B71)
 return result
base=raster({'NORMAL_MAPS':0,'POM':0,'SPECULAR_MAPS':0})
norm=raster({'NORMAL_MAPS':1,'POM':0,'SPECULAR_MAPS':1})
pom=raster({'NORMAL_MAPS':1,'POM':1,'POM_DEPTH':.12,'SPECULAR_MAPS':1})
mask=base[0][:,:,3]>.5
metrics={'normal_mean_abs_change':float(np.abs(base[0]-norm[0])[mask,:3].mean()),'pom_albedo_mean_abs_change':float(np.abs(norm[1]-pom[1])[mask,:3].mean()),'specular_roughness':float(norm[2][mask,0].mean()),'base_roughness':float(base[2][mask,0].mean())}
assert metrics['normal_mean_abs_change']>.01
assert metrics['pom_albedo_mean_abs_change']>.01
assert abs(metrics['specular_roughness']-.0625)<.001
# Atlas UV density must not change the tangent frame of the same face.
s.neutralnormal=rt.texture(rt.constant([.8,.5,1,.5],4))
coord=G['TexCoord2f']
G['TexCoord2f']=lambda u,v:coord(v,u)
wide=raster({'NORMAL_MAPS':1,'POM':0})[0]
G['TexCoord2f']=lambda u,v:coord(v/4096,u/4096)
tiny=raster({'NORMAL_MAPS':1,'POM':0})[0]
G['TexCoord2f']=coord
metrics['tiny_atlas_normal_error']=float(np.abs(wide-tiny)[mask,:3].max())
print('RASTER_METRICS',json.dumps(metrics),flush=True)
assert metrics['tiny_atlas_normal_error']<.002
out=Path(__file__).parent/'ptgi-evidence'
for name,a in [('v074-pbr-off',base[1]),('v074-pom-on',pom[1]),('v074-normal-on',norm[0])]:Image.fromarray((np.clip(a[::-1,:,:3],0,1)*255).astype('uint8')).save(out/(name+'.png'))
# Probe actual emission functions; candle wax texture must not override hue.
rt.ROOT=(Path(__file__).resolve().parents[1]/'shaders')
old=rt.ROOT
# Compile the existing standalone probe with absolute include expansion rooted in shaders.
v=rt.shader(old/'final.vsh',0x8B31,{})
f=rt.shader(Path(__file__).parent/'source_probe.fsh',0x8B30,{})
p=G['CreateProgram']();G['AttachShader'](p,v);G['AttachShader'](p,f);G['LinkProgram'](p)
s.fixed(np.eye(4),np.eye(4));G['Color4f'](1,1,1,1)
colors=[]
for i in range(16):
 rt.values.update(sourceId=float(10400+i),sourceNative=3.,sourceColor=(.02,.02,.02))
 _,outputs=rt.draw(p,{},1,1);rgb=outputs[0][0,0,:3]
 assert np.isfinite(rgb).all() and rgb.max()>0
 colors.append(rgb.tolist())
assert colors[14][0]>colors[14][2]*10 and colors[11][2]>colors[11][0]*10
metrics['candle_rgb']=colors;metrics['scope']='Synthetic OpenGL raster and emission functions, not Iris/Minecraft.'
(out/'v074-pbr-review.json').write_text(json.dumps(metrics,indent=2)+'\n')
print(json.dumps(metrics),flush=True)
