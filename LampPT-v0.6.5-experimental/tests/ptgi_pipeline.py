#!/usr/bin/env python3
"""PT first-hit reconstruction and history validity regressions."""
import json
from pathlib import Path
import numpy as np
import gl_runtime as rt
from world_runtime import fragment,WorldGPU

HERE=Path(__file__).parent
records={}
rt.uniforms.update(gbufferPreviousModelView=np.eye(4),gbufferPreviousProjection=rt.projection)

def check(name,condition,value):
    assert condition,(name,value)
    records[name]=value;print('PT PIPELINE PASS:',name,value,flush=True)

def constant(v,w,h):return rt.texture(np.broadcast_to(v,(h,w,len(v))).copy())

world=WorldGPU(32,{})
probe=fragment(HERE/'ptgi_probe.fsh',{'GEOMETRY_BUDGET':65536})
for w,h in [(64,64),(127,75)]:
    y,x=np.mgrid[:h,:w]
    rays=np.stack([((x+.5)/w*2-1)/rt.scale,((y+.5)/h*2-1)/rt.scale,-np.ones((h,w))],-1)
    normal=np.array([0,.4,1.]);normal/=np.linalg.norm(normal)
    plane=-4*normal[2]
    positions=rays*(plane/np.einsum('ijk,k->ij',rays,normal))[:,:,None]
    inputs={'depthtex1':rt.texture(rt.depth_for_z(positions[:,:,2])),
            'colortex1':constant([*(normal*.5+.5),1],w,h),'colortex3':constant([.7,.7,.7,1],w,h),
            'colortex4':constant([.75,.04,0,0],w,h),'colortex10':constant([0,1,0,1],w,h)}
    _,values=rt.draw(probe,inputs,w//2,h//2,full_precision=(0,),value_overrides={'probeMode':8})
    error=np.max(abs(values[0][:,:,:3]@normal-plane))
    check('half-resolution tilted plane '+str((w,h)),error<.0001,float(error))
    # Independent negative control: the former unsnapped UV/depth pairing must
    # fail on this plane so a regression cannot silently weaken the fixture.
    yl,xl=np.mgrid[:h//2,:w//2];u=(xl+.5)/(w//2);v=(yl+.5)/(h//2)
    fullx=np.minimum((u*w).astype(int),w-1);fully=np.minimum((v*h).astype(int),h-1)
    wrong=np.stack([(u*2-1)/rt.scale,(v*2-1)/rt.scale,-np.ones_like(u)],-1)*(-positions[fully,fullx,2,None])
    check('unsnapped negative control '+str((w,h)),np.max(abs(wrong@normal-plane))>.01,float(np.max(abs(wrong@normal-plane))))

from buffer_encoding import material24,rgb24
data=rt.flat((.7,.7,.7))
data.update(depthtex1=data['depthtex0'],colortex4=constant([.75,.04,0,0],64,64),
            colortex2=constant([.25,.4,.6,1],32,32),colortex12=constant([1.,1.,1.,8],32,32),
            colortex8=constant([.05,.05,.05,0],32,32),colortex11=constant([.05,.05,.05,.0025],32,32))
data['colortex9']=constant([0,0,material24([.75,.04,0,0]),rgb24([((.7+.055)/1.055)**2.4]*3)],32,32)
for mode in (1,):
    program=rt.program('composite2',{})
    for marker in (-4.,4.):
        inp={**data,'colortex13':constant([.5,.5,1,marker],32,32)}
        _,out=rt.draw(program,inp,32,32,outputs=6 if mode else 3,full_precision=(1,3,4,5) if mode else (2,),value_overrides={'frameCounter':10,'previousCameraPosition':(0.,0.,0.)})
        age=out[2 if mode else 1][16,16,3];expected=9 if (marker<0)==bool(mode) else 1
        check('history isolation mode '+str(mode)+' marker '+str(marker),age==expected,float(age))
        check('history output sign mode '+str(mode)+' marker '+str(marker),bool(out[4 if mode else 2][16,16,3]<0)==bool(mode),float(out[4 if mode else 2][16,16,3]))
    rt.gl['DeleteProgram'](program)

out=HERE/'ptgi-evidence';out.mkdir(exist_ok=True)
(out/'pipeline.json').write_text(json.dumps({'checks':records,'all_passed':True},indent=2)+'\n')
print('PT PIPELINE ALL PASSED',flush=True)
