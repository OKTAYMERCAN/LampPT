# LampPT 0.7.2 experimental

Select the new ZIP, Reset, Medium, Apply. Saved roughness and filtering overrides
can preserve the old frosted appearance.

- Clear Water and Glass: smooth dielectric pixels trace at the base Lighting
  Resolution instead of the coarser Reflection HRR grid. Old coarse optical paths
  are skipped. This increases optical work; turn the option Off for lower cost.
- Secondary-hit guides: the denoiser uses the traced receiver's color, normal and
  distance to avoid smearing unrelated scenery behind a flat interface. Existing
  intersections and buffer storage provide the guides, without new guide rays.
- Clear Interface Filter: adjustable optical strength, default 0.75. Missing hit
  guides receive only one compact filter rather than repeated broad smoothing.
- Built-in Glass Roughness defaults to 0.001 instead of 0.04. Frosted glass remains
  available by increasing roughness; resource PBR maps may override it.

Real world-space Snell/Fresnel paths, GI, waves, absorption and temporal denoising
are retained. No hybrid fallback or screen-color refraction is introduced. Opaque
tracing grids, scene allocations and bounce budgets remain unchanged. On glass/
water-heavy views, extra optical ray pixels can reduce performance. There is no
claim of free quality, zero residual grain or native-resolution optical detail.

All UI and comments remain English. All 135 options have tooltips; Profile/About
remain first, and normals/POM/powder emission remain Off by default. Tests use
Mesa GLSL, not Minecraft/Iris or NVIDIA gameplay. See TEST_RESULTS.md.
