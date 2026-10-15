#version 430 compatibility
#include "/lib/ptgi/context.glsl"
#include "/lib/water.glsl"
#include "/lib/scene/trace.glsl"
#include "/lib/ptgi/bsdf.glsl"
#include "/lib/ptgi/lights.glsl"
layout(location=0)out vec4 result;
void main(){result=vec4(ptHandIntensity(heldItemId,heldBlockLightValue),1);}
