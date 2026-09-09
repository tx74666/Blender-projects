"""Actual-X explicit spine reset and separate fresh-process persistence check."""
import bpy, hashlib, json, math, sys
from array import array
from pathlib import Path
from mathutils import Matrix, Vector
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons']
import character_designer
from character_designer import spine_ik_fk as spine, torso_controls as torso, eye_controls as eyes, limb_ik, foot_controls

ROOT=Path(r'D:\Blender\Projects\Character\X\outputs\rig')
SOURCE=Path(r'D:\Blender\Projects\Character\X\X.blend')
POSED=ROOT/'X_spine_ik_fk_050_preview.blend'
PREVIEW=ROOT/'X_spine_ik_fk_050_reset_preview.blend'
REPORT=ROOT/'latest_x_spine_reset_050_validation.json'
EXPECTED=ROOT/'X_spine_ik_fk_050_reset_preview_expected.json'
REOPEN_REPORT=ROOT/'latest_x_spine_reset_050_reopen_validation.json'
REOPEN='--reopen' in sys.argv

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def persist(path,value):path.write_text(json.dumps(value,indent=2),encoding='utf-8')
def update():spine._update(bpy.context,rig)
def matrices():
    update()
    return {pb.name:pb.matrix.copy() for pb in rig.pose.bones}
def matrix_error(expected):
    return max((abs(rig.pose.bones[name].matrix[i][j]-value[i][j]) for name,value in expected.items() for i in range(4) for j in range(4)),default=0.0)
def mesh_digest():
    result={}
    dg=bpy.context.evaluated_depsgraph_get()
    for obj in bpy.data.objects:
        if obj.type!='MESH' or not any(mod.type=='ARMATURE' and mod.object==rig for mod in obj.modifiers):continue
        evaluated=obj.evaluated_get(dg)
        mesh=evaluated.to_mesh()
        coords=array('f',[0.0])*(len(mesh.vertices)*3)
        mesh.vertices.foreach_get('co',coords)
        result[obj.name]=hashlib.sha256(coords.tobytes()).hexdigest()
        evaluated.to_mesh_clear()
    return result
def weights():
    return {obj.name:hashlib.sha256(repr((tuple(group.name for group in obj.vertex_groups),
             tuple(tuple((group.group,group.weight) for group in vertex.groups) for vertex in obj.data.vertices))).encode()).hexdigest()
            for obj in bpy.data.objects if obj.type=='MESH'}
def neutral_expected(record):
    # Independent check for X's full-inheritance chain: transport native rest by Hips.
    hips=rig.pose.bones[record['hips']]
    transport=hips.matrix@hips.bone.matrix_local.inverted()
    return {name:transport@rig.data.bones[name].matrix_local for name in record['sources']}
def check_reset(label):
    record=spine.validate(rig)
    affected=set(record['bones'].values())|set(record['torso_bones'])
    before=spine._pose_snapshot(rig)
    desired=neutral_expected(record)
    desired[record['hips']]=rig.pose.bones[record['hips']].matrix.copy()
    value=rig.pose.bones[record['chest']][spine.PROPERTY]
    result=spine.reset(bpy.context,rig)
    error=matrix_error(desired)
    assert error<=4e-4,(label,error)
    assert rig.pose.bones[record['chest']][spine.PROPERTY]==value
    identity=Matrix.Identity(4)
    affected_error=max(abs(rig.pose.bones[name].matrix_basis[i][j]-identity[i][j]) for name in affected for i in range(4) for j in range(4))
    unrelated_error=max(abs(rig.pose.bones[name].matrix_basis[i][j]-basis[i][j])
             for name,(_mode,basis) in before.items() if name not in affected for i in range(4) for j in range(4))
    assert affected_error<=2e-6 and unrelated_error<=2e-6
    limb_ik._validate_inventory(rig)
    report['checks'][label]={'result':result,'independent_neutral_matrix_error':error,
                            'affected_basis_identity_error':affected_error,'unrelated_basis_error':unrelated_error}
    print('X_SPINE_RESET_CHECK',label,json.dumps(report['checks'][label]),flush=True)

source_hash,posed_hash=sha(SOURCE),sha(POSED)
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=str(PREVIEW if REOPEN else POSED))
rig=bpy.data.objects['CoshaRig']
limb_ik._mode_set(bpy.context,rig,'POSE')
update()
record=spine.validate(rig)
eyes.validate(rig)
if REOPEN:
    expected=json.loads(EXPECTED.read_text(encoding='utf-8'))
    error=matrix_error({name:Matrix(value) for name,value in expected['pose'].items()})
    neutral_error=matrix_error(neutral_expected(record))
    result={'status':'passed','fresh_process':True,'preview':str(PREVIEW),'preview_sha256':sha(PREVIEW),
            'mode':spine.mode_for_rig(rig),'all_pose_matrix_error':error,'native_neutral_matrix_error':neutral_error,
            'evaluated_mesh_bitwise_equal':mesh_digest()==expected['mesh_digest'],
            'source_sha256_unchanged':sha(SOURCE)==source_hash,'posed_preview_unchanged':sha(POSED)==posed_hash}
    assert error<=4e-4 and neutral_error<=4e-4 and result['mode']=='IK'
    limb_ik._validate_inventory(rig)
    persist(REOPEN_REPORT,result)
    print('X_SPINE_RESET_FRESH_REOPEN',json.dumps(result),flush=True)
    raise SystemExit(0)

report={'source':str(SOURCE),'input_preview':str(POSED),'module_path':spine.__file__,
        'source_sha256_before':source_hash,'posed_preview_sha256_before':posed_hash,'status':'running','checks':{}}
try:
    rest={bone.name:torso._state(bone) for bone in rig.data.bones}
    before_weights=weights()
    other_rigs={obj.name:{pb.name:pb.matrix.copy() for pb in obj.pose.bones} for obj in bpy.data.objects if obj.type=='ARMATURE' and obj!=rig}
    records={key:rig.data[key] for key in (torso.RECORD_KEY,foot_controls.RECORD_KEY,eyes.RECORD_KEY)}
    hips=rig.pose.bones[record['hips']]
    hips_mode,hips_basis=hips.rotation_mode,hips.matrix_basis.copy()
    check_reset('posed_IK_to_native_neutral')
    spine.switch(bpy.context,rig,'FK')
    hips.rotation_mode='XYZ'
    hips.rotation_euler.z+=.07
    hips.location.x+=.005
    rig.pose.bones[record['bend']].rotation_euler=(.09,-.03,.02)
    rig.pose.bones[record['fk_controls'][record['sources'][1]]].rotation_euler.x-=.05
    update()
    check_reset('posed_FK_under_moved_Hips_to_native_neutral')
    hips.rotation_mode=hips_mode
    hips.matrix_basis=hips_basis
    update()
    spine.switch(bpy.context,rig,'IK')
    check_reset('final_original_Hips_IK_native_neutral')
    report['preservation']={'rest_equal':all(torso._same_rest(rig.data.bones[name],state) for name,state in rest.items()),
                            'weights_equal':weights()==before_weights,'existing_records_equal':records=={key:rig.data[key] for key in records}}
    other_errors={name:max(abs(bpy.data.objects[name].pose.bones[bone].matrix[i][j]-matrix[i][j]) for bone,matrix in values.items() for i in range(4) for j in range(4))
                  for name,values in other_rigs.items()}
    report['preservation']['other_armatures']=other_errors
    assert all(report['preservation'][key] for key in ('rest_equal','weights_equal','existing_records_equal'))
    assert all(value<=1e-6 for value in other_errors.values())
    expected={'pose':{name:[list(row) for row in matrix] for name,matrix in matrices().items()},'mesh_digest':mesh_digest()}
    persist(EXPECTED,expected)
    bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW),check_existing=False)
    report['preview']={'path':str(PREVIEW),'sha256':sha(PREVIEW),'mode':spine.mode_for_rig(rig)}
    report['status']='passed'
except Exception as exc:
    report['status']='failed'
    report['error']=repr(exc)
    raise
finally:
    report['source_sha256_after']=sha(SOURCE)
    report['source_unchanged']=sha(SOURCE)==source_hash
    report['posed_preview_unchanged']=sha(POSED)==posed_hash
    persist(REPORT,report)
    print('X_SPINE_RESET_RESULT',json.dumps(report),flush=True)
