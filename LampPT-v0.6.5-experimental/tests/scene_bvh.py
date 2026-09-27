#!/usr/bin/env python3
"""Wide-range BVH visibility and invariants against independent CPU geometry.

Executes the pack's capture, all 48 build dispatches and production ray query.
The fixture is deliberately larger than the removed 32-block half-width grid.
"""
import ctypes as C
import json
from pathlib import Path
import numpy as np
from ptgi_runtime import Fixture,box,rt
from world_runtime import gl,fragment

checks={}
def check(name,ok,value=True):
    assert ok,(name,value)
    checks[name]=value;print('SCENE PASS:',name,value,flush=True)
def read(buffer,offset,count,dtype):
    data=np.empty(count,dtype)
    gl['BindBuffer'](0x90D2,buffer)
    gl['GetBufferSubData'](0x90D2,offset,data.nbytes,data.ctypes.data)
    return data

f=Fixture({'GEOMETRY_BUDGET':65536,'PT_DISTANCE':'256.0','shadowDistance':'128.0'})
verts=[]
for x in range(-56,57,8):
    for z in range(-108,-27,8):
        verts+=box((x,-1,z),(x+3,.5,z+.5))
# Shuffle triangles, preserving their actual vertex triplets.
triangles=np.arange(len(verts)//3);np.random.default_rng(9).shuffle(triangles)
verts=[verts[3*i+j] for i in triangles for j in range(3)]
f.capture(verts)
count,overflow,*_=map(int,f.world.geometry_stats())
check('all far triangles captured',count==len(verts)//3 and overflow==0,count)
keys=read(f.world.buffers[0],8*f.world.budget,2*count,np.uint32).reshape(-1,2)
check('stable radix keys sorted across workgroups',bool(np.all(keys[:-1,0]<=keys[1:,0])))
check('sort is a permutation of captured triangles',bool(np.array_equal(np.sort(keys[:,1]),np.arange(count))))
leaves=count
mesh=read(f.world.buffers[1],16,count*20,np.uint32).reshape(-1,20)
reverse=mesh[keys[:,1],17]
check('triangle reverse index matches leaf position',bool(np.array_equal(reverse,np.arange(count)+leaves-1)))
nodes=read(f.world.buffers[2],0,(2*leaves-1)*8,np.float32).reshape(-1,8)
xyz=np.asarray([v['position'] for v in verts])
check('root bounds include near and distant geometry',bool(np.all(nodes[0,:3]<=xyz.min(0)) and np.all(nodes[0,4:7]>=xyz.max(0))))
# Trace rays into multiple distant cells; reference is an independent vectorized
# Moller-Trumbore implementation in float64 over the original vertex mesh.
width=257
origins=np.tile([-64.,0.,-50.],(width,1));origins[:,0]+=128*(np.arange(width)+.5)/width
v=xyz.reshape(-1,3,3);e1=v[:,1]-v[:,0];e2=v[:,2]-v[:,0]
direction=np.array([0,0,-1.]);p=np.cross(direction,e2);det=(e1*p).sum(-1)
expected=[]
for origin in origins:
    offset=origin-v[:,0];q=np.cross(offset,e1)
    with np.errstate(divide='ignore',invalid='ignore'):
        u=(offset*p).sum(-1)/det;vv=(q*direction).sum(-1)/det;t=(q*e2).sum(-1)/det
    with np.errstate(invalid='ignore'):valid=(abs(det)>1e-9)&(u>=-1e-6)&(vv>=-1e-6)&(u+vv<=1.000001)&(t>.0002)
    expected.append(np.min(t[valid]) if valid.any() else 256.)
a=f.draw(size=(width,1),probeMode=3,probePosition=(-64.,0.,-50.),probeU=(128.,0.,0.),probeDirection=(0.,0.,-1.))[0]
error=float(np.max(abs(a[:,1]-expected)))
check('BVH distances agree with brute-force reference',error<1e-4,error)
check('rays starting outside old voxel grid hit far terrain',int((a[:,0]>.5).sum())>70,int((a[:,0]>.5).sum()))
# A thin surface at 100 blocks keeps its holes instead of becoming a solid cube.
atlas=np.ones((8,8,4),np.float32);atlas[:,:4,3]=0
# Both faces have mirrored UVs; use the single front face for a cutout fixture.
f.capture(box((-1,-1,-100),(1,1,-99.8))[:6],rt.texture(atlas))
hole=f.draw(size=(1,1),probeMode=3,probePosition=(-.7,0.,-90.),probeDirection=(0.,0.,-1.))[0,0]
solid=f.draw(size=(1,1),probeMode=3,probePosition=(.7,0.,-90.),probeDirection=(0.,0.,-1.))[0,0]
check('far alpha holes remain open',hole[0]==0 and solid[0]==1,{'hole':hole.tolist(),'solid':solid.tolist()})
# A raster first hit can lie outside the captured radius. Its rays must still
# test retained geometry instead of treating that radius as a black boundary.
outside=f.draw(size=(1,1),probeMode=3,probePosition=(.7,0.,-140.),probeDirection=(0.,0.,1.))[0,0]
check('origin outside capture still intersects retained terrain',outside[0]==1 and abs(outside[1]-40.2)<.001,outside.tolist())
# Failure policy: one missing triangle must not turn every clear ray black.
# Inject the production overflow counter independently of the retained geometry.
subdata=rt.function(rt.G,'glBufferSubData',None,rt.U,C.c_ssize_t,C.c_ssize_t,rt.P)
flag=np.array([1],np.uint32);gl['BindBuffer'](0x90D2,f.world.buffers[1]);subdata(0x90D2,4,4,flag.ctypes.data)
overflow=f.draw(size=(1,1),probeMode=11,probePosition=(-.7,0.,-90.),probeDirection=(0.,0.,-1.))[0,0]
check('overflow does not create a global black occluder',overflow[0]==0 and overflow[1]==1,overflow.tolist())
gl['DeleteProgram'](f.program)
f.program=fragment(Path(__file__).with_name('ptgi_probe.fsh'),{**f.options,'GEOMETRY_RAY_TESTS':1})
exhausted=f.draw(size=(1,1),probeMode=11,probePosition=(.7,0.,-90.),probeDirection=(0.,0.,-1.))[0,0]
check('traversal budget exhaustion is bounded and opaque',np.array_equal(exhausted,[1,0,1,0]),exhausted.tolist())
# One-event direct sunlight is deterministic apart from the tiny finite-disc
# cosine variation. The former random sun/sky mixture had relative std ~1.
f=Fixture({'PT_BOUNCES':1,'SUN_INTENSITY':'1.0'})
sun=f.draw(size=(192,128),sunPosition=(0.,1.,0.),shadowLightPosition=(0.,1.,0.))[:,:,:3]
relative=float(sun[:,:,0].std()/sun[:,:,0].mean())
check('separate sun sampling removes binary sparkle',relative<.002,relative)
# Light the same receiver geometry at 100 blocks; shift both source and receiver.
f=Fixture({'PT_BOUNCES':2})
lamp=box((0,2,-3),(1,3,-2),block=10001,color=(1.,1.,1.))
f.capture(lamp);near=f.draw(probeMode=4)[:,:,:3].mean((0,1))
shift=np.array([0,0,-98.])
farverts=[dict(v,position=v['position']+shift) for v in lamp]
f.capture(farverts);far=f.draw(probeMode=4,probePosition=(.5,-.5,-100.5))[:,:,:3].mean((0,1))
check('far colored area light preserves near-scene radiance',float(abs(near-far).max())<.0001,{'near':near.tolist(),'far':far.tolist()})
out=Path(__file__).parent/'ptgi-evidence/scene-bvh.json'
out.write_text(json.dumps({'checks':checks,'all_passed':True},indent=2)+'\n')
