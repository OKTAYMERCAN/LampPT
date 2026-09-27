# Performance and Upscaling — 0.6.5

Open **Shader Options -> Performance and Upscaling**. Start with Med. Low/Med
use Fast upscaling; Detail is an optional quality tradeoff. All source lighting
continues to use the existing world-space path integrator.

## Resolution and work

These are percentages of each display axis, not percentages of total pixels.
The pixel counts below are before integer dimension rounding and before the
water multiplier, event budgets or early path termination.

| Setting | Transport pixels vs native | Transport pixels vs old 50% Med | Example at 1920x1080 |
| --- | ---: | ---: | --- |
| 33% | 10.89% | 43.56% | 633x356 |
| 40% (Med) | 16.00% | 64.00% | 768x432 |
| 50% | 25.00% | 100.00% | 960x540 |
| 59% | 34.81% | 139.24% | 1132x637 |
| 67% | 44.89% | 179.56% | 1286x723 |
| 77% | 59.29% | 237.16% | 1478x831 |
| 100% | 100.00% | 400.00% | 1920x1080 |

New Med has **36% fewer transport pixels** than old Med, with the same per-pixel
path/event settings. This is not a 36% frame-rate promise. Primary visibility,
material buffers, final resolve and lens processing remain full resolution.
Scene capture and BVH construction still happen each frame at their existing
capacity. A geometry/CPU bottleneck may barely respond to resolution changes.

The new guide cache stores geometry/material information for filter taps.
This avoids repeated full-resolution layer decoding, at the cost of another
transport-sized RGBA32F target. Two 40%-scale copies at 1080p contain about
10.1 MiB of guide data. Actual driver allocation is implementation-dependent.
Lower scales shrink the existing transport/history targets; they do not shrink
the scene BVH or Minecraft's world data.

## Quality and cost controls

| Control | Lower-cost choice | Tradeoff |
| --- | --- | --- |
| Upscale Filter | Fast (4 taps) | Detail (16 taps) reconstructs sampled smooth fields more accurately but costs more |
| Lighting Resolution | 40%, then 33% | Thin surfaces, small shadows and reflected/refracted features can be undersampled |
| Adaptive Sharpening | Off | Skips the whole pass; On adds controlled local detail contrast |
| Spatial Filter Passes | One | Skips the wider second filter; leaves more grain, especially in water and clouds |
| Spatial Reconstruction | Off | Skips both spatial filters, with much more visible Monte Carlo noise |
| Bloom Quality | Fast (9 taps) | Fine uses 25 taps for a smoother lens kernel; neither illuminates the scene |
| Water Sample Multiplier | 1x | Less water-path work, more caustic/transmission noise |
| Cloud Density / Shadow Steps | Lower counts | Less cloud integration work, more quadrature error/banding |

Keep Temporal Accumulation and two spatial passes enabled initially. Try lower
resolution and Fast first. Sharpening cannot recreate missing light samples;
excessive sharpening can emphasize grain despite its variance guard. If fine
reflected detail matters, raise Lighting Resolution before raising sharpening.
Normals, POM and optional concrete powder emitters remain Off in all profiles.

## What the upscaler is

LampPT uses its own geometry-guided spatial reconstruction of separate HDR
diffuse/specular transport. The primary diffuse texture is multiplied back in
at display resolution. Detail uses bounded cubic weights at the actual snapped
ray positions; the sharpening stage is noise-aware and limited by local extrema.
Neither algorithm was copied from AMD FSR or RCAS. No FSR SDK, temporal
super-resolution, motion interpolation, generated frames or RT-core backend is
included. Temporal accumulation remains the existing lighting denoiser.

## Synthetic draw timing

The figures below are **software-renderer measurements**, not game FPS or an
RTX benchmark. The fixture is 257x145 with a room, lights, water and clouds;
geometry capacity is 65,536 and wind is frozen. It records GL_TIME_ELAPSED
around composite1..6 draws, excluding compilation, allocations, readbacks,
geometry capture/build, final tone mapping/bloom and Minecraft. Nine frames are
measured after three warmup frames. Cases were run sequentially with
LP_NUM_THREADS=1. Every new case retains the same PT integrator as 0.6.4.

| Run | Sum of composite draws (median ms/frame) | Upscale/resolve stage (median ms) |
| --- | ---: | ---: |
| 0.6.4, 50% | 196.85 | 15.28 |
| 0.6.5, 50%, Fast | 112.95 | 9.91 |
| 0.6.5, 40%, Fast (new Med) | 78.94 | 7.41 |
| 0.6.5, 40%, Detail | 80.68 | 20.83 |

The shared CPU environment still varies substantially between runs: even the
unchanged integrator at equal resolution has different times. These values
illustrate the test and the Detail filter's extra cost, **not a reliable overall
speedup percentage**. Earlier driver-default-thread runs are also retained in
`tests/ptgi-evidence/*-timing.json`; they include a slower new-build run and
must not be selectively treated as hardware predictions. Workload counts and
image regressions are the reproducible claims; actual game performance needs
measurement on the user's GPU/world.

Reproduce the controlled comparison sequentially, with no concurrent renders:

```bash
LP_NUM_THREADS=1 python3 tests/performance_scene.py --pack /path/LampPT-v064 --scale 50 --label controlled-v064-50
LP_NUM_THREADS=1 python3 tests/performance_scene.py --scale 50 --filter 0 --label controlled-v065-50-fast
LP_NUM_THREADS=1 python3 tests/performance_scene.py --scale 40 --filter 0 --label controlled-v065-40-fast
LP_NUM_THREADS=1 python3 tests/performance_scene.py --scale 40 --filter 1 --label controlled-v065-40-detail
```

`--pack` points to an extracted pack root containing `shaders/`. The old ZIP is
not embedded in the new one. See TEST_RESULTS.md for reconstruction quality,
finite-image checks and the absence of a Minecraft/Iris/NVIDIA runtime here.
