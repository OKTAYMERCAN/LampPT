# LampPT 0.7.5 — source provenance review

Review date: 2026-10-03. Reviewed snapshot: the local `LampPT-v075` source tree.
Documentation follow-up: 2026-10-05; renderer code and original findings unchanged.

**Result:** recognizable external helper implementations and formula adaptations
are present. It would be inaccurate to describe every line as independently
original. This review did not establish that the main renderer was copied from
another shaderpack. It also does not establish that all code is free of outside
claims or that attribution alone resolves every licensing question.

## Scope and method

The input shader directory contains 141 text files, 5,759 lines and 299,000 bytes,
including stage wrappers, settings, mappings and language files. The starting
runtime archive's SHA-256 is:

`7f5debe21a9a7ac9eb81766ecdc5cf94e5a90266d1f0c39c6c5d91d1333ac56b`

The review inventoried the runtime, searched shader and test sources for credits,
license headers and distinctive constants, and inspected the main material,
BVH, scattering, integration, cloud, temporal, denoising and resolve modules.
Selected distinctive snippets were compared with public author repositories,
papers and example code. This was a targeted manual review, not a database-wide
clone detector. Tests and historical documentation received a metadata/reference
scan, not a complete independent provenance audit of every test line.

Generation logs, training-data provenance and a complete commit history were
not available for tracing the origin of generated snippets. Earlier releases,
closed/proprietary shader code, patents, trademarks and resource packs loaded by
the game are outside this review. Similarities establish correspondence, not
which website, intermediary or model output supplied the code.

## Concrete implementation correspondences

| ID | Local component | Finding | License evidence / action |
| --- | --- | --- | --- |
| P1 | `common.glsl::hash12` | Same three-step body as David Hoskins' **Hash without Sine**: `0.1031`, `yzx + 33.33`, final product/fraction. | Credit and MIT notice added. Original Shadertoy access failed; original-grant verification remains open. |
| P2 | `cloud_medium.glsl::ptCloudHash` | Closely related Hoskins construction using a 3D input and the `hash12` mixing pattern. Not an exact match to Hoskins' `hash13`. | Covered by the same component notice, explicitly described as a variant. |
| P3 | `bsdf.glsl::ptHash` | Same shifts and multipliers as hash-prospector's **lowbias32**; GLSL syntax and an inlined final XOR do not change the operation sequence. | Credit to Chris Wellons; upstream Unlicense inspected and preserved. This is not the newer parameter set credited to TheIronBorn in the same README. |
| P4 | `final.fsh::toneMap`, `TONEMAP == 1` | Same fitted rational curve and five coefficients as Narkowicz's **ACES Filmic Tone Mapping Curve**. | Author explicitly offers CC0 or MIT; CC0 selected for this component and credit added. |
| P5 | `bsdf.glsl::ptVisibleNormal` | Close adaptation of Heitz's `sampleGGXVNDF`: stretched view, tangent frame, warped disk, hemisphere reprojection and unstretch. | Existing short Heitz comment expanded. Sample header contains no license; exact code terms remain unverified. |
| P6 | `translucent_data.glsl::octEncode` / `octDecode` | Formula correspondence with Narkowicz's octahedral encoding post, whose optimized decode credits Rune Stubbe. GLSL conditions and packing differ. | Source reference added. No explicit code-license statement found on that page; no license inferred from an unrelated post. |

Primary references:

- Hoskins: <https://www.shadertoy.com/view/4djSRW>. Attribution is also recorded
  in Jarzynski and Olano's [Hash Functions for GPU Rendering](https://jcgt.org/published/0009/03/02/paper.pdf).
  A [WGSL port published by David A. Roberts](https://gist.github.com/davidar/5f9677a0ccfbd63d7a8657ad9af3a856)
  preserves Hoskins' copyright and MIT notice. That is corroborating evidence,
  not a substitute for direct original-grant verification; the port itself was
  not imported into LampPT.
- Wellons: [repository and matching function](https://github.com/skeeto/hash-prospector),
  [license](https://github.com/skeeto/hash-prospector/blob/master/UNLICENSE).
- Narkowicz: [tone curve and license offer](https://knarkowicz.wordpress.com/2016/01/06/aces-filmic-tone-mapping-curve/).
- Heitz: [paper](https://jcgt.org/published/0007/04/01/paper.pdf),
  [sample header](https://jcgt.org/published/0007/04/01/sampleGGXVNDF.h),
  [publisher code policy](https://www.jcgt.org/write.html).
- Narkowicz/Stubbe: [encoding post](https://knarkowicz.wordpress.com/2014/04/16/octahedron-normal-vector-encoding/).

## Algorithm similarities, distinguished from established code origin

`scene/build.glsl` implements a Morton-prefix parallel BVH with the recognizable
Karras construction. Its bit-spreading masks match a widespread short Morton
pattern. Giesen's published `Part1By2` uses the same construction with differences
in operators and one mask. This is insufficient to identify one exclusive source
or to assign a particular repository's license to the whole BVH implementation.
The algorithm references are credited in README and source comments.

`temporal.glsl` and `denoise.glsl` contain temporal moments, geometry validation
and variance-guided a-trous filtering. These are related to published SVGF
techniques; a wholesale Falcor/NRD implementation match was not established.
Fresnel, Snell, Beer-Lambert, cosine sampling, Henyey-Greenstein, triangle/slab
intersection, barycentric coordinates and sRGB equations are standard techniques;
their use alone does not establish copying from a particular shaderpack.

The runtime inventory contains no vendored NRD, FSR or DLSS SDK, external shader
library bundle, or texture asset bundle. Referencing Iris interfaces, block IDs
or resource-pack material conventions is not the same as bundling their code.
Development tests import external packages including NumPy and Pillow; imported
dependencies are not copied into the runtime archive.

Earlier release notes mention SEUS HRR's public descriptions and NRD documentation.
Those statements explain recorded references, but cannot prove either copying
or independent authorship. No proprietary SEUS source was accessed for this review.

## Changes made and remaining work

- Added English README credits, component-level code comments, this report and
  `shaders/THIRD_PARTY_LICENSES.txt`. Corrected the source guide's classification
  of the Heitz routine as only a general reference.
- Preserved the Hoskins MIT notice and hash-prospector Unlicense text. Marked
  unresolved evidence explicitly instead of assigning invented license labels.
- Added related Karras, Giesen, SVGF, PBRT and Iris references. These do not claim
  implementation provenance where none was established.
- Confirmed that all pre-existing shader code tokens and configuration bytes
  remain unchanged; the shader edits are comments only. ZIP integrity was checked.
  No rendering or performance improvement is claimed by this attribution update.

The highest-priority follow-ups are exact licensing confirmation for the Heitz
sample, direct confirmation of Hoskins' original notice, and clarification of
the octahedral sample's terms if that implementation is retained as adapted code.
Options include obtaining authoritative permission/license evidence or reviewing
a replacement implementation with a documented origin. Changing names, comments
or whitespace would not resolve provenance.

The included notices do not by themselves turn these open items into a licensing
clearance. The project's custom license must not be presented as overriding
upstream rights. No author was contacted and no release was published by this
review. The supplied patch omits `LICENSE.txt`, allowing the owner's separately
updated license to remain in place.

## 2026-10-05 follow-up

Consolidated the notice under `shaders/THIRD_PARTY_LICENSES.txt`, retaining the
earlier filename as a pointer. Added a clear status summary so unverified code
terms are not presented as confirmed permissions. README now explains that the
previously built runtime ZIP predates the notice and needs the patch/rebuild.

`SOURCE_ALTERNATIVES.md` documents concrete replacement candidates and the
difference between equivalent purpose and identical output. PBRT v4's GGX and
octahedral implementations have explicit Apache-2.0 source headers; they were
inspected as alternatives only. They have not been imported into LampPT, and
their license does not retroactively clear the current implementations. The
current hash-prospector and ACES components already have explicit upstream terms.
