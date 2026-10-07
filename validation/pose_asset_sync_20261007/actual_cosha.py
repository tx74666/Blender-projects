"""Actual CoshaRig integration evidence, in a disposable background process.

Loads only the adjacent immutable artist checkpoint. No .blend save operation
exists in this script. It writes JSON evidence in this directory, never X.blend.
Run serially after the shared Blender/Dress validation window has been released.
Suggested runner: blender --background --factory-startup --disable-autoexec
  --threads 2 --python-exit-code 1 --python <absolute path to this file>
"""
import hashlib
import json
import os
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bpy
from mathutils import Vector

FOLDER = Path(__file__).resolve().parent
CHECKPOINT = FOLDER / 'X_before_pose_asset_sync.blend'
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
REPOSITORY = Path(r'D:\MyRepository\Blender-addons-by-Randy')
SOURCE_ROOT = Path(os.environ.get('POSE_APPROVED_SOURCE_ROOT', str(REPOSITORY / 'addons')))
EXPECTED_SELECTED = {'shoulder.L', 'upper_arm.L', 'forearm.L'}
EXPECTED_CAPTURED = EXPECTED_SELECTED | {'hand.L'}
PHASES = ('load_checkpoint', 'capture_existing_selection', 'native_action_oracle',
          'restore_in_fk', 'restore_in_ik_and_continue', 'apply_in_original_and_return')
START = datetime.now(timezone(timedelta(hours=8)))
REPORT_PATH = FOLDER / ('actual_cosha_' + START.strftime('%Y%m%d_%H%M%S_%f') + '.json')
report = {
    'schema': 1, 'started_at': START.isoformat(), 'pid': os.getpid(),
    'script': str(Path(__file__).resolve()), 'checkpoint': str(CHECKPOINT),
    'artist_file': str(ARTIST), 'report': str(REPORT_PATH), 'passed': False,
    'steps': [], 'limitations': [
        'Disposable background copy; no live artist scene modification.',
        'Local Action capture/application; Asset Browser GUI and library export are not tested.',
        'Native Action oracle uses an unconstrained temporary armature copy, without the plugin matcher.',
    ],
}
initial_hashes = {}


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_value(value):
    if isinstance(value, dict):
        return {str(key): safe_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [safe_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(safe_value(item) for item in value)
    if hasattr(value, 'as_pointer') and hasattr(value, 'name'):
        return {'type': type(value).__name__, 'name': value.name, 'pointer': value.as_pointer()}
    return value


def state_digest(value):
    encoded = json.dumps(safe_value(value), sort_keys=True, allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def checkpoint_report():
    REPORT_PATH.write_text(json.dumps(safe_value(report), ensure_ascii=False,
                                      indent=2, allow_nan=False), encoding='utf-8')


def step(name, operation):
    entry = {'name': name, 'passed': False}
    report['steps'].append(entry)
    began = time.perf_counter()
    try:
        value = operation()
        entry.update(value or {})
        entry['passed'] = True
        print('COSHA_PASS', name, flush=True)
        return value
    except Exception as exc:
        entry.update(error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        print('COSHA_FAIL', name, type(exc).__name__, str(exc), flush=True)
        raise
    finally:
        entry['seconds'] = round(time.perf_counter() - began, 4)
        checkpoint_report()


def pose_error(actual, expected, tolerance=4e-4):
    errors = {name: poses._difference(actual[name], matrix) for name, matrix in expected.items()}
    worst = max(errors, key=errors.get)
    result = {'max_matrix_error': errors[worst], 'worst_bone': worst, 'tolerance': tolerance,
              'largest_errors': dict(sorted(errors.items(), key=lambda item: item[1], reverse=True)[:8])}
    require(errors[worst] <= tolerance, 'Pose mismatch: ' + json.dumps(result))
    return result


def curves(action):
    if action is None:
        return ()
    return tuple((c.data_path, c.array_index, c.mute,
                  tuple((tuple(p.co), p.interpolation, tuple(p.handle_left), tuple(p.handle_right))
                        for p in c.keyframe_points)) for c in limb_ik._fcurves_for_action(action))


def artist_state():
    """Use the test helper while allowing historical artist Action slot names."""
    # Existing animation can have an imported slot name unlike CoshaRig; it
    # needs read-only curve enumeration, not a Pose asset compatibility check.
    with patch.object(workflows, 'curve_state', side_effect=lambda action, _rig: curves(action)):
        return workflows.workspace(rig)


def same_fields(before, after, keys):
    changed = [key for key in keys if before[key] != after[key]]
    require(not changed, 'Protected artist state changed: ' + ', '.join(changed))
    return list(keys)


def arm_entry():
    return limb_ik._validate_inventory(rig)['rigs'][('ARM', 'L')]


def rotate_forearm(amount):
    pb = rig.pose.bones['forearm.L']
    basis = pb.matrix_basis.copy()
    pb.rotation_mode = 'XYZ'
    pb.matrix_basis = basis
    pb.rotation_euler.x += amount
    workflows.update(rig)


def load():
    global character_designer, poses, capture, original, limb_ik, limb_ik_fk
    global bone_display, workflows, patch, rig, wanted, rest, action, action_curves
    require(bpy.app.background, 'Run this evidence script in an isolated background Blender process.')
    require(CHECKPOINT.is_file(), 'The adjacent saved artist checkpoint is missing.')
    require(CHECKPOINT.resolve() != ARTIST.resolve(), 'The evidence checkpoint cannot be X.blend.')
    initial_hashes['checkpoint'] = sha256(CHECKPOINT)
    initial_hashes['artist'] = sha256(ARTIST) if ARTIST.is_file() else None
    sys.path[:0] = [str(SOURCE_ROOT), str(REPOSITORY / 'tests')]
    existing = sys.modules.get('character_designer')
    canonical = (SOURCE_ROOT / 'character_designer' / '__init__.py').resolve()
    if existing is not None and Path(existing.__file__).resolve() != canonical:
        existing.unregister()
        for module_name in list(sys.modules):
            if module_name == 'character_designer' or module_name.startswith('character_designer.'):
                del sys.modules[module_name]
    import character_designer
    require(Path(character_designer.__file__).resolve() == canonical, 'The approved add-on source was not imported.')
    character_designer.register()
    from character_designer import control_pose_assets as poses, control_pose_capture as capture
    from character_designer import body_original_mode as original, bone_display, limb_ik, limb_ik_fk
    from unittest.mock import patch
    import test_control_pose_capture_blender as workflows
    result = bpy.ops.wm.open_mainfile(filepath=str(CHECKPOINT), load_ui=False, use_scripts=False)
    require(result == {'FINISHED'}, 'Blender did not finish loading the checkpoint.')
    require(Path(bpy.data.filepath).resolve() == CHECKPOINT.resolve(), 'An unexpected file is loaded.')
    rig = bpy.data.objects.get('CoshaRig')
    require(rig is not None and rig.type == 'ARMATURE', 'CoshaRig is unavailable.')
    require(bpy.context.view_layer.objects.active == rig, 'The checkpoint active object is not CoshaRig.')
    require(not original.active(rig), 'The checkpoint unexpectedly starts in Original mode.')
    selected = {pb.name for pb in rig.pose.bones if (pb if hasattr(pb, 'select') else pb.bone).select}
    require(selected == EXPECTED_SELECTED, 'Checkpoint selection differs: ' + ', '.join(sorted(selected)))
    wanted = workflows.evaluated(rig)
    rest = poses.native_rest(rig)
    action = None
    action_curves = None
    return {'runtime': bpy.app.version_string, 'addon_version': character_designer.bl_info['version'],
            'approved_source': str(canonical), 'native_bones': len(rest), 'all_bones': len(rig.data.bones),
            'source_sha256': {str(path): sha256(path) for path in (
                canonical,
                canonical.parent / 'control_pose_capture.py',
                canonical.parent / 'control_pose_assets.py',
                canonical.parent / 'control_pose_mirror.py',
                REPOSITORY / 'tests' / 'test_control_pose_capture_blender.py')},
            'loaded_file': bpy.data.filepath, 'mode': bpy.context.mode,
            'frame': [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe],
            'selected': sorted(selected), 'active_bone': rig.data.bones.active.name,
            'left_arm_mode': limb_ik_fk.mode_for_rig(rig, arm_entry()),
            'checkpoint_sha256': initial_hashes['checkpoint']}


def capture_current():
    global action, action_curves
    before = artist_state()
    before_actions = {a.as_pointer() for a in bpy.data.actions}
    before_assets = {a.as_pointer() for a in bpy.data.actions if a.asset_data}
    action = capture.save_pose(bpy.context, rig, 'Cosha arm evidence (isolated)',
                               scope='SELECTED', include_fingers=False)
    after = artist_state()
    same_fields(before, after, before.keys())
    require({a.as_pointer() for a in bpy.data.actions} - before_actions == {action.as_pointer()},
            'Capture created more than its one Action.')
    require({a.as_pointer() for a in bpy.data.actions if a.asset_data} - before_assets == {action.as_pointer()},
            'Capture created more than its one internal asset.')
    metadata = poses.asset_metadata(action)
    require(set(metadata['names']) == EXPECTED_CAPTURED, 'The selected arm region was not expanded correctly.')
    require(metadata['rest'] == rest, 'The saved authoring Rest differs from the current native skeleton.')
    action_curves = curves(action)
    return {'action': action.name, 'captured_names': metadata['names'],
            'curve_count': len(action_curves), 'key_count': sum(len(item[3]) for item in action_curves),
            'control_modes': metadata['control_modes'], 'before_state_sha256': state_digest(before),
            'after_state_sha256': state_digest(after), 'state_unchanged': True,
            'pose': pose_error(workflows.evaluated(rig), wanted, tolerance=2e-6)}


def oracle():
    before = artist_state()
    reference = workflows.native_action_reference(rig, action)
    result = pose_error(reference, wanted)
    same_fields(before, artist_state(), before.keys())
    require(curves(action) == action_curves, 'The independent oracle changed the captured Action.')
    return {'method': 'Blender pose.apply_pose_from_action on an unconstrained armature copy',
            'native_matrices_checked': len(wanted), 'capture_oracle': result, 'scratch_copy_removed': True}


def fk_restore():
    limb_ik._mode_set(bpy.context, rig, 'POSE')
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    switch = limb_ik_fk.switch_limb(bpy.context, rig, ('ARM', 'L'), 'FK', keyframe=False)
    switch_error = pose_error(workflows.evaluated(rig), wanted)
    rotate_forearm(.12)
    disturbed = workflows.evaluated(rig)
    disturbed_max = max(poses._difference(disturbed[name], wanted[name]) for name in wanted)
    require(disturbed_max > 1e-4, 'The FK disturbance did not actually change the visible pose.')
    result = poses.apply(bpy.context, rig, action)
    mode = limb_ik_fk.mode_for_rig(rig, arm_entry())
    require(mode == 'FK', 'Applying the asset changed the current FK mode.')
    require(poses.native_rest(rig) == rest, 'FK testing changed authoring Rest.')
    return {'switch': switch, 'switch_no_jump': switch_error, 'disturbance_max_error': disturbed_max,
            'apply': result, 'mode_after': mode, 'restored': pose_error(workflows.evaluated(rig), wanted)}


def ik_restore_and_continue():
    switch = limb_ik_fk.switch_limb(bpy.context, rig, ('ARM', 'L'), 'IK', keyframe=False)
    switch_error = pose_error(workflows.evaluated(rig), wanted)
    entry = arm_entry()
    target = rig.pose.bones[entry['target'].name]
    target.location += Vector((-.012, .009, .007))
    disturbed = workflows.evaluated(rig)
    disturbed_max = max(poses._difference(disturbed[name], wanted[name]) for name in wanted)
    require(disturbed_max > 1e-4, 'The IK disturbance did not actually change the visible pose.')
    result = poses.apply(bpy.context, rig, action)
    require(limb_ik_fk.mode_for_rig(rig, arm_entry()) == 'IK', 'Applying the asset changed the current IK mode.')
    restored = pose_error(workflows.evaluated(rig), wanted)
    before_hand = workflows.evaluated(rig)['hand.L'].translation.copy()
    target.location.x += .002
    moved = workflows.evaluated(rig)['hand.L'].translation
    delta = (moved - before_hand).length
    require(1e-5 < delta < .015, f'The IK target cannot continue smoothly: hand delta {delta}.')
    poses.apply(bpy.context, rig, action)
    return {'switch': switch, 'switch_no_jump': switch_error, 'target': target.name,
            'disturbance_max_error': disturbed_max, 'apply': result, 'restored': restored,
            'continued_target_delta_x': .002, 'continued_hand_distance': delta,
            'restored_after_continue': pose_error(workflows.evaluated(rig), wanted)}


def original_restore_and_return():
    entered = original.enter(bpy.context, rig)
    enter_error = pose_error(workflows.evaluated(rig), wanted)
    session = json.loads(rig[original.SESSION])
    rotate_forearm(.08)
    before = artist_state()
    display = bone_display._snapshot(rig)
    applied = poses.apply(bpy.context, rig, action)
    require(original.active(rig), 'Asset application exited the current Original session.')
    restored = pose_error(workflows.evaluated(rig), wanted)
    after = artist_state()
    same_fields(before, after, ('mode', 'active_object', 'selected_objects', 'active_bone',
                               'selected_bones', 'action', 'slot', 'keys', 'auto_key', 'constraints', 'rest'))
    require(display == bone_display._snapshot(rig), 'Asset application changed Original display.')
    current = json.loads(rig[original.SESSION])
    preserved = ('version', 'rest', 'bones', 'names', 'constraints', 'locks', 'display',
                 'native_groups', 'extra_display', 'extra_bones', 'dress_edit')
    require(all(session[key] == current[key] for key in preserved),
            'Asset application changed Original session structure.')
    before_return = workflows.evaluated(rig)
    left = original.leave(bpy.context, rig)
    require(not original.active(rig), 'Returning to Controls did not finish.')
    require(limb_ik_fk.mode_for_rig(rig, arm_entry()) == 'IK', 'Original return changed the saved IK mode.')
    require(poses.native_rest(rig) == rest, 'Original testing changed authoring Rest.')
    return {'enter': entered, 'enter_no_jump': enter_error, 'apply': applied, 'restored': restored,
            'preserved_session_fields': preserved, 'leave': left,
            'return_no_jump': pose_error(workflows.evaluated(rig), before_return),
            'final_vs_captured': pose_error(workflows.evaluated(rig), wanted)}


try:
    step('load_checkpoint', load)
    step('capture_existing_selection', capture_current)
    step('native_action_oracle', oracle)
    step('restore_in_fk', fk_restore)
    step('restore_in_ik_and_continue', ik_restore_and_continue)
    step('apply_in_original_and_return', original_restore_and_return)
    require(curves(action) == action_curves, 'Integration checks changed the captured Action.')
    report['passed'] = True
except Exception as exc:
    report['error'] = str(exc)
    report['error_type'] = type(exc).__name__
    completed = {entry['name'] for entry in report['steps']}
    report['steps'].extend({'name': name, 'passed': False, 'skipped': True,
                            'reason': 'An earlier required step failed.'}
                           for name in PHASES if name not in completed)
    raise
finally:
    report['finished_at'] = datetime.now(timezone(timedelta(hours=8))).isoformat()
    report['blend_save_performed'] = False
    report['file_protection'] = {
        'checkpoint_sha256_before': initial_hashes.get('checkpoint'),
        'checkpoint_sha256_after': sha256(CHECKPOINT) if CHECKPOINT.is_file() else None,
        'artist_sha256_before': initial_hashes.get('artist'),
        'artist_sha256_after': sha256(ARTIST) if ARTIST.is_file() else None,
        'loaded_file_at_exit': bpy.data.filepath,
    }
    report['file_protection']['checkpoint_unchanged'] = (
        report['file_protection']['checkpoint_sha256_before'] == report['file_protection']['checkpoint_sha256_after'])
    report['file_protection']['artist_unchanged_during_run'] = (
        report['file_protection']['artist_sha256_before'] == report['file_protection']['artist_sha256_after'])
    if initial_hashes.get('checkpoint') and not report['file_protection']['checkpoint_unchanged']:
        report['passed'] = False
        report['file_protection']['error'] = 'The checkpoint file changed while this script ran.'
    checkpoint_report()
    print('COSHA_EVIDENCE', str(REPORT_PATH), 'PASS' if report['passed'] else 'FAIL', flush=True)
