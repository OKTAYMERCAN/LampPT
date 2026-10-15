#!/usr/bin/env python3
"""Transport partition, real independent image sizes, glass alpha, and BVH slabs.
All measurements use production GLSL on Mesa; this does not launch Minecraft.
"""
import json
from pathlib import Path
import numpy as np
from ptgi_runtime import Fixture,box,rt
from pipeline_routing import Pipeline
from world_runtime import fragment
OUT=Path(__file__).parent/'ptgi-evidence';records={}
def check(name,ok,details):
 assert ok,(name,details)
 records[name]=details;print('HRR PASS',name,details,flush=True)
def means(a):return a[:,:,:3].mean((0,1))
def compare(f,name,**kw):
 a=f.draw(size=(128,64),probeMode=0,**kw)[:,:,:3];b=f.draw(size=(128,64),probeMode=12,**kw)[:,:,:3]
 se=np.sqrt((a.var((0,1))+b.var((0,1)))/(128*64))
 error=np.abs(a.mean((0,1))-b.mean((0,1)))
 check(name,np.all(error<5*se+.025*np.maximum(a.mean((0,1)),.03)),{'reference':a.mean((0,1)).tolist(),'components':b.mean((0,1)).tolist(),'error':error.tolist(),'5_standard_errors':(5*se).tolist()})
f=Fixture({'PT_BOUNCES':3,'PT_SKYLIGHT':1})
compare(f,'sky diffuse/specular partition',skyColor=(.5,.5,.5))
lamp=box((0,2,-3),(1,3,-2),color=(1.,1.,1.),block=10001)
wall=box((1,-1,-4),(1.5,3,-1),color=(.8,.08,.025))
f.capture(lamp+wall)
compare(f,'emitter and colored bounce partition')
f.capture(box((-1,-1,1),(1,1,2),block=10204,color=(1.,1.,1.)))
compare(f,'metal reflection partition',probePosition=(0.,0.,-2.),probeNormal=(0.,0.,1.),probeMaterial=(.18,-1.,0.),probeAlbedo=(.8,.5,.2))
f=Fixture({'PT_REFLECTIONS':0});f.capture(lamp)
a=f.draw(probeMode=15)
check('reflection switch eliminates opaque specular contribution',float(a[:,:,:3].max())==0,float(a[:,:,:3].max()))
# Parallel axes on a BVH slab boundary must not produce NaN or a false miss.
f.capture(box((0,0,-3),(1,1,-2)))
for origin,want in [((0.,.5,0.),1),((1.,.5,0.),1),((1.001,.5,0.),0),((-.001,.5,0.),0)]:
 a=f.draw(size=(1,1),probeMode=3,probePosition=origin,probeDirection=(0.,0.,-1.))[0,0]
 check('parallel slab '+str(origin),np.isfinite(a).all() and int(a[0])==want,a.tolist())
# All four toggles change only their own physical output allocation.
base={k:0 for k in ['HRR_SHADOWS','HRR_GI','HRR_REFLECTIONS','HRR_CLOUDS']}
for toggle,component in [('HRR_SHADOWS','Direct'),('HRR_GI','GI'),('HRR_REFLECTIONS','Reflect'),('HRR_CLOUDS','Cloud')]:
 p=Pipeline({},127,75,{'PT_RESOLUTION':40,**base,toggle:1})
 sizes={name:v[2:] for name,v in p.images.items()}
 for name,size in sizes.items():assert size==((25,15) if name in ['pt'+component+'Image','pt'+component+'GuideImage'] else (50,30)),(toggle,name,size)
 check('independent '+toggle,True,sizes)
# Raster a clear glass face with a fully transparent BLACK atlas texel. This
# reproduces the vanilla cutout center ignored by older opaque-white tests.
f=Fixture({'PT_BOUNCES':2,'GLASS_ROUGHNESS':'0.001','PT_SUNLIGHT':0})
glass=box((-1,-1,-.6),(1,1,-.5),block=10010,color=(1,1,1))
light=box((-2,-2,-3),(2,2,-2),block=10204,color=(1,1,1))
f.capture(glass+light)
transparent=rt.texture(rt.constant([0,0,0,0],4));white=f.white
shader=rt.program('gbuffers_water',f.options)
tex,out=rt.draw(shader,{'texture':transparent,'lightmap':white,'specular':rt.texture(rt.constant([0,0,0,1],4))},32,32,vertices=glass[:6],outputs=4,full_precision=(0,1,2,3))
check('zero-alpha glass keeps optical metadata',out[2][16,16,3]==1 and out[3][16,16,3]==1,{'glass':out[2][16,16].tolist(),'material':out[3][16,16].tolist()})
inputs={'colortex0':tex[0],'colortex14':tex[1],'colortex15':tex[2],'colortex5':tex[3],
 'depthtex1':rt.texture(np.ones((32,32))),'colortex1':rt.texture(np.zeros((32,32,4))),
 'colortex3':white,'colortex4':rt.texture(rt.constant([.5,.04,0,0],32)), 'colortex10':rt.texture(rt.constant([0,1,0,1],32))}
opts={**f.options,'PT_RESOLUTION':100,'PT_SHARPEN':0,'DITHER':0,'BLOOM_ENABLED':0}
p=Pipeline(inputs,32,32,opts)
for frame in range(8):
 rt.values['frameCounter']=frame
 for name in ['composite1','composite2','composite3','composite4','composite5','composite6','composite7']:values=p.pass_(name,opts)
image=values[0][:,:,:3]
check('light visible through zero-alpha glass in full pipeline',np.isfinite(image).all() and image[16,16].min()>.2,{'center':image[16,16].tolist(),'mean':image.mean((0,1)).tolist()})
# Transmission remains active when reflections are disabled (not a black pane).
opts={**opts,'PT_REFLECTIONS':0};p=Pipeline(inputs,32,32,opts)
for name in ['composite1','composite2','composite3','composite4','composite5','composite6','composite7']:values=p.pass_(name,opts)
check('reflections off preserves glass transmission',values[0][16,16,:3].min()>.2,values[0][16,16,:3].tolist())
(OUT/'v072-hrr.json').write_text(json.dumps({'all_passed':True,'checks':records,'scope':'Synthetic Mesa GLSL, not Minecraft'},indent=2)+'\n')
