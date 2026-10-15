"""Equal luminous intensity for all four held torch families."""
import json
from pathlib import Path
import numpy as np
import gl_runtime as rt
from world_runtime import fragment
p=fragment(Path(__file__).with_name('hand_balance_probe.fsh'))
r=[]
for id,native in [(20200,14),(20201,10),(20202,7),(20203,14)]:
 a=rt.draw(p,{},1,1,full_precision=(0,),value_overrides={'heldItemId':id,'heldBlockLightValue':native})[1][0][0,0,:3]
 r.append(a.tolist())
y=np.array(r)@np.array([.2126,.7152,.0722]);assert np.allclose(y,y[0],rtol=1e-5)
(Path(__file__).parent/'ptgi-evidence/v075-hand-balance.json').write_text(json.dumps({'rgb':r,'luminance':y.tolist(),'passed':True},indent=2)+'\n')
print('PASS four held torch types have equal reference luminance')
