# LampPT 0.7.3 experimental

## Lighting

- Explicit colored source groups for copper flames/lanterns, crying obsidian,
  all lit candle colors/cakes, redstone lamps, copper bulbs, glow lichen, firefly
  bushes, lit redstone ore, glow berries, active sculk and charged respawn anchors.
- Lit-state mappings keep inactive placed sources dark. Native emission remains
  the fallback for unmapped captured terrain. A dark base texture no longer
  suppresses native-emission color twice.
- Lamp Strength defaults to 3; Candle Strength to 2. Candles no longer use the
  torch bright-texel cutoff, which removed dark wax sources. Candle geometry is
  an emitting proxy; the separate vanilla flame particle is not captured.
- Held Item Lighting (On/Off) and Held Light Strength support both hands. Point
  emitters use inverse-square attenuation, traced terrain visibility, the same
  BSDF and indirect path vertices. They use approximate grip positions, not
  captured animated item meshes.

## Water, glass and clouds

- Finite-disk solar NEE + matching dielectric-reflection MIS reduces rare huge
  smooth water/glass sun hits, without hard-clamping their energy.
- Clear water roughness defaults to 0.001 (was 0.005), reducing microscopic
  refraction jitter; procedural wave normals and Snell refraction remain active.
- Conditional primary cloud collisions preserve event probability and energy.
- Cloud/medium reconstruction compares the bounded camera segment instead of
  background material/normal edges. A small volume-only filter runs before
  adding sharp optical scenery, and is disabled with Denoiser Off/Raw Estimate.
- Vanilla cloud fragments are discarded if submitted, so they cannot overwrite
  the PT terrain depth/G-buffer as a second unlit cloud layer.

## Evidence and limits

See TEST_RESULTS.md and tests/ptgi-evidence/v073-*.json. The shader programs were
checked with Mesa OpenGL, not Minecraft/Iris or an NVIDIA driver. These tests
do not establish game FPS or complete visual correctness.

The lit-glass fixture did not reproduce the user's fully black glass. The
underwater fixture is visible but still noisy around caustic/reflection regions.
Those reports are NOT marked resolved. Reproducing the user's exact case needs
the affected world/minimal scene, resource pack, shader overrides and latest.log.
Finite capture and bounded traversal remain limitations; they are not replaced
with invented ambient light or screen-space refraction.
