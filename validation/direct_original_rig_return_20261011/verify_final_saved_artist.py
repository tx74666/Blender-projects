"""Read only reopen check of a hash-equal copy of the final saved artist."""
import hashlib, importlib, json, math, sys, traceback
from pathlib import Path
import bpy

EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(EVIDENCE))
from validation_preservation import asset_snapshot, evaluate_forearm_runtime
import verify_direct_return_isolated as verifier

report = {'completed': False, 'scope': 'Final hash-equal copy only; no saves or artist mutation.'}
copy_path = EVIDENCE / 'artist_final_validation.blend'
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
receipt = json.loads((EVIDENCE / 'artist_cleanup_receipt.json').read_text(encoding='utf-8'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
try:
    assert sha(artist) == sha(copy_path) == receipt['file_sha256']
    runtime = EVIDENCE / 'release_07724'
    sys.path.insert(0, str(runtime))
    cd = importlib.import_module('character_designer')
    assert Path(cd.__file__).resolve().is_relative_to(runtime)
    assert tuple(cd.bl_info['version']) == (0, 77, 24)
    cd.register()
    from character_designer import animation_worklist as worklist, animation_worklist_target as target, unity_animation as ua
    from character_designer import animation_worklist_fingerprint as fp
    bpy.ops.wm.open_mainfile(filepath=str(copy_path), use_scripts=False, load_ui=False)
    scene, rig = bpy.data.scenes['Scene'], bpy.data.objects['CoshaRig']
    assert receipt['removed_scene'] not in bpy.data.scenes
    assert 'CoshaRig.001' not in bpy.data.objects
    verifier.select_rig(scene, rig)
    saved = scene.character_designer_animation_worklist
    item = worklist._item(saved, receipt['item_id'])
    target.ensure_active(bpy.context, rig)
    assert item.rig is rig and saved.rig is rig
    assert rig.animation_data.action is item.custom_action
    assert item.source_action.library and not item.custom_action.library
    assert fp.fingerprint_action(item.source_action, item.source_slot)['action_fingerprint'] == fp.fingerprint_action(item.custom_action, item.custom_slot)['action_fingerprint'] == receipt['action_fingerprint']
    assets = asset_snapshot(scene, rig, ua)
    assert assets['component_sha256'] == receipt['original_assets_after_cleanup']['component_sha256']
    assert len(rig.data.bones) == receipt['bone_count'] == 346
    assert sum(pb.custom_shape is not None for pb in rig.pose.bones) == receipt['widgets']
    packet = ua.load_package(str(Path(receipt['packet'])))
    mapping = ua._mapping(rig, packet, scene.unit_settings.scale_length)
    authored = set(mapping.indices) - set(mapping.controls.delegated_names)
    rows = []
    for index in (0, 29, 58):
        ua._set_frame(scene, 1.0 + packet['frames'][index]['time'] * scene.render.fps / scene.render.fps_base)
        bpy.context.view_layer.update()
        runtime_state = evaluate_forearm_runtime(scene, rig)
        evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
        expected = ua.expected_world_matrices(rig, packet, index, unit_scale=scene.unit_settings.scale_length, mapping=mapping)
        maximum = 0.0
        for name in authored:
            actual = evaluated.matrix_world @ evaluated.pose.bones[name].matrix
            desired = expected[name]
            assert all(math.isfinite(value) for matrix in (actual, desired) for row in matrix for value in row)
            maximum = max(maximum, *(abs(actual[r][c] - desired[r][c]) for r in range(4) for c in range(4)))
        assert maximum <= 2e-4
        rows.append({'sample': index, 'maximum_matrix_error': maximum, 'forearm_errors': runtime_state['errors']})
    report.update({'completed': True, 'file_sha256': sha(artist), 'copy_sha256': sha(copy_path),
                   'scenes': list(bpy.data.scenes.keys()), 'rig': rig.name, 'bone_count': len(rig.data.bones),
                   'source': item.source_action.name, 'custom': item.custom_action.name, 'assets': assets,
                   'samples': rows, 'persistent_adoption_verified': True})
except Exception as exc:
    report.update({'error': str(exc), 'traceback': traceback.format_exc()})
finally:
    report['artist_file_unchanged'] = sha(artist) == receipt['file_sha256']
    report['copy_file_unchanged'] = sha(copy_path) == receipt['file_sha256']
    report['completed'] = bool(report['completed'] and report['artist_file_unchanged'] and report['copy_file_unchanged'])
    (EVIDENCE / 'artist_final_reopen_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('FINAL_ARTIST_REOPEN ' + json.dumps({k: report.get(k) for k in ('completed', 'error', 'scenes', 'rig', 'bone_count', 'artist_file_unchanged')}, ensure_ascii=False))
if not report['completed']:
    raise RuntimeError(report.get('error', 'Final reopening check failed.'))
