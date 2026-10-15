#version 430 compatibility
#include "/lib/ptgi/context.glsl"
#include "/lib/scene/trace.glsl"
#include "/lib/ptgi/ray_material.glsl"
uniform int probeMode;
layout(location=0)out vec4 result;
void main(){
    SceneHit h=traceScene(vec3(.13,.27,2),vec3(0,0,-1),10.0,ivec3(-1));
    vec3 n=h.normal;vec4 m=h.material;
    if(h.hit)ptRayMaterial(h,vec3(0,0,-1),n,m);
    result=probeMode==0?vec4(n,h.hit?1.0:0.0):m;
}
