"""Repair X's unanimated left reverse-foot baseline using its existing services."""
import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Matrix
if bpy.app.background:
    sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import limb_ik, limb_ik_fk, foot_controls as feet, control_colors
ROOT=Path(r'D:\Blender\Projects\Character\X\outputs\rig')

def run():
    rig=bpy.data.objects['CoshaRig']
    if not bpy.app.background:
        assert Path(bpy.data.filepath).resolve()==(ROOT.parent.parent/'X.blend').resolve()
        diagnostic=json.loads((ROOT/'pose_reset_diagnostic.json').read_text(encoding='utf-8'))
        for saved in diagnostic['bones']:
            current=rig.pose.bones[saved['name']].matrix_basis
            assert max(abs(current[i][j]-saved['basis'][i][j]) for i in range(4) for j in range(4))<2e-4, 'Pose changed during inspection; stop before repair.'
    assert not rig.animation_data or (not rig.animation_data.action and not rig.animation_data.nla_tracks)
    assert not bpy.context.scene.tool_settings.use_keyframe_insert_auto
    key=('LEG','L')
    rec=feet.get_record(rig,key)
    assert rec
    rig_before={pb.name:pb.matrix.copy() for pb in rig.pose.bones}
    rest_before={b.name:[list(r) for r in b.matrix_local] for b in rig.data.bones if b.name not in rec['bones'].values()}
    shape_colors={name:control_colors.capture_bone(rig.pose.bones[name]) for name in [rec['roll'],rec['toe_control']]}
    desired={name:rig.data.bones[name].matrix_local.copy() for name in (*rec['chain'],rec['toe'])}
    print('OLD_LEFT_ANGLE_DEGREES',__import__('math').degrees(limb_ik._rotation_error(rig.pose.bones['foot.L'].matrix,desired['foot.L'])))
    feet.remove(bpy.context,rig,key)
    limb_ik_fk.match_existing_pose(bpy.context,rig,key,desired,keyframe=False)
    new=feet.build(bpy.context,rig,key,toe_name='toe.L',shoe=bpy.data.objects.get('Shoes'))
    for name,state in shape_colors.items():control_colors.restore_bone_state(rig.pose.bones[name],state)
    # Reproduce Clear Location / Rotation / Scale on animator controls.
    names=[new['target'],new['roll'],new['toe_control']]
    inv=limb_ik._validate_inventory(rig)
    names.append(inv['rigs'][key]['pole'].name)
    for name in names:
        pb=rig.pose.bones[name]
        pb.location=(0,0,0)
        pb.rotation_euler=(0,0,0)
        pb.rotation_quaternion=(1,0,0,0)
        pb.rotation_axis_angle=(0,0,1,0)
        pb.scale=(1,1,1)
    limb_ik_fk._update(bpy.context,rig)
    errors=limb_ik_fk._verify(rig,desired)
    if bpy.app.background:
        rig.pose.bones[new['target']].rotation_euler.x=0.24
        rig.pose.bones[new['roll']].rotation_euler.x=0.31
        rig.pose.bones[new['toe_control']].rotation_euler.x=-0.18
        limb_ik_fk._update(bpy.context,rig)
        for name in names:
            pb=rig.pose.bones[name]
            pb.location=(0,0,0)
            pb.rotation_euler=(0,0,0)
            pb.rotation_quaternion=(1,0,0,0)
            pb.scale=(1,1,1)
        limb_ik_fk._update(bpy.context,rig)
        errors=limb_ik_fk._verify(rig,desired)
    assert all([list(row) for row in rig.data.bones[name].matrix_local]==rest for name,rest in rest_before.items())
    unaffected={n:m for n,m in rig_before.items() if n not in rec['bones'].values() and n not in rec['chain'] and n!=rec['toe'] and not n.endswith('.L')}
    limb_ik_fk._verify(rig,unaffected)
    feet.validate(rig,limb_ik._validate_inventory(rig))
    print('NEUTRAL_RESET_VERIFIED',errors)
    return dict(ok=True,errors=errors,controls_zeroed=names,original_bone_rest_preserved=True)

if bpy.app.background:
    bpy.context.view_layer.objects.active=bpy.data.objects['CoshaRig']
    bpy.context.object.select_set(True)
    result=run()
    (ROOT/'left_foot_reset_verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'X_left_foot_reset_preview.blend'),copy=True)
else:
    class CD_OT_repair_left_foot_neutral(bpy.types.Operator):
        bl_idname='character_designer.repair_left_foot_neutral'
        bl_label='Restore Left Foot Neutral Baseline'
        bl_options={'REGISTER','UNDO'}
        def execute(self,context):
            result=run()
            (ROOT/'left_foot_reset_live.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            self.report({'INFO'},'Left foot restored; zeroed controls now return to neutral')
            return {'FINISHED'}
    if hasattr(bpy.types,'CD_OT_repair_left_foot_neutral'):
        bpy.utils.unregister_class(bpy.types.CD_OT_repair_left_foot_neutral)
    bpy.utils.register_class(CD_OT_repair_left_foot_neutral)
    bpy.ops.character_designer.repair_left_foot_neutral()
