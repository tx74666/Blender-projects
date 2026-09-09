import sys
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\tests')
import test_root_control_blender as t
orig=t.root._verify_pose
def verify(r,d):
 try:orig(r,d)
 except Exception:
  e=t.limb_ik_fk._pose_errors(r,d)
  worst=sorted([(n,max(abs(r.pose.bones[n].matrix[i][j]-m[i][j]) for i in range(4) for j in range(4))) for n,m in d.items()],key=lambda p:p[1],reverse=True)[:7]
  print('ROOT_REMOVE_ERROR',e,worst,flush=True)
  raise
t.root._verify_pose=verify
t.test_whole_body_follow_roundtrip_and_removal()
