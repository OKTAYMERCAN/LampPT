# Performance and HRR — 0.7.3

Start with **Medium** after Reset. All presets keep temporal/spatial denoising
and Shared Surface Paths On. Sharpening starts Off. These profiles budget a
software GPU path tracer; they are not certified RTX performance tiers.

## Profile budgets

| Budget | Low | Medium | High | Ultra |
| --- | ---: | ---: | ---: | ---: |
| Base PT scale, each axis | 25% | 33% | 40% | 50% |
| Component scale with HRR | 12.5% | 16.5% | 20% | 25% |
| Paths per pixel | 1 | 1 | 1 | 1 |
| Scattering events | 2 | 2 | 3 | 4 |
| Transmission events | 4 | 4 | 6 | 8 |
| Emitter candidates / samples | 2 / 1 | 2 / 1 | 4 / 1 | 4 / 1 |
| Water sample multiplier | 1 | 1 | 1 | 1 |
| Capture radius, blocks | 64 | 96 | 128 | 160 |
| Triangle capacity | 262144 | 524288 | 1048576 | 1048576 |
| Traversal node budget | 256 | 512 | 512 | 512 |
| Ray length, blocks | 128 | 192 | 256 | 256 |
| Scene buffers, MiB | 46.03 | 92.06 | 184.13 | 184.13 |
| Reflections | Off | On | On | On |
| Volumetric clouds | Off | On | On | On |
| Cloud density / shadow steps | 16 / 8 | 16 / 8 | 24 / 8 | 32 / 16 |
| Cloud distance, blocks | 1024 | 1024 | 1024 | 2048 |
| Caustic guide iterations | 2 | 2 | 4 | 4 |
| Maximum history weight | 32 | 64 | 64 | 64 |
| Spatial stages, 3x3 each | 3 | 4 | 4 | 4 |
| History Stabilization | 0.25 | 0.25 | 0.25 | 0.25 |
| Optical History Limit | 16 | 16 | 16 | 16 |
| Clear Water and Glass | On | On | On | On |
| Clear Interface Filter | 0.75 | 0.75 | 0.75 | 0.75 |
| Smooth optical scale, each axis | 25% | 33% | 40% | 50% |

Every preset enables all four HRR switches, Fast upscaling, Fast bloom and Rough
Reflection Stability. Normal maps, POM and concrete powder emission remain Off.
Low's cloud step values apply if clouds are manually enabled. Reflection Off
preserves glass/water transmission but removes reflective lobes; metals can darken.
Choosing another preset replaces the same controlled keys, including these switches.

## What HRR means

Each switch halves both axes relative to the base scale: one quarter of the
component pixels. At 1920x1080, Medium uses a 633x356 reconstruction grid and
316x178 component images (integer truncation). It does not reduce the resolution
of Minecraft's first-hit rasterization, primary diffuse textures or final display.

| Switch | Component |
| --- | --- |
| Direct Shadows HRR | Primary diffuse direct light and source visibility |
| GI HRR | Diffuse continuation and secondary bounce lighting |
| Reflections HRR | Opaque reflections and water/glass optical paths |
| Clouds HRR | Visible sky and primary cloud/air/water scattering |

Matching surface grids use one weighted BSDF continuation for diffuse/specular
lighting. A mixed configuration remains independent and costs more tracing.
Primary volume sampling remains separate. Unsupported silhouettes receive real
base-grid path repairs. These repairs add work and cannot reconstruct unsampled
secondary detail. Low-resolution reflected/refracted detail can soften.

## Cost of clear optical detail

Clear Water and Glass applies to dielectric first hits with roughness below 0.08.
With Reflection HRR On, their surface paths run at the base grid instead of the
coarse grid: approximately four times the optical path pixels. Coarse optical
surface paths are skipped, so both resolutions are not traced. PT Samples and
Water Sample Multiplier still apply. Opaque surface grids, scene capture and BVH
budgets remain unchanged. With Reflection HRR Off the optical grid is already
base-sized. No additional image allocations or render passes are required.

The traced receiver's normal/color/distance piggybacks on existing intersections.
The filter reuses colortex6; optical primary guides are fetched from the raster
buffers instead of their old cache payload. This adds guide/filter operations.

In the two-frame, 127x75 synthetic Medium scene, total ray queries increase from
562.0 to 727.5 per frame (~29.4%); node entries from 7,125 to 9,229. This is a
workload count, not a frame-time result. A water-filled view can cost more. Turn
Clear Water and Glass Off to restore the coarse grid if necessary; lowering the
whole pack's resolution is not required. Clear Interface Filter changes the
noise/detail tradeoff separately. No minimum FPS is guaranteed.

## Why old Ultra was excessive

Old Ultra combined 100% scale, HRR Off, four camera samples, eight scattering
events, four light samples, eight emitter candidates, 4x water samples and 96/48
cloud steps. The new preset removes those simultaneous multipliers. At 1080p,
nominal primary surface samples fall from 8,294,400 to 129,600: a factor of 64.
The budget audit counts declarations, excluding the optical override and
other adaptive repairs; it does not establish a 64x speedup.

The four profiles now increase selected work gradually. No preset enables a
native-resolution multi-sample stress configuration. Those manual controls remain
available, but raising several budgets together can still overwhelm the GPU.

## Motion denoising and remaining costs

Surface-plane validation preserves history on grazing geometry. Rough reflections
keep up to 32 compatible frames during motion; sharp mirrors/glass keep a shorter
history. This reuses the existing temporal pass without extra rays or render passes.
History Stabilization feeds a bounded fraction of the first compact filter into
diffuse and rough opaque reflection history; the two existing history targets
receive additional writes, without new allocations or filter passes. Water/glass
are excluded from this feedback. Wider stages never feed back. Primary textures
and visible emission are restored at full resolution. Extra ripple evaluation adds
three cosine terms when waves are enabled. None of these costs has an in-game
GPU timing measurement.

Terrain capture and the 49-dispatch BVH rebuild still run each frame. Reducing
resolution does not reduce that work, CPU cost or all display-resolution passes.
The listed scene memory excludes all framebuffers, atlas textures and Minecraft
allocations. The eight component images remain allocated to support independent
HRR choices. Reduced capture/capacity can lose distant geometry; check Scene
Coverage and Triangle Capacity. Increasing ray length does not capture more terrain.

Select Low if Medium remains slow; reduce capture distance in dense vegetation,
or disable clouds/reflections independently. Avoid disabling denoising as the
first performance adjustment: it exposes the one-sample path noise. No in-game
FPS floor or GPU speedup has been measured; see TEST_RESULTS.md.

## 0.7.3 incremental cost

Hand lighting skips all visibility work with empty/nonemissive hands or when
disabled. A lit hand adds up to one shadow connection per scattering vertex
(two with both hands). Dielectric solar NEE adds a bounded sun visibility ray
where the reflection lobe can see the sun. Volume reconstruction uses nine
texture taps, not additional scene rays. Conditional clouds reuse bounded
quadrature. These are variance/feature changes, not a measured game FPS gain.
