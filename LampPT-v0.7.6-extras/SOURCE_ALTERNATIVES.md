# LampPT 0.7.5: replacement options

Review date: 2026-10-05. This is a source and licensing comparison, not a
benchmark or an implementation change. The renderer's executable code is
unchanged by this documentation update.

## What a 1:1 replacement means

The same interface, the same mathematical distribution, and bit-for-bit identical
output are different requirements. An independently sourced implementation can
perform the same job without producing the same random sequence or exact pixels.
Changing identifiers or rewriting the same expression is not evidence of a new,
independent origin. No drop-in replacement with verified bit-identical output
has been established by this review.

| Current component | Concrete alternative or retention option | Effect on compatibility and appearance |
| --- | --- | --- |
| `hash12` and `ptCloudHash` | Adapt the existing `ptHash` / lowbias32 integer mixer, whose upstream uses the Unlicense. A 2D/3D coordinate-to-seed mapping is also needed. | Same role as a deterministic noise source, but different dither values and cloud-density pattern. Test negative/large coordinates, spatial correlations and cloud appearance. Not a bit-identical substitution. |
| `ptHash` | Retain the current lowbias32 implementation and upstream Unlicense notice. | Its license is already explicit; replacing it merely to avoid an attribution entry has no established technical benefit. |
| ACES fitted tone curve | Retain Narkowicz's curve using the author's explicit CC0 option. | Preserves the current look. A different tone curve changes brightness/color response; no replacement is needed just to obtain stated permission. |
| `ptVisibleNormal` | Review and adapt `TrowbridgeReitzDistribution::Sample_wm` from the Apache-2.0-licensed PBRT v4 source. | It implements visible GGX sampling. Isotropic roughness, frame convention, PDF, numerical guards and grazing cases must be matched and tested. The same target distribution does not guarantee identical samples or performance. |
| `octEncode` / `octDecode` | Review and adapt `OctahedralVector` from PBRT v4's Apache-2.0-licensed source. | It represents the same class of normal encoding, but its 16-bit storage, rounding and signed-zero convention must be reconciled with LampPT's floating-point helpers and packing. Validate all producer/consumer paths and fold boundaries before claiming drop-in compatibility. |

The PBRT candidates are references for possible future replacements, not bundled
components. Their source headers explicitly name Apache-2.0. Importing/adapting
them would require retaining the applicable copyright/license notices, marking
changes and checking any relevant upstream NOTICE requirements. Do not copy a
license label onto the existing implementation without actually establishing its
source and applicable terms. The PBRT book's document license is separate from
the repository's software license.

## Action in this update

`shaders/THIRD_PARTY_LICENSES.txt` now centralizes the identified authors, affected
functions, source links, retained license text and verification status. README
and source comments point to it. `THIRD_PARTY_NOTICES.txt` is a compatibility
pointer for earlier links. Existing MIT and Unlicense text is preserved.

The Heitz example and the octahedral blog example remain credited references
with unverified exact code terms. The Hoskins original-page license verification
also remains open; a public port corroborates the retained MIT notice. Attribution
alone is not a substitute for permission where adapted code requires it. These
items should be resolved through authoritative evidence or documented replacements
before describing the project as fully cleared.

No shader algorithm, setting, project LICENSE.txt, release number, runtime ZIP or
extras ZIP was changed. The accompanying attribution patch contains only source
comments and documentation. It can be applied without replacing the owner's
separately updated project license.

## Sources inspected

- Chris Wellons, [hash-prospector / lowbias32](https://github.com/skeeto/hash-prospector),
  [Unlicense](https://github.com/skeeto/hash-prospector/blob/master/UNLICENSE).
- Krzysztof Narkowicz, [ACES Filmic Tone Mapping Curve and CC0/MIT offer](https://knarkowicz.wordpress.com/2016/01/06/aces-filmic-tone-mapping-curve/).
- Matt Pharr, Wenzel Jakob and Greg Humphreys, PBRT v4:
  [software license](https://github.com/mmp/pbrt-v4/blob/master/LICENSE.txt),
  [GGX source](https://github.com/mmp/pbrt-v4/blob/master/src/pbrt/util/scattering.h),
  [octahedral source](https://github.com/mmp/pbrt-v4/blob/master/src/pbrt/util/vecmath.h),
  [sampling explanation](https://pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory).
- Original-component evidence and access limitations are in
  [SOURCE_PROVENANCE_REVIEW.md](SOURCE_PROVENANCE_REVIEW.md).
