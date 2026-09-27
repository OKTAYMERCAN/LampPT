#version 430 compatibility
// BASIC ENTRY: select the shared vertex pipeline and the flags
// appropriate to this Minecraft draw category. See lib/gbuffer.vsh.
out vec4 vertexColor;
out vec3 viewNormal;
void main() {
    gl_Position = ftransform();
    vertexColor = gl_Color;
    viewNormal = normalize(gl_NormalMatrix * gl_Normal);
}
