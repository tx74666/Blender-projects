import sys,json
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\tests')
import test_root_control_blender as t
r=t.fixture();rec=t.root.build(t.bpy.context,r);p=r.pose.bones[rec['master']];p.rotation_euler=(.08,-.11,.05);p[t.root.SCALE_PROPERTY]=1.11;t.update(r)
d=t.poses(r)
orig=t.limb_ik_fk._match_ik
def errors():
 return sorted([(n,max(abs(r.pose.bones[n].matrix[i][j]-m[i][j]) for i in range(4) for j in range(4))) for n,m in d.items() if n!=rec['master']], key=lambda x:x[1],reverse=True)[:9]
def match(*args,**kw):
 print('BEFORE_MATCH',args[3]['chain'],errors(),flush=True)
 result=orig(*args,**kw)
 print('AFTER_MATCH',args[3]['chain'],errors(),flush=True)
 return result
t.limb_ik_fk._match_ik=match
try: t.root.remove(t.bpy.context,r)
except Exception as e: print('REMOVE_FAILED',str(e),flush=True)
