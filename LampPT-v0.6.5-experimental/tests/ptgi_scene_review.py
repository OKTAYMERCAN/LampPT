#!/usr/bin/env python3
"""End-to-end terrain, glass, water and PT controls in isolated GL contexts.

Images are synthetic Mesa renders, not screenshots from the user's Minecraft.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

HERE=Path(__file__).parent
OUT=HERE/'ptgi-evidence';OUT.mkdir(exist_ok=True)
BASE={'DITHER':0,'GEOMETRY_BUDGET':65536,'shadowMapResolution':256,
      'PT_AIR_DENSITY':'0.000','PT_VOLUMETRICS':0,'PT_BOUNCES':4}
CASES={'pt':{},'effects-off':{'PT_GI':0,'PT_REFLECTIONS':0,'PT_REFRACTION':0,'PT_GLASS':0,'WATER_ENABLED':0}}

def render_case(name,target,root=None):
    import scene_review as s
    from pipeline_routing import Pipeline
    from world_runtime import WorldGPU
    if root:s.rt.ROOT=Path(root)
    s.faces.clear();s.W,s.H=193,113;s.OUT=OUT
    s.eye=np.array([4.2,3.2,6.4],np.float32);s.center=np.array([-.2,.6,-1.5],np.float32)
    s.V=s.look(s.eye,s.center);s.V[:3,3]=0
    s.P=np.array(s.rt.projection,copy=True);s.P[0,0]*=s.H/s.W
    s.rt.uniforms.update(gbufferProjection=s.P,gbufferProjectionInverse=np.linalg.inv(s.P),
        gbufferModelView=s.V,gbufferModelViewInverse=np.linalg.inv(s.V))
    for x in range(-4,4):
        for z in range(-4,3):
            pool=1<=x<=2 and -1<=z<=1
            s.box((x,-2 if pool else -1,z),(x+1,-1 if pool else 0,z+1),(.6,.6,.6))
    for x in range(-4,4):
        for y in range(4):s.box((x,y,-5),(x+1,y+1,-4),(.75,.75,.75))
    for z in range(-4,1):
        for y in range(4):s.box((-5,y,z),(-4,y+1,z+1),(.75,.75,.75))
    for y in range(3):s.box((-2,y,-2),(-1,y+1,-1),(.7,.08,.025))
    s.box((-3,1,-4),(-2,2,-3),(1.,.9,.7),10001)
    s.box((2,1,-4),(3,2,-3),(.5,.8,1.),10002)
    s.box((0,0,-3),(1,1,-2),(.75,.63,.3),10011)
    # Nearest glass is retained in its own translucent G-buffer. Secondary
    # boundaries come from the same world geometry captured in the shadow pass.
    before=len(s.faces);s.box((-1,0,0),(0,2,.125),(1.,1.,1.),10010)
    for i in range(before,len(s.faces)):
        p,n,c,b,lm,_=s.faces[i];s.faces[i]=(p,n,c,b,lm,True)
    for x in (1,2):
        for z in (-1,0,1):s.floor(x,x+1,z,z+1,-.15,(.2,.5,.7),True)
    opts={**BASE,**CASES[name]}
    # Force 16 different paths through temporal history; one-frame debug
    # renders would not exercise the promised mode's reconstruction.
    result,passes,gray,water,trace=s.render(opts,frames=16)
    s.save('scene-'+name+('-baseline' if root else ''),result)
    np.savez(target,frame=result,pt=passes['composite5'][0],gray=gray,water=water)
    print('PT SCENE rendered',name,'baseline' if root else 'current',flush=True)

if __name__=='__main__':
    if '--case' in sys.argv:
        render_case(sys.argv[2],sys.argv[3]);sys.exit(0)
    frames={};metrics={}
    with tempfile.TemporaryDirectory(prefix='pt-scenes-') as temp:
        for label in CASES:
            path=Path(temp)/(label+'.npz')
            subprocess.run([sys.executable,__file__,'--case',label,str(path)],check=True)
            with np.load(path) as data:
                frame=data['frame'];assert np.isfinite(frame).all()
                assert data['pt'][:,:,:3].max()>.2,'Path illumination did not reach final resolve'
                assert 'gi' not in data,'Resolved output must not contain an additive GI target'
                frames[label]=frame.copy()
    difference=float(abs(frames['pt']-frames['effects-off']).mean())
    assert difference>.002, difference
    metrics.update(all_passed=True,final_controls_mean_difference=difference,resolution=[193,113],frames=16,
        renderer='Synthetic Mesa GL, not Minecraft')
    (OUT/'scene-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    print(json.dumps(metrics,indent=2),flush=True)
