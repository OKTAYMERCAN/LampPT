// ENVIRONMENT: compute dimension-aware sun/moon radiance and atmosphere color.
// Non-directional dimensions retain their native sky rather than inventing a sun.
#ifndef LAMPPT_ENVIRONMENT
#define LAMPPT_ENVIRONMENT
#include "/lib/settings.glsl"
#include "/lib/common.glsl"
uniform bool hasSkylight;
uniform bool hasCeiling;
uniform int biome_category;
bool directionalSky(){
#ifdef CAT_THE_END
    if(biome_category==CAT_THE_END)return false;
#endif
    return hasSkylight&&!hasCeiling;
}
float dayAmount(vec3 sunDirection){return smoothstep(-0.10,0.12,sunDirection.y);}
vec3 sunlightColor(vec3 sunDirection){
    float elevation=smoothstep(0.0,0.55,sunDirection.y);
    vec3 tint=mix(vec3(1.0,0.34,0.10),vec3(1.0,0.91,0.78),elevation);
    return mix(vec3(1.0),tint,SUN_WARMTH);
}
vec3 mainLightRadiance(vec3 sunDirection,float rain){
    if(!directionalSky())return vec3(0.0);
    float day=dayAmount(sunDirection);
    float horizon=smoothstep(-0.05,0.12,abs(sunDirection.y));
    vec3 solar=sunlightColor(sunDirection)*3.0*SUN_INTENSITY;
    vec3 lunar=vec3(0.38,0.53,0.85)*MOON_INTENSITY;
    return mix(lunar,solar,day)*horizon*(1.0-clamp(rain,0.0,1.0)*0.85);
}
vec3 atmosphereColor(vec3 direction,vec3 sunDirection,vec3 vanillaSky,float rain){
#if CUSTOM_SKY == 1
    if(!directionalSky())return srgbToLinear(vanillaSky);
    float day=dayAmount(sunDirection);
    float elevation=pow(clamp(direction.y,0.0,1.0),0.45);
    vec3 noon=mix(vec3(0.47,0.62,0.83),vec3(0.07,0.22,0.49),elevation);
    float sunset=(1.0-smoothstep(0.0,0.32,abs(sunDirection.y)))*day;
    float glow=pow(max(dot(direction,sunDirection),0.0),8.0);
    noon=mix(noon,vec3(0.92,0.28,0.07),sunset*glow*SKY_HAZE);
    vec3 night=mix(vec3(0.007,0.013,0.028),vec3(0.001,0.003,0.012),elevation);
    vec3 sky=mix(night,noon,day);
    float luminance=dot(sky,vec3(0.2126,0.7152,0.0722));
    sky=mix(vec3(luminance),sky,SKY_SATURATION);
    return mix(sky,vec3(luminance*0.65),clamp(rain,0.0,1.0)*0.8);
#else
    return srgbToLinear(vanillaSky);
#endif
}
#endif
