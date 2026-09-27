#version 430 compatibility
// SCENE BUILD ENTRY: bounded, sequential GPU construction of the terrain BVH.
#include "/lib/settings.glsl"
#if GEOMETRY_BUDGET == 65536
const ivec3 workGroups=ivec3(256,1,1);
#elif GEOMETRY_BUDGET == 262144
const ivec3 workGroups=ivec3(1024,1,1);
#elif GEOMETRY_BUDGET == 524288
const ivec3 workGroups=ivec3(2048,1,1);
#elif GEOMETRY_BUDGET == 1048576
const ivec3 workGroups=ivec3(4096,1,1);
#elif GEOMETRY_BUDGET == 1572864
const ivec3 workGroups=ivec3(6144,1,1);
#endif
#define BUILD_STAGE 3
#define RADIX_SHIFT 20
#include "/lib/scene/build.glsl"
