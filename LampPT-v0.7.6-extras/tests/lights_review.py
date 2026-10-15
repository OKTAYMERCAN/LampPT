"""Production GLSL source mapping, held-light off/on/two hands and occlusion."""
import json
from pathlib import Path
import numpy as np
import gl_runtime as rt
from world_runtime import fragment
from ptgi_runtime import Fixture,box
out=Path(__file__).parent/'ptgi-evidence';out.mkdir(exist_ok=True)
p=fragment(Path(__file__).with_name('source_probe.fsh'),{})
def source(i,native=0,color=(1.,1.,1.)):
 return rt.draw(p,{},4,4,full_precision=(0,),value_overrides={'sourceId':float(i),'sourceNative':float(native),'sourceColor':color})[1][0][0,0,:].tolist()
r={name:source(i,n,c) for name,i,n,c in [
 ('torch',10200,14,(1.,1.,1.)),('lamp',10302,15,(1.,1.,1.)),('candle',10301,3,(1.,1.,1.)),('black_candle',10301,3,(.01,.01,.01)),
 ('copper',10300,14,(.2,1.,.4)),('crying_obsidian',10303,10,(.3,.04,.45)),
 ('lichen',10304,7,(.2,.4,.2)),('firefly',10305,2,(.5,.5,.2)),('copper_bulb_oxidized',10306,4,(1.,1.,1.)),
 ('redstone_ore',10307,9,(.8,.03,.02)),('glow_berries',10308,14,(.8,.4,.03)),('sculk',10309,6,(.1,.7,.8)),('anchor',10310,15,(.5,.1,.8)),('native_dark',0,10,(.1,.05,.2)),('unlit',0,0,(1.,1.,1.))]}
assert all(sum(v[:3])>0 for k,v in r.items() if k!='unlit'),r
assert sum(r['unlit'][:3])==0
assert r['copper'][1]>r['copper'][0] and r['crying_obsidian'][2]>r['crying_obsidian'][0]
f=Fixture({'HAND_LIGHT':1})
kw=dict(probeMode=4,probePosition=(0.,0.,-2.),probeNormal=(0.,0.,1.),probeDirection=(0.,0.,-1.))
def hand(**k):return f.draw(size=(4,4),**kw,**k)[0,0,:3]
empty=hand(heldItemId=-1,heldItemId2=-1,heldBlockLightValue=0,heldBlockLightValue2=0)
main=hand(heldItemId=20001,heldItemId2=-1,heldBlockLightValue=14,heldBlockLightValue2=0)
off=hand(heldItemId=-1,heldItemId2=20005,heldBlockLightValue=0,heldBlockLightValue2=14)
both=hand(heldItemId=20001,heldItemId2=20005,heldBlockLightValue=14,heldBlockLightValue2=14)
assert np.max(empty)==0 and main.sum()>.1 and off.sum()>.1
assert np.allclose(both,main+off,rtol=1e-5)
f.capture(box((-2,-2,-1.2),(2,2,-1.0)))
blocked=hand(heldItemId=20001,heldItemId2=-1,heldBlockLightValue=14,heldBlockLightValue2=0)
assert blocked.sum()<1e-8,blocked
f=Fixture({'HAND_LIGHT':0})
disabled=hand(heldItemId=20001,heldItemId2=20005,heldBlockLightValue=14,heldBlockLightValue2=14)
assert disabled.sum()==0
record={'all_passed':True,'sources_rgba':r,'hand_empty':empty.tolist(),'hand_main':main.tolist(),'hand_offhand':off.tolist(),'hand_both':both.tolist(),'hand_blocked':blocked.tolist(),'hand_disabled':disabled.tolist(),'scope':__doc__+' Mesa offscreen, not a Minecraft runtime test.'}
(out/'v073-lights.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
