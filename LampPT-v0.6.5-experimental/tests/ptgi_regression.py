#!/usr/bin/env python3
"""Monte Carlo transport checks against independent analytic expectations.

Runs real pack GLSL and terrain capture on Mesa. This is not a Minecraft or
NVIDIA test, and probe sample counts are validation counts, not game settings.
"""
import json
import sys
from pathlib import Path
import numpy as np
from ptgi_runtime import *

OUT=Path(__file__).parent/'ptgi-evidence';OUT.mkdir(exist_ok=True)
records={}
def check(name,passed,details=None):
    assert passed,(name,details)
    records[name]=True if details is None else details
    print('PT PASS:',name,details if details is not None else '',flush=True)
def mean(a):return a[:,:,:3].mean((0,1))

def scattering():
    f=Fixture()
    # White-furnace hemispherical reflectance: all incident radiance is one.
    for rough,f0,albedo in [(.8,.04,(.7,.7,.7)),(.2,.04,(1.,1.,1.)),(.2,-1.,(.8,.5,.2))]:
        a=f.draw(size=(256,128),probeMode=1,probeMaterial=(rough,f0,0.),probeAlbedo=albedo)
        energy=mean(a)
        check('white furnace '+str((rough,f0)),np.all(energy>0)&np.all(energy<=1.02),energy.tolist())
        if f0<0:check('metal spectral energy',np.max(abs(energy/np.asarray(albedo)-energy[0]/albedo[0]))<.04)
    # Fresnel evaluated independently in double precision over incident angles.
    a=f.draw(size=(257,1),probeMode=5)[0,:,0];c=(np.arange(257)+.5)/257
    ct=np.sqrt(1-(1/1.5)**2*(1-c*c))
    expected=.5*(((c-1.5*ct)/(c+1.5*ct))**2+((1.5*c-ct)/(1.5*c+ct))**2)
    check('dielectric Fresnel matches analytic reference',np.max(abs(a-expected))<2e-6,float(np.max(abs(a-expected))))
    # Near-smooth glass directions must obey Snell, including the correct side.
    d=(.5,-np.sqrt(.75),0.)
    a=f.draw(size=(256,128),probeMode=2,probeMaterial=(.001,.04,0.),probeDirection=d)
    transmitted=a[:,:,3]>.5;angles=a[transmitted,:3].mean(0)
    expected=np.array([.5/1.5,-np.sqrt(1-(.5/1.5)**2),0.])
    check('Snell transmission direction',np.linalg.norm(angles-expected)<.005,angles.tolist())
    F=.5*(((np.sqrt(.75)-1.5*-expected[1])/(np.sqrt(.75)+1.5*-expected[1]))**2+((1.5*np.sqrt(.75)+expected[1])/(1.5*np.sqrt(.75)-expected[1]))**2)
    check('Fresnel event frequency',abs((~transmitted).mean()-F)<.008,float((~transmitted).mean()))
    a=f.draw(size=(256,128),probeMode=2,probeEtaI=1.5,probeEtaT=1.,probeMaterial=(.001,.04,0.),probeDirection=(.8660254,-.5,0.))
    check('total internal reflection',a[:,:,3].mean()<.001 and a[:,:,1].mean()>.49,float(a[:,:,3].mean()))

def lights():
    f=Fixture({'PT_BOUNCES':2})
    dark=f.draw();check('unlit world emits zero energy',dark[:,:,:3].max()==0)
    lamp=box((0,2,-3),(1,3,-2),color=(1.,1.,1.),block=10001)
    f.capture(lamp)
    direct=f.draw(probeMode=4);lit=f.draw()
    check('area emitter lights receiver',mean(direct)[0]>.03 and mean(lit)[0]>.02,{'NEE':mean(direct).tolist(),'path':mean(lit).tolist()})
    check('warm source color survives transport',mean(lit)[0]>mean(lit)[1]*1.8 and mean(lit)[1]>mean(lit)[2]*3)
    # A nearby complete ceiling cannot conduct the buried emitter to its top.
    ceiling=[]
    for x in range(-1,2):
        for z in range(-4,-1):ceiling+=box((x,1,z),(x+1,1.25,z+1),owner=(x,1,z))
    f.capture(lamp+ceiling)
    blocked=f.draw(probeMode=4)
    check('slab blocks the area light',blocked[:,:,:3].max()==0,float(blocked[:,:,:3].max()))
    # The emitter is behind the camera; continuation/reflection must still find it.
    f.capture(box((-1,-1,1),(1,1,2),owner=(0,0,1),color=(1.,1.,1.),block=10002))
    mirror=f.draw(probePosition=(0.,0.,-2.),probeNormal=(0.,0.,1.),probeMaterial=(.025,-1.,0.),probeAlbedo=(.8,.8,.8))
    check('offscreen emitter appears in reflection',mean(mirror)[2]>.1,mean(mirror).tolist())
    # Native source registration must survive a dark atlas midpoint. Flame UVs
    # are bright on one half; captured material cannot be zero everywhere.
    atlas=np.ones((8,8,4),np.float32);atlas[:,:5,:3]=.03
    f.capture(lamp,rt.texture(atlas))
    stem=f.draw(probeMode=4)
    check('dark midpoint does not delete luminous artwork',mean(stem)[0]>.005,mean(stem).tolist())

def light_distribution():
    f=Fixture()
    f.capture(box((0,3,-3),(1,4,-2),block=10204,color=(1.,1.,1.))+
              box((0,-3,-3),(1,-2,-2),block=10204,color=(1.,1.,1.)))
    a=f.draw(size=(256,128),probeMode=9,probePosition=(.5,.5,-2.5))
    upper=a[:,:,0]>0
    check('source sampler retains both hemispheres',upper.mean()>.9 and upper.mean()<.99,float(upper.mean()))
    check('selected and MIS source PDFs agree',np.max(abs(a[:,:,1]-a[:,:,2]))<1e-6,float(np.max(abs(a[:,:,1]-a[:,:,2]))))
    indices=a[:,:,3].astype(int)-1
    frequencies=np.bincount(indices.ravel(),minlength=24)/indices.size
    expected=np.array([a[:,:,1][indices==i].mean() if np.any(indices==i) else 0 for i in range(24)])
    check('source probabilities match per-triangle frequencies',np.max(abs(frequencies-expected))<.008,
          {'max_error':float(np.max(abs(frequencies-expected))), 'represented_triangles':int((frequencies>0).sum())})
    check('nonzero PDF preserves all triangle support',int((frequencies>0).sum())==24)

def media():
    f=Fixture({'PT_BOUNCES':8,'GLASS_ROUGHNESS':'0.001','WATER_WAVES':0})
    glass=box((-1,-1,-3),(1,1,-2),owner=(0,0,-3),color=(1.,1.,1.),block=10010)
    f.capture(glass)
    entering=f.draw(size=(1,1),probeMode=3,probePosition=(.1,.1,-1.),probeDirection=(0.,0.,-1.))[0,0]
    leaving=f.draw(size=(1,1),probeMode=3,probePosition=(.1,.1,-2.2),probeDirection=(0.,0.,-1.))[0,0]
    check('captured glass has oriented entry and exit surfaces',entering[0]==1 and leaving[0]==1 and entering[2]>.9 and leaving[2]<-.9,{'entry':entering.tolist(),'exit':leaving.tolist()})
    # View an area source through a slab. This exercises both medium interfaces,
    # not the hybrid transparent compositor or a screen-color lookup.
    light=box((-1,-1,-5),(1,1,-4),owner=(0,0,-5),color=(1.,1.,1.),block=10204)
    f.capture(light+glass)
    clear=f.draw(size=(256,128),probePosition=(.01,.01,-2.),probeNormal=(0.,0.,1.),probeMaterial=(.001,.04,0.),probeKind=2.,probeAlbedo=(1.,1.,1.))
    redglass=box((-1,-1,-3),(1,1,-2),owner=(0,0,-3),color=(1.,.12,.04),block=10013)
    f.capture(light+redglass)
    red=f.draw(size=(256,128),probePosition=(.01,.01,-2.),probeNormal=(0.,0.,1.),probeMaterial=(.001,.04,0.),probeKind=2.,probeAlbedo=(1.,.012,.003))
    check('clear glass preserves source radiance',mean(clear).min()>.5,mean(clear).tolist())
    check('glass absorption tints transported light',mean(red)[0]>mean(red)[1]*2 and mean(red)[1]>mean(red)[2],mean(red).tolist())
    # Absorption from the underwater camera to a directly visible emitter has
    # the exact Beer-Lambert solution when scattering is disabled.
    f.capture([])
    for distance in (1.,4.):
        a=f.draw(size=(32,16),probePosition=(0.,0.,-distance),probeNormal=(0.,0.,1.),probeMaterial=(.75,.04,1.),probeKind=24.,probeAlbedo=(1.,1.,1.),isEyeInWater=1)
        settings=(rt.ROOT/'lib/settings.glsl').read_text()
        import re
        val=lambda k:float(re.search(r'^#define '+k+r' (\S+)',settings,re.M)[1])
        extinction=np.maximum(1-np.array([val('WATER_R'),val('WATER_G'),val('WATER_B')]),.02)*val('WATER_ABSORPTION')
        expected=8.0*val('SMALL_LIGHT_BOOST')*val('EMISSIVE_STRENGTH')*np.exp(-extinction*distance)  # Documented end-rod radiance scale.
        check('Beer-Lambert distance '+str(distance),np.max(abs(mean(a)-expected))<.001,{'actual':mean(a).tolist(),'expected':expected.tolist()})

def transport():
    f=Fixture({'PT_BOUNCES':4,'SUN_INTENSITY':'1.0'})
    sun=f.draw(size=(256,128),sunPosition=(0.,1.,0.),shadowLightPosition=(0.,1.,0.))
    check('unoccluded sunlight has positive energy',mean(sun).min()>.2,mean(sun).tolist())
    # Compare single-event direct transport with additional bounces from red
    # diffuse geometry. The white source itself remains unchanged.
    vertices=box((-2,2,-3),(-1,3,-2),block=10204,color=(1.,1.,1.))
    for y in range(-1,3):
        for z in range(-4,-1):vertices+=box((1,y,z),(2,y+1,z+1),color=(.95,.02,.01))
    f=Fixture({'PT_BOUNCES':1});f.capture(vertices)
    short=f.draw(size=(256,128))
    f=Fixture({'PT_BOUNCES':4});f.capture(vertices)
    long=f.draw(size=(256,128))
    check('diffuse multi-bounce color transport',mean(long)[0]>mean(long)[1]*1.15 and mean(long)[0]>mean(short)[0]*1.1,
          {'one_event':mean(short).tolist(),'four_events':mean(long).tolist()})
    # Surface-caustic paths: camera in water -> diffuse receiver -> refractive
    # water boundary -> finite sun disc. No projected caustic function is called.
    options={'PT_BOUNCES':4,'SUN_INTENSITY':'1.0','WATER_ROUGHNESS':'0.001',
             'WATER_ABSORPTION':'0.0','WATER_WAVES':0,'PT_SUN_ANGLE':'0.0186'}
    f=Fixture(options)
    surface=[]
    for x in range(-4,4):
        for z in range(-5,4):
            surface+=box((x,.5,z),(x+1,.5,z+1),owner=(x,0,z),block=10000)[24:30]
    f.capture(surface)
    values=dict(size=(256,256),probePosition=(-1.,-1.,-3.),probeU=(2.,0.,0.),probeV=(0.,0.,2.),
                sunPosition=(0.,1.,0.),shadowLightPosition=(0.,1.,0.),isEyeInWater=1)
    flat=f.draw(**values)
    check('sun reaches underwater receiver through traced refraction',mean(flat).min()>.2,mean(flat).tolist())
    f=Fixture({**options,'WATER_WAVES':1});f.capture(surface)
    waves=f.draw(**values)
    check('wave normals change refractive light paths',np.max(abs(waves[:,:,:3]-flat[:,:,:3]))>1.0 and mean(waves).min()>.02,
          {'flat':mean(flat).tolist(),'waves':mean(waves).tolist(),'max_difference':float(abs(waves-flat).max())})
    f.capture([dict(v,attributes={**v['attributes'],'mc_Entity':(0,0,0,0)}) for v in surface])
    opaque=f.draw(**values)
    check('opaque replacement closes underwater light path',mean(opaque).max()<.005,mean(opaque).tolist())

def volume():
    f=Fixture({'PT_VOLUMETRICS':1,'PT_AIR_DENSITY':'0.008'})
    a=f.draw(size=(128,128),probeValid=0,probePosition=(0.,0.,-4.))
    check('unlit participating medium stays black',a[:,:,:3].max()==0,float(a[:,:,:3].max()))
    f.capture(box((1,0,-6),(2,1,-5),block=10204,color=(1.,1.,1.)))
    lit=f.draw(size=(256,128),probeValid=0,probePosition=(0.,0.,-4.))
    check('off-axis lamp lights participating medium',mean(lit).min()>.00001,mean(lit).tolist())
    f=Fixture({'PT_VOLUMETRICS':0,'PT_AIR_DENSITY':'0.008'})
    f.capture(box((1,0,-6),(2,1,-5),block=10204,color=(1.,1.,1.)))
    off=f.draw(size=(128,128),probeValid=0,probePosition=(0.,0.,-4.))
    check('scattering switch removes medium light paths',off[:,:,:3].max()==0,float(off[:,:,:3].max()))

groups={'scattering':scattering,'lights':lights,'media':media,'transport':transport,'volume':volume,'distribution':light_distribution}
if __name__=='__main__':
    group=sys.argv[1]
    groups[group]()
    (OUT/(group+'.json')).write_text(json.dumps({'checks':records,'all_passed':True},indent=2)+'\n')
    print('PT GROUP PASSED',group,flush=True)
