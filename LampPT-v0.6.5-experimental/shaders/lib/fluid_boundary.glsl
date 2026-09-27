// PHYSICAL FLUID BOUNDARIES: Sodium can submit an inward copy of a fluid quad.
// at_midBlock is the vector from the vertex to its owning block center * 64.
// Recover the physical outward side before wave shading or medium-stack updates.
#ifndef LAMPPT_FLUID_BOUNDARY
#define LAMPPT_FLUID_BOUNDARY
vec3 fluidOutward(vec3 normal, vec3 midBlock){
    vec3 local=.5-midBlock/64.0;
    if(abs(normal.y)>.01){
        // A shallow top is still a top, even below the block's center. Only
        // the bottom fluid face lies at the lower block boundary.
        float side=local.y>.01?1.0:-1.0;
        return normal*(normal.y*side<0.0?-1.0:1.0);
    }
    int axis=abs(normal.x)>abs(normal.z)?0:2;
    float side=local[axis]>=.5?1.0:-1.0;
    return normal*(normal[axis]*side<0.0?-1.0:1.0);
}
#endif
