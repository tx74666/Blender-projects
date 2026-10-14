"""Root executes once in the artist Console after the verified 0.77.12 deploy.

Protect the current live data, refresh through the normal operator, create the
already-proven pair without posing, verify, and save. No orphan-key adoption,
mesh/weight/Rest edits, trial angles, whole-blend replacement, or layout writes.
"""
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import time
import traceback

import bpy

BASE = Path(__file__).resolve().parent
ARTIST = BASE.parent.parent / 'X.blend'
BACKUP = BASE / 'X_before_forearm_twist_fix.blend'
ARTIST_SHA = '40bd97a1e27ab3daab2bd2600e705561f5aed9c6883cddf2e18d6eb2d8607518'
BACKUP_SHA = '15e3593a16ccd53a85690e3f9c862a2338b58317291e43a9a8cda7acdd25eebb'
VERSION = (0, 77, 12)
RECEIPT = BASE / 'live_fix_receipt.json'
CHANGED = ('__init__.py', 'body_calibration_ui.py', 'forearm_twist.py',
           'forearm_twist_cache.py', 'forearm_twist_edit.py', 'forearm_twist_topology.py',
           'unity_export_worker.py', 'unity_forearm.py')
spec = importlib.util.spec_from_file_location('forearm_live_protection', BASE / 'validate_fresh_actual.py')
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)
manifest = json.loads(proof.MANIFEST.read_text(encoding='utf-8'))
native = json.loads((BASE / 'fresh_actual_report.json').read_text(encoding='utf-8'))
fingerprint = json.loads((BASE / 'protected_backup_fingerprint.json').read_text(encoding='utf-8'))
assert native['status'] == fingerprint['status'] == 'PASS'
assert fingerprint['backup_sha256'] == native['backup_sha256'] == BACKUP_SHA
assert fingerprint['projection_sha256'] == native['projection_sha256'] == proof.PROJECTION_SHA
assert proof.sha(proof.MANIFEST) == proof.PROJECTION_SHA and len(manifest['files']) == 152
assert manifest['version'] == '0.77.12'
assert not bpy.app.background, 'This is the protected artist operation, not a native fixture.'
assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
assert proof.sha(ARTIST) == ARTIST_SHA and proof.sha(BACKUP) == BACKUP_SHA
assert not RECEIPT.exists(), 'Already applied: inspect the receipt; do not repeat.'
rig, mesh = bpy.data.objects['CoshaRig'], bpy.data.objects['Cosha']
assert bpy.context.object == rig and bpy.context.mode == 'POSE'
assert bpy.context.scene.frame_current == 46
from character_designer import forearm_twist as old_runtime, body_original_mode
assert old_runtime._SESSION is None and old_runtime._records(mesh) == {}
assert old_runtime.PREVIEW_KEY not in mesh and not body_original_mode.active(rig)
assert rig.animation_data is None or (rig.animation_data.action is None and not rig.animation_data.nla_tracks)


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.writing')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def disk_proof(main):
    source = Path(main.__file__).resolve().parent
    differences = {name: proof.sha(source / name) if (source / name).is_file() else None
                   for name, expected in manifest['files'].items()
                   if not (source / name).is_file() or proof.sha(source / name) != expected}
    assert not differences, 'Active deployment differs from the frozen 152-file projection: ' + str(differences)
    return source


def context_state():
    active = bpy.context.view_layer.objects.active
    return {'object': active.name if active else None, 'mode': bpy.context.mode,
            'selected_objects': sorted(obj.name for obj in bpy.context.selected_objects),
            'active_bone': rig.data.bones.active.name if rig.data.bones.active else None,
            'selected_bones': sorted(pb.name for pb in rig.pose.bones
                if getattr(pb, 'select', getattr(pb.bone, 'select', False))),
            'auto_key': bpy.context.scene.tool_settings.use_keyframe_insert_auto}


def layout_state():
    return [{'screen': window.screen.name,
             'areas': [(area.type, area.ui_type, area.x, area.y, area.width, area.height,
                        [(space.type, getattr(space, 'tree_type', None),
                          getattr(space, 'shader_type', None), getattr(space, 'pin', None))
                         for space in area.spaces]) for area in window.screen.areas]}
            for window in bpy.context.window_manager.windows]


def ui_values():
    settings = bpy.context.window_manager.character_designer_forearm_twist
    return {p.identifier: getattr(settings, p.identifier) for p in settings.bl_rna.properties
            if p.identifier not in ('rna_type', 'name') and p.type not in ('POINTER', 'COLLECTION')}


def restore_ui(runtime, values):
    old_busy = runtime._UI_BUSY
    runtime._UI_BUSY = True
    try:
        settings = bpy.context.window_manager.character_designer_forearm_twist
        for name, value in values.items():
            setattr(settings, name, value)
    finally:
        runtime._UI_BUSY = old_busy


before = proof.protected_snapshot()
if proof.digest(before) != fingerprint['protected_sha256']:
    atomic_json(BASE / 'live_preflight_diagnostic.json',
                {'expected_sha256': fingerprint['protected_sha256'], 'actual_sha256': proof.digest(before),
                 'expected': fingerprint['protected'], 'actual': before})
    raise AssertionError('The current live artist data differs from the protected native input; no changes made.')
pre_context, pre_layout, pre_ui = context_state(), layout_state(), ui_values()
pre_metadata = mesh.get(old_runtime.RECORD_KEY)
original_names = set(mesh.data.shape_keys.key_blocks.keys())
assert original_names == set(native['original_keys'])
pre_key_ids = {key.name: key.as_pointer() for key in mesh.data.shape_keys.key_blocks}
report = {'status': 'SCHEDULED', 'artist': str(ARTIST), 'artist_sha256_before': ARTIST_SHA,
          'backup': str(BACKUP), 'backup_sha256': BACKUP_SHA,
          'projection_sha256': proof.PROJECTION_SHA, 'before_protected_sha256': proof.digest(before),
          'original_key_names': sorted(original_names), 'changed_package_files': list(CHANGED),
          'before_context': pre_context, 'before_layout': pre_layout, 'before_forearm_ui': pre_ui}
atomic_json(BASE / 'live_fix_progress.json', report)
deadline = time.monotonic() + 20.


def assert_artist_context():
    assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
    assert bpy.data.objects.get('CoshaRig') == rig and bpy.data.objects.get('Cosha') == mesh
    assert context_state() == pre_context, 'Artist selection, frame, mode or auto-key changed.'
    assert layout_state() == pre_layout, 'Artist layout changed during this operation.'


def rollback_owned_pair(runtime, created_ids):
    if runtime._SESSION is not None:
        assert runtime._SESSION['mesh'] == mesh, 'Another preview owns the active session.'
        runtime.finish_test(bpy.context, False)
    records = runtime._records(mesh)
    if records:
        # Only keys proven to have been created by this transaction may be
        # removed. The four similarly named, unrecorded artist keys are never
        # considered candidates, even after a failed after-check.
        assert set(records) == {'L', 'R'} and set(records) == set(created_ids)
        for side, record in records.items():
            key = runtime._managed_key(mesh, side, record, repair_name=False)
            assert key.name not in original_names and key.as_pointer() == created_ids[side]
            assert key.name == native['records'][side]['key']
        runtime.remove_paired_calibration(bpy.context, mesh)
    if pre_metadata is None:
        assert runtime.RECORD_KEY not in mesh
    else:
        mesh[runtime.RECORD_KEY] = pre_metadata
    restore_ui(runtime, pre_ui)
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = pre_context['auto_key']
    bpy.context.view_layer.update()
    proof.compare(before, proof.protected_snapshot(), 'Owned-pair rollback')
    assert_artist_context()
    assert proof.sha(ARTIST) == ARTIST_SHA


def apply_after_refresh():
    saved = False
    calibration_started = False
    runtime = None
    created_ids = {}
    try:
        import character_designer
        if tuple(character_designer.bl_info['version']) != VERSION:
            error = getattr(character_designer, 'ADDON_REFRESH_LAST_ERROR', '')
            assert not error, 'Add-on refresh failed: ' + error
            if time.monotonic() < deadline:
                return .25
            raise AssertionError('The verified 0.77.12 runtime did not become ready; no calibration applied.')
        source = disk_proof(character_designer)
        runtime = importlib.import_module('character_designer.forearm_twist')
        assert Path(runtime.__file__).resolve().parent == source
        assert hasattr(runtime, 'ForearmTwistRecaptureRequired')
        loaded = {}
        for name in CHANGED:
            if name in ('__init__.py', 'unity_export_worker.py'):
                continue
            module = importlib.import_module('character_designer.' + name[:-3])
            assert Path(module.__file__).resolve().parent == source
            loaded[name] = str(module.__file__)
        runtime._complete_runtime_lifecycle()
        proof.compare(before, proof.protected_snapshot(), 'Refresh preserved live artist data')
        assert_artist_context()
        assert runtime._SESSION is None and runtime._records(mesh) == {}
        assert all(mesh.data.shape_keys.key_blocks[name].as_pointer() == pointer
                   for name, pointer in pre_key_ids.items()), 'Refresh replaced an artist key identity.'
        # Reloaded RNA may need its transient calibration controls restored;
        # the guard prevents UI setters from editing any saved calibration.
        restore_ui(runtime, pre_ui)
        assert ui_values() == pre_ui
        assert abs(pre_ui['curve_strength'] - .4) < 1e-7 and abs(pre_ui['transition'] - .1) < 1e-7
        assert pre_ui['ring_index'] == 3 and abs(pre_ui['ratio'] - .4434150457382202) < 1e-7
        report.update(status='APPLYING', runtime=list(VERSION), module_root=str(source),
                      loaded_module_paths=loaded,
                      changed_file_sha256={name: manifest['files'][name] for name in CHANGED})
        atomic_json(BASE / 'live_fix_progress.json', report)
        try:
            bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
            settings = bpy.context.window_manager.character_designer_forearm_twist
            old_busy = runtime._UI_BUSY
            runtime._UI_BUSY = True
            settings.side, settings.symmetry = 'L', True
            runtime._UI_BUSY = old_busy
            calibration_started = True
            record = runtime.start_paired_test(bpy.context)
            assert runtime._SESSION['mesh'] == mesh and runtime._SESSION['side'] == 'L'
            assert not runtime._SESSION['pose_locked']
            for field in ('chain', 'target', 'topology', 'rest', 'rings', 'vertices', 'positions',
                          'range_start', 'range_end', 'current_ring', 'curve_strength', 'transition',
                          'distribution', 'support_topology'):
                assert record.get(field) == native['records']['L'].get(field), 'Live fresh capture differs from native proof: ' + field
            left_key = runtime._managed_key(mesh, 'L', record, repair_name=False)
            assert left_key.name == native['records']['L']['key'] and left_key.name not in original_names
            created_ids['L'] = left_key.as_pointer()
            session = runtime._SESSION
            try:
                runtime.finish_test(bpy.context, True)
            finally:
                # The official finisher records every counterpart it created
                # before dropping the preview session. Keep that ownership
                # ledger even if a later restore/after-check raises.
                for side, name in session.get('added_keys', {}).items():
                    key = runtime._managed_key(mesh, side, {'key': name}, required=False, repair_name=False)
                    if key is not None:
                        assert name not in original_names
                        created_ids[side] = key.as_pointer()
            records = runtime._records(mesh)
            assert set(records) == {'L', 'R'} and runtime._SESSION is None and runtime.PREVIEW_KEY not in mesh
            for side, record in records.items():
                key = runtime._managed_key(mesh, side, record, repair_name=False)
                assert key.name == native['records'][side]['key'] and key.name not in original_names
                created_ids[side] = key.as_pointer()
                assert record == native['records'][side], 'Committed record differs from the actual native proof.'
                assert record['paired'] and record['enabled'] and key.value == 1. and not key.mute
            assert mesh.name not in runtime._ERRORS, runtime._ERRORS.get(mesh.name)
            assert set(mesh.data.shape_keys.key_blocks.keys()) == original_names | {r['key'] for r in records.values()}
            assert all(mesh.data.shape_keys.key_blocks[name].as_pointer() == pointer
                       for name, pointer in pre_key_ids.items()), 'An artist key identity changed.'
            expected = copy.deepcopy(before)
            expected['objects']['Cosha']['props'].pop(runtime.RECORD_KEY, None)
            expected['scene']['props'].pop(runtime.LOCK_KEY, None)
            expected['scene']['render_lock'] = None
            owned_names = {r['key'] for r in records.values()}
            proof.compare(expected, proof.protected_snapshot(owned_names, committed=True), 'Fresh live pair preserved artist data')
        except Exception:
            rollback_owned_pair(runtime, created_ids)
            calibration_started = False
            report['rollback'] = 'Only transaction-owned new outputs removed; artist protection matched pre-refresh state.'
            raise
        finally:
            restore_ui(runtime, pre_ui)
            bpy.context.scene.tool_settings.use_keyframe_insert_auto = pre_context['auto_key']
        assert_artist_context()
        assert proof.sha(ARTIST) == ARTIST_SHA and proof.sha(BACKUP) == BACKUP_SHA
        report.update(records=runtime._records(mesh), after_context=context_state(),
                      after_layout=layout_state(), after_forearm_ui=ui_values(),
                      all_original_key_coordinates_and_state_preserved=True,
                      all_geometry_weights_native_rest_raw_pose_constraints_actions_preserved=True,
                      all_152_deployment_files_verified=True, trial_poses_performed=False)
        result = bpy.ops.wm.save_mainfile()
        assert result == {'FINISHED'}, 'Native artist save did not confirm success.'
        saved = True
        assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
        report.update(status='SAVED', save_result=sorted(result), artist_sha256_after=proof.sha(ARTIST),
                      backup_sha256_after=proof.sha(BACKUP), blender=bpy.app.version_string)
        atomic_json(RECEIPT, report)
        atomic_json(BASE / 'live_fix_progress.json', report)
        print('FOREARM_LIVE_PAIR_VERIFIED_SAVED_OK', tuple(VERSION), report['artist_sha256_after'])
    except Exception:
        original_error = traceback.format_exc()
        if calibration_started and not saved and runtime is not None:
            try:
                rollback_owned_pair(runtime, created_ids)
                report['rollback'] = 'Transaction-owned new outputs removed; all pre-refresh artist data restored.'
            except Exception:
                report['rollback_error'] = traceback.format_exc()
        if runtime is not None:
            restore_ui(runtime, pre_ui)
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = pre_context['auto_key']
        report.update(status='SAVED_RECEIPT_FAILED' if saved else 'FAILED', error=original_error)
        atomic_json(BASE / 'live_fix_progress.json', report)
        (BASE / 'live_fix_error.txt').write_text(original_error, encoding='utf-8')
        print(original_error)
    return None


import character_designer
disk_proof(character_designer)
if tuple(character_designer.bl_info['version']) != VERSION:
    assert not getattr(character_designer, 'ADDON_REFRESH_PENDING', False)
    assert character_designer._source_changed(), 'Installed source did not change; refuse an unproved reload.'
    character_designer.ADDON_REFRESH_LAST_STATE = True
    result = bpy.ops.character_designer.refresh_addon()
    assert result == {'FINISHED'}, 'Normal protected add-on refresh was refused.'
bpy.app.timers.register(apply_after_refresh, first_interval=.25)
print('FOREARM_LIVE_PROTECTED_REFRESH_AND_PAIR_SCHEDULED')
