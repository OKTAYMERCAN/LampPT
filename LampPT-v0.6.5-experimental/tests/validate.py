#!/usr/bin/env python3
"""Pack metadata and real OpenGL link validation. Does not launch Minecraft."""
import json,re,subprocess,sys
from pathlib import Path
import gl_runtime as rt
from world_runtime import compute
from pipeline_routing import active_properties,targets
R=rt.ROOT
settings=(R/'lib/settings.glsl').read_text();props=(R/'shaders.properties').read_text()
options={k:(d,a.split()) for k,d,a in re.findall(r'^#define (\w+) (\S+) // \[([^\]]+)\]',settings,re.M)}
for k,d,a in re.findall(r'const (?:int|float) (\w+)\s*=\s*([^;]+); // \[([^\]]+)\]',(R/'lib/shadow_settings.glsl').read_text()):options[k]=(d,a.split())
profiles={k:dict(v.split(':',1) for v in vals.split()) for k,vals in re.findall(r'^profile\.(\w+)=(.*)$',props,re.M)}
assert set(profiles)=={'LOW','MED','HIGH','ULTRA'}
for name,p in profiles.items():
    assert p['NORMAL_MAPS']==p['POM']==p['POWDER_EMISSION']=='0'
    for k,v in p.items():assert k in options and v in options[k][1],(name,k,v)
for k,(d,a) in options.items():assert d in a,(k,d,a)
for k,v in profiles['MED'].items():assert options[k][0]==v,('MED default mismatch',k,v,options[k][0])
screens={k or 'root':v.split() for k,v in re.findall(r'^screen(?:\.(\w+))?=(.*)$',props,re.M)}
screens.pop('columns',None);seen=set();menuopts=set()
assert screens['root'][:2]==['<profile>','[ABOUT]']
def walk(k):
    assert k not in seen,k
    seen.add(k)
    for token in screens[k]:
        if token.startswith('['):walk(token[1:-1])
        elif token not in ['<empty>','<profile>']:
            assert token in options,('unknown menu token',token)
            menuopts.add(token)
walk('root');assert menuopts==set(options),('hidden options',set(options)-menuopts)
assert 'PTGI' not in options and 'WORLD_SPACE' not in options
shader_files=[p for p in R.rglob('*') if p.suffix in ['.glsl','.csh','.fsh','.vsh','.gsh']]
source='\n'.join(p.read_text() for p in shader_files if p.name!='settings.glsl')
# Options may control actual Iris scheduling rather than GLSL instructions.
source+='\n'+'\n'.join(line for line in props.splitlines() if line.startswith(('#if ', '#elif ')))
for k in options:assert re.search(r'\b'+k+r'\b',source),('unused setting',k)
for p in shader_files:
    for inc in re.findall(r'#include "([^"]+)"',p.read_text()):assert (R/inc.lstrip('/')).is_file(),(p,inc)
for language in ['en_us','en_US']:
    text=(R/'lang'/(language+'.lang')).read_text()
    for k in options:assert 'option.'+k+'=' in text,k
    for k in screens:
        if k!='root':assert 'screen.'+k+'=' in text,k
assert (R/'lang/en_us.lang').read_bytes()==(R/'lang/en_US.lang').read_bytes()
clear=0
for p in shader_files:
    for args in re.findall(r'const vec4 \w+ClearColor = vec4\(([^)]+)\);',p.read_text()):
        assert len(args.split(','))==4,(p,args)
        for v in args.split(','):float(v)
        clear+=1
assert clear>=10
for b in [65536,262144,524288,1048576,1572864]:
    a=active_properties({'GEOMETRY_BUDGET':b});cap=1<<(b-1).bit_length()
    buffers={int(i):int(n) for i,n in re.findall(r'bufferObject\.(\d+)\s*=\s*(\d+)',a)}
    assert buffers=={0:b*20+((b+255)//256)*32,1:16+b*80,2:(2*b-1)*32,3:b*20,4:16},buffers
    assert max(buffers.values())<=128*1024*1024
assert not re.search(r'^image\.',props,re.M)
assert 'shadow.culling=false' in props and 'allowConcurrentCompute=false' in props
assert len(list(R.glob('shadowcomp*.csh')))==49
for res in [33,40,50,59,67,77,100]:
    active=active_properties({'PT_RESOLUTION':res})
    dims=[(int(i),float(x),float(y)) for i,x,y in re.findall(r'size.buffer.colortex(\d+)\s*=\s*(\S+)\s+(\S+)',active)]
    assert set(i for i,_,_ in dims)=={2,6,8,9,11,12,13}
    assert all(x==y==res/100 for _,x,y in dims)
variants={**profiles,'PBR':{'NORMAL_MAPS':1,'POM':1,'PBR_FORMAT':2},'EFFECTS_OFF':{k:0 for k in ['PT_GI','PT_REFLECTIONS','PT_REFRACTION','PT_GLASS','PT_CAUSTICS','PT_SHADOWS','PT_SUNLIGHT','PT_SKYLIGHT','WATER_ENABLED','WATER_WAVES','PT_VOLUMETRICS','PT_DENOISE','PT_TEMPORAL','EMISSIVE_ENABLED','SPECULAR_MAPS','BLOOM_ENABLED']},'LAB_PBR':{'NORMAL_MAPS':1,'POM':1,'PBR_FORMAT':1,'PT_FIREFLY_CLAMP':'4.0','POWDER_EMISSION':1}}
# Additional branches exercise each scale and both reconstruction qualities.
variants.update({f'SCALE_{scale}':{'PT_RESOLUTION':scale,'PT_UPSCALE_FILTER':i%2,'PT_DENOISE_PASSES':1,'PT_SHARPEN':0} for i,scale in enumerate([33,59,67,77])})
assert 'program.composite3.enabled=false' in active_properties({'PT_DENOISE':0})
assert 'program.composite4.enabled=false' in active_properties({'PT_DENOISE_PASSES':1})
assert 'program.composite6.enabled=false' in active_properties({'PT_SHARPEN':0})
assert 'program.composite6.enabled=false' in active_properties({'DEBUG_VIEW':9})
if len(sys.argv)>1:
    name=sys.argv[1];preset=variants[name];count=0
    for p in sorted(R.glob('*.fsh')):rt.gl['DeleteProgram'](rt.program(p.stem,preset));count+=1
    if name in profiles:
        for p in sorted(R.glob('*.csh')):rt.gl['DeleteProgram'](compute(p.stem,preset));count+=1
    else:
        for i in range(13):rt.gl['DeleteProgram'](rt.program('final',{**preset,'DEBUG_VIEW':i}));count+=1
    print('LINK PASS',name,count,flush=True);sys.exit(0)
print('METADATA PASS',len(options),'options; four profiles;',clear,'literal clear colors',flush=True)
for name in variants:subprocess.run([sys.executable,__file__,name],check=True)
count=len(profiles)*(len(list(R.glob('*.fsh')))+len(list(R.glob('*.csh'))))+(len(variants)-len(profiles))*(len(list(R.glob('*.fsh')))+13)
result={'all_passed':True,'option_count':len(options),'profile_count':4,'linked_program_variants':count,'renderer':'Mesa llvmpipe OpenGL 4.5, not Iris/Minecraft'}
(Path(__file__).parent/'ptgi-evidence/validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
