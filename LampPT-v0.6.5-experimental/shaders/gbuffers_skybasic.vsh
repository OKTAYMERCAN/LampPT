#version 430 compatibility
// SKYBASIC ENTRY: select the shared vertex pipeline and the flags
// appropriate to this Minecraft draw category. See lib/gbuffer.vsh.
out vec4 skyColor;
void main() {
    gl_Position = ftransform();
    skyColor = gl_Color;
}
