// MATERIAL CLASSIFICATION: map block IDs to roughness, emission and source color.
// Visible glow can use a texture mask; world-space source identity is block-wide.
#ifndef LAMPPT_MATERIALS
#define LAMPPT_MATERIALS
#include "/lib/settings.glsl"
#include "/lib/common.glsl"
// kind: 0=ordinary, 1=water, 2=glass, 3..7=large emitters, 8..23=RGB emission,
// 24=end rod, 25..28=small warm/cold/red/purple emitters.
// colortex4: roughness, dielectric F0 or negative metal sentinel, emission, kind.
// The same classification is used by raster guides and captured ray hits.
// 29=ice, 30=honey, 31=slime, 32=tinted glass, 33=held thin sheet,
// 34=unmapped translucent terrain. These are optical classes, not emitters.
bool materialDielectric(float kind){return (kind>.5&&kind<2.5)||(kind>28.5&&kind<34.5);}
float materialIor(float kind){
    if(kind==1.0)return WATER_IOR;
    if(kind==29.0)return 1.31;
    if(kind==30.0)return 1.47;
    if(kind==31.0)return 1.40;
    return PT_GLASS_IOR;
}
vec3 sourceTint(float kind) {
    if(kind>24.5&&kind<28.5)kind-=22.0;
    if (kind > 2.5 && kind < 3.5) return vec3(WARM_R, WARM_G, WARM_B);
    if (kind > 3.5 && kind < 4.5) return vec3(COLD_R, COLD_G, COLD_B);
    if (kind > 4.5 && kind < 5.5) return vec3(RED_R, RED_G, RED_B);
    if (kind > 5.5 && kind < 6.5) return vec3(PURPLE_R, PURPLE_G, PURPLE_B);
    if (kind > 6.5 && kind < 7.5) return vec3(WARM_R, WARM_G * 0.5, WARM_B * 0.25);
    return vec3(1.0);
}
// Radiance is energy per emitting area. A 2/16-wide torch must emit much more
// radiance than a whole glowing cube to light a room. Keep that distinction in
// both direct sampling and BSDF hits; it is not a point-light or ambient fallback.
float smallSourceScale(float kind){
    float scale=1.0;
    if(kind>24.5&&kind<26.5)scale=64.0;
    else if(kind>26.5&&kind<27.5)scale=16.0;
    else if(kind>27.5&&kind<28.5)scale=8.0;
    else if(kind>23.5&&kind<24.5)scale=8.0;
    return scale>1.0?scale*SMALL_LIGHT_BOOST:1.0;
}
vec3 emissionRadiance(vec4 material, vec3 albedo) {
#if EMISSIVE_ENABLED == 1
    bool mapped=(material.a>2.5&&material.a<7.5)||(material.a>24.5&&material.a<28.5);
    vec3 tint = mapped ? sourceTint(material.a) : albedo;
    if(material.a>23.5&&material.a<24.5)tint=vec3(1.0); // End-rod light is neutral white.
    float l = dot(tint, vec3(0.2126, 0.7152, 0.0722));
    tint = max(mix(vec3(l), tint, LIGHT_SATURATION), vec3(0.0));
    return tint * max(material.b, 0.0) * EMISSIVE_STRENGTH * smallSourceScale(material.a);
#else
    return vec3(0.0);
#endif
}
// PT capture stores an unmasked mapped source. Evaluate luminous artwork at
// the actual hit UV so stems stay dark without removing the emitting surface.
vec4 ptTexelEmission(vec4 material,vec3 texel){
    if(material.a>23.5&&material.a<28.5)
        material.b*=smoothstep(.60,.90,max(texel.r,max(texel.g,texel.b)));
    else if(material.a>2.5&&material.a<7.5)
        material.b*=smoothstep(.15,.65,max(texel.r,max(texel.g,texel.b)));
    return material;
}
vec4 builtinMaterial(float id, vec3 albedo) {
    bool smallSource=id>10199.5&&id<10203.5;
    if(id>10199.5 && id<10203.5)id=10001.0+(id-10200.0);
    vec4 m = vec4(DEFAULT_ROUGHNESS, 0.04, 0.0, 0.0);
    if(id>10203.5&&id<10204.5)m=vec4(.45,.04,1.0,24.0);
    if(id>10099.5 && id<10100.5){
#if POWDER_EMISSION == 1
        m.b=POWDER_STRENGTH;
        m.a=8.0;
#endif
        return m; // Dark powder is dim, but not removed by a torch-texture mask.
    }
    if (id > 9999.5 && id < 10000.5) m = vec4(WATER_ROUGHNESS, 0.02, 0.0, 1.0);
    if (id > 10000.5 && id < 10001.5) m = vec4(0.6, 0.04, 1.0, 3.0);
    if (id > 10001.5 && id < 10002.5) m = vec4(0.6, 0.04, 1.0, 4.0);
    if (id > 10002.5 && id < 10003.5) m = vec4(0.6, 0.04, 0.8, 5.0);
    if (id > 10003.5 && id < 10004.5) m = vec4(0.35, 0.06, 0.7, 6.0);
    if (id > 10004.5 && id < 10005.5) m = vec4(0.5, 0.04, 1.5, 7.0);
    if (id > 10009.5 && id < 10010.5) m = vec4(GLASS_ROUGHNESS, 0.04, 0.0, 2.0);
    if (id > 10012.5 && id < 10013.5) m = vec4(GLASS_ROUGHNESS, 0.04, 0.0, 2.0);
    if (id > 10010.5 && id < 10011.5) m = vec4(0.22, -1.0, 0.0, 0.0);
    if (id > 10011.5 && id < 10012.5) m = vec4(0.12, 0.05, 0.0, 0.0);
    if(id>10013.5&&id<10014.5)m=vec4(GLASS_ROUGHNESS,.04,0,32);
    if(id>10014.5&&id<10015.5)m=vec4(.08,.02,0,29);
    if(id>10015.5&&id<10016.5)m=vec4(.16,.04,0,30);
    if(id>10016.5&&id<10017.5)m=vec4(.20,.04,0,31);
    if(id>10017.5&&id<10018.5)m=vec4(.6,.04,1.0,8.0); // Froglight artwork supplies its own source color.
    if(smallSource)m.a+=22.0;
    // A brightness mask keeps torch stems and dark lamp borders from emitting.
    return ptTexelEmission(m,albedo);
}
// Native emission and PBR emission agree for visible sources and ray hits.
// Resolve identity before masking luminous artwork; never erase glass identity.
vec4 resolveMaterial(float id,float nativeEmission,bool translucent,vec4 sp){
    vec4 m=builtinMaterial(id,vec3(1));
    if(translucent&&m.a==0.0&&m.b==0.0&&m.g>=0.0)m=vec4(GLASS_ROUGHNESS,.04,0,34);
    if(m.a==1.0)return m;
#if SPECULAR_MAPS == 1
    if(sp.r>.001||sp.g>.001){
        m.r=max(pow(1.0-sp.r,2.0),.02);
#if PBR_FORMAT == 1
        m.g=sp.g>=229.5/255.0?-1.0:sp.g;
#else
        m.g=sp.g>.5?-1.0:.04;
#endif
    }
#if PBR_FORMAT == 1
    float emission=sp.a<254.5/255.0?sp.a*(255.0/254.0):0.0;
#else
    float emission=sp.b;
#endif
    m.b=max(m.b,emission);
#endif
    if(m.a==0.0||materialDielectric(m.a))m.b=max(m.b,clamp(nativeEmission/15.0,0.0,1.0));
    if(m.a==0.0){
        if(m.b>0.0)m.a=8.0+clamp(ceil(m.b*15.0),1.0,15.0);
    }
    return m;
}
#endif
