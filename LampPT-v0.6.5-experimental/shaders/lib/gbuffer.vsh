// GEOMETRY INPUT: transform vertices to view/clip space and pass material IDs,
// lightmap coordinates and per-tile atlas bounds to the material shader.
#include "/lib/fluid_boundary.glsl"
out vec2 lmcoord;
out vec2 texcoord;
out vec4 vertexColor;
out vec3 viewNormal;
out vec3 viewPositionV;
flat out vec4 atlasBounds;
flat out float blockId;
flat out float nativeEmission;
#ifdef TERRAIN_MATERIALS
in vec2 mc_midTexCoord;
in vec4 mc_Entity;
in vec4 at_midBlock;
#endif
void main() {
    gl_Position = ftransform();
    texcoord = (gl_TextureMatrix[0] * gl_MultiTexCoord0).xy;
    lmcoord = (gl_TextureMatrix[1] * gl_MultiTexCoord1).xy;
    vertexColor = gl_Color;
    viewNormal = gl_NormalMatrix * gl_Normal;
    viewPositionV = (gl_ModelViewMatrix * gl_Vertex).xyz;
    blockId = 0.0;nativeEmission=0.0;
    atlasBounds = vec4(0.0, 0.0, 1.0, 1.0);
#ifdef TERRAIN_MATERIALS
    vec2 mid = (gl_TextureMatrix[0] * vec4(mc_midTexCoord, 0.0, 1.0)).xy;
    vec2 halfTile = abs(texcoord - mid);
    atlasBounds = vec4(mid - halfTile, mid + halfTile);
    blockId = mc_Entity.x;nativeEmission=at_midBlock.w;
    if(abs(blockId-10000.0)<.5)viewNormal=gl_NormalMatrix*fluidOutward(gl_Normal,at_midBlock.xyz);
#endif
}
