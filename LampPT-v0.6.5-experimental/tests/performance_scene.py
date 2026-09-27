#!/usr/bin/env python3
"""GL_TIME_ELAPSED comparison of actual post-capture draws on llvmpipe.

Reports software-renderer draw cost only: excludes capture, BVH construction,
allocation, transfer, compilation and Minecraft. Never convert this to RTX FPS.
Run comparison cases sequentially with no other rendering test in progress.
"""
import argparse,json,os,statistics
from pathlib import Path
import numpy as np
import gl_runtime as rt
p=argparse.ArgumentParser();p.add_argument('--pack',type=Path);p.add_argument('--scale',type=int,default=40);p.add_argument('--label',default='v065-40');p.add_argument('--frames',type=int,default=12)
p.add_argument('--filter',type=int,choices=[0,1]);args=p.parse_args()
if args.pack:rt.ROOT=args.pack.resolve()/'shaders'
import scene_review as s
from pipeline_routing import Pipeline
s.W,s.H=257,145;s.P=np.array(rt.projection,copy=True);s.P[0,0]*=s.H/s.W
rt.uniforms.update(gbufferProjection=s.P,gbufferProjectionInverse=np.linalg.inv(s.P))
s.OUT=Path(__file__).parent/'ptgi-evidence'
original=Pipeline.pass_
def timed(self,name,options):
    rt.draw_timer_label=name
    return original(self,name,options)
Pipeline.pass_=timed
rt.draw_timer_enabled=True
# Capture geometry/work is the same in both releases, and held at the small
# test capacity. All frame-dependent lighting still uses production code.
options={'GEOMETRY_BUDGET':65536,'shadowMapResolution':128,'PT_RESOLUTION':args.scale,'DITHER':0,
         'CLOUD_WIND_SPEED':'0.0'}
if args.filter is not None:options['PT_UPSCALE_FILTER']=args.filter
frame,passes,_,_,_=s.render(options,sun=(.3,.9,.2),frames=args.frames)
s.save(args.label+'-scene',frame)
records=[x for x in rt.draw_times if 3<=x['frame']<args.frames and x['stage'].startswith('composite')]
# final draw inherits the last stage label; remove it using its output size and
# position in the recorded stream (scene_review calls final once after frames).
if records:records=records[:-1]
stages={name:statistics.median(x['nanoseconds'] for x in records if x['stage']==name)/1e6 for name in sorted(set(x['stage'] for x in records))}
frames={i:sum(x['nanoseconds'] for x in records if x['frame']==i)/1e6 for i in range(3,args.frames)}
report={'label':args.label,'scale':args.scale,'display':[s.W,s.H],
        'option_overrides':options,
        'llvmpipe_threads':os.environ.get('LP_NUM_THREADS','driver default'),
        'median_draw_ms_by_stage':stages,'median_composite_draw_ms':statistics.median(frames.values()),
        'frames_measured':len(frames),'renderer':rt.gl['GetString'](0x1F01).decode(),
        'scope':'GL_TIME_ELAPSED software-renderer draws only. Excludes geometry capture/BVH, allocation, transfers and Minecraft. Not GPU-game FPS.',
        'finite_image':bool(np.isfinite(frame).all())}
assert report['finite_image'] and len(stages)>=5 and all(v>0 for v in stages.values()),report
(s.OUT/(args.label+'-timing.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
