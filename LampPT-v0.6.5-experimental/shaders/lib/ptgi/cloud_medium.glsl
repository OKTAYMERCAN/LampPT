// CLOUD MEDIUM: world-anchored 3D density, shared by camera, continuation and
// shadow rays. No sky overlay or screen-space cloud color is composited here.
#ifndef LAMPPT_CLOUD_MEDIUM
#define LAMPPT_CLOUD_MEDIUM
#include "/lib/environment.glsl"
bool ptCloudsActive(){
#if VOLUMETRIC_CLOUDS == 1 && PT_VOLUMETRICS == 1
    return directionalSky()&&CLOUD_DENSITY>0.0&&CLOUD_COVERAGE>0.0;
#else
    return false;
#endif
}
float ptCloudHash(vec3 p){
    p=fract(p*.1031);p+=dot(p,p.yzx+33.33);return fract((p.x+p.y)*p.z);
}
float ptCloudNoise(vec3 p){
    vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
    return mix(mix(mix(ptCloudHash(i),ptCloudHash(i+vec3(1,0,0)),f.x),
                   mix(ptCloudHash(i+vec3(0,1,0)),ptCloudHash(i+vec3(1,1,0)),f.x),f.y),
               mix(mix(ptCloudHash(i+vec3(0,0,1)),ptCloudHash(i+vec3(1,0,1)),f.x),
                   mix(ptCloudHash(i+vec3(0,1,1)),ptCloudHash(i+vec3(1,1,1)),f.x),f.y),f.z);
}
float ptCloudDensity(vec3 relative){
    if(!ptCloudsActive())return 0.0;
    vec3 world=relative+cameraPosition;
    float h=(world.y-CLOUD_HEIGHT)/CLOUD_THICKNESS;
    if(h<=0.0||h>=1.0)return 0.0;
    float angle=CLOUD_WIND_ANGLE*(PI/180.0);
    world.xz-=vec2(cos(angle),sin(angle))*frameTimeCounter*CLOUD_WIND_SPEED;
    vec3 p=vec3(world.x/CLOUD_SCALE,h*1.7,world.z/CLOUD_SCALE);
    float shape=ptCloudNoise(p)*.625+ptCloudNoise(p*2.03+17.7)*.25+ptCloudNoise(p*4.11-8.1)*.125;
    float threshold=1.0-CLOUD_COVERAGE;
    float body=smoothstep(threshold,threshold+.24,shape);
    float vertical=smoothstep(0.0,.18,h)*(1.0-smoothstep(.55,1.0,h));
    return clamp(body*vertical,0.0,1.0)*CLOUD_DENSITY;
}
bool ptCloudInterval(vec3 origin,vec3 direction,float limit,out vec2 interval){
    interval=vec2(0);
    if(!ptCloudsActive()||limit<=0.0)return false;
    float y=origin.y+cameraPosition.y,hi=CLOUD_HEIGHT+CLOUD_THICKNESS;
    if(abs(direction.y)<1e-6){
        if(y<=CLOUD_HEIGHT||y>=hi)return false;
        interval=vec2(0,min(limit,CLOUD_DISTANCE));return interval.y>0.0;
    }
    vec2 crossings=(vec2(CLOUD_HEIGHT,hi)-y)/direction.y;
    interval=vec2(max(min(crossings.x,crossings.y),0.0),min(max(crossings.x,crossings.y),min(limit,CLOUD_DISTANCE)));
    return interval.y>interval.x;
}
float ptCloudEnvironmentDistance(){return ptCloudsActive()?max(PT_DISTANCE,CLOUD_DISTANCE):PT_DISTANCE;}
// Finite midpoint quadrature approximates the heterogeneous optical depth.
// Invert an exponential optical-depth sample in the SAME piecewise medium.
// This is a bounded numerical medium, not unbounded rejection tracking: cost
// cannot explode in dense clouds. More steps resolve smaller density features.
float ptCloudFreeFlight(vec3 origin,vec3 direction,float limit,float opticalDepth){
    vec2 interval;if(!ptCloudInterval(origin,direction,limit,interval))return 1e30;
    float dt=(interval.y-interval.x)/float(CLOUD_STEPS);
    for(int i=0;i<CLOUD_STEPS;i++){
        float start=interval.x+float(i)*dt;
        float extinction=ptCloudDensity(origin+direction*(start+.5*dt));
        float segment=extinction*dt;
        if(extinction>0.0&&opticalDepth<segment)return start+opticalDepth/extinction;
        opticalDepth-=segment;
    }
    return 1e30;
}
float ptCloudTransmittance(vec3 origin,vec3 direction,float limit){
#if CLOUD_SHADOWS == 1
    vec2 interval;if(!ptCloudInterval(origin,direction,limit,interval))return 1.0;
    float dt=(interval.y-interval.x)/float(CLOUD_SHADOW_STEPS),tau=0.0;
    for(int i=0;i<CLOUD_SHADOW_STEPS;i++){
        tau+=ptCloudDensity(origin+direction*(interval.x+(float(i)+.5)*dt))*dt;
    }
    return exp(-tau);
#else
    return 1.0;
#endif
}
#endif
