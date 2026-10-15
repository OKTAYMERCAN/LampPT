#version 430 compatibility
// Test-only 0.6.6 reconstruction and four-call repair reference.
// Reconstruct each independently sized component onto the base transport grid.
// Surface guides reject samples across walls/material interfaces. This stage
// does not filter the full-resolution primary albedo or visible emission.
#include "/lib/ptgi/context.glsl"
#include "/lib/ptgi/integrator.glsl"
uniform sampler2D ptDirectTex,ptDirectGuideTex;
uniform sampler2D ptGITex,ptGIGuideTex;
uniform sampler2D ptReflectTex,ptReflectGuideTex;
uniform sampler2D ptCloudTex,ptCloudGuideTex;
in vec2 texcoord;
/* RENDERTARGETS:2,8 */
layout(location=0)out vec4 outDiffuse;
layout(location=1)out vec4 outSpecular;
PtGuide ptComponentGuide(vec4 d,vec4 light,ivec2 pixel,ivec2 size){
    PtGuide g;g.valid=d.b>0.0?1:int(-d.b+.5)-1;g.depth=max(d.b,0.0);
    vec2 full=vec2(textureSize(depthtex1,0));vec2 uv=(ptSampleAnchor(pixel,size)+.5)/full;
    vec3 ray=viewPosition(uv,.5,gbufferProjectionInverse);g.p=ray*(g.depth/max(-ray.z,1e-6));
    g.ng=unpackNormal24(d.r);g.n=unpackNormal24(d.g);
    g.material=unpackMaterial24(d.a,0.0);g.albedo=unpackRGB24(light.a);return g;
}
vec3 ptMergeComponent(sampler2D source,sampler2D guides,PtGuide target,int component){
    ivec2 size=textureSize(source,0),baseSize=textureSize(colortex2,0);
    if(all(equal(size,baseSize)))return texelFetch(source,ivec2(gl_FragCoord.xy),0).rgb;
    ivec2 base;vec2 f;ptSampleFootprint(texcoord,size,base,f);
    vec3 sum=vec3(0);float total=0.0;
    for(int y=0;y<2;y++)for(int x=0;x<2;x++){
        ivec2 q=clamp(base+ivec2(x,y),ivec2(0),size-1);vec4 L=texelFetch(source,q,0);
        PtGuide g=ptComponentGuide(texelFetch(guides,q,0),L,q,size);
        float w=(x==0?1.0-f.x:f.x)*(y==0?1.0-f.y:f.y)*ptGuideWeight(target,g);
        if(component==2&&target.valid==1)w*=ptSpecularGuideWeight(target,g);
        sum+=L.rgb*w;total+=w;
    }
    if(total>1e-5)return sum/total;
    // Thin panes and newly revealed geometry can be smaller than a coarse
    // sample cell. Trace their actual guide once instead of showing a black
    // hole or copying the lighting from the wrong side of a wall.
    uint rng=ptHash(uint(gl_FragCoord.x)+uint(gl_FragCoord.y)*65537u+uint(frameCounter%1048576)*747796405u+uint(component+9)*2891336453u);
    PtRadiance L=ptIntegrateComponent(target,rng,component);return component<2?L.diffuse:L.specular;
}
void main(){
    PtGuide g=ptGuide(texcoord);outDiffuse=vec4(0);outSpecular=vec4(0);
    if(g.valid==2){outSpecular=vec4(srgbToLinear(texture2D(colortex0,texcoord).rgb),0);return;}
    outDiffuse=vec4(ptMergeComponent(ptDirectTex,ptDirectGuideTex,g,0)+ptMergeComponent(ptGITex,ptGIGuideTex,g,1),0);
    outSpecular=vec4(ptMergeComponent(ptReflectTex,ptReflectGuideTex,g,2)+ptMergeComponent(ptCloudTex,ptCloudGuideTex,g,3),0);
}
