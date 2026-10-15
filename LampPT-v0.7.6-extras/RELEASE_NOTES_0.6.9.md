# LampPT 0.6.9 experimental

This update addresses the reported performance regression and remaining noise.
It keeps world-space mesh path tracing for illumination. Rasterization still
supplies first visibility; this is not a replacement for the entire game engine.

## Less repeated tracing

**Shared Surface Paths**, On by default, evaluates direct illumination, diffuse
bounce and specular reflection with one BSDF continuation when their three HRR
grids match. Diffuse irradiance and specular radiance remain separate outputs,
with matching sampling PDFs and MIS. Primary volumetric/cloud scattering remains
separate. Mixed HRR configurations automatically keep their independent paths.

The unused GI/reflection kernels become empty and never overwrite the shared
outputs. HRR repair also shares a path for missing diffuse/specular samples while
retaining one integrator call site. Turning the option Off restores independent
surface estimators, at higher cost. Sharing fewer rays can increase raw variance;
the estimator remains PT and does not substitute screen-space or cached light.

Medium stacks now reserve only the interface-event budget plus one entry (9 at
Med), instead of 16 entries for every path. The stackless BVH traversal from the
NVIDIA C5041 fix remains unchanged. No geometry or light is disabled to save work.

## Cheaper reconstruction and less residual noise

- Merge writes a compact first-hit cache before temporal accumulation. Temporal
  statistics read this cache instead of decoding all full-resolution material,
  glass and water inputs for nine neighbors.
- Sparse Sample Reconstruction reuses that variance estimate. The extra 3x3
  first-pass variance gather is removed; raw accumulated light is never clipped.
- Med/High use four 3x3 a-trous filters and a maximum of 64 history frames. Med
  previously used three 5x5 filters plus the extra 3x3 gather: 84 neighborhood
  taps become 36. These counts exclude temporal statistics and final upscaling.
- Low uses three 3x3 filters and 32 history frames. All controls remain editable.
- BSDF lobe selection uses view-angle Fresnel and estimated diffuse energy.
  Grazing reflective paths are no longer stuck with a five-percent proposal.
  Sampling and PDF evaluation use the same probability.
- Full-resolution primary albedo and visible emission remain outside filtering.
  Temporal means receive no spatial-filter feedback, avoiding accumulating blur.

## What was verified

The fixed synthetic room records about 35% fewer ray queries and 42% fewer BVH
node entries. The known-mean sparse RGB reconstruction fixture records 14–17%
lower error with the new default reconstruction settings. These are scoped test
results, not a promise of the same change in game FPS or scene noise.

See TEST_RESULTS.md for exact numbers, glass/slab/detail checks and limitations.
The 49-dispatch scene rebuild, capture range and scene storage are unchanged;
they can still dominate a complex Minecraft world. No Minecraft or NVIDIA
runtime is available for validation here.

## Installation

Select `LampPT-v0.6.9-experimental.zip`, Reset, choose **Med**, then Apply. Keep
Shared Surface Paths, Temporal Accumulation, Spatial Denoiser and all four HRR
switches On initially. Keep Adaptive Sharpening Off. If frame rate remains too
low, choose Low. Reusing old option files can retain expensive old filter sizes.

## Public technical references

SEUS's published HRR release notes describe half-resolution reconstruction,
history responsiveness and an improved GI filter. They also describe some
screen-space features; LampPT does not add those to its illumination renderer.
This is not a port of SEUS shader code.

- [Sonic Ether: SEUS PTGI HRR Test 2.1](https://www.patreon.com/sonicether/posts/download-seus-2-45141775)
- [NVIDIA NRD: signal separation, material demodulation and sampling guidance](https://github.com/NVIDIA-RTX/NRD)

NRD is an algorithm reference, not an SDK integrated into this shaderpack. These
original GLSL changes do not add NRD, FSR, DLSS, RT-core acceleration or frame
generation. No proprietary SEUS shader source is included.
