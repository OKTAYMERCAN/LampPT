#version 430 compatibility
// WORLD CAPTURE: pass terrain triangles and materials to the geometry stage.
// The shadow pass is a mesh capture opportunity, not a lighting/shadow-map input.
#include "/lib/shadow_settings.glsl"
#include "/lib/materials.glsl"
#include "/lib/fluid_boundary.glsl"

uniform mat4 shadowModelViewInverse;
uniform vec3 cameraPosition;
uniform sampler2D texture;
#if SPECULAR_MAPS == 1
uniform sampler2D specular;
#endif
uniform int renderStage;
in vec4 mc_Entity;
in vec4 at_midBlock;
in vec2 mc_midTexCoord;

out vec2 shadowTexcoordV;
out vec3 geometryPositionV;

flat out uint geometryDataV;
flat out uint geometryTintV;
flat out uint geometryPbrV;
out vec3 geometryOutwardV;
flat out int geometryCaptureV;
flat out float shadowMaterialKindV;
void main(){
    gl_Position=ftransform();
    geometryCaptureV=0;geometryPositionV=vec3(0.0);geometryDataV=0u;geometryTintV=0u;geometryPbrV=0u;geometryOutwardV=vec3(0,1,0);
    shadowTexcoordV=(gl_TextureMatrix[0]*gl_MultiTexCoord0).xy;
    shadowMaterialKindV=builtinMaterial(mc_Entity.x,vec3(1.0)).a;
#if 1 // Capture all submitted terrain inside the selected range.
    bool terrain=false;
#ifdef MC_RENDER_STAGE_TERRAIN_SOLID
    terrain=renderStage==MC_RENDER_STAGE_TERRAIN_SOLID||renderStage==MC_RENDER_STAGE_TERRAIN_TRANSLUCENT;
#endif
#ifdef MC_RENDER_STAGE_TERRAIN_CUTOUT
    terrain=terrain||renderStage==MC_RENDER_STAGE_TERRAIN_CUTOUT;
#endif
#ifdef MC_RENDER_STAGE_TERRAIN_CUTOUT_MIPPED
    terrain=terrain||renderStage==MC_RENDER_STAGE_TERRAIN_CUTOUT_MIPPED;
#endif
#ifdef MC_RENDER_STAGE_TRIPWIRE
    terrain=terrain||renderStage==MC_RENDER_STAGE_TRIPWIRE;
#endif
    if(terrain){
        vec3 relative=(shadowModelViewInverse*gl_ModelViewMatrix*gl_Vertex).xyz;
        vec3 center=relative+at_midBlock.xyz/64.0;
        if(length(center)<=shadowDistance){
            vec2 mid=(gl_TextureMatrix[0]*vec4(mc_midTexCoord,0.0,1.0)).xy;
            vec4 texel=textureLod(texture,mid,0.0);
            vec3 color=clamp(texel.rgb*gl_Color.rgb,0.0,1.0);
            vec4 sp=vec4(0,0,0,1);
#if SPECULAR_MAPS == 1
            sp=textureLod(specular,mid,0.0);
#endif
            bool translucent=false;
#ifdef MC_RENDER_STAGE_TERRAIN_TRANSLUCENT
            translucent=renderStage==MC_RENDER_STAGE_TERRAIN_TRANSLUCENT;
#endif
            vec4 m=resolveMaterial(mc_Entity.x,at_midBlock.w,translucent,sp);
            if(abs(mc_Entity.x-10010.0)<.5)color=vec3(1);
            uint kind=uint(round(m.a));
            uint tag=(materialDielectric(m.a)?0u:128u)|kind;
            geometryDataV=packUnorm4x8(vec4(color,float(tag)/255.0));
            geometryPositionV=relative;
            geometryTintV=packUnorm4x8(vec4(clamp(gl_Color.rgb,0.0,1.0),1.0));
            geometryCaptureV=1;
            // Preserve emission as a half float. UNORM8 divided by eight made
            // a unit native source disagree with its visible raster material.
            uint surface=packUnorm4x8(vec4(m.r,m.g<0.0?1.0:m.g,0,0))&65535u;
            geometryPbrV=surface|((packHalf2x16(vec2(m.b,0))&65535u)<<16u);
            vec3 physical=gl_Normal;
            if(m.a==1.0)physical=fluidOutward(physical,at_midBlock.xyz);
            geometryOutwardV=normalize(mat3(shadowModelViewInverse)*gl_NormalMatrix*physical);

        }
    }
#endif
}
