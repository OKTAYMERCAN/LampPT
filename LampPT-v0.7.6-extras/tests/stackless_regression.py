#!/usr/bin/env python3
"""Compare parent-link traversal with the shipped 0.6.6 stack walk and CPU rays.
The stack reference lives only in test fixtures, never in runtime shaders.
"""
import json,re
from pathlib import Path
import numpy as np
from ptgi_runtime import Fixture,box,rt
from world_runtime import fragment
OUT=Path(__file__).parent/'ptgi-evidence';records={}

def check(name,ok,detail):
 assert ok,(name,detail)
 records[name]=detail;print('STACKLESS PASS',name,detail,flush=True)

# Prevent the exact reported resource from returning to production includes.
source=rt.source(rt.ROOT/'composite1.fsh',{'GEOMETRY_BUDGET':65536})
check('runtime has no private BVH stack',not re.search(r'\b(?:uint|int)\s+stack\s*\[',source),True)
merge=(rt.ROOT/'lib/ptgi/merge.glsl').read_text()
check('merge has one runtime integrator call site',merge.count('ptIntegrateComponent(')==1,merge.count('ptIntegrateComponent('))
f=Fixture({'GEOMETRY_BUDGET':65536,'GEOMETRY_RAY_TESTS':512,'PT_DISTANCE':'256.0'})
p=fragment(Path(__file__).with_name('stackless_probe.fsh'),f.options)
rng=np.random.default_rng(667);N=4096
origins=rng.uniform([-12,-5,-12],[12,8,8],(N,3));directions=rng.normal(size=(N,3));directions/=np.linalg.norm(directions,axis=1)[:,None]
# Parallel and on-slab rays complement random floating-point rays.
origins[:24]=np.tile([[0,0,0],[1,1,1],[-1,-1,-1]],(8,1))
directions[:24]=np.tile([[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]],(4,1))

def run(name,mesh,alpha=False,cpu=False):
 atlas=np.ones((8,8,4),np.float32)
 if alpha:atlas[:,:4,3]=0
 f.capture(mesh,rt.texture(atlas))
 inputs={'testOrigins':rt.texture(np.column_stack([origins,np.ones(N)]).reshape(64,64,4)),
         'testDirections':rt.texture(np.column_stack([directions,np.ones(N)*256]).reshape(64,64,4))}
 _,out=rt.draw(p,inputs,64,64,outputs=2,full_precision=(0,1))
 error=out[0].reshape(-1,4);actual=out[1].reshape(-1,4)
 check(name+' reference parity',np.isfinite(error).all() and error.max()<.0002,{'rays':N,'max_error':error.max(0).tolist()})
 if cpu:
  triangles=np.array([v['position'] for v in mesh],float).reshape(-1,3,3)
  a=triangles[:,0];e1=triangles[:,1]-a;e2=triangles[:,2]-a
  distances=[]
  for start in range(0,N,64):
   o=origins[start:start+64,None,:];d=directions[start:start+64,None,:]
   h=np.cross(d,e2);det=np.sum(e1*h,axis=-1);s=o-a;q=np.cross(s,e1)
   with np.errstate(divide='ignore',invalid='ignore'):
    u=np.sum(s*h,axis=-1)/det;v=np.sum(d*q,axis=-1)/det;t=np.sum(e2*q,axis=-1)/det
   with np.errstate(invalid='ignore'):valid=(abs(det)>=1e-9)&(u>=-.000001)&(v>=-.000001)&(u+v<=1.000001)&(t>=.0002)&(t<=256)
   distances.extend(np.where(valid,t,256).min(1))
  # GPU inputs are float32; allow 0.002 world units for grazing intersections.
  err=np.abs(actual[:,0]-distances)
  check(name+' CPU brute force',err.max()<.002,{'max_distance_error':float(err.max()),'hit_count':int((actual[:,1]>.5).sum())})
run('empty',[])
run('single triangle',box((-.5,-.5,-2),(.5,.5,-1.5))[:3],cpu=True)
mesh=[]
for i in range(60):
 lo=rng.uniform([-9,-3,-9],[9,5,4]);hi=lo+rng.uniform(.03,1.8,3)
 mesh+=box(lo,hi)
run('shuffled boxes',mesh,cpu=True)
run('alpha-cutout boxes',mesh,alpha=True)
# Overlapping Morton keys, identical faces and origins inside the hierarchy.
mesh=box((-1,-1,-1),(1,1,1))*3+box((-6,-.05,-6),(6,.05,6))
run('overlap and parallel boundaries',mesh,cpu=True)
(OUT/'stackless_v067.json').write_text(json.dumps({'all_passed':True,'checks':records,'scope':'Mesa GLSL against original stack traversal and independent float64 triangle tests; not NVIDIA compilation.'},indent=2)+'\n')
