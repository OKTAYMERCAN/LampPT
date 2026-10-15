# Troubleshooting — 0.7.3

Select the new ZIP, Reset options, choose Medium and set Diagnostic View to Final
Image. A saved settings file from older versions can contain obsolete values.

| Symptom | Check |
| --- | --- |
| Far objects do not occlude/reflection ends | Scene Coverage. Increase capture range and ensure chunks are loaded; Ray Length alone does not help. |
| Whole scene is black in daylight | Confirm version 0.7.3 and reset saved settings. The previous overflow flag blacked out every missed light ray; that policy remains removed. Check Sunlight, Skylight and capture diagnostics. |
| Torch is bright but its surroundings are dark | Emissive Lighting must be On; Small Light Power defaults to 1.0 with calibrated torch radiance. Check capture and resource textures. Real walls still block source connections. Held items are not captured secondary emitters. |
| Complicated silhouettes have dark patches | Traversal Budget still conservatively stops an exhausted ray. Test a higher budget cautiously; it costs tracing time. |
| Missing shadows or light leaks in dense scenes | Triangle Capacity red means geometry was dropped. Increase capacity or reduce capture range. Dropped triangles cannot block light. |
| Large colored speckles, especially during motion | Use 0.7.3, Final Image, Temporal Accumulation On, Spatial Denoiser On and Sparse Sample Reconstruction On. Texture changes no longer reset diffuse history; HRR evidence no longer falsely deletes it. Grazing-floor reprojection now keeps compatible plane history; keep Rough Reflection Stability On and try History Stabilization 0.25. Shared Surface Paths reduces duplicate tracing when surface HRR grids match; Medium uses History 64 and four 3x3 filters. A camera cut or newly revealed surface still needs fresh samples. |
| Fine residual grain in glass or caustics | Keep reconstruction enabled. These sparse paths remain difficult; more history or samples can help at the usual detail/performance cost. |
| Fine reflections look soft | Reduce Specular Filter Strength or turn Half Resolution - Reflections Off, then raise the base PT Render Scale. Native traces about 9.18 times the Medium base pixel count at equal HRR settings; Detail upscaling is another option with extra cost. |
| Thin walls leak light | Keep Ray Origin Offset near 0.005. Check that geometry lies within capture and is terrain rather than an uncaptured entity. |
| Glass is dark / nested glass is incomplete | Clear/stained glass now uses the translucent layer and preserves alpha-zero optical faces. Reload the pack fully. Check the separate Interface Limit budget and capture. Interfaces no longer consume Scattering Events. Missing faces/intersections or an unknown starting glass medium remain limitations. |
| Reflections Off makes metal dark | Expected: a metal primarily reflects. The renderer does not substitute vanilla ambient light. |
| Water is black | Reset the new water roughness/scattering defaults and check capture, Sunlight and Skylight. Medium starts at Interface Limit 4; raise to 8 for deep or nested interfaces at extra cost. Deep unlit water can still be physically dark; no ambient light is injected. |
| Water does not show caustics | Caustic Paths, Caustic Guiding, Refraction and Water Enabled must be On; underwater sunlight also needs sufficient scattering/interface depth. Small caustics remain difficult to sample. |
| Water is noisy | Keep Temporal Accumulation, Spatial Denoiser and Water and Glass Filter enabled. Homogeneous medium flight sampling no longer creates exponentially large blue weights. Optical History Limit controls water/glass averaging separately; lower values preserve wave motion, higher values trade responsiveness for smoothing. Residual rare paths still occur. |
| Frame rate drops | Start Medium at 33% / Fast or Low at 25% / Fast under Performance and Upscaling. Enable the four Half Resolution controls; optionally disable Reflections. Try lower water/cloud budgets before disabling denoising. Capture/BVH cost does not shrink with PT resolution. See PERFORMANCE.md. |
| C5041 mentioning `@stack` in composite1 | Select the exact 0.7.3 ZIP and reload the pack. Runtime BVH stack arrays and four cloned repair call sites were removed. The old 0.6.6 ZIP still contains the problem. If compilation still fails, preserve the full new log because the named resource/stage may differ. |
| Shader fails to load | Provide the exact Iris/Sodium/Minecraft versions and relevant `logs/latest.log` error/stack trace. A screenshot alone cannot establish a loader exception's cause. |

The historical `Index 1 out of bounds for length 1` cannot be diagnosed from its
message alone. This pack uses four literal values in all clear colors and checks
menu references/buffer sizes, but these checks do not replace an Iris runtime log.

The build was tested in Mesa OpenGL, not inside Minecraft. If reproducing a
problem, include the active profile, changed options, Capture/Capacity diagnostics,
resource pack name, and whether the object is terrain or an entity. Do not report
synthetic evidence images as game screenshots.

## Blurred water or glass

Reset this version's options, select Medium and Apply. Under Performance and
Upscaling leave Clear Water and Glass On; under Denoiser and Noise Reduction,
Clear Interface Filter defaults to 0.75. Built-in Glass Roughness should be 0.001;
a higher value or a resource-pack roughness map intentionally spreads refraction.
Smooth interfaces now use secondary-hit edges where available. They no longer
receive unrestricted repeated filtering based only on the flat pane's normal.

Clear optics still use the base Lighting Resolution, not display resolution.
Increasing that setting costs more. Reducing Clear Interface Filter preserves
more fine detail but exposes sampling grain. Increasing it cannot recover missing
geometry or make rare paths noise-free. If water-heavy views become too slow,
turn Clear Water and Glass Off to restore economical coarse tracing.

## Water detail and history

Water Ripple Detail adds shorter wave slopes. For clearer refracted scenery,
disable Half Resolution - Reflections or raise Lighting Resolution at extra cost.
Optical History Limit defaults to 16; high values can smear moving waves. The
shader does not displace the actual flat water mesh. Low-resolution transport
cannot reproduce every fine detail in a reference image.

History Stabilization defaults to 0.25. Set it to 0 if diffuse/rough highlights
soften or leave unwanted trails; ordinary temporal accumulation stays active.

## Moving reflections leave trails

Rough Reflection Stability trades more averaging for slower response in rough
reflections. Disable it if trails are conspicuous. Sharp mirrors and glass use a
shorter moving history automatically. Fresh disocclusions must collect new samples;
raising global history cannot recover missing geometry or motion information.

## After updating to 0.7.3

Select the new ZIP, reset shader options, then choose Medium and Apply. Do not reuse
an older extracted folder with the same name: framebuffer formats and material
records changed. A proper pack reload recreates history. If a remaining issue
appears, include the exact ZIP/version, selected profile, a screenshot and the
relevant Iris error/log excerpt. Compilation tests here do not replace a game run.

## Clouds and water focusing

- **No clouds:** Low intentionally disables them; check Sky and Volumes -> Volumetric Clouds, the Volumetric
  Scattering master switch, nonzero coverage and the layer height. Clouds are
  limited to dimensions with a directional sky; flying above the layer changes
  which directions see it. Vanilla clouds are deliberately disabled.
- **Cloud grain or trails:** keep Spatial Denoiser on and adjust Cloud
  Reconstruction Strength / Cloud History Limit. More history reduces static
  noise but can trail animated density. Wind Speed 0 is useful for comparison.
- **Horizon density bands:** increase Cloud Density Steps and Cloud Shadow Steps,
  or increase Cloud Shape Scale. Integration has a finite step budget.
- **Clouds too dark:** density, coverage and scattering-event depth affect actual
  multiple scattering. Lower extinction first; adding more scattering events
  costs time. Turning Cloud Light Attenuation off is an artistic override.
- **Water too expensive:** set Water -> Caustic Paths -> Water Sample Multiplier
  to 1x. Medium now uses 1x only for water-covered / underwater pixels. Disable
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
  instead of four at every display pixel. Low/Medium therefore use Fast by default.
- **Lower resolution did not improve FPS:** geometry capture/build, full-resolution
  raster work, final passes or the CPU may dominate. This pack cannot measure the
  game's bottleneck automatically. Increasing quality budgets can cancel savings.
- **Want more reflected detail:** disable Half Resolution - Reflections first,
  then raise the base PT Render Scale. This also increases water/glass transmission
  detail and cost. Denoiser strength controls a separate softness/noise tradeoff.

HRR and Medium's smaller sample budgets do not guarantee a frame rate. Actual
Minecraft capture, driver compilation, world complexity and GPU memory can still
be limiting. Report the new ZIP version, preset and modified options if it stalls.
