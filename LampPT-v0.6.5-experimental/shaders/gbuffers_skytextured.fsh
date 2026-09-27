#version 430 compatibility
// SKYTEXTURED ENTRY: select the shared fragment pipeline and the flags
// appropriate to this Minecraft draw category. See lib/gbuffer.fsh.
#define UNLIT_TEXTURE
#define CELESTIAL_PROGRAM
#include "/lib/gbuffer.fsh"
