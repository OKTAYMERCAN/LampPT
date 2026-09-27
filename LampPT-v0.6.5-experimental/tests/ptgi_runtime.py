"""Small analytic PT fixtures, using production geometry capture and GLSL."""
from pathlib import Path
import numpy as np
import gl_runtime as rt
from world_runtime import WorldGPU, fragment

BASE={'VOLUMETRIC_CLOUDS':0,'PT_AIR_DENSITY':'0.000',
      'PT_VOLUMETRICS':0,'CUSTOM_SKY':0,'SUN_INTENSITY':'0.0','MOON_INTENSITY':'0.0',
      'PT_DENOISE':0,'PT_TEMPORAL':0,'PT_BOUNCES':4,'PT_SAMPLES':1}

def box(lo,hi,owner=None,color=(.7,.7,.7),block=0,uv=None):
    x,y,z=lo;X,Y,Z=hi
    infer_owner=owner is None
    owner=np.floor((np.asarray(lo)+hi)*.5) if owner is None else np.asarray(owner)
    # Flat synthetic water tops belong to the block below an integer boundary,
    # matching Sodium's at_midBlock owner (not a zero-height block above it).
    if block==10000 and abs(Y-y)<1e-8 and infer_owner:owner[1]=np.floor(y-.001)
    uv=uv or [(0,0),(1,0),(1,1),(0,1)]
    faces=[([(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],(0,0,1)),
           ([(X,y,z),(x,y,z),(x,Y,z),(X,Y,z)],(0,0,-1)),
           ([(X,y,Z),(X,y,z),(X,Y,z),(X,Y,Z)],(1,0,0)),
           ([(x,y,z),(x,y,Z),(x,Y,Z),(x,Y,z)],(-1,0,0)),
           ([(x,Y,Z),(X,Y,Z),(X,Y,z),(x,Y,z)],(0,1,0)),
           ([(x,y,z),(X,y,z),(X,y,Z),(x,y,Z)],(0,-1,0))]
    return [{'position':np.asarray(points[i]),'normal':normal,'color':(*color,1.),'uv':uv[i],
      'attributes':{'mc_Entity':(block,0,0,0),'at_midBlock':(*(owner+.5-points[i])*64.,0.),'mc_midTexCoord':(.5,.5)}}
      for points,normal in faces for i in [0,1,2,0,2,3]]

class Fixture:
    def __init__(self,options=None):
        # Every stage must agree on the fixed SSBO array layout, including
        # parent links after the triangle-budget-sized children array.
        self.options={'GEOMETRY_BUDGET':65536,**BASE,**(options or {})}
        self.world=WorldGPU(64,self.options)
        self.program=fragment(Path(__file__).with_name('ptgi_probe.fsh'),self.options)
        self.white=rt.texture(rt.constant([1,1,1,1],4))
        self.capture([])
    def capture(self,vertices,atlas=None,specular=(0.,0.,0.,1.)):
        self.world.voxelize_vertices(vertices,atlas=atlas or self.white,specular=specular)
    def draw(self,size=(128,64),**kw):
        rt.resource_binders[:]=[self.world.bind]
        values={'probePosition':(.5,-.5,-2.5),'probeNormal':(0.,1.,0.),'probeAlbedo':(.7,.7,.7),
                'probeMaterial':(.75,.04,0.),'probeKind':0.,'probeMode':0,'probeValid':1,
                'probeEtaI':1.,'probeEtaT':1.5,'probeDirection':(0.,-1.,0.),
                'probeU':(0.,0.,0.),'probeV':(0.,0.,0.),'skyColor':(0.,0.,0.),'frameCounter':0,
                'cameraPosition':(0.,0.,0.),'isEyeInWater':0,**kw}
        return rt.draw(self.program,{},*size,full_precision=(0,),value_overrides=values)[1][0]
