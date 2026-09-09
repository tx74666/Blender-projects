"""Apply the verified palette in the current X scene after saving a backup."""
from datetime import datetime
from pathlib import Path
import json
import bpy
import character_designer as cd
from character_designer import control_colors as colors

ROOT = Path(r'D:\Blender\Projects\Character\X')
assert Path(bpy.data.filepath).resolve() == (ROOT / 'X.blend').resolve()
assert cd.bl_info['version'] == (0, 48, 0)


class CD_OT_apply_colors_048(bpy.types.Operator):
    bl_idname = 'character_designer.apply_colors_048'
    bl_label = 'Apply Soft Controller Colors'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig = bpy.data.objects['CoshaRig']
        assert context.object == rig and rig.mode in {'POSE', 'OBJECT'}
        before = {pb.name: {'rest': [list(row) for row in pb.bone.matrix_local],
                           'basis': [list(row) for row in pb.matrix_basis],
                           'shape': pb.custom_shape.name if pb.custom_shape else None}
                  for pb in rig.pose.bones}
        backup = ROOT / 'outputs' / 'rig' / 'backups' / ('X_before_control_colors_048_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
        backup.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True)
        assert bpy.ops.character_designer.control_colors(action='APPLY') == {'FINISHED'}
        after = {pb.name: {'rest': [list(row) for row in pb.bone.matrix_local],
                          'basis': [list(row) for row in pb.matrix_basis],
                          'shape': pb.custom_shape.name if pb.custom_shape else None}
                 for pb in rig.pose.bones}
        assert before == after
        context.window_manager.character_designer.ui_page = 'RIG'
        context.window_manager.character_designer.rig_section = 'BODY'
        report = {'ok': True, 'version': list(cd.bl_info['version']), 'source': bpy.data.filepath,
                  'backup': str(backup), 'rig': rig.name,
                  'colored_count': sum(colors.BACKUP_KEY in pb for pb in rig.pose.bones),
                  'rest_pose_and_shapes_unchanged': True, 'main_file_saved': False}
        (ROOT / 'outputs' / 'rig' / 'control_colors_048_live_result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('CONTROL_COLORS_048_LIVE', json.dumps(report))
        return {'FINISHED'}


if hasattr(bpy.types, 'CD_OT_apply_colors_048'):
    bpy.utils.unregister_class(bpy.types.CD_OT_apply_colors_048)
bpy.utils.register_class(CD_OT_apply_colors_048)
bpy.ops.character_designer.apply_colors_048()
