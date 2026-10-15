#version 430 compatibility
#include "/lib/ptgi/context.glsl"
#include "/lib/ptgi/integrator.glsl"
layout(location=0) out vec4 result;
void main(){
    uint seed=ptHash(uint(gl_FragCoord.x)+uint(gl_FragCoord.y)*65537u+ptSeedFrame()*747796405u);
    float x=ptRandom(seed),y=ptRandom(seed);
    // Known integrals: E[x]=1/2, P(x<0.13)=0.13, E[x*y]=1/4.
    result=vec4(x,x<.13?1.0:0.0,x*y,1.0);
}
