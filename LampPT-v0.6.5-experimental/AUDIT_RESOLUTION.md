# Audit resolution — 0.6.3 experimental

| Audit finding | Disposition | Implementation / verification |
| --- | --- | --- |
| Water entry/exit orientation | Fixed in covered cases | Shared block-local physical normal; separate geometric guide; double-sided, side and slope tests |
| Translucent identity mismatch | Fixed | Shared resolver and RGBA32F metadata; seven primary/secondary class comparisons |
| Missing visible native emission | Fixed | at_midBlock.w propagated to raster material; half-float capture emission; direct parity test |
| Stale lighting history | Reduced | Material validation and expected-missing-sample response; rare-energy and switch-off tests |
| Guidance without sunlight/water exit | Fixed | Radiance and boundary gating; matching sampling/PDF; valid-caustic and disabled-guidance tests |
| Full per-frame BVH build cost | Partially mitigated | Indirect counts remove unused workgroups; full rebuild and ordered dispatch overhead remain |
| Finite capture / traversal limit | Remains a design limit | No unlimited-world claim; coverage diagnostics and conservative ray-budget behavior retained |

Minor changes: froglights use their own texture-derived color; held translucent
items use a finite thin-sheet approximation. Secondary normal maps/POM, exact
spectral materials, small-light specular manifold sampling and complete entity
capture remain unsupported. None is silently replaced by a Hybrid lighting mode.

Tests run on synthetic Mesa OpenGL, not Minecraft/Iris/NVIDIA. Runtime loading,
user-world appearance and RTX performance still require a game session.
