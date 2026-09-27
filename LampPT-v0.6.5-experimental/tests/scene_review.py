#!/usr/bin/env python3
"""Actual terrain -> shadow -> deferred -> water -> composite -> final GLSL.

Procedural block scene rendered in Mesa/EGL, not a Minecraft screenshot.
No hand-authored G-buffer: positions, normals, material IDs and depths come
from the pack's geometry shaders. See TEST_RESULTS.md for runtime limits.
"""
import ctypes as C
import json
import re
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import gl_runtime as rt
from pipeline_routing import Pipeline,targets
from world_runtime import WorldGPU

gl = rt.gl
for name,sig in {
    'Enable':(None,rt.U), 'Enablei':(None,rt.U,rt.U), 'Disablei':(None,rt.U,rt.U),
    'DepthFunc':(None,rt.U), 'DepthMask':(None,rt.U),
    'ClearDepth':(None,C.c_double), 'Clear':(None,rt.U),
    'ClearBufferfv':(None,rt.U,rt.I,rt.P), 'DrawBuffer':(None,rt.U),
    'LoadMatrixf':(None,rt.P), 'BlendFuncSeparate':(None,rt.U,rt.U,rt.U,rt.U),
}.items(): gl[name]=rt.function(rt.G,'gl'+name,*sig)

W,H=513,289  # odd dimensions exercise half/eighth size rounding
OUT=Path(__file__).parent/'scene-evidence'
OUT.mkdir(exist_ok=True)

def unit(v): return np.asarray(v,dtype=np.float32)/np.linalg.norm(v)
def look(eye,target):
    f=unit(np.asarray(target)-eye)
    up=[0,0,1] if abs(f[1])>.999 else [0,1,0]
    r=unit(np.cross(f,up)); u=np.cross(r,f)
    m=np.eye(4,dtype=np.float32);m[:3,:3]=[r,u,-f];m[:3,3]=-m[:3,:3]@eye
    return m

eye=np.array([6.8,4.2,8.4],dtype=np.float32)
center=np.array([-.5,1.1,-1.5],dtype=np.float32)
V=look(eye,center); V[:3,3]=0 # camera-relative Minecraft geometry
P=np.array(rt.projection,copy=True);P[0,0]*=H/W
rt.uniforms.update(gbufferProjection=P,gbufferProjectionInverse=np.linalg.inv(P),
                   gbufferModelView=V,gbufferModelViewInverse=np.linalg.inv(V))

def fixed(p,v):
    for mode,matrix in [(0x1701,p),(0x1700,v)]:
        gl['MatrixMode'](mode);m=np.ascontiguousarray(matrix.T,dtype=np.float32)
        gl['LoadMatrixf'](m.ctypes.data)

def bind(p,textures):
    gl['UseProgram'](p)
    for k,m in rt.uniforms.items():
        a=np.ascontiguousarray(m,dtype=np.float32)
        gl['UniformMatrix4fv'](gl['GetUniformLocation'](p,k.encode()),1,1,a.ctypes.data)
    for k,v in rt.values.items():
        loc=gl['GetUniformLocation'](p,k.encode())
        if isinstance(v,(tuple,list)):
            rt.function(rt.G,'glUniform3f',None,rt.I,rt.F,rt.F,rt.F)(loc,*v)
        elif isinstance(v,int):gl['Uniform1i'](loc,v)
        else:gl['Uniform1f'](loc,v)
    gl['Uniform1f'](gl['GetUniformLocation'](p,b'alphaTestRef'),.1)
    for i,(name,t) in enumerate(textures.items()):
        gl['ActiveTexture'](0x84C0+i);gl['BindTexture'](rt.TEX,t)
        gl['Uniform1i'](gl['GetUniformLocation'](p,name.encode()),i)
    for binder in rt.resource_binders:binder(p)

def depth_texture(w,h):
    obj=rt.U();gl['GenTextures'](1,C.byref(obj));gl['BindTexture'](rt.TEX,obj.value)
    for k,v in [(0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812F),(0x2803,0x812F)]:
        gl['TexParameteri'](rt.TEX,k,v)
    gl['TexImage2D'](rt.TEX,0,0x8CAC,w,h,0,0x1902,rt.FLOAT,None)
    return obj.value

def read_depth(w,h):
    a=np.empty((h,w),dtype=np.float32)
    gl['ReadPixels'](0,0,w,h,0x1902,rt.FLOAT,a.ctypes.data)
    return a

def new_fbo():
    obj=rt.U();gl['GenFramebuffers'](1,C.byref(obj));gl['BindFramebuffer'](rt.FB,obj.value)
    return obj.value

def color_targets():
    result={}
    # Lightmap RG and geometric-normal BA share the declared RGBA16F target.
    formats={0:0x881A,1:0x881A,3:0x8058,4:0x881A,10:0x881A}
    gl['ActiveTexture'](0x84CF)
    for slot,index in enumerate([0,1,3,4,10]):
        t=rt.texture(np.zeros((H,W,4)))
        gl['BindTexture'](rt.TEX,t)
        gl['TexImage2D'](rt.TEX,0,formats[index],W,H,0,rt.RGBA,rt.FLOAT,None)
        gl['FramebufferTexture2D'](rt.FB,rt.ATT+slot,rt.TEX,t,0)
        result['colortex'+str(index)]=t
    gl['DrawBuffers'](5,(rt.U*5)(*[rt.ATT+i for i in range(5)]))
    for i in range(5):
        c=(rt.F*4)(*(rt.values['skyColor']+(1.,) if i==0 else (0.,0.,0.,0.)))
        gl['ClearBufferfv'](0x1800,i,c)
    return result

# Quad list: world corners, normal, tint, block ID, lightmap, water flag.
faces=[]
def quad(points,normal,color=(.78,.78,.78),block=0,lm=(0.,1.),water=False):
    faces.append((np.array(points,dtype=np.float32),normal,color,block,lm,water))
def floor(x0,x1,z0,z1,y=0,color=(.72,.72,.72),water=False):
    quad([(x0,y,z0),(x0,y,z1),(x1,y,z1),(x1,y,z0)],(0,1,0),color,
         10000 if water else 0,water=water)
def box(lo,hi,color=(.78,.78,.78),block=0,lm=(0.,1.)):
    x,y,z=lo;X,Y,Z=hi
    for p,n in [([(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],(0,0,1)),
                ([(X,y,z),(x,y,z),(x,Y,z),(X,Y,z)],(0,0,-1)),
                ([(X,y,Z),(X,y,z),(X,Y,z),(X,Y,Z)],(1,0,0)),
                ([(x,y,z),(x,y,Z),(x,Y,Z),(x,Y,z)],(-1,0,0)),
                ([(x,Y,Z),(X,Y,Z),(X,Y,z),(x,Y,z)],(0,1,0)),
                ([(x,y,z),(X,y,z),(X,y,Z),(x,y,Z)],(0,-1,0))]:
        quad(p,n,color,block,lm)

floor(-6,.3,-6,5);floor(4.3,6,-6,5);floor(.3,4.3,-6,-2.5);floor(.3,4.3,2,5)
floor(.3,4.3,-2.5,2,-.7,(.35,.49,.53))
box((-6,0,-6.3),(6,4.8,-6),(.8,.8,.8))
box((-6.3,0,-6),(-6,4.8,3),(.78,.78,.78))
box((-6,4,-6),(-1,4.25,1),(.8,.8,.8))
box((-1.4,0,-.5),(-.8,4.1,.1),(.76,.76,.76))
box((-1.4,0,-4.7),(-.8,4.1,-4.1),(.76,.76,.76))
for i,color in enumerate([(.9,.06,.015),(.95,.35,.02),(.85,.75,.03),(.12,.65,.04),(.03,.45,.8),(.5,.035,.65)]):
    floor(-5.8,-2.0,-5.7+i*1.1,-4.62+i*1.1,.003,color)
box((1.5,0,-4.8),(2.8,1.3,-3.5),(.8,.67,.34),10011)
box((3.8,0,-5.8),(4.8,1,-4.8),(.35,.5,.65))
box((-4.6,1.4,-5.95),(-4.33,1.7,-5.68),(1.,.78,.42),10001,(1.,.45))
box((.0,1.2,-5.95),(.27,1.5,-5.68),(.3,.85,1.),10002,(1.,.45))
floor(.3,4.3,-2.5,2,.12,(.25,.55,.72),True)

yy,xx=np.mgrid[:16,:16]
noise=np.random.default_rng(7).uniform(.92,1.,(16,16))
noise[(xx==0)|(yy==0)]=.83
diffuse=rt.texture(np.dstack([noise,noise,noise,np.ones((16,16))]))
watertex=rt.texture(np.tile(np.array([1.,1.,1.,.45]),(16,16,1)))
neutralnormal=rt.texture(rt.constant([.5,.5,1,1],16))
neutralspec=rt.texture(rt.constant([0,0,0,1],16))

def draw_faces(p,water=False,old_shade=False,shadow=False):
    entity=gl['GetAttribLocation'](p,b'mc_Entity');mid=gl['GetAttribLocation'](p,b'mc_midTexCoord')
    midblock=gl['GetAttribLocation'](p,b'at_midBlock')
    gl['Uniform1i'](gl['GetUniformLocation'](p,b'renderStage'),8 if water else 7)
    for points,normal,color,block,lm,iswater in faces:
        if iswater!=water:continue
        if entity>=0:gl['VertexAttrib4f'](entity,block,0,0,0)
        if mid>=0:gl['VertexAttrib2f'](mid,.5,.5)
        factor=np.dot(np.square(normal),[.6,1. if normal[1]>0 else .5,.8]) if old_shade else 1.
        gl['Color4f'](*(np.array(color)*factor),1.)
        gl['Normal3f'](*normal)
        gl['MultiTexCoord2f'](0x84C1,(lm[0]*15+.5)/16,(lm[1]*15+.5)/16)
        gl['Begin'](0x0004)
        for index in [0,1,2,0,2,3]:
            if midblock>=0:
                center=np.floor(points.mean(axis=0)-np.array(normal)*.001)+.5
                offset=(center-points[index])*64.
                gl['VertexAttrib4f'](midblock,*offset,0.)
            gl['TexCoord2f'](*[(0,0),(1,0),(1,1),(0,1)][index])
            gl['Vertex3f'](*(points[index]-eye))
        gl['End']()

def render(options=None,sun=(-.45,.8,.4),frames=1):
    options={'GEOMETRY_BUDGET':65536,**(options or {})}
    volume=WorldGPU(64,options)
    volume.atlas=diffuse
    sun=unit(sun);light=sun if sun[1]>0 else -sun
    rt.values.update(sunPosition=tuple(V[:3,:3]@sun),shadowLightPosition=tuple(V[:3,:3]@light),
                     cameraPosition=tuple(eye),previousCameraPosition=tuple(eye),frameTimeCounter=3.,frameCounter=0)
    rt.uniforms.update(gbufferPreviousModelView=V,gbufferPreviousProjection=P)
    SP=np.diag([1/10,1/10,-2/45,1.]).astype(np.float32);SP[2,3]=-1.
    SV=look(center-eye+light*20,center-eye)
    rt.uniforms.update(shadowProjection=SP,shadowModelView=SV,shadowModelViewInverse=np.linalg.inv(SV))
    sres=int(options.get('shadowMapResolution',2048))
    sf=new_fbo();st=depth_texture(sres,sres)
    gl['FramebufferTexture2D'](rt.FB,0x8D00,rt.TEX,st,0)
    gl['DrawBuffer'](0);gl['ReadBuffer'](0)
    assert gl['CheckFramebufferStatus'](rt.FB)==0x8CD5
    gl['Viewport'](0,0,sres,sres);gl['Enable'](0x0B71);gl['DepthFunc'](0x0201);gl['DepthMask'](1)
    gl['ClearDepth'](1);gl['Clear'](0x100);fixed(SP,SV)
    p=rt.program('shadow',options);bind(p,{'texture':diffuse,'specular':neutralspec});draw_faces(p,shadow=True)
    bind(p,{'texture':watertex,'specular':neutralspec});draw_faces(p,water=True,shadow=True)
    gl['DeleteProgram'](p)
    volume.collect()
    gf=new_fbo();data=color_targets();depth=depth_texture(W,H)
    gl['FramebufferTexture2D'](rt.FB,0x8D00,rt.TEX,depth,0)
    assert gl['CheckFramebufferStatus'](rt.FB)==0x8CD5
    gl['Clear'](0x100);gl['Viewport'](0,0,W,H);fixed(P,V)
    # Small reproducible lightmap fixture: real lightmap sampler, not custom main light.
    sy,sx=np.mgrid[:16,:16];bright=np.maximum(sx/15*.85,sy/15*(.95 if sun[1]>0 else .16))+.025
    lmtex=rt.texture(np.dstack([bright,bright,bright,np.ones((16,16))]))
    textures={'texture':diffuse,'lightmap':lmtex,'normals':neutralnormal,'specular':neutralspec}
    p=rt.program('gbuffers_terrain',options);bind(p,textures)
    old='oldLighting=true' in (rt.ROOT/'shaders.properties').read_text()
    draw_faces(p,old_shade=old);gl['DeleteProgram'](p)
    opaque_depth=read_depth(W,H)
    data.update(depthtex0=depth,depthtex1=rt.texture(opaque_depth),shadowtex0=st)
    # Read unlit albedo/normal masks only for objective region selection.
    gl['ReadBuffer'](rt.ATT+2);albedo=np.empty((H,W,4),np.float32)
    gl['ReadPixels'](0,0,W,H,rt.RGBA,rt.FLOAT,albedo.ctypes.data)
    gl['ReadBuffer'](rt.ATT+1);normals=np.empty_like(albedo)
    gl['ReadPixels'](0,0,W,H,rt.RGBA,rt.FLOAT,normals.ctypes.data)
    gl['Disable'](0x0B71);fixed(np.eye(4),np.eye(4));gl['Color4f'](1,1,1,1)
    pipeline=Pipeline(data,W,H,options)
    for path in sorted(rt.ROOT.glob('deferred*.fsh'),key=lambda p:int(p.stem[8:] or 0)):
        pipeline.pass_(path.stem,options)
    # Match the declared independent water/glass attachments; keep opaque G-buffers.
    gl['BindFramebuffer'](rt.FB,gf);gl['Viewport'](0,0,W,H);gl['Enable'](0x0B71)
    fixed(P,V);p=rt.program('gbuffers_water',options)
    dest=targets('gbuffers_water',options)
    for i in range(8):gl['FramebufferTexture2D'](rt.FB,rt.ATT+i,rt.TEX,0,0)
    for slot,index in enumerate(dest):
        if index>=14 or index==5:
            texture=rt.texture(np.zeros((H,W,4)),half=False)
            pipeline.bank[index][pipeline.front[index]]=texture
        else:texture=pipeline.inputs()['colortex'+str(index)]
        gl['FramebufferTexture2D'](rt.FB,rt.ATT+slot,rt.TEX,texture,0)
    gl['DrawBuffers'](len(dest),(rt.U*len(dest))(*[rt.ATT+i for i in range(len(dest))]))
    bind(p,{**textures,'texture':watertex})
    gl['Enablei'](0x0BE2,0);gl['BlendFuncSeparate'](0x0302,0x0303,1,0x0303)
    for i in range(1,len(dest)):
        if dest[i]>=14 or dest[i]==5:gl['Enablei'](0x0BE2,i)
        else:gl['Disablei'](0x0BE2,i)
    draw_faces(p,water=True,old_shade=old);gl['Disablei'](0x0BE2,0);gl['DeleteProgram'](p)
    for i in range(len(dest)):gl['Disablei'](0x0BE2,i)
    actual_depth=read_depth(W,H)
    watermask=actual_depth<opaque_depth-1e-6
    gl['Disable'](0x0B71);fixed(np.eye(4),np.eye(4));gl['Color4f'](1,1,1,1)
    captured={}
    for frame in range(frames):
        rt.values['frameCounter']=frame
        for path in sorted(rt.ROOT.glob('composite*.fsh'),key=lambda p:int(p.stem[9:] or 0)):
            captured[path.stem]=pipeline.pass_(path.stem,options)
    p=rt.program('final',options);_,output=rt.draw(p,pipeline.inputs(),W,H);gl['DeleteProgram'](p)
    gray=(np.ptp(albedo[:,:,:3],axis=2)<.01)&(opaque_depth<1)&(~watermask)
    return output[0],captured,gray,watermask,pipeline.trace

def save(name,frame):
    Image.fromarray((np.clip(frame[::-1,:,:3],0,1)*255+.5).astype('uint8')).save(OUT/(name+'.png'))
