"""Source-only prepared live Pose library write. Root must authorize execution.
No scene save, frame_set, model edit, append/readback or permanent fake-user edit.
"""
import bpy
import hashlib
import json
import os
from pathlib import Path
import traceback

ROUND = Path(r'D:\Blender\Projects\Character\X\validation\composition_20261011\fresh_rigging_round_20261012')
OBSERVED = ROUND / 'original_pose_metadata_02/original_pose_metadata.json'
OBSERVED_SHA = 'e655f9f28de84210dd0f34898db79f0dad4f8b8b9f7867bfe2f7cc293c5a4f4a'
OUT = ROUND / 'Pose-preservation_01'
BACKUP = OUT / 'Pose.blend'
META = 'character_designer_pose_asset_v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def curves(action):
    if action.is_action_layered:
        return [curve for layer in action.layers for strip in layer.strips
                for bag in strip.channelbags for curve in bag.fcurves]
    return list(action.fcurves)


def pose_content(action):
    result = {'name': action.name, 'custom_properties': {key: action[key] for key in action.keys()},
        'slots': [{'handle': slot.handle, 'identifier': slot.identifier, 'name_display': slot.name_display,
                   'target_id_type': slot.target_id_type} for slot in action.slots],
        'layer_names': [layer.name for layer in action.layers],
        'layout': [{'name': layer.name, 'strips': [{'type': strip.type,
            'channelbags': [{'slot_handle': bag.slot_handle,
                'curves': [[curve.data_path, curve.array_index] for curve in bag.fcurves]}
                for bag in strip.channelbags]} for strip in layer.strips]} for layer in action.layers],
        'curves': []}
    for curve in curves(action):
        result['curves'].append({'data_path': curve.data_path, 'array_index': curve.array_index,
            'mute': curve.mute, 'lock': curve.lock, 'extrapolation': curve.extrapolation,
            'group': curve.group.name if curve.group else None,
            'modifiers': [(modifier.type, modifier.name, modifier.mute) for modifier in curve.modifiers],
            'sampled': [list(point.co) for point in curve.sampled_points],
            'keys': [{'co': list(key.co), 'left': list(key.handle_left), 'right': list(key.handle_right),
                'interpolation': key.interpolation, 'easing': key.easing, 'type': key.type,
                'left_type': key.handle_left_type, 'right_type': key.handle_right_type,
                'back': key.back, 'amplitude': key.amplitude, 'period': key.period,
                'selected': [key.select_control_point, key.select_left_handle, key.select_right_handle]}
                for key in curve.keyframe_points]})
    return result


def context_state(action, rig):
    ad = rig.animation_data
    slot = ad.action_slot if ad else None
    return {'filepath': bpy.data.filepath, 'dirty': bpy.data.is_dirty,
        'scene': bpy.context.scene.as_pointer(), 'frame': bpy.context.scene.frame_current,
        'subframe': bpy.context.scene.frame_subframe, 'mode': bpy.context.mode,
        'active_object': bpy.context.view_layer.objects.active.as_pointer() if bpy.context.view_layer.objects.active else None,
        'selected_objects': sorted(obj.as_pointer() for obj in bpy.context.selected_objects),
        'rig': rig.as_pointer(), 'rig_active_action': ad.action.as_pointer() if ad and ad.action else None,
        'rig_active_slot': [slot.handle, slot.identifier] if slot else None,
        'active_bone': rig.data.bones.active.name if rig.data.bones.active else None,
        'bone_selection': [(bone.name, bone.select, bone.select_head, bone.select_tail) for bone in rig.data.bones],
        'action_pointer': action.as_pointer(), 'action_users': action.users,
        'action_fake_user': action.use_fake_user, 'action_asset': action.asset_data is not None,
        'pose_content_sha256': digest(pose_content(action))}


assert os.getpid() == 27676, 'Wrong live original Blender PID; caller must also retain exact FILETIME.'
assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
raw = OBSERVED.read_bytes()
assert hashlib.sha256(raw).hexdigest() == OBSERVED_SHA
observed = json.loads(raw)['Pose']
action = bpy.data.actions.get('Pose')
rig = bpy.data.objects.get('CoshaRig')
assert action is not None and action.library is None and rig is not None and rig.type == 'ARMATURE'
assert action.users == 0 and action.use_fake_user is False and action.asset_data is None
assert list(action.keys()) == [META] and isinstance(action[META], str)
assert [(slot.handle, slot.identifier) for slot in action.slots] == [(929201142, 'OBCoshaRig')]
actual_curves = curves(action)
assert len(actual_curves) == 360 and sum(len(curve.keyframe_points) for curve in actual_curves) == 360
assert not bpy.data.user_map(subset={action}).get(action, set())
assert not any(action in owners for owners in bpy.data.user_map().values()), 'Pose has outgoing ID dependencies; stop before write.'
for curve, prior in zip(actual_curves, observed['curves']):
    assert curve.data_path == prior['data_path'] and curve.array_index == prior['array_index']
    assert len(curve.keyframe_points) == prior['keys'] and len(curve.sampled_points) == prior['sampled_points']
    assert [{'co': list(key.co), 'interpolation': key.interpolation,
             'left': list(key.handle_left), 'right': list(key.handle_right)}
            for key in curve.keyframe_points] == prior['key_content']
before = context_state(action, rig)
original_fake = action.use_fake_user
assert not OUT.exists(), 'Refuse overwriting a backup or an unknown prior SDK outcome.'
OUT.mkdir()
report = {'schema': 'x.validation.original-Pose-library-write/1', 'completed': False,
    'write_completed': False, 'original_state_unchanged': False, 'pid': os.getpid(),
    'observation_sha256': OBSERVED_SHA, 'before': before, 'pose_content': pose_content(action),
    'requested_datablocks': ['Action:Pose'],
    'fake_user_argument': True, 'compress_argument': True, 'path_remap': 'NONE',
    'backup_readback_verified': False, 'indirect_datablocks_not_yet_readback': True,
    'artist_saved': False, 'model_or_frame_changed_by_script': False, 'fake_user_restore_performed': False}
try:
    bpy.data.libraries.write(str(BACKUP), {action}, path_remap='NONE', fake_user=True, compress=True)
    data = BACKUP.read_bytes()
    assert data, 'Library writer returned without a nonempty artifact.'
    report.update(write_completed=True, backup={'path': str(BACKUP),
        'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
except Exception:
    report['error'] = traceback.format_exc()
finally:
    if action.use_fake_user != original_fake:
        action.use_fake_user = original_fake
        report['fake_user_restore_performed'] = True
    report['after'] = context_state(action, rig)
    report['original_state_unchanged'] = report['after'] == before
    with (OUT / 'Pose_library_write_report.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
assert report['write_completed'] and report['original_state_unchanged'], 'Backup write or original-state guard failed; retain report, no automatic retry.'
print(json.dumps({'write_completed': True, 'original_state_unchanged': True,
    'backup_readback_verified': False, 'backup': report['backup'], 'artist_saved': False}))
