// PT HISTORY: independent diffuse/specular means and luminance moments.
// History stores octahedral world normal RG, diffuse second moment B, and
// negative view depth A. Only compatible reprojected geometry retains history.
#include "/lib/ptgi/context.glsl"
in vec2 texcoord;
/* RENDERTARGETS:2,8,12,11,13,9,6 */
layout(location=0)out vec4 outDiffuse;
layout(location=1)out vec4 outSpecular;
layout(location=2)out vec4 outHistory;
layout(location=3)out vec4 outSpecHistory;
layout(location=4)out vec4 outGeometry;
layout(location=5)out vec4 outReactive;
layout(location=6)out vec4 outGuide;
void main(){
    ivec2 size=textureSize(colortex2,0),px=screenPixel(texcoord,size);
    vec2 uv=(vec2(px)+.5)/vec2(size);PtGuide g=ptGuide(uv);
    vec3 wn=normalize(mat3(gbufferModelViewInverse)*(g.valid==0?safeNormalize(-g.p):g.ng));
    vec3 currentD=texelFetch(colortex2,px,0).rgb,currentS=texelFetch(colortex8,px,0).rgb;
    vec2 luma=vec2(ptLuminance(currentD),ptLuminance(currentS)),moments=luma*luma;
    vec3 loD=currentD,hiD=currentD,loS=currentS,hiS=currentS;
    vec2 localMean=vec2(0),localSquare=vec2(0);float localWeight=0.0;
    float neighborsD[8],neighborsS[8];int neighbors=0;
    // Bootstrap variance from compatible nearby samples until history exists.
    for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){
        ivec2 q=clamp(px+ivec2(x,y),ivec2(0),size-1);
        if(ptGuideWeight(g,ptGuide((vec2(q)+.5)/vec2(size)))<.5)continue;
        vec3 d=texelFetch(colortex2,q,0).rgb,s=texelFetch(colortex8,q,0).rgb;
        loD=min(loD,d);hiD=max(hiD,d);loS=min(loS,s);hiS=max(hiS,s);
        vec2 l=vec2(ptLuminance(d),ptLuminance(s));localMean+=l;localSquare+=l*l;localWeight+=1.0;
        if(x!=0||y!=0){neighborsD[neighbors]=l.x;neighborsS[neighbors]=l.y;neighbors++;}
    }
    localMean/=max(localWeight,1.0);localSquare/=max(localWeight,1.0);
    vec2 localVariance=max(localSquare-localMean*localMean,vec2(0));
#if PT_DENOISE == 1 && PT_OUTLIER_FILTER == 1 && DEBUG_VIEW != 9
    // Limit isolated stochastic spikes using the median of compatible neighbors.
    // This optional reconstruction step is biased; the raw transport is not.
    // No texture/color averaging occurs, and glass/mirror highlights are exempt.
    if(g.valid==1&&neighbors>=4&&!materialDielectric(g.material.a)){
        for(int i=1;i<8;i++)for(int j=i;j>0;j--){
            if(i>=neighbors)break;
            if(neighborsD[j]<neighborsD[j-1]){float v=neighborsD[j];neighborsD[j]=neighborsD[j-1];neighborsD[j-1]=v;}
            if(neighborsS[j]<neighborsS[j-1]){float v=neighborsS[j];neighborsS[j]=neighborsS[j-1];neighborsS[j-1]=v;}
        }
        float limitD=neighborsD[neighbors/2]*8.0+1.0;
        float limitS=neighborsS[neighbors/2]*8.0+1.0;
        currentD*=min(1.0,limitD/max(luma.x,1e-8));
        if(g.material.r>.15)currentS*=min(1.0,limitS/max(luma.y,1e-8));
        luma=vec2(ptLuminance(currentD),ptLuminance(currentS));moments=luma*luma;
    }
#endif
    float age=1.0,specAge=1.0;
    vec2 missing=vec2(0);float materialKey=packMaterial24(g.material),colorKey=packRGB24(g.albedo);
#if PT_TEMPORAL == 1 && DEBUG_VIEW != 9
    vec3 movement=cameraPosition-previousCameraPosition;
    vec3 world=(gbufferModelViewInverse*vec4(g.p,1)).xyz+movement;
    vec3 oldView=(gbufferPreviousModelView*vec4(world,1)).xyz;
    vec4 clip=gbufferPreviousProjection*vec4(oldView,1);
    if(frameCounter>0&&length(movement)<2.0&&clip.w>0.0&&g.valid!=2){
        vec2 oldUV=clip.xy/clip.w*.5+.5;
        if(all(greaterThan(oldUV,vec2(0)))&&all(lessThan(oldUV,vec2(1)))){
            ivec2 base;vec2 f;ptSampleFootprint(oldUV,size,base,f);
            vec3 priorD=vec3(0),priorS=vec3(0);vec2 priorMoments=vec2(0);
            float weights=0.0,priorAge=0.0;vec2 priorMissing=vec2(0);
            for(int y=0;y<2;y++)for(int x=0;x<2;x++){
                ivec2 tap=base+ivec2(x,y);if(any(greaterThanEqual(tap,size)))continue;
                vec4 reactive=texelFetch(colortex9,tap,0);
                // Depth alone accepts a replaced block with a different BSDF.
                if(reactive.b!=materialKey||reactive.a!=colorKey)continue;
                vec4 geometry=texelFetch(colortex13,tap,0),history=texelFetch(colortex12,tap,0);
                if(geometry.a>=0.0||history.a<1.0||history.a>float(PT_HISTORY)+1.0)continue;
                if(abs(geometry.a-oldView.z)>max(.04,g.depth*.002)||dot(wn,octDecode(geometry.rg))<.97)continue;
                float w=(x==0?1.0-f.x:f.x)*(y==0?1.0-f.y:f.y);
                vec4 sh=texelFetch(colortex11,tap,0);
                priorD+=history.rgb*w;priorS+=sh.rgb*w;
                priorMoments+=vec2(geometry.b,sh.a)*w;priorAge+=history.a*w;priorMissing+=reactive.rg*w;weights+=w;
            }
            if(weights>.05){
                priorD/=weights;priorS/=weights;priorMoments/=weights;priorAge/=weights;priorMissing/=weights;
                // Clip stale lighting to the local signal range. Variance keeps
                // rare legitimate light samples from being clipped every frame.
                // A black 3x3 neighborhood is common for rare caustic/emitter
                // samples. Clipping a valid historical mean to that zero range
                // systematically erased light. Include historical sample
                // variance before deciding that illumination is stale.
                vec2 priorMean=vec2(ptLuminance(priorD),ptLuminance(priorS));
                vec2 priorVariance=max(priorMoments-priorMean*priorMean,vec2(0));
                vec2 sigma=sqrt(max(localVariance,priorVariance));
                priorD=clamp(priorD,max(loD-vec3(sigma.x+.025),vec3(0)),hiD+vec3(sigma.x+.025));
                priorS=clamp(priorS,max(loS-vec3(sigma.y+.025),vec3(0)),hiS+vec3(sigma.y+.025));
                // Estimate how many light-bearing samples should have arrived.
                // A lone black neighborhood proves nothing for rare caustics;
                // sustained absence after ~8 expected arrivals is evidence of
                // a lighting change. This reactive reconstruction is biased,
                // optional with temporal filtering, and does not alter transport.
                vec2 probability=clamp(priorMean*priorMean/max(priorMoments,vec2(1e-12)),0.0,1.0);
                for(int channel=0;channel<2;channel++){
                    bool absent=localMean[channel]<max(priorMean[channel]*.01,1e-8)&&priorMean[channel]>.001;
                    missing[channel]=absent?priorMissing[channel]+probability[channel]*localWeight:0.0;
                }
                if(missing.x>=8.0){priorD=currentD;priorMoments.x=moments.x;missing.x=0.0;}
                if(missing.y>=8.0){priorS=currentS;priorMoments.y=moments.y;missing.y=0.0;}
                age=min(priorAge+1.0,float(PT_HISTORY));
                // Moving density has no raster motion vector. A separate cap
                // limits sky/foreground-cloud trails without shortening terrain
                // history everywhere. Reflections retain the specular motion cap.
                if(ptPrimaryCloudSegment(g))age=min(age,float(CLOUD_HISTORY));
                vec2 currentUV=(ptSampleAnchor(px,size)+.5)/vec2(textureSize(depthtex1,0));
                float motion=length((oldUV-currentUV)*vec2(size));
                // Specular lighting changes with the view even on the same mesh.
                specAge=min(age,motion>.5?8.0:float(PT_HISTORY));
                currentD=mix(priorD,currentD,1.0/age);currentS=mix(priorS,currentS,1.0/specAge);
                moments=mix(priorMoments,moments,1.0/vec2(age,specAge));
            }
        }
    }
#endif
    vec2 mean=vec2(ptLuminance(currentD),ptLuminance(currentS));
    vec2 variance=max(moments-mean*mean,vec2(0))/vec2(age,specAge);
    variance=max(variance,localVariance/vec2(age,specAge)*clamp(1.0-age/8.0,0.0,1.0));
    outDiffuse=vec4(currentD,min(variance.x,65000.0));outSpecular=vec4(currentS,min(variance.y,65000.0));
    outHistory=vec4(currentD,age);outSpecHistory=vec4(currentS,moments.y);
    outGeometry=vec4(octEncode(wn),moments.x,-max(g.depth,.0001));
    outReactive=vec4(missing,materialKey,colorKey);
    // Exact 24-bit packed normals require RGBA32F, never RGBA16F. This is a
    // per-frame cache, independent of whether history accumulation is enabled.
    outGuide=vec4(packNormal24(g.ng),packNormal24(g.n),g.depth,float(g.valid));
}
