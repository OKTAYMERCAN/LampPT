# Verification — LampPT 0.6.5 experimental

Production GLSL was compiled and executed through EGL on **Mesa llvmpipe /
OpenGL 4.5 compatibility**. All meshes, cameras and scenes are synthetic.
Minecraft, Iris's shader transformer, Sodium's live frame flow and NVIDIA
hardware were unavailable. No in-game FPS, GPU-driver stability or appearance
of the user's actual world is established by these tests.

## Naming update — 2026-09-27

The LampPT naming update passed the existing Med metadata/link check: 74 shader
programs linked. All 124 shader source files differ from the previous package
only by the consistent brand rename. No old brand remains in the packaged
filenames or contents. The full feature measurements below are retained from
the same 0.6.5 implementation, rather than newly measured game performance.

## Current release checks

| Area | Result |
| --- | --- |
| Compilation / menu | 555 linked program variants; 123 exposed English options; four profiles; Med matches defaults |
| Optional defaults | Normals, POM and concrete powder emission Off; Profile and About first |
| Target sizes | All seven scales select matching transport MRT dimensions; raster inputs stay full resolution |
| Pass scheduling | Denoise Off skips both spatial passes; one-pass mode disables the second; sharpening Off and diagnostics disable composite6 |
| Texture reconstruction | Constant-light maximum error 0.0002522 at every scale, including odd 127x75 display size |
| Occlusion edge fixture | Interior error below 0.0002522 on both sides of a depth discontinuity with nearby samples |
| Smooth-field upscaling, 40% | Fast RMSE 0.00083364; Detail 0.00016932 against a known analytic field |
| Fractional-grid interpolation | Detail improves the smooth-field fixture at every reduced scale; Native bypasses both filters |
| Adaptive sharpening | Changes the known sharp feature by up to 0.005127 while remaining within the fixture signal bounds |
| Noise guard | High supplied variance reduces that change to 0.0002441 |
| Full pipeline | Torch room, water above/below and cloud/ground/reflector scenes produce finite final images at new Med defaults |
| Visibility in water fixture | More than 99.9% of the selected below-water fixture region exceeds 0.05 in a display channel |
| History | Stationary drift zero; disocclusion resets age to 1; changed material resets history |
| Noisy-field reconstruction | Raw RMSE 0.45076 -> filtered 0.04858; full-resolution texture error 0.0006704 |

These are fixture-specific error checks, not perceptual-quality or noise-free
claims. The edge test has nearby samples on both surfaces. Unsampled thin
objects cannot be recovered. The actual low-resolution water images retain
visible grain/softness; higher lighting resolution or more paths can improve
them at additional cost. Sharpening is not a substitute for missing samples.

The source comparison against 0.6.4 changes reconstruction, scheduling,
resolution defaults and display processing. Integrator, BSDF, scene traversal,
source sampling, water caustic guidance and cloud-medium files are unchanged.

## Timing scope and evidence

`PERFORMANCE.md` reports actual GL_TIME_ELAPSED medians with full conditions.
The run measures composite draws only, excluding geometry capture/BVH,
allocation, readback, compilation, final bloom and Minecraft. The shared CPU
has variable scheduling/throughput, including substantial differences in the
unchanged integrator. Neither the faster runs nor the slower runs establish a
reliable RTX/game speedup. All measurements, including the initial variable
multi-thread cases, remain in the evidence folder.

The deterministic workload changes are 36% fewer transport pixels for new Med
40% versus old Med 50%, fewer full-resolution layer reads per filter guide, an
optional one-pass denoiser, removal of disabled post-passes and a 9-tap rather
than 25-tap Fast bloom kernel. Extra guide storage and optional Detail/sharpening
cost work themselves. PT scale does not change BVH capture/build cost.

## Retained 0.6.4 transport evidence

The following tests/results were delivered with 0.6.4 and are retained as prior
verification of unchanged transport code. They were not all re-executed for this
reconstruction release and are not new GPU or in-game measurements.

| Area | Prior result |
| --- | --- |
| Cloud phase | HG mean cosine 0.5913 for target g=0.60; 32,768 samples |
| Cloud extinction | Numerical transmittance 0.204243; sampled survival 0.201538 |
| Cloud anchoring/switches | World-position agreement; Cloud Off, Volumetrics Off and ceiling dimensions remove cloud collisions/extinction |
| Emitter behind clouds | Radiance 4.83691 versus numerical Beer expectation 4.90183 |
| Caustic guide | Four-step direction error below 0.005 for 4,096 fixture receivers |
| Water focusing | Spatial variation 0.38595 with waves versus 0.08415 with flat water; 256 paths/pixel, no filter |
| Caustic energy | Wave/flat mean ratio 1.00904; focused maximum/mean 2.8612 |
| Caustic occlusion | Caustics Off and opaque water replacement produce zero refractive receiver contribution |
| Materials and BVH | Seven translucent classes, native emission, fluid boundaries and bounded indirect dispatch pass |

Clouds still use finite density quadrature and bounded path budgets. Water
uses a refracted-sun importance proposal, not a photon map or a separate caustic
texture. These approximation limits remain documented in SOURCE_GUIDE.md.

The rare-light history regression was re-run with the new cache. It preserves
97.01% of the fixture's steady energy; after switching the source Off, 0.7807%
remains at 16 frames and 0.0439% at 32. This tests a stationary stochastic signal,
not live Minecraft motion or exact animated-cloud motion vectors.

## Reproduce current checks

Requirements: Python 3, NumPy, Pillow, libEGL and libGL with a compatible OpenGL
context. No game assets or NVIDIA runtime are used. Run render/timing cases
sequentially. A reduced LP_NUM_THREADS can limit software-renderer CPU use.

```bash
python3 tests/validate.py
python3 tests/upscale_regression.py
python3 tests/ptgi_reconstruction.py
python3 tests/temporal_response.py
python3 tests/material_scene_review.py
python3 tests/cloud_scene_review.py
```

Current evidence:

- `validation.json`: linked programs, menu/default and allocation checks.
- `upscale_v065.json`, `v065-upscale-comparison.png`: production reconstruction
  of analytic input fields. Image panels are reference / Fast / Detail.
- `current-reconstruction.json`: texture/history/noisy-light reconstruction.
- `v063-temporal-response.json`: reusable rare-light fixture's current result;
  the retained filename identifies its introduction, not a GPU or game version.
- `v065-{torch-room,water-above,water-below}.{png,json}`: actual whole-pipeline
  193x113 synthetic renders with 32 frames of accumulation.
- `v065-cloud-scene.{png,json}`: 257x145, 32 frames, Med clouds and frozen wind.
- `controlled-*-timing.json` and `*-scene.png`: measured synthetic comparison
  cases; `PERFORMANCE.md` lists reproducible commands and limitations.

All evidence paths above are relative to `tests/ptgi-evidence/`. Images are
actual shader output, not Minecraft screenshots or generated mockups. The small
resolutions make tests practical in a software renderer; they are not desktop
resolution quality or throughput measurements.

Optional retained transport checks:

```bash
python3 tests/atmosphere_regression.py clouds
python3 tests/atmosphere_regression.py caustics
python3 tests/audit_regression.py
python3 tests/ptgi_regression.py transport
python3 tests/ptgi_regression.py volume
python3 tests/pt_effect_controls.py
```

`clouds_v064.json`, `caustics_v064.json`, `cloud_transport.png`,
`water_focusing.png`, `v064-*`, `v063-*` and AUDIT_RESOLUTION.md retain earlier
checks. Older dense-BVH, white-furnace and loader-source audits do not establish
OptiFine/macOS compatibility or a hardware RT backend for this release.
