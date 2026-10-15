"""Exact numeric representation of the production guide/history buffers."""
import numpy as np
def rgb24(c):
 q=np.rint(np.clip(c,0,1)*255).astype(np.uint32)
 return float(q[0]|(q[1]<<8)|(q[2]<<16))
def normal24(n):
 n=np.asarray(n,float);n/=np.abs(n).sum();xy=n[:2]
 if n[2]<0:xy=(1-np.abs(xy[::-1]))*np.where(xy>=0,1,-1)
 q=np.rint((xy*.5+.5)*4095).astype(np.uint32)
 return float(q[0]|(q[1]<<12))
def material24(m):return rgb24([m[0],1 if m[1]<0 else m[1],m[3]/255])
