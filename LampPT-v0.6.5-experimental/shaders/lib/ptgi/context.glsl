// PT FRAME INPUTS: rasterization supplies only the first surface and guides.
// No hybrid lightmap, shadow-map lighting or resolved scene color is consumed.
#ifndef LAMPPT_PT_CONTEXT
#define LAMPPT_PT_CONTEXT
#include "/lib/settings.glsl"
#include "/lib/common.glsl"
#include "/lib/translucent_data.glsl"
#include "/lib/materials.glsl"
uniform sampler2D colortex0;
uniform sampler2D colortex1;
uniform sampler2D colortex2;
uniform sampler2D colortex3;
uniform sampler2D colortex4;
uniform sampler2D colortex5;
uniform sampler2D colortex6;
uniform sampler2D colortex8;
uniform sampler2D colortex9;
uniform sampler2D colortex11;
uniform sampler2D colortex10;
uniform sampler2D colortex12;
uniform sampler2D colortex13;
uniform sampler2D colortex14;
uniform sampler2D colortex15;
uniform sampler2D depthtex1;
uniform mat4 gbufferProjectionInverse;
uniform mat4 gbufferModelViewInverse;
uniform mat4 gbufferPreviousModelView;
uniform mat4 gbufferPreviousProjection;
#define LAMPPT_CAMERA_UNIFORM
uniform vec3 cameraPosition;
uniform vec3 previousCameraPosition;
uniform vec3 sunPosition;
uniform vec3 shadowLightPosition;
uniform vec3 skyColor;
uniform float rainStrength;
uniform float frameTimeCounter;
uniform int frameCounter;
uniform int isEyeInWater;
#include "/lib/surface.glsl"
#include "/lib/ptgi/cloud_medium.glsl"
struct PtGuide {vec3 p;vec3 n;vec3 ng;vec3 albedo;vec4 material;float depth;int valid;};
PtGuide ptGuide(vec2 uv){
    // A half-resolution ray must use the CENTER of the full-resolution depth
    // texel it sampled. Reconstructing at the unsnapped low-res UV moves the
    // point behind tilted surfaces and makes the surface shadow itself.
    ivec2 fullSize=textureSize(depthtex1,0);
    uv=(vec2(screenPixel(uv,fullSize))+.5)/vec2(fullSize);
    PtGuide g;float d=texture2D(depthtex1,uv).r;
    g.p=viewPosition(uv,min(d,.999999),gbufferProjectionInverse);
    vec4 nd=texture2D(colortex1,uv);
    g.n=decodeNormal(nd.rgb);g.ng=geometricNormalAt(uv,g.n);
    g.albedo=srgbToLinear(texture2D(colortex3,uv).rgb);
    g.material=texture2D(colortex4,uv);g.depth=-g.p.z;
    g.valid=d>=1.0?0:(nd.a>.5&&nd.a<1.5?1:2);
    vec4 w=texelFetch(colortex14,screenPixel(uv,textureSize(colortex14,0)),0);
    vec4 c=texelFetch(colortex15,screenPixel(uv,textureSize(colortex15,0)),0);
    float wd=w.a>.5?w.b:1e30,cd=c.a>.5?c.g:1e30;
    float nearest=min(wd,cd);
    if(nearest<1e29&&(d>=1.0||nearest<g.depth)){
        bool water=wd<cd;
        vec3 ray=viewPosition(uv,.5,gbufferProjectionInverse);
        g.p=ray*(nearest/max(-ray.z,1e-6));g.depth=nearest;
        vec4 meta=texelFetch(colortex5,screenPixel(uv,textureSize(colortex5,0)),0);
        g.n=unpackNormal24(water?w.r:c.b);
        g.ng=unpackNormal24(water?w.g:meta.b);
        g.albedo=water?vec3(1):srgbToLinear(unpackRGB24(c.r));
        g.material=water?vec4(WATER_ROUGHNESS,.02,0,1):unpackMaterial24(meta.r,meta.g);
        g.valid=1;
    }
    return g;
}
// Reconstruct a transport-grid guide from the cache written by composite2.
// Filters and upscaling used to re-read all full-resolution material layers for
// every tap. Two compact records now provide the same sample-grid information.
// This function is only valid AFTER composite2; temporal reprojection still
// reads the original first-hit data and refreshes this cache every frame.
PtGuide ptTransportGuide(ivec2 pixel){
    ivec2 size=textureSize(colortex6,0);pixel=clamp(pixel,ivec2(0),size-1);
    vec4 data=texelFetch(colortex6,pixel,0),reactive=texelFetch(colortex9,pixel,0);
    vec2 full=vec2(textureSize(depthtex1,0));
    vec2 uv=(floor((vec2(pixel)+.5)*full/vec2(size))+.5)/full;
    PtGuide g;g.depth=data.b;g.valid=int(data.a+.5);
    vec3 ray=viewPosition(uv,.5,gbufferProjectionInverse);
    g.p=ray*(g.depth/max(-ray.z,1e-6));
    g.ng=unpackNormal24(data.r);g.n=unpackNormal24(data.g);
    g.material=unpackMaterial24(reactive.b,0.0);g.albedo=unpackRGB24(reactive.a);
    return g;
}
// A primary emitter behind/in clouds must use sampled medium visibility.
// Otherwise deterministic full-resolution emission would shine through clouds.
bool ptPrimaryCloudSegment(PtGuide g){
    if(isEyeInWater==1&&WATER_ENABLED==1)return false;
    vec3 p=(gbufferModelViewInverse*vec4(g.p,1)).xyz;
    vec2 interval;
    return ptCloudInterval(vec3(0),safeNormalize(p),g.valid==1?length(p):ptCloudEnvironmentDistance(),interval);
}
// Visible emissive artwork is deterministic, including camera-medium extinction.
// Keeping it outside Monte Carlo reconstruction preserves individual texels.
vec3 ptPrimaryEmission(PtGuide g){
    if(g.valid!=1||ptPrimaryCloudSegment(g))return vec3(0);
    vec3 extinction=isEyeInWater==1&&WATER_ENABLED==1?max(vec3(1)-vec3(WATER_R,WATER_G,WATER_B),vec3(.02))*WATER_ABSORPTION:vec3(PT_AIR_DENSITY*.1);
#if PT_VOLUMETRICS == 1
    extinction+=vec3(isEyeInWater==1&&WATER_ENABLED==1?WATER_SCATTERING:PT_AIR_DENSITY);
#endif
    return emissionRadiance(g.material,g.albedo)*exp(-extinction*length(g.p));
}
float ptLuminance(vec3 value){return dot(value,vec3(.2126,.7152,.0722));}
// Invert the actual depth-sample grid, not nominal half-resolution texel
// centers. Otherwise even a stationary camera mixes 25% of a neighbor every
// frame. This mapping also handles odd window dimensions and full resolution.
vec2 ptSampleAnchor(ivec2 pixel,ivec2 size){
    return floor((vec2(pixel)+.5)*vec2(textureSize(depthtex1,0))/vec2(size));
}
void ptSampleFootprint(vec2 uv,ivec2 size,out ivec2 base,out vec2 fraction){
    vec2 target=uv*vec2(textureSize(depthtex1,0))-.5;
    base=ivec2(floor(uv*vec2(size)-.5));
    vec2 first=ptSampleAnchor(base,size),next=ptSampleAnchor(base+1,size);
    for(int axis=0;axis<2;axis++){
        if(target[axis]<first[axis])base[axis]--;
        else if(target[axis]>=next[axis])base[axis]++;
    }
    base=clamp(base,ivec2(0),max(size-2,ivec2(0)));
    first=ptSampleAnchor(base,size);next=ptSampleAnchor(base+1,size);
    fraction=clamp((target-first)/max(next-first,vec2(1)),vec2(0),vec2(1));
    // Matrix round-off must not accumulate into stationary image diffusion.
    fraction=mix(fraction,vec2(0),lessThan(fraction,vec2(.0001)));
    fraction=mix(fraction,vec2(1),greaterThan(fraction,vec2(.9999)));
}
float ptGuideWeight(PtGuide a,PtGuide b){
    if(a.valid!=b.valid)return 0.0;
    if(a.valid!=1)return 1.0;
    if(abs(a.material.a-b.material.a)>.25||abs(a.material.g-b.material.g)>.08||abs(a.material.r-b.material.r)>.12)return 0.0;
    float plane=max(abs(dot(a.p-b.p,a.ng)),abs(dot(a.p-b.p,b.ng)));
    return exp(-plane/max(.02,a.depth*.002))*pow(max(dot(a.ng,b.ng),0.0),32.0);
}
// Glossy highlights follow the shading normal, unlike diffuse irradiance.
// Metallic and transmitting surfaces also retain their material-color edges.
float ptSpecularGuideWeight(PtGuide a,PtGuide b){
    float w=pow(max(dot(a.n,b.n),0.0),mix(96.0,16.0,a.material.r));
    if(a.material.g<0.0||materialDielectric(a.material.a))
        w*=exp(-length(a.albedo-b.albedo)*8.0);
    return w;
}
#endif
