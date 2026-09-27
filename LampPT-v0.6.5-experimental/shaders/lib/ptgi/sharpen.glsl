// OPTIONAL SHARPENING: bounded, noise-aware detail recovery after PT upscaling.
// This is not AMD RCAS. It operates in a bounded HDR compression and clamps to
// neighborhood extrema, avoiding negative light and overshoot around emitters.
#include "/lib/ptgi/context.glsl"
uniform sampler2D colortex7;
in vec2 texcoord;
/* RENDERTARGETS:7 */
layout(location=0)out vec4 outScene;
vec3 ptCompress(vec3 c){c=max(c,vec3(0));return c/(1.0+c);}
void main(){
    ivec2 size=textureSize(colortex7,0),p=screenPixel(texcoord,size);
    vec3 original=texelFetch(colortex7,p,0).rgb;
    outScene=vec4(original,1);
#if PT_SHARPEN == 1 && DEBUG_VIEW == 0
    vec3 c=ptCompress(original),sum=vec3(0),lo=c,hi=c;
    const ivec2 offsets[4]=ivec2[4](ivec2(-1,0),ivec2(1,0),ivec2(0,-1),ivec2(0,1));
    for(int i=0;i<4;i++){
        vec3 n=ptCompress(texelFetch(colortex7,clamp(p+offsets[i],ivec2(0),size-1),0).rgb);
        sum+=n;lo=min(lo,n);hi=max(hi,n);
    }
    // Remaining transport variance suppresses sharpening of Monte Carlo grain.
    ivec2 q=screenPixel(texcoord,textureSize(colortex8,0));
    float variance=max(texelFetch(colortex8,q,0).a+texelFetch(colortex2,q,0).a,0.0);
    float signal=max(ptLuminance(original),.1);
    float trust=1.0/(1.0+4.0*sqrt(variance)/signal);
    float contrast=max(hi.r-lo.r,max(hi.g-lo.g,hi.b-lo.b));
    float gain=PT_SHARPNESS*trust*(1.0-.5*clamp(contrast,0.0,1.0));
    vec3 sharp=clamp(c+(c-sum*.25)*gain,lo,hi);
    outScene.rgb=clamp(sharp/max(vec3(1)-sharp,vec3(1e-5)),vec3(0),vec3(65000));
#endif
}
