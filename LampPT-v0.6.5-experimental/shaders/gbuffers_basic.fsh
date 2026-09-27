#version 430 compatibility
// BASIC ENTRY: select the shared fragment pipeline and the flags
// appropriate to this Minecraft draw category. See lib/gbuffer.fsh.
in vec4 vertexColor;
in vec3 viewNormal;
/* DRAWBUFFERS:013 */
layout(location = 0) out vec4 outColor;
layout(location = 1) out vec4 outNormalData;
layout(location = 2) out vec4 outAlbedo;
void main() {
    outColor = vertexColor;
    outNormalData = vec4(0.0);
    outAlbedo = vec4(0.0);
}
