#version 430 compatibility
// TEXTURED ENTRY: select the shared fragment pipeline and the flags
// appropriate to this Minecraft draw category. See lib/gbuffer.fsh.
#define UNLIT_TEXTURE
#include "/lib/gbuffer.fsh"
