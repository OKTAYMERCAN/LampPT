#version 430 compatibility
// DISPLAY: tone mapping and optional lens bloom operate on the traced image.
// They do not inject ambient light, screen-space GI or screen-space reflections.
#include "/lib/ptgi/context.glsl"
#include "/lib/scene/storage.glsl"
#include "/lib/shadow_settings.glsl"
uniform sampler2D colortex7;
in vec2 texcoord;
layout(location=0)out vec4 fragColor;
vec3 toneMap(vec3 c){
    c=max(c,vec3(0.0));
#if TONEMAP == 1
    return saturate((c*(2.51*c+0.03))/(c*(2.43*c+0.59)+0.14));
#else
    float peak=max(c.r,max(c.g,c.b));
    if(peak<=0.85)return c;
    return c*((0.85+0.15*(1.0-exp(-(peak-0.85)/0.15)))/peak);
#endif
}
vec3 resolvedColor(vec2 uv,float weight){
#if DEBUG_VIEW == 10
    if(weight==0.0)return srgbToLinear(texture2D(colortex0,uv).rgb);
#endif
    return texture2D(colortex7,uv).rgb;
}
void main(){
#if DEBUG_VIEW == 1
    fragColor=vec4(texture2D(colortex0,texcoord).rgb,1);return;
#elif DEBUG_VIEW == 2
    fragColor=vec4(linearToSrgb(texture2D(colortex2,texcoord).rgb*DEBUG_GAIN),1);return;
#elif DEBUG_VIEW == 3
    fragColor=vec4(texture2D(colortex1,texcoord).rgb,1);return;
#elif DEBUG_VIEW == 4
    // Green = captured range, yellow = boundary, magenta = missing coverage.
    // Red everywhere means capacity overflow: visibility is incomplete.
    float range=length(ptGuide(texcoord).p)/shadowDistance;
    vec3 status=range<.9?vec3(.05,.7,.2):range<=1.0?vec3(1,.65,0):vec3(.8,0,.8);
    if(geometryOverflow>0u)status=vec3(1,0,0);
    fragColor=vec4(status,1);return;
#elif DEBUG_VIEW == 5
    fragColor=vec4(vec3(texture2D(colortex4,texcoord).b/2.0),1);return;
#elif DEBUG_VIEW == 6
    fragColor=vec4(vec3(texture2D(colortex4,texcoord).r),1);return;
#elif DEBUG_VIEW == 7
    fragColor=vec4(linearToSrgb(texture2D(colortex8,texcoord).rgb*DEBUG_GAIN),1);return;
#elif DEBUG_VIEW == 8
    fragColor=vec4(vec3(texture2D(colortex12,texcoord).a/float(PT_HISTORY)),1);return;
#elif DEBUG_VIEW == 9 || DEBUG_VIEW == 11
    fragColor=vec4(linearToSrgb(texture2D(colortex7,texcoord).rgb*DEBUG_GAIN),1);return;
#elif DEBUG_VIEW == 12
    float useRatio=float(sceneCount())/float(GEOMETRY_BUDGET);
    vec3 status=texcoord.x<useRatio?vec3(.2,.6,.9):vec3(.02);
    if(geometryOverflow>0u)status=vec3(1,0,0);
    fragColor=vec4(status,1);return;
#endif
    vec2 uvScene=texcoord;float giWeight=1.0;
#if DEBUG_VIEW == 10
    uvScene.x=fract(texcoord.x*2.0);giWeight=texcoord.x<.5?0.0:1.0;
#endif
    vec3 color=resolvedColor(uvScene,giWeight);
#if BLOOM_ENABLED == 1
    vec2 pixel=BLOOM_RADIUS/vec2(textureSize(colortex7,0));
    vec3 bloom=vec3(0.0); float weights=0.0;
#if BLOOM_QUALITY == 0
    const int bloomExtent=1;const float bloomSpacing=2.0;
#else
    const int bloomExtent=2;const float bloomSpacing=1.0;
#endif
    for(int y=-bloomExtent;y<=bloomExtent;y++)for(int x=-bloomExtent;x<=bloomExtent;x++){
        float w=1.0/(1.0+float(x*x+y*y)*bloomSpacing*bloomSpacing);
        vec2 uv=clamp(uvScene+vec2(x,y)*pixel*bloomSpacing,vec2(0.0),vec2(1.0));
        bloom+=max(resolvedColor(uv,giWeight)-BLOOM_THRESHOLD,vec3(0.0))*w;weights+=w;
    }
    color+=bloom/weights*BLOOM_STRENGTH;
#endif
    color*=EXPOSURE;
    float l=dot(color,vec3(0.2126,0.7152,0.0722));
    color=max(mix(vec3(l),color,SATURATION),vec3(0.0));
    color=linearToSrgb(toneMap(color));
    color=clamp((color-0.5)*CONTRAST+0.5,0.0,1.0);
    color=pow(color,vec3(1.0/GAMMA_ADJUST));
#if VIGNETTE == 1
    vec2 edge=texcoord*2.0-1.0;
    color*=1.0-VIGNETTE_STRENGTH*pow(clamp(dot(edge,edge)*0.5,0.0,1.0),1.5);
#endif
#if DITHER == 1
    color+=(hash12(gl_FragCoord.xy)-0.5)/255.0;
#endif
    #if DEBUG_VIEW == 10
    if(abs(texcoord.x-0.5)<1.0/float(textureSize(colortex7,0).x))color=vec3(1.0);
#endif
    fragColor=vec4(saturate(color),1.0);
}
