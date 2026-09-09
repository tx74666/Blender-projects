"""Read-only production-scene validation of persistent controller colors."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys
import traceback

import bpy

ROOT = Path(r'D:\Blender\Projects\Character\X')
SOURCE = ROOT / 'X.blend'
OUT = ROOT / 'outputs' / 'rig'
PREVIEW = OUT / 'X_control_colors_048_preview.blend'
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import control_colors as colors


def digest_assets():
    digest = hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: o.name):
        data = {
            'name': obj.name,
            'vertices': [list(v.co) for v in obj.data.vertices],
            'edges': [list(e.vertices) for e in obj.data.edges],
            'faces': [list(p.vertices) for p in obj.data.polygons],
            'groups': [g.name for g in obj.vertex_groups],
            'weights': [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices],
            'uv': [[list(item.uv) for item in layer.data] for layer in obj.data.uv_layers],
        }
        digest.update(json.dumps(data, sort_keys=True).encode())
    return digest.hexdigest()


def matrices(rig):
    bpy.context.view_layer.update()
    return {pb.name: {
        'rest': [list(row) for row in pb.bone.matrix_local],
        'basis': [list(row) for row in pb.matrix_basis],
        'pose': [list(row) for row in pb.matrix],
        'parent': pb.bone.parent.name if pb.bone.parent else None,
        'shape': pb.custom_shape.name if pb.custom_shape else None,
        'shape_transform': pb.custom_shape_transform.name if pb.custom_shape_transform else None,
        'shape_translation': list(pb.custom_shape_translation),
        'shape_rotation': list(pb.custom_shape_rotation_euler),
        'shape_scale': list(pb.custom_shape_scale_xyz),
    } for pb in rig.pose.bones}


def color_states(rig):
    return {pb.name: colors.capture_bone(pb) for pb in rig.pose.bones}


def brightness(rgb):
    return sum(a * b for a, b in zip(rgb, (.2126, .7152, .0722)))


report = {'ok': False}
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
try:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    rig = bpy.data.objects['CoshaRig']
    original = color_states(rig)
    original_display = rig.data.show_bone_colors
    original_display_backup = rig.data.get(colors.DISPLAY_KEY)
    assert not colors.has_backup(rig), 'Production already has color backups; use baseline-aware test'
    original_structure = matrices(rig)
    original_assets = digest_assets()
    targets = [pb for pb in rig.pose.bones if colors.is_control(pb)]
    target_names = [pb.name for pb in targets]
    count = colors.apply(rig)
    assert count == len(targets)
    assert rig.data.show_bone_colors
    assert rig.data[colors.DISPLAY_KEY] == original_display
    for pb in targets:
        state = colors.capture_bone(pb)['color']
        assert state['palette'] == 'CUSTOM', pb.name
        assert not state['constraints'], pb.name
        assert brightness(state['normal']) < brightness(state['select']) < brightness(state['active']), pb.name
        assert max(state['normal']) - min(state['normal']) > .1, pb.name
        assert json.loads(pb[colors.BACKUP_KEY]) == original[pb.name]['color'], pb.name
    assert matrices(rig) == original_structure
    assert digest_assets() == original_assets
    first_applied = color_states(rig)
    count_repeat = colors.apply(rig)
    assert count_repeat == count
    assert color_states(rig) == first_applied, 'Repeat Apply changed backup or result'

    report['palettes'] = dict(Counter(colors.palette_for(pb) for pb in targets))
    report['palette_per_control'] = {pb.name: {
        'palette': colors.palette_for(pb),
        'owner': pb.bone.get(colors.OWNER_KEY),
        'normal': list(pb.color.custom.normal),
        'select': list(pb.color.custom.select),
        'active': list(pb.color.custom.active),
    } for pb in targets}
    assert colors.palette_for(rig.pose.bones['CTRL_foot_roll.L']) == 'MINT'
    assert colors.palette_for(rig.pose.bones['CTRL_foot_roll.R']) == 'ROSE'
    assert colors.palette_for(rig.pose.bones['CTRL_toe_bend.L']) == 'SKY'
    assert colors.palette_for(rig.pose.bones['CTRL_toe_bend.R']) == 'PEACH'
    assert colors.palette_for(rig.pose.bones['CTRL_torso_bend']) == 'LILAC'
    torso_fk = [pb for pb in targets if pb.bone.get(colors.OWNER_KEY) == 'torso_controls' and pb.name != 'CTRL_torso_bend']
    assert len(torso_fk) == 3
    assert all(colors.palette_for(pb) == 'IRIS' for pb in torso_fk)

    for pb in rig.pose.bones:
        pb.select = False
    rig.data.bones.active = None
    bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW), copy=True)
    report['preview'] = str(PREVIEW)

    manual = rig.pose.bones['CTRL_foot_roll.L']
    manual.color.custom.normal = (.123, .234, .345)
    manual_state = colors.capture_bone(manual)
    colors.sync(rig)
    assert colors.capture_bone(manual) == manual_state, 'Sync replaced artist color'
    assert matrices(rig) == original_structure
    assert colors.restore(rig) == count
    assert color_states(rig) == original
    assert rig.data.show_bone_colors == original_display
    assert rig.data.get(colors.DISPLAY_KEY) == original_display_backup
    assert not colors.has_backup(rig)

    bpy.ops.wm.open_mainfile(filepath=str(PREVIEW), load_ui=False)
    rig = bpy.data.objects['CoshaRig']
    assert color_states(rig) == first_applied, 'Saved colors or backups did not persist'
    assert matrices(rig) == original_structure
    assert colors.restore(rig) == count
    assert color_states(rig) == original
    assert rig.data.show_bone_colors == original_display
    assert rig.data.get(colors.DISPLAY_KEY) == original_display_backup
    assert digest_assets() == original_assets
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
    report.update(
        ok=True, bone_count=len(rig.pose.bones), colored_count=count,
        original_display_enabled=original_display,
        all_custom_shapes_colored=True,
        brightness_increases_on_selection=True,
        repeated_apply_keeps_first_backup=True,
        artist_color_survives_sync=True,
        restore_exact_including_display=True,
        save_reopen_colors_and_backups=True,
        rest_pose_basis_and_shape_transforms_unchanged=True,
        geometry_weights_uv_unchanged=True,
        production_file_unchanged=True,
        production_sha256=source_hash,
    )
except Exception as exc:
    report.update(error=str(exc), traceback=traceback.format_exc())
    raise
finally:
    (OUT / 'control_colors_048_verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('CONTROL_COLORS_048', json.dumps({k: v for k, v in report.items() if k != 'palette_per_control'}), flush=True)
