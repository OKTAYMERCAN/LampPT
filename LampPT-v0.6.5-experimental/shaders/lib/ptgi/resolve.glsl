// PT UPSCALING: geometry-guided reconstruction of low-resolution transport.
// Full-resolution albedo and primary emission are restored AFTER reconstruction.
// This is LampPT's own spatial filter, not AMD FSR, TAAU or frame generation.
#include "/lib/ptgi/context.glsl"
in vec2 texcoord;
/* RENDERTARGETS:7 */
layout(location=0)out vec4 outScene;
vec4 ptCubicWeights(vec4 positions,float target){
    // The ray grid is snapped to full-resolution depth texels. At 33/40/59/67%
    // its spacings are NOT uniform. Interpolate at the actual anchors, avoiding
    // the alternating blur/sharpen pattern from assuming a uniform sample grid.
    vec4 w=vec4(1);
    for(int i=0;i<4;i++)for(int j=0;j<4;j++)if(i!=j)
        w[i]*=(target-positions[j])/(positions[i]-positions[j]);
    return w;
}
void main(){
    PtGuide g=ptGuide(texcoord);ivec2 size=textureSize(colortex2,0),px=screenPixel(texcoord,size);
    if(g.valid==2){outScene=vec4(srgbToLinear(texture2D(colortex0,texcoord).rgb),1);return;}
#if PT_RESOLUTION == 100
    vec3 exact=texelFetch(colortex2,px,0).rgb*g.albedo+texelFetch(colortex8,px,0).rgb+ptPrimaryEmission(g);
    outScene=vec4(min(max(exact,vec3(0)),vec3(65000)),1);return;
#endif
    ivec2 base;vec2 f;ptSampleFootprint(texcoord,size,base,f);
    vec3 diffuse=vec3(0),specular=vec3(0);float wd=0.0,ws=0.0;
    vec3 loD=vec3(1e30),hiD=vec3(0),loS=vec3(1e30),hiS=vec3(0);
    vec3 nearestD=texelFetch(colortex2,px,0).rgb,nearestS=texelFetch(colortex8,px,0).rgb;
    float bestD=0.0,bestS=0.0;
#if PT_UPSCALE_FILTER == 1
    const int start=-1,end=2;
    vec2 target=texcoord*vec2(textureSize(depthtex1,0))-.5;
    vec2 a=ptSampleAnchor(base-1,size),b=ptSampleAnchor(base,size);
    vec2 c=ptSampleAnchor(base+1,size),d=ptSampleAnchor(base+2,size);
    vec4 weightsX=ptCubicWeights(vec4(a.x,b.x,c.x,d.x),target.x);
    vec4 weightsY=ptCubicWeights(vec4(a.y,b.y,c.y,d.y),target.y);
#else
    const int start=0,end=1;
#endif
    for(int y=start;y<=end;y++)for(int x=start;x<=end;x++){
        ivec2 q=clamp(base+ivec2(x,y),ivec2(0),size-1);
        PtGuide tap=ptTransportGuide(q);
        vec3 d=texelFetch(colortex2,q,0).rgb,s=texelFetch(colortex8,q,0).rgb;
#if PT_UPSCALE_FILTER == 1
        float kernel=weightsX[x+1]*weightsY[y+1];
#else
        float kernel=(x==0?1.0-f.x:f.x)*(y==0?1.0-f.y:f.y);
#endif
        float gd=ptGuideWeight(g,tap),gs=gd*ptSpecularGuideWeight(g,tap);
        diffuse+=d*(kernel*gd);wd+=kernel*gd;
        specular+=s*(kernel*gs);ws+=kernel*gs;
        float distance=1.0+dot(vec2(x,y)-f,vec2(x,y)-f);
        if(gd/distance>bestD){nearestD=d;bestD=gd/distance;}
        if(gs/distance>bestS){nearestS=s;bestS=gs/distance;}
        if(gd>.05){loD=min(loD,d);hiD=max(hiD,d);}
        if(gs>.05){loS=min(loS,s);hiS=max(hiS,s);}
    }
    // Negative cubic lobes retain detail but must not introduce bright/dark
    // ringing at occlusion edges or amplify noisy HDR beyond nearby samples.
    diffuse=wd>1e-4?diffuse/wd:nearestD;specular=ws>1e-4?specular/ws:nearestS;
    if(bestD>.05)diffuse=clamp(diffuse,loD,hiD);
    if(bestS>.05)specular=clamp(specular,loS,hiS);
    vec3 sum=max(diffuse,vec3(0))*g.albedo+max(specular,vec3(0))+ptPrimaryEmission(g);
    outScene=vec4(min(max(sum,vec3(0)),vec3(65000)),1);
}
