#version 430 compatibility
// SKYBASIC ENTRY: select the shared fragment pipeline and the flags
// appropriate to this Minecraft draw category. See lib/gbuffer.fsh.
in vec4 skyColor;
uniform int renderStage;
/* DRAWBUFFERS:013 */
layout(location = 0) out vec4 outColor;
layout(location = 1) out vec4 outNormalData;
layout(location = 2) out vec4 outAlbedo;
void main() {
    outColor = skyColor;
    outNormalData = vec4(0.0);
#ifdef MC_RENDER_STAGE_STARS
    if(renderStage==MC_RENDER_STAGE_STARS)outNormalData.a=3.0;
#endif
    outAlbedo = vec4(0.0);
}
