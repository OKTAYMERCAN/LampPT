#version 430 compatibility
// Test-only copy of the delivered 0.6.6 algorithm; not used by the pack.
#include "/lib/ptgi/context.glsl"
#include "/lib/scene/trace.glsl"
SceneHit traceWorldStackReference(vec3 origin,vec3 direction,float maxDistance,ivec3 unused,bool anyHit){
    SceneHit h;h.material=vec4(0);h.outward=-direction;h.escaped=false;h.triangle=0xffffffffu;
    h.transmittance=vec3(1);h.detailed=true;h.hit=false;h.position=origin;h.normal=-direction;
    h.data=0u;h.cell=ivec3(-1);h.distance=0.0;
    // Trace the represented scene even when capture is incomplete. A global
    // overflow flag describes missing geometry, not a wall across every ray.
    // Missing terrain may leak light; coverage/capacity diagnostics expose it.
    if(sceneCount()==0u){h.escaped=true;h.distance=maxDistance;return h;}
    uint stack[64];int top=0;uint node=0u,base=sceneLeafBase();
    float closest=maxDistance;vec3 ray=safeNormalize(direction);
    bvec3 parallel=lessThan(abs(ray),vec3(1e-8));
    vec3 inverseRay=1.0/mix(ray,vec3(1),parallel);
    for(int visit=0;visit<GEOMETRY_RAY_TESTS;visit++){
        SceneNode current=sceneNodes[node];
        if(sceneBoxDistance(current,origin,inverseRay,parallel,closest)<1e29){
            if(node>=base){
                uint index=floatBitsToUint(current.hi.w);
                if(index<sceneCount()&&sceneTriangleHit(index,origin,ray,closest,h)){
                    closest=h.distance;if(anyHit)return h;
                }
            }else{
                uvec2 children=sceneChildren[node];uint a=children.x,b=children.y;
                float da=sceneBoxDistance(sceneNodes[a],origin,inverseRay,parallel,closest),db=sceneBoxDistance(sceneNodes[b],origin,inverseRay,parallel,closest);
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
uniform sampler2D testOrigins;
uniform sampler2D testDirections;
layout(location=0)out vec4 difference;
layout(location=1)out vec4 actual;
void main(){
    ivec2 pixel=ivec2(gl_FragCoord.xy);
    vec3 origin=texelFetch(testOrigins,pixel,0).xyz;
    vec4 direction=texelFetch(testDirections,pixel,0);
    SceneHit a=traceWorld(origin,direction.xyz,direction.w,ivec3(-1),false);
    SceneHit b=traceWorldStackReference(origin,direction.xyz,direction.w,ivec3(-1),false);
    SceneHit sa=traceWorld(origin,direction.xyz,direction.w,ivec3(-1),true);
    SceneHit sb=traceWorldStackReference(origin,direction.xyz,direction.w,ivec3(-1),true);
    difference=vec4(a.hit==b.hit?0:1,a.escaped==b.escaped?0:1,abs(a.distance-b.distance),sa.hit==sb.hit?0:1);
    actual=vec4(a.distance,a.hit?1:0,a.data==0u?1:0,a.escaped?1:0);
}
