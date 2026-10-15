# LampPT 0.7.1 experimental

## Install

Select this exact ZIP, Reset, select Medium, Apply. Keep Temporal Accumulation,
Spatial Denoiser and Sparse Sample Reconstruction On. Adaptive Sharpening starts
Off. Old per-pack overrides can retain the previous darker water coefficients.

## Changed

- Replaced homogeneous RGB-extinction free-flight sampling with scattering-only
  sampling plus analytic colored absorption. This avoids rare enormous water
  throughput weights while preserving the expected transport integral.
- Added bounded first-filter recurrent stabilization for diffuse and rough opaque
  lighting. Later wide filters and water/glass optics never feed back.
- Added optical-normal history and an adjustable water/glass history cap. Moving
  wave refraction refreshes instead of holding the old optical image too long.
- Kept smooth-interface spatial reconstruction compact to preserve more detail.
- Added adjustable short water ripples using the same wave normal for primary
  refraction, traced secondary intersections and caustic guiding.
- Lowered Water Absorption to 0.08 and Scattering to 0.02; Blue transmission is
  0.75. These are editable material defaults, not a replacement ambient term.
- Added English options/tooltips: History Stabilization (0.25), Optical History
  Limit (16), Water Ripple Detail (0.35). All four presets set these consistently.

## Retained

World-space mesh PT; no hybrid fallback. Same four preset ray/grid budgets,
independent HRR controls, reflection/effect switches, editable About, and default
Off normal maps/POM/powder emission. Stackless BVH and single merge trace call site
remain. No new image allocations, render passes or camera path samples.

## Limits

Two existing history targets receive extra writes and ripples add wave math.
No Minecraft FPS comparison was possible. Feedback can soften narrow highlights
or trail changed lighting; set History Stabilization to 0 if needed. Smooth
optical detail still shares the reflection HRR grid, so finer water costs more
resolution. Rare paths, movement and newly revealed surfaces can remain noisy.
Water geometry is not displaced; waves perturb Snell/Fresnel normals. Finite
terrain capture and other renderer limits in README.md remain. Test results are
synthetic Mesa GLSL, not NVIDIA/Iris gameplay validation. See TEST_RESULTS.md.
