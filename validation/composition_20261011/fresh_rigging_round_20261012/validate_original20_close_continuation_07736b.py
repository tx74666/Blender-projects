"""Owned .36 Close continuation from clean D4CB; historical .35 remains failed.

No repeated Gun edit/Save/Undo/Redo and no original-artist integration.
"""
import argparse
import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback
from types import MethodType, SimpleNamespace

ROUND = Path(__file__).resolve().parent
REFERENCE_SOURCE = ROUND / 'validate_original20_recovery_gun_undo_07735.py'
REFERENCE_SOURCE_SHA = '1bde43fa0b108f1b43f832f4ec9f0a3e5cf14c94d9e8dfb9d244528778ea13b8'
REFERENCE_REPORT = ROUND / 'recovery_gun_undo_07735_01/original20_recovery_gun_undo_report.json'
REFERENCE_REPORT_SHA = '17c37654b8587bae2111f8a03092ce476977036b9d5a0d605c692a1e9a396ce9'
REFERENCE_RELEASE = ROUND / 'resource_release_X_RECOVERY_GUN_UNDO_07735_01.json'
REFERENCE_RELEASE_SHA = '377c0048dff9c58c488f5e152aee7b63ba45c23f23e85fd06532d0d5b15eac31'
RECOVERY = ROUND / 'native_original20_r13_12/unverified_native12_quit_recovery.blend'
RECOVERY_SHA = 'd4cb2b7c8fb4667baa11e9f6cd7956076ef010f511069ea9c912a01e3d2dc5a6'
PACKAGE_MANIFEST = ROUND / 'package_c1e59f7f/python_projection.json'
PACKAGE_ROOT = ROUND / 'package_c1e59f7f/source/character_designer'
MANIFEST_SHA = 'e413d8e6d66bb5a0dd676fc24b0152d1599436464981979fd12d38085daca7e4'
RUNTIME_PINS = {'__init__.py': '81b276e22fb170f860a08510db7db2bc26508fb3a711bc8e291b328a59fe71a9',
    'unity_animation_rigging.py': 'b3348175c63cf1d0d29ffb184bd7eb5123c2e4ca274eb5b39893f94658a5019f',
    'animation_composition_weapon.py': '881dc4bfd28e0830628835e3329f77e72f458b0c2ae139033c0ecc618ffa47a1'}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path, expected):
    path = Path(path).resolve()
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    require(digest == expected.lower(), 'File pin changed: ' + str(path))
    return {'path': str(path), 'sha256': digest, 'bytes': len(data)}


def document(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def load(path, expected, name, package=False):
    path = Path(pin(path, expected)['path'])
    spec = importlib.util.spec_from_file_location(name, path,
        submodule_search_locations=[str(path.parent)] if package else None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def same_pin(a, b):
    return Path(a['path']).resolve() == Path(b['path']).resolve() and a['sha256'] == b['sha256'] and a['bytes'] == b['bytes']


def reference_evidence(inputs):
    """Reuse only pinned successful subproofs; never promote the failed Close."""
    inputs['reference35_source'] = pin(REFERENCE_SOURCE, REFERENCE_SOURCE_SHA)
    inputs['reference35_report'] = pin(REFERENCE_REPORT, REFERENCE_REPORT_SHA)
    inputs['reference35_release'] = pin(REFERENCE_RELEASE, REFERENCE_RELEASE_SHA)
    prior, release = document(REFERENCE_REPORT), document(REFERENCE_RELEASE)
    require(prior['schema'] == 'x.validation.original20-recovery-gun-undo/3'
        and prior['completed'] is False and prior['stage'] == 'close_save'
        and 'An external object uses this weapon context' in prior['error']
        and prior['save_reopen_verified'] is False and prior['final_closed_Source_Body_motions_exact'] is False,
        'The .35 reference must remain the actual failed Close, not a completed run.')
    require(same_pin(prior['source_inputs']['source'], inputs['reference35_source'])
        and same_pin(release['source'], inputs['reference35_source'])
        and same_pin(release['report'], inputs['reference35_report'])
        and release['schema'] == 'x.validation.resource-release/1'
        and release['owned_pid'] == prior['pid'] and release['owned_process_filetime'].isdigit()
        and release['completed'] is False and release['passed'] is False
        and release['retained_handle_natural_exit'] is True and release['native_exit_code'] == 0
        and release['owned_native_gone'] is True and release['all_owned_activity_closed'] is True
        and release['process_termination_performed'] is False
        and datetime.fromisoformat(release['native_exited_utc']) > datetime.fromisoformat(release['actual_started_utc']),
        'Historical failed .35 must retain its exact natural END and source/report binding.')
    flags = ('load_cache_reacquired_before_current', 'noop_numeric_roundtrip_reference_verified',
        'marker_Undo_reference_verified', 'Gun_Undo_exact_BF59', 'Gun_Redo_exact_edited_Return',
        'Gun_Redo_qualified_Custom20', 'final_Undo_exact_BF59',
        'edited_payload_retained_exact_through_checkpoint', 'input_files_unchanged')
    require(all(prior.get(key) is True for key in flags)
        and prior['Gun_Redo_whole_fingerprint_exact'] is False
        and prior['Gun_Motion_UI_edit_Key']['completed'] is True
        and prior['Gun_Motion_UI_edit_Key']['public_save_count'] == 1
        and prior['Gun_Motion_UI_edit_Key']['edited_Return_readback_verified'] is True,
        'The exact historical Gun/Undo/qualified Redo subproof is incomplete.')
    for key, row in prior['source_inputs'].items():
        target = 'reference35_package_manifest' if key == 'package_manifest' else key
        if key != 'source':
            inputs[target] = pin(row['path'], row['sha256'])
    require(inputs['recovery']['sha256'] == RECOVERY_SHA and Path(inputs['recovery']['path']) == RECOVERY.resolve()
        and inputs['seed']['sha256'] != RECOVERY_SHA,
        'Open only clean D4CB; preserve the distinct original disk seed binding.')
    for label in ('baseline', 'edited_after_Save', 'after_publication', 'after_display_restore', 'post_checkpoint_before_Undo', 'Redo'):
        row = prior['custom20_payloads'][label]['payload']
        inputs['reference35_payload_' + label] = pin(row['path'], row['sha256'])
    for name, row in prior['Gun_Motion_UI_edit_Key']['edited_publication'].items():
        inputs['reference35_edited_' + name] = pin(row['path'], row['sha256'])
    baseline = REFERENCE_REPORT.parent / 'baseline_Return.json'
    inputs['reference35_baseline_return'] = pin(baseline, '968083205e5344a5eaeac3c6ac82d61a8695f1c4da32d2614f09f71dc6d052e7')
    boundaries = {row['boundary']: row for row in prior['motion_boundaries']}
    reference = boundaries['final_BF_before_Close']
    require(all(boundaries[name]['Source_Body_motions_exact'] is True
        and boundaries[name]['pair_and_weights_exact'] is True
        and boundaries[name]['display_and_VIEW_REFS_exact'] is True
        and boundaries[name]['pair_identity'] == reference['pair_identity']
        and boundaries[name]['validated_motion_pins'] == reference['validated_motion_pins']
        for name in ('fixed_35_prebaseline', 'Gun_edited_saved', 'Gun_Undo', 'Gun_Redo', 'final_Undo', 'final_BF_before_Close'))
        and reference['exact_initial_twenty_and_BF59'] is True,
        'Historical successful boundaries do not share exact Source/Body/pair evidence.')
    return prior, {'completed': False, 'subproofs_verified': list(flags),
        'Gun_Redo_whole_fingerprint_exact': False, 'Gun_Redo_qualified_Custom20': True,
        'historical_failure_preserved': True, 'reference_boundary': reference,
        'Close_save_reopen_publication_reused': False}


def code_scope(inputs, manifest):
    old = document(inputs['reference35_package_manifest']['path'])
    expected = {'__init__.py', 'unity_animation_rigging.py', 'animation_composition_weapon.py'}
    require(set(old['files']) == set(manifest['files']) and len(manifest['files']) == 190,
        'The .36 manifest file domain changed.')
    changed = {name for name in old['files'] if old['files'][name] != manifest['files'][name]}
    require(changed == expected, 'Only init/native/weapon may differ from the actual .35 runtime.')
    result = {'changed_manifest_leaves': sorted(changed), 'other_187_manifest_leaves_exact': True}
    for leaf, changed_names, added_names in (
            ('unity_animation_rigging.py', {'restore_owned'}, set()),
            ('animation_composition_weapon.py', {'remove_context'}, {'validate_removal'})):
        paths = [Path(value['source_root']) / leaf for value in (old, manifest)]
        for path, value in zip(paths, (old, manifest)):
            pin(path, value['files'][leaf])
        trees = [ast.parse(path.read_text(encoding='utf-8-sig')) for path in paths]
        funcs = [{node.name: ast.dump(node, include_attributes=False) for node in tree.body
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))} for tree in trees]
        actual_changed = {name for name in funcs[0].keys() & funcs[1].keys() if funcs[0][name] != funcs[1][name]}
        require(actual_changed == changed_names and funcs[1].keys() - funcs[0].keys() == added_names
            and not funcs[0].keys() - funcs[1].keys(), 'Unreviewed runtime function change: ' + leaf)
        for tree in trees:
            tree.body = [node for node in tree.body if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        require(ast.dump(trees[0], include_attributes=False) == ast.dump(trees[1], include_attributes=False),
            'Runtime module state/import/class change outside reviewed functions: ' + leaf)
        result[leaf] = {'changed_existing_functions': sorted(actual_changed), 'added_functions': sorted(added_names),
            'all_other_function_ASTs_exact': True, 'module_state_imports_classes_AST_exact': True}
    return result


def replay_reference(inputs, prior, legacy, fingerprint):
    """Replay the existing portable evidence, without new Gun or Undo execution."""
    numeric = legacy.referenced_noop(inputs)
    marker = legacy.referenced_marker_and_redo(inputs)
    numeric_scope = legacy.verify_noop_code_scope(inputs, document(inputs['marker_reference_package_manifest']['path']))
    capture_scope = legacy.verify_capture_publish_scope(inputs, document(inputs['reference35_package_manifest']['path']))
    require(numeric == prior['noop_numeric_reference'] and marker == prior['marker_Undo_reference']
        and numeric_scope == prior['noop_reference_code_scope'] and capture_scope == prior['capture_publish_code_scope'],
        'Referenced numeric/marker evidence or precise historical AST scope changed.')
    tests = document(inputs['redo_qualification_test_receipt']['path'])
    require(tests == prior['qualification_pure_tests'] and tests['completed'] is True
        and tests['native_execution_performed'] is False and tests['tests_run'] == 15
        and all(type(tests[key]) is int and tests[key] == 0 for key in ('failures', 'errors', 'exit_code'))
        and same_pin(tests['source'], inputs['redo_qualification_helper'])
        and same_pin(tests['tests'], inputs['redo_qualification_tests'])
        and same_pin(tests['diagnostic_before'], inputs['redo_diagnostic_before'])
        and same_pin(tests['diagnostic_after'], inputs['redo_diagnostic_after']),
        'The exact fifteen portable qualification tests and diagnostic bindings changed.')
    qualifier = load(inputs['redo_qualification_helper']['path'], inputs['redo_qualification_helper']['sha256'], 'close36_linear_qualification')
    labels = ('baseline', 'edited_after_Save', 'after_publication', 'after_display_restore', 'post_checkpoint_before_Undo', 'Redo')
    payloads = {}
    for label in labels:
        payloads[label] = document(inputs['reference35_payload_' + label]['path'])
        qualifier.domain(payloads[label])
        require(fingerprint._stream_digest({'schema': fingerprint.SCHEMA, 'action': payloads[label]})
            == prior['custom20_payloads'][label]['whole_motion_sha256'], 'Historical full20 fingerprint changed: ' + label)
    for label in ('after_publication', 'after_display_restore', 'post_checkpoint_before_Undo'):
        require(not qualifier.full_diff(payloads['edited_after_Save'], payloads[label]), 'Historical pre-Undo data changed: ' + label)
    qualified = qualifier.qualify_redo(payloads['post_checkpoint_before_Undo'], payloads['Redo'],
        document(inputs['redo_diagnostic_before']['path']), document(inputs['redo_diagnostic_after']['path']))
    require(qualified == prior['Redo_qualification'] and qualified['qualified_semantic20_equal'] is True
        and qualified['difference_count'] == 200 and qualified['whole_payload_exact'] is False,
        'The historical Redo must retain exactly its qualified200 differences, never whole-byte equality.')
    masked = [fingerprint._stream_digest({'schema': fingerprint.SCHEMA, 'action': qualifier.masked_payload(payloads[label])})
        for label in ('post_checkpoint_before_Undo', 'Redo')]
    require(masked[0] == masked[1] and prior['Redo_masked_fingerprint']['before'] == masked[0]
        and prior['Redo_masked_fingerprint']['after'] == masked[1] and prior['Redo_masked_fingerprint']['equal'] is True,
        'Historical non-qualified fields changed under the original full fingerprint stream.')
    return {'historical_completed': False, 'six_payloads_replayed': list(labels),
        'qualification_test_count': 15, 'qualified_difference_count': 200, 'whole_fingerprint_exact': False,
        'qualified_Custom20': True, 'numeric_and_marker_references_replayed': True,
        'numeric_and_backend_historical_AST_scope_exact': True}


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--confirm-isolated-headful', required=True, action='store_true')
    parser.add_argument('--quit-on-completion', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    require(len(MANIFEST_SHA) == 64 and all(len(value) == 64 for value in RUNTIME_PINS.values()),
        'PENDING: reviewed frozen .36 package pins are required before execution.')
    output = Path(args.output_root).resolve()
    require(output != ROUND and output.is_relative_to(ROUND) and output.is_dir() and not any(output.iterdir()),
        'Use a new empty owned output directory.')
    inputs = {'source': pin(__file__, args.source_sha256)}
    historical, reference = reference_evidence(inputs)
    inputs['package_manifest'] = pin(PACKAGE_MANIFEST, MANIFEST_SHA)
    manifest = document(PACKAGE_MANIFEST)
    root = Path(manifest['source_root']).resolve()
    require(manifest['schema_version'] == 1 and manifest['module'] == 'character_designer'
        and manifest['version'] == '0.77.36' and root == PACKAGE_ROOT
        and all(manifest['files'].get(name) == value for name, value in RUNTIME_PINS.items()),
        'The exact reviewed .36 frozen projection is required.')
    scope = code_scope(inputs, manifest)
    files = {}
    for relative, expected in manifest['files'].items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root) and '__pycache__' not in path.parts, 'Invalid package leaf.')
        files[relative] = pin(path, expected)
    require({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} == set(files),
        'The frozen package has extra/missing files.')
    legacy = load(REFERENCE_SOURCE, REFERENCE_SOURCE_SHA, 'original20_reference35')
    harness = load(inputs['harness']['path'], inputs['harness']['sha256'], 'original20_r14_close36')
    helper = load(inputs['helper']['path'], inputs['helper']['sha256'], 'original20_protection_close36')
    import bpy
    require(not bpy.app.background and not bpy.data.filepath and tuple(bpy.app.version[:2]) == (5, 2)
        and len(bpy.context.window_manager.windows) == 1, 'Use one fresh isolated headful Blender 5.2 factory child.')
    require(not any(name == 'character_designer' or name.startswith('character_designer.') for name in sys.modules)
        and bpy.context.preferences.edit.use_global_undo and not bpy.context.preferences.filepaths.use_scripts_auto_execute,
        'No mixed runtime or changed Undo/autoexecute preferences are allowed.')
    report = {'schema': 'x.validation.original20-recovery-gun-undo/4', 'completed': False,
        'scope': 'Clean D4CB .36 Close continuation; failed .35 load/Gun Save/Undo/qualified Redo/final BF subproofs referenced, never globally promoted.',
        'source_inputs': inputs, 'pid': os.getpid(), 'native_execution_performed': True,
        'package_manifest_version': manifest['version'], 'package_manifest_file_count': len(files),
        'reference35_subproofs': reference, 'reference35_subproofs_verified': False, 'close_code_scope': scope,
        'Gun_Undo_reference_verified': False, 'Gun_Redo_reference_verified': False, 'final_Undo_reference_verified': False,
        'Gun_Undo_performed_this_run': False, 'Gun_Redo_performed_this_run': False, 'final_Undo_performed_this_run': False,
        'Gun_Save_Undo_Redo_performed_this_run': False, 'Undo_Redo_performed': False,
        'recovery_opened': False, 'seed_opened': False, 'artist_opened': False, 'artist_written': False,
        'original_artist_integration_verified': False, 'full_original_preservation_oracle_run': False,
        'reference_phases_run': False, 'reimport_performed': False, 'private_curve_writes': False,
        'Unity_Apply_verified': False, 'natural_exit_verified': False,
        'natural_exit_external_retained_handle_readback_required': True,
        'load_cache_reacquired_before_current': False, 'persistent_pair_and_exact_BF20_authenticated': False,
        'extra_Scene_reference_Close_rejected_without_mutation': False, 'public_Close_success': False,
        'save_reopen_verified': False, 'strict14_Return_and_twenty_scalar_publication_verified': False,
        'no_QA_offset_remaining': False, 'final_closed_Source_Body_motions_exact': False,
        'existing_ID_colors_modifiers_and_closed_display_verified': False,
        'deferred_public_UI': list(harness.DEFERRED_PUBLIC_UI)}
    report_path = output / 'original20_recovery_gun_undo_report.json'
    state = {'phase': 'reference_proof'}
    write(report_path, report)

    @contextmanager
    def timed(operation):
        row = {'operation': operation, 'started_utc': datetime.now(timezone.utc).isoformat(), 'completed': False}
        report.setdefault('operation_timings', []).append(row)
        write(report_path, report)
        print('ORIGINAL20_OPERATION_BEGIN ' + operation, flush=True)
        started = time.perf_counter()
        try:
            yield
            row['completed'] = True
        finally:
            row['elapsed_seconds'] = time.perf_counter() - started
            row['ended_utc'] = datetime.now(timezone.utc).isoformat()
            write(report_path, report)
            print('ORIGINAL20_OPERATION_END ' + json.dumps(row), flush=True)

    package = load(root / '__init__.py', files['__init__.py']['sha256'], 'character_designer', package=True)
    require(tuple(package.bl_info['version']) == (0, 77, 36), 'Loaded version mismatch.')
    package.register()
    for name in ('animation_worklist', 'animation_worklist_target', 'animation_worklist_fingerprint',
                 'animation_composition_weapon', 'animation_composition', 'unity_animation',
                 'unity_animation_rigging', 'unity_animation_original_inputs'):
        module = __import__('character_designer.' + name, fromlist=[name])
        require(Path(module.__file__).resolve() == root / (name + '.py'), 'Mixed runtime: ' + name)
        setattr(package, name, module)
    backend, native, weapon = package.unity_animation_original_inputs, package.unity_animation_rigging, package.animation_composition_weapon
    probe = SimpleNamespace(bpy=bpy)
    for name in ('id', 'plain', 'rna'):
        setattr(probe, name, MethodType(getattr(helper.OriginalRound, name), probe))
    from mathutils import Color, Euler, Matrix, Quaternion, Vector

    def exact_plain(self, value, depth=0):
        # These native math values implement indexed sequences without exposing
        # __iter__. Preserve every component; delegate all other types unchanged.
        require(depth <= 24, 'Original metadata exceeds its bounded depth.')
        if type(value) in (Color, Euler, Matrix, Quaternion, Vector):
            require(len(value) <= 100000, 'Protected math sequence is too large.')
            return [self.plain(value[index], depth + 1) for index in range(len(value))]
        return helper.OriginalRound.plain(self, value, depth)

    probe.plain = MethodType(exact_plain, probe)

    def pair_identity(pair):
        return {'rig': probe.id(pair['rig']), 'scene': probe.id(pair['scene']),
            'actions': {side: probe.id(pair[side + '_action']) for side in ('source', 'custom')},
            'slots': {side: pair[side + '_slot'] for side in ('source', 'custom')},
            'source_uuid': pair['source_uuid'], 'custom_uuid': pair['capture']['newActionId'],
            'bindings': probe.plain(pair['capture']['bindings'])}

    def motion_pins(pair):
        # Read only after this boundary's complete public admission or _pair_validate.
        return {'Source20': pair['source_owner']['source_input_motion'],
            'original_Custom_Body': pair['body_motion'], 'original_Source_Body': pair['body_source_motion']}

    def pair_boundary(pair, label, *, dto=None, admission_path):
        require(pair_identity(pair) == state['pair_identity'] and motion_pins(pair) == state['motions'],
            'Protected pair/Source20/Body motion changed at ' + label)
        harness.exact_initial_twenty(package, pair)
        require(native._motion(pair['custom_action'], pair['custom_slot']) == state['baseline_motion'],
            'Custom20 complete motion is not exact BF59 at ' + label)
        if dto is not None:
            require(set(dto) == legacy.RETURN_FIELDS and len(dto['frames']) == 59 and dto == state['baseline'],
                'Strict14/BF59 changed at ' + label)
        report.setdefault('motion_boundaries', []).append({'boundary': label, 'validated_motion_pins': motion_pins(pair),
            'pair_identity': pair_identity(pair), 'Source_Body_motions_exact': True, 'pair_and_weights_exact': True,
            'exact_initial_twenty_and_BF59': True, 'Return_BF59_measured_this_boundary': dto is not None,
            'actual_admission_path': admission_path})

    def display(ctx, rig):
        return probe.plain(package.bone_display._checkpoint(package.bone_display._affected(ctx, rig)))

    def metadata(rig, names):
        objects = [bpy.data.objects.get(name) for name in names]
        require(all(obj is not None for obj in objects), 'An existing Object disappeared.')
        return {'rig': probe.id(rig), 'data': probe.id(rig.data),
            'objects': {obj.name: {'id': probe.id(obj), 'data': probe.id(obj.data) if obj.data else None,
                'parent': probe.id(obj.parent), 'parent_type': obj.parent_type, 'parent_bone': obj.parent_bone,
                'collections': sorted(c.name for c in obj.users_collection),
                'modifiers': [probe.rna(modifier) for modifier in obj.modifiers]} for obj in objects},
            'bone_colors': {bone.name: probe.rna(bone.color) for bone in rig.data.bones},
            'pose_colors': {bone.name: probe.rna(bone.color) for bone in rig.pose.bones}}

    def lifecycle(ctx, rig):
        require(native._REACQUIRE_TIMER is None and not native._REACQUIRE_PENDING, 'Deferred admission has not settled.')
        cached = native.display_state(rig)
        require(cached is not None and cached['rig'] == rig and cached['scene'] == ctx.scene
            and cached['enabled'] and cached['original_controls_only'] and not native._HANDLER_ERRORS,
            'Fresh load did not restore the authenticated cache before current.')
        callbacks = {name: sum(value is callback for value in getattr(bpy.app.handlers, name)) for name, callback in (
            ('load_post', native._reacquire), ('undo_post', native._reacquire), ('redo_post', native._reacquire),
            ('frame_change_post', native._frame), ('depsgraph_update_post', native._depsgraph))}
        require(all(value == 1 for value in callbacks.values()), 'Missing/duplicate lifecycle callback.')
        report['lifecycle_witnesses'] = [{'boundary': 'load_post_before_current', 'callbacks': callbacks,
            'cache_checked_before_current_or_manual_activate': True, 'pending_empty': True, 'handler_errors_empty': True}]

    def rejection_snapshot(ctx, rig):
        # No dense fingerprint repetition: exact RNA/state snapshot around only the rejected operator.
        return {'prior': probe.plain(package.animation_composition._prior(ctx, rig)),
            'display': display(ctx, rig), 'rig_properties': probe.plain(dict(rig.items())),
            'tweak': rig.animation_data.use_tweak_mode,
            'nla': probe.rna(rig.animation_data, exclude=('drivers',)),
            'object_ids': sorted((o.name, o.as_pointer()) for o in bpy.data.objects),
            'collection_ids': sorted((c.name, c.as_pointer()) for c in bpy.data.collections),
            'weapon_asset_ids': {key: sorted((value.name, value.as_pointer()) for value in rows.values())
                for key, rows in rig[weapon.RECORD].get('assets', {}).items()},
            'action_ids': sorted((action.name, action.as_pointer()) for action in bpy.data.actions),
            'handler_errors': dict(native._HANDLER_ERRORS),
            'cache_owner': native._CACHE[rig.as_pointer()]['owner'],
            'session_refs': {key: value.as_pointer() for key, value in rig[native._REFS_KEY].items()}}

    def validate_reference():
        with timed('replay pinned historical subproofs and six Custom20 payloads'):
            report['reference35_payload_replay'] = replay_reference(inputs, historical, legacy, package.animation_worklist_fingerprint)
        report.update(reference35_subproofs_verified=True, Gun_Undo_reference_verified=True,
            Gun_Redo_reference_verified=True, final_Undo_reference_verified=True)
        return 'open_recovery'

    def open_recovery():
        with timed('open clean D4CB recovery'):
            result = bpy.ops.wm.open_mainfile('EXEC_DEFAULT', False, filepath=str(RECOVERY), use_scripts=False, load_ui=False)
        require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == RECOVERY.resolve(), 'Clean recovery failed to open.')
        report['recovery_opened'] = True
        return 'admit'

    def authenticate():
        with harness.owning_context(bpy) as (ctx, rig):
            lifecycle(ctx, rig)
            report['load_cache_reacquired_before_current'] = True
            with timed('fresh current and complete public BF59 capture'):
                session = backend.current(rig)
                require(session is not None and 'original_inputs' in session, 'No persistent Original20 session.')
                pair = session['original_inputs']
                baseline = backend.capture_inputs(ctx, session)
            for key, input_key in (('prepared_report', 'prepared_report'), ('clock_certificate', 'clock_report'), ('snapshot_receipt', 'snapshot_receipt')):
                require(same_pin(pair[key], inputs[input_key]), 'Persistent evidence changed: ' + key)
            require(pair['packet']['sha256'] == legacy.PACKET_SHA and session['enabled'] and session['tweak_enabled']
                and session['edit_role'] == 'RIGGING' and rig.mode == 'POSE' and rig.animation_data.use_tweak_mode
                and native._time(ctx, session) == 0., 'Recovery lost its authenticated first-key context.')
            state.update(pair_identity=pair_identity(pair), motions=motion_pins(pair), baseline=baseline,
                baseline_motion=native._motion(pair['custom_action'], pair['custom_slot']))
            require(state['pair_identity'] == reference['reference_boundary']['pair_identity']
                and state['motions'] == reference['reference_boundary']['validated_motion_pins']
                and baseline == document(inputs['reference35_baseline_return']['path'])
                and state['baseline_motion'] == historical['custom20_payloads']['baseline']['whole_motion_sha256'],
                'Fresh D4CB does not match the exact historical BF59/pair/Source/Body measurement.')
            report['Action_inventory'] = legacy.inventory(bpy, helper, pair, document(inputs['snapshot_receipt']['path']))
            record, owned = weapon.validate_owned(rig)
            state['original_object_names'] = sorted(o.name for o in bpy.data.objects if o not in set(owned))
            state['metadata'] = metadata(rig, state['original_object_names'])
            state['original_object_pointers'] = {name: bpy.data.objects[name].as_pointer() for name in state['original_object_names']}
            state['entry_display'] = probe.plain(session['display'])
            state['entry_context'] = {key: probe.plain(session['prior'][key]) for key in ('rig_mode', 'active', 'selected', 'active_bone', 'selected_bones')}
            pair_boundary(pair, 'clean_D4CB_BF59', dto=baseline, admission_path='fresh public current + complete public capture_inputs')
            report['persistent_pair_and_exact_BF20_authenticated'] = True
            write(output / 'baseline_Return.json', baseline)
        return 'negative_close'

    def negative_close():
        with harness.owning_context(bpy) as (ctx, rig):
            record, owned = weapon.validate_owned(rig)
            key = 'codex_close_probe_' + str(os.getpid())
            require(key not in ctx.scene and not native._HANDLER_ERRORS, 'Negative probe key/error state is not clean.')
            obj = owned[0]
            before_count = ctx.scene.user_of_id(obj)
            ctx.scene[key] = obj
            try:
                require(ctx.scene.user_of_id(obj) == before_count + 1, 'Probe did not create exactly one Scene ID reference.')
                before = rejection_snapshot(ctx, rig)
                error = None
                with timed('public Close negative extra Scene reference'):
                    try:
                        result = bpy.ops.character_designer.original_inputs_close('EXEC_DEFAULT', False)
                    except RuntimeError as exc:
                        error = str(exc)
                require(error is not None and 'The owning Scene has an extra weapon reference' in error,
                    'Public Close did not reject the exact extra Scene reference.')
                after = rejection_snapshot(ctx, rig)
                require(after == before and not native._HANDLER_ERRORS,
                    'Rejected Close mutated Tweak/tracks/session/refs/pose/display/owned IDs or polluted handlers.')
                report['negative_Close'] = {'error': error, 'reference_count_before': before_count,
                    'reference_count_injected': before_count + 1, 'state_before_sha256': helper.digest(before),
                    'state_after_sha256': helper.digest(after), 'actual_public_operator': True,
                    'Tweak_tracks_session_refs_pose_display_owned_IDs_exact': True, 'handler_errors_empty': True}
                report['extra_Scene_reference_Close_rejected_without_mutation'] = True
            finally:
                require(ctx.scene.get(key) == obj, 'The unique probe reference changed ownership.')
                del ctx.scene[key]
            require(ctx.scene.user_of_id(obj) == before_count and key not in ctx.scene, 'Probe reference did not restore exactly.')
            report['negative_Close']['probe_reference_removed_exactly'] = True
        return 'close_save'

    def check_closed(ctx, rig, label):
        require(backend.current(rig) is None and native.SESSION_KEY not in rig and native._REFS_KEY not in rig
            and weapon.RECORD not in rig and not rig.animation_data.use_tweak_mode and not native._HANDLER_ERRORS,
            'Close did not remove only the owned session/display and leave a clean closed pair.')
        with timed(label + ' complete pair/file validation'):
            pair = backend._pair_validate(backend._pair(rig), files=True)
        pair_boundary(pair, label, admission_path='closed complete _pair_validate(files=True)')
        require(metadata(rig, state['original_object_names']) == state['metadata'], 'Close/reopen changed existing IDs/colors/modifiers.')
        require(probe.plain(package.bone_display._snapshot(rig)) == state['entry_display'], 'Close did not restore entry display.')
        prior = package.animation_composition._prior(ctx, rig)
        require({key: probe.plain(prior[key]) for key in state['entry_context']} == state['entry_context'],
            'Close did not restore entry mode/active/selection context.')
        return pair

    def close_save():
        with harness.owning_context(bpy) as (ctx, rig):
            with timed('public Close after exact reference cleanup'):
                result = bpy.ops.character_designer.original_inputs_close('EXEC_DEFAULT', False)
            require(result == {'FINISHED'}, 'Public Close failed.')
            legacy.record_public(report, 'character_designer.original_inputs_close')
            check_closed(ctx, rig, 'closed_BF59')
            require({name: bpy.data.objects[name].as_pointer() for name in state['original_object_names']} == state['original_object_pointers'],
                'Close replaced an existing Object identity.')
            report['public_Close_success'] = True
        clone = output / 'original20_controls_owned.blend'
        require(not clone.exists(), 'Never overwrite a previous clone.')
        with timed('closed BF59 SaveCopy'):
            result = bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', False, filepath=str(clone), copy=True, check_existing=False)
        require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == RECOVERY.resolve(), 'SaveCopy did not finish on the owned scene.')
        report['saved_clone'] = pin(clone, hashlib.sha256(clone.read_bytes()).hexdigest())
        return 'reopen'

    def reopen():
        clone = report['saved_clone']
        pin(clone['path'], clone['sha256'])
        with timed('reopen actual closed BF59 clone'):
            result = bpy.ops.wm.open_mainfile('EXEC_DEFAULT', False, filepath=clone['path'], use_scripts=False, load_ui=False)
        require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == Path(clone['path']), 'Saved clone did not reopen.')
        return 'reopened_readback'

    def reopened_readback():
        with harness.owning_context(bpy) as (ctx, rig):
            pair = check_closed(ctx, rig, 'reopened_closed_BF59')
            report['reopened_Action_inventory'] = legacy.inventory(bpy, helper, pair, document(inputs['snapshot_receipt']['path']))
            with timed('reopened existing-pair public Edit'):
                result = bpy.ops.character_designer.original_inputs_edit('EXEC_DEFAULT', False)
            require(result == {'FINISHED'}, 'Reopened public Edit failed.')
            legacy.record_public(report, 'character_designer.original_inputs_edit')
            session = native._CACHE.get(rig.as_pointer())
            require(session is not None and session['rig'] == rig and session['scene'] == ctx.scene, 'Edit did not publish its actual session.')
            identity = legacy.publication_identity(rig, session, native)
            with timed('publish actual reopened BF59 Return'):
                published = backend.publish_inputs(ctx, rig, str(output / 'captured_controls_Return.json'))
            require(legacy.publication_identity(rig, session, native) == identity, 'Publisher changed same-callback ownership.')
            require(set(published) == {'return', 'publication'}, 'Publisher did not return two pins.')
            for row in published.values(): pin(row['path'], row['sha256'])
            dto, publication = document(published['return']['path']), document(published['publication']['path'])
            pair = session['original_inputs']
            require(publication['schema'] == backend.PUBLICATION_SCHEMA and publication['completed'] is True
                and publication['controlChannelCount'] == 20 and publication['returnSha256'] == published['return']['sha256']
                and publication['sourceActionId'] == pair['source_uuid'] and publication['targetInputActionId'] == pair['capture']['newActionId']
                and all(publication[key] == dto[key] for key in legacy.RETURN_FIELDS - {'schema', 'frames'})
                and all(publication[key] is True for key in ('sourceReadOnly', 'targetEditable', 'sourceControlsOnly', 'targetControlsOnly')),
                'Reopened publication is not the strict controls-only identity.')
            pair_boundary(pair, 'reopened_BF59', dto=dto, admission_path='actual public Edit + public publish_inputs Return readback')
            report['actual_controls_only_publication'] = published
            report['save_reopen_verified'] = True
            report['strict14_Return_and_twenty_scalar_publication_verified'] = True
            with timed('final public Close'):
                result = bpy.ops.character_designer.original_inputs_close('EXEC_DEFAULT', False)
            require(result == {'FINISHED'}, 'Final public Close failed.')
            check_closed(ctx, rig, 'final_closed_BF59')
            report['final_closed_Source_Body_motions_exact'] = True
            report['no_QA_offset_remaining'] = True
            report['existing_ID_colors_modifiers_and_closed_display_verified'] = True
        return 'finish'

    def finish(error=None):
        if error is not None:
            report.update(completed=False, error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
            report['failure_lifecycle_raw'] = {'HANDLER_ERRORS': dict(native._HANDLER_ERRORS),
                'pending_rig_pointers': sorted(native._REACQUIRE_PENDING), 'current_or_capture_called': False}
            write(report_path, report)
            try:
                allowed = {RECOVERY.resolve()}
                if 'saved_clone' in report: allowed.add(Path(report['saved_clone']['path']).resolve())
                require(bpy.data.filepath and Path(bpy.data.filepath).resolve() in allowed, 'Retain only an authenticated owned scene.')
                failure = output / 'failed_original20_close_continuation.blend'
                require(not failure.exists(), 'Never overwrite failure evidence.')
                active = Path(bpy.data.filepath).resolve()
                with timed('failure diagnostic SaveCopy'):
                    result = bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', False, filepath=str(failure), copy=True, check_existing=False)
                require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == active, 'Failure SaveCopy failed.')
                report['failure_scene'] = pin(failure, hashlib.sha256(failure.read_bytes()).hexdigest())
            except Exception as exc:
                report['failure_scene_error'] = type(exc).__name__ + ': ' + str(exc)
        try:
            with timed('final immutable input pins'):
                for row in list(inputs.values()) + list(files.values()): pin(row['path'], row['sha256'])
                if 'saved_clone' in report: pin(report['saved_clone']['path'], report['saved_clone']['sha256'])
            report['input_files_unchanged'] = True
        except Exception as exc:
            report['immutable_input_error'] = type(exc).__name__ + ': ' + str(exc)
            error = exc
        required = ('reference35_subproofs_verified', 'load_cache_reacquired_before_current',
            'persistent_pair_and_exact_BF20_authenticated', 'extra_Scene_reference_Close_rejected_without_mutation',
            'Gun_Undo_reference_verified', 'Gun_Redo_reference_verified', 'final_Undo_reference_verified',
            'public_Close_success', 'save_reopen_verified', 'strict14_Return_and_twenty_scalar_publication_verified',
            'final_closed_Source_Body_motions_exact', 'no_QA_offset_remaining',
            'existing_ID_colors_modifiers_and_closed_display_verified', 'input_files_unchanged')
        report['completed'] = error is None and all(report.get(key) is True for key in required)
        write(report_path, report)
        print('ORIGINAL20_CLOSE_CONTINUATION ' + json.dumps({'completed': report['completed'], 'report': str(report_path)}), flush=True)
        if args.quit_on_completion:
            def quit_owned():
                observation = {'pid': os.getpid(), 'requested_from_timer': True,
                    'completed_report': report['completed'], 'natural_exit_still_external': True}
                try:
                    observation['operator_result'] = sorted(bpy.ops.wm.quit_blender('EXEC_DEFAULT', False))
                except Exception as exc:
                    observation['error'] = type(exc).__name__ + ': ' + str(exc)
                write(output / 'owned_quit_observation.json', observation)
                return None
            bpy.app.timers.register(quit_owned, first_interval=3., persistent=False)
        return None

    def tick():
        phase = state['phase']
        report['stage'] = phase
        write(report_path, report)
        print('ORIGINAL20_RECOVERY_STAGE ' + phase, flush=True)
        try:
            if phase == 'admit':
                rig = bpy.data.objects.get('CoshaRig')
                timer = native._REACQUIRE_TIMER
                pending = rig is not None and rig.as_pointer() in native._REACQUIRE_PENDING
                if pending and timer is not None and bpy.app.timers.is_registered(timer):
                    first = state.setdefault('lifecycle_pending_started', time.monotonic())
                    require(time.monotonic() - first <= 120., 'Owned one-shot lifecycle callback remained pending over 120 seconds.')
                    return .1
            if phase == 'finish': return finish()
            functions = {'reference_proof': validate_reference, 'open_recovery': open_recovery, 'admit': authenticate, 'negative_close': negative_close,
                'close_save': close_save, 'reopen': reopen, 'reopened_readback': reopened_readback}
            require(phase in functions, 'Unknown owned continuation phase.')
            state['phase'] = functions[phase]()
            write(report_path, report)
            return .1
        except Exception as exc:
            return finish(exc)

    bpy.app.timers.register(tick, first_interval=.1, persistent=True)


if __name__ == '__main__':
    main()
