# Current verification: 0.7.6

All measurements below use production GLSL on Mesa llvmpipe OpenGL 4.5.
Minecraft, Iris's shader transformer and the user's NVIDIA GPU/world were not
available. These are controlled regression tests, not game screenshots or FPS
benchmarks. Historical sections retain their original scope and release.

## Glass history and filtering

- An analytic receiver 16 blocks behind a pane at 2 blocks reproduces the old
  camera-parallax blur at a simulated 12 FPS. In the noise-free fixture, RGB
  RMSE changes from 0.07399 to 2.72e-8 and contrast retention from 21.27% to
  effectively 100%. This ideal thin-interface result does not predict exact
  contrast in arbitrary thick or curved refracting scenes.
- With injected exponential noise in the same moving fixture, RGB RMSE is
  0.23843 raw and 0.01760 filtered. The production passes also preserve the
  packed secondary guide exactly and exclude metadata from diffuse radiance.
- A stationary random reflection/transmission mixture retains its known mean
  RGB energy. Filtered/raw RMSE is 0.03289. Changing a stochastic secondary
  guide must not continually restart an otherwise stationary pixel's history.
- A real captured finite glass slab and colored emissive bars pass the complete
  PT pipeline at 257x145 over 32 frames. Central RGB is 0.46327 / 0.04249 /
  0.51175; red-blue contrast is 0.77145. Secondary hit guidance is real ray-hit
  data, not a screen-color substitution.
- The ideal secondary-guide fixture over 64 frames has raw/filtered RGB RMSE
  0.67489 / 0.05387, with 100.65-100.96% mean RGB energy retention. This is
  intentionally easier than real mixed optical paths.

## Sampling, motion and display color

- The production sampler passes known uniform 1D and 2D integral means.
  Eight-frame MSE ratios (stratified/white noise) are 0.01566, 0.04350 and
  0.30600 for the three chosen functions. These are targeted sampler results,
  not a universal path-tracing noise reduction percentage. No extra paths are
  introduced.
- The existing synthetic rare-night-path moving-floor fixture remains finite:
  mean RGB RMSE 0.00293, temporal flicker RMSE 0.000565, with displaced-surface
  history reset to one frame. Newly visible geometry still needs new samples.
- The production final pass preserves RGB ratios before gamut compression
  (maximum tested error 1.28e-7), matches the legacy fit for neutral ramps, and
  remains finite and monotonic across the tested HDR range. Tone mapping
  changes display color, not illumination or cloud coverage.

## Water regression and compilation

- The animated underwater fixture uses real captured geometry and production
  PT at 257x145, base scale 50%, HRR enabled, over 12 frames. Final frame-
  difference RMSE is 0.01500 versus 0.01578 in the same 0.7.5 fixture;
  98.65% of sampled water pixels exceed display 0.05. Both actual animation
  and sampling noise affect this metric. The compact glass reprojection and
  filter policy is deliberately excluded from water's wave/volume mixture.
- The unchanged unguided optical history case retains 99.64% of known mean
  energy. Its filtered/raw RGB RMSE ratio is 0.11034.
- 60 reconstruction program links pass across LOW, MED, HIGH, ULTRA, optical
  economy, effects off, non-sparse, raw, PBR and mixed-HRR configurations.
  The standard MED compilation also completed 80 program links. These are
  Mesa compiler checks, not NVIDIA C5041 or Iris integration guarantees.
- Static validation covers 143 English option labels/tooltips, four profiles,
  menu reachability, buffer contracts and 15 literal clear colors.

The tracing budgets are unchanged. Sampling adds integer arithmetic, and
colortex12 changes from RGBA16F to RGBA32F for exact optical metadata: an extra
8 bytes per base-grid pixel per ping-pong image. No Minecraft performance
increase is established. Motion noise, low-resolution optical detail, thick
refraction and animated media remain limited by sample count and reconstruction.

Current runtime hashes and the evidence inventory are recorded in
`tests/ptgi-evidence/v076-verification-manifest.json`. Relevant test scripts and
synthetic image evidence are included in the extras archive.

---

# Historical verification: 0.7.5

- 25 GPU source-radiance probes: all four torch families and copper lanterns
  match the normal-source luminance at five equal texture intensities.
- All eight copper lantern variants resolve to one dedicated identity.
- Normal and soul lantern IDs remain unchanged. Source colors remain distinct.
- About metadata, complete option tooltips, four profiles, and program links
  checked by validate.py. ZIP contents and exact license bytes checked by build.py.

These are synthetic Mesa OpenGL tests, not Minecraft screenshots or driver/FPS
benchmarks. Different source meshes and resource-pack textures can still change
integrated output; the user's exact scene has not been run here.

---

# Historical verification: 0.7.4

All new tests run on Mesa llvmpipe OpenGL 4.5, not Minecraft/Iris/NVIDIA.

- Raster material test: normal toggle changes encoded normal by mean absolute
  0.04341; POM changes full-resolution albedo by 0.10552 with synthetic relief.
  Smoothness 0.75 decodes to roughness 0.0625 (disabled baseline 0.75).
- Dense-atlas regression: same face with UV scale 1 versus 1/4096 gives a maximum
  normal error of 0.298584 in v0.7.3, and 0 in v0.7.4. The retained baseline
  assertion failure is intentional proof of the old defect.
- Closest ray hit: normal changes from (0,0,1) to (0.3,0,0.95394), roughness
  changes from 0.74902 to 0.04. Disabling map options restores geometric material.
- All 16 dyed candle source probes are finite/nonzero and preserve assigned RGB
  despite dark wax inputs; red and blue channel-dominance assertions pass.
- MED: 80 program links; LAB_PBR: 43 links; oldPBR: 43 links; new diagnostic variants: 12 links (178 total).
- Shader metadata/options and two new debug views are checked separately.

No user resource pack was supplied. These tests establish functional map paths
and a reproducible atlas defect; they do not prove every reported no-effect case
is fixed in-game. POM is not applied to secondary intersections or silhouettes.
No new performance benchmark is available. Earlier evidence below is historical.

---

# Historical verification: 0.7.3

All current measurements are synthetic Mesa llvmpipe OpenGL 4.5 results, not
Minecraft, Iris or NVIDIA results. Historical sections below retain earlier
measurements and do not imply every old test was rerun.

- Source probe: torch, lamp, white/black candle, copper flame, crying obsidian,
  lichen, firefly, oxidized bulb, redstone ore, berries, sculk, anchor and dark
  native-emission fallback produce finite nonzero radiance; unlit input is zero.
- Held emitters: empty and disabled are zero; main/off hand are colored, both
  add exactly, and a real captured opaque wall blocks them completely.
- Solar reflection fixture (16,384 raw samples): old luminance variance
  871120.06, new 0.01108. The old mean is poorly converged (nine nonzero hits);
  this is a targeted variance result, not a universal noise reduction figure.
- Cloud fixture (9,216 raw samples): variance 0.00139367 -> 0.0000639954
  (95.4% lower), average RGB energy ratio 0.9923.
- Lit glass and a foreground-cloud scene remain finite/nonblack through the
  complete production pipeline. Neither reproduces the user's full-black case.
- Animated underwater fixture: 12 frames, 257x145, 50% base grid with HRR.
  Clear-water material tuning reduces frame-difference RMSE from 0.02939 to 0.01578; 99.2% of water pixels exceed display 0.05.
  Animation and Monte Carlo variance both affect this metric; the image still
  contains visible caustic noise. It is not a noise-free result or FPS benchmark.

The source, sample data, images and scope notes accompany the ZIP.

- Final metadata: 140 documented options, four profiles. MED: 80 real GLSL
  links; mixed HRR: 43 links, all passed. No NVIDIA C5041 guarantee is implied.

---

# Verification — LampPT 0.7.2 experimental

Production GLSL was rendered and linked on Mesa llvmpipe OpenGL 4.5.
**Minecraft, Iris's transformer and NVIDIA hardware were unavailable.** The
results below are controlled synthetic tests, not game FPS or the user's world.
Historical evidence remains labeled with its original release. The current
runtime shader hashes and evidence list are in v072-verification-manifest.json.

## Reproduced optical blur

`optical_detail.py` injects a known, noise-free colored secondary image behind a
flat clear interface and executes the production temporal/filter/resolve passes.
It isolates filtering from transport noise. At 257x145 and base scale 50%:

| Metric | 0.7.1 | 0.7.2, without secondary-hit guidance |
| --- | ---: | ---: |
| RGB error against the unfiltered image | 0.17337 | 0.04090 |
| Red-channel contrast retained | 20.00% | 85.53% |

This demonstrates the old filter destroying optical detail, not a measured
improvement for arbitrary scenes. The new compact fallback already preserves
more of the known image. Evidence: v071-comparison-optical-detail.json and
v072-optical-detail.json, with paired reference/filtered PNGs.

## Actual traced glass and secondary-hit guidance

`glass_review.py` uses a finite glass slab and 24 alternating red/blue emissive
bars. Actual raster/capture shaders, BVH intersections, dielectric entry/exit,
traced transport and reconstruction run for 32 frames at 257x145, base 50%.
Clouds, bloom, dither, sun and environment light are disabled to isolate the bars.
The new default glass roughness and optical reconstruction are both active;
this comparison does not isolate their individual contributions.

| Metric | 0.7.1 | 0.7.2 |
| --- | ---: | ---: |
| Central red-minus-blue contrast | 0.16012 | 0.85966 |
| Central mean RGB | 0.48246 / 0.04085 / 0.48099 | 0.46314 / 0.04217 / 0.50760 |

The old image merges the bars into a broad magenta patch; the new render retains
separate bars. Both PNGs were inspected. The effect comes from real secondary
intersections, not a screen-image substitution. v072-guide-check-glass additionally
asserts that actual hit payloads exist and survive the temporal pass bit-exactly.

Eight-frame route checks pass with Clear Water and Glass Off, Reflection HRR Off,
and Shared Surface Paths Off. Their central total radiance remains inside the
same bounded expected range; no mode drops glass transmission or double-counts
both coarse and base-grid optical paths. Evidence: v072-route-*-glass.json.

`optical_guidance.py` supplies ideal receiver guides for a known colored image
with 20%-probability noisy samples. After 64 production reconstruction frames,
RGB RMSE falls from 0.67489 raw to 0.05542, contrast retention is 102.98%, and RGB
energy retention is 101.4–102.0%. This tests noise reduction without erasing color
edges. It is an ideal-guide test; real stochastic hit guides are less stable.

## Water, residual grain and energy

`water_review.py` uses a real captured checker pool, submerged geometry and
colored pillars. First-hit wave normals are refreshed each frame with the same
production wave function used by secondary paths. Above and below views render
48 frames at 257x145, base 50%, HRR On, with clouds/bloom/dither Off.

The new images are finite, the pool pattern is more distinct, and more than 98%
of sampled underwater pixels are visibly nonblack. Linear mean RGB below water
is 0.08294 / 0.12344 / 0.19679 versus 0.08452 / 0.12495 / 0.19750 in 0.7.1. The
change is not an exposure/ambient-light increase. Above water the new mean is
0.06696 / 0.08899 / 0.11749. These images were inspected.

Sharper optical detail exposes more grain. The animated frame-difference metric
increases (below: 0.00949 to 0.01843), including both actual wave motion and Monte
Carlo noise. It must NOT be described as a global noise improvement. The fixture
is tiny and undersampled; no claim of reference-image quality or noise-free
moving water is made. Clear Interface Filter controls the smoothing tradeoff.

`transmission_history.py` retains 99.84% of known mean optical energy. Raw RGB
RMSE 0.86614 becomes 0.08291; this is higher than 0.7.1's 0.04793 because the
unguided compact filter deliberately avoids repeated blur. The target here is
clarity with preserved energy, not the lowest error on a constant-color field.

## Regressions and workload

- `ptgi_reconstruction.py`: primary texture max error 0.000915, emission error
  0.000435; zero stationary drift at even/odd sizes; zero stale disocclusion
  error; spatial Off and opaque reflection/noise fixtures pass with the same
  results as 0.7.1. Opaque reconstruction behavior was not replaced.
- `hrr_regression.py`: independent component sizes, diffuse/specular partitions,
  parallel slab intersections, zero-alpha glass metadata, visible emitter behind
  glass, and transmission with Reflections Off all pass.
- `validate.py MED`: 80 real OpenGL program links completed.
- `validate.py METADATA`: 135 options with English labels and tooltips; supported
  values, four consistent presets, menu reachability, Medium defaults, buffer
  sizing, 15 literal clear colors, and first-row Profile/About pass.
- `reconstruction_compile.py`: 60 links across all profiles, optical economy,
  temporal/denoiser Off, diagnostics, PBR and mixed HRR.
- `hotfix_compile.py`: 45 compute/merge links including all HRR Off, effects Off,
  optical economy and shared paths Off. Stackless BVH and one merge integrator
  call site are retained; Mesa compilation cannot certify NVIDIA C5041 behavior.
- `preset_budget.py`: four consistent key sets and 64 image/dispatch combinations
  pass. Nominal component budgets exclude selective base-grid optical tracing.

The real-mesh two-frame Medium workload test at 127x75 counts 727.5 ray queries,
9,229 node entries and 520 camera estimators per frame, versus 562 / 7,125 / 502
in 0.7.1. The roughly 29.4% ray-query increase in this scene is a real cost; a
water-filled scene can cost more. Instrumentation excludes BVH build and post
filters and does not measure game FPS. Clear Water and Glass is an optional
quality/cost tradeoff, not a free optimization.

## Reproduce

From the pack root with Python, NumPy, Pillow, cpp and Mesa EGL/OpenGL:

```bash
LP_NUM_THREADS=2 python3 tests/optical_detail.py
LP_NUM_THREADS=2 python3 tests/optical_guidance.py
LP_NUM_THREADS=2 python3 tests/glass_review.py
LP_NUM_THREADS=2 python3 tests/glass_review.py --frames 8 --label v072-route --hrr-off
LP_NUM_THREADS=2 python3 tests/glass_review.py --frames 8 --label v072-route --shared-off
LP_NUM_THREADS=2 python3 tests/glass_review.py --frames 8 --label v072-route --economy
LP_NUM_THREADS=2 python3 tests/water_review.py --case above
LP_NUM_THREADS=2 python3 tests/water_review.py --case below
LP_NUM_THREADS=2 python3 tests/ptgi_reconstruction.py
LP_NUM_THREADS=2 python3 tests/transmission_history.py
LP_NUM_THREADS=2 python3 tests/hrr_regression.py
LP_NUM_THREADS=2 python3 tests/validate.py MED
LP_NUM_THREADS=2 python3 tests/validate.py METADATA
LP_NUM_THREADS=2 python3 tests/reconstruction_compile.py
LP_NUM_THREADS=2 python3 tests/hotfix_compile.py
LP_NUM_THREADS=2 python3 tests/preset_budget.py
LP_NUM_THREADS=2 python3 tests/workload_compare.py --profile MED --frames 2 --label v072-medium-optics
```

Glass and optical-detail tests accept --pack /path/to/v071/shaders and --label
for the baseline. workload_compare.py accepts the pack root instead. No test
establishes universal loader compatibility, a minimum frame rate or zero noise.
