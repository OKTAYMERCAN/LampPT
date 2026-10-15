# LampPT
This project Path Traced Global illimunation shaderpack for minecraft (Iris). Prof of Concept and Early alpha stage.

# LampPT

![Platform](https://img.shields.io/badge/platform-Minecraft%20Java-darkgreen.svg)
![Loader](https://img.shields.io/badge/requires-Iris%20%2B%20Sodium-blue.svg)
![PBR](https://img.shields.io/badge/LabPBR-supported-purple.svg)
![Version](https://img.shields.io/badge/version-4.64-orange.svg)

This project Path Traced Global illimunation shaderpack for minecraft (Iris). Prof of Concept and Early alpha stage.

I wanted to create my own shaderpack because the existing ones are either paid or locked behind paywalls or subscriptions, which is frustrating. I decided to make my own, but due to life circumstances, I didn't have the time or the necessary skills to do it from scratch. So I purchased a paid AI subscription (OpenAI Plus - GPT-6 Astra) and then started making LampPT to test how much the technology has advanced and what it's capable of, while also bringing my dream shaderpack to life to share with the community.

---

## Coral Reef License (v1.0) - What You Can and Cannot Do (İts short sumarry check full license!)

### What You Can Do (+)
* **Free Use:** You can run, study, and change the Program for free, and use it for personal study, research, experiment, testing, private entertainment, or hobby projects.
* **Content Creation & Monetization:** You can show the Program in videos, live streams, short videos, screenshots, and reviews, and earn money from that content through advertising, sponsorships, memberships, and donations (provided you give proper credit).
* **Voluntary Donations:** You may accept voluntary donations for your work, as long as every version is free to everyone, donating gives no special access or priority, and donations are not tied to downloads.
* **Modification:** You can modify the Program and create versions based on it.
* **Sharing Modified Versions:** You can share modified versions only for free, under this same license, with their complete source code open to everyone, with proper credit, and under a clearly new and different name.
* **Sharing Exact Copies:** You can share exact copies of the Program by directing people to the Official Source.
* **Giving Credit:** You can use the Program's name, author name, and official source link to provide required credits.

### What You Cannot Do (-)
* **Commercial Sale & Rental:** You cannot sell, rent, lease, or license the Program or any copy for a fee, or charge any price for access or downloads.
* **Paywalled Access:** You cannot make the Program, or any version, feature, update, or early access, available only to people who pay through paid memberships, subscriptions, or donation tiers.
* **Link Monetization:** You cannot convey the Program or its links through link-monetization services that force users to view advertisements or wait before downloading.
* **Commercial Distribution of Modified Versions:** You cannot distribute modified versions for any commercial purpose or earn money from them.
* **Sublicensing:** You cannot sublicense the Program under any circumstances.
* **Hosting Official Copies Elsewhere:** You cannot host, mirror, or upload exact copies of the Program anywhere else except its Official Source (unless the version becomes abandoned).
* **Endorsement Illusion:** You cannot suggest that the Licensor or contributors endorse you or your use without written permission.

---

<img width="2560" height="1362" alt="Screenshot_20260926_094316" src="https://github.com/user-attachments/assets/6acc4091-1c87-4548-97d4-f08a4100de8d" />

<img width="2560" height="1362" alt="Screenshot_20260926_094438" src="https://github.com/user-attachments/assets/8dcb85a5-f06f-461a-b986-11a6fb4a5018" />

<img width="2560" height="1363" alt="Screenshot_20260926_094101" src="https://github.com/user-attachments/assets/95677acb-a276-4ff5-bc9a-25bc33e61a38" />

## Compatibility and validation

The observed user target was Iris 1.11.4 / Minecraft 26.2 with Sodium. This build
requires OpenGL 4.3, compute shaders, SSBOs and Iris block-emission attributes.
It is an Iris-targeted build; OptiFine and native macOS OpenGL are not supported.
No universal loader/GPU compatibility is claimed.

## Is this full path tracing? Can it use hardware RT?

The lighting integrator traces world-space paths for GI, reflective and refractive
transport, source visibility, caustic paths and medium scattering. It does not use
screen-space GI or a Hybrid lighting fallback. Calling the whole Minecraft
renderer "100% path traced" would be inaccurate: first visibility is rasterized,
capture is finite, wave/sky/material models are approximations, and reconstruction,
tone mapping and bloom are separate operations. The limits above remain applicable.

Traversal currently runs in GLSL on the GPU's general shader cores. "Software
ray tracing" here does not mean the game traces rays on its CPU. Hardware RT is
possible in a different rendering backend, but cannot be enabled by changing a
shaderpack option. The loader/mod would need an RT API, acceleration structures
and pipeline integration, plus compatible GPU/drivers. For example, Vulkan's
`VK_KHR_ray_tracing_pipeline` and `VK_KHR_acceleration_structure` expose those
facilities. This release does not add a hardware backend or claim RT-core use.
See the [Khronos ray-tracing example](https://docs.vulkan.org/samples/latest/samples/extensions/ray_tracing_basic/README.html).

The included GLSL was compiled and rendered on Mesa software OpenGL 4.5.
**Minecraft, Iris's shader transformer and NVIDIA hardware were unavailable.**
No in-game FPS, driver stability or user-scene appearance has been measured.
See `TEST_RESULTS.md` for reproducible checks and limits; images in the tests
folder are synthetic shader renders, not Minecraft screenshots.

## Notice

LampPT - Minecraft shaderpack
Copyright (C) 2026 Oktay Mercan

Licensed under the Coral Reef License, version 1.0.
The full text of the license is in the LICENSE file.

Official Source: https://github.com/OKTAYMERCAN/LampPT
  Any other official download pages (such as Modrinth or CurseForge)
  are those listed as official in the README at the Official Source.
Contact: oktaylamacera@gmail.com
  If the Official Source is ever unavailable, you can ask for a copy
  at this address.
Governing law and courts: Republic of Türkiye

Credit example:
  Shaders: LampPT by Oktay Mercan - https://github.com/OKTAYMERCAN/LampPT

Modpacks: including a copy of LampPT in a modpack requires written
permission from Oktay Mercan (section 11). A modpack that only refers
to LampPT, so that players download it from an official page, needs no
permission, but must give Credit and must not earn platform rewards or
revenue (sections 3 and 11).

This work comes with ABSOLUTELY NO WARRANTY.

---
Contains AI-generated code, assets and text. Made with AI.
