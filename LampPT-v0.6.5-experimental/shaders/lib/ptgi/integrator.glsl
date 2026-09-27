// PATH INTEGRATOR: one light-transport loop for diffuse, glossy, dielectric and
// volume events. Emission is counted with MIS; no hybrid shading is added.
#include "/lib/water.glsl"
#include "/lib/environment.glsl"
#include "/lib/scene/trace.glsl"
#include "/lib/ptgi/bsdf.glsl"
#include "/lib/ptgi/lights.glsl"
PtSurface ptSurface(SceneHit h,vec3 direction){
    PtSurface s;s.p=h.position;s.ng=h.normal;s.n=h.normal;s.albedo=sceneAlbedo(h.data);
    s.m=h.material;
    s.emission=dot(h.outward,-direction)>0.0?emissionRadiance(s.m,s.albedo):vec3(0);
    if(s.m.a==1.0){
        s.m.r=WATER_ROUGHNESS;s.albedo=vec3(1);
        if(abs(h.outward.y)>.5)s.n=waterWaveNormal(s.p.xz+cameraPosition.xz,frameTimeCounter)*sign(h.outward.y);
        if(dot(s.n,s.ng)<0.0)s.n=-s.n;
    }
    return s;
}
vec3 ptGlassExtinction(vec3 dye){return -log(max(dye,vec3(.003)))*GLASS_TINT*.65;}
PtRadiance ptIntegrateParts(PtGuide guide,inout uint rng){
    vec3 ray=safeNormalize(mat3(gbufferModelViewInverse)*guide.p),origin=vec3(0);
    vec3 betaD=vec3(0),betaS=vec3(1),previous=vec3(0),previousLightNormal=vec3(0),previousSkyNormal=vec3(0);
    PtRadiance L;L.diffuse=vec3(0);L.specular=vec3(0);
    float previousPdf=0.0,etaScale=1.0;bool previousDelta=true,seenOpaque=false,causticWeighted=false;
    int scatteringEvents=0,interfaceEvents=0;
    // A bounded medium stack allows water -> glass -> water, nested glass,
    // and independent entry/exit Fresnel instead of tinting one screen layer.
    float iors[16];vec3 absorption[16];float scattering[16];int top=0;
    iors[0]=isEyeInWater==1&&WATER_ENABLED==1?WATER_IOR:1.0;
    absorption[0]=isEyeInWater==1&&WATER_ENABLED==1?max(vec3(1)-vec3(WATER_R,WATER_G,WATER_B),vec3(.02))*WATER_ABSORPTION:vec3(PT_AIR_DENSITY*.1);
    scattering[0]=isEyeInWater==1&&WATER_ENABLED==1?WATER_SCATTERING:PT_AIR_DENSITY;
    // Transmission interfaces have their own budget. A water entry and exit
    // must not consume all diffuse/volume events before light reaches the camera.
    // One extra terminal query allows a completed path to reach an emitter/sky.
    for(int bounce=0;bounce<PT_BOUNCES+PT_TRANSMISSION_DEPTH+1;bounce++){
        SceneHit h;
        if(bounce==0){
            h.hit=guide.valid==1;h.escaped=!h.hit;h.detailed=true;h.data=1u;
            h.position=(gbufferModelViewInverse*vec4(guide.p,1)).xyz;
            h.distance=h.hit?length(h.position):PT_DISTANCE;
            h.normal=safeNormalize(mat3(gbufferModelViewInverse)*guide.ng);h.outward=h.normal;
            h.material=guide.material;h.triangle=0xffffffffu;h.cell=ivec3(floor(h.position+sceneOffset()));
        }else h=traceScene(origin,ray,PT_DISTANCE,ivec3(-1));
        // Clouds extend beyond the finite captured terrain. Only a confirmed
        // geometry miss may extend the medium segment; a traversal failure or
        // a real surface must never be replaced by the distant environment.
        if(!h.hit&&h.escaped&&iors[top]<1.01)h.distance=ptCloudEnvironmentDistance();
        vec3 sigmaA=absorption[top];float sigmaS=scattering[top];
#if PT_VOLUMETRICS == 0
        sigmaS=0.0;
#endif
        vec3 sigmaT=sigmaA+vec3(sigmaS);float majorant=ptMax(sigmaT);
        float flight=majorant>0.0?-log(max(1.0-ptRandom(rng),1e-7))/majorant:1e30;
        float cloudFlight=1e30;
        if(iors[top]<1.01&&ptCloudsActive()){
            vec2 interval;
            if(ptCloudInterval(origin,ray,h.distance,interval))
                cloudFlight=ptCloudFreeFlight(origin,ray,h.distance,-log(max(1.0-ptRandom(rng),1e-7)));
        }
        bool cloud=cloudFlight<h.distance&&(sigmaS<=0.0||cloudFlight<flight);
        bool volume=cloud||(sigmaS>0.0&&flight<h.distance);
        PtSurface s;vec3 wo=-ray;
        if(volume){
            float distance=cloud?cloudFlight:flight;
            // Independent cloud and homogeneous free flights compete. Cloud
            // survival is already sampled: multiplying it here would attenuate
            // twice. Preserve the homogeneous majorant likelihood ratio.
            vec3 attenuation=exp((sigmaS>0.0?vec3(majorant)-sigmaT:-sigmaT)*distance);
            attenuation*=cloud?CLOUD_ALBEDO:sigmaS/majorant;
            betaD*=attenuation;betaS*=attenuation;
            s.p=origin+ray*distance;s.n=-ray;s.ng=s.n;s.albedo=vec3(1);
            s.m=vec4(1,cloud?CLOUD_ANISOTROPY:0.0,0,cloud?-2.0:-1.0);s.emission=vec3(0);
        }else{
            // Absorption-only glass is integrated deterministically. Scattering
            // media use the matching free-flight survival probability.
            vec3 attenuation=exp((sigmaS>0.0?vec3(majorant)-sigmaT:-sigmaT)*h.distance);
            betaD*=attenuation;betaS*=attenuation;
            if(!h.hit){
                if(h.escaped){vec3 environment=ptEnvironmentMIS(ray,previousSkyNormal,previousPdf,previousDelta);L.diffuse+=betaD*environment;L.specular+=betaS*environment;}
                break;
            }
            if(h.data==0u)break; // Traversal-budget exhaustion is never sky.
            if(bounce==0){
                s.p=h.position;s.ng=h.outward;
                s.n=safeNormalize(mat3(gbufferModelViewInverse)*guide.n);
                s.albedo=guide.albedo;s.m=guide.material;s.emission=emissionRadiance(s.m,s.albedo);
                if(dot(s.ng,ray)>0.0){s.ng=-s.ng;s.n=-s.n;}
            }else s=ptSurface(h,ray);
            // The directly visible emitter is evaluated analytically at full
            // resolution during resolve unless cloud visibility is stochastic.
            if(bounce>0||ptPrimaryCloudSegment(guide)){
                float w=previousDelta?1.0:ptMIS(previousPdf,ptHitLightPdf(h,previous,previousLightNormal,rng));
                L.diffuse+=betaD*s.emission*w;L.specular+=betaS*s.emission*w;
            }
        }
        // Shading waves live on a flat capture mesh. At grazing angles their
        // normal can face away from the incident ray; never flip it below the
        // geometric plane. Blend toward the facing geometric normal instead.
        if(!volume){
            float facing=dot(s.n,wo);
            if(facing<.05)s.n=safeNormalize(mix(s.n,s.ng,clamp((.05-facing)/max(dot(s.ng,wo)-facing,1e-5),0.0,1.0)));
        }
        vec3 weight;vec3 nextRay;bool splitPrimary=bounce==0&&!volume&&!ptDielectric(s);
        if(ptDielectric(s)){
            if(interfaceEvents>=PT_TRANSMISSION_DEPTH)break;
            interfaceEvents++;
            bool entering=dot(ray,h.outward)<0.0;
            if(seenOpaque&&!causticWeighted){
                betaD*=float(PT_CAUSTICS)*PT_CAUSTICS_STRENGTH;betaS*=float(PT_CAUSTICS)*PT_CAUSTICS_STRENGTH;causticWeighted=true;
            }
            bool optics=(s.m.a==1.0?WATER_ENABLED==1:PT_GLASS==1);
            float boundaryIor=optics?materialIor(s.m.a):1.0;
            float nextIor=entering?boundaryIor:(top>0?iors[top-1]:1.0);
            bool transmitted;nextRay=ptSampleDielectric(s,wo,iors[top],nextIor,rng,weight,transmitted);
            previousDelta=true;previousPdf=0.0;
            if(transmitted&&ptMax(weight)>0.0&&s.m.a!=33.0){
#if PT_REFRACTION == 1
                if(optics)etaScale*=nextIor*nextIor/(iors[top]*iors[top]);
#endif
                if(entering){
                    if(top>=14)break;
                    top++;iors[top]=nextIor;
                    absorption[top]=!optics?vec3(0):s.m.a==1.0?max(vec3(1)-vec3(WATER_R,WATER_G,WATER_B),vec3(.02))*WATER_ABSORPTION:ptGlassExtinction(s.albedo)*(s.m.a==32.0?6.0:1.0);
                    scattering[top]=optics&&s.m.a==1.0?WATER_SCATTERING:0.0;
                }else if(top>0)top--;
                else{iors[0]=1.0;absorption[0]=vec3(PT_AIR_DENSITY*.1);scattering[0]=PT_AIR_DENSITY;}
            }
        }else{
            if(scatteringEvents>=PT_BOUNCES)break;
            scatteringEvents++;
            bool continuation=scatteringEvents<PT_BOUNCES&&(volume||PT_GI==1||PT_REFLECTIONS==1);
            PtRadiance direct=ptDirectParts(s,wo,iors[top],sigmaT,continuation,rng);
            if(splitPrimary){L.diffuse+=betaS*direct.diffuse;L.specular+=betaS*direct.specular;}
            else{
                vec3 incoming=direct.diffuse*s.albedo+direct.specular;
                L.diffuse+=betaD*incoming;L.specular+=betaS*incoming;
            }
            if(!continuation)break;
            nextRay=ptSample(s,wo,iors[top],ptWorldLight(),rng,weight,previousPdf);
            if(!volume)seenOpaque=true;
            previousDelta=false;
        }
        if(splitPrimary){
            PtRadiance f=ptEvalParts(s,wo,nextRay);
            float scale=max(dot(s.n,nextRay),0.0)/max(previousPdf,1e-20);
            betaD=betaS*f.diffuse*scale*float(PT_GI)*PT_GI_STRENGTH;betaS*=f.specular*scale;
        }else{betaD*=weight;betaS*=weight;}
        vec3 physicalBeta=betaD*guide.albedo+betaS;
        if(ptMax(physicalBeta)<=0.0||any(isnan(physicalBeta))||any(isinf(physicalBeta)))break;
        previous=s.p;previousLightNormal=volume?vec3(0):s.ng;previousSkyNormal=volume?vec3(0):s.n;
        origin=s.p+(volume?nextRay:s.ng*sign(dot(nextRay,s.ng)))*RAY_BIAS;ray=nextRay;
        if(scatteringEvents>=3){
            float survive=clamp(ptMax(physicalBeta)*etaScale,.05,.95);
            if(ptRandom(rng)>survive)break;betaD/=survive;betaS/=survive;
        }
    }
    // A zero clamp keeps the estimator unbiased. This optional post-estimate
    // limiter trades caustic energy for fewer bright outliers when requested.
    if(PT_FIREFLY_CLAMP>0.0){
        float limit=min(1.0,PT_FIREFLY_CLAMP/max(ptMax(L.diffuse*guide.albedo+L.specular),1e-8));
        L.diffuse*=limit;L.specular*=limit;
    }
    L.diffuse=max(L.diffuse,vec3(0));L.specular=max(L.specular,vec3(0));return L;
}

// Unfiltered transport reference used by the physical regression fixtures.
vec3 ptIntegrate(PtGuide guide,inout uint rng){
    PtRadiance L=ptIntegrateParts(guide,rng);
    return L.diffuse*guide.albedo+L.specular+ptPrimaryEmission(guide);
}
