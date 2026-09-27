# Build notes — 0.6.5

The 2026-09-27 naming update applies LampPT throughout the package, including
source guards, English menu text, documentation, copyright label and ZIP name.
The version remains 0.6.5; rendering algorithms and quality defaults are unchanged.

Based on the previous 0.6.4 experimental release ZIP (514907 bytes), preserving the existing
world-space PT integrator, cloud medium, caustic guidance, geometry/material fixes
and all per-effect controls. Baseline SHA-256:

```text
717ee8985e6beaf06fb033b45f80d8ad6427b4acee23b56b6a658ff3b906363d
```

This release adds original PT upscaling, adaptive sharpening, shared guide data,
pass scheduling controls and a cheaper bloom gather. No AMD FSR/RCAS, NVIDIA DLSS,
frame-generation SDK or hardware RT backend is included. All source and comments
are English. Existing licensing is retained.

Reproduce with the Python/EGL tests in TEST_RESULTS.md, then build with:

```bash
python3 build.py /path/LampPT-v0.6.5-experimental.zip
```

The ZIP contains shaders/shaders.properties at its root, documentation, source,
test scripts and actual synthetic-render evidence. It is installed as a ZIP.
Reset saved shader options on update: scales, defaults and target formats changed.
Historical audit findings remain in AUDIT_RESOLUTION.md. They are not newly
measured Minecraft or NVIDIA results.
