# LampPT
This project Path Traced Global illimunation shaderpack for minecraft (Iris). Prof of Concept and Early alpha stage.

<img width="2560" height="1362" alt="Screenshot_20260926_094316" src="https://github.com/user-attachments/assets/6acc4091-1c87-4548-97d4-f08a4100de8d" />

<img width="2560" height="1362" alt="Screenshot_20260926_094438" src="https://github.com/user-attachments/assets/8dcb85a5-f06f-461a-b986-11a6fb4a5018" />

<img width="2560" height="1363" alt="Screenshot_20260926_094101" src="https://github.com/user-attachments/assets/95677acb-a276-4ff5-bc9a-25bc33e61a38" />

---
Contains AI-generated code, assets and text. Made with AI.

# LampPT 0.6.5 experimental

Minecraft Java terrain lighting for Iris + Sodium, using **one world-space path
integrator**. There is no Hybrid renderer or renderer selection. Diffuse GI,
reflections, dielectric refraction, area-light shadows, caustic paths and medium
scattering are evaluated by traced light paths. They have individual controls.
The interface, documentation and source comments are in English.

This is **path-traced lighting with raster first visibility**, not a complete
ray-traced replacement for the Minecraft engine. Terrain capture is finite;
secondary entities and some material detail are not represented. No claim of
unlimited world coverage, zero noise or a measured RTX frame rate is made.

## Install

1. Put `LampPT-v0.6.5-experimental.zip` in `.minecraft/shaderpacks/` as a ZIP.
2. Select that exact pack in Iris. Reset its options, select **Med**, then Apply.
3. Leave **Diagnostic View = Final Image**. No PT mode switch is needed.
4. Allow several stationary frames for temporal accumulation.

Do not import overrides from earlier versions: the render paths and menus changed.
Normal maps, POM and concrete powder emission are Off in all four profiles.
About fields are editable; see `ABOUT_EDITING.md`.

## What changed in 0.6.5

- Added **Performance and Upscaling** with seven PT resolution scales: 33%, 40%,
  50%, 59%, 67%, 77% and 100% per axis. Material textures and first visibility
  stay at display resolution. Med now traces at 40% per axis: 36% fewer PT
  pixels than the previous 50% Med grid, before integer rounding.
- Added custom surface-guided upscaling: **Fast** uses four taps and is the
  Low/Med default; **Detail** uses sixteen bounded cubic taps. It uses the actual
  snapped sample positions at fractional scales. Detail improves reconstruction
  of smooth sampled fields, but costs more and cannot recover unsampled objects.
- Added adjustable noise-aware HDR sharpening. It reduces its response to
  remaining path noise and clamps against nearby values to limit ringing.
  Off removes the entire sharpening pass. It is Off in Low and On in Med.
- Cached transport-sample normals, depth and material keys after the temporal
  pass. Spatial reconstruction and upscaling reuse this compact data instead
  of decoding all full-resolution material layers at every tap.
- Added one/two-pass spatial filtering. Spatial Reconstruction Off now removes
  both passes from scheduling; the required history/guide update remains active.
- Added Fast/Fine bloom quality, using 9/25 scene taps. Low/Med/High use Fast.
  Bloom is a display effect and does not alter path-traced world illumination.

This is **LampPT's own PT upscaler**, not AMD FSR, DLSS, temporal super-resolution
or frame generation. The path integrator is unchanged. Lower resolution trades
fine reflected/refracted lighting detail for less work; it does not reduce BVH
capture cost or guarantee a particular game frame rate. See `PERFORMANCE.md` for
controls, measured software-renderer costs and their limits.

## Retained cloud and caustic features from 0.6.4

- Refracted-sun caustic guidance now solves for the wave normal at the actual
  water interface with a bounded, damped Newton proposal. The previous three
  fixed-point iterations could aim away from the sun in deeper/wavier water.
  A local angular Jacobian adapts the elliptical proposal to wave focusing,
  with a matching solid-angle PDF. Only two BVH queries prepare the proposal.
  Actual Snell/Fresnel paths,
  occlusion and the matching mixture PDF determine all caustic energy.
- Water pixels have a separate 1x / 2x / 4x camera-path multiplier. Med uses 2x;
  dry-land paths keep their existing sample count. Caustic gain remains 1.0.
- Added world-space volumetric clouds to the same path integrator. Procedural
  3D density produces sampled scattering events and attenuates light connections.
  Clouds participate in camera, reflection and transmission paths, sun/sky
  illumination, self-shadowing and terrain shadows. No additive cloud glow or
  painted sky overlay is used. Vanilla cloud geometry is disabled.
- Cloud scattering uses a normalized Henyey-Greenstein phase with matching
  sampling/PDF. Density integration is bounded midpoint quadrature; it is a
  numerical approximation whose accuracy depends on the selected step budgets.
- Added English controls for cloud coverage, density, base/thickness, scale,
  wind, forward scattering, scattering albedo, distance, density/shadow steps
  and spatial reconstruction / temporal history. Cloud history has a separate cap for moving density.
- Primary emitters viewed through clouds use stochastic medium visibility
  instead of bypassing it in the full-resolution emission restore.

The four profiles, 123 English controls, editable About page and PT-only lighting
remain. Profile and About occupy the first menu row. Normal maps, POM and
concrete powder emission remain Off in all profiles. The material, fluid-boundary,
source and indirect BVH-dispatch fixes from 0.6.3 are retained.

## Quality profiles

| Profile | Capture radius | Triangle capacity | Lighting resolution per axis | Paths/pixel | Scattering events | Emitter samples |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Low | 64 blocks | 262,144 | 33% | 1 | 2 | 1 |
| Med | 128 blocks | 1,048,576 | 40% | 1 | 4 | 1 |
| High | 192 blocks | 1,572,864 | 50% | 2 | 6 | 2 |
| Ultra | 256 blocks | 1,572,864 | 100% | 4 | 8 | 4 |

Water sample multipliers are **1 / 2 / 2 / 4**. Cloud density steps are
**24 / 48 / 64 / 96**, with **8 / 24 / 32 / 48** steps per shadow connection.
Cloud transport distances are **1024 / 2048 / 2048 / 4096** blocks. These are
medium distances, not additional terrain capture. Clouds are enabled in all
profiles and can be disabled independently under Sky and Volumes.

Transmission event budgets are 4 / 8 / 12 / 12. Emitter candidates per estimate
are 2 / 4 / 4 / 8. Interfaces do not consume the scattering-event budget; both
budgets remain bounded. Increasing either increases possible work per path.

Med is the starting configuration for the requested RTX 3060/4060 class, **not a
performance guarantee**. 100% resolution traces 6.25 times as many pixels as
40%, or four times as many as 50%, before dimension rounding.
The scene buffers use approximately 46 / 184 / 276 / 276 MiB respectively, in
addition to framebuffers, textures and the game's allocations. Dense vegetation
and resource-pack geometry can exceed the capacity even at a short range.

Use **Scene Capture -> Scene Capture Range** to extend geometry coverage, and
**Triangle Capacity** to hold more triangles. Ray Length alone does not capture
more terrain or load chunks. Do not increase every budget together if the game is
already slow. Low reduces coverage and path depth, including paths through glass.
This pack uses GLSL compute/SSBOs, not hardware RTX acceleration or DLSS.

## Controls

- **Performance and Upscaling:** internal PT scale, Fast/Detail reconstruction,
  adaptive sharpening and one/two spatial filter passes.
- **Lighting:** diffuse GI, bounce gain, direct shadows, sunlight/moonlight,
  environment, emission, source RGB colors and opt-in concrete powder emitters.
- **Reflections:** reflective BSDF lobe, reflection gain, roughness and refraction.
- **Water / Glass:** optical boundaries, IOR, roughness, waves, absorption, color
  and water scattering. Caustic Paths and sampling guidance are separately switchable.
- **Sky and Volumes -> Volumetric Clouds:** cloud medium, shadows, density, shape,
  placement, wind, phase, quality and motion-history controls.
- **Noise Reduction:** temporal history, spatial reconstruction, diffuse/specular
  and transmission filter strengths, isolated sparkle suppression and optional
  radiance clamp.
- **Materials:** optional resource-pack normals, POM and PBR maps.
- **Display and Lens:** exposure, tone mapping, color response and optional bloom.
  These are display operations; bloom does not illuminate the world.

At unit gains and with optical controls enabled, effects share the same light
transport. Disabling a physical lobe or changing its gain is an artistic override;
for example, a metal without reflections has little remaining light response.
See `SETTINGS.md` for semantics and useful diagnostics.

## Actual limits

- First visibility and guides are rasterized. The PT integrator supplies all
  terrain illumination and traces subsequent paths against captured terrain.
  Special unlit overlays retain their raster presentation.
- Capture consists of shadow-pass terrain inside the selected radius and the
  game's loaded/rendered chunks. It is not the entire Minecraft world. Outside
  capture, visibility is unknown. Rays test available terrain and use an analytic
  environment on a complete traversal miss. Uncaptured occluders cannot cast
  shadows; increasing capture range does not guarantee sufficient storage.
- Mobs, the hand and block entities are not captured as secondary geometry.
  Raster first-hit entities can receive PT light but cannot provide complete
  reflected visibility or secondary shadows. Held translucent items use an
  analytic thin-sheet approximation, not traced internal item geometry.
- Secondary albedo uses actual atlas UVs with alpha cutouts. Roughness/F0/emission
  for resource materials are stored per triangle from its texture midpoint;
  mapped source artwork is masked at the actual sampled UV. Normal mapping/POM are
  first-hit inputs. POM does not displace the traced mesh. Metals use an RGB
  albedo-tinted approximation, not measured spectral complex indices.
- Water waves perturb optical normals on the captured mesh. Caustics come from
  traced refraction, with directional sampling guidance underwater; there is no
  general photon map or general specular manifold solver. The water-only Newton
  solve improves an importance proposal; it is not a new light contribution.
  Small sources and nested
  glass can remain noisy. Missing/intersecting interfaces are not fully handled.
- The sky radiance source is analytic. Air/water media are homogeneous; clouds
  are procedural heterogeneous media in one bounded layer. Cloud shape is an
  advected density model, not a weather/fluid simulation. Density quadrature,
  finite cloud distance and path-event budgets approximate transport. Spectral
  dispersion, diffraction and fluid surface displacement are absent.
- Clouds inherit the shared scattering-event budget. Low can look darker because
  it captures fewer multiple-scattering paths. Dense clouds and rare caustics
  still need accumulation; no noise-free moving image or frame-rate guarantee
  is made. Cloud Shadow Off deliberately removes direct-connection extinction.
- Low-resolution lighting can miss thin silhouettes or small reflected features.
  The upscaler keeps full-resolution primary diffuse textures; it cannot create
  missing light samples. Raise Lighting Resolution for those cases.
- Event/ray limits, incomplete capture and reconstruction introduce bias. The
  reactive temporal filter and default outlier filter are also biased; disable it and the radiance clamp for
  raw estimator inspection. A low-sample moving image cannot be noise-free.
- Every traversal and build loop is bounded. That prevents unbounded loops, but
  does not guarantee a frame-time ceiling or prevent GPU overload at high settings.

## Compatibility and validation

The observed user target was Iris 1.11.4 / Minecraft 26.2 with Sodium. This build
requires OpenGL 4.3, compute shaders, SSBOs and Iris block-emission attributes.
It is an Iris-targeted build; OptiFine and native macOS OpenGL are not supported.
No universal loader/GPU compatibility is claimed.

## Is this full path tracing? Can it use hardware RT?

The lighting integrator traces world-space paths for GI, reflective and refractive
transport, source visibility, caustic paths and medium scattering. It does not use
screen-space GI or a Hybrid lighting fallback. Calling the whole Minecraft
renderer "100% path traced" would be inaccurate: first visibility is rasterized,
capture is finite, wave/sky/material models are approximations, and reconstruction,
tone mapping and bloom are separate operations. The limits above remain applicable.

Traversal currently runs in GLSL on the GPU's general shader cores. "Software
ray tracing" here does not mean the game traces rays on its CPU. Hardware RT is
possible in a different rendering backend, but cannot be enabled by changing a
shaderpack option. The loader/mod would need an RT API, acceleration structures
and pipeline integration, plus compatible GPU/drivers. For example, Vulkan's
`VK_KHR_ray_tracing_pipeline` and `VK_KHR_acceleration_structure` expose those
facilities. This release does not add a hardware backend or claim RT-core use.
See the [Khronos ray-tracing example](https://docs.vulkan.org/samples/latest/samples/extensions/ray_tracing_basic/README.html).

The included GLSL was compiled and rendered on Mesa software OpenGL 4.5.
**Minecraft, Iris's shader transformer and NVIDIA hardware were unavailable.**
No in-game FPS, driver stability or user-scene appearance has been measured.
See `TEST_RESULTS.md` for reproducible checks and limits; images in the tests
folder are synthetic shader renders, not Minecraft screenshots.

Source map: `SOURCE_GUIDE.md`. Rebuild: `python3 build.py /path/LampPT.zip`.
License: MIT, retained from the previous release.

