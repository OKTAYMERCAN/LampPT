// PT RECONSTRUCTION: compact variance-guided filters for separate lighting
// components. No albedo or directly visible emission is blurred by these passes.
#include "/lib/ptgi/context.glsl"
in vec2 texcoord;
/* RENDERTARGETS:2,8 */
layout(location=0)out vec4 outDiffuse;
layout(location=1)out vec4 outSpecular;
float ptSignalWeight(vec4 center,vec4 tap){
    float a=ptLuminance(center.rgb),b=ptLuminance(tap.rgb);
    float tolerance=2.5*sqrt(max(center.a+tap.a,0.0))+.035*max(a,b)+.015;
    return exp(-abs(a-b)/tolerance);
}
void main(){
    ivec2 size=textureSize(colortex2,0),px=screenPixel(texcoord,size);
    vec4 originalD=texelFetch(colortex2,px,0),originalS=texelFetch(colortex8,px,0);
    outDiffuse=originalD;outSpecular=originalS;
#if PT_DENOISE == 1 && DEBUG_VIEW != 9
    PtGuide center=ptTransportGuide(px);
    bool cameraWater=isEyeInWater==1&&WATER_ENABLED==1;
    bool cloudMedium=ptPrimaryCloudSegment(center);
    // Sky used to be a deterministic source and skipped reconstruction. A sky
    // ray through clouds now contains stochastic volume transport too.
    if(center.valid!=1&&!(center.valid==0&&(cameraWater||cloudMedium)))return;
    bool transmission=cameraWater||materialDielectric(center.material.a)||cloudMedium;
    vec3 sumD=vec3(0),sumS=vec3(0);float wd=0.0,ws=0.0;
    vec2 variance=vec2(0);
    // Opaque specular stays compact to retain reflected detail. Transmission
    // and camera-water scattering use the second pass's wider spacing: their
    // residual includes noisy secondary lighting, not just a sharp reflection.
    for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){
        float kernel=(x==0?2.0:1.0)*(y==0?2.0:1.0);
        ivec2 q=clamp(px+ivec2(x,y)*filterStep,ivec2(0),size-1);
        PtGuide tap=ptTransportGuide(q);
        vec4 d=texelFetch(colortex2,q,0);
        float w=kernel*ptGuideWeight(center,tap)*ptSignalWeight(originalD,d);
        sumD+=d.rgb*w;variance.x+=d.a*w*w;wd+=w;
        q=clamp(px+ivec2(x,y)*(transmission?filterStep:1),ivec2(0),size-1);
        if(filterStep!=1&&!transmission)tap=ptTransportGuide(q);
        vec4 s=texelFetch(colortex8,q,0);
        w=kernel*ptGuideWeight(center,tap)*ptSpecularGuideWeight(center,tap)*ptSignalWeight(originalS,s);
        sumS+=s.rgb*w;variance.y+=s.a*w*w;ws+=w;
    }
    // Fade the spatial blend as temporal confidence grows. The raw history is
    // saved before this filter, so spatial blur cannot feed back indefinitely.
    float age=max(texelFetch(colortex12,px,0).a,1.0);
    float confidence=mix(1.0,.45,clamp((age-1.0)/31.0,0.0,1.0));
    if(wd>0.0)outDiffuse=vec4(mix(originalD.rgb,sumD/wd,PT_FILTER_STRENGTH*confidence),max(variance.x/(wd*wd),originalD.a*.25));
    // Age alone is not confidence when rare caustic/volume samples still have
    // high variance. Keep filtering those paths, while converged signals use
    // the compact lower-strength history rule. No filtered data enters history.
    float luma=ptLuminance(originalS.rgb);
    float uncertainty=clamp(originalS.a/max(luma*luma,.0001),0.0,1.0);
    float specularConfidence=transmission?mix(confidence,1.0,uncertainty):confidence;
    float specularBlend=cloudMedium?CLOUD_FILTER:transmission?PT_TRANSMISSION_FILTER:PT_SPECULAR_FILTER;
    if(ws>0.0)outSpecular=vec4(mix(originalS.rgb,sumS/ws,specularBlend*specularConfidence),max(variance.y/(ws*ws),originalS.a*.25));
#endif
}
