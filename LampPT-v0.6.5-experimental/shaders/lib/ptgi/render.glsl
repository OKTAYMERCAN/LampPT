// PT CAMERA PASS: separate diffuse irradiance and residual transport while
// following the same camera paths. Material textures are restored at full size.
#include "/lib/ptgi/context.glsl"
#include "/lib/ptgi/integrator.glsl"
in vec2 texcoord;
/* RENDERTARGETS:2,8 */
layout(location=0)out vec4 outDiffuse;
layout(location=1)out vec4 outSpecular;
void main(){
    PtGuide g=ptGuide(texcoord);
    outDiffuse=vec4(0);outSpecular=vec4(0);
    if(g.valid==2){outSpecular=vec4(srgbToLinear(texture2D(colortex0,texcoord).rgb),0);return;}
    uvec2 pixel=uvec2(gl_FragCoord.xy);
    uint rng=ptHash(pixel.x+pixel.y*65537u+uint(frameCounter%1048576)*747796405u+2891336453u);
    PtRadiance sum;sum.diffuse=vec3(0);sum.specular=vec3(0);
    int sampleCount=PT_SAMPLES;
#if WATER_ENABLED == 1 && PT_CAUSTICS == 1
    // Extra independent camera paths only for water-covered/underwater pixels.
    // This reduces caustic variance without multiplying the dry-land workload
    // or adding a second light source / a projected caustic texture.
    if(isEyeInWater==1||(g.valid==1&&g.material.a==1.0))sampleCount*=PT_WATER_SAMPLES;
#endif
    for(int i=0;i<sampleCount;i++){
        PtRadiance path=ptIntegrateParts(g,rng);
        sum.diffuse+=path.diffuse;sum.specular+=path.specular;
    }
    // Keep HDR values finite without a mandatory artistic firefly clamp.
    outDiffuse=vec4(min(sum.diffuse/float(sampleCount),vec3(65000)),0);
    outSpecular=vec4(min(sum.specular/float(sampleCount),vec3(65000)),0);
}
