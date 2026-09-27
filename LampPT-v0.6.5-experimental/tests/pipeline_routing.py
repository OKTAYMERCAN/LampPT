#!/usr/bin/env python3
"""Render using pack-declared MRT routing and buffer sizes, not hand-wired stages.

Models documented Iris post-pass flips with logical front/back banks. This is
not a replacement for running Iris's transformer or Minecraft itself.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path
import numpy as np
import gl_runtime as rt

def targets(name,options=None):
    import subprocess
    source=rt.source(rt.ROOT/(name+'.fsh'),{**rt.default_options,**(options or {})})
    source=re.sub(r'^\s*#(?:version|extension).*$', '',source,flags=re.M)
    source=subprocess.run(['cpp','-P','-CC','-undef','-nostdinc','-'],input=source,text=True,capture_output=True,check=True).stdout
    matches=list(re.finditer(r'/\*\s*(DRAWBUFFERS|RENDERTARGETS):\s*([0-9,]+)\s*\*/',source))
    if not matches:return [0]
    m=matches[-1]
    return [int(v) for v in (m[2].split(',') if m[1]=='RENDERTARGETS' else list(m[2]))]

def active_properties(options=None):
    """Use the same option branches as Iris before inspecting sizes or enables."""
    settings=(rt.ROOT/'lib/settings.glsl').read_text()
    merged={**rt.default_options,**(options or {})}
    for name,value in merged.items():
        settings=re.sub(r'^(#define\s+'+re.escape(name)+r')\s+\S+',lambda m:m[1]+' '+str(value),settings,flags=re.M)
    properties=(rt.ROOT/'shaders.properties').read_text()
    properties=re.sub(r'^#(?!if|elif|else|endif|define|undef).*$', '',properties,flags=re.M)
    return subprocess.run(['cpp','-P','-undef','-nostdinc','-'],input=settings+'\n'+properties,
                          text=True,capture_output=True,check=True).stdout

class Pipeline:
    def __init__(self,initial,width=rt.N,height=rt.N,options=None):
        self.width,self.height=width,height
        self.options=dict(options or {})
        self.properties=active_properties(self.options)
        self.initial=dict(initial)
        self.bank={}
        self.front={}
        self.trace=[]
        self.program_cache={}
        for index in range(16):
            key=f'colortex{index}'
            w,h=self.size(index)
            zero=rt.texture(np.zeros((h,w,4)))
            self.bank[index]=[initial.get(key,zero),zero]
            self.front[index]=0
    def size(self,index):
        m=re.search(r'^size\.buffer\.colortex'+str(index)+r'=(\S+) (\S+)',self.properties,re.M)
        if not m:return self.width,self.height
        values=[]
        for value,full in zip(m.groups(),(self.width,self.height)):
            values.append(max(1,int(float(value)*full)) if '.' in value else int(value))
        return tuple(values)
    def inputs(self):
        return {**self.initial,**{f'colortex{i}':self.bank[i][self.front[i]] for i in self.bank}}
    def pass_(self,name,options):
        if options!=self.options:
            self.options=dict(options);self.properties=active_properties(options)
        if re.search(r'^program\.'+re.escape(name)+r'\.enabled=false$',self.properties,re.M):return None
        key=(name,tuple(sorted((k,str(v)) for k,v in options.items())))
        if key not in self.program_cache:
            self.program_cache[key]=(targets(name,options),rt.program(name,options))
        dest,p=self.program_cache[key]
        sizes=[self.size(i) for i in dest]
        assert len(set(sizes))==1,(name,sizes)
        formats='\n'.join(path.read_text() for path in rt.ROOT.glob('*.fsh'))
        fp=tuple(i for i,index in enumerate(dest) if re.search(r'const int colortex'+str(index)+r'Format = RGBA32F;',formats))
        tex,values=rt.draw(p,self.inputs(),*sizes[0],outputs=len(dest),full_precision=fp)
        for index,texture in zip(dest,tex):
            self.bank[index][1-self.front[index]]=texture
            explicit=re.search(r'^flip\.'+name+r'\.colortex'+str(index)+r'=(true|false)$',self.properties,re.M)
            if not explicit or explicit[1]=='true':self.front[index]=1-self.front[index]
        self.trace.append({'stage':name,'writes':dest,'size':sizes[0]})
        return values
    def run(self,options=None):
        options=options or {}
        for path in sorted(rt.ROOT.glob('deferred*.fsh'),key=lambda p:int(p.stem[8:] or 0)):
            self.pass_(path.stem,options)
        stages=sorted(rt.ROOT.glob('composite*.fsh'),key=lambda p:int(p.stem[9:] or 0))
        for path in stages:
            self.pass_(path.stem,options)
        p=rt.program('final',options)
        _,out=rt.draw(p,self.inputs(),self.width,self.height)
        rt.gl['DeleteProgram'](p)
        return out[0]

def room():
    N=rt.N;yy,xx=np.mgrid[:N,:N]
    dirs=np.stack([((xx+.5)/N*2-1)/rt.scale,((yy+.5)/N*2-1)/rt.scale,-np.ones((N,N))],-1)
    with np.errstate(divide='ignore',invalid='ignore'):
        floor=np.where(dirs[:,:,1]<0,-1/dirs[:,:,1],np.inf)
        right=np.where(dirs[:,:,0]>0,1.8/dirs[:,:,0],np.inf)
    times=np.stack([np.full((N,N),5.),floor,right],-1)
    which=times.argmin(-1);pos=dirs*times.min(-1)[:,:,None]
    normal=np.array([[0,0,1],[0,1,0],[-1,0,0]])[which]
    color=np.array([[.35,.35,.35],[.35,.35,.35],[.95,.04,.01]])[which]
    # Non-emissive red wall: isolates diffuse color bounce rather than emission.
    return {'colortex0':rt.texture(np.dstack([color,np.ones((N,N))])),
            'colortex1':rt.texture(np.dstack([normal*.5+.5,np.ones((N,N))])),
            'colortex3':rt.texture(np.dstack([color,np.ones((N,N))])),
            'colortex4':rt.texture(rt.constant([.75,.04,0,0])),
            'colortex10':rt.texture(rt.constant([0,1,0,1])),
            'depthtex0':rt.texture(rt.depth_for_z(pos[:,:,2])),
            'depthtex1':rt.texture(rt.depth_for_z(pos[:,:,2])),
            'shadowtex0':rt.texture(np.ones((N,N)))}

