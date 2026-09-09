import bpy,sys,json,hashlib
from pathlib import Path
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import root_control as root,limb_ik,torso_controls,spine_ik_fk,eye_controls,foot_controls
SOURCE=Path(r'D:\Blender\Projects\Character\X\X.blend');REPORT=SOURCE.parent/'outputs/rig/root_extension_readonly_validation.json'
hash_before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
character_designer.register();bpy.ops.wm.open_mainfile(filepath=str(SOURCE));rig=bpy.data.objects['CoshaRig'];limb_ik._mode_set(bpy.context,rig,'POSE')
def update():root._update(bpy.context,rig)
def poses():update();return {p.name:p.matrix.copy() for p in rig.pose.bones}
def error(expected):return max(abs(rig.pose.bones[n].matrix[i][j]-m[i][j]) for n,m in expected.items() for i in range(4) for j in range(4))
before=poses();rest={b.name:torso_controls._state(b) for b in rig.data.bones};records={k:rig.data[k] for k in (spine_ik_fk.RECORD_KEY,eye_controls.RECORD_KEY,foot_controls.RECORD_KEY,torso_controls.RECORD_KEY)}
rec=root.build(bpy.context,rig);build_err=error(before);assert build_err<4e-4;assert len(rig.data.bones)==102
p=rig.pose.bones[rec['master']];motion=[]
for label,loc,rot,scale in [('move',(.1,-.08,.035),(0,0,0),1),('rotate',(.1,-.08,.035),(.13,-.11,.2),1),('scale',(.1,-.08,.035),(.13,-.11,.2),1.2)]:
 p.location,p.rotation_euler=loc,rot;p[root.SCALE_PROPERTY]=scale;update();e=error({n:p.matrix@m for n,m in before.items()});assert e<4e-4,(label,e);root.validate(rig);limb_ik._validate_inventory(rig);motion.append({'motion':label,'max_matrix_error':e});print('X_ROOT_MOTION',label,e,flush=True)
current=poses();expected={n:m for n,m in current.items() if n!=rec['master'] and n not in rec['controls']};root.remove(bpy.context,rig);update();remove_err=error(expected);assert remove_err<4e-4
assert {b.name:torso_controls._state(b) for b in rig.data.bones}==rest;assert records=={k:rig.data[k] for k in records};limb_ik._validate_inventory(rig)
report={'build_max_matrix_error':build_err,'whole_body_motion':motion,'remove_max_matrix_error':remove_err,'source_bones':len(rest),'rest_and_hierarchy_restored':True,'foot_spine_eye_records_unchanged':True,'saved':False,'source_file_unchanged':hashlib.sha256(SOURCE.read_bytes()).hexdigest()==hash_before}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8');print('X_ROOT_RESULT',json.dumps(report),flush=True)
