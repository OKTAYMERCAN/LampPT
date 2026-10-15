# Building separated packages

Extract the runtime ZIP and extras ZIP into one directory. Requires Python 3
standard library for packaging. Edit release.json, then run:

python3 build.py LampPT-v0.7.5-experimental.zip --extras LampPT-v0.7.5-extras.zip

Only the runtime ZIP is installed into Minecraft. It contains shaders/ and
LICENSE.txt. Extras contain documentation, build/test tools, evidence, release
metadata and an identical license copy. Neither ZIP includes Python caches.
GPU fixture tests additionally require numpy, Pillow, EGL and OpenGL libraries.
