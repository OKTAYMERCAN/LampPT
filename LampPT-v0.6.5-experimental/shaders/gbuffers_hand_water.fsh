#version 430 compatibility
// HAND WATER ENTRY: select the shared fragment pipeline and the flags
// appropriate to this Minecraft draw category. See lib/gbuffer.fsh.
#define NO_GI
#define WATER_PROGRAM
#include "/lib/gbuffer.fsh"
