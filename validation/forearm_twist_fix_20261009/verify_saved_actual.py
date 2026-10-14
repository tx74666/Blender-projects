"""Root-run read-only verification of the final, saved artist X.

Use a disposable --background --factory-startup process. This script opens the
saved file, verifies its pair and protected artist data, and writes JSON only.
It never poses the rig, starts a calibration, exports, or saves a blend.
"""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import traceback

import bpy

HERE = Path(__file__).resolve().parent
ARTIST = HERE.parent.parent / 'X.blend'
FINAL_SHA = '17a9312f6ec7f3ec0d709ca89fb2bc918aa94856af0fef544c3ce6ca83bded86'
OUT = HERE / 'saved_actual_verification.json'
spec = importlib.util.spec_from_file_location('forearm_saved_actual_proof', HERE / 'validate_fresh_actual.py')
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)
report = {'status': 'STARTED', 'artist': str(ARTIST), 'expected_artist_sha256': FINAL_SHA,
          'saved': False, 'trial_poses_performed': False, 'exports_performed': False}


def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


def json_plain(value):
    # Cross-process RNA snapshots contain tuples before JSON serialization.
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def main():
    assert bpy.app.background and not bpy.data.filepath, 'Require factory-startup disposable background Blender.'
    layout, live = read('layout_restore_receipt.json'), read('live_fix_receipt.json')
    fingerprint, native = read('protected_backup_fingerprint.json'), read('fresh_actual_report.json')
    manifest = json.loads(proof.MANIFEST.read_text(encoding='utf-8'))
    assert layout['status'] == live['status'] == 'SAVED'
    assert layout['save_result'] == live['save_result'] == ['FINISHED']
    assert Path(layout['artist']).resolve() == Path(live['artist']).resolve() == ARTIST.resolve()
    assert layout['artist_sha256'] == FINAL_SHA == proof.sha(ARTIST), 'The final saved artist file changed.'
    assert live['runtime'] == [0, 77, 12] and live['all_152_deployment_files_verified']
    assert live['all_original_key_coordinates_and_state_preserved']
    assert live['all_geometry_weights_native_rest_raw_pose_constraints_actions_preserved']
    assert not live['trial_poses_performed']
    assert fingerprint['status'] == native['status'] == 'PASS'
    assert fingerprint['backup_sha256'] == native['backup_sha256'] == proof.BACKUP_SHA
    assert proof.sha(HERE / 'X_before_forearm_twist_fix.blend') == proof.BACKUP_SHA
    assert live['before_protected_sha256'] == fingerprint['protected_sha256']
    assert proof.digest(fingerprint['protected']) == fingerprint['protected_sha256']
    assert live['projection_sha256'] == native['projection_sha256'] == fingerprint['projection_sha256'] == proof.PROJECTION_SHA
    assert proof.sha(proof.MANIFEST) == proof.PROJECTION_SHA
    assert manifest['version'] == '0.77.12' and len(manifest['files']) == 152

    # Verify the actual installed source identified by the live save receipt,
    # then import the same frozen projection in this disposable process.
    installed = Path(live['module_root'])
    assert installed.is_dir()
    for relative, expected in manifest['files'].items():
        assert proof.sha(installed / relative) == expected, 'Installed source differs: ' + relative
    sys.path.insert(0, str(proof.REPOSITORY / 'tools'))
    from release_projection import load_source
    source = load_source('character_designer', proof.MANIFEST, root=proof.REPOSITORY)
    assert source.projection_sha256 == proof.PROJECTION_SHA and source.version == '0.77.12'
    sys.path.insert(0, str(proof.CANDIDATE.parent))
    import character_designer
    assert Path(character_designer.__file__).resolve().parent == proof.CANDIDATE.resolve()
    assert tuple(character_designer.bl_info['version']) == (0, 77, 12)
    character_designer.register()
    opened = bpy.ops.wm.open_mainfile(filepath=str(ARTIST))
    assert opened == {'FINISHED'} and Path(bpy.data.filepath).resolve() == ARTIST.resolve()
    from character_designer import forearm_twist as runtime
    runtime._complete_runtime_lifecycle()
    rig, mesh = bpy.data.objects['CoshaRig'], bpy.data.objects['Cosha']
    records = runtime._records(mesh)
    assert runtime._SESSION is None and runtime.PREVIEW_KEY not in mesh
    assert set(records) == {'L', 'R'} and records == native['records'] == live['records']
    assert mesh.name not in runtime._ERRORS, runtime._ERRORS.get(mesh.name)
    owned = set()
    for side in ('L', 'R'):
        record = records[side]
        key = runtime._managed_key(mesh, side, record, repair_name=False)
        assert record['paired'] and record['enabled'] and record['distribution'] == 'WRIST_CONTINUOUS'
        assert record['support_topology'] and key.name not in native['original_keys']
        assert key.value == 1. and not key.mute and key.relative_key.name == 'Basis'
        assert not key.vertex_group
        # Read-only scoped preflight proves the saved mesh support. The full
        # protected snapshot below independently checks every calibrated Rest.
        prepared = runtime._current_topology_record(mesh.data, record)
        assert prepared == record, 'Saved calibration needs migration or recapture.'
        owned.add(key.name)
    expected_names = native['original_keys'] + [records['L']['key'], records['R']['key']]
    assert list(mesh.data.shape_keys.key_blocks.keys()) == expected_names

    expected = copy.deepcopy(fingerprint['protected'])
    expected['objects']['Cosha']['props'].pop(runtime.RECORD_KEY, None)
    expected['scene']['props'].pop(runtime.LOCK_KEY, None)
    expected['scene']['render_lock'] = None
    actual = json_plain(proof.protected_snapshot(owned, committed=True))
    report.update(expected_protected_sha256=proof.digest(expected),
                  actual_protected_sha256=proof.digest(actual))
    if expected != actual:
        diagnostic = {'expected': expected, 'actual': actual}
        (HERE / 'saved_protection_diagnostic.json').write_text(
            json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding='utf-8')
    proof.compare(expected, actual, 'Final saved X artist protection')
    assert bpy.context.scene.frame_current == 46
    assert bpy.context.scene.tool_settings.use_keyframe_insert_auto == live['before_context']['auto_key']
    assert bpy.context.view_layer.objects.active == rig and rig.data.bones.active.name == live['before_context']['active_bone']
    assert proof.sha(ARTIST) == FINAL_SHA and proof.sha(HERE / 'X_before_forearm_twist_fix.blend') == proof.BACKUP_SHA
    report.update(status='PASS', artist_sha256_after_read=proof.sha(ARTIST),
                  backup_sha256_after_read=proof.BACKUP_SHA, runtime=list(character_designer.bl_info['version']),
                  projection_sha256=source.projection_sha256, manifest_file_count=152,
                  actual_import_root=str(proof.CANDIDATE), installed_source_root=str(installed),
                  blender=bpy.app.version_string, original_key_names=native['original_keys'],
                  owned_key_names=sorted(owned), records=records,
                  all_protected_artist_data_preserved=True, all_installed_source_files_verified=True,
                  saved_frame=bpy.context.scene.frame_current,
                  saved_active_bone=rig.data.bones.active.name)


try:
    main()
except Exception:
    report.update(status='FAIL', error=traceback.format_exc())
    raise
finally:
    temporary = OUT.with_suffix('.json.writing')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(OUT)
    print('FOREARM_SAVED_ACTUAL_VERIFICATION_' + report['status'], str(OUT), flush=True)
