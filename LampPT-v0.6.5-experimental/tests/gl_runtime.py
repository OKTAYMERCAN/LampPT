#!/usr/bin/env python3
"""Offscreen GLSL/link and synthetic render regression tests (not Minecraft).

Requires Python 3, numpy, libEGL.so.1 and libGL.so.1; no downloads, no game.
Run: python3 tests/validate.py
"""
import ctypes as C
import json
import re
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / 'shaders'
E = C.CDLL('libEGL.so.1')
G = C.CDLL('libGL.so.1')
I, U, F, P = C.c_int, C.c_uint, C.c_float, C.c_void_p

def function(lib, name, result, *args):
    f = getattr(lib, name)
    f.restype, f.argtypes = result, list(args)
    return f

display = function(E, 'eglGetPlatformDisplay', P, U, P, P)(0x31DD, None, None)
major, minor = I(), I()
assert function(E, 'eglInitialize', U, P, P, P)(display, C.byref(major), C.byref(minor))
assert function(E, 'eglBindAPI', U, U)(0x30A2)
attrs = (I * 11)(0x3033, 1, 0x3040, 8, 0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3038)
config, count = P(), I()
assert function(E, 'eglChooseConfig', U, P, P, P, I, P)(display, attrs, C.byref(config), 1, C.byref(count)) and count.value
contextAttrs = (I * 7)(0x3098, 3, 0x30FB, 3, 0x30FD, 2, 0x3038)
context = function(E, 'eglCreateContext', P, P, P, P, P)(display, config, None, contextAttrs)
assert context, 'OpenGL 3.3 compatibility context unavailable'
surfaceAttrs = (I * 5)(0x3057, 96, 0x3056, 96, 0x3038)
surface = function(E, 'eglCreatePbufferSurface', P, P, P, P)(display, config, surfaceAttrs)
assert function(E, 'eglMakeCurrent', U, P, P, P, P)(display, surface, surface, context)

signatures = {
    'GetAttribLocation': (I, U, C.c_char_p), 'VertexAttrib4f': (None, U, F, F, F, F), 'VertexAttrib2f': (None, U, F, F),
    'Translatef': (None, F, F, F), 'Scalef': (None, F, F, F),
    'GetString': (C.c_char_p, U), 'GetError': (U,),
    'CreateShader': (U, U), 'ShaderSource': (None, U, I, P, P),
    'CompileShader': (None, U), 'GetShaderiv': (None, U, U, P),
    'GetShaderInfoLog': (None, U, I, P, P), 'DeleteShader': (None, U),
    'CreateProgram': (U,), 'AttachShader': (None, U, U), 'LinkProgram': (None, U),
    'GetProgramiv': (None, U, U, P), 'GetProgramInfoLog': (None, U, I, P, P),
    'UseProgram': (None, U), 'DeleteProgram': (None, U),
    'GetUniformLocation': (I, U, C.c_char_p), 'Uniform1i': (None, I, I),
    'Uniform1f': (None, I, F), 'UniformMatrix4fv': (None, I, I, U, P),
    'GenTextures': (None, I, P), 'BindTexture': (None, U, U),
    'TexImage2D': (None, U, I, I, I, I, I, U, U, P),
    'TexParameteri': (None, U, U, I), 'ActiveTexture': (None, U),
    'DeleteTextures': (None, I, P),
    'GenerateMipmap': (None, U),
    'GenFramebuffers': (None, I, P), 'BindFramebuffer': (None, U, U),
    'FramebufferTexture2D': (None, U, U, U, U, I),
    'CheckFramebufferStatus': (U, U), 'DrawBuffers': (None, I, P),
    'ReadBuffer': (None, U), 'ReadPixels': (None, I, I, I, I, U, U, P),
    'Viewport': (None, I, I, I, I), 'Disable': (None, U),
    'MatrixMode': (None, U), 'LoadIdentity': (None,),
    'Begin': (None, U), 'End': (None,), 'TexCoord2f': (None, F, F),
    'Vertex2f': (None, F, F), 'Vertex3f': (None, F, F, F), 'Color4f': (None, F, F, F, F),
    'Normal3f': (None, F, F, F), 'MultiTexCoord2f': (None, U, F, F),
    'Finish': (None,),
}
gl = {k: function(G, 'gl' + k, *v) for k, v in signatures.items()}
print('RENDERER', gl['GetString'](0x1F01).decode(), flush=True)
print('OPENGL', gl['GetString'](0x1F02).decode(), flush=True)

def expand(path, stack=()):
    assert path not in stack, 'Circular include'
    text = path.read_text()
    def include(m):
        rel = m.group(1)
        child = ROOT / rel.lstrip('/') if rel.startswith('/') else path.parent / rel
        return expand(child, (*stack, path))
    return re.sub(r'^\s*#include\s+"([^"]+)"\s*$', include, text, flags=re.M)

def source(path, options):
    text = expand(path)
    # Iris normally injects these symbols. Fixture numeric IDs are arbitrary;
    # tests set the uniform to the same ID, shaders never hardcode the value.
    text=re.sub(r'^(#version[^\n]*\n)',r'\1#define MC_RENDER_STAGE_STARS 6\n#define CAT_THE_END 9\n#define MC_RENDER_STAGE_TERRAIN_SOLID 7\n#define MC_RENDER_STAGE_TERRAIN_TRANSLUCENT 8\n#define MC_RENDER_STAGE_TERRAIN_CUTOUT 10\n#define MC_RENDER_STAGE_TERRAIN_CUTOUT_MIPPED 11\n#define MC_RENDER_STAGE_TRIPWIRE 12\n',text,count=1)
    for name, value in options.items():
        text = re.sub(r'^(#define\s+' + re.escape(name) + r')\s+\S+',
                      lambda m: m[1] + ' ' + str(value), text, flags=re.M)
    for name, value in options.items():
        text = re.sub(r'^(const (?:int|float) ' + re.escape(name) + r' = )[^;]+;',
                      lambda m: m[1] + str(value) + ';', text, flags=re.M)
    assert text.lstrip().startswith('#version'), str(path)
    assert len(re.findall(r'^#version', text, flags=re.M)) == 1, str(path)
    return text

def shader(path, kind, options):
    obj = gl['CreateShader'](kind)
    text = C.c_char_p(source(path, options).encode())
    gl['ShaderSource'](obj, 1, C.byref(text), None)
    gl['CompileShader'](obj)
    ok = I()
    gl['GetShaderiv'](obj, 0x8B81, C.byref(ok))
    if not ok.value:
        log = C.create_string_buffer(32768)
        gl['GetShaderInfoLog'](obj, len(log), None, log)
        raise AssertionError(f'{path.name}: {log.value.decode()}')
    return obj

PROGRAM_MIPMAPS = {}
PROGRAM_GEOMETRY = set()
default_options = {}
resource_binders = []

def program(name, options=None):
    options = {**default_options,**(options or {})}
    v = shader(ROOT / (name + '.vsh'), 0x8B31, options)
    f = shader(ROOT / (name + '.fsh'), 0x8B30, options)
    p = gl['CreateProgram']()
    gl['AttachShader'](p, v)
    gl['AttachShader'](p, f)
    g = None
    if (ROOT / (name + '.gsh')).exists():
        g = shader(ROOT / (name + '.gsh'), 0x8DD9, options)
        gl['AttachShader'](p, g)
        PROGRAM_GEOMETRY.add(p)
    gl['LinkProgram'](p)
    ok = I()
    gl['GetProgramiv'](p, 0x8B82, C.byref(ok))
    if not ok.value:
        log = C.create_string_buffer(32768)
        gl['GetProgramInfoLog'](p, len(log), None, log)
        raise AssertionError(f'{name}: {log.value.decode()}')
    gl['DeleteShader'](v)
    gl['DeleteShader'](f)
    if g is not None: gl['DeleteShader'](g)
    PROGRAM_MIPMAPS[p] = set(re.findall(r'const bool (colortex\d+)MipmapEnabled = true;', source(ROOT / (name + '.fsh'), options)))
    return p

TEX, FLOAT, RGBA = 0x0DE1, 0x1406, 0x1908
FB, ATT = 0x8D40, 0x8CE0

def texture(data, half=False):
    a = np.ascontiguousarray(data, dtype=np.float32)
    if a.ndim == 2:
        a = a[:, :, None]
    channels = a.shape[2]
    fmt = 0x1903 if channels == 1 else RGBA
    internal = 0x822E if channels == 1 else (0x881A if half else 0x8814)
    obj = U()
    gl['GenTextures'](1, C.byref(obj))
    gl['BindTexture'](TEX, obj.value)
    for key, val in ((0x2801, 0x2600), (0x2800, 0x2600), (0x2802, 0x812F), (0x2803, 0x812F)):
        gl['TexParameteri'](TEX, key, val)
    gl['TexImage2D'](TEX, 0, internal, a.shape[1], a.shape[0], 0, fmt, FLOAT, a.ctypes.data)
    return obj.value

fbo = U()
gl['GenFramebuffers'](1, C.byref(fbo))
for capability in (0x0BE2, 0x0B71, 0x0B44, 0x8DB9):
    gl['Disable'](capability)  # blending, depth, cull, framebuffer sRGB
for mode in (0x1700, 0x1701):
    gl['MatrixMode'](mode)
    gl['LoadIdentity']()
gl['Color4f'](1, 1, 1, 1)
gl['Normal3f'](0, 0, 1)
gl['MultiTexCoord2f'](0x84C1, 0.03125, 0.96875)

N = 64
near, far = 0.05, 128.0
scale = 1.0 / np.tan(np.radians(70.0) * 0.5)
projection = np.array([[scale, 0, 0, 0], [0, scale, 0, 0],
    [0, 0, -(far + near)/(far - near), -2*far*near/(far - near)], [0, 0, -1, 0]], dtype=np.float32)
values = {'sunPosition':(0.3,0.85,0.4),'shadowLightPosition':(0.3,0.85,0.4),'skyColor':(.52,.69,.86),'fogColor':(.52,.62,.75),'rainStrength':0.0,'frameTimeCounter':0.0,'wetness':0.0,'isEyeInWater':0,'cameraPosition':(0.0,0.0,0.0)}
values.update(hasSkylight=1,hasCeiling=0,biome_category=0,renderStage=0)

uniforms = {'gbufferProjection': projection, 'gbufferProjectionInverse': np.linalg.inv(projection),
            'gbufferModelView': np.eye(4), 'gbufferModelViewInverse': np.eye(4), 'shadowModelView': np.eye(4),
            'shadowProjection': np.diag([0.1, 0.1, 0.02, 1.0])}

EMPTY_INPUTS={}
draw_timer_enabled=False
draw_timer_label='unlabelled'
draw_times=[]
def begin_draw_timer():
    query=U();function(G,'glGenQueries',None,I,P)(1,C.byref(query))
    function(G,'glBeginQuery',None,U,U)(0x88BF,query.value)
    return query

def end_draw_timer(query,width,height):
    function(G,'glEndQuery',None,U)(0x88BF)
    ns=C.c_uint64()
    function(G,'glGetQueryObjectui64v',None,U,U,P)(query.value,0x8866,C.byref(ns))
    function(G,'glDeleteQueries',None,I,P)(1,C.byref(query))
    draw_times.append({'stage':draw_timer_label,'frame':values.get('frameCounter',0),
                       'width':width,'height':height,'nanoseconds':ns.value})


def draw(p, inputs, width=N, height=N, outputs=1, attributes=None, vertices=None, value_overrides=None, full_precision=()):
    inputs=dict(inputs)
    if 'depthtex0' in inputs:inputs.setdefault('depthtex1',inputs['depthtex0'])
    for key in ('colortex5','colortex9','colortex14','colortex15'):
        if key not in inputs and gl['GetUniformLocation'](p,key.encode())>=0:
            if key not in EMPTY_INPUTS:EMPTY_INPUTS[key]=texture(np.zeros((1,1,4)))
            inputs[key]=EMPTY_INPUTS[key]
    gl['UseProgram'](p)
    for key, vals in (attributes or {}).items():
        location = gl['GetAttribLocation'](p, key.encode())
        if location >= 0:
            gl['VertexAttrib4f' if len(vals)==4 else 'VertexAttrib2f'](location,*vals)
    for key, a in uniforms.items():
        loc = gl['GetUniformLocation'](p, key.encode())
        a = np.ascontiguousarray(a, dtype=np.float32)
        gl['UniformMatrix4fv'](loc, 1, 1, a.ctypes.data)
    gl['Uniform1f'](gl['GetUniformLocation'](p, b'alphaTestRef'), 0.1)
    for unit, (key, obj) in enumerate(inputs.items()):
        gl['ActiveTexture'](0x84C0 + unit)
        gl['BindTexture'](TEX, obj)
        if key in PROGRAM_MIPMAPS.get(p, ()):
            gl['GenerateMipmap'](TEX)
            gl['TexParameteri'](TEX, 0x2801, 0x2703)
            gl['TexParameteri'](TEX, 0x2800, 0x2601)
        gl['Uniform1i'](gl['GetUniformLocation'](p, key.encode()), unit)
    for key,value in {**values,**(value_overrides or {})}.items():
        loc=gl['GetUniformLocation'](p,key.encode())
        if isinstance(value,(tuple,list)):
            function(G,'glUniform3f',None,I,F,F,F)(loc,*value)
        elif isinstance(value,int):gl['Uniform1i'](loc,value)
        else:gl['Uniform1f'](loc,value)
    for binder in resource_binders:binder(p)
    # Output allocation must not overwrite an input binding.
    gl['ActiveTexture'](0x84C0 + 30)
    gl['BindFramebuffer'](FB, fbo.value)
    targets = []
    for i in range(8):
        obj = texture(np.zeros((height, width, 4)), half=i not in full_precision) if i < outputs else 0
        gl['FramebufferTexture2D'](FB, ATT+i, TEX, obj, 0)
        if obj:
            targets.append(obj)
    buffers = (U * outputs)(*[ATT+i for i in range(outputs)])
    gl['DrawBuffers'](outputs, buffers)
    assert gl['CheckFramebufferStatus'](FB) == 0x8CD5, 'Incomplete framebuffer'
    gl['Viewport'](0, 0, width, height)
    vertex_attribute_locations={key:gl['GetAttribLocation'](p,key.encode()) for v in (vertices or []) for key in v.get('attributes',{})}
    triangles = vertices is not None or p in PROGRAM_GEOMETRY
    timer=begin_draw_timer() if draw_timer_enabled else None
    gl['Begin'](0x0004 if triangles else 0x0007)
    if vertices is None:
        corners=((0, 0, -1, -1), (1, 0, 1, -1), (1, 1, 1, 1), (0, 1, -1, 1))
        for index in ([0,1,2,0,2,3] if triangles else range(4)):
            u,v,x,y=corners[index]
            gl['TexCoord2f'](u, v)
            gl['Vertex2f'](x, y)
    else:
        for vertex in vertices:
            for key,value in vertex.get('attributes',{}).items():
                loc=vertex_attribute_locations[key]
                if loc>=0:gl['VertexAttrib4f' if len(value)==4 else 'VertexAttrib2f'](loc,*value)
            gl['Color4f'](*vertex.get('color',(1,1,1,1)))
            gl['Normal3f'](*vertex.get('normal',(0,0,1)))
            gl['MultiTexCoord2f'](0x84C1,*vertex.get('lm',(0.03125,0.96875)))
            gl['TexCoord2f'](*vertex.get('uv',(0.5,0.5)))
            gl['Vertex3f'](*vertex['position'])
    gl['End']()
    if timer is not None:end_draw_timer(timer,width,height)
    if vertices is not None:
        gl['Color4f'](1,1,1,1)
        gl['Normal3f'](0,0,1)
        gl['MultiTexCoord2f'](0x84C1,0.03125,0.96875)
    gl['Finish']()
    result = []
    for i in range(outputs):
        gl['ReadBuffer'](ATT+i)
        a = np.empty((height, width, 4), dtype=np.float32)
        gl['ReadPixels'](0, 0, width, height, RGBA, FLOAT, a.ctypes.data)
        assert np.isfinite(a).all(), 'Nonfinite render'
        result.append(a)
    error = gl['GetError']()
    assert error == 0, f'OpenGL error {error:#x}'
    return targets, result

def constant(values, n=N):
    return np.broadcast_to(np.array(values, dtype=np.float32), (n, n, len(values))).copy()

def depth_for_z(z):
    return ((projection[2, 2] * z + projection[2, 3]) / -z) * 0.5 + 0.5

def flat(rgb=(0.5, 0.5, 0.5), lm=240/255, mask=1):
    return {'colortex0': texture(constant([*rgb, 1])),
            'colortex1': texture(constant([0.5, 0.5, 1, mask])),
            'colortex3': texture(constant([*rgb, lm])),
            'colortex10': texture(constant([(round(lm*255)%16)/15,(round(lm*255)//16)/15,0,1])),
            'depthtex0': texture(np.full((N, N), depth_for_z(-4))),
            'shadowtex0': texture(np.ones((N, N)))}
