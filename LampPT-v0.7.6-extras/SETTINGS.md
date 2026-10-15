# Settings reference — 0.7.3

There is one lighting renderer. Profiles change workload; effect controls operate
on this same path integrator. Every exposed option has an English label and tooltip. Profile
and About occupy the first row; the remaining categories follow underneath.

| Page | Purpose |
| --- | --- |
| Performance and Upscaling | Shared surface paths, PT scale, four HRR switches, reflections and sharpening |
| Path Tracing Quality | Samples, scattering/interface events, ray length, emitter samples/candidates |
| Scene Capture | Terrain radius, triangle storage, per-ray node budget, bias, cutout threshold |
| Lighting | Diffuse bounce, direct light, shadows, source colors and emission |
| Reflections | Reflection gain, default roughness, refracted vs straight transmission |
| Water / Glass | Dielectric material parameters and medium absorption/scattering |
| Caustic Paths | Opaque -> dielectric path contribution and underwater sampling guidance |
| Denoiser and Noise Reduction | Temporal accumulation, spatial filtering, outlier/radiance limits |
| Materials | First-hit normal/POM and specular resource textures |
| Sky and Volumes | Analytic environment source and stochastic participating media |
| Volumetric Clouds | 3D density, placement, wind, scattering, shadows, distance and integration quality |
| Display and Lens | Tone/color response and optional lens bloom |
| Debug | Component, history, coverage and capacity views |
| About | Version/changelog, owner, contact, license, credits and system requirements |

## Performance and Upscaling

| Control | Default (Medium) | Behavior |
| --- | --- | --- |
| Clear Water and Glass | On | Trace smooth dielectric pixels at the base grid, skipping their coarse HRR surface paths; adds optical cost and secondary-hit edge guidance |
| Shared Surface Paths | On | Uses one correctly weighted surface path when Shadows/GI/Reflections HRR grids match; otherwise uses separate paths |
| Lighting Resolution | 33% per axis | Eight scales from 25% to 100%; only transport/history/filter grids shrink |
| Upscale Filter | Fast (4 taps) | Guided bilinear reconstruction; Detail uses 16 nonuniform cubic taps and costs more |
| Adaptive Sharpening | Off | Bounded HDR detail contrast with a remaining-noise guard; Off skips the pass |
| Sharpening Strength | 0.25 | Higher values can emphasize grain; 0 gives no intentional sharpening |
| Four Half Resolution switches | On | Each component traces at half the base scale in both axes; independent controls |
| Reflections | On | Off removes opaque reflection transport, while retaining transmitted paths |

**Denoiser and Noise Reduction** contains Temporal Accumulation, Spatial
Denoiser, Spatial Filter Passes, Denoiser Kernel and Rough Reflection Stability.
Medium, High and Ultra use four Small 3x3 passes with 64-frame history. Low uses
three Small passes with 32-frame history. Temporal Off still writes guides; Denoiser Off skips every spatial pass.
Sharpening is Off in every profile and bypassed in diagnostics.

Low/Medium/High/Ultra use base grids 25/33/40/50%, with all HRR switches On.
Individual component scales are 12.5/16.5/20/25% per display axis. HRR Shadows
affects primary diffuse direct light; shadows inside GI/reflections follow that
component's scale. HRR Clouds controls sky and primary medium scattering.
Reflections HRR also covers transmission. Clear Water and Glass overrides its
coarse grid for smooth dielectric pixels only; turning Clear Water and Glass Off
restores the coarse optical grid. Every HRR switch remains editable.

Low disables Reflections and Volumetric Clouds. Choosing another profile
explicitly restores them. Bloom Quality is Fast in all profiles. Profile budgets
and capture-memory tradeoffs are tabulated in PERFORMANCE.md.

These are original spatial filters, not AMD FSR or frame generation. Primary
material textures remain full resolution, but fine shadows/reflections/refractions
have only the selected number of light samples. `PERFORMANCE.md` explains the
tradeoffs and workload ratios. All illumination still comes from the same PT
integrator, even with Fast reconstruction selected.

## Transport control semantics

- **Diffuse Global Illumination Off:** stop diffuse continuation. Direct diffuse
  illumination remains, with the correct direct-light sampling weight.
- **Reflections Off:** disable opaque and dielectric reflective lobes. Reflective
  energy is not replaced by artificial ambient light; metals can become dark.
- **Refraction Off:** transmission travels straight instead of bending; absorption
  remains unless the material's optical control is disabled as well.
- **Glass Optics / Water Enabled Off:** interfaces transmit neutrally. Disabling
  water also removes camera-water extinction and water scattering.
- **Caustic Paths Off:** suppress paths passing through a dielectric after an
  opaque event. Primary views through glass/water remain. This classification
  includes reflected dielectric paths as well as transmitted focusing paths.
- **Direct Light Shadows Off:** direct source connections ignore occlusion.
  Reflections and continuation still intersect scene geometry.
- **Volumetrics Off:** stop volume scattering events and disable the entire cloud
  medium. Water/glass absorption still follows
  material density. Air density controls both air absorption and scattering.
  All profiles start at zero air density; water uses its separate coefficients.
- **Bounce/Reflection/Caustic Gain:** 1.0 preserves their transport weighting.
  Higher values are artistic and can accumulate with path depth.
- **Concrete Powder Emission:** all mapped concrete powder colors emit their
  material RGB. It is Off by default and can be used to test color mixing.
- **Small Light Power:** scales the calibrated surface radiance of torches,
  small mapped sources and end rods. It affects both sampled direct light and
  visible/reflected emission; it does not brighten glowstone or add ambient light.
- **Scattering Events:** limits opaque and volume interactions. **Transmission
  Events** separately limits dielectric interfaces, including their reflections.
  Medium uses 2 scattering events and 4 interface events. A final bounded query can
  reach a source/environment after the last interface. More events cost time.
- **Emitter Candidates:** resamples possible triangle/light positions before
  each visibility query. Medium uses 2 candidates and 1 emitter sample. Increasing
  candidates improves source selection without multiplying shadow rays, but still
  costs material/BVH sampling work. Emitter Samples multiplies visibility queries.

## Noise and distant detail

Start with Medium, Temporal Accumulation On, Spatial Denoiser On, History 64,
Diffuse Filter Strength 1.0, Specular Filter Strength 1.0 and Water and Glass
Filter 0.85 and Rough Reflection Stability On. Sparse Sample Reconstruction is On; the absolute radiance clamp is
0 (disabled). These settings are separate from the four HRR controls.

Sparse Sample Reconstruction reuses the temporal statistics over compatible
geometry to estimate spatial-filter variance. No second 3x3 gather is needed. This prevents rare bright HRR clusters being
misidentified as stable lighting edges. It replaces the old median sparkle cap;
valid samples are no longer truncated before temporal accumulation. The raw-path
diagnostic bypasses reconstruction. Full-resolution primary textures and visible
emissive artwork remain outside filtering.

History reuses diffuse irradiance across changes in primary texture color.
Grazing surfaces use a point-to-plane test rather than equal-depth validation,
so camera motion across a floor does not erase compatible history. Infinite sky
uses rotational reprojection without camera parallax and a distinct validity key.

**Rough Reflection Stability** (On) retains up to 32 compatible frames for rough
reflections during motion instead of abruptly dropping to eight. The cap changes
smoothly with speed and roughness. Sharp mirrors/glass retain short moving
history. This reduces sparkle without extra rays, but changing reflected content
can trail: turn it Off if that compromise is unsuitable. There is no secondary
hit-point motion-vector reprojection.

Metallic/glass tint remains part of history validation, as do material, depth
and physical normal. HRR statistics use separated sample footprints so repeated
pixels do not falsely erase valid GI. Removed-light detection remains reactive;
very rare paths and changing reflected content can still trail. History
Stabilization now feeds a bounded fraction of the first compact filter into
diffuse/rough opaque history; later wide filters never do. Smooth glass/water
exclude optical feedback. With Clear Water and Glass On, secondary-hit color,
normal and distance guide filtering; without a usable guide they receive only
one compact filter. This avoids repeatedly blurring unrelated scenery on a pane.

Increasing Paths Per Pixel reduces sampling noise; increasing Emitter Samples
helps many-source direct lighting; Emitter Candidates improves each estimate's
selection. Increasing History Frames helps stationary
views but cannot retain invalid history after camera motion or edits. 100%
Lighting Resolution helps thin silhouettes and reflected detail at four times
the tracing pixel count of 50%, or about 9.18 times the Medium 33% base grid, at equal HRR settings. Neither filtering nor higher resolution restores terrain
that was never captured.

## New temporal and water controls

| Control | Location / default | Purpose |
| --- | --- | --- |
| Clear Interface Filter | Denoiser and Noise Reduction / 0.75 | Controls smooth-optics filtering. Secondary-hit guides protect scenery edges; missing guides use one compact pass. Lower values expose grain, higher values can soften detail. |
| History Stabilization | Denoiser and Noise Reduction / 0.25 | Reuse a bounded fraction of the first compact filtered diffuse/rough opaque estimate in the next frame. Requires Temporal Accumulation and Spatial Denoiser. 0 disables only this feedback; higher values can soften detail or trail. |
| Optical History Limit | Water / 16 | Maximum averaging weight for water and glass optical paths. Changing wave normals shorten it further. Lower values respond faster; higher values can reduce stationary grain but smear animation. |
| Water Ripple Detail | Water / 0.35 | Strength of three shorter ripple slopes on top of the broad waves; 0 retains broad waves, Water Waves Off disables both. Shared by traced interfaces and caustic guidance. |

The base history still uses camera reprojection and physical-surface validation.
Normal-map detail is not used to reject the physical plane. Optical normal
changes adjust the water/glass averaging weight separately. Filtering is biased
reconstruction; it cannot recover fine scenery absent from the low-resolution
optical sample grid. The Reflections HRR switch controls transmission too, subject to the clear-optics
base-grid override described above.

## Capture diagnostics

**Scene Coverage:** green is inside the capture radius, yellow the outer 10%,
magenta beyond it; red indicates triangle overflow. This is a coverage indicator,
not proof that Minecraft submitted every possible object in the region.

**Triangle Capacity:** blue horizontal fill shows stored triangles / capacity.
Red means some triangles could not be stored. Increase capacity or reduce capture
range. Overflow no longer blocks every light ray, but missing occluders can leak
light. Even with storage available, the scene cannot include unloaded chunks.

**Traversal Budget** is the maximum BVH node visits per ray. Exhaustion stops
conservatively and can darken complex regions instead of turning them into sky.
Increasing the value costs GPU time. **Ray Origin Offset** should stay near 0.005;
large offsets can jump across thin geometry and cause light leaks.

## Physical inputs vs display

Glass Roughness starts at 0.001; increase it deliberately for frosted glass.
Resource specular maps can override the built-in roughness.

Water starts at Roughness 0.001, Absorption 0.08, Scattering 0.02 and Blue 0.75. Roughness changes optical
microfacet normals; Wave Strength changes the larger wave slopes. Scattering is
the probability of a medium interaction per unit distance, not a brightness
control. Raising it makes short low-budget paths harder to resolve. Absorption
still darkens deep water physically, even with volumetric scattering disabled.

Caustics arise from refracted paths, not from an animated caustic texture. Wave
settings change the optical normal that those paths meet. Normals/POM require
appropriate resource maps and affect first visibility; the secondary mesh is
not displaced. Sun and sky are analytic radiance sources, and bloom/tone mapping
are display effects. These components are not claimed to be spectral simulations.

## 0.6.3 behavior notes

- Glass controls also govern ordinary ice, honey, slime, tinted glass and
  unclassified translucent terrain. Material IORs are 1.31 / 1.47 / 1.40 for
  ice / honey / slime; generic and tinted glass use Glass IOR. Tinted glass
  multiplies the color-derived extinction by six. Glass Tint scales that effect.
- Temporal History is a maximum averaging weight, not a strict sliding window.
  Changed BSDF/color resets history. Sustained missing illumination reacts faster
  than the old exponential tail, while isolated black samples retain rare light.
- Caustic Guidance is only active for a reachable water exit and enabled nonzero
  directional illumination. It is a sampling option, not an extra caustic overlay.
- Triangle Capacity still allocates memory up front. Adaptive dispatch reduces
  unused build invocations, not allocation, capture cost or the number of paths.

## Water focusing controls

Under **Water -> Caustic Paths**:

- **Caustic Paths** enables opaque-to-dielectric light paths; **Caustic Gain**
  should stay 1.0 for the transport model's energy weighting.
- **Caustic Guidance** enables an underwater refracted-sun sampling proposal.
  **Caustic Guide Refinement** changes the bounded numerical solve (2/4/6/8).
  It changes variance, not the physical light source.
- **Water Sample Multiplier** traces 1x/2x/4x camera paths for water-covered or
  underwater pixels, only while Water and Caustics are enabled. Medium uses 1x.
  Try 1x first if water is too expensive; raise it to reduce sampling grain.
- Wave Strength/Scale/Speed, Water IOR/Roughness and the sun angular size change
  the actual refractive focusing. Water absorption/scattering can soften and
  attenuate deep-water caustics. Focusing is not an extra animated texture.

## Volumetric cloud controls

Under **Sky and Volumes -> Volumetric Clouds**:

| Control | Meaning |
| --- | --- |
| Volumetric Clouds | Entire cloud medium On/Off; also requires Volumetric Scattering |
| Cloud Light Attenuation | Direct-light extinction and self-shadowing; Off is an artistic override |
| Cloud Coverage | Threshold of the world-space density field; zero clears the sky |
| Cloud Extinction | Maximum extinction per block, not an emissive brightness gain |
| Cloud Base Height / Layer Thickness | Absolute Y position and vertical extent in blocks |
| Cloud Shape Scale | Horizontal size of density features in blocks |
| Cloud Wind Speed / Direction | Density advection; speed 0 freezes clouds |
| Cloud Forward Scattering | HG asymmetry, from isotropic 0 to forward-peaked 0.85 |
| Cloud Scattering Albedo | Scattering fraction of extinction; 1 has no absorption |
| Cloud Ray Distance | Maximum medium distance, independent of captured terrain |
| Cloud Density Steps / Shadow Steps | Bounded quadrature quality for paths / direct connections |
| Cloud Reconstruction Strength | Spatial filter strength for primary rays through clouds; requires Spatial Denoiser |
| Cloud History Limit | Cap for temporal history when a primary ray crosses the layer |

Medium starts with coverage 0.55, extinction 0.08, Y=192, thickness 48, shape scale
128, 1 block/second wind, phase g=0.60 and scattering albedo 0.98. It uses 16
path-density steps, 8 shadow steps, 1024-block distance and 16-frame cloud
history. These values are starting settings, not a measured RTX performance tier.

Clouds use the same Scattering Events budget as the rest of PT. More events can
brighten dense interiors by capturing additional physical scattering, at extra
cost. There is no ambient cloud fill term. Increase density steps for small
features/horizon banding; decrease coverage/density or turn clouds Off if their
workload is excessive. Raising density without enough scattering events can
make the cloud interior dark. Reflection/refraction toggles govern those BSDF
paths; the cloud medium is automatically encountered on enabled paths.

## Additional Lighting controls

| Setting | Default | Behavior |
| --- | --- | --- |
| Held Item Lighting | On | Main/off-hand PT point emitters; terrain visibility and inverse-square falloff |
| Held Light Strength | 1.0 | Scales the hand emitters only |
| Lamp Strength | 3.0 | Lit redstone lamps and copper bulbs |
| Candle Strength | 2.0 | Lit candle/candle-cake small-area emission, independent of wax color |
| Natural and Unmapped Light Strength | 2.0 | Natural source groups and native-emission fallback |

Placed lamps/candles/bulbs use lit-state mappings. Hand candles and switchable lamps are treated as
ignited while held. Unknown held block items use Iris native light strength and
a neutral color. Empty hands and nonemissive, unmapped items produce no light.
Hand positions approximate the grip and do not track item animations, third-person
player geometry or exact per-item shapes. Glass blocks still block straight
point-light visibility; refracted hand-light caustics need a separate connector.
