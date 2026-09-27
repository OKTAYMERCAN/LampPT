// SCENE STORAGE: real terrain triangles and a spatially sorted binary BVH.
// Unlike the old block cube, storage capacity does not set the world distance.
#ifndef LAMPPT_SCENE_STORAGE
#define LAMPPT_SCENE_STORAGE
#include "/lib/settings.glsl"
// Coherence is needed only for child publication within the final build dispatch.
// Cross-pass ordering is provided by Iris SSBO memory barriers.
#if defined(BUILD_STAGE) && BUILD_STAGE == 5
#define SCENE_SHARED coherent
#else
#define SCENE_SHARED
#endif
#define SORT_GROUPS ((GEOMETRY_BUDGET+255)/256)
// Preserve full-precision positions and atlas coordinates (80 bytes/triangle).
struct SceneTriangle {vec4 p0;vec4 p1;vec4 p2;vec4 uv;uvec4 meta;};
layout(std430,binding=1) buffer SceneGeometry {
    uint geometryCount;uint geometryOverflow;uint geometryPad0;uint geometryPad1;
    SceneTriangle sceneTriangles[];
};
// Compact radix BVH: internal nodes [0,n-2], leaves [n-1,2*n-2].
// lo.w is source power; leaf hi.w contains its exact triangle index.
struct SceneNode {vec4 lo;vec4 hi;};
layout(std430,binding=2) SCENE_SHARED buffer SceneHierarchy {SceneNode sceneNodes[];};
layout(std430,binding=0) buffer SceneSort {
    uvec2 sortA[GEOMETRY_BUDGET];
    uvec2 sortB[GEOMETRY_BUDGET];
    uint sortRank[GEOMETRY_BUDGET];
    uvec4 sortHistogram[SORT_GROUPS];
    uvec4 sortOffset[SORT_GROUPS];
};
// Explicit links follow Morton-prefix splits instead of equal-sized array
// halves, which could put spatially distant regions under overlapping boxes.
layout(std430,binding=3) SCENE_SHARED buffer SceneLinks {
    uvec2 sceneChildren[GEOMETRY_BUDGET];
    uint sceneParents[2*GEOMETRY_BUDGET];
    uint sceneReady[GEOMETRY_BUDGET];
};
uint sceneCount(){return min(geometryCount,uint(GEOMETRY_BUDGET));}
uint sceneLeaves(){return max(sceneCount(),1u);}
uint sceneLeafBase(){return sceneLeaves()-1u;}
vec4 sceneMaterial(SceneTriangle t){vec4 v=unpackUnorm4x8(t.meta.w);return vec4(v.r,v.g>.99?-1.0:v.g,unpackHalf2x16(t.meta.w>>16u).x,float((t.meta.x>>24u)&127u));}
float sceneArea(SceneTriangle t){return .5*length(cross(t.p1.xyz-t.p0.xyz,t.p2.xyz-t.p0.xyz));}
#endif
