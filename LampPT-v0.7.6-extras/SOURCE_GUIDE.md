## 0.7.6 optical reconstruction and sampling

The first surface is still rasterized and all lighting still comes from the
world-space path integrator. No screen-color transparency fallback is added.

`ptOpticalData` piggybacks on the existing path's first opaque receiver. It
contains world normal, diffuse receiver modulation (white for emissive/glossy
receivers) and total path length; -1 is environment and 0 is unavailable.
Optical `colortex12.rgb`, formerly unused diffuse history, now retains that
secondary guide. The texture must be RGBA32F: packed 24-bit values are not safe
in RGBA16F. Alpha remains the history count. Ordinary diffuse pixels keep their
previous meaning. Metadata must never feed diffuse radiance or spatial history
feedback. The buffer grows by 8 bytes per base-grid pixel per ping-pong image.

For clear non-water interfaces, `temporal.glsl` constructs a virtual image point along the original camera ray
using path length. This fixes planar/thin-sheet parallax and is approximate for
other refraction. It validates secondary normal and virtual depth and remodulates
compatible history with the current receiver texture. Missing/incompatible guides
use the short optical response path. `frameTime` bounds moving optical history
in seconds; stationary water and glass retain their independent frame limits.
`denoise.glsl` demodulates glass diffuse texture, uses at most step 1 and 2,
then remodulates it. Stationary glass accumulates reflection/transmission mixtures even when a
random path changes its secondary guide. Water retains its previous wave/volume
history and wider secondary-guided filter; the new compact glass policy must
not be applied to random water-scattering events. Reflection, emission and
volume mixtures can still be noisy.

`bsdf.glsl` randomizes one-dimensional eight-frame strata with per-dimension
bit permutations and jitter. `ptSeedFrame` is shared by production component,
merge-repair and reference paths. These sampling changes add arithmetic, not
rays, buffers or a second integrator call. They do not guarantee a given FPS or
remove disocclusion noise. The option can restore white-noise sampling.

`final.fsh` offers luminance tone fitting followed by bounded display-gamut
compression. It reuses the existing credited CC0 fitted curve; the project adds
the luminance/gamut wrapper. The old operator remains selectable. This affects
display color, not scene radiance, cloud coverage or physical light transport.

The following older sections describe the previous release history and must be
read with the current buffer contract above.

# Source guide — 0.7.3

## Current 0.7.3 optical reconstruction

PT_OPTICAL_DETAIL enables selective base-grid tracing for dielectric first hits
with roughness below 0.08. With HRR_REFLECTIONS enabled, component.glsl skips their
coarse surface estimates and merge.glsl marks the optical component for its
existing single repair-integrator call site. The bounded sample loop respects
PT_SAMPLES and PT_WATER_SAMPLES. Shared surface paths still work; mixed grids and
HRR Off have separate verified routes. This adds optical ray pixels, not a
second lighting renderer. Opaque tracing budgets remain unchanged.

Existing intersections fill ptOpticalData with packed receiver world normal,
packed linear receiver albedo and accumulated optical path length. The first
opaque receiver is recorded only before an opaque/volume scattering event.
An environment escape is encoded with distance -1 and ray direction; unavailable
guidance is zero. A representative sample's guide is retained when multiple
samples are averaged. It is spatial guidance, not exact secondary reprojection.

For eligible optical pixels, colortex6 RGB now holds this secondary payload; A
retains the primary packed material. ptCachedGeometry detects that material and
fetches the exact primary guide from raster inputs instead. All opaque cache
records retain their original layout. The reflection compute guide carries the
same payload when HRR is Off; coarse skipped optical pixels are repaired in merge.
Temporal copies colortex6 unchanged rather than replacing its secondary data.
RGBA32F remains required for exact packed values. No new target is allocated.

The spatial filter combines primary compatibility with receiver color, normal
and relative optical-distance checks. This distinguishes objects behind a flat
pane and preserves colored refracted patterns. Missing/scattered guides use one
compact stage. PT_OPTICAL_FILTER scales smooth-interface reconstruction; opaque
and frosted signals retain their ordinary filtering. The first-stage recurrent
history from 0.7.1 still excludes optical signals. No scene colors are fetched to
fake refraction, and no extra ray is traced just to produce a guide.

GLASS_ROUGHNESS now defaults to 0.001 rather than 0.04. Both new controls have
English tooltips, all presets control identical keys, and the pack exposes 140
options. The existing finite scene, perturbed flat wave geometry and temporal
bias limitations remain. Full data-flow sections below have this optical-cache
exception; older release-specific sections describe historical behavior.

## Retained 0.7.1 changes

`ptgi/integrator.glsl` samples homogeneous free flight at scalar sigmaS, not
max(sigmaA + sigmaS). The probability of survival supplies exp(-sigmaS * d),
while throughput explicitly multiplies exp(-sigmaA * d). A homogeneous collision
therefore has no sigmaS/majorant compensation. Independent cloud free flight still
competes for the first event and cloud collisions retain their single-scattering
albedo. Direct visibility connections and deterministic primary surface/emission
partitions still use full extinction. This removes the old exponentially large
blue/green compensation while retaining the transport expectation.

`composite3` defines PT_FIRST_FILTER and writes MRT 2,8,12,11. Later spatial stages
write only 2,8. The first stage copies history before all early returns, then
optionally mixes a variance-dependent PT_HISTORY_STABILIZATION fraction of its
compact result into diffuse/rough opaque history RGB. History age and raw moments
are unchanged; transmitting and cloud specular signals are excluded. This is
biased recurrent reconstruction, not additional samples. Two existing history
attachments are written; no extra image, render pass or ray query is allocated.
Do not feed later wide filter outputs into history.

`temporal.glsl` stores a packed 24-bit world optical normal in colortex13.B for
dielectric first hits. Their diffuse component is zero, so its second-moment slot
is unused. Other pixels retain the diffuse second moment. RG still stores the
physical world normal and A negative view depth. Exact RGBA32F is required.
WATER_HISTORY caps optical averaging; changing optical normals lower it toward
two frames without discarding compatible physical-plane history. Smooth-interface
spatial tap spacing is capped at two base pixels to avoid the old step-8 blur.

`water.glsl` adds three adjustable ripple slopes under WAVE_DETAIL. Primary
surface normals, secondary dielectric interactions and caustic guidance evaluate
the same function. No mesh displacement or screen-color warp is added. Lower
absorption/scattering and higher blue transmission are explicit new material
defaults, independent of the medium-sampling correction. Trace/sample budgets
remain as in 0.7.0; this release adds three English controls (133 total).

## Retained 0.7.0 changes

`lib/ptgi/temporal.glsl` reconstructs previous tap positions at the actual snapped
full-resolution anchors. Perspective projection scale and off-axis offsets are
included. Two signed point-to-plane errors reject displaced surfaces while allowing
large view-depth differences along one grazing surface. Physical-normal and BSDF
keys remain; diffuse primary albedo changes do not invalidate irradiance.

`PT_MOTION_STABILIZATION` raises the moving specular averaging cap from eight
up to 32 for rough, non-dielectric surfaces. Smooth speed transitions avoid the
old abrupt cap change. Sharp optics retain a short cap. No extra sampling pass
is introduced. Secondary reflection content still lacks hit-motion vectors.

Sky reprojection uses a vector (w=0) with rotation only. The reactive buffer B key
is negative for non-surface validity (-1 sky, -3 unlit) and a packed material for
surfaces. Infinite sky skips finite-plane validation. Geometry history layout is
otherwise unchanged. Camera cuts, material changes and displaced surfaces retain
history rejection.

`settings.glsl`, `shadow_settings.glsl` and `shaders.properties` define the new
four presets. All have identical controlled key sets. 25% base lighting has
0.125/0.250 component image scales and matching `composite1*.csh` dispatches.
No temporal/spatial-filter pass, scene buffer or per-ray BVH stack was added.
Current defaults are in PERFORMANCE.md; historical sections below describe the
retained architecture, not current profile budgets.


## Retained 0.6.9 execution changes

`PT_SHARED_PATHS` derives `LAMPPT_SHARED_SURFACE` only when Shadows/GI/Reflections
HRR flags agree. `composite1.csh` then writes diffuse and specular images together;
its `_a`/`_b` kernels are empty. `ptIntegrateComponent(...,5)` evaluates the full
primary BSDF, one continuation PDF, and both radiance outputs. Primary camera
medium is integrated deterministically here; component 3 supplies its separate
scattering term. Different HRR grids or Shared Surface Paths Off use 0..3.

The merge omits the inactive GI image. One pending-mask call site repairs either
or both shared outputs without retracing each. Reflections/GI toggles still act
inside the estimator; no screen-space or radiance-cache term is introduced.

`ptPackGuide` writes current geometry/material to colortex6 during composite1.
Temporal statistics use `ptCachedGeometry` before writing their histories.
`ptTransportGuide` adds a tint key from colortex9 only for metallic/transmitting
surfaces, after composite2. This ordering matters when reproducing isolated passes.
Tests that inject raw lighting call the same production guide packer explicitly.

In 0.6.9 temporal means were unfiltered; 0.7.1 optionally feeds back only its
first compact filter as described above. The nine-sample HRR statistics supply
variance bootstrap at all history ages; the denoiser's second 3x3 gather is gone.
Med uses four 3x3 stages (steps 1/2/4/8) and History 64. Diffuse/specular share a
geometry weight where their sample locations agree. View-dependent Fresnel and
albedo estimate BSDF lobe probability in both sampling and PDF evaluation.

IOR/absorption/scattering arrays have `PT_TRANSMISSION_DEPTH+1` entries. An
interface event can push at most one entry, so the event budget proves this bound.
The earlier private BVH stack remains removed. Cache layout below is current;
versioned sections document the preceding implementation.


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
5. `composite1.csh`, `_a`, `_b`, `_c` write primary diffuse direct,
   diffuse continuation, reflective/transmitted, and primary-volume/sky radiance
   respectively, each with a packed guide. Their eight custom images have
   independently selected dimensions. Each invocation bounds-checks imageSize.
   `composite1.fsh` reconstructs these onto the common base grid; incompatible
   silhouettes receive a fresh base-grid path instead of borrowed wall lighting.
6. `composite2` reprojects history and updates independent diffuse/specular
   moments, reactive keys and current guides. This pass always runs.
   `composite3..6` are selectable a-trous steps 1, 2, 4, 8.
7. `composite7` restores full-resolution primary albedo and emitter artwork;
   `composite8` optionally sharpens. `final` applies display response and bloom.
   No additive Hybrid lighting target is produced.

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

`lib/scene/trace.glsl` uses stackless near-first AABB traversal with the existing
`sceneParents` links. `node` and `previous` distinguish first entry from returning
to a parent. Child order is computed against the ORIGINAL ray limit, so a closer
hit cannot swap near/far children during backtracking. Current closest distance
still prunes unreachable children. Only first entries consume Traversal Budget;
a separate bound of twice that budget plus one limits all transitions. There is
no private 64-element traversal array, recursive call or per-ray scratch buffer. It computes reciprocal ray directions once and explicitly handles
parallel axes before vector slab tests. Hits use Moller-Trumbore barycentrics, UV alpha tests, outward normals
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
first-hit sample positions, history validation, separate moments, variance-guided filtering
and full-resolution texture restore. Only the bounded, optional first-stage
feedback above may modify history RGB; wider recursive filtering accumulates blur.
Temporal history is no longer RGB-clipped with a luminance-only bound. The
missing-signal test uses a 3x3 stencil spaced four base pixels apart when any HRR
component is active, avoiding overlapping source footprints. The stencil shifts inward
at borders so it keeps distinct observations; tiny targets skip unavailable taps. Transmission reconstruction
uses its own strength and variance-based confidence, including camera-water
scattering; rough opaque specular also uses widening a-trous spacing. Sharp
mirrors keep the compact footprint to retain secondary detail. Full-resolution primary
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

These references include algorithms and interfaces. Heitz's visible-normal
routine also has a close implementation correspondence, documented in the
README credits, shaders/THIRD_PARTY_LICENSES.txt and SOURCE_PROVENANCE_REVIEW.md.
The source review distinguishes those correspondences from general techniques
and records unresolved licensing evidence. No claim is made that this pack
implements every technique in these references.

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
| colortex6 | packed geometric/optical normals, signed depth/validity, packed material | transport resolution, RGBA32F; composite1 writes, composite2 refreshes |
| colortex9 | diffuse/specular missing-signal counters, material key, albedo key | transport resolution, RGBA32F, persistent |

Packed normals use two 12-bit octahedral coordinates in one exact float32
integer. Tint and material keys use three bytes. Metadata must never be stored
in RGBA16F or interpolated as colors. Selective alpha blending preserves the
other translucent layer; water writes zero alpha to glass metadata and vice versa.

History validates material, depth and physical normal. Color equality is
required for metals and transmitting materials; diffuse dielectric irradiance
is independent of the current primary albedo texture.
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

Visible emission bypasses stochastic reconstruction to retain texture detail.
`ptPrimaryEmission` multiplies it by homogeneous and numerical cloud camera
transmittance, returning immediately for nonemissive receivers. Primary-volume
paths include emission only after a real scattering event. This partitions the
camera integral without double-counting the straight surface contribution.
Cloud segments still limit temporal history; accurate cloud motion vectors are
not available.

`component.glsl` applies the water camera-sample multiplier independently to
active components. `render.glsl` retains the old monolithic estimator only as a
regression reference. Production dispatches use `ptIntegrateComponent` instead.
Primary diffuse/specular lobe selection affects BSDF evaluation and PDFs only
at the first surface. Secondary interactions restore the full BSDF. Direct
primary diffuse NEE and diffuse continuation have complementary MIS weights.
Primary dielectric paths belong to the reflection/transmission component;
primary sky and medium scattering belong to the cloud/volume component.

Algorithm references: [PBRT volume integrators](https://pbr-book.org/4ed/Light_Transport_II_Volume_Rendering/Volume_Scattering_Integrators),
[PBRT phase functions](https://pbr-book.org/4ed/Volume_Scattering/Phase_Functions),
and [Iris rendering properties](https://shaders.properties/current/reference/shadersproperties/features/).

## Reconstruction and scheduling in 0.6.6

`shaders.properties` scales targets 2, 6, 8, 9, 11, 12 and 13 together. Raster
G-buffers and targets 5/14/15 remain full resolution. Every MRT in composite2
must have identical dimensions. Its output list is `2,8,12,11,13,9,6`; the new
cache is appended so the existing history output slots keep their meanings.

`context.glsl::ptTransportGuide` reads current-frame colortex6 plus colortex9.
In 0.6.9 the former has packed octahedral normals, signed depth/validity and
material; the latter carries the current linear RGB key used for tinted optics. Reconstruct view
position at the same full-resolution depth-texel center used by the integrator.
Composite1 writes the geometry cache before temporal statistics read it.
Only call the color-aware accessor after composite2 refreshes the tint key.
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

Scheduling removes composite3..6 with Spatial Denoiser Off, excludes passes
beyond Spatial Filter Passes, and removes composite8 with sharpening Off or
a diagnostic view. Composite2 must ALWAYS run to update current guides and optional history.
Iris's normal buffer flips preserve the most recent preceding result when a
later pass is skipped. Since 0.7.1 only composite3 may update existing history
targets with its optional compact feedback; disabled filtering leaves raw history.

`final.fsh` chooses a 3x3/5x5 bloom gather. The fast gather doubles sample spacing
and adjusts weights to retain the footprint. It is an approximation to the fine
lens kernel, not a physical caustic/illumination contribution.

The guide cache adds a transport-sized RGBA32F target. Shrinking PT resolution
reduces transport work/history storage; scene capture, radix build, full-resolution
G-buffers and final resolve remain at their prior sizes. The BVH still rebuilds
every frame. This release does not claim acceleration from RT cores or an AMD SDK.

## Independent HRR image contract

For each of Direct, GI, Reflect and Cloud, `pt{Name}Image` stores RGB radiance
and a packed linear primary albedo in A. `pt{Name}GuideImage` stores packed
geometric normal, packed shading normal, signed depth/validity and packed
material. These are RGBA32F records, not interpolated color textures. Positive
depth means a surface; negative -1 means sky and -3 means an unlit raster input.
Sample anchors are snapped to the actual full-resolution depth texel centers.

Property image sizes and compute workGroupsRender constants use the same eight
literal base scales and independent HRR branches. HRR halves each component axis
before allocation; the merge uses actual textureSize, including odd dimensions.
Four-tap guided reconstruction rejects different surfaces and optical materials.
An unsupported coarse silhouette triggers one real path at the base-grid guide.
This can reduce savings in complex scenes; it does not add a screen-space fallback.

After merging, diffuse and specular/volume histories share the base grid. These
are not four separate temporal histories. Reconstruction introduces bias and
correlation; variance is an estimate, not an exact uncertainty bound. Increasing
filter radius/passes trades secondary-image detail for reduced visible noise.
No display-resolution diffuse texture is filtered by these lighting passes.

## Historical C5041 fix in 0.6.7

Previously, `ptMergeComponent` contained a fallback integrator call and was
invoked separately for four samplers. Shader inlining could expand private
traversal arrays at each call site. The NVIDIA error named those `@stack...`
resources. The stackless traversal removes that resource from every runtime
program, including the four compute programs and fragment repair.

Reconstruction now returns RGB plus a missing-support flag. The fragment merges
supported values, builds a four-bit pending mask and processes it in ascending
bit order with ONE `ptIntegrateComponent` call site. Clearing the lowest set bit
bounds the loop to four iterations. Per-component seeds are unchanged. This
retains exact traced repair on unsupported thin surfaces, with no sky/color fill
or discarded fallback components. No extra pass or render image was added.

The medium IOR/absorption arrays remain: those small arrays have a different
purpose and were not the `stack` named in the reported error. Driver-specific
resource allocation cannot be certified by the Mesa checks alone.

## Historical sparse colored-sample reconstruction in 0.6.8

The former eight-neighbor median truncation and history RGB range clipping were
removed from `temporal.glsl`. Temporal history stores the raw accumulated signal
and moments; spatial filtering never feeds back into these means. The optional
`PT_OUTLIER_FILTER` key is retained for settings compatibility, but its English
label is now Sparse Sample Reconstruction. It adds a geometry-guided 3x3 variance
gather only to filterStep 1. Later a-trous passes consume propagated variance;
there are no new ray queries, history targets or full-screen passes.

This is a biased finite-neighborhood reconstruction, not an unbiased/noise-free
solution or NVIDIA NRD integration. Luminance variance is still approximate;
colorful rare paths, water and moving reflective content remain difficult.
The core integrator, source sampler, BSDF, GI switch and final albedo restoration
are byte-identical to 0.6.7. See the GI propagation fixture for direct evidence that
indirect radiance reaches `composite7` without an invented ambient term.

## 0.7.3 lighting changes

`lib/ptgi/hand_light.glsl` implements the two optional delta-position hand
emitters. `item.properties` maps item colors separately from placed block states.
`lib/materials.glsl` contains extended source families (kinds 35..45);
`block.properties` restricts switchable sources to active states. Native block
emission from `at_midBlock.w` remains the fallback for unmapped terrain.

`ptDielectricReflection` evaluates f*cos and the matching visible-GGX branch PDF.
The integrator samples the finite sun disk at dielectric vertices and tracks a
separate solar MIS PDF, so sky and mesh-emitter weights remain unchanged.
Conditional primary cloud collisions carry their event probability; primary
surface transmission already carries the complementary deterministic survival.
`ptVolumeGuideWeight` avoids using background material/normal edges as cloud edges.
