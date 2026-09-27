// LIGHT SAMPLING: choose emitting triangles from the scene hierarchy.
// The tree is only a sampling distribution; it never paints point-light glow.
#ifndef LAMPPT_PT_LIGHTS
#define LAMPPT_PT_LIGHTS
vec3 ptWorldSun(){return safeNormalize(mat3(gbufferModelViewInverse)*sunPosition);}
vec3 ptWorldLight(){return safeNormalize(mat3(gbufferModelViewInverse)*shadowLightPosition);}
float ptSunSolidAngle(){return 2.0*PI*(1.0-cos(PT_SUN_ANGLE));}
vec3 ptSkyEnvironment(vec3 direction){
#if PT_SKYLIGHT == 1
    // The environment is a complete background, avoiding a hard black stripe
    // below the horizon where no loaded terrain exists.
    return atmosphereColor(direction,ptWorldSun(),skyColor,rainStrength)*PT_SKY_STRENGTH;
#else
    return vec3(0);
#endif
}
vec3 ptSolarEnvironment(vec3 direction){
#if PT_SUNLIGHT == 1
    if(directionalSky()&&dot(direction,ptWorldLight())>=cos(PT_SUN_ANGLE))
        return mainLightRadiance(ptWorldSun(),rainStrength)/ptSunSolidAngle();
#endif
    return vec3(0);
}
vec3 ptEnvironment(vec3 direction){return ptSkyEnvironment(direction)+ptSolarEnvironment(direction);}
float ptEnvironmentPdf(vec3 wi){return directionalSky()&&dot(wi,ptWorldLight())>=cos(PT_SUN_ANGLE)?1.0/ptSunSolidAngle():0.0;}
float ptSkyPdf(vec3 normal,vec3 wi){return length(normal)<.5?1.0/(4.0*PI):max(dot(normal,wi),0.0)/PI;}
vec3 ptEnvironmentMIS(vec3 wi,vec3 previousNormal,float previousPdf,bool delta){
    float sunWeight=delta?1.0:ptMIS(previousPdf,ptEnvironmentPdf(wi));
    float skyWeight=delta?1.0:ptMIS(previousPdf,ptSkyPdf(previousNormal,wi));
    return ptSolarEnvironment(wi)*sunWeight+ptSkyEnvironment(wi)*skyWeight;
}
// The geometry BVH doubles as a triangle-emitter importance hierarchy.
// Probability is evaluated identically during selection and BSDF-hit MIS.
float ptNodeWeight(SceneNode node,vec3 p,vec3 n){
    if(node.lo.w<=0.0)return 0.0;
    vec3 delta=clamp(p,node.lo.xyz,node.hi.xyz)-p;
    vec3 center=(node.lo.xyz+node.hi.xyz)*.5,extent=(node.hi.xyz-node.lo.xyz)*.5;
    float facing=length(n)<.5?1.0:clamp((dot(n,center-p)+dot(abs(n),extent))/max(length(delta),.001),0.0,1.0);
    return node.lo.w*(.02+.98*facing)/(.25+dot(delta,delta));
}
bool ptChooseTriangle(vec3 p,vec3 n,inout uint rng,out uint triangle,out float pdf){
    triangle=0xffffffffu;pdf=1.0;
    if(sceneCount()==0u||sceneNodes[0].lo.w<=0.0)return false;
    uint node=0u,base=sceneLeafBase();float u=ptRandom(rng);
    for(int level=0;level<64;level++){
        if(node>=base){triangle=floatBitsToUint(sceneNodes[node].hi.w);return triangle<sceneCount();}
        uvec2 children=sceneChildren[node];uint a=children.x,b=children.y;
        float wa=ptNodeWeight(sceneNodes[a],p,n),wb=ptNodeWeight(sceneNodes[b],p,n),sum=wa+wb;
        if(sum<=0.0)return false;
        float pa=wa/sum;
        if(u<pa){pdf*=pa;u/=max(pa,1e-20);node=a;}
        else{pdf*=1.0-pa;u=(u-pa)/max(1.0-pa,1e-20);node=b;}
        u=clamp(u,0.0,.9999999);
    }
    return false;
}
float ptTrianglePdf(vec3 p,vec3 n,uint triangle){
    if(triangle>=sceneCount())return 0.0;
    uint node=sceneTriangles[triangle].meta.y;float pdf=1.0;
    for(int level=0;level<64;level++){
        if(node==0u)break;
        uint parent=sceneParents[node];uvec2 children=sceneChildren[parent];uint a=children.x,b=children.y;
        float wa=ptNodeWeight(sceneNodes[a],p,n),wb=ptNodeWeight(sceneNodes[b],p,n);
        if(wa+wb<=0.0)return 0.0;pdf*=(node==a?wa:wb)/(wa+wb);node=parent;
    }
    return pdf;
}
vec3 ptVisibilitySegment(vec3 p,vec3 direction,float geometryDistance,float distance,vec3 sigmaT){
#if PT_SHADOWS == 0
    return exp(-sigmaT*distance)*ptCloudTransmittance(p,direction,distance);
#endif
    // A visibility connection only needs the first opaque/interface hit, not
    // the nearest shaded surface. Stop immediately after alpha-tested occlusion.
    SceneHit h=traceWorld(p,direction,max(geometryDistance-.002,0.0),ivec3(-1),true);
    // Refractive interfaces cannot be connected by a straight shadow ray.
    // Their contributions are found by BSDF paths (including caustic guidance).
    return h.hit||!h.escaped?vec3(0):exp(-sigmaT*distance)*ptCloudTransmittance(p,direction,distance);
}
// Source connections retain their complete endpoint distance. Environment
// connections extend only the cloud medium, not the terrain traversal budget.
vec3 ptVisibility(vec3 p,vec3 direction,float distance,vec3 sigmaT){
    return ptVisibilitySegment(p,direction,distance,distance,sigmaT);
}
vec3 ptEnvironmentVisibility(vec3 p,vec3 direction,vec3 sigmaT){
    return ptVisibilitySegment(p,direction,PT_DISTANCE,ptCloudEnvironmentDistance(),sigmaT);
}
PtRadiance ptDirectParts(PtSurface s,vec3 wo,float mediumIor,vec3 sigmaT,bool continuation,inout uint rng){
    // Prepare the refracted-sun proposal once per scattering vertex. PDFs and
    // source candidates reuse it; they must not repeat geometry queries.
    ptPrepareGuidance(s,mediumIor,ptWorldLight());
    PtRadiance sum;sum.diffuse=vec3(0);sum.specular=vec3(0);
    vec3 wi,offset,incident;float bp,cosine;PtRadiance f;
    // Always sample the sun separately from diffuse sky. The old 50/50 choice
    // made fully sunlit pixels alternate between dark and double brightness.
#if PT_SUNLIGHT == 1
    if(directionalSky()){
        wi=ptCone(ptWorldLight(),cos(PT_SUN_ANGLE),ptRandom2(rng));
        float pdf=1.0/ptSunSolidAngle();bp=continuation?ptPdf(s,wo,wi,mediumIor,ptWorldLight()):0.0;
        cosine=s.m.a<0.0?1.0:max(dot(s.n,wi),0.0);offset=s.m.a<0.0?wi:s.ng;
        f=ptEvalParts(s,wo,wi);
        if(cosine>0.0&&ptMax(f.diffuse+f.specular)>0.0){
            incident=cosine*ptSolarEnvironment(wi)*ptEnvironmentVisibility(s.p+offset*RAY_BIAS,wi,sigmaT)/pdf;
            sum.diffuse+=f.diffuse*incident*(PT_GI==0&&s.m.a>=0.0?1.0:ptMIS(pdf,bp));sum.specular+=f.specular*incident*ptMIS(pdf,bp);
        }
    }
#endif
#if PT_SKYLIGHT == 1
    wi=s.m.a<0.0?ptCone(vec3(0,1,0),-1.0,ptRandom2(rng)):tangentBasis(s.n)*cosineHemisphere(ptRandom2(rng));
    float skyPdf=ptSkyPdf(s.m.a<0.0?vec3(0):s.n,wi);bp=continuation?ptPdf(s,wo,wi,mediumIor,ptWorldLight()):0.0;
    cosine=s.m.a<0.0?1.0:max(dot(s.n,wi),0.0);offset=s.m.a<0.0?wi:s.ng;
    f=ptEvalParts(s,wo,wi);
    if(cosine>0.0&&ptMax(f.diffuse+f.specular)>0.0){
        incident=cosine*ptSkyEnvironment(wi)*ptEnvironmentVisibility(s.p+offset*RAY_BIAS,wi,sigmaT)/max(skyPdf,1e-20);
        sum.diffuse+=f.diffuse*incident*(PT_GI==0&&s.m.a>=0.0?1.0:ptMIS(skyPdf,bp));sum.specular+=f.specular*incident*ptMIS(skyPdf,bp);
    }
#endif
    // Reservoir importance resampling chooses a useful unoccluded contribution
    // before tracing a visibility ray. Its normalization estimates the same
    // average of proposal samples, including the same MIS weights. No light is
    // injected when the selected connection is blocked.
    for(int sampleIndex=0;sampleIndex<PT_LIGHT_SAMPLES;sampleIndex++){
        PtRadiance selected;selected.diffuse=vec3(0);selected.specular=vec3(0);
        vec3 selectedPoint=vec3(0);float weightSum=0.0,selectedWeight=0.0;
        for(int candidate=0;candidate<PT_LIGHT_CANDIDATES;candidate++){
            uint chosen;float cp;
            if(!ptChooseTriangle(s.p,s.m.a<0.0?vec3(0):s.ng,rng,chosen,cp))continue;
            SceneTriangle t=sceneTriangles[chosen];vec2 u=ptRandom2(rng);float r=sqrt(u.x);
            vec3 bary=vec3(1.0-r,r*(1.0-u.y),r*u.y);
            vec3 q=t.p0.xyz*bary.x+t.p1.xyz*bary.y+t.p2.xyz*bary.z;
            vec3 normal=normalize(cross(t.p1.xyz-t.p0.xyz,t.p2.xyz-t.p0.xyz))*t.uv.w;
            vec2 uv=vec2(t.p0.w,t.p1.w)*bary.x+vec2(t.p2.w,t.uv.x)*bary.y+t.uv.yz*bary.z;
            vec4 texel=textureLod(sceneAtlas,uv,0.0);if(texel.a<CUTOUT_THRESHOLD)continue;
            vec3 emission=emissionRadiance(ptTexelEmission(sceneMaterial(t),texel.rgb),srgbToLinear(texel.rgb*unpackUnorm4x8(t.meta.z).rgb));
            float area=sceneArea(t);
            vec3 delta=q-s.p;float d2=dot(delta,delta),dist=sqrt(d2);if(dist<.01)continue;
            wi=delta/dist;float lightCos=max(dot(normal,-wi),0.0);if(lightCos<1e-5)continue;
            float pdf=cp*d2/(area*lightCos);bp=continuation?ptPdf(s,wo,wi,mediumIor,ptWorldLight()):0.0;
            cosine=s.m.a<0.0?1.0:max(dot(s.n,wi),0.0);f=ptEvalParts(s,wo,wi);
            if(cosine<=0.0||ptMax(f.diffuse+f.specular)<=0.0)continue;
            incident=cosine*emission/max(pdf,1e-20);
            PtRadiance proposed;
            proposed.diffuse=f.diffuse*incident*(PT_GI==0&&s.m.a>=0.0?1.0:ptMIS(pdf,bp));
            proposed.specular=f.specular*incident*ptMIS(pdf,bp);
            float weight=ptMax(proposed.diffuse*s.albedo+proposed.specular);
            weightSum+=weight;
            if(weight>0.0&&ptRandom(rng)*weightSum<weight){selected=proposed;selectedPoint=q;selectedWeight=weight;}
        }
        if(selectedWeight<=0.0)continue;
        vec3 delta=selectedPoint-s.p;
        vec3 shadowOrigin=s.p+(s.m.a<0.0?safeNormalize(delta):s.ng)*RAY_BIAS;
        vec3 shadowDelta=selectedPoint-shadowOrigin;
        vec3 visibility=ptVisibility(shadowOrigin,safeNormalize(shadowDelta),length(shadowDelta),sigmaT);
        float normalization=weightSum/(float(PT_LIGHT_CANDIDATES*PT_LIGHT_SAMPLES)*selectedWeight);
        sum.diffuse+=selected.diffuse*visibility*normalization;
        sum.specular+=selected.specular*visibility*normalization;
    }
    return sum;
}
vec3 ptDirect(PtSurface s,vec3 wo,float mediumIor,vec3 sigmaT,bool continuation,inout uint rng){
    PtRadiance L=ptDirectParts(s,wo,mediumIor,sigmaT,continuation,rng);
    return L.diffuse*s.albedo+L.specular;
}
float ptHitLightPdf(SceneHit hit,vec3 previous,vec3 normal,inout uint rng){
    if(hit.triangle>=sceneCount()||hit.material.b<=0.0)return 0.0;
    float area=sceneArea(sceneTriangles[hit.triangle]);
    vec3 delta=hit.position-previous;float c=abs(dot(hit.outward,-safeNormalize(delta)));
    return ptTrianglePdf(previous,normal,hit.triangle)*dot(delta,delta)/max(area*c,1e-20);
}
#endif
