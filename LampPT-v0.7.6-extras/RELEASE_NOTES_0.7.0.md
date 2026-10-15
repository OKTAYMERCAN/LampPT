# LampPT 0.7.0 experimental

Repairs motion-related history rejection and replaces the four performance presets.
The world-space mesh PT integrator, shared paths and NVIDIA C5041 mitigation remain.

- Reprojection validates current and previous surface planes instead of requiring
  nearby pixels to have equal view depth. This fixes false history rejection on
  grazing floors during translation and rotation. Normal/material checks remain.
- Rough Reflection Stability keeps a roughness-dependent moving history budget,
  transitioning smoothly from stationary accumulation. Mirrors/glass keep short
  history; no secondary-hit motion-vector system is claimed. The option is On in
  every profile, with an English tooltip explaining the possible trail tradeoff.
- Infinite sky history ignores camera translation, uses rotation, and has its own
  validity key so a newly visible surface cannot inherit sky lighting.
- Base resolution becomes 25/33/40/50%, HRR On everywhere, one sample and one
  water-path multiplier everywhere. Scattering events become 2/2/3/4. Ultra no
  longer combines native resolution, 4x samples and large cloud/water multipliers.
- Capture/storage, emitter, interface and cloud budgets are reduced. Low disables
  reflections and clouds; Medium/High/Ultra explicitly restore them when selected.
- 25% has matching buffer sizes, custom images and dispatch scales, including
  independent HRR-Off branches. Every preset controls the same option keys.
- Profile/About remain the top row; editable fields, English comments/tooltips,
  and per-effect controls remain. Normal maps/POM/powder emitters remain Off.

The night-like moving-floor fixture shows about 94% less temporal flicker and
65% less RGB error at an equal scale. Expected light energy is retained and a
newly displaced floor rejects stale history. These are scoped synthetic tests,
not measured gameplay. Night caustics, newly revealed surfaces and moving sharp
optics can still be noisy; longer reflection history can trail changing content.

Install the new ZIP, Reset, select **Medium**, Apply. Do not import older settings.
See PERFORMANCE.md for exact budgets and TEST_RESULTS.md for evidence and limits.
