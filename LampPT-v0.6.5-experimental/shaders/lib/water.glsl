// WATER SURFACE: wave slopes perturb the dielectric normal. Focusing,
// reflection, absorption and refraction are evaluated by the path integrator.
#ifndef LAMPPT_WATER
#define LAMPPT_WATER
#include "/lib/settings.glsl"
vec3 waterWaveNormal(vec2 xz,float time){
#if WATER_WAVES == 1
    vec2 p=xz*WAVE_SCALE;
    float t=time*WAVE_SPEED;
    vec2 grad=vec2(1.7,.9)*cos(dot(p,vec2(1.7,.9))+t)
        +vec2(-1.1,2.3)*cos(dot(p,vec2(-1.1,2.3))-t*1.3)*.55
        +vec2(3.1,-1.3)*cos(dot(p,vec2(3.1,-1.3))+t*.7)*.25;
    return normalize(vec3(-grad.x*WAVE_STRENGTH,1.0,-grad.y*WAVE_STRENGTH));
#else
    return vec3(0.0,1.0,0.0);
#endif
}
#endif
