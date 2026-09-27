// SHARED MATH: color-space conversion, position reconstruction, normal encoding,
// random sequences and sampling bases used by the rendering stages.
#ifndef LAMPPT_COMMON
#define LAMPPT_COMMON

const float PI = 3.14159265359;

float saturate(float x) { return clamp(x, 0.0, 1.0); }
vec3 saturate(vec3 x) { return clamp(x, vec3(0.0), vec3(1.0)); }

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

mat3 tangentBasis(vec3 n) {
    vec3 up = abs(n.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
    vec3 t = normalize(cross(up, n));
    return mat3(t, cross(n, t), n);
}

vec3 cosineHemisphere(vec2 xi) {
    float r = sqrt(xi.x);
    float phi = 2.0 * PI * xi.y;
    return vec3(r * cos(phi), r * sin(phi), sqrt(max(0.0, 1.0 - xi.x)));
}

vec3 viewPosition(vec2 uv, float depth, mat4 projectionInverse) {
    vec4 clip = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 view = projectionInverse * clip;
    return view.xyz / max(view.w, 1e-6);
}

vec2 projectUV(vec3 viewPos, mat4 projection) {
    vec4 clip = projection * vec4(viewPos, 1.0);
    return clip.xy / clip.w * 0.5 + 0.5;
}

vec3 encodeNormal(vec3 n) { return n * 0.5 + 0.5; }
vec3 safeNormalize(vec3 n) {
    return dot(n, n) > 1e-8 ? normalize(n) : vec3(0.0, 0.0, 1.0);
}
vec3 decodeNormal(vec3 n) { return safeNormalize(n * 2.0 - 1.0); }
vec3 srgbToLinear(vec3 c) {
    c = max(c, vec3(0.0));
    return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)),
               step(vec3(0.04045), c));
}
vec3 linearToSrgb(vec3 c) {
    c = max(c, vec3(0.0));
    return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055,
               step(vec3(0.0031308), c));
}
ivec2 screenPixel(vec2 uv, ivec2 resolution) {
    return clamp(ivec2(uv * vec2(resolution)), ivec2(0), resolution - 1);
}

#endif
