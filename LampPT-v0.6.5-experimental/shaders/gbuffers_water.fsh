#version 430 compatibility
// WATER ENTRY: select the shared fragment pipeline and the flags
// appropriate to this Minecraft draw category. See lib/gbuffer.fsh.
#define TERRAIN_MATERIALS
#define WATER_PROGRAM
#include "/lib/gbuffer.fsh"
