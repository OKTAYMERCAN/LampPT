#version 430 compatibility
// FRAME RESET: only counters need clearing; active BVH nodes are rebuilt after capture.
#include "/lib/scene/storage.glsl"
layout(local_size_x=1)in;
const ivec3 workGroups=ivec3(1,1,1);
void main(){geometryCount=0u;geometryOverflow=0u;geometryPad0=0u;geometryPad1=0u;}
