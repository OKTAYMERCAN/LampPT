#version 430 compatibility
#include "/lib/scene/storage.glsl"
#include "/lib/scene/dispatch.glsl"
layout(local_size_x=1)in;
const ivec3 workGroups=ivec3(1,1,1);
void main(){sceneDispatch=uvec4(max(1u,(sceneCount()+255u)/256u),1u,1u,0u);}
