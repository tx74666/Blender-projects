import bpy,hashlib,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons']
import character_designer
from character_designer import limb_ik,limb_ik_fk as limbs,spine_ik_fk as spine,torso_controls as torso,eye_controls as eyes,foot_controls as feet,bone_collections
SOURCE=Path(r'D:\Blender\Projects\Character\X\X.blend')
REPORT=Path(r'D:\Blender\Projects\Character\X\outputs\rig\latest_x_endpoint_recovery_051_validation.json')
source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=bpy.data.objects['CoshaRig']
limb_ik._mode_set(bpy.context,rig,'POSE')
def update():spine._update(bpy.context,rig)
def native():
    update()
    return spine._matrices(rig)
def error(expected):
    return max(abs(rig.pose.bones[name].matrix[i][j]-matrix[i][j]) for name,matrix in expected.items() for i in range(4) for j in range(4))
def bases():return spine._pose_snapshot(rig)
def basis_error(expected,exclude=()):
    return max((abs(rig.pose.bones[name].matrix_basis[i][j]-basis[i][j]) for name,(_mode,basis) in expected.items() if name not in exclude for i in range(4) for j in range(4)),default=0.0)
def weights():
    return {obj.name:hashlib.sha256(repr((tuple(g.name for g in obj.vertex_groups),tuple(tuple((g.group,g.weight) for g in v.groups) for v in obj.data.vertices))).encode()).hexdigest()
            for obj in bpy.data.objects if obj.type=='MESH'}
report={'source':str(SOURCE),'source_size':SOURCE.stat().st_size,'source_sha256_before':source_hash,'status':'running','cases':[]}
try:
    inventory=limb_ik._validate_inventory(rig)
    sp=spine.validate(rig)
    tr=torso.validate(rig)
    er=eyes.validate(rig)
    assert sp and tr and er
    report['preflight']={'all_bones':len(rig.data.bones),'native_bones':len(native()),'schema':inventory['schema'],'limbs':[str(k) for k in inventory['rigs']]}
    print('X_ENDPOINT_PREFLIGHT',json.dumps(report['preflight']),flush=True)
    rest={b.name:torso._state(b) for b in rig.data.bones}
    weight_before=weights()
    records={key:rig.data[key] for key in (spine.RECORD_KEY,torso.RECORD_KEY,eyes.RECORD_KEY,feet.RECORD_KEY)}
    other={obj.name:{pb.name:pb.matrix.copy() for pb in obj.pose.bones} for obj in bpy.data.objects if obj.type=='ARMATURE' and obj!=rig}
    spine.switch(bpy.context,rig,'FK')
    rig.pose.bones[tr['bend']].rotation_euler.x+=.04
    rig.pose.bones[tr['controls'][sp['sources'][1]]].rotation_euler.x-=.025
    foot=feet.records(rig)
    for rec in foot.values():
        rig.pose.bones[rec['roll']].rotation_euler.x+=.08
        rig.pose.bones[rec['toe_control']].rotation_euler.x+=.04
    for idx,record in enumerate(inventory['rigs'].values()):
        rig.pose.bones[record['target'].name].location+=Vector((.004 if idx%2 else -.004,-.003,.004))
    rig.pose.bones[er['master']].location.x+=.005
    update()
    baseline=bases()
    properties={rec['target'].name:rig.pose.bones[rec['target'].name][limbs.PROPERTY] for rec in inventory['rigs'].values()}
    properties[sp['chest']]=rig.pose.bones[sp['chest']][spine.PROPERTY]
    layout=bone_collections.capture_managed_layout(rig)
    def restore():
        for name,value in properties.items():rig.pose.bones[name]['ik_fk']=value
        spine._restore_pose(bpy.context,rig,baseline)
        bone_collections.restore_layout(rig,layout)
        update()
    for key,record in inventory['rigs'].items():
        for mode in ('FK','IK'):
            restore()
            target=rig.pose.bones[record['target'].name]
            target.location+=Vector((.006,-.007,.005))
            target[limbs.PROPERTY]=.5
            desired=native()
            before=bases()
            changed=set(record['chain']) if mode=='FK' else {record['target'].name,record['pole'].name}
            if record.get('foot_controls'):changed.add(record['foot_controls']['toe_control'])
            result=limbs.switch_limb(bpy.context,rig,key,mode,keyframe=False)
            update()
            entry={'module':str(key),'mode':mode,'result':result,'all_native_matrix_error':error(desired),'untouched_basis_error':basis_error(before,changed)}
            assert entry['all_native_matrix_error']<=4e-4,entry
            assert entry['untouched_basis_error']<=2e-6,entry
            limb_ik._validate_inventory(rig)
            report['cases'].append(entry)
            print('X_ENDPOINT_CASE',json.dumps(entry),flush=True)
    for mode in ('FK','IK'):
        restore()
        chest=rig.pose.bones[sp['chest']]
        chest.location+=Vector((.004,-.005,.004))
        rig.pose.bones[sp['shape']].rotation_euler=(.05,-.02,.015)
        chest[spine.PROPERTY]=.5
        desired=native()
        before=bases()
        changed=set(sp['fk_controls'].values()) if mode=='FK' else set(sp['bones'].values())
        result=spine.switch(bpy.context,rig,mode)
        update()
        entry={'module':'spine','mode':mode,'result':result,'all_native_matrix_error':error(desired),'untouched_basis_error':basis_error(before,changed)}
        assert entry['all_native_matrix_error']<=4e-4,entry
        assert entry['untouched_basis_error']<=2e-6,entry
        limb_ik._validate_inventory(rig)
        report['cases'].append(entry)
        print('X_ENDPOINT_CASE',json.dumps(entry),flush=True)
    restore()
    key=('LEG','L')
    record=inventory['rigs'][key]
    limbs.switch_limb(bpy.context,rig,key,'FK',keyframe=False)
    rig.pose.bones[record['chain'][0]].scale.y*=1.4
    desired=native()
    before=bases()
    value=rig.pose.bones[record['target'].name][limbs.PROPERTY]
    try:limbs.switch_limb(bpy.context,rig,key,'IK',keyframe=False)
    except limb_ik.LimbIKError as exc:
        report['unsupported_scale']={'refused':True,'message':str(exc),'all_native_matrix_error':error(desired),'basis_error':basis_error(before),'mode_value_preserved':rig.pose.bones[record['target'].name][limbs.PROPERTY]==value}
    else:raise AssertionError('Unsupported scaled FK unexpectedly switched to IK')
    assert report['unsupported_scale']['all_native_matrix_error']<=4e-4
    assert report['unsupported_scale']['basis_error']<=2e-6 and report['unsupported_scale']['mode_value_preserved']
    restore()
    assert weights()==weight_before
    assert all(torso._same_rest(rig.data.bones[name],state) for name,state in rest.items())
    assert records=={key:rig.data[key] for key in records}
    other_errors={name:max(abs(bpy.data.objects[name].pose.bones[bone].matrix[i][j]-matrix[i][j]) for bone,matrix in values.items() for i in range(4) for j in range(4)) for name,values in other.items()}
    assert all(value<=1e-6 for value in other_errors.values())
    report['preservation']={'rest':True,'weights':True,'ownership_records':True,'other_armatures':other_errors}
    report['status']='passed'
except Exception as exc:
    report['status']='failed'
    report['error']=repr(exc)
    raise
finally:
    report['source_sha256_after']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    report['source_unchanged']=report['source_sha256_after']==source_hash
    REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('X_ENDPOINT_RECOVERY_RESULT',json.dumps(report),flush=True)
