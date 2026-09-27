#version 430 compatibility
// SCENE BUILD ENTRY: bounded, sequential GPU construction of the terrain BVH.
#include "/lib/settings.glsl"
const ivec3 workGroups=ivec3(1,1,1);
#define BUILD_STAGE 2
#define RADIX_SHIFT 0
#include "/lib/scene/build.glsl"
