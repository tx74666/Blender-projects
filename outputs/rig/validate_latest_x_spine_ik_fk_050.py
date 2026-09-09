"""Disposable actual-X integration; source file is never saved by this script."""
import bpy
import hashlib
import json
import math
import sys
from array import array
from datetime import datetime
from pathlib import Path
from mathutils import Matrix, Vector

sys.path[:0] = [r'D:\MyRepository\Blender-addons-by-Randy\addons']
import character_designer
from character_designer import spine_ik_fk as spine, eye_controls as eyes, torso_controls as torso
from character_designer import limb_ik, foot_controls, bone_collections

ROOT = Path(r'D:\Blender\Projects\Character\X\outputs\rig')
SOURCE = Path(r'D:\Blender\Projects\Character\X\X.blend')
PREVIEW = ROOT / 'X_spine_ik_fk_050_preview.blend'
REPORT = ROOT / 'latest_x_spine_ik_fk_050_validation.json'
EXPECTED = ROOT / 'X_spine_ik_fk_050_preview_expected.json'
REOPEN_REPORT = ROOT / 'latest_x_spine_ik_fk_050_reopen_validation.json'
IS_REOPEN = '--reopen' in sys.argv

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def persist(path, data):
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')

def update():
    spine._update(bpy.context, rig)

def pose_snapshot(names=None):
    update()
    return {pb.name: pb.matrix.copy() for pb in rig.pose.bones if names is None or pb.name in names}

def pose_error(expected, obj=None):
    obj = rig if obj is None else obj
    return max((abs(obj.pose.bones[name].matrix[i][j] - matrix[i][j])
                for name, matrix in expected.items() for i in range(4) for j in range(4)), default=0.0)

def pose_json(expected):
    return {name: [list(row) for row in matrix] for name, matrix in expected.items()}

def verify_pose(label, expected, limit=4e-4):
    update()
    value = pose_error(expected)
    assert math.isfinite(value) and value <= limit, (label,value)
    report['checks'][label] = value
    return value

def mesh_snapshot():
    result = {}
    dg = bpy.context.evaluated_depsgraph_get()
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not any(mod.type=='ARMATURE' and mod.object==rig for mod in obj.modifiers):
            continue
        evaluated = obj.evaluated_get(dg)
        mesh = evaluated.to_mesh()
        coords = array('f', [0.0]) * (len(mesh.vertices)*3)
        mesh.vertices.foreach_get('co', coords)
        result[obj.name] = coords
        evaluated.to_mesh_clear()
    return result

def mesh_digest():
    return {name: hashlib.sha256(values.tobytes()).hexdigest() for name,values in mesh_snapshot().items()}

def verify_mesh(label, expected):
    current = mesh_snapshot()
    assert current.keys()==expected.keys()
    errors={name:max((abs(a-b) for a,b in zip(values,current[name])), default=0.0)
            for name,values in expected.items()}
    assert all(value<=4e-4 for value in errors.values()), (label,errors)
    report['checks'][label]=errors

def weight_digest(names):
    result={}
    for name in names:
        obj=bpy.data.objects[name]
        payload=(tuple(group.name for group in obj.vertex_groups),
                 tuple(tuple((group.group,group.weight) for group in vertex.groups) for vertex in obj.data.vertices))
        result[name]=hashlib.sha256(repr(payload).encode()).hexdigest()
    return result

def preserve_names():
    omitted=set(spine.get_record(rig)['bones'].values()) | set(torso.get_record(rig)['bones'].values())
    return set(rig.pose.bones.keys())-omitted

def geometry(chain):
    directions=[(rig.pose.bones[name].tail-rig.pose.bones[name].head).normalized() for name in chain]
    root=rig.pose.bones[chain[0]].head.copy()
    endpoint=rig.pose.bones[chain[-1]].head.copy()
    axis=(endpoint-root).normalized()
    return {'sources':list(chain), 'lengths':[rig.data.bones[name].length for name in chain],
            'source_segment_angles_degrees':[math.degrees(a.angle(b)) for a,b in zip(directions,directions[1:])],
            'lower_chain_segment_angles_degrees':[math.degrees(a.angle(b)) for a,b in zip(directions[:-1],directions[1:-1])],
            'lower_chain_radial_bend':max((rig.pose.bones[name].head-root-axis*(rig.pose.bones[name].head-root).dot(axis)).length for name in chain),
            'root_to_chest_length':(endpoint-root).length,
            'posed_gaps':[(rig.pose.bones[a].tail-rig.pose.bones[b].head).length for a,b in zip(chain,chain[1:])]}

source_hash=sha(SOURCE)
stat=SOURCE.stat()
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=str(PREVIEW if IS_REOPEN else SOURCE))
rig=bpy.data.objects['CoshaRig']
limb_ik._mode_set(bpy.context,rig,'POSE')
update()

if IS_REOPEN:
    expected=json.loads(EXPECTED.read_text(encoding='utf-8'))
    spine.validate(rig)
    eyes.validate(rig)
    torso.validate(rig)
    limb_ik._validate_inventory(rig)
    native_error=pose_error({name:Matrix(value) for name,value in expected['pose'].items()})
    assert native_error<=4e-4,native_error
    same_mesh=mesh_digest()==expected['mesh_digest']
    result={'status':'passed','fresh_process':True,'preview':str(PREVIEW),'preview_sha256':sha(PREVIEW),
            'mode':spine.mode_for_rig(rig),'all_pose_matrix_error':native_error,
            'evaluated_mesh_bitwise_equal':same_mesh,'source_sha256_unchanged':sha(SOURCE)==source_hash,
            'spine_record_equal':rig.data[spine.RECORD_KEY]==expected['spine_record'],
            'eye_record_equal':rig.data[eyes.RECORD_KEY]==expected['eye_record']}
    assert result['mode']=='IK' and result['source_sha256_unchanged']
    assert result['spine_record_equal'] and result['eye_record_equal']
    persist(REOPEN_REPORT,result)
    print('X_SPINE_FRESH_REOPEN_RESULT',json.dumps(result),flush=True)
    raise SystemExit(0)

report={'source':str(SOURCE),'source_size':stat.st_size,'source_saved_mtime':datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'source_sha256_before':source_hash,'checks':{},'status':'running','module_path':spine.__file__}
try:
    original=torso.validate(rig)
    assert original is not None
    chain=original['sources']
    report['baseline_geometry']=geometry(chain)
    report['initial_extensions']={'eye':eyes.get_record(rig) is not None,'spine_ik':spine.get_record(rig) is not None}
    print('X_SPINE_INITIAL_GEOMETRY',json.dumps(report['baseline_geometry']),flush=True)
    rest={bone.name:torso._state(bone) for bone in rig.data.bones}
    original_names=set(rest)
    original_native=set(spine._matrices(rig))
    meshes=[obj.name for obj in bpy.data.objects if obj.type=='MESH']
    weights=weight_digest(meshes)
    digest=limb_ik._armature_digest(rig)
    original_records={key:rig.data[key] for key in (torso.RECORD_KEY,foot_controls.RECORD_KEY)}
    other_rigs={obj.name:{pb.name:pb.matrix.copy() for pb in obj.pose.bones}
                for obj in bpy.data.objects if obj.type=='ARMATURE' and obj!=rig}
    initial_pose=pose_snapshot()
    initial_mesh=mesh_snapshot()
    eye_record=eyes.build(bpy.context,rig)
    spine_record=spine.build(bpy.context,rig)
    verify_pose('combined_build_pose',initial_pose)
    verify_mesh('combined_build_mesh',initial_mesh)
    limb_ik._validate_inventory(rig)
    report['build']={'native_bones':len(original_native),'preexisting_bones':len(original_names),
                     'added_eye_bones':len(eye_record['bones']),'added_spine_bones':len(spine_record['bones'])}
    print('X_SPINE_INITIAL_BUILD',json.dumps({'build':report['build'],'checks':report['checks']}),flush=True)
    persist(REPORT,report)

    # Baseline FK -> IK -> FK retains all pre-existing native and control matrices.
    baseline=pose_snapshot()
    spine.switch(bpy.context,rig,'IK')
    verify_pose('baseline_fk_to_ik_all_existing', {n:m for n,m in baseline.items() if n not in spine_record['bones'].values()})
    baseline_ik=pose_snapshot()
    spine.switch(bpy.context,rig,'FK')
    verify_pose('baseline_ik_to_fk_native_and_other_controls',{n:m for n,m in baseline_ik.items() if n in preserve_names()})
    spine.switch(bpy.context,rig,'IK')

    # Pure axial compression at Shape zero, restored before authored pose checks.
    chest=rig.pose.bones[spine_record['chest']]
    shape=rig.pose.bones[spine_record['shape']]
    baseline=pose_snapshot()
    chest_basis=chest.matrix_basis.copy()
    root=rig.pose.bones[chain[0]].head.copy()
    span=(chest.head-root).length
    compression=span*0.03
    target=chest.matrix.copy()
    target.translation-=(chest.head-root).normalized()*compression
    chest.matrix=target
    update()
    endpoint_error=(rig.pose.bones[chain[-1]].head-chest.head).length
    report['axial_shape_zero']={'compression_fraction':.03,'compression_distance':compression,
                                'endpoint_error':endpoint_error,'solves_within_2e_4':endpoint_error<=2e-4,
                                'shape_rotation':list(shape.rotation_euler)}
    chest.matrix_basis=chest_basis
    update()
    verify_pose('axial_excursion_return',baseline)
    print('X_SPINE_AXIAL_RESULT',json.dumps(report['axial_shape_zero']),flush=True)

    # Simultaneous existing feet/limbs/Bend/FK and eye pose, then match into IK.
    spine.switch(bpy.context,rig,'FK')
    rig.pose.bones[original['bend']].rotation_euler.x+=.06
    rig.pose.bones[original['controls'][chain[1]]].rotation_euler.x-=.045
    feet=foot_controls.records(rig)
    rig.pose.bones[feet['L']['roll']].rotation_euler.x+=.10
    rig.pose.bones[feet['R']['toe_control']].rotation_euler.x-=.08
    inventory=limb_ik._validate_inventory(rig)
    limb_targets={str(key):rig_info['target'].name for key,rig_info in inventory['rigs'].items()}
    for i,name in enumerate(limb_targets.values()):
        rig.pose.bones[name].location.x+=(.002 if i%2 else -.002)
    rig.pose.bones[eye_record['master']].location+=Vector((.008,0,.004))
    rig.pose.bones[eye_record['targets']['L']].location.z+=.002
    combined=pose_snapshot(preserve_names())
    combined_mesh=mesh_snapshot()
    spine.switch(bpy.context,rig,'IK')
    verify_pose('combined_fk_to_ik_native_and_other_controls',combined)
    verify_mesh('combined_fk_to_ik_mesh',combined_mesh)

    chest=rig.pose.bones[spine_record['chest']]
    shape=rig.pose.bones[spine_record['shape']]
    chest.location+=Vector((.006,-.008,.003))
    chest.rotation_euler.z+=.045
    shape.rotation_euler=(.06,-.025,.018)
    rig.pose.bones[eye_record['targets']['R']].location.x-=.002
    moved=pose_snapshot(preserve_names())
    moved_mesh=mesh_snapshot()
    spine.switch(bpy.context,rig,'FK')
    verify_pose('moved_ik_to_fk_native_and_other_controls',moved)
    verify_mesh('moved_ik_to_fk_mesh',moved_mesh)
    spine.switch(bpy.context,rig,'IK')
    verify_pose('moved_fk_to_ik_native_and_other_controls',moved)
    verify_mesh('moved_fk_to_ik_mesh',moved_mesh)
    report['simultaneous_modules']={'limb_targets':limb_targets,'feet':list(feet),'torso':True,'eyes':True}

    # Save only the separately authorized IK preview; fresh process opens it next.
    preview_pose=pose_snapshot()
    preview_expected={'pose':pose_json(preview_pose),'mesh_digest':mesh_digest(),
                      'spine_record':rig.data[spine.RECORD_KEY],'eye_record':rig.data[eyes.RECORD_KEY]}
    persist(EXPECTED,preview_expected)
    bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW),check_existing=False)
    report['preview']={'path':str(PREVIEW),'sha256':sha(PREVIEW),'mode':spine.mode_for_rig(rig)}

    removal_pose=pose_snapshot(preserve_names())
    removal_mesh=mesh_snapshot()
    spine.remove(bpy.context,rig)
    verify_pose('spine_removal_native_and_other_controls',removal_pose)
    verify_mesh('spine_removal_mesh',removal_mesh)
    eye_removal=pose_snapshot()
    eye_removal={n:m for n,m in eye_removal.items() if n not in eye_record['bones'].values()}
    eyes.remove(bpy.context,rig)
    verify_pose('eye_removal_remaining_all_controls',eye_removal)
    verify_mesh('eye_removal_mesh',removal_mesh)
    assert set(rig.data.bones.keys())==original_names
    assert all(torso._same_rest(rig.data.bones[name],state) for name,state in rest.items())
    assert weight_digest(meshes)==weights
    assert limb_ik._armature_digest(rig)==digest
    assert original_records=={key:rig.data[key] for key in original_records}
    limb_ik._validate_inventory(rig)
    other_errors={name:pose_error(expected,bpy.data.objects[name]) for name,expected in other_rigs.items()}
    assert all(value<=1e-6 for value in other_errors.values()),other_errors
    report['preservation']={'rest_bones':len(rest),'weights_equal':True,'armature_digest_equal':True,
                            'existing_records_equal':True,'other_armatures':other_errors,
                            'extension_removal_clean':spine.get_record(rig) is None and eyes.get_record(rig) is None}
    report['status']='passed'
except Exception as exc:
    report['status']='failed'
    report['error']=repr(exc)
    raise
finally:
    report['source_sha256_after']=sha(SOURCE)
    report['source_unchanged']=report['source_sha256_after']==source_hash
    persist(REPORT,report)
    print('X_SPINE_INTEGRATION_RESULT',json.dumps(report),flush=True)
