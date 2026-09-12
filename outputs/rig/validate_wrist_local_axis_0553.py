"""Native viewport checks on the captured X copy; never save the source."""
import bpy, sys, json, math, hashlib, runpy
from pathlib import Path
from mathutils import Vector
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons',r'D:\MyRepository\Blender-addons-by-Randy\tests']
from character_designer import limb_ik, forearm_twist
from test_wrist_rotation_blender import select, update, rotation_vector
out=Path(__file__).parent
source=Path(bpy.data.filepath); digest=hashlib.sha256(source.read_bytes()).hexdigest()
rig=bpy.data.objects['CoshaRig']
if bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.objects.active=rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
for w in bpy.context.window_manager.windows:
    for a in w.screen.areas:
        if a.type=='CONSOLE':a.type='VIEW_3D'
w=bpy.context.window; a=next(a for a in w.screen.areas if a.type=='VIEW_3D'); r=next(r for r in a.regions if r.type=='WINDOW')
bpy.context.scene.tool_settings.use_keyframe_insert_auto=False
update(rig)
before={p.name:p.matrix.copy() for p in rig.pose.bones}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
bases={p.name:p.matrix_basis.copy() for p in rig.pose.bones}
mesh_digest=runpy.run_path(str(out/'repair_reversal_20260912.py'))['digest_meshes']
meshes=mesh_digest()
report={'ok':False,'cases':[]}
for side in 'LR':
    target=rig.pose.bones['CTRL_hand_IK.'+side]
    hand=rig.pose.bones['hand.'+side]
    target.use_transform_at_custom_shape=True
    assert not target.use_transform_around_custom_shape
    select(rig,target)
    for orientation,axis in [('LOCAL','Y'),('GLOBAL','X'),('GLOBAL','Y'),('GLOBAL','Z'),('VIEW','Z')]:
        update(rig)
        old=rig.matrix_world@hand.matrix
        direction=(old.col[1].xyz.normalized() if orientation=='LOCAL' else
            a.spaces.active.region_3d.view_rotation@Vector((0,0,1)) if orientation=='VIEW' else
            Vector(tuple(float(c==axis) for c in 'XYZ')))
        for sign in [-1,1]:
            with bpy.context.temp_override(window=w,area=a,region=r):
                assert bpy.ops.transform.rotate(value=sign*.19,orient_axis=axis,orient_type=orientation,
                    constraint_axis=tuple(c==axis for c in 'XYZ'),use_proportional_edit=False)=={'FINISHED'}
            update(rig)
            new=rig.matrix_world@hand.matrix
            err=(rotation_vector(old,new)-direction*sign*.19).length
            shift=(new.translation-old.translation).length
            report['cases'].append({'side':side,'orientation':orientation,'axis':axis,'sign':sign,'rotation_error':err,'shift':shift})
            assert err<8e-5 and shift<3e-5,report['cases'][-1]
            for n,m in bases.items():rig.pose.bones[n].matrix_basis=m
            update(rig)
assert mesh_digest()==meshes
assert all(rig.data.bones[n].matrix_local==m for n,m in rest.items())
report['max_pose_error']=max(abs(rig.pose.bones[n].matrix[i][j]-m[i][j]) for n,m in before.items() for i in range(4) for j in range(4))
assert report['max_pose_error']<2e-5
obj=bpy.data.objects['Cosha']
records=forearm_twist._records(obj)
assert all(r['enabled'] for r in records.values())
forearm_twist.toggle_paired_calibration(bpy.context,obj)
assert not any(r['enabled'] for r in forearm_twist._records(obj).values())
assert mesh_digest()==meshes
report['stale_disable_ok']=True
report['source_unchanged']=digest==hashlib.sha256(source.read_bytes()).hexdigest()
report['ok']=report['source_unchanged']
(out/'wrist_local_axis_0553_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('X_WRIST_LOCAL_AXIS_OK',report['ok'],flush=True)
