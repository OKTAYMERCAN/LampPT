#!/usr/bin/env python3
"""Audit fixes: real raster guides, capture, indirect commands and transport.

Synthetic OpenGL fixtures, not an Iris/game benchmark. Inward fluid copies and
unmapped block-light attributes reproduce cases absent from earlier tests.
"""
import copy,ctypes as C,json
from pathlib import Path
import numpy as np
from ptgi_runtime import Fixture,box,rt
from world_runtime import fragment
from pipeline_routing import Pipeline
from buffer_encoding import normal24,material24,rgb24
HERE=Path(__file__).parent;OUT=HERE/'ptgi-evidence';records={}
def check(name,ok,detail):
 assert ok,(name,detail)
 records[name]=detail;print('AUDIT PASS',name,detail,flush=True)
f=Fixture({'WATER_WAVES':0,'WATER_SCATTERING':'0.0','WATER_ROUGHNESS':'0.001','PT_SUNLIGHT':0})
probe=fragment(HERE/'audit_probe.fsh',f.options)
white=f.white;spec=rt.texture(rt.constant([0,0,0,1],4))
def draw_probe(inputs,mode,size=(32,32),**kw):
 return rt.draw(probe,inputs,*size,full_precision=(0,),value_overrides={'probeMode':mode,**kw})[1][0]
def reverse(mesh):
 result=[]
 for i in range(0,len(mesh),3):
  for v in mesh[i:i+3][::-1]:
   q=copy.deepcopy(v);q['normal']=tuple(-np.array(v['normal']));result.append(q)
 return result
# Raster a test quad with block-local attributes. It supplies guides, not a
# fabricated material buffer. The normal is independently inspected below.
def raster(block,normal=(0,0,1),emission=0,trans=True,water_height=.8):
 vertices=box((-1,-1,-.6),(1,1,-.5),owner=(0,0,-1),block=block,color=(1,1,1))[:6]
 for v in vertices:
  v['normal']=normal
  v['attributes']['at_midBlock']=(0,(.5-water_height)*64,-32,emission)
 name='gbuffers_water' if trans else 'gbuffers_terrain'
 p=rt.program(name,f.options)
 tx,values=rt.draw(p,{'texture':white,'lightmap':white,'specular':spec},32,32,vertices=vertices,outputs=4 if trans else 5,full_precision=tuple(range(5)))
 rt.gl['DeleteProgram'](p)
 if trans:
  inputs={'colortex0':tx[0],'colortex14':tx[1],'colortex15':tx[2],'colortex5':tx[3],
   'depthtex1':rt.texture(np.ones((32,32))), 'colortex1':rt.texture(rt.constant([.5,.5,1,1],32)),
   'colortex3':white,'colortex4':rt.texture(rt.constant([.5,.04,0,0],32)),
   'colortex10':rt.texture(rt.constant([0,1,.5,.5],32))}
 else:inputs={}
 return inputs,values
# Material identity is checked against captured rays, not only menu definitions.
for block,name,wanted in [(10010,'clear glass',2),(10013,'stained glass',2),(10014,'tinted glass',32),(10015,'ice',29),(10016,'honey',30),(10017,'slime',31),(0,'unmapped translucent',34)]:
 inputs,values=raster(block)
 primary=draw_probe(inputs,0)[16,16]
 mesh=box((-.5,-.5,-3),(.5,.5,-2),block=block,color=(1,1,1))
 f.world.voxelize_vertices(mesh,atlas=white,render_stage=8)
 secondary=draw_probe({},3,probePosition=(0.,0.,0.),probeDirection=(0.,0.,-1.))[16,16]
 check('material '+name,primary[3]==secondary[3]==wanted,{'primary':primary.tolist(),'secondary':secondary.tolist()})
# Unmapped luminous blocks glow visibly and illuminate secondary paths equally.
_,values=raster(0,emission=15,trans=False)
primary=values[3][16,16]
mesh=box((-.5,-.5,-3),(.5,.5,-2),color=(1,1,1))
for v in mesh:v['attributes']['at_midBlock']=(*v['attributes']['at_midBlock'][:3],15)
f.capture(mesh)
secondary=draw_probe({},3,probePosition=(0.,0.,0.),probeDirection=(0.,0.,-1.))[16,16]
check('native emission parity',abs(primary[2]-1)<.001 and abs(primary[2]-secondary[2])<.001,{'primary':primary.tolist(),'secondary':secondary.tolist()})
# Test duplicated water faces in both insertion orders and shallow top/bottom.
for height,expected in [(.8,1.),(.125,1.),(.001,-1.)]:
 top=box((-2,height,-4),(2,height,0),owner=(0,0,-2),block=10000,color=(1,1,1))[24:30]
 back=reverse(top)
 normals=[]
 for mesh in [top+back,back+top]:
  f.capture(mesh)
  hit=draw_probe({},2,probePosition=(0.,-1.,-2.),probeDirection=(0.,1.,0.))[16,16]
  normals.append(float(hit[1]))
 check('fluid capture at '+str(height),all(abs(n-expected)<.001 for n in normals),normals)
 for normal in [(0,1,0),(0,-1,0)]:
  inputs,_=raster(10000,normal,water_height=height)
  n=draw_probe(inputs,1)[16,16,:3]
  check('fluid guide '+str((height,normal)),abs(n[1]-expected)<.001,n.tolist())
# Vertical sides must stay vertical. Sloped flowing tops retain their actual
# mesh normal for ray offsets instead of being flattened to world +Y.
solid=box((0,0,0),(1,.8,1),owner=(0,0,0),block=10000,color=(1,1,1))
for start,normal in [(0,(0,0,1)),(6,(0,0,-1)),(12,(1,0,0)),(18,(-1,0,0))]:
 face=solid[start:start+6];norm=np.array(normal,float)
 for order in [face+reverse(face),reverse(face)+face]:
  f.capture(order)
  hit=draw_probe({},2,probePosition=tuple(np.array([.5,.4,.5])+norm*2),probeDirection=tuple(-norm))[16,16]
  assert hit[3]==1 and np.dot(hit[:3],norm)>.999,hit
 check('fluid side '+str(normal),True,list(normal))
n=np.array([-.3,1.,0.]);n/=np.linalg.norm(n)
points=[(0,.3,0),(0,.3,1),(1,.6,1),(1,.6,0)];slope=[]
for i in [0,1,2,0,2,3]:
 pos=np.array(points[i]);slope.append({'position':pos,'normal':tuple(n),'color':(1,1,1,1),'uv':(.5,.5),
  'attributes':{'mc_Entity':(10000,0,0,0),'at_midBlock':(*((.5-pos)*64),0.),'mc_midTexCoord':(.5,.5)}})
for order in [slope+reverse(slope),reverse(slope)+slope]:
 f.capture(order);hit=draw_probe({},2,probePosition=(.5,2.,.5),probeDirection=(0.,-1.,0.))[16,16]
 assert hit[3]==1 and np.dot(hit[:3],n)>.999,hit
for sign in [1,-1]:
 inputs,_=raster(10000,tuple(n*sign),water_height=.45)
 normal=draw_probe(inputs,1)[16,16,:3];assert np.dot(normal,n)>.999,normal
check('sloped fluid capture and guide',True,normal.tolist())
# Held glass has no captured back face. Its finite sheet must not trap paths.
p=rt.program('gbuffers_hand_water',f.options)
verts=box((-1,-1,-.6),(1,1,-.5),color=(.8,.9,1.))[:6]
tx,_=rt.draw(p,{'texture':white,'lightmap':white,'specular':spec},32,32,vertices=verts,outputs=4,full_precision=(0,1,2,3))
inputs,_=raster(10010);inputs.update(colortex14=tx[1],colortex15=tx[2],colortex5=tx[3]);f.capture([])
kind=draw_probe(inputs,0)[16,16,3]
view=draw_probe(inputs,4,(128,128),isEyeInWater=0,skyColor=(1.,1.,1.))[:,:,:3]
check('held glass finite transmission',kind==33 and view.mean()>.5,{'kind':float(kind),'mean':float(view.mean())})
# An underwater view must exit water even when Sodium supplied the inward copy.
f.capture([]);brightness=[]
for normal in [(0,1,0),(0,-1,0)]:
 inputs,_=raster(10000,normal)
 image=draw_probe(inputs,4,(128,128),isEyeInWater=1,skyColor=(1.,1.,1.))
 brightness.append(float(image[:,:,:3].mean()))
check('underwater outward versus inward',min(brightness)>.5 and abs(brightness[0]-brightness[1])<.0001,brightness)
# Real indirect commands: preparation must initialize zero and clamp overflow.
gl=rt.gl;counts={}
for count in [0,1,255,256,257,f.world.budget,f.world.budget+123]:
 data=np.array([count,0,0,0],np.uint32);gl['BindBuffer'](0x90D2,f.world.buffers[1]);
 gl['BufferSubData']=rt.function(rt.G,'glBufferSubData',None,rt.U,C.c_ssize_t,C.c_ssize_t,rt.P)
 gl['BufferSubData'](0x90D2,0,data.nbytes,data.ctypes.data)
 f.world.dispatch('shadowcomp')
 cmd=np.zeros(4,np.uint32);gl['BindBuffer'](0x90D2,f.world.buffers[4]);gl['GetBufferSubData'](0x90D2,0,cmd.nbytes,cmd.ctypes.data)
 expected=max(1,(min(count,f.world.budget)+255)//256)
 assert cmd.tolist()==[expected,1,1,0],(count,cmd)
 counts[str(count)]=int(cmd[0])
check('bounded indirect commands',True,counts)
f.capture(box((0,0,-3),(1,1,-2)))
check('indirect-built geometry remains visible',draw_probe({},3,probePosition=(.5,.5,0.),probeDirection=(0.,0.,-1.))[16,16,0]>.1,int(f.world.geometry_stats()[0]))
# Disabled/non-directional sunlight and absent boundaries must not spend 65%
# of BSDF samples in a refracted-sun cone. Same RNG gives identical samples.
for case,extra in [('sun disabled',{'PT_SUNLIGHT':0,'SUN_INTENSITY':'1.0'}),('zero radiance',{}),('no captured water',{'PT_SUNLIGHT':1,'SUN_INTENSITY':'1.0'})]:
 samples=[]
 for enabled in [0,1]:
  q=Fixture({**extra,'PT_CAUSTIC_GUIDING':enabled})
  a=q.draw(size=(128,128),probeMode=1,probeNormal=(0.,1.,0.),probeDirection=(0.,-1.,0.),probeAlbedo=(1.,1.,1.),probeEtaI=1.333,probeMaterial=(.75,.04,0.),sunPosition=(0.,1.,0.),shadowLightPosition=(0.,1.,0.))
  samples.append(a)
 error=float(np.max(abs(samples[0]-samples[1])))
 check('guidance gate '+case,error<1e-6,error)
records['all_passed']=True;records['scope']='Production GLSL on synthetic OpenGL; not Minecraft'
(OUT/'v063-audit-fixes.json').write_text(json.dumps(records,indent=2)+'\n')
