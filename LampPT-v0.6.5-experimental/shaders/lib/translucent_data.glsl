// TWO TRANSLUCENT LAYERS: retain nearest water and nearest glass independently.
// RGB32 precision is intentional: packed 24-bit integers must remain exact.
// Per-target alpha blending preserves the other layer when this one is written.
#ifndef LAMPPT_TRANSLUCENT_DATA
#define LAMPPT_TRANSLUCENT_DATA
vec2 octEncode(vec3 n){
    n/=abs(n.x)+abs(n.y)+abs(n.z);
    return (n.z>=0.0?n.xy:(1.0-abs(n.yx))*mix(vec2(-1.0),vec2(1.0),greaterThanEqual(n.xy,vec2(0.0))))*.5+.5;
}
vec3 octDecode(vec2 e){
    vec2 f=e*2.0-1.0;vec3 n=vec3(f,1.0-abs(f.x)-abs(f.y));
    n.xy+=mix(vec2(1.0),vec2(-1.0),greaterThanEqual(n.xy,vec2(0.0)))*max(-n.z,0.0);
    return normalize(n);
}
// Two 12-bit octahedral coordinates fit exactly in a float32 integer.
float packNormal24(vec3 n){uvec2 q=uvec2(round(clamp(octEncode(n),0.0,1.0)*4095.0));return float(q.x|(q.y<<12u));}
vec3 unpackNormal24(float f){uint q=uint(f);return octDecode(vec2(q&4095u,q>>12u)/4095.0);}
float packMaterial24(vec4 m){return float(packUnorm4x8(vec4(m.r,m.g<0.0?1.0:m.g,m.a/255.0,0))&0xffffffu);}
vec4 unpackMaterial24(float f,float emission){vec3 v=unpackUnorm4x8(uint(f)).rgb;return vec4(v.r,v.g>.99?-1.0:v.g,emission,round(v.b*255.0));}
float packRGB24(vec3 c){return float(packUnorm4x8(vec4(c,0.0))&0xffffffu);}
vec3 unpackRGB24(float f){return unpackUnorm4x8(uint(f)).rgb;}
#endif
