#version 430 compatibility
#include "/lib/ptgi/context.glsl"
uniform float sourceId;
uniform float sourceNative;
uniform vec3 sourceColor;
layout(location=0)out vec4 result;
void main(){vec4 m=ptTexelEmission(resolveMaterial(sourceId,sourceNative,false,vec4(0,0,0,1)),sourceColor);result=vec4(emissionRadiance(m,srgbToLinear(sourceColor)),m.a);}
