#version 430 compatibility
// TERRAIN CAPTURE: store actual triangles throughout the configured capture
// distance. There is no near-only detail radius or block-sized proxy geometry.
#include "/lib/scene/storage.glsl"
layout(triangles)in;
layout(triangle_strip,max_vertices=3)out;
in vec2 shadowTexcoordV[];
in vec3 geometryPositionV[];
flat in uint geometryDataV[];
flat in uint geometryTintV[];
flat in uint geometryPbrV[];
in vec3 geometryOutwardV[];
flat in int geometryCaptureV[];
flat in float shadowMaterialKindV[];
out vec2 texcoord;
flat out float shadowMaterialKind;
void main(){
    vec3 a=geometryPositionV[0],b=geometryPositionV[1],c=geometryPositionV[2];
    if(geometryCaptureV[0]!=0&&dot(cross(b-a,c-a),cross(b-a,c-a))>1e-12){
        uint index=atomicAdd(geometryCount,1u);
        if(index<uint(GEOMETRY_BUDGET)){
            SceneTriangle t;t.p0=vec4(a,shadowTexcoordV[0].x);t.p1=vec4(b,shadowTexcoordV[0].y);
            t.p2=vec4(c,shadowTexcoordV[1].x);t.uv=vec4(shadowTexcoordV[1].y,shadowTexcoordV[2],0);
            t.uv.w=dot(cross(b-a,c-a),geometryOutwardV[0])>=0.0?1.0:-1.0;
            t.meta=uvec4(geometryDataV[0],0u,geometryTintV[0],geometryPbrV[0]);sceneTriangles[index]=t;
        }else atomicAdd(geometryOverflow,1u);
    }

    for(int i=0;i<3;i++){
        gl_Position=gl_in[i].gl_Position;texcoord=shadowTexcoordV[i];
        shadowMaterialKind=shadowMaterialKindV[i];EmitVertex();
    }
    EndPrimitive();
}
