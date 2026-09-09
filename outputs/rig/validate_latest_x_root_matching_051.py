import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import bpy
from character_designer import limb_ik,limb_ik_fk as fk,spine_ik_fk as spine,root_control as root
source=Path(r'D:\Blender\Projects\Character\X\X.blend');checksum=lambda:hashlib.sha256(source.read_bytes()).hexdigest()
result={'source_sha_before':checksum(),'checks':[]}
bpy.ops.wm.open_mainfile(filepath=str(source))
r=bpy.data.objects['CoshaRig'];bpy.context.view_layer.objects.active=r;r.select_set(True)
if r.mode!='POSE':bpy.ops.object.mode_set(mode='POSE')
rootrec=root.build(bpy.context,r);p=r.pose.bones[rootrec['master']]
p.location=(.15,-.07,.06);p.rotation_euler=(.12,-.15,.2);p[root.SCALE_PROPERTY]=1.17;fk._update(bpy.context,r)
def native():return {pb.name:pb.matrix.copy() for pb in r.pose.bones if pb.bone.get(limb_ik.OWNER_KEY) not in limb_ik.GENERATED_CONTROL_OWNERS}
def error(before):return max(abs(r.pose.bones[n].matrix[i][j]-m[i][j]) for n,m in before.items() for i in range(4) for j in range(4))
for key,data in limb_ik._validate_inventory(r)['rigs'].items():
 for endpoint in ('FK','IK'):
  before=native();entry={'limb':str(key),'from':'endpoint','to':endpoint}
  try:entry['result']=fk.switch_limb(bpy.context,r,key,endpoint,keyframe=False);entry['native_matrix_error']=error(before)
  except Exception as exc:entry['failure']=str(exc);entry['rollback_matrix_error']=error(before)
  result['checks'].append(entry)
for key,data in limb_ik._validate_inventory(r)['rigs'].items():
 for endpoint in ('FK','IK'):
  target=r.pose.bones[data['target'].name];target.location.x+=.007;target[fk.PROPERTY]=.5;fk._update(bpy.context,r)
  before=native();entry={'limb':str(key),'from':'blend','to':endpoint}
  try:entry['result']=fk.switch_limb(bpy.context,r,key,endpoint,keyframe=False);entry['native_matrix_error']=error(before)
  except Exception as exc:entry['failure']=str(exc);entry['rollback_matrix_error']=error(before)
  result['checks'].append(entry)
rec=spine.get_record(r)
for endpoint in ('FK','IK'):
 r.pose.bones[rec['chest']].location.x+=.01;r.pose.bones[rec['chest']][spine.PROPERTY]=.5;fk._update(bpy.context,r)
 before=native();entry={'limb':'SPINE','from':'blend','to':endpoint}
 try:entry['result']=spine.switch(bpy.context,r,endpoint);entry['native_matrix_error']=error(before)
 except Exception as exc:entry['failure']=str(exc);entry['rollback_matrix_error']=error(before)
 result['checks'].append(entry)
result['source_sha_after']=checksum();result['source_unchanged']=result['source_sha_before']==result['source_sha_after']
Path(r'D:\Blender\Projects\Character\X\outputs\rig\latest_x_root_matching_051_validation.json').write_text(json.dumps(result,indent=2))
print('ACTUAL_X_ROOT_MATCH',json.dumps(result,indent=2))
assert result['source_unchanged'] and not any('failure' in e for e in result['checks'])
