"""Real-X Foot Roll direction migration; production input is never saved."""
import bpy
import copy
import importlib
import importlib.util
import json
import math
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

ROOT=Path(r'D:\Blender\Projects\Character\X')
OUT=ROOT/'outputs/rig'
SOURCE=ROOT/'X.blend'
TEST_INPUT=SOURCE
PREVIEW=OUT/'X_foot_direction_0532_preview.blend'
REPORT=OUT/'foot_direction_0532_validation.json'
spec=importlib.util.spec_from_file_location('body_checks',OUT/'validate_body_detail_0530.py')
checks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
h=checks.helpers


def refresh():
    global service,limb,colors,root_service
    service=importlib.import_module('character_designer.foot_controls')
    limb=importlib.import_module('character_designer.limb_ik')
    colors=importlib.import_module('character_designer.control_colors')
    root_service=importlib.import_module('character_designer.root_control')
    checks.limb_ik_fk=importlib.import_module('character_designer.limb_ik_fk')
    checks.rig=bpy.data.objects['CoshaRig']
    checks.update()


def capture_current():
    """Capture live scene around reload/migration without save or pose edits."""
    refresh()
    rig=checks.rig
    records=service.validate(rig)
    inputs={record['roll'] for record in records.values()}
    paths=set()
    normalized=copy.deepcopy(records)
    for side,record in records.items():
        for role,axis in (('HEEL_PIVOT',0),('HEEL_PIVOT',1),('BALL_PIVOT',0),('TOE_TIP_PIVOT',0)):
            paths.add((rig.pose.bones[record['bones'][role]].path_from_id('rotation_euler'),axis))
        normalized[side].pop('rotation_direction',None)
    for record in normalized.values():
        for driver in record['drivers']:
            if (driver['path'],driver['index']) in paths: driver.pop('expression')
    data={'objects':[],'meshes':[],'bones':[],'custom_properties':[],
          'records':normalized,'animation':h.animation_state()}
    for assignment in data['animation']['assignments']:
        if assignment[0] == ['Object',rig.name]:
            for curve in assignment[3]:
                settings=curve['settings']
                if (settings['data_path'],settings['array_index']) in paths:
                    curve['driver'].pop('expression')
    poses,displays,input_state={},{},{}
    for obj in sorted(bpy.data.objects,key=lambda item:item.name):
        data['objects'].append([obj.name,obj.type,h.plain(obj.data),h.plain(obj.matrix_world),
            h.plain(obj.matrix_basis),[h.rna_values(mod) for mod in obj.modifiers],
            [h.rna_values(con) for con in obj.constraints],
            [g.name for g in obj.vertex_groups] if obj.type=='MESH' else None])
        data['custom_properties'].append(['object',obj.name,h.properties(obj)])
        if obj.type!='ARMATURE':continue
        properties=h.properties(obj.data)
        if obj==rig:properties.pop(service.RECORD_KEY,None)
        data['custom_properties'].append(['armature',obj.name,properties])
        for pb in sorted(obj.pose.bones,key=lambda pb:pb.name):
            key=obj.name+'/'+pb.name
            is_input=obj==rig and pb.name in inputs
            channels={'location':list(pb.location),'scale':list(pb.scale),'rotation_mode':pb.rotation_mode}
            if not is_input:
                channels.update(basis=h.plain(pb.matrix_basis),euler=list(pb.rotation_euler),
                    quaternion=list(pb.rotation_quaternion),axis_angle=list(pb.rotation_axis_angle))
                poses[key]=h.plain(pb.matrix)
            else:
                input_state[key]={'euler':list(pb.rotation_euler),'basis':h.plain(pb.matrix_basis),
                                   'pose':h.plain(pb.matrix)}
            data['bones'].append([key,root_service._state(pb.bone),channels,h.properties(pb.bone),
                h.properties(pb),[h.rna_values(con) for con in pb.constraints],
                limb._pose_shape_json_state(pb),colors.capture_bone(pb),
                list(pb.lock_location),list(pb.lock_rotation),list(pb.lock_scale)])
            if pb.custom_shape:
                anchor=pb.custom_shape_transform or pb
                scale=pb.custom_shape_scale_xyz*(pb.bone.length if pb.use_custom_shape_bone_size else 1.)
                frame=obj.matrix_world@anchor.matrix@Matrix.LocRotScale(pb.custom_shape_translation,
                    pb.custom_shape_rotation_euler.to_quaternion(),scale)
                displays[key]=h.plain(frame)
    for mesh in sorted(bpy.data.meshes,key=lambda mesh:mesh.name):
        data['meshes'].append([mesh.name,[list(v.co) for v in mesh.vertices],
            [list(e.vertices) for e in mesh.edges],[list(p.vertices) for p in mesh.polygons],
            [[(g.group,g.weight) for g in v.groups] for v in mesh.vertices],
            None if mesh.shape_keys is None else [[k.name,k.value,[list(p.co) for p in k.data]]
                                                  for k in mesh.shape_keys.key_blocks]])
        data['custom_properties'].append(['mesh',mesh.name,h.properties(mesh)])
    return {'digests':{key:h.digest(value) for key,value in data.items()},
            'poses':poses,'displays':displays,'inputs':input_state}


def assert_unchanged(before,after,tolerance=4e-6):
    """Allow direction metadata/expressions and input rotation, preserve output."""
    changed=[key for key in before['digests'] if before['digests'][key]!=after['digests'][key]]
    assert not changed,'Unexpected migration changes: '+', '.join(changed)
    errors={}
    for category in ('poses','displays'):
        assert before[category].keys()==after[category].keys(),category+' set changed'
        errors[category]=max(abs(after[category][name][i][j]-matrix[i][j])
            for name,matrix in before[category].items() for i in range(4) for j in range(4))
        assert errors[category]<tolerance,(category,errors[category])
    return errors


def open_source():
    bpy.ops.wm.open_mainfile(filepath=str(TEST_INPUT),use_scripts=False)
    rig=bpy.data.objects['CoshaRig']
    if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    for obj in bpy.context.selected_objects:obj.select_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='POSE')
    refresh()
    return rig


def migrate():
    return {side:service.update_rotation_direction(bpy.context,checks.rig,side) for side in ('L','R')}


def rotation_vector(new,old):
    q=(new@old.inverted()).normalized()
    if q.w<0:q.negate()
    axis,angle=q.to_axis_angle()
    return axis*angle


def test_directions():
    rig=checks.rig
    records=service.records(rig)
    window,area,region=next((w,a,r) for w in bpy.context.window_manager.windows
        for a in w.screen.areas if a.type=='VIEW_3D' for r in a.regions if r.type=='WINDOW')
    result=[]
    for side,record in records.items():
        control=rig.pose.bones[record['roll']]
        foot=rig.pose.bones[record['chain'][2]]
        saved=control.rotation_euler.copy()
        control.rotation_euler=(0,0,0)
        checks.update()
        for pb in rig.pose.bones:pb.select=pb==control
        control.bone.hide=False
        rig.data.bones.active=control.bone
        for orient in ('GLOBAL','LOCAL'):
            for axis in ('X','Y'):
                for degrees in (-10,10):
                    control.rotation_euler=(0,0,0)
                    checks.update()
                    old_control=(rig.matrix_world@control.matrix).to_quaternion()
                    old_foot=(rig.matrix_world@foot.matrix).to_quaternion()
                    with bpy.context.temp_override(window=window,area=area,region=region):
                        status=bpy.ops.transform.rotate(value=math.radians(degrees),orient_axis=axis,orient_type=orient,
                            constraint_axis=(axis=='X',axis=='Y',False),use_proportional_edit=False)
                    assert status=={'FINISHED'}
                    checks.update()
                    input_delta=rotation_vector((rig.matrix_world@control.matrix).to_quaternion(),old_control)
                    output_delta=rotation_vector((rig.matrix_world@foot.matrix).to_quaternion(),old_foot)
                    alignment=input_delta.normalized().dot(output_delta.normalized())
                    assert alignment>.98,(side,orient,axis,degrees,alignment)
                    result.append({'side':side,'orientation':orient,'axis':axis,'degrees':degrees,
                        'alignment':alignment,'input_degrees':input_delta.length*180/math.pi,
                        'output_degrees':output_delta.length*180/math.pi})
        control.rotation_euler=saved
        checks.update()
    return result


def main():
    global TEST_INPUT
    assert bpy.app.background
    source_hash=h.sha_file(SOURCE)
    report={'ok':False,'source':str(SOURCE),'preview':str(PREVIEW),'source_sha_before':source_hash}
    try:
        fixture_folder=OUT/'fixtures'
        fixture_folder.mkdir(exist_ok=True)
        TEST_INPUT=fixture_folder/('X_foot_direction_0532_input_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.blend')
        shutil.copy2(SOURCE,TEST_INPUT)
        assert h.sha_file(TEST_INPUT)==source_hash,'Source changed while fixture was copied.'
        report['immutable_fixture']=str(TEST_INPUT)
        checks.cd.register()
        scenarios=[{'L':(.3,.08),'R':(-.25,-.09)},
                   {'L':(-.28,-.07),'R':(.35,.06)},
                   {'L':(1.,.08),'R':(-.95,-.08)}]
        report['nonzero_scenarios']=[]
        for scenario in scenarios:
            rig=open_source()
            assert hasattr(service,'update_rotation_direction'),'Service updater is not ready.'
            records=service.records(rig)
            for side,(x,y) in scenario.items():
                pb=rig.pose.bones[records[side]['roll']]
                pb.rotation_euler.x=x
                pb.rotation_euler.y=y
            checks.update()
            before=capture_current()
            meshes=checks.evaluated_meshes()
            migrate()
            errors=assert_unchanged(before,capture_current())
            mesh_errors=checks.mesh_errors(meshes)
            assert max(mesh_errors.values(),default=0.)<5e-6
            for side in ('L','R'):
                pb=rig.pose.bones[records[side]['roll']]
                assert abs(pb.rotation_euler.x+scenario[side][0])<1e-6
                wanted_y=-scenario[side][1] if side=='R' else scenario[side][1]
                assert abs(pb.rotation_euler.y-wanted_y)<1e-6
            checks.validate_existing()
            report['nonzero_scenarios'].append({'old_input':scenario,'errors':errors,'mesh_errors':mesh_errors})
        rig=open_source()
        before=capture_current()
        migrate()
        report['saved_pose_migration']=assert_unchanged(before,capture_current())
        preserved=capture_current()
        assert bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW),copy=True)=={'FINISHED'}
        bpy.ops.wm.open_mainfile(filepath=str(PREVIEW),use_scripts=False)
        refresh()
        bpy.context.view_layer.objects.active=checks.rig
        checks.rig.select_set(True)
        limb._mode_set(bpy.context,checks.rig,'POSE')
        report['reopened']=assert_unchanged(preserved,capture_current())
        report['direction_operations']=test_directions()
        checks.validate_existing()
        records=service.records(checks.rig)
        removed_names={name for record in records.values() for name in record['bones'].values()}
        # Removal matches base IK inputs, including knee poles; their matrices
        # may change while the native deformation pose is preserved.
        desired={pb.name:pb.matrix.copy() for pb in checks.rig.pose.bones
                 if pb.name not in removed_names and not pb.bone.get('character_designer_owner')}
        meshes=checks.evaluated_meshes()
        for side in ('L','R'):service.remove(bpy.context,checks.rig,side)
        checks.update()
        remove_error=max(abs(checks.rig.pose.bones[name].matrix[i][j]-matrix[i][j])
            for name,matrix in desired.items() for i in range(4) for j in range(4))
        assert remove_error<5e-4,remove_error
        remove_mesh=checks.mesh_errors(meshes)
        assert max(remove_mesh.values(),default=0.)<5e-4
        checks.validate_existing()
        report.update(ok=True,version=list(checks.cd.bl_info['version']),removal_pose_error=remove_error,
            removal_mesh_errors=remove_mesh,native_poses_and_displays_preserved=True,
            topology_weights_animation_rest_pivots_preserved=True,reopened_verified=True)
    except Exception as exc:
        report.update(error=str(exc),traceback=traceback.format_exc())
    finally:
        report['source_sha_after']=h.sha_file(SOURCE)
        report['source_file_unchanged']=source_hash==report['source_sha_after']
        report['production_checksum_external_change']=not report['source_file_unchanged']
        report['production_write_performed']=False
        report['fixture_file_unchanged']=TEST_INPUT!=SOURCE and h.sha_file(TEST_INPUT)==source_hash
        if not report['fixture_file_unchanged']:report.update(ok=False,error='The immutable input fixture changed during validation.')
        REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('FOOT_DIRECTION_0532_VALIDATION',json.dumps(report),flush=True)
    assert report['ok'],report.get('error')


if __name__=='__main__':main()
