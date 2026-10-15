#version 430 compatibility
// Test-only refresh of primary water normals for a stationary camera. Uses the
// same analytic wave function and full-resolution world position as gbuffer.fsh.
#include "/lib/ptgi/context.glsl"
#include "/lib/water.glsl"
in vec2 texcoord;
layout(location=0)out vec4 result;
void main(){
    ivec2 px=screenPixel(texcoord,textureSize(colortex14,0));
    result=texelFetch(colortex14,px,0);
    if(result.a<.5)return;
    vec3 physical=mat3(gbufferModelViewInverse)*unpackNormal24(result.g);
    if(abs(physical.y)<.5)return;
    vec3 ray=viewPosition(texcoord,.5,gbufferProjectionInverse);
    vec3 pos=(gbufferModelViewInverse*vec4(ray*(result.b/max(-ray.z,1e-6)),1)).xyz+cameraPosition;
    vec3 normal=transpose(mat3(gbufferModelViewInverse))*waterWaveNormal(pos.xz,frameTimeCounter)*sign(physical.y);
    result.r=packNormal24(normalize(normal));
}
