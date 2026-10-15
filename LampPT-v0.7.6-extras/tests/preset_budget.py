#!/usr/bin/env python3
"""Audit profile budgets and actual image/dispatch scale declarations.

Nominal path-pixel counts are not measured FPS and exclude adaptive edge repair,
secondary work, base-grid optical replacement, capture, BVH builds, full-resolution rasterization and filtering.
"""
import json,re,subprocess
from pathlib import Path
import gl_runtime as rt
from pipeline_routing import active_properties
R=rt.ROOT
props=(R/'shaders.properties').read_text()
profiles={k:dict(v.split(':',1) for v in s.split()) for k,s in re.findall(r'^profile\.(\w+)=(.*)$',props,re.M)}
assert len({tuple(sorted(p)) for p in profiles.values()})==1,'Switching profiles must replace the same controlled keys'
components=[('Direct','HRR_SHADOWS','composite1'),('GI','HRR_GI','composite1_a'),('Reflect','HRR_REFLECTIONS','composite1_b'),('Cloud','HRR_CLOUDS','composite1_c')]
for res in [25,33,40,50,59,67,77,100]:
    for half in [0,1]:
        opts={'PT_RESOLUTION':res,'PT_SHARED_PATHS':0,**{flag:half for _,flag,_ in components}}
        active=active_properties(opts)
        images={n:(float(x),float(y)) for n,x,y in re.findall(r'^image\.(\w+)\s*=\s*\w+ rgba rgba32f float false true (\S+) (\S+)',active,re.M)}
        expected=res/100*(.5 if half else 1)
        assert len(images)==8 and all(x==y==expected for x,y in images.values()),(res,half,images)
        for comp,flag,stage in components:
            source=rt.source(R/(stage+'.csh'),opts)
            source=re.sub(r'^\s*#(?:version|extension).*$', '',source,flags=re.M)
            source=subprocess.run(['cpp','-P','-undef','-nostdinc','-'],input=source,text=True,capture_output=True,check=True).stdout
            m=re.search(r'workGroupsRender=vec2\(([\d.]+),([\d.]+)\)',source)
            assert m and all(float(x)==expected for x in m.groups()),(res,half,stage)
records={}
for name,p in profiles.items():
    assert all(p[k]=='1' for _,k,_ in components)
    assert p['PT_SAMPLES']==p['PT_LIGHT_SAMPLES']==p['PT_WATER_SAMPLES']=='1'
    assert p['NORMAL_MAPS']==p['POM']==p['POWDER_EMISSION']=='0'
    assert p['PT_SHARED_PATHS']==p['PT_TEMPORAL']==p['PT_DENOISE']==p['PT_MOTION_STABILIZATION']=='1'
    assert p['PT_REFLECTIONS']==('0' if name=='LOW' else '1')
    assert p['VOLUMETRIC_CLOUDS']==('0' if name=='LOW' else '1')
    scale=float(p['PT_RESOLUTION'])/200
    sizes=[int(1920*scale),int(1080*scale)]
    buffers=re.findall(r'bufferObject\.\d+\s*=\s*(\d+)',active_properties(p))
    records[name]={'base_scale_percent':int(p['PT_RESOLUTION']),'component_scale_percent':scale*100,
      'component_size_at_1080p':sizes,'nominal_shared_surface_paths':sizes[0]*sizes[1],
      'scattering_events':int(p['PT_BOUNCES']),'transmission_events':int(p['PT_TRANSMISSION_DEPTH']),
      'scene_buffer_MiB':sum(map(int,buffers))/1048576,'capture_radius':float(p['shadowDistance']),'clear_optics':int(p['PT_OPTICAL_DETAIL']),
      'cloud_density_shadow_steps':[int(p['CLOUD_STEPS']),int(p['CLOUD_SHADOW_STEPS'])]}
assert records['ULTRA']['nominal_shared_surface_paths']==129600
report={'all_passed':True,'profiles':records,'image_dispatch_configurations':64,
 'old_ultra_nominal_surface_paths_at_1080p':1920*1080*4,
 'new_ultra_nominal_surface_paths_at_1080p':129600,'ultra_nominal_primary_sample_reduction_factor':64,
 'scope':__doc__}
print(json.dumps(report,indent=2),flush=True)
(Path(__file__).parent/'ptgi-evidence/v072-preset-budget.json').write_text(json.dumps(report,indent=2)+'\n')
