#version 430 compatibility
// Regression harness for production clouds and refractive water focusing.
#include "/lib/ptgi/context.glsl"
#include "/lib/ptgi/integrator.glsl"
in vec2 texcoord;
uniform vec3 probePosition;
uniform vec3 probeNormal;
uniform vec3 probeAlbedo;
uniform vec3 probeMaterial;
uniform vec3 probeU;
uniform vec3 probeV;
uniform vec3 probeDirection;
uniform float probeKind;
uniform float probeEtaI;
uniform float probeEtaT;
uniform int probeMode;
uniform int probeValid;
layout(location=0)out vec4 result;
void main(){
    uint rng=ptHash(uint(gl_FragCoord.x)+uint(gl_FragCoord.y)*65537u+uint(frameCounter)*747796405u+13u);
    if(probeMode==7){
        PtGuide g=ptGuide(texcoord);
        vec3 p=(gbufferModelViewInverse*vec4(g.p,1)).xyz;
        vec3 n=mat3(gbufferModelViewInverse)*g.ng;
        SceneHit h=traceScene(p+n*RAY_BIAS,ptWorldLight(),PT_DISTANCE,ivec3(-1));
        result=vec4(max(dot(n,ptWorldLight()),0),h.hit?1:0,h.hit&&h.data==0u?1:0,g.valid);return;
    }
    if(probeMode==8){PtGuide g=ptGuide(texcoord);result=vec4(g.p,1);return;}
    PtGuide g;g.p=probePosition+probeU*texcoord.x+probeV*texcoord.y;
    g.n=probeNormal;g.ng=g.n;g.albedo=probeAlbedo;g.material=vec4(probeMaterial,probeKind);
    g.valid=probeValid;g.depth=-g.p.z;
    PtSurface s;s.p=g.p;s.n=g.n;s.ng=g.ng;s.albedo=g.albedo;s.m=g.material;s.emission=vec3(0);
    if(probeMode==11){
        SceneHit h=traceScene(g.p,probeDirection,PT_DISTANCE,ivec3(-1));
        result=vec4(h.hit?1:0,h.escaped?1:0,h.data==0u?1:0,h.distance);return;
    }
    if(probeMode==9){
        uint triangle;float pdf;
        bool selected=ptChooseTriangle(g.p,g.ng,rng,triangle,pdf);
        result=vec4(selected?sceneTriangles[triangle].p0.y:0,pdf,selected?ptTrianglePdf(g.p,g.ng,triangle):0.0,selected?float(triangle+1u):0.0);return;
    }
    if(probeMode==20){
        vec3 wi=ptSamplePhase(-probeDirection,CLOUD_ANISOTROPY,ptRandom2(rng));
        result=vec4(wi,ptPhase(dot(probeDirection,wi),CLOUD_ANISOTROPY));return;
    }
    if(probeMode==21){
        vec3 d=safeNormalize(probeDirection);float limit=PT_DISTANCE;
        float t=ptCloudFreeFlight(g.p,d,limit,-log(max(1.0-ptRandom(rng),1e-7)));
        result=vec4(ptCloudTransmittance(g.p,d,limit),ptCloudDensity(g.p),t<limit?1.0:0.0,min(t,limit));return;
    }
    if(probeMode==22){
        vec3 sum=vec3(0);
        for(int i=0;i<32;i++)sum+=ptIntegrate(g,rng);
        result=vec4(sum/32.0,1);return;
    }
    if(probeMode==23){
        ptPrepareGuidance(s,probeEtaI,ptWorldLight());
        vec3 axis=ptGuideAxis(s,ptWorldLight());
        SceneHit hit=traceScene(g.p+axis*RAY_BIAS,axis,PT_DISTANCE,ivec3(-1));
        vec3 n=-waterWaveNormal(hit.position.xz+cameraPosition.xz,frameTimeCounter);
        vec3 outRay=refract(axis,n,WATER_IOR);
        result=vec4(length(outRay-ptWorldLight()),ptGuideCachedProbability,ptGuideConeCosine(),hit.hit?1:0);return;
    }
    if(probeMode==0){result=vec4(ptIntegrate(g,rng),1);return;}
    if(probeMode==1){
        vec3 weight;float pdf;vec3 wi=ptSample(s,safeNormalize(-probeDirection),probeEtaI,ptWorldLight(),rng,weight,pdf);
        result=vec4(weight,1);return;
    }
    if(probeMode==2){
        vec3 weight;bool transmitted;vec3 wi=ptSampleDielectric(s,safeNormalize(-probeDirection),probeEtaI,probeEtaT,rng,weight,transmitted);
        result=vec4(wi,transmitted?1.0:0.0);return;
    }
    if(probeMode==3){
        SceneHit h=traceScene(g.p,probeDirection,PT_DISTANCE,ivec3(-1));
        result=vec4(h.hit?1.0:0.0,h.distance,h.outward.z,float((h.data>>24u)&127u));return;
    }
    if(probeMode==4){result=vec4(ptDirect(s,safeNormalize(-probeDirection),probeEtaI,vec3(0),false,rng),1);return;}
    if(probeMode==5){result=vec4(ptFresnel(texcoord.x,probeEtaI,probeEtaT));return;}
    if(probeMode==6){
        SceneHit h=traceScene(g.p,probeDirection,PT_DISTANCE,ivec3(-1));
        result=vec4(h.material.rgb,h.hit?1:0);return;
    }
}
