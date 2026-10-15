#version 430 compatibility
// Focused audit regression harness. All transport functions are production code.
#include "/lib/ptgi/context.glsl"
#include "/lib/ptgi/integrator.glsl"
in vec2 texcoord;
uniform int probeMode;
uniform vec3 probePosition;
uniform vec3 probeDirection;
layout(location=0)out vec4 result;
void main(){
    if(probeMode==0){result=ptGuide(texcoord).material;return;}
    if(probeMode==1){result=vec4(ptGuide(texcoord).ng,1);return;}
    if(probeMode==2){SceneHit h=traceScene(probePosition,probeDirection,PT_DISTANCE,ivec3(-1));result=vec4(h.outward,h.hit?1:0);return;}
    if(probeMode==3){SceneHit h=traceScene(probePosition,probeDirection,PT_DISTANCE,ivec3(-1));result=h.material;return;}
    if(probeMode==4){
        PtGuide g=ptGuide(texcoord);g.p=vec3(0,1,-.2);g.depth=.2;
        uint rng=ptHash(uint(gl_FragCoord.x)+uint(gl_FragCoord.y)*65537u+13u);
        result=vec4(ptIntegrate(g,rng),1);return;
    }
}
