# Source guide — 0.6.5

All shaders include English comments describing their role and important limits.

## Data flow

1. `begin.csh` resets the captured triangle counters once per frame.
2. `shadow.vsh` reads camera-relative terrain positions, material IDs and atlas
   data. `shadow.gsh` appends actual triangles up to Triangle Capacity. The shadow
   pass provides geometry access; its raster depth is not used for PT illumination.
3. `shadowcomp` writes a bounded indirect-dispatch command from the captured
   count. `shadowcomp_a` produces 30-bit Morton keys. `shadowcomp1` through `45` run fifteen
   stable two-bit radix passes (scan, parallel global prefix, scatter). `46`
   writes leaves and the Morton-prefix radix topology; `47` propagates bounds
   using child-completion counters. Each dispatch is ordered. Within `47`, the
   first child exits and the second merges; no thread spins waiting for another.
4. `gbuffers_*` record first-hit depth, albedo, materials and normals. Translucent
   targets retain nearest water and nearest glass independently of opaque data.
5. `composite1` runs the path integrator into diffuse irradiance and residual
   specular/transmission/volume channels. It does not read lit raster scene color.
6. `composite2` reprojects valid history, updates independent moments and optionally
   suppresses isolated outliers and writes a compact current-frame guide cache.
   `composite3/4` filter compatible lighting samples when enabled.
7. `composite5` restores full-resolution albedo and visible emitter artwork;
   `composite6` optionally sharpens with a variance guard. `final` applies display response/bloom
   or a selected diagnostic. No additive Hybrid illumination target is produced.

## Geometry and memory

`lib/scene/storage.glsl` defines SSBO layouts: binding 0 stores sort scratch,
binding 1 stores a 16-byte header and 80-byte triangles, binding 2 stores 32-byte
BVH nodes, and binding 3 stores child links, parent links and completion counters.
Binding 4 is a 16-byte indirect command (`uvec4`). Its XYZ group counts are
initialized after every capture, clamped to capacity, and never zero. Iris uses
its command barrier before indirect dispatch and SSBO barriers between passes.
Only the single-group radix prefix passes keep a fixed dispatch size.
For n triangles, internal nodes occupy [0,n-2] and leaves [n-1,2*n-2]. The root is
node 0. Leaves retain triangle indices; triangles retain their reverse leaf index
for source-hit MIS. Empty capture uses an invalid root. Capacity does not set range.

`lib/scene/build.glsl` uses longest common prefixes of sorted Morton keys to split
spatial regions. Sorted indices break duplicate-key ties. Each internal node's
topology is computed independently, following parallel radix-tree construction;
this is not a surface-area-heuristic optimizer. The bounds pass publishes child
data before atomic completion and uses coherent buffers. Iris dispatch ordering
supplies the SSBO barriers between passes. All walks and storage remain bounded.
`shaders.properties` allocations must match all five layouts exactly.

`lib/scene/trace.glsl` uses near-first AABB traversal, a 64-entry stack and bounded
node visits. Hits use Moller-Trumbore barycentrics, UV alpha tests, outward normals
and actual dielectric boundaries. Direct-light connections terminate at the first
valid occluder; closest-hit transport still finds the nearest surface. A complete
miss uses the environment even if capture overflowed: missing triangles are not
a universal blocker. Actual node-budget exhaustion remains conservatively opaque.
There is no voxel visibility fallback. Incomplete capture can produce light leaks.

## Transport

`ptgi/bsdf.glsl`: Lambert/GGX evaluation, visible-normal GGX sampling, dielectric
Fresnel, Snell transmission/TIR, matching PDF and bounded caustic guidance.
Underwater guidance performs two captured-interface queries, with bounded damped
Newton iterations between them. The 2D residual is the horizontal receiver-to-
interface displacement minus the refracted-sun slope times water depth. Its
finite-difference Jacobian uses the same wave function as the water BSDF. A
remaining residual widens the proposal. A finite-difference angular Jacobian
warps the finite sun/roughness disc into an ellipse in the receiver tangent plane.
The gnomonic solid-angle Jacobian is included in its PDF; sampling and PDF share
the same warp. This avoids rare huge weights from a fixed cone missing most of
a focused or stretched sun preimage. Cache preparation runs once per scattering vertex;
PDF evaluation must not repeat those geometry queries. Guidance only changes
sampling probabilities; it does not supply an unoccluded lighting term. The
proposal is disabled without active directional radiance or a usable water exit;
the same cached probability controls sampling and PDF evaluation.

`ptgi/lights.glsl`: separate finite sun and cosine-sampled sky proposals, source
triangle importance sampling via the BVH, area-to-solid-angle conversion and MIS.
The emitter tree is a probability distribution; it never injects point-light glow.
For each emitter estimate, candidate contributions are weighted by their actual
unoccluded radiance, BSDF, cosine and MIS factor. Reservoir selection chooses one
candidate, then normalization recovers the proposal average before visibility.
Only the selected candidate needs a shadow ray. Selection and BSDF-hit source PDFs
must continue to agree. Emission is one-sided according to captured orientation.

`ptgi/integrator.glsl`: diffuse/glossy/dielectric/volume events in one loop, area
emission, medium stack, Beer-Lambert absorption, stochastic free flight and Russian
roulette. Individual switches alter lobes/path classes. Caustics are sampled
paths, not a separate projected caustic function.
Scattering events and dielectric interface events use separate counters. The loop
is bounded by their sum plus a terminal query. Russian roulette is based on actual
scattering depth, so entering/exiting clear water does not trigger early roulette.

`ptgi/context.glsl`, `temporal.glsl`, `denoise.glsl`, `resolve.glsl`: snapped
first-hit sample positions, history validation, separate moments, compact filtering
and full-resolution texture restore. Do not feed spatially filtered output back
into the unfiltered history: it causes accumulating blur.
Temporal clipping includes prior sample variance, preventing all-black local
samples from erasing accumulated caustic/source energy. Transmission reconstruction
uses its own strength and variance-based confidence, including camera-water
scattering; opaque specular keeps a compact footprint. Full-resolution primary
textures/emission are restored separately, while secondary textures can soften
with transmission filtering.

`materials.glsl`, `block.properties`: source identities, glass, water, metals and
optional powder emission. `water.glsl` supplies only optical wave normals.
`environment.glsl` supplies analytic incoming sky/sun radiance.
Kinds 25..28 retain small-source identity independently of cube emitters 3..7.
Their surface-radiance calibration is shared by direct sampling, source-hit paths,
visible emission and hierarchy weights. Torch stems are masked at actual UVs;
an unmasked capture record keeps a dark midpoint from deleting the flame entirely.

## References

- [Iris shadowcomp ordering](https://shaders.properties/current/reference/programs/shadow_comp/)
- [Iris rendering properties](https://github.com/IrisShaders/docs/blob/main/src/content/docs/current/Reference/Shaders.Properties/rendering.mdx)
- [Iris compute ordering](https://shaders.properties/current/reference/shadersproperties/ordering/)
- [Heitz, Sampling the GGX Distribution of Visible Normals](https://jcgt.org/published/0007/04/01/)
- [Karras, parallel BVH construction](https://research.nvidia.com/publication/2012-06_maximizing-parallelism-construction-bvhs-octrees-and-k-d-trees)

These are algorithm/interface references. The implementation and tests are
included; no claim is made that this pack implements every technique in them.

## Material and history contracts added in 0.6.3

`lib/fluid_boundary.glsl` uses `at_midBlock.xyz / 64` to recover block-local
position. This identifies physical water boundaries independently of Sodium's
inward/outward raster copies. Do not discard all back faces: the submitted side
may depend on camera and terrain bucket culling. Both copies are retained with
one physical outward direction. `trace.glsl` orients the scattering normal toward
the ray while keeping this physical outward direction for the medium stack.

`resolveMaterial` is shared by visible and captured materials. Native emission
comes from the block's own `at_midBlock.w`, not the neighbor lightmap. A captured
PBR word contains roughness/F0 in its low two bytes and half-float emission in
its high two bytes. Material kinds 29..34 represent ice, honey, slime, tinted
glass, held thin sheets and unmapped translucent terrain respectively. Froglights
use texture-colored emission class 8. Resource-pack PBR is still sampled per
triangle at capture; this release does not add secondary POM or normal maps.

| Target | Layout | Lifetime / precision |
| --- | --- | --- |
| colortex5 | packed roughness/F0/kind, emission, geometric normal, valid | full resolution, RGBA32F, cleared |
| colortex14 | optical normal, geometric normal, view depth, valid | full resolution, RGBA32F, cleared |
| colortex15 | packed tint, view depth, optical normal, valid | full resolution, RGBA32F, cleared |
| colortex6 | packed geometric/optical normals, view depth, validity | transport resolution, RGBA32F, cleared; composite2 writes |
| colortex9 | diffuse/specular missing-signal counters, material key, albedo key | transport resolution, RGBA32F, persistent |

Packed normals use two 12-bit octahedral coordinates in one exact float32
integer. Tint and material keys use three bytes. Metadata must never be stored
in RGBA16F or interpolated as colors. Selective alpha blending preserves the
other translucent layer; water writes zero alpha to glass metadata and vice versa.

History validates material and color in addition to depth and physical normal.
A missing-signal counter estimates expected arrivals using mean-squared over
second moment and compatible neighborhood support. Eight expected missing
arrivals discard stale channel history. A single black neighborhood cannot erase
rare accumulated caustics. This is a biased reconstruction heuristic, disabled
with temporal filtering; very rare contributions still require time to react.

## Clouds and water sampling in 0.6.4

`ptgi/cloud_medium.glsl` contains world-space 3D value-noise density, a vertical
layer envelope, slab intersection, optical-depth integration and sampled free
flight. Camera-relative ray points are translated by `cameraPosition` before
wind advection. Cloud functions return neutral results in dimensions without a
directional sky, when coverage is zero or when either cloud/volume switch is Off.

A finite midpoint quadrature constructs a piecewise-constant medium along each
ray. `ptCloudFreeFlight` inverts an exponential optical-depth variate within those
segments. `ptCloudTransmittance` integrates the density for direct connections.
The two quality budgets may differ; low budgets introduce integration error.
This is not exact unbiased delta tracking against an infinitely resolved density.
Both loops have fixed bounds; there are no rejection loops or full-screen extra
cloud raymarch passes.

In the integrator, independently sampled homogeneous and cloud free flights
compete for the nearest event before a surface. Cloud collisions receive cloud
single-scattering albedo and HG phase; air/water keep the isotropic phase.
Cloud survival is already in the collision probability, so it must not be
multiplied into continuation throughput a second time. Direct-light connections
use cloud transmittance, and subsequent rays can scatter again, reach sources
or escape to the environment. A confirmed geometry miss can extend the cloud
segment to Cloud Ray Distance; a hit or exhausted traversal cannot.

Visible emission normally bypasses stochastic reconstruction to retain texture
detail. If a camera segment crosses the cloud layer, `ptPrimaryEmission` returns
zero and the integrator evaluates that source after sampled cloud visibility.
This prevents unattenuated emitter artwork leaking through clouds. Primary
cloud segments cap temporal history with Cloud History Limit; no accurate
animated-volume motion vectors are claimed. `denoise.glsl` also reconstructs
stochastic cloud sky pixels; they must no longer take the old deterministic-sky
early return. Cloud Reconstruction Strength controls this spatial blend.

`render.glsl` multiplies paths only when the primary material is water or the
camera is underwater, and Water/Caustics are enabled. Every path is independent,
uses the same integrator and is divided by the actual sample count. This changes
variance and cost, not a second lighting term. Wave normals remain optical
perturbations on the captured mesh, not displaced fluid geometry.

Algorithm references: [PBRT volume integrators](https://pbr-book.org/4ed/Light_Transport_II_Volume_Rendering/Volume_Scattering_Integrators),
[PBRT phase functions](https://pbr-book.org/4ed/Volume_Scattering/Phase_Functions),
and [Iris rendering properties](https://shaders.properties/current/reference/shadersproperties/features/).

## Reconstruction and scheduling in 0.6.5

`shaders.properties` scales targets 2, 6, 8, 9, 11, 12 and 13 together. Raster
G-buffers and targets 5/14/15 remain full resolution. Every MRT in composite2
must have identical dimensions. Its output list is `2,8,12,11,13,9,6`; the new
cache is appended so the existing history output slots keep their meanings.

`context.glsl::ptTransportGuide` reads current-frame colortex6 plus colortex9.
The former has two 24-bit packed octahedral normals, depth and validity; the
latter already carries a material key and linear RGB key. Reconstruct view
position at the same full-resolution depth-texel center used by the integrator.
Do not call this cache accessor in composite1 or before composite2 updates it.
The original `ptGuide` still supplies exact full-resolution receiver data.
Guide RGB, roughness and F0 reuse the existing 8-bit history quantization;
packed records require exact RGBA32F and texelFetch, never color filtering.

`resolve.glsl` reconstructs diffuse irradiance and specular/transmission
separately using normal, depth and material compatibility. Fast uses four
bilinear taps. Detail uses the tensor product of four-point Lagrange weights at
actual snapped sample anchors. Fractional scales create nonuniform anchor
spacings: assuming uniform Catmull-Rom coordinates would introduce a repeating
error. Negative lobes are bounded to compatible local extrema. Small/invalid
weight sums fall back to a compatible nearest sample. Full-resolution albedo
and visible emitter artwork are restored after reconstruction. No filter can
recreate a thin object for which the transport grid has no matching sample.

`sharpen.glsl` reads the resolved image and its four axial neighbors. It compresses
HDR as c/(1+c), adds an adjustable unsharp term, clamps to local extrema and
inverts the compression. Relative residual variance suppresses the gain on noisy
lighting; local contrast also reduces it. The result stays within finite HDR
bounds. This is an original filter, not AMD RCAS. It has no temporal motion
vectors, frame generation or new light-transport term.

Scheduling removes composite3/4 with Spatial Reconstruction Off, composite4
alone with one spatial pass, and composite6 with sharpening Off or a diagnostic
view. Composite2 must ALWAYS run to update current guides and optional history.
Iris's normal buffer flips preserve the most recent preceding result when a
later pass is skipped. No filtered lighting is written into history targets.

`final.fsh` chooses a 3x3/5x5 bloom gather. The fast gather doubles sample spacing
and adjusts weights to retain the footprint. It is an approximation to the fine
lens kernel, not a physical caustic/illumination contribution.

The guide cache adds a transport-sized RGBA32F target. Shrinking PT resolution
reduces transport work/history storage; scene capture, radix build, full-resolution
G-buffers and final resolve remain at their prior sizes. The BVH still rebuilds
every frame. This release does not claim acceleration from RT cores or an AMD SDK.
