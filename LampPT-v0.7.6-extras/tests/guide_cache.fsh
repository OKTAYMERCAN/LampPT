#version 430 compatibility
#include "/lib/ptgi/context.glsl"
in vec2 texcoord;
layout(location=0)out vec4 guide;
void main(){guide=ptPackGuide(ptGuide(texcoord));}
