#version 430 compatibility
// WATER ENTRY: select the shared vertex pipeline and the flags
// appropriate to this Minecraft draw category. See lib/gbuffer.vsh.
#define TERRAIN_MATERIALS
#define WATER_PROGRAM
#include "/lib/gbuffer.vsh"
