// BVH BUILD: stable radix sort, Morton-prefix topology and bottom-up bounds.
// Dependencies use ordered dispatches and coherent memory publication.
// Bounded child-completion propagation never spins or waits for another thread.
#include "/lib/scene/storage.glsl"
#include "/lib/materials.glsl"
#include "/lib/shadow_settings.glsl"
#if BUILD_STAGE == 0
layout(local_size_x=256)in;
uint mortonSpread(uint v){v&=1023u;v=(v|(v<<16u))&0x030000ffu;v=(v|(v<<8u))&0x0300f00fu;v=(v|(v<<4u))&0x030c30c3u;v=(v|(v<<2u))&0x09249249u;return v;}
void main(){
    uint i=gl_GlobalInvocationID.x;if(i>=sceneCount())return;
    SceneTriangle t=sceneTriangles[i];vec3 center=(t.p0.xyz+t.p1.xyz+t.p2.xyz)/3.0;
    uvec3 q=uvec3(clamp(center/(2.0*shadowDistance)+.5,vec3(0),vec3(.999999))*1024.0);
    sortA[i]=uvec2(mortonSpread(q.x)|(mortonSpread(q.y)<<1u)|(mortonSpread(q.z)<<2u),i);
}
#elif BUILD_STAGE == 1
layout(local_size_x=256)in;
shared uvec4 prefix[256];
uvec2 sortRead(uint i){
#if (RADIX_SHIFT / 2) % 2 == 0
    return sortA[i];
#else
    return sortB[i];
#endif
}
void main(){
    uint lane=gl_LocalInvocationID.x,group=gl_WorkGroupID.x,i=gl_GlobalInvocationID.x;
    if(group*256u>=sceneCount())return; // Uniform for the whole workgroup.
    uint digit=i<sceneCount()?((sortRead(i).x>>uint(RADIX_SHIFT))&3u):0u;
    uvec4 value=uvec4(0);if(i<sceneCount())value[digit]=1u;
    prefix[lane]=value;barrier();
    for(uint step=1u;step<256u;step<<=1u){
        uvec4 before=lane>=step?prefix[lane-step]:uvec4(0);
        barrier();prefix[lane]+=before;barrier();
    }
    if(i<sceneCount())sortRank[i]=prefix[lane][digit]-1u;
    if(lane==255u)sortHistogram[group]=prefix[lane];
}
#elif BUILD_STAGE == 2
layout(local_size_x=256)in;
shared uvec4 totals[256];
void main(){
    uint lane=gl_LocalInvocationID.x,groups=(sceneCount()+255u)/256u;
    // Distribute the global histogram prefix over 256 lanes. Previously just
    // four lanes walked every group serially, once per radix digit.
    uint span=(groups+255u)/256u,start=lane*span;uvec4 sum=uvec4(0);
    for(uint i=0u;i<(uint(SORT_GROUPS)+255u)/256u;i++){
        uint g=start+i;if(i>=span||g>=groups)break;sum+=sortHistogram[g];
    }
    totals[lane]=sum;barrier();
    for(uint step=1u;step<256u;step<<=1u){
        uvec4 previous=lane>=step?totals[lane-step]:uvec4(0);
        barrier();totals[lane]+=previous;barrier();
    }
    uvec4 all=totals[255],prefix=lane>0u?totals[lane-1u]:uvec4(0);
    prefix+=uvec4(0,all.x,all.x+all.y,all.x+all.y+all.z);
    for(uint i=0u;i<(uint(SORT_GROUPS)+255u)/256u;i++){
        uint g=start+i;if(i>=span||g>=groups)break;
        sortOffset[g]=prefix;prefix+=sortHistogram[g];
    }

}
#elif BUILD_STAGE == 3
layout(local_size_x=256)in;
void main(){
    uint i=gl_GlobalInvocationID.x;if(i>=sceneCount())return;
#if (RADIX_SHIFT / 2) % 2 == 0
    uvec2 value=sortA[i];
#else
    uvec2 value=sortB[i];
#endif
    uint digit=(value.x>>uint(RADIX_SHIFT))&3u,dest=sortOffset[i/256u][digit]+sortRank[i];
#if (RADIX_SHIFT / 2) % 2 == 0
    sortB[dest]=value;
#else
    sortA[dest]=value;
#endif

}
#elif BUILD_STAGE == 4
layout(local_size_x=256)in;
// Longest common prefix of Morton keys, with sorted index as the duplicate-key
// tie breaker. At most 30 coordinate bits + 21 index bits determine the tree.
int scenePrefix(int a,int b,int n){
    if(b<0||b>=n)return -1;
    uint different=sortB[a].x^sortB[b].x;
    return different!=0u?31-findMSB(different):32+31-findMSB(uint(a)^uint(b));
}
void main(){
    uint i=gl_GlobalInvocationID.x,n=sceneCount();if(i>=max(n,1u))return;
    if(n==0u){sceneNodes[0].lo=vec4(1e30,1e30,1e30,0);sceneNodes[0].hi=vec4(-1e30,-1e30,-1e30,0);return;}
    uint index=sortB[i].y;SceneTriangle t=sceneTriangles[index];
    vec3 lo=min(t.p0.xyz,min(t.p1.xyz,t.p2.xyz)),hi=max(t.p0.xyz,max(t.p1.xyz,t.p2.xyz));
    vec3 albedo=srgbToLinear(unpackUnorm4x8(t.meta.x).rgb);
    vec3 emitted=emissionRadiance(sceneMaterial(t),albedo);
    float power=max(emitted.r,max(emitted.g,emitted.b))*sceneArea(t);
    uint leaf=n-1u+i;SceneNode node;
    node.lo=vec4(lo-.0001,power);node.hi=vec4(hi+.0001,uintBitsToFloat(index));
    sceneNodes[leaf]=node;sceneTriangles[index].meta.y=leaf;
    if(i==0u)sceneParents[0]=0xffffffffu;
    if(i<n-1u){
        int x=int(i),count=int(n);
        int direction=scenePrefix(x,x+1,count)>scenePrefix(x,x-1,count)?1:-1;
        int minimum=scenePrefix(x,x-direction,count),upper=2;
        for(int k=0;k<22;k++){
            if(scenePrefix(x,x+upper*direction,count)<=minimum)break;upper*=2;
        }
        int length=0;
        for(int step=upper/2;step>0;step/=2)
            if(scenePrefix(x,x+(length+step)*direction,count)>minimum)length+=step;
        int end=x+length*direction,first=min(x,end),last=max(x,end);
        int commonPrefix=scenePrefix(first,last,count),split=first,step=last-first;
        for(int k=0;k<22;k++){
            step=(step+1)/2;int candidate=split+step;
            if(candidate<last&&scenePrefix(first,candidate,count)>commonPrefix)split=candidate;
            if(step<=1)break;
        }
        uint left=split==first?n-1u+uint(split):uint(split);
        uint right=split+1==last?n-1u+uint(split+1):uint(split+1);
        sceneChildren[i]=uvec2(left,right);sceneParents[left]=i;sceneParents[right]=i;sceneReady[i]=0u;
    }

}
#else
layout(local_size_x=256)in;
void main(){
    uint i=gl_GlobalInvocationID.x,n=sceneCount();if(i>=n||n<2u)return;
    uint node=n-1u+i;
    // Publish each child before signalling its parent. The first arrival exits;
    // only the second child merges and continues. No workgroup spins or waits.
    for(int level=0;level<64;level++){
        uint parent=sceneParents[node];if(parent==0xffffffffu)break;
        memoryBarrierBuffer();uint arrived=atomicAdd(sceneReady[parent],1u);
        if(arrived!=1u)break;
        memoryBarrierBuffer();uvec2 children=sceneChildren[parent];
        SceneNode a=sceneNodes[children.x],b=sceneNodes[children.y],merged;
        merged.lo=vec4(min(a.lo.xyz,b.lo.xyz),a.lo.w+b.lo.w);
        merged.hi=vec4(max(a.hi.xyz,b.hi.xyz),0);sceneNodes[parent]=merged;
        node=parent;
    }
    memoryBarrierBuffer();
}
#endif
