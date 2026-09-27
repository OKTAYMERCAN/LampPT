// MATERIAL PASS: read atlas/PBR maps, optionally apply normal mapping and POM,
// and write separate albedo, normal, material and lightmap buffers for later lighting.
#include "/lib/settings.glsl"
#include "/lib/common.glsl"
#include "/lib/materials.glsl"
#include "/lib/water.glsl"
#include "/lib/translucent_data.glsl"
uniform sampler2D texture;
uniform sampler2D lightmap;
#if NORMAL_MAPS == 1 || POM == 1
uniform sampler2D normals;
#endif
#if SPECULAR_MAPS == 1
uniform sampler2D specular;
#endif
uniform float alphaTestRef;
uniform float frameTimeCounter;
uniform vec3 cameraPosition;
uniform mat4 gbufferModelView;
uniform mat4 gbufferModelViewInverse;
uniform vec3 shadowLightPosition;
in vec2 lmcoord;
in vec2 texcoord;
in vec4 vertexColor;
in vec3 viewNormal;
in vec3 viewPositionV;
flat in vec4 atlasBounds;
flat in float blockId;
flat in float nativeEmission;
#ifdef WATER_PROGRAM
/* RENDERTARGETS:0,14,15,5 */
layout(location=0) out vec4 outColor;
layout(location=1) out vec4 outTransmissionNormal;
layout(location=2) out vec4 outTransmissionTint;
layout(location=3) out vec4 outTransmissionMaterial;
#else
/* RENDERTARGETS:0,1,3,4,10 */
layout(location=0) out vec4 outColor;
layout(location=1) out vec4 outNormalData;
layout(location=2) out vec4 outAlbedo;
layout(location=3) out vec4 outMaterial;
layout(location=4) out vec4 outLightmap;
#endif

#if PBR_FORMAT == 1
#define USE_LAB
#endif

mat3 surfaceFrame(vec3 n) {
    vec3 a = dFdx(viewPositionV), b = dFdy(viewPositionV);
    vec2 u = dFdx(texcoord), v = dFdy(texcoord);
    float det = u.x*v.y - u.y*v.x;
    if (abs(det) < 1e-10) return tangentBasis(n);
    vec3 t = (a*v.y - b*u.y) / det;
    vec3 bt = (-a*v.x + b*u.x) / det;
    t = safeNormalize(t - n*dot(n,t));
    bt = safeNormalize(bt - n*dot(n,bt) - t*dot(t,bt));
    return mat3(t,bt,n);
}
vec2 materialUV(vec2 uv, mat3 frame, vec2 dx, vec2 dy) {
#if POM == 1 && defined(TERRAIN_MATERIALS)
    vec2 extent = atlasBounds.zw - atlasBounds.xy;
    if (min(extent.x,extent.y) < 1e-6 || length(viewPositionV) > POM_DISTANCE) return uv;
    if (textureGrad(normals,uv,dx,dy).a > 0.9999) return uv;
    vec2 margin = 0.5 / vec2(textureSize(texture,0));
    vec2 lo = atlasBounds.xy + margin, hi = atlasBounds.zw - margin;
    if (any(greaterThanEqual(lo,hi))) return uv;
    vec3 v = transpose(frame) * safeNormalize(-viewPositionV);
    float fade = 1.0 - smoothstep(POM_DISTANCE*0.7,POM_DISTANCE,length(viewPositionV));
    // Fade at grazing angles and tile edges instead of stretching a clamped
    // border texel into a wide stripe. Keep the displacement inside this tile.
    vec2 localUV=(uv-atlasBounds.xy)/extent;
    float edge=min(min(localUV.x,localUV.y),min(1.0-localUV.x,1.0-localUV.y));
    fade*=smoothstep(.02,.12,edge)*smoothstep(.10,.35,abs(v.z));
    vec2 relativeShift=-v.xy/max(abs(v.z),.20)*POM_DEPTH*fade;
    relativeShift*=min(1.0,.12/max(length(relativeShift),1e-6));
    vec2 shift=relativeShift*extent;
    float previous = 0.0, current = 0.0;
    for (int i=1;i<=POM_STEPS;i++) {
        current=float(i)/float(POM_STEPS);
        float h=1.0-textureGrad(normals,clamp(uv+shift*current,lo,hi),dx,dy).a;
        if (current>=h) break;
        previous=current;
    }
    for (int j=0;j<POM_REFINEMENT;j++) {
        float mid=(previous+current)*0.5;
        float h=1.0-textureGrad(normals,clamp(uv+shift*mid,lo,hi),dx,dy).a;
        if (mid>=h) current=mid; else previous=mid;
    }
    return clamp(uv+shift*current,lo,hi);
#else
    return uv;
#endif
}
void main() {
    vec3 geometric = safeNormalize(viewNormal);
    mat3 frame = surfaceFrame(geometric);
    vec2 dx=dFdx(texcoord), dy=dFdy(texcoord);
    // Resource-pack height, normals or emission must not turn procedural
    // water into a glass/opaque material. Its identity comes from the block ID.
    bool proceduralWater=blockId>9999.5&&blockId<10000.5;
    vec2 uv=proceduralWater?texcoord:materialUV(texcoord,frame,dx,dy);
    vec4 texel=textureGrad(texture,uv,dx,dy);
    vec4 albedo=texel*vertexColor;
#ifdef TERRAIN_MATERIALS
    // separateAo stores terrain AO in vertex alpha, not opacity or albedo.
    albedo.a=texel.a;
#endif
    if (albedo.a < max(alphaTestRef,0.001)) discard;
    vec3 n=geometric;
    float materialAO=1.0;
#if NORMAL_MAPS == 1
    if(!proceduralWater){
        vec4 nt=textureGrad(normals,uv,dx,dy);
        vec3 tn=nt.rgb*2.0-1.0;
#if NORMAL_Y_FLIP == 1
        tn.y=-tn.y;
#endif
        tn.xy*=NORMAL_STRENGTH;
#ifdef USE_LAB
        // Scale XY BEFORE reconstructing Z. Previously an extreme XY input
        // kept z=0 even at low strength, producing sideways mirror normals.
        float xy2=dot(tn.xy,tn.xy);
        tn.xy*=min(1.0,.92/sqrt(max(xy2,1e-8)));
        tn.z=sqrt(max(1.0-dot(tn.xy,tn.xy),.001));
        // Baked material AO is excluded: PT tests geometric visibility.
#else
        tn.z=max(tn.z,.25);
#endif
        n=safeNormalize(frame*safeNormalize(tn));
    }
#endif
    vec4 sp=vec4(0,0,0,1);
#if SPECULAR_MAPS == 1
    sp=textureGrad(specular,uv,dx,dy);
#if PBR_FORMAT == 1
    // Metal IDs are categorical, so do not interpolate the F0/metal channel.
    ivec2 specSize=textureSize(specular,0);
    sp.g=texelFetch(specular,clamp(ivec2(uv*vec2(specSize)),ivec2(0),specSize-1),0).g;
#endif
#endif
#ifdef WATER_PROGRAM
    bool translucent=true;
#else
    bool translucent=false;
#endif
    vec4 m=ptTexelEmission(resolveMaterial(blockId,nativeEmission,translucent,sp),texel.rgb);
#if defined(WATER_PROGRAM) && !defined(TERRAIN_MATERIALS)
    // Held translucent items have no captured exit mesh. Treat them as a thin
    // sheet, rather than leaving the path trapped in an infinite glass medium.
    if(materialDielectric(m.a))m.a=33.0;
#endif
    float mask=albedo.a>=0.99 ? 1.0 : 0.0;
#ifdef TERRAIN_MATERIALS
    // Surviving solid/cutout terrain fragments participate in lighting.
    // Translucent terrain is explicitly excluded by WATER_PROGRAM below.
    mask=1.0;
#endif
#ifdef UNLIT_TEXTURE
    mask=0.0;
#endif
#ifdef CELESTIAL_PROGRAM
    mask=3.0;
#endif
#ifdef WATER_PROGRAM
    mask=4.0; // Glass and other translucent surfaces do not replace opaque G-buffers.
#if 1 // Always retain water boundaries, including with optical effects disabled.
    if (m.a>0.5 && m.a<1.5) {
        mask=2.0;
        m.r=WATER_ROUGHNESS;
#if WATER_WAVES == 1
        vec3 wn=mat3(gbufferModelViewInverse)*geometric;
        vec3 wp=(gbufferModelViewInverse*vec4(viewPositionV,1.0)).xyz+cameraPosition;
        if (abs(wn.y)>0.5) n=safeNormalize(mat3(gbufferModelView)*waterWaveNormal(wp.xz,frameTimeCounter)*sign(wn.y));
#endif
    }
#endif
#endif
#ifdef UNLIT_TEXTURE
    vec3 lighting=vec3(1.0);
#else
    vec3 lighting=texture2D(lightmap,lmcoord).rgb;
#endif
#ifdef TERRAIN_MATERIALS
    lighting*=clamp(vertexColor.a,0.0,1.0);
    // oldLighting is disabled so baked face shading never enters albedo.
    // Retain an approximate vanilla reference only in the raw color buffer.
    vec3 rawWorldNormal=mat3(gbufferModelViewInverse)*geometric;
    lighting*=dot(rawWorldNormal*rawWorldNormal,vec3(0.6,rawWorldNormal.y>0.0?1.0:0.5,0.8));
#endif
#if NORMAL_MAPS == 1
    vec3 lightDir=safeNormalize(shadowLightPosition);
    float relief=(0.35+0.65*max(dot(n,lightDir),0.0))/(0.35+0.65*max(dot(geometric,lightDir),0.0));
    lighting*=clamp(relief,0.3,2.0)*materialAO;
#endif
    outColor=vec4(albedo.rgb*lighting,albedo.a);
#ifdef WATER_PROGRAM
    // Keep water behind glass: writing zero alpha leaves the other attachment
    // untouched. Each type keeps its nearest layer through sorted depth draws.
    outTransmissionNormal=vec4(0.0);outTransmissionTint=vec4(0.0);outTransmissionMaterial=vec4(0.0);
    if(mask>1.5&&mask<2.5){
        outTransmissionNormal=vec4(packNormal24(n),packNormal24(geometric),max(-viewPositionV.z,0.0001),1.0);
    }else{
        vec3 tint=albedo.rgb;
        if(blockId>10009.5&&blockId<10010.5)tint=vec3(1.0);
        outTransmissionTint=vec4(packRGB24(tint),max(-viewPositionV.z,0.0001),
            packNormal24(n),1.0);
        outTransmissionMaterial=vec4(packMaterial24(m),m.b,packNormal24(geometric),1.0);
    }
#else
    outNormalData=vec4(encodeNormal(n),mask);
    // Preserve interpolated block/sky light. Four-bit rounding produced
    // visible contours aligned with the triangles of otherwise flat blocks.
    vec2 lm=clamp((lmcoord*16.0-0.5)/15.0,0.0,1.0);
    float surfaceAO=materialAO;
#ifdef TERRAIN_MATERIALS
    surfaceAO*=clamp(vertexColor.a,0.0,1.0);
#endif
    outAlbedo=vec4(albedo.rgb,surfaceAO);
    outMaterial=m;
    outLightmap=vec4(lm,octEncode(geometric));
#endif
}
