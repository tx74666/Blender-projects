"""Read saved X; exercise real GLOBAL/LOCAL X rotations in memory only."""
import bpy
import hashlib
import json
import math
import sys
import traceback
from pathlib import Path
from mathutils import Vector

ROOT=Path(r'D:\Blender\Projects\Character\X')
OUT=ROOT/'outputs/rig'
SOURCE=ROOT/'X.blend'
REPORT=OUT/'foot_roll_direction_0531_diagnosis.json'
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import foot_controls, limb_ik_fk


def update():
    limb_ik_fk._update(bpy.context,rig)


def bone_state(pb):
    world=rig.matrix_world@pb.matrix
    return {'local_euler':list(pb.rotation_euler),'world_rotation':list(world.to_quaternion()),
        'world_x_axis':list(world.to_3x3().col[0].normalized()),
        'head_world':list(rig.matrix_world@pb.head),'tail_world':list(rig.matrix_world@pb.tail),
        'pose_determinant':pb.matrix.to_3x3().determinant()}


def capture(record):
    names={role:record['bones'][role] for role in ('FOOT_ROLL','HEEL_PIVOT','TOE_TIP_PIVOT','BALL_PIVOT','ANKLE_SOLVER')}
    names.update(NATIVE_FOOT=record['chain'][2],NATIVE_TOE=record['toe'],FOOT_TARGET=record['target'])
    return {role:bone_state(rig.pose.bones[name]) for role,name in names.items()}


def delta(before,after):
    from mathutils import Quaternion
    result={}
    for role,old in before.items():
        new=after[role]
        q=(Quaternion(new['world_rotation'])@Quaternion(old['world_rotation']).inverted()).normalized()
        if q.w<0: q.negate()
        axis,angle=q.to_axis_angle()
        result[role]={'rotation_vector_degrees':list(axis*math.degrees(angle)),
            'head_world_delta':list(Vector(new['head_world'])-Vector(old['head_world'])),
            'tail_world_delta':list(Vector(new['tail_world'])-Vector(old['tail_world'])),
            'local_euler_delta_degrees':[math.degrees(a-b) for a,b in zip(new['local_euler'],old['local_euler'])]}
    return result


def main():
    global rig
    assert bpy.app.background
    sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    report={'ok':False,'source':str(SOURCE),'source_sha_before':sha,'tests':{}}
    try:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE),use_scripts=False)
        rig=bpy.data.objects['CoshaRig']
        if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.context.selected_objects: obj.select_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active=rig
        bpy.ops.object.mode_set(mode='POSE')
        update()
        records=foot_controls.records(rig)
        report['records']={side:{'roll':rec['roll'],'bones':rec['bones'],'chain':rec['chain'],'toe':rec['toe'],
            'drivers':rec['drivers']} for side,rec in records.items()}
        window,area,region=next((w,a,r) for w in bpy.context.window_manager.windows
            for a in w.screen.areas if a.type=='VIEW_3D' for r in a.regions if r.type=='WINDOW')
        for side in ('L','R'):
            record=records[side]
            pb=rig.pose.bones[record['roll']]
            for other in rig.pose.bones: other.select=other==pb
            rig.data.bones.active=pb.bone
            pb.bone.hide=False
            saved={'location':pb.location.copy(),'rotation_mode':pb.rotation_mode,
                   'euler':pb.rotation_euler.copy(),'quaternion':pb.rotation_quaternion.copy(),
                   'axis_angle':list(pb.rotation_axis_angle),'scale':pb.scale.copy()}
            before=capture(record)
            report['tests'][side]={'before':before,
                'custom_shape_transform':pb.custom_shape_transform.name if pb.custom_shape_transform else None,
                'lock_rotation':list(pb.lock_rotation),'use_local_location':pb.bone.use_local_location,
                'inherit_scale':pb.bone.inherit_scale,'operations':[]}
            for orient in ('GLOBAL','LOCAL'):
                for degrees in (-10,10):
                    try:
                        with bpy.context.temp_override(window=window,area=area,region=region):
                            status=bpy.ops.transform.rotate(value=math.radians(degrees),orient_axis='X',
                                orient_type=orient,constraint_axis=(True,False,False),use_proportional_edit=False)
                        update()
                        after=capture(record)
                        report['tests'][side]['operations'].append({'orientation':orient,'requested_degrees':degrees,
                            'status':list(status),'after':after,'delta':delta(before,after)})
                    finally:
                        pb.rotation_mode=saved['rotation_mode']
                        pb.location=saved['location']
                        pb.rotation_euler=saved['euler']
                        pb.rotation_quaternion=saved['quaternion']
                        pb.rotation_axis_angle=saved['axis_angle']
                        pb.scale=saved['scale']
                        update()
                        assert max(abs(a-b) for role,data in before.items()
                            for a,b in zip(data['head_world'],capture(record)[role]['head_world']))<2e-6
        report['ok']=True
    except Exception as exc:
        report.update(error=str(exc),traceback=traceback.format_exc())
    finally:
        report['source_sha_after']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        report['source_file_unchanged']=sha==report['source_sha_after']
        REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
        compact={key:value for key,value in report.items() if key not in {'records','tests'}}
        compact['tests']={side:{'shape_anchor':data['custom_shape_transform'],
            'input_world_x':data['before']['FOOT_ROLL']['world_x_axis'],
            'heel_world_x':data['before']['HEEL_PIVOT']['world_x_axis'],
            'operations':[{'orientation':op['orientation'],'requested_degrees':op['requested_degrees'],
                'input_world_delta':op['delta']['FOOT_ROLL']['rotation_vector_degrees'],
                'foot_world_delta':op['delta']['NATIVE_FOOT']['rotation_vector_degrees'],
                'heel_z':op['delta']['HEEL_PIVOT']['head_world_delta'][2],
                'ankle_z':op['delta']['NATIVE_FOOT']['head_world_delta'][2],
                'ball_z':op['delta']['NATIVE_TOE']['head_world_delta'][2],
                'tip_z':op['delta']['NATIVE_TOE']['tail_world_delta'][2]} for op in data['operations']]}
            for side,data in report['tests'].items()}
        print('FOOT_ROLL_DIRECTION_DIAGNOSIS',json.dumps(compact),flush=True)
    assert report['ok'] and report['source_file_unchanged'],report.get('error')


if __name__=='__main__':main()
