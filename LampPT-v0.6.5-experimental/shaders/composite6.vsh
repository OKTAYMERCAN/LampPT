#version 430 compatibility
// FULLSCREEN VERTEX: pass screen coordinates to this post-processing stage.
out vec2 texcoord;
void main(){gl_Position=ftransform();texcoord=gl_MultiTexCoord0.xy;}
