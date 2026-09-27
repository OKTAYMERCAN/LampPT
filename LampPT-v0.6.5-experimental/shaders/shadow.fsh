#version 430 compatibility
// SHADOW ALPHA: discard transparent atlas texels so texture holes also affect
// the raster sun/moon shadow map, independently of world light sampling.
#include "/lib/settings.glsl"
uniform sampler2D texture;
in vec2 texcoord;
flat in float shadowMaterialKind;
void main() {
    if(shadowMaterialKind>0.5 && shadowMaterialKind<2.5)discard;
    // Terrain vertex alpha contains AO with separateAo enabled. Occlusion
    // must never punch holes in an otherwise surviving shadow caster.
    vec4 c = texture2D(texture, texcoord);
    if (c.a < CUTOUT_THRESHOLD) discard;
}
