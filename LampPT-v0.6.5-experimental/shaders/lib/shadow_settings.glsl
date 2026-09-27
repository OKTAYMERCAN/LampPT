// CAPTURE CONFIGURATION: the shadow pass supplies geometry, not lighting.
#ifndef LAMPPT_SHADOW_SETTINGS
#define LAMPPT_SHADOW_SETTINGS
#include "/lib/settings.glsl"
const int shadowMapResolution = 256;
const float shadowDistance = 128.0; // [64.0 96.0 128.0 192.0 256.0 384.0]
const float shadowDistanceRenderMul = 1.0;
#endif
