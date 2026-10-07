"""Apply validated native-FK Forearm Twist to the live artist, with rollback.

Prepared for a coordinated native Blender Console call AFTER official deploy.
This script does not register/reload an add-on or touch unrelated runtime state.
Every invocation saves a unique full safety copy before its first data mutation.
"""
from __future__ import annotations

import ast
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import traceback
import uuid

import bpy

HERE = Path(__file__).resolve().parent
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
EXPECTED_PID = 12696
FUNCTIONS = ('_resolve_rig', '_preview_pose_locked')
EXPECTED_INSTALLED_VERSION = (0, 76, 4)
EXPECTED_SOURCE_SHA256 = {
    'forearm_twist.py': '4f159b83a2bac2aebbc9e23f03ce958da75a10728d0f21010f1178b476d66bf3',
    'forearm_twist_math.py': 'bf32b47bdb11b897467b8606578baaff8acc218150ed3dab83cced03e364c421',
    'unity_forearm.py': '3979192a00a93417ee077d6290c71a229b57d2de04ebf04c41efa65bc321c1bb',
}


def load_guard_helpers():
    spec = importlib.util.spec_from_file_location('_cd_actual_forearm_guards', HERE / 'validate_actual.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # __name__ differs: validation main never runs.
    return module


def body_key_snapshot(body, guard):
    keys = body.data.shape_keys
    return {k.name: {'co': guard.coordinates(k), 'value': k.value, 'mute': k.mute,
                     'relative': k.relative_key.name, 'vertex_group': k.vertex_group,
                     'slider_min': k.slider_min, 'slider_max': k.slider_max}
            for k in keys.key_blocks} if keys else {}


def restore_key_snapshot(body, before):
    """Remove only invocation-created keys; old unrecorded CD names are protected."""
    keys = body.data.shape_keys
    if keys:
        added = [k for k in keys.key_blocks if k.name not in before]
        for key in added:
            assert not any(k.name in before and k.relative_key == key for k in keys.key_blocks), \
                'An original key now references a new output; rollback must stop before deletion'
        for key in reversed(added):
            body.shape_key_remove(key)
    if not before:
        assert body.data.shape_keys is None, 'New Shape Key container was not fully removed'
        return
    keys = body.data.shape_keys
    assert keys and set(keys.key_blocks.keys()) == set(before), 'Original Shape Key membership changed'
    for name, saved in before.items():
        key = keys.key_blocks[name]
        key.data.foreach_set('co', saved['co'])
        key.value, key.mute = saved['value'], saved['mute']
        key.relative_key = keys.key_blocks[saved['relative']]
        key.vertex_group = saved['vertex_group']
        key.slider_min, key.slider_max = saved['slider_min'], saved['slider_max']
    keys.update_tag()
    body.data.update()


def optional_entry(mapping, name):
    return (name in mapping, mapping.get(name))


def restore_entry(mapping, name, saved):
    if saved[0]:
        mapping[name] = saved[1]
    else:
        mapping.pop(name, None)


def exact_functions(runtime, source_path, expected_sha, guard):
    assert guard.file_hash(source_path) == expected_sha, 'Installed Forearm Twist differs from the PASS candidate'
    source = source_path.read_text(encoding='utf-8-sig')
    tree = ast.parse(source, filename=str(source_path))
    nodes = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in FUNCTIONS}
    assert set(nodes) == set(FUNCTIONS), 'Both exact native FK functions must exist'
    assert all(not n.decorator_list for n in nodes.values()), 'Unexpected function decorators'
    patch_tree = ast.fix_missing_locations(ast.Module(body=[nodes[n] for n in FUNCTIONS], type_ignores=[]))
    # Compile before mutating live globals. Only these two top-level functions run.
    code = compile(patch_tree, str(source_path), 'exec')
    signatures = {n: guard.digest(ast.dump(nodes[n], include_attributes=False)) for n in FUNCTIONS}
    return code, signatures


def installed_version(init_path):
    """Read the deployed version without executing/reloading package init."""
    tree = ast.parse(init_path.read_text(encoding='utf-8-sig'), filename=str(init_path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'bl_info' for t in node.targets):
            return tuple(ast.literal_eval(node.value)['version'])
    raise AssertionError('Installed bl_info literal was not found')


def apply(validation_receipt=HERE / 'actual_final_1914' / 'actual_result.json'):
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '_' + uuid.uuid4().hex[:8]
    run_dir = HERE / ('apply_artist_' + run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    receipt = run_dir / 'receipt.json'
    report = {'status': 'FAILED', 'stage': 'preflight', 'run_id': run_id,
              'pid': os.getpid(), 'blender_version': bpy.app.version_string,
              'validation_receipt': str(Path(validation_receipt).resolve()),
              'tracebacks': [], 'artist_save_attempted': False, 'artist_save_confirmed': False}
    guard = runtime = body = rig = None
    state = None
    old_functions = None
    patch_applied = mutation_started = False
    try:
        assert not bpy.app.background, 'Artist apply is allowed only in the live interactive process'
        assert bpy.app.version[:2] == (5, 2), 'Expected Blender 5.2'
        assert os.getpid() == EXPECTED_PID, 'Artist process identity changed; re-audit before applying'
        assert Path(bpy.data.filepath).resolve() == ARTIST, 'Exact artist X.blend identity required'
        assert not any(w.screen.is_animation_playing for w in bpy.context.window_manager.windows), 'Stop playback first'
        import character_designer
        from character_designer import forearm_twist as runtime
        assert not runtime._SESSION and not runtime._BUSY and not runtime._UI_BUSY, 'Runtime is busy or has an unfinished test'
        body, rig = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
        assert runtime.PREVIEW_KEY not in body, 'Unfinished preview marker is protected'
        source = Path(runtime.__file__).resolve()
        expected_install = (Path(bpy.utils.user_resource('SCRIPTS')) / 'addons' / 'character_designer').resolve()
        assert source.parent == expected_install, 'Live module is not from the Blender 5.2 installed package'
        guard = load_guard_helpers()
        verified = json.loads(Path(validation_receipt).read_text(encoding='utf-8'))
        assert verified['status'] == 'PASS' and verified['stage'] == 'complete', 'Actual-model PASS receipt required'
        assert verified.get('protected_data_unchanged') and verified.get('pose_restored'), 'PASS protection incomplete'
        assert len(verified.get('tests', ())) >= 16, 'Actual-model pose cases incomplete'
        installed_hashes = {name: guard.file_hash(source.parent / name) for name in EXPECTED_SOURCE_SHA256}
        assert installed_hashes == EXPECTED_SOURCE_SHA256, 'Official installed sources differ from the final reviewed three hashes'
        assert verified['source_sha256'] == EXPECTED_SOURCE_SHA256, 'PASS receipt uses a different source candidate'
        deployed_version = installed_version(source.parent / '__init__.py')
        assert deployed_version == EXPECTED_INSTALLED_VERSION, 'Official deployed release version is not 0.76.4'
        code, signatures = exact_functions(runtime, source, verified['source_sha256']['forearm_twist.py'], guard)
        poses = {o.name: guard.pose_state(o) for o in bpy.data.objects if o.type == 'ARMATURE'}
        selection = guard.selection_state()
        assert selection['mode'] in {'OBJECT', 'POSE'}, 'Preserve Edit/Sculpt state; do not apply here'
        old_records = runtime._records(body)
        owned = {r['key'] for r in old_records.values()}
        original_keys = {o.name: [k.name for k in o.data.shape_keys.key_blocks
                                 if o is not body or k.name not in owned]
                         for o in bpy.data.objects if o.type == 'MESH' and o.data.shape_keys}
        protected = guard.protected_state(original_keys)
        frame, subframe = bpy.context.scene.frame_current, bpy.context.scene.frame_subframe
        settings = bpy.context.window_manager.character_designer_forearm_twist
        pointer = body.as_pointer()
        state = {'poses': poses, 'selection': selection, 'frame': frame, 'subframe': subframe,
                 'original_keys': original_keys, 'protected': protected,
                 'body_keys': body_key_snapshot(body, guard), 'active_key_index': body.active_shape_key_index,
                 'record_json': body.get(runtime.RECORD_KEY), 'pointer': pointer,
                 'cache': optional_entry(runtime._CACHE, pointer),
                 'output_cache': optional_entry(runtime._OUTPUT_CACHE, pointer),
                 'error': optional_entry(runtime._ERRORS, body.name),
                 'key_references': {i: k for i, k in runtime._KEY_REFERENCES.items() if i[0] == pointer},
                 'render_lock': bpy.context.scene.render.use_lock_interface,
                 'render_lock_property': optional_entry(bpy.context.scene, runtime.LOCK_KEY),
                 'settings': {n: getattr(settings, n) for n in ('side', 'test_angle', 'ring_index')}}
        report.update(artist_path=str(ARTIST), artist_dirty_before=bpy.data.is_dirty,
                      artist_disk_sha256_before=guard.file_hash(ARTIST),
                      installed_source_sha256=guard.file_hash(source), addon_version=list(character_designer.bl_info['version']),
                      installed_source_hashes=installed_hashes, installed_addon_version=list(deployed_version),
                      loaded_package_version=list(character_designer.bl_info['version']),
                      package_reloaded=False,
                      function_ast_sha256=signatures, original_frame=frame, original_selection=selection,
                      original_pose_sha256=guard.digest(poses), existing_records=old_records)
        report['stage'] = 'save_complete_live_safety_copy'
        safety_copy = run_dir / 'artist_live_before_apply.blend'
        result = bpy.ops.wm.save_as_mainfile(filepath=str(safety_copy), copy=True)
        assert result == {'FINISHED'} and safety_copy.exists(), 'Live safety copy did not save successfully'
        assert Path(bpy.data.filepath).resolve() == ARTIST, 'Safety-copy operation changed artist identity'
        assert guard.file_hash(ARTIST) == report['artist_disk_sha256_before'], 'Safety-copy operation overwrote artist disk'
        report['safety_copy'] = {'path': str(safety_copy), 'bytes': safety_copy.stat().st_size,
                                 'sha256': guard.file_hash(safety_copy), 'result': sorted(result)}
        guard.check_protection(protected, original_keys)
        for name, pose in poses.items():
            guard.assert_pose(bpy.data.objects[name], pose)
        assert guard.selection_state() == selection, 'Saving a copy changed current selection/mode'
        assert bpy.context.scene.frame_current == frame and bpy.context.scene.frame_subframe == subframe
        report['stage'] = 'verify_live_model_matches_actual_PASS'
        verified_protection = verified['protected_before']
        for field in ('topology', 'weights', 'geometry', 'uv'):
            assert protected['meshes']['Cosha'][field] == verified_protection['meshes']['Cosha'][field], \
                f'Live Cosha {field} changed since actual-model validation'
        # This is stricter than rest-only: it also protects bone parents, colors,
        # display scales and constraint definitions from a stale model receipt.
        assert protected['armatures']['CoshaRig'] == verified_protection['armatures']['CoshaRig'], \
            'Live bones/rest/parents/display/constraints differ from actual-model PASS'
        report['model_identity_matches_PASS'] = True
        report['stage'] = 'patch_only_two_validated_functions'
        old_functions = {n: getattr(runtime, n) for n in FUNCTIONS}
        patch_applied = True
        exec(code, runtime.__dict__)
        assert all(getattr(runtime, n).__globals__ is runtime.__dict__ for n in FUNCTIONS)
        targets = {}
        for side in ('L', 'R'):
            resolved_arm, resolved = runtime._resolve_rig(body, side)
            assert resolved_arm is rig and resolved.get('native_source') and resolved.get('fk_source'), \
                f'{side}: live arm is not the validated native FK/Original source'
            assert resolved['target'].name == resolved['chain'][2], f'{side}: inactive IK target resolved'
            assert list(resolved['chain']) == verified['records'][side]['chain'], f'{side}: native bone chain changed'
            assert runtime._rest_signature(rig, resolved['chain']) == verified['records'][side]['rest'], \
                f'{side}: actual rest frames changed'
            targets[side] = {'target': resolved['target'].name, 'chain': list(resolved['chain']),
                             'pose_locked': bool(runtime._preview_pose_locked(rig, rig.pose.bones[resolved['target'].name], resolved))}
        report['native_targets'] = targets
        report['stage'] = 'capture_confirm_paired_existing_ForearmTwist'
        guard.object_mode()
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        body.select_set(True)
        bpy.context.view_layer.objects.active = body
        mutation_started = True
        runtime.start_test(bpy.context, body, 'L', symmetry=True, recapture=bool(old_records),
                           continuous=True, initial_angle=None)
        runtime.finish_test(bpy.context, confirm=True)
        assert not runtime._SESSION and runtime.PREVIEW_KEY not in body
        records = runtime._records(body)
        assert set(records) == {'L', 'R'}
        for side, record in records.items():
            assert record['target'] == targets[side]['target'] and record['paired']
            assert record.get('distribution') == 'WRIST_CONTINUOUS' and 'twist_mode' not in record
            assert record['chain'] == verified['records'][side]['chain']
            assert record['rings'] == verified['records'][side]['rings'], f'{side}: captured loops/profile differ from PASS'
            assert record['vertices'] == verified['records'][side]['vertices'], f'{side}: capture support differs from PASS'
        guard.refresh(runtime)
        guard.check_protection(protected, original_keys)
        for name, pose in poses.items():
            guard.assert_pose(bpy.data.objects[name], pose)
        assert bpy.context.scene.frame_current == frame and bpy.context.scene.frame_subframe == subframe
        guard.restore_selection(selection)
        assert guard.selection_state() == selection, 'Current artist selection/mode not restored'
        body.active_shape_key_index = state['active_key_index']
        report.update(records=records, rotation_model='Existing alpha + ratio * beta; no new common-alpha profile',
                      protected_data_unchanged=True, pose_restored=True, selection_restored=True,
                      runtime_errors=dict(runtime._ERRORS), protected_after=guard.protected_state(original_keys))
        report['stage'] = 'save_artist'
        report['artist_save_attempted'] = True
        result = bpy.ops.wm.save_mainfile()
        report['artist_save_result'] = sorted(result)
        report['artist_save_confirmed'] = result == {'FINISHED'}
        assert report['artist_save_confirmed'], 'Blender did not report artist save FINISHED'
        assert Path(bpy.data.filepath).resolve() == ARTIST, 'Saved artist identity changed'
        for name, pose in poses.items():
            guard.assert_pose(bpy.data.objects[name], pose)
        assert guard.selection_state() == selection, 'Post-save artist selection changed'
        guard.check_protection(protected, original_keys)
        assert not runtime._ERRORS and not runtime._SESSION and runtime.PREVIEW_KEY not in body
        report['artist_saved'] = {'path': str(ARTIST), 'bytes': ARTIST.stat().st_size,
                                   'sha256': guard.file_hash(ARTIST), 'dirty_after': bpy.data.is_dirty,
                                   'mtime': datetime.fromtimestamp(ARTIST.stat().st_mtime).astimezone().isoformat()}
        report['status'], report['stage'] = 'PASS', 'complete'
    except BaseException:
        report['tracebacks'].append(traceback.format_exc())
        if report['artist_save_confirmed']:
            # Save has succeeded. Never revert a successfully saved scene just
            # because subsequent receipt/verification failed; report explicitly.
            report['status'] = 'SAVED_REQUIRES_REVIEW'
            report['rollback_skipped_reason'] = 'Artist save already returned FINISHED'
        elif state is not None:
            report['rollback'] = {}
            rollback_failures = []

            def restore_step(label, operation):
                try:
                    operation()
                    report['rollback'][label] = True
                    return True
                except Exception:
                    rollback_failures.append(label)
                    report['tracebacks'].append('ROLLBACK ' + label + '\n' + traceback.format_exc())
                    return False

            try:
                if mutation_started and runtime._SESSION:
                    restore_step('cancel_preview', lambda: runtime.finish_test(bpy.context, confirm=False, refresh=False))
                previous_busy = runtime._BUSY
                runtime._BUSY = True
                try:
                    if mutation_started:
                        keys_restored = restore_step('restore_original_keys', lambda: restore_key_snapshot(body, state['body_keys']))
                        if keys_restored:
                            def restore_owned_state():
                                if state['record_json'] is None:
                                    body.pop(runtime.RECORD_KEY, None)
                                else:
                                    body[runtime.RECORD_KEY] = state['record_json']
                                body.pop(runtime.PREVIEW_KEY, None)
                                body.active_shape_key_index = state['active_key_index']
                                runtime._SESSION = None
                                restore_entry(runtime._CACHE, state['pointer'], state['cache'])
                                restore_entry(runtime._OUTPUT_CACHE, state['pointer'], state['output_cache'])
                                restore_entry(runtime._ERRORS, body.name, state['error'])
                                for identity in tuple(runtime._KEY_REFERENCES):
                                    if identity[0] == state['pointer']:
                                        runtime._KEY_REFERENCES.pop(identity, None)
                                runtime._KEY_REFERENCES.update(state['key_references'])
                                bpy.context.scene.render.use_lock_interface = state['render_lock']
                                restore_entry(bpy.context.scene, runtime.LOCK_KEY, state['render_lock_property'])
                            restore_step('restore_records_and_local_runtime', restore_owned_state)
                        def restore_settings():
                            settings = bpy.context.window_manager.character_designer_forearm_twist
                            previous_ui_busy = runtime._UI_BUSY
                            runtime._UI_BUSY = True
                            try:
                                for name, value in state['settings'].items():
                                    setattr(settings, name, value)
                            finally:
                                runtime._UI_BUSY = previous_ui_busy
                        restore_step('restore_settings', restore_settings)
                    if patch_applied:
                        runtime.__dict__.update(old_functions)
                        report['rollback']['restore_two_functions'] = True
                    if bpy.context.scene.frame_current != state['frame'] or bpy.context.scene.frame_subframe != state['subframe']:
                        restore_step('restore_frame', lambda: bpy.context.scene.frame_set(state['frame'], subframe=state['subframe']))
                    # Key/preview rollback refusal must never prevent restoring
                    # the artist's live pose, selection and mode independently.
                    for name, pose in state['poses'].items():
                        if guard.pose_state(bpy.data.objects[name]) != pose:
                            restore_step('restore_pose_' + name, lambda n=name, p=pose: guard.restore_pose(bpy.data.objects[n], p))
                    if guard.selection_state() != state['selection']:
                        restore_step('restore_selection_mode', lambda: guard.restore_selection(state['selection']))
                    restore_step('update_view_layer', lambda: bpy.context.view_layer.update())
                finally:
                    runtime._BUSY = previous_busy
                for name, pose in state['poses'].items():
                    guard.assert_pose(bpy.data.objects[name], pose)
                guard.check_protection(state['protected'], state['original_keys'])
                assert guard.selection_state() == state['selection']
                report['rollback']['pose_selection_original_keys_records_restored'] = not rollback_failures
                report['rollback']['did_not_resave_artist'] = True
                if rollback_failures:
                    report['rollback']['incomplete_steps'] = rollback_failures
            except Exception:
                report['tracebacks'].append('ROLLBACK\n' + traceback.format_exc())
                report['rollback']['incomplete'] = True
        if guard is not None and ARTIST.exists():
            report['artist_disk_sha256_after_failure'] = guard.file_hash(ARTIST)
            report['disk_unchanged_after_failure'] = report.get('artist_disk_sha256_before') == report['artist_disk_sha256_after_failure']
        if report['artist_save_attempted'] and not report['artist_save_confirmed']:
            report['save_failure_limitation'] = 'Scene was rolled back when possible; a failed save may have changed disk, so consult hashes and the complete safety copy before further writes.'
    finally:
        text = json.dumps(report, ensure_ascii=False, indent=2)
        receipt.write_text(text, encoding='utf-8')
        (HERE / 'apply_artist_result.json').write_text(text, encoding='utf-8')
        print('FOREARM_ARTIST_APPLY', report['status'], report['stage'], str(receipt), flush=True)
    if report['status'] != 'PASS':
        raise RuntimeError('\n'.join(report['tracebacks']))
    return report


if __name__ == '__main__':
    apply()
