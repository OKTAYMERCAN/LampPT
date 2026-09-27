# Troubleshooting — 0.6.5

Select the new ZIP, Reset options, choose Med and set Diagnostic View to Final
Image. A saved settings file from older versions can contain obsolete values.

| Symptom | Check |
| --- | --- |
| Far objects do not occlude/reflection ends | Scene Coverage. Increase capture range and ensure chunks are loaded; Ray Length alone does not help. |
| Whole scene is black in daylight | Confirm version 0.6.5 and reset saved settings. The previous overflow flag blacked out every missed light ray; that policy remains removed. Check Sunlight, Skylight and capture diagnostics. |
| Torch is bright but its surroundings are dark | Emissive Lighting must be On; Small Light Power defaults to 1.0 with calibrated torch radiance. Check capture and resource textures. Real walls still block source connections. Held items are not captured secondary emitters. |
| Complicated silhouettes have dark patches | Traversal Budget still conservatively stops an exhausted ray. Test a higher budget cautiously; it costs tracing time. |
| Missing shadows or light leaks in dense scenes | Triangle Capacity red means geometry was dropped. Increase capacity or reduce capture range. Dropped triangles cannot block light. |
| Bright single-pixel speckles | Keep sun/sky sampling enabled and temporal/spatial reconstruction on. Try more paths or emitter samples if GPU time allows. Glass/caustics need more samples than matte surfaces. |
| Fine reflections look soft | Reduce Specular Filter Strength or try 100% Lighting Resolution. Native traces 6.25 times the new Med pixel count; Detail upscaling is another option with extra cost. |
| Thin walls leak light | Keep Ray Origin Offset near 0.005. Check that geometry lies within capture and is terrain rather than an uncaptured entity. |
| Glass is dark / nested glass is incomplete | Check the separate Interface Limit budget and capture. Interfaces no longer consume Scattering Events. Missing faces/intersections or an unknown starting glass medium remain limitations. |
| Reflections Off makes metal dark | Expected: a metal primarily reflects. The renderer does not substitute vanilla ambient light. |
| Water is black | Reset the new water roughness/scattering defaults and check capture, Sunlight and Skylight. Use Interface Limit 8 with Med. Deep unlit water can still be physically dark; no ambient light is injected. |
| Water does not show caustics | Caustic Paths, Caustic Guiding, Refraction and Water Enabled must be On; underwater sunlight also needs sufficient scattering/interface depth. Small caustics remain difficult to sample. |
| Water is noisy | Keep Temporal Accumulation, Spatial Reconstruction and Water and Glass Filter enabled. The filter now preserves rare-sample history and remains stronger while variance is high. More History Frames help stationary views; more paths cost GPU time. Motion and thin refractive details remain difficult. |
| Frame rate drops | Start Med at 40% / Fast or Low at 33% / Fast under Performance and Upscaling. Try sharpening Off, one spatial pass, or lower water/cloud budgets. Capture/BVH cost does not shrink with PT resolution. See PERFORMANCE.md. |
| Shader fails to load | Provide the exact Iris/Sodium/Minecraft versions and relevant `logs/latest.log` error/stack trace. A screenshot alone cannot establish a loader exception's cause. |

The historical `Index 1 out of bounds for length 1` cannot be diagnosed from its
message alone. This pack uses four literal values in all clear colors and checks
menu references/buffer sizes, but these checks do not replace an Iris runtime log.

The build was tested in Mesa OpenGL, not inside Minecraft. If reproducing a
problem, include the active profile, changed options, Capture/Capacity diagnostics,
resource pack name, and whether the object is terrain or an entity. Do not report
synthetic evidence images as game screenshots.

## After updating to 0.6.5

Select the new ZIP, reset shader options, then choose Med and Apply. Do not reuse
an older extracted folder with the same name: framebuffer formats and material
records changed. A proper pack reload recreates history. If a remaining issue
appears, include the exact ZIP/version, selected profile, a screenshot and the
relevant Iris error/log excerpt. Compilation tests here do not replace a game run.

## Clouds and water focusing

- **No clouds:** check Sky and Volumes -> Volumetric Clouds, the Volumetric
  Scattering master switch, nonzero coverage and the layer height. Clouds are
  limited to dimensions with a directional sky; flying above the layer changes
  which directions see it. Vanilla clouds are deliberately disabled.
- **Cloud grain or trails:** keep Spatial Reconstruction on and adjust Cloud
  Reconstruction Strength / Cloud History Limit. More history reduces static
  noise but can trail animated density. Wind Speed 0 is useful for comparison.
- **Horizon density bands:** increase Cloud Density Steps and Cloud Shadow Steps,
  or increase Cloud Shape Scale. Integration has a finite step budget.
- **Clouds too dark:** density, coverage and scattering-event depth affect actual
  multiple scattering. Lower extinction first; adding more scattering events
  costs time. Turning Cloud Light Attenuation off is an artistic override.
- **Water too expensive:** set Water -> Caustic Paths -> Water Sample Multiplier
  to 1x. Med now uses 2x only for water-covered / underwater pixels. Disable
  Volumetric Clouds separately to isolate its cost.
- **Weak or noisy caustics:** use visible sunlight, Wave Strength above zero,
  Caustic Paths/Guidance On and gain 1.0. Strong absorption/scattering softens
  deep-water focusing. Guide Refinement and Water Sample Multiplier improve
  sampling; they cannot create sunlight behind an actual opaque occluder.

## Upscaling tradeoffs

- **Fine reflection, refraction or thin silhouette is missing:** raise Lighting
  Resolution to 50/67/100%. Detail improves interpolation of available samples;
  it cannot reconstruct an object that was never sampled.
- **Sharpened grain or bright outlines:** lower Sharpening Strength or turn
  Adaptive Sharpening Off. Leave temporal/spatial reconstruction enabled.
- **Detail is slower than Fast:** expected; it gathers sixteen guided samples
  instead of four at every display pixel. Low/Med therefore use Fast by default.
- **Lower resolution did not improve FPS:** geometry capture/build, full-resolution
  raster work, final passes or the CPU may dominate. This pack cannot measure the
  game's bottleneck automatically. Increasing quality budgets can cancel savings.
- **Want the previous Med trace density:** keep Med and set Lighting Resolution
  to 50%. To match its display controls more closely, disable sharpening and
  select Fine bloom. No Hybrid renderer is reintroduced by these controls.
