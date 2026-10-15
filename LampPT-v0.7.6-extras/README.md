# LampPT 0.7.6 experimental

Owner: OKTAY MERCAN. Contact and license terms: see LICENSE.txt.

Install only `LampPT-v0.7.6-experimental.zip` into `.minecraft/shaderpacks/`.
The runtime contains only `shaders/` (including `THIRD_PARTY_LICENSES.txt`) and
`LICENSE.txt`. Documentation, test tools and evidence are in the separate extras
ZIP; extract both into one directory to recreate the development source.

## Changes in 0.7.6

- Clear-glass history uses traced virtual image distance and validates the
  previous secondary scene instead of attaching its image to the pane depth.
  Water/glass motion history also has a time limit, so low FPS does not turn a
  short frame budget into a long visible trail.
- Texture-aware glass reconstruction removes diffuse receiver modulation
  before filtering and restores the current texture afterward. Guided smooth
  glass uses two compact passes, with no wide step-4/8 image blur.
- Stationary glass keeps accumulating stochastic reflection/transmission
  mixtures; random branch changes are not mistaken for camera movement. Water
  retains its existing wave/volume history and spatial reconstruction policy.
- Randomized temporal strata spread sample coordinates across eight frames
  without adding traced paths. This reduces sampling variance in controlled
  tests; rare paths and newly exposed/moving surfaces still contain noise.
- New Luminance Fit display option preserves RGB ratios before gamut fitting.
  The previous per-channel look is available under Post / Tone Mapping.
- Added English descriptions for Glass History Limit, Optical Motion Response
  and Temporal Sample Stratification. Presets retain their tracing budgets;
  Normal Maps, POM and powder emission remain off by default.

Select MED to start. The relevant controls are Noise / Temporal Sample
Stratification, Noise / Optical Motion Response, Noise / Clear Interface Filter,
Glass / Glass History Limit and Post / Tone Mapping. Motion Response defaults
to 0.20 seconds; 0.10 reacts faster but reveals more grain.

This remains an experimental finite-scene renderer. Virtual-image reprojection
is exact only for ideal planar mirror/thin straight-sheet cases and approximate
for thick or curved refraction. Mixed reflection/transmission, waves and volume
scattering remain difficult. Clear optics still trace at the chosen Lighting
Resolution; low-resolution tracing cannot reproduce every full-resolution texel.
No noise-free image or Minecraft FPS improvement is promised. See TEST_RESULTS.md
for controlled test results and limits.

## Requirements and support targets

- Minecraft Java Edition 26.2; Iris 1.11.4 minimum support target for this release.
  Compatible newer builds may work; older/newer combinations are not validated.
- Install the Sodium version matching that Iris/game build.
- OpenGL 4.3+ with compute shaders, SSBOs and required Iris feature flags.
- Windows/Linux graphics driver supporting those capabilities. Native macOS
  OpenGL and OptiFine are unsupported. Hardware RT cores are not used.
- RTX 3060/4060 class is the intended performance target, not a measured minimum
  or FPS guarantee. Start with Medium; choose Low if needed.

## PBR and tracing limits

Choose a profile before enabling normal maps/POM; every preset defaults them Off.
Select labPBR/oldPBR to match the resource pack. POM requires height in normal-map
alpha and changes the first-visible-surface UVs, not captured geometric silhouettes.
Secondary opaque ray hits read normal and specular maps. Low-resolution transport
can soften fine normal highlights. The Debug menu includes normal, roughness,
height and albedo/POM views for troubleshooting.

Lighting uses bounded world-space paths over captured terrain triangles, with
raster first visibility. Capture distance/capacity and traversal budgets are finite.
Unsupported geometry, incomplete capture, water/glass artifacts and residual noise
remain possible. Offscreen tests are not Minecraft/Iris/NVIDIA runtime validation.
See TEST_RESULTS.md in the extras archive for scope and historical evidence.

## Build

Edit release.json (version, short changelog, three visible change lines), then:

```sh
python3 build.py LampPT-v0.7.6-experimental.zip --extras LampPT-v0.7.6-extras.zip
```

The build checks ZIP integrity, runtime-only contents and unchanged license bytes.
The provided custom license describes the project terms. Identified third-party
components retain their applicable upstream terms; see the notices below.
Historical releases may have been distributed with different terms; see
LICENSE_REVIEW.md in extras.

## Credits and source provenance

LampPT is maintained by **OKTAY MERCAN** and was developed with AI assistance.
A source review of version 0.7.5 identified the following small implementations
and formula correspondences. AI assistance is not evidence of independent origin.
These credits identify public sources, not the route by which generated code
entered the project, and do not imply endorsement by the credited authors.

| Component | Credit / public source | Relationship and license evidence |
| --- | --- | --- |
| `hash12` in `lib/common.glsl`; `ptCloudHash` in `lib/ptgi/cloud_medium.glsl` | David Hoskins, [Hash without Sine](https://www.shadertoy.com/view/4djSRW) (2014) | Matching hash body and a related 3D variant. MIT notice preserved; original-page access was unavailable during review. |
| `ptHash` in `lib/ptgi/bsdf.glsl` | Chris Wellons, [hash-prospector / lowbias32](https://github.com/skeeto/hash-prospector) | Same shifts, multipliers and operation order, expressed in GLSL. Upstream: Unlicense. |
| `TONEMAP == 1/2` in `final.fsh` | Krzysztof Narkowicz, [ACES Filmic Tone Mapping Curve](https://knarkowicz.wordpress.com/2016/01/06/aces-filmic-tone-mapping-curve/) (2016) | Same fitted equation and coefficients; 0.7.6 also applies the fit to luminance. Author offers CC0 or MIT; the CC0 option is used for this component. |
| `ptVisibleNormal` in `lib/ptgi/bsdf.glsl` | Eric Heitz, [Sampling the GGX Distribution of Visible Normals](https://jcgt.org/published/0007/04/01/) (2018) | Isotropic/world-frame adaptation of the published routine. The downloaded sample has no explicit license header; exact code-license verification remains open. |
| `octEncode` / `octDecode` in `lib/translucent_data.glsl` | Krzysztof Narkowicz, [Octahedron normal vector encoding](https://knarkowicz.wordpress.com/2014/04/16/octahedron-normal-vector-encoding/); optimized decode credited there to Rune Stubbe | Corresponding compact formulas, expressed with GLSL vector conditions. The inspected page does not specify a code license. |

See [third-party licenses and credits](shaders/THIRD_PARTY_LICENSES.txt) for retained notices and
verification limits, and [the source review](SOURCE_PROVENANCE_REVIEW.md) in extras
for evidence and unresolved items. Attribution alone does not establish permission
where the applicable code license remains unclear. This review is not a legal
clearance, an exhaustive similarity scan, or a certification of original authorship.

[Replacement options](SOURCE_ALTERNATIVES.md) distinguish equivalent purpose
from identical output. They include the existing Unlicense hash and separately
licensed PBRT implementations as candidates; no candidate was imported by the
attribution update. A candidate's license does not clear the current code.

### Algorithm and interface references

The following explain recognizable techniques or interfaces. They are separate
from the implementation correspondences above and do not establish code copying:

- Tero Karras, [parallel BVH construction](https://research.nvidia.com/publication/2012-06_maximizing-parallelism-construction-bvhs-octrees-and-k-d-trees) (2012): Morton-prefix hierarchy construction in `lib/scene/build.glsl`.
- Fabian Giesen, [Decoding Morton Codes](https://fgiesen.wordpress.com/2009/12/13/decoding-morton-codes/) (2009): the classic bit-spreading construction; similar short routines occur in many projects, so the immediate source cannot be identified from this pattern alone.
- Christoph Schied et al., [Spatiotemporal Variance-Guided Filtering](https://research.nvidia.com/publication/2017-07_spatiotemporal-variance-guided-filtering-real-time-reconstruction-path-traced) (2017): related temporal moments and variance-guided wavelet reconstruction techniques.
- [Physically Based Rendering, fourth edition](https://pbr-book.org/4ed/Light_Transport_II_Volume_Rendering/Volume_Scattering_Integrators): background on Monte Carlo light transport and volume scattering.
- [Iris shader interface documentation](https://shaders.properties/current/): shader stages, resources and loader conventions; Iris/Sodium are external dependencies, not bundled code.

The reviewed runtime contains no vendored NRD, FSR or DLSS SDK. Earlier notes cite
SEUS HRR's public descriptions and NRD documentation as references; that citation
history is not proof of implementation provenance. No large renderer-code match
to another shaderpack was established in this bounded review, and proprietary
shader sources were not examined.
