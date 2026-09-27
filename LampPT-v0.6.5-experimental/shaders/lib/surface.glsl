// GEOMETRY VS SHADING: normal-map relief changes the shading frame, never the
// mesh plane used for ray origins, GI history or spatial edge rejection.
#ifndef LAMPPT_SURFACE
#define LAMPPT_SURFACE
#include "/lib/translucent_data.glsl"
vec3 geometricNormalAt(vec2 uv,vec3 shadingNormal){
#if NORMAL_MAPS == 1
    vec2 encoded=texelFetch(colortex10,screenPixel(uv,textureSize(colortex10,0)),0).ba;
    // Zero is the clear/unwritten sentinel; opaque mesh programs write both.
    if(dot(encoded,encoded)>1e-8)return octDecode(encoded);
#endif
    return shadingNormal;
}
#endif
