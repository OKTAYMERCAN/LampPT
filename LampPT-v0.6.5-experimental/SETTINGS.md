# Settings reference — 0.6.5

There is one lighting renderer. Profiles change workload; effect controls operate
on this same path integrator. Every exposed option has an English label. Profile
and About occupy the first row; the remaining categories follow underneath.

| Page | Purpose |
| --- | --- |
| Performance and Upscaling | PT scale, reconstruction quality, adaptive sharpening and spatial pass count |
| Path Tracing Quality | Samples, scattering/interface events, ray length, emitter samples/candidates |
| Scene Capture | Terrain radius, triangle storage, per-ray node budget, bias, cutout threshold |
| Lighting | Diffuse bounce, direct light, shadows, source colors and emission |
| Reflections | Reflective BSDF, gain, default roughness, refracted vs straight transmission |
| Water / Glass | Dielectric material parameters and medium absorption/scattering |
| Caustic Paths | Opaque -> dielectric path contribution and underwater sampling guidance |
| Noise Reduction | Temporal accumulation, spatial filtering, outlier/radiance limits |
| Materials | First-hit normal/POM and specular resource textures |
| Sky and Volumes | Analytic environment source and stochastic participating media |
| Volumetric Clouds | 3D density, placement, wind, scattering, shadows, distance and integration quality |
| Display and Lens | Tone/color response and optional lens bloom |
| Debug | Component, history, coverage and capacity views |
| About | Editable version, owner, contact, license, credits and build labels |

## Performance and Upscaling

| Control | Default (Med) | Behavior |
| --- | --- | --- |
| Lighting Resolution | 40% per axis | Seven scales from 33% to 100%; only transport/history/filter grids shrink |
| Upscale Filter | Fast (4 taps) | Guided bilinear reconstruction; Detail uses 16 nonuniform cubic taps and costs more |
| Adaptive Sharpening | On | Bounded HDR detail contrast with a remaining-noise guard; Off skips the pass |
| Sharpening Strength | 0.25 | Higher values can emphasize grain; 0 gives no intentional sharpening |
| Spatial Filter Passes | Two | One saves a pass but leaves more grain, especially in water/clouds |

Temporal Accumulation and Spatial Reconstruction retain their separate switches
under Noise Reduction. Temporal Off still writes current guide data needed by
later passes. Spatial Reconstruction Off skips both spatial passes. Diagnostic
views skip sharpening. At 100% lighting resolution the upscaler is bypassed;
Adaptive Sharpening remains independently available.

Low starts at 33%, Fast, sharpening Off. Med uses 40%, Fast, sharpening On.
High uses 50%, Detail; Ultra uses 100% with no upscaling. All four start with
two spatial passes. **Display and Lens -> Bloom -> Bloom Quality** chooses
Fast (9 taps) or Fine (25 taps); Fine is the Ultra default.

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
  Low and Med start at zero air density; water uses its separate coefficients.
- **Bounce/Reflection/Caustic Gain:** 1.0 preserves their transport weighting.
  Higher values are artistic and can accumulate with path depth.
- **Concrete Powder Emission:** all mapped concrete powder colors emit their
  material RGB. It is Off by default and can be used to test color mixing.
- **Small Light Power:** scales the calibrated surface radiance of torches,
  small mapped sources and end rods. It affects both sampled direct light and
  visible/reflected emission; it does not brighten glowstone or add ambient light.
- **Scattering Events:** limits opaque and volume interactions. **Transmission
  Events** separately limits dielectric interfaces, including their reflections.
  Med uses 4 scattering events and 8 interface events. A final bounded query can
  reach a source/environment after the last interface. More events cost time.
- **Emitter Candidates:** resamples possible triangle/light positions before
  each visibility query. Med uses 4 candidates and 1 emitter sample. Increasing
  candidates improves source selection without multiplying shadow rays, but still
  costs material/BVH sampling work. Emitter Samples multiplies visibility queries.

## Noise and distant detail

Start with Med, Temporal Accumulation On, Spatial Reconstruction On, History 32,
Diffuse Filter Strength 0.75, Specular Filter Strength 0.50 and Water and Glass Filter 0.85. The isolated
sparkle filter is On; the absolute radiance clamp is 0 (disabled).

The sparkle filter caps isolated opaque-surface samples against compatible local
medians. It is deliberately biased and exempts sharp mirrors and glass. The raw
path diagnostic bypasses this filter. Material textures and visible emissive
artwork are restored separately at full resolution, not blurred with lighting.
Transmission filtering also applies to camera-water scattering. It has wider
second-pass spacing and keeps its strength while measured variance is high.
Reduce it for sharper refracted detail at the cost of more visible noise.
History clipping uses historical variance so rare light is not repeatedly erased.

Increasing Paths Per Pixel reduces sampling noise; increasing Emitter Samples
helps many-source direct lighting; Emitter Candidates improves each estimate's
selection. Increasing History Frames helps stationary
views but cannot retain invalid history after camera motion or edits. 100%
Lighting Resolution helps thin silhouettes and reflected detail at four times
the tracing pixel count of 50%, or 6.25 times the new Med 40% grid. Neither filtering nor higher resolution restores terrain
that was never captured.

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

Water starts at Roughness 0.005 and Scattering 0.04. Roughness changes optical
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
  underwater pixels, only while Water and Caustics are enabled. Med uses 2x.
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
| Cloud Reconstruction Strength | Spatial filter strength for primary rays through clouds; requires Spatial Reconstruction |
| Cloud History Limit | Cap for temporal history when a primary ray crosses the layer |

Med starts with coverage 0.55, extinction 0.08, Y=192, thickness 48, shape scale
128, 1 block/second wind, phase g=0.60 and scattering albedo 0.98. It uses 48
path-density steps, 24 shadow steps, 2048-block distance and 16-frame cloud
history. These values are starting settings, not a measured RTX performance tier.

Clouds use the same Scattering Events budget as the rest of PT. More events can
brighten dense interiors by capturing additional physical scattering, at extra
cost. There is no ambient cloud fill term. Increase density steps for small
features/horizon banding; decrease coverage/density or turn clouds Off if their
workload is excessive. Raising density without enough scattering events can
make the cloud interior dark. Reflection/refraction toggles govern those BSDF
paths; the cloud medium is automatically encountered on enabled paths.
