// WORLD INTERSECTION: ordered BVH traversal of captured terrain triangles.
// Distance never substitutes a block cube for a model. Alpha holes, thin
// geometry and dielectric entry/exit use the same intersections at every range.
#ifndef LAMPPT_SCENE_TRACE
#define LAMPPT_SCENE_TRACE
#include "/lib/materials.glsl"
#include "/lib/scene/storage.glsl"
#include "/lib/shadow_settings.glsl"
uniform sampler2D sceneAtlas;
struct SceneHit {vec4 material;vec3 outward;bool escaped;uint triangle;vec3 transmittance;bool detailed;bool hit;vec3 position;vec3 normal;uint data;ivec3 cell;float distance;};
// RGB packing is just a compact hit payload; visibility no longer uses voxels.
vec3 sceneAlbedo(uint data){return srgbToLinear(unpackUnorm4x8(data).rgb);}
vec3 sceneOffset(){return vec3(0);}
float sceneBoxDistance(SceneNode node,vec3 origin,vec3 direction,float limit){
    if(any(greaterThan(node.lo.xyz,node.hi.xyz)))return 1e30;
    float enter=0.0,leave=limit;
    for(int axis=0;axis<3;axis++){
        if(abs(direction[axis])<1e-8){if(origin[axis]<node.lo[axis]||origin[axis]>node.hi[axis])return 1e30;}
        else{
            float a=(node.lo[axis]-origin[axis])/direction[axis],b=(node.hi[axis]-origin[axis])/direction[axis];
            enter=max(enter,min(a,b));leave=min(leave,max(a,b));
        }
    }
    return leave>=enter?enter:1e30;
}
bool sceneTriangleHit(uint index,vec3 origin,vec3 direction,float upper,inout SceneHit hit){
    SceneTriangle tri=sceneTriangles[index];
    vec3 e1=tri.p1.xyz-tri.p0.xyz,e2=tri.p2.xyz-tri.p0.xyz,crossDir=cross(direction,e2);
    float determinant=dot(e1,crossDir);if(abs(determinant)<1e-9)return false;
    vec3 offset=origin-tri.p0.xyz,q=cross(offset,e1);float inv=1.0/determinant;
    float u=dot(offset,crossDir)*inv,v=dot(direction,q)*inv,t=dot(e2,q)*inv;
    if(u<-.000001||v<-.000001||u+v>1.000001||t<.0002||t>upper)return false;
    vec2 uv=vec2(tri.p0.w,tri.p1.w)*(1.0-u-v)+vec2(tri.p2.w,tri.uv.x)*u+tri.uv.yz*v;
    vec4 texel=textureLod(sceneAtlas,uv,0.0);vec4 material=sceneMaterial(tri);
    if(!materialDielectric(material.a)&&texel.a<CUTOUT_THRESHOLD)return false;
    vec3 outward=safeNormalize(cross(e1,e2))*tri.uv.w;
    vec3 albedo=texel.rgb*unpackUnorm4x8(tri.meta.z).rgb;
    if(materialDielectric(material.a))albedo=unpackUnorm4x8(tri.meta.x).rgb;
    hit.hit=true;hit.escaped=false;hit.detailed=true;hit.distance=t;hit.position=origin+direction*t;
    hit.outward=outward;hit.normal=dot(outward,direction)<0.0?outward:-outward;
    hit.material=ptTexelEmission(material,texel.rgb);hit.triangle=index;
    hit.data=(tri.meta.x&0xff000000u)|(packUnorm4x8(vec4(albedo,0))&0xffffffu)|0x80000000u;
    return true;
}
SceneHit traceWorld(vec3 origin,vec3 direction,float maxDistance,ivec3 unused,bool anyHit){
    SceneHit h;h.material=vec4(0);h.outward=-direction;h.escaped=false;h.triangle=0xffffffffu;
    h.transmittance=vec3(1);h.detailed=true;h.hit=false;h.position=origin;h.normal=-direction;
    h.data=0u;h.cell=ivec3(-1);h.distance=0.0;
    // Trace the represented scene even when capture is incomplete. A global
    // overflow flag describes missing geometry, not a wall across every ray.
    // Missing terrain may leak light; coverage/capacity diagnostics expose it.
    if(sceneCount()==0u){h.escaped=true;h.distance=maxDistance;return h;}
    uint stack[64];int top=0;uint node=0u,base=sceneLeafBase();
    float closest=maxDistance;vec3 ray=safeNormalize(direction);
    for(int visit=0;visit<GEOMETRY_RAY_TESTS;visit++){
        SceneNode current=sceneNodes[node];
        if(sceneBoxDistance(current,origin,ray,closest)<1e29){
            if(node>=base){
                uint index=floatBitsToUint(current.hi.w);
                if(index<sceneCount()&&sceneTriangleHit(index,origin,ray,closest,h)){
                    closest=h.distance;if(anyHit)return h;
                }
            }else{
                uvec2 children=sceneChildren[node];uint a=children.x,b=children.y;
                float da=sceneBoxDistance(sceneNodes[a],origin,ray,closest),db=sceneBoxDistance(sceneNodes[b],origin,ray,closest);
                if(da<1e29||db<1e29){
                    if(da<1e29&&db<1e29){
                        if(top>=64)break;
                        stack[top++]=da<db?b:a;
                    }
                    node=da<db?a:b;continue;
                }
            }
        }
        if(top==0){h.escaped=!h.hit;h.distance=h.hit?h.distance:maxDistance;return h;}
        node=stack[--top];
    }
    // Budget exhaustion cannot become sky or a guessed bright hit. Every loop
    // and stack is bounded, so an overloaded scene cannot spin indefinitely.
    h.hit=true;h.data=0u;h.material=vec4(0);h.escaped=false;h.distance=0.0;return h;
}
SceneHit traceScene(vec3 p,vec3 d,float distance,ivec3 unused){return traceWorld(p,d,distance,unused,false);}
#endif
