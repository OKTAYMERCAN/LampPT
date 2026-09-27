// SCATTERING: normalized Lambert/GGX mixture and rough dielectric interfaces.
// All continuation weights are f * abs(cosine) / PDF, including guidance.
#ifndef LAMPPT_PT_BSDF
#define LAMPPT_PT_BSDF
uint ptHash(uint x){x^=x>>16u;x*=0x7feb352du;x^=x>>15u;x*=0x846ca68bu;return x^(x>>16u);}
float ptRandom(inout uint state){state=ptHash(state+0x9e3779b9u);return float(state>>8u)*(1.0/16777216.0);}
vec2 ptRandom2(inout uint s){float x=ptRandom(s);return vec2(x,ptRandom(s));}
float ptMIS(float a,float b){return a*a/max(a*a+b*b,1e-30);}
float ptMax(vec3 v){return max(v.x,max(v.y,v.z));}
// Henyey-Greenstein phase. Directions use the renderer's wo convention:
// -wo is propagation into the medium; positive g favors forward scattering.
float ptPhase(float cosine,float g){
    float d=max(1.0+g*g-2.0*g*cosine,1e-6);
    return (1.0-g*g)/(4.0*PI*d*sqrt(d));
}
vec3 ptSamplePhase(vec3 wo,float g,vec2 u){
    float c;
    if(abs(g)<.001)c=1.0-2.0*u.x;
    else{float q=(1.0-g*g)/(1.0-g+2.0*g*u.x);c=(1.0+g*g-q*q)/(2.0*g);}
    c=clamp(c,-1.0,1.0);float r=sqrt(max(1.0-c*c,0.0)),phi=2.0*PI*u.y;
    return tangentBasis(-wo)*vec3(r*cos(phi),r*sin(phi),c);
}
float ptFresnel(float cosine,float etaI,float etaT){
    float c=clamp(abs(cosine),0.0,1.0),s2=(etaI/etaT)*(etaI/etaT)*(1.0-c*c);
    if(s2>=1.0)return 1.0;
    float ct=sqrt(max(0.0,1.0-s2));
    float rs=(etaI*c-etaT*ct)/max(etaI*c+etaT*ct,1e-8);
    float rp=(etaT*c-etaI*ct)/max(etaT*c+etaI*ct,1e-8);
    return .5*(rs*rs+rp*rp);
}
float ptD(float nh,float a){float d=nh*nh*(a*a-1.0)+1.0;return a*a/(PI*d*d);}
float ptLambda(float cosine,float a){float c2=max(cosine*cosine,1e-8);return .5*(sqrt(1.0+a*a*(1.0-c2)/c2)-1.0);}
vec3 ptMicroNormal(vec3 n,float a,vec2 u){
    float c=sqrt((1.0-u.x)/max(1.0+(a*a-1.0)*u.x,1e-8));
    float s=sqrt(max(0.0,1.0-c*c)),phi=2.0*PI*u.y;
    return tangentBasis(n)*vec3(s*cos(phi),s*sin(phi),c);
}
// Visible-GGX sampling (Heitz): avoid sampling microfacets hidden from wo.
// Sampling and PDFs use the same Smith G1 distribution, reducing grazing spikes.
vec3 ptVisibleNormal(vec3 n,vec3 wo,float alpha,vec2 u){
    mat3 frame=tangentBasis(n);vec3 v=transpose(frame)*wo;
    vec3 stretched=safeNormalize(vec3(alpha*v.xy,max(v.z,1e-6)));
    float lensq=dot(stretched.xy,stretched.xy);
    vec3 t1=lensq>1e-8?vec3(-stretched.y,stretched.x,0)/sqrt(lensq):vec3(1,0,0);
    vec3 t2=cross(stretched,t1);float r=sqrt(u.x),phi=2.0*PI*u.y;
    float x=r*cos(phi),y=r*sin(phi),blend=.5*(1.0+stretched.z);
    y=mix(sqrt(max(0.0,1.0-x*x)),y,blend);
    vec3 h=t1*x+t2*y+stretched*sqrt(max(0.0,1.0-x*x-y*y));
    return frame*safeNormalize(vec3(alpha*h.xy,max(h.z,0.0)));
}
vec3 ptCone(vec3 axis,float cosine,vec2 u){
    float c=mix(1.0,cosine,u.x),s=sqrt(max(0.0,1.0-c*c)),phi=2.0*PI*u.y;
    return tangentBasis(axis)*vec3(s*cos(phi),s*sin(phi),c);
}
struct PtSurface {vec3 p;vec3 ng;vec3 n;vec3 albedo;vec4 m;vec3 emission;};
// Keep primary diffuse irradiance separate from all view-dependent transport.
// Both channels follow the SAME sampled path; this does not trace extra rays.
struct PtRadiance {vec3 diffuse;vec3 specular;};
bool ptDielectric(PtSurface s){return materialDielectric(s.m.a);}
vec3 ptF0(PtSurface s){return s.m.g<0.0?clamp(s.albedo,vec3(0),vec3(.99)):vec3(clamp(s.m.g,0.0,.99));}
float ptSpecProbability(PtSurface s){
#if PT_REFLECTIONS == 0
    return 0.0;
#elif PT_GI == 0
    return 1.0;
#else
    return s.m.g<0.0?1.0:clamp(ptMax(ptF0(s)),.05,.8);
#endif
}
PtRadiance ptEvalParts(PtSurface s,vec3 wo,vec3 wi){
    PtRadiance f;f.diffuse=vec3(0);f.specular=vec3(0);
    if(s.m.a<0.0){f.specular=vec3(ptPhase(dot(-wo,wi),s.m.g));return f;}
    float nv=dot(s.n,wo),nl=dot(s.n,wi);
    if(nv<=0.0||nl<=0.0||dot(s.ng,wi)<=0.0)return f;
    vec3 h=safeNormalize(wo+wi),f0=ptF0(s);
    vec3 F=f0+(1.0-f0)*pow(1.0-max(dot(wo,h),0.0),5.0);
    float a=max(s.m.r,.025),D=ptD(max(dot(s.n,h),0.0),a);
    float G=1.0/(1.0+ptLambda(nv,a)+ptLambda(nl,a));
    f.diffuse=s.m.g<0.0?vec3(0):(1.0-F)/PI;
#if PT_REFLECTIONS == 1
    f.specular=F*(D*G/max(4.0*nv*nl,1e-8))*PT_REFLECTION_STRENGTH;
#endif
    return f;
}
vec3 ptEval(PtSurface s,vec3 wo,vec3 wi){PtRadiance f=ptEvalParts(s,wo,wi);return f.diffuse*s.albedo+f.specular;}
float ptBasePdf(PtSurface s,vec3 wo,vec3 wi){
    if(s.m.a<0.0)return ptPhase(dot(-wo,wi),s.m.g);
    if(dot(s.n,wi)<=0.0)return 0.0;
    vec3 h=safeNormalize(wo+wi);float nh=max(dot(s.n,h),0.0);
    float p=ptSpecProbability(s),a=max(s.m.r,.025);
    return (1.0-p)*max(dot(s.n,wi),0.0)/PI+p*ptD(nh,a)/(1.0+ptLambda(dot(s.n,wo),a))/max(4.0*dot(s.n,wo),1e-8);
}
float ptGuidance(float mediumIor){
#if PT_CAUSTIC_GUIDING == 1 && PT_CAUSTICS == 1 && PT_REFRACTION == 1 && WATER_ENABLED == 1 && PT_SUNLIGHT == 1
    vec3 sun=safeNormalize(mat3(gbufferModelViewInverse)*sunPosition);
    return abs(mediumIor-WATER_IOR)<.01&&ptMax(mainLightRadiance(sun,rainStrength))>0.0?.65:0.0;
#else
    return 0.0;
#endif
}
vec3 ptGuideCachedPosition=vec3(1e30),ptGuideCachedLight=vec3(0),ptGuideCachedAxis=vec3(0,1,0);
float ptGuideCachedProbability=0.0,ptGuideCachedCosine=.9999;
mat2 ptGuideWarp=mat2(.01),ptGuideWarpInverse=mat2(100.0);
float ptGuideArea=PI*.0001;
float ptGuideConeCosine(){return ptGuideCachedCosine;}
vec3 ptGuideAxis(PtSurface s,vec3 light){return ptGuideCachedAxis;}
vec3 ptRefractedSun(vec2 point,vec3 light){
    return safeNormalize(-refract(-light,waterWaveNormal(point+cameraPosition.xz,frameTimeCounter),1.0/WATER_IOR));
}
vec2 ptWaterSlope(vec2 point,vec3 light){
    vec3 axis=ptRefractedSun(point,light);return axis.xz/max(axis.y,.05);
}
vec3 ptWaterConnection(vec3 receiver,float height,vec3 direction){
    vec3 point=receiver+direction*(height/max(direction.y,.01));
    vec3 n=-waterWaveNormal(point.xz+cameraPosition.xz,frameTimeCounter);
    return refract(direction,n,WATER_IOR);
}
float ptGuideDirectionalPdf(vec3 wi){
    mat3 basis=tangentBasis(ptGuideCachedAxis);vec3 local=transpose(basis)*wi;
    if(local.z<=0.0)return 0.0;
    vec2 offset=local.xy/local.z,disc=ptGuideWarpInverse*offset;
    // Gnomonic projection has dOmega = dArea / (1 + |offset|^2)^(3/2).
    return dot(disc,disc)<=1.0?pow(1.0+dot(offset,offset),1.5)/ptGuideArea:0.0;
}
vec3 ptSampleGuide(vec2 u){
    float phi=2.0*PI*u.y;vec2 offset=ptGuideWarp*(sqrt(u.x)*vec2(cos(phi),sin(phi)));
    return tangentBasis(ptGuideCachedAxis)*normalize(vec3(offset,1));
}
void ptPrepareGuidance(PtSurface s,float ior,vec3 light){
    if(ptGuidance(ior)<=0.0)return;
    if(all(equal(s.p,ptGuideCachedPosition))&&all(equal(light,ptGuideCachedLight)))return;
    ptGuideCachedPosition=s.p;ptGuideCachedLight=light;ptGuideCachedProbability=0.0;
    vec3 axis=ptRefractedSun(s.p.xz,light);
    SceneHit boundary=traceScene(s.p+axis*RAY_BIAS,axis,PT_DISTANCE,ivec3(-1));
    if(!boundary.hit||boundary.data==0u||abs(boundary.material.a-1.0)>.1||boundary.outward.y<.5)return;
    float height=boundary.position.y-s.p.y;if(height<=RAY_BIAS)return;
    vec2 point=boundary.position.xz;
    // Solve the receiver-to-interface Snell connection, not a normal at the
    // receiver. A damped 2D Newton step handles wave curvature and depth better
    // than the old three fixed-point iterations. Only two BVH queries are used;
    // all intermediate evaluations are the same analytic wave normal as water.
    for(int i=0;i<PT_CAUSTIC_SOLVER_STEPS;i++){
        vec2 f=point-s.p.xz-ptWaterSlope(point,light)*height;
        if(dot(f,f)<1e-8)break;
        const float e=.02;
        vec2 dx=(ptWaterSlope(point+vec2(e,0),light)-ptWaterSlope(point-vec2(e,0),light))*(height/(2.0*e));
        vec2 dz=(ptWaterSlope(point+vec2(0,e),light)-ptWaterSlope(point-vec2(0,e),light))*(height/(2.0*e));
        mat2 J=mat2(vec2(1,0)-dx,vec2(0,1)-dz);
        vec2 step=abs(determinant(J))>.02?inverse(J)*f:f*.5;
        step*=min(1.0,1.5/max(length(step),1e-6));
        vec2 candidate=point-step;
        vec2 residual=candidate-s.p.xz-ptWaterSlope(candidate,light)*height;
        if(dot(residual,residual)>dot(f,f))candidate=point-step*.25;
        point=candidate;
    }
    axis=safeNormalize(vec3(point.x-s.p.x,height,point.y-s.p.z));
    boundary=traceScene(s.p+axis*RAY_BIAS,axis,PT_DISTANCE,ivec3(-1));
    if(!boundary.hit||boundary.data==0u||abs(boundary.material.a-1.0)>.1||dot(boundary.outward,axis)<=0.0)return;
    // Failed or approximate connections get a wider proposal, never invented
    // light. The ordinary BSDF remains in the mixture so other paths retain
    // support. Actual intersections, Fresnel and the mixture PDF decide energy.
    vec3 expected=ptRefractedSun(boundary.position.xz,light);
    float residual=acos(clamp(dot(axis,expected),-1.0,1.0));
    float angle=clamp(PT_SUN_ANGLE/WATER_IOR+2.0*WATER_ROUGHNESS+residual*1.5,.006,.25);
    ptGuideCachedAxis=axis;ptGuideCachedCosine=cos(angle);
    // A focused sun preimage is generally an ellipse, not a fixed cone. Estimate
    // its local angular Jacobian so deep-water curvature does not leave most
    // valid sun paths outside a tiny proposal (and create huge rare weights).
    mat3 basis=tangentBasis(axis),sunBasis=tangentBasis(light);const float e=.001;
    vec3 xp=ptWaterConnection(s.p,height,normalize(axis+basis[0]*e));
    vec3 xm=ptWaterConnection(s.p,height,normalize(axis-basis[0]*e));
    vec3 yp=ptWaterConnection(s.p,height,normalize(axis+basis[1]*e));
    vec3 ym=ptWaterConnection(s.p,height,normalize(axis-basis[1]*e));
    mat2 angular=mat2((transpose(sunBasis)*(xp-xm)).xy/(2.0*e),(transpose(sunBasis)*(yp-ym)).xy/(2.0*e));
    float radius=PT_SUN_ANGLE+2.5*WATER_ROUGHNESS*WATER_IOR+residual*WATER_IOR*1.5;
    ptGuideWarp=abs(determinant(angular))>.01?inverse(angular)*radius:mat2(tan(angle)*4.0);
    // Keep the proposal finite at singular folds. The base BSDF still covers
    // every other direction; this numerical guide never clips physical energy.
    float largest=max(length(ptGuideWarp[0]),length(ptGuideWarp[1]));
    ptGuideWarp*=min(1.0,.3/max(largest,1e-8));
    ptGuideArea=PI*abs(determinant(ptGuideWarp));
    if(ptGuideArea<1e-9){ptGuideWarp=mat2(.006);ptGuideArea=PI*.006*.006;}
    ptGuideWarpInverse=inverse(ptGuideWarp);ptGuideCachedProbability=ptGuidance(ior);
}
float ptPdf(PtSurface s,vec3 wo,vec3 wi,float ior,vec3 light){
    ptPrepareGuidance(s,ior,light);
    float guide=ptGuidance(ior)>0.0?ptGuideCachedProbability:0.0;
    if(guide<=0.0)return ptBasePdf(s,wo,wi);
    float cone=ptGuideDirectionalPdf(wi);
    return (1.0-guide)*ptBasePdf(s,wo,wi)+guide*cone;
}
vec3 ptSample(PtSurface s,vec3 wo,float ior,vec3 light,inout uint rng,out vec3 weight,out float pdf){
    vec3 wi;ptPrepareGuidance(s,ior,light);
    float guide=ptGuidance(ior)>0.0?ptGuideCachedProbability:0.0;
    if(ptRandom(rng)<guide)wi=ptSampleGuide(ptRandom2(rng));
    else if(s.m.a<0.0)wi=ptSamplePhase(wo,s.m.g,ptRandom2(rng));
    else if(ptRandom(rng)<ptSpecProbability(s))wi=reflect(-wo,ptVisibleNormal(s.n,wo,max(s.m.r,.025),ptRandom2(rng)));
    else wi=tangentBasis(s.n)*cosineHemisphere(ptRandom2(rng));
    pdf=ptPdf(s,wo,wi,ior,light);
    PtRadiance f=ptEvalParts(s,wo,wi);
    if(s.m.a>=0.0)f.diffuse*=float(PT_GI)*PT_GI_STRENGTH;
    weight=(f.diffuse*s.albedo+f.specular)*(s.m.a<0.0?1.0:max(dot(s.n,wi),0.0))/max(pdf,1e-20);
    return wi;
}
vec3 ptSampleDielectric(PtSurface s,vec3 wo,float etaI,float etaT,inout uint rng,out vec3 weight,out bool transmitted){
    if((s.m.a==1.0&&WATER_ENABLED==0)||(s.m.a!=1.0&&PT_GLASS==0)){
        weight=vec3(1);transmitted=true;return -wo;
    }
    if(s.m.a==33.0){
        // Parallel thin sheet: integrate repeated internal Fresnel reflections.
        // Net transmission is straight; finite absorption needs no medium stack.
        float F=ptFresnel(dot(wo,s.n),etaI,etaT),sheetF=2.0*F/(1.0+F);
        transmitted=PT_REFLECTIONS==0||ptRandom(rng)>=sheetF;
        weight=transmitted?pow(max(s.albedo,vec3(.003)),vec3(GLASS_TINT*.08)):vec3(PT_REFLECTION_STRENGTH);
        if(PT_REFLECTIONS==0)weight*=1.0-sheetF;
        return transmitted?-wo:reflect(-wo,s.n);
    }
    float a=max(s.m.r,.001);vec3 h=ptVisibleNormal(s.n,wo,a,ptRandom2(rng));
    if(dot(wo,h)<=0.0){weight=vec3(0);transmitted=false;return s.n;}
    float F=ptFresnel(dot(wo,h),etaI,etaT);
#if PT_REFLECTIONS == 1
    transmitted=ptRandom(rng)>=F;
#else
    transmitted=true;
#endif
#if PT_REFRACTION == 1
    vec3 wi=transmitted?refract(-wo,h,etaI/etaT):reflect(-wo,h);
#else
    vec3 wi=transmitted?-wo:reflect(-wo,h);
#endif
    if(dot(wi,wi)<.001||((dot(s.ng,wi)<0.0)!=transmitted)){weight=vec3(0);return s.n;}
    float G=1.0/(1.0+ptLambda(dot(s.n,wo),a)+ptLambda(dot(s.n,wi),a));
    float w=G*(1.0+ptLambda(dot(s.n,wo),a));
#if PT_REFLECTIONS == 0
    w*=1.0-F;
#endif
    if(!transmitted)w*=PT_REFLECTION_STRENGTH;
#if PT_REFRACTION == 1
    if(transmitted)w*=(etaI*etaI)/(etaT*etaT);
#endif // Radiance transport across media.
    weight=vec3(w);return safeNormalize(wi);
}
#endif
