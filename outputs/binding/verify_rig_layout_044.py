import bpy
import json
import sys
from pathlib import Path
from mathutils import Euler, Vector

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import character_setup, skirt, skirt_rig, quick_bind
character_designer.register()
state = bpy.context.scene.character_designer_setup
source = bpy.data.objects['Dress']
status = skirt_rig.attachment_status(source)
started_unbound = status is None
assert state.rig is not None and state.body is not None
hips = character_setup.resolve_bone(bpy.context, 'HIPS')
head = character_setup.resolve_bone(bpy.context, 'HEAD')
if bpy.context.active_object and bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
for obj in bpy.context.selected_objects:
    obj.select_set(False)
source.select_set(True)
bpy.context.view_layer.objects.active = source
assert skirt._desired_attachment(bpy.context, source) == (state.rig, hips)
assert bpy.ops.character_designer.set_rig_section(section='SKIRT') == {'FINISHED'}
assert skirt.CHARACTERDESIGNER_PT_skirt_setup.poll(bpy.context)
if started_unbound:
    bpy.context.window_manager.character_designer_skirt.physics = False
    assert bpy.ops.character_designer.create_skirt_setup() == {'FINISHED'}
    status = skirt_rig.attachment_status(source)
assert status['attached'] and status['character'] is state.rig and status['parent_bone'] == hips
record_before = source[skirt_rig.RECORD_KEY]
object_count = len(bpy.data.objects)
assert bpy.ops.character_designer.skirt_update_attachment() == {'FINISHED'}
assert source[skirt_rig.RECORD_KEY] == record_before
assert len(bpy.data.objects) == object_count
assert not skirt_rig.has_attachment_backup(source)
pose = state.rig.pose.bones[hips]
original = pose.matrix_basis.copy()
before = status['rig'].matrix_world.copy()
try:
    pose.matrix_basis = original @ Euler((0.04, -0.025, 0.03)).to_matrix().to_4x4()
    pose.location += Vector((0.012, 0.005, 0.007))
    bpy.context.view_layer.update()
    after = status['rig'].matrix_world.copy()
    delta = max(abs(after[i][j] - before[i][j]) for i in range(4) for j in range(4))
    assert delta > 1e-4, 'Skirt did not follow the main Hips'
finally:
    pose.matrix_basis = original
    bpy.context.view_layer.update()
assert max(abs(status['rig'].matrix_world[i][j] - before[i][j]) for i in range(4) for j in range(4)) < 1e-5
report = {
    'file': bpy.data.filepath, 'addon': character_designer.bl_info['version'],
    'rig': state.rig.name, 'body': state.body.name, 'hips': hips, 'head': head,
    'skirt': source.name, 'actual_attachment': f"{status['character'].name} / {status['parent_bone']}",
    'existing_physics': status['physics'], 'hips_pose_follow_verified': True,
    'created_new_setup_for_verification': started_unbound,
    'same_attachment_update_noop': True,
    'weight_restore_records_preserved': all(quick_bind.has_binding_backup(bpy.data.objects[name]) for name in ('Clothes', 'Stocking', 'Shoes')),
    'production_file_saved': False,
}
if started_unbound:
    skirt_rig.remove_skirt(bpy.context, source)
    assert skirt_rig.read_record(source) is None and source.parent is None
    assert len(source.vertex_groups) == 0
    report['remove_restored_unbound'] = True
Path(r'D:\Blender\Projects\Character\X\outputs\binding\rig_layout_044_verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('REAL_CHARACTER_RIG_LAYOUT_OK', report)
