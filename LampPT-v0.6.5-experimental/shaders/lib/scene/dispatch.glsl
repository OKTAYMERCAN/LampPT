// INDIRECT BUILD COMMAND: written after capture, consumed in ordered passes.
// Counts are clamped to allocated storage and at least one group initializes
// the empty-scene root. Four uints keep the command at a 16-byte boundary.
#ifndef LAMPPT_SCENE_DISPATCH
#define LAMPPT_SCENE_DISPATCH
layout(std430,binding=4) buffer SceneDispatch {uvec4 sceneDispatch;};
#endif
