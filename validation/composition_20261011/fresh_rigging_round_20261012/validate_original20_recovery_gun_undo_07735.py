"""Focused .35 recovery: exact BF59 and narrowly qualified native LINEAR Redo.

No reimport, Body reference phases, full asset oracle or original-artist integration.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback
from types import MethodType, SimpleNamespace
from contextlib import contextmanager

ROUND = Path(__file__).resolve().parent
RECOVERY = ROUND / 'native_original20_r13_12/unverified_native12_quit_recovery.blend'
RECOVERY_SHA = 'd4cb2b7c8fb4667baa11e9f6cd7956076ef010f511069ea9c912a01e3d2dc5a6'
REPORT_SHA = '01b1d9fa2e428e03710a304bac7c8e7174c727edf650d3228b2c08fd09c7ea5b'
RELEASE_SHA = '239d846cade89959e0ecd73979c39e968d62acb86161cc4b990d9f4a10a7e6e2'
OLD_SOURCE_SHA = '82522f42851abbb1e3434cbaf4a9a26fd07aaaf327b1bee58400355c5fca7172'
HELPER_SHA = '7098c3b20a5a115423913ce91268cc4fd9a57adab9973c9c6c2000e2afd2d468'
PACKET_SHA = 'bffbbf00c3bcdfccc1a8bc1995aadeb188afb9f1d643bc78f1a34c8bb5cf7c4f'
PREPARED_SHA = '401b00d209b7806fa3c44c06fdf7e643256c64009d2abda45495a8b1cc0d4ac6'
CLOCK_SHA = 'cc0c749f29419747ec54195c63bd5d35249e97c2da0e62f5657880db77fc4e1d'
SNAPSHOT_SHA = '5387b972a123b81ab3b77df398fd1cfd3e33165a8934095bf3ff1953663c81ef'
ARTIST_SHA = 'cc9a624dfc3e8a939ee62d0f4b14ccef3456ad9152c9091661968a9a0593c756'


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


def inventory(bpy, helper, pair, snapshot):
    probe = SimpleNamespace(bpy=bpy)
    for name in ('id', 'snapshot_identity'):
        setattr(probe, name, MethodType(getattr(helper.OriginalRound, name), probe))
    old = {helper.digest(probe.snapshot_identity(row['identity'])): row
           for row in snapshot['before']['actions']}
    owned = [probe.id(pair[key + '_action']) for key in ('source', 'custom')]
    owned_keys = {helper.digest(row) for row in owned}
    actual = {helper.digest(probe.id(action)): action for action in bpy.data.actions}
    require(len(old) == 10 and len(owned_keys) == 2 and not set(old) & owned_keys
            and len(actual) == 12 and set(actual) == set(old) | owned_keys,
            'Recovery must retain the original ten Actions and exactly the two authenticated input carriers.')
    for key, row in old.items():
        action = actual[key]
        slots = [{'handle': s.handle, 'target_id_type': s.target_id_type,
                  'identifier': s.identifier, 'name_display': s.name_display}
                 for s in action.slots] if action.is_action_layered else []
        require(slots == row['slots'], 'An original Action slot identity changed: ' + action.name)
    return {'original_count': len(old), 'original_identities_and_slots_exact': True,
            'original_actions': [probe.snapshot_identity(row['identity']) for row in old.values()],
            'owned_actions': owned, 'owned_slots': [pair['source_slot'], pair['custom_slot']],
            'source_uuid': pair['source_uuid'], 'custom_uuid': pair['capture']['newActionId'],
            'all_original_action_motion_or_geometry_preservation_claimed': False}


R14_SHA = '621f4872cd1a4ee29a1c8182a802e6beec5f7065afaaa21cfe0be624a0da258c'
MANIFEST_SHA = '004281ac5eed3ba7740eca5398b4b41dde94bb9e12685d28d77db00b6f735713'
PACKAGE_MANIFEST = ROUND / 'package_cd043f92/python_projection.json'
PACKAGE_ROOT = ROUND / 'package_cd043f92/source/character_designer'
QUALIFICATION_SHA = 'd1a25ad902d579205e88a11c7bdb1e4c55ea2746c47fd2fad69856ff9c7aadc3'
QUALIFICATION_TEST_SHA = '03047fa0ddf500fa594f29ed9be474ec7b2336b519e540c1d44325e372b4b2a3'
QUALIFICATION_RECEIPT_SHA = 'efd42410a2cb661e9fea461e4ac3c9a0e6b5f47e93237ab96a353a6c4ce09954'
NOOP_REPORT_SHA = '27a97f201811d3742e3677444a4d68b664294bc71506555b03da94e7138c49cf'
NOOP_SOURCE_SHA = '6d89a1cb652a6aa564a66ab25c73312439dc887f25f44c0326a050305be50d1a'
NOOP_RELEASE_SHA = '5418b13506dc506f98ebe633a129350820538f686d2e5cfa4447ff2808ac3d9a'
LIFECYCLE_CHANGED_FUNCTIONS = ('display_state', '_reacquire', 'register', 'unregister')
LIFECYCLE_ADDED_FUNCTIONS = ('_cancel_reacquire', '_deferred_reacquire')
LIFECYCLE_ADDED_MODULE_NAMES = ('_REACQUIRE_PENDING', '_REACQUIRE_TIMER', '_REACQUIRE_GENERATION')
RUNTIME_PINS = {
    '__init__.py': 'c9b05b3fc01a8686c0a48b0cb487e245adf76f21b53df6b5a2a53f56ca9319fa',
    'unity_animation_original_inputs.py': 'f2f6e1693c7fab0cb8ffaa479a3af19f5c4392f66119844183c32a61f91b1473',
    'unity_animation_rigging.py': '77397546086392365428bcb3d87a48139aa2f36fb540e4479ec21d86109d4faf',
    'animation_original_inputs_ui.py': '38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426',
    'animation_worklist_ui.py': '24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067',
    'forearm_twist.py': '54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408',
}
RETURN_FIELDS = {'schema', 'sourcePacketSha256', 'bindingsSha256', 'targetGuid', 'workItemId',
    'newActionId', 'sourceAction', 'sourceActionSlot', 'targetInputAction', 'targetInputActionSlot',
    'duration', 'sampleRate', 'loopTime', 'frames'}


def referenced_noop(inputs):
    """Admit only the measured numeric portion of the failed .33 run."""
    inputs['noop_reference_report'] = pin(ROUND / 'recovery_gun_undo_07733_01/original20_recovery_gun_undo_report.json', NOOP_REPORT_SHA)
    inputs['noop_reference_source'] = pin(ROUND / 'validate_original20_recovery_gun_undo_07733.py', NOOP_SOURCE_SHA)
    inputs['noop_reference_release'] = pin(ROUND / 'resource_release_X_RECOVERY_GUN_UNDO_07733_01.json', NOOP_RELEASE_SHA)
    inputs['noop_reference_package_manifest'] = pin(ROUND / 'package_0fa9adfa/python_projection.json',
        '5b195a86a5b6d3834c7c76f02c0f83e42835e0cf7ca268556ec1e4ebf36f6640')
    prior, release = document(inputs['noop_reference_report']['path']), document(inputs['noop_reference_release']['path'])
    require(prior['schema'] == 'x.validation.original20-recovery-gun-undo/1' and prior['completed'] is False
        and prior['noop_numeric_roundtrip_verified'] is False and prior['noop_Undo_restored_exact_BF59'] is False
        and prior['native_execution_performed'] is True and prior['input_files_unchanged'] is True
        and prior['source_inputs']['source'] == inputs['noop_reference_source']
        and prior['source_inputs']['package_manifest'] == inputs['noop_reference_package_manifest']
        and prior['package_manifest_version'] == '0.77.33' and prior['package_manifest_file_count'] == 190
        and prior['stage'] == 'noop_readback' and 'Undo/Redo did not reacquire' in prior['error'],
        'Keep the failed .33 report failed; only its preceding numeric no-op measurement may be referenced.')
    require(all(prior['source_inputs'][key] == inputs[key] for key in ('harness', 'recovery', 'seed', 'protected_artist',
        'snapshot_receipt', 'prepared_report', 'clock_report', 'native12_report', 'native12_source', 'native12_release')),
        'The historical numeric measurement belongs to another recovery or source context.')
    require(release['schema'] == 'x.validation.resource-release/1' and release['passed'] is False
        and release['report'] == inputs['noop_reference_report'] and release['source'] == inputs['noop_reference_source']
        and release['owned_pid'] == prior['pid'] and release['retained_handle_natural_exit'] is True
        and type(release['native_exit_code']) is int and release['native_exit_code'] == 0
        and release['owned_native_gone'] is True and release['process_termination_performed'] is False,
        'The historical failed run needs its actual retained-handle natural release.')
    numeric = prior['noop_save']
    require(numeric['numeric_roundtrip_gate'] is True and numeric['no_Target_or_Hint_edit_performed'] is True
        and numeric['native_time'] == 0. and numeric['frames_1_through_58_exact'] is True
        and numeric['restored_BF59_gate_remains_exact'] is True
        and numeric['gate_limits'] == {'position_max_component': 1e-5, 'hint_max_component': 1e-5, 'rotation_degrees': .001}
        and len(numeric['control_deltas']) == 2 and all(0 <= row['position_max_component'] <= 1e-5
            and 0 <= row['hint_max_component'] <= 1e-5 and 0 <= row['rotation_degrees'] <= .001
            for row in numeric['control_deltas']), 'The actual .33 numeric no-op gate is absent or outside its original limits.')
    boundaries = {row['boundary']: row for row in prior['motion_boundaries']}
    before, after = boundaries['fixed_33_prebaseline'], boundaries['no_op_saved']
    require(before['exact_initial_twenty_and_BF59'] is True and all(row['Source_Body_motions_exact'] is True
        and row['pair_and_weights_exact'] is True and row['display_and_VIEW_REFS_exact'] is True
        and row['native_time'] == 0. for row in (before, after))
        and before['source_body_motions'] == after['source_body_motions'] and before['pair_identity'] == after['pair_identity'],
        'The referenced numeric Save lacks its unchanged Source/Body/pair boundary evidence.')
    return {'source_version': '0.77.33', 'historical_report_completed': False,
        'historical_top_level_noop_numeric_verified': False, 'historical_noop_Undo_restored_exact_BF59': False,
        'numeric_gate_measured_true': True, 'measured_this_run': False, 'numeric_observation': numeric,
        'source_body_motions': after['source_body_motions'], 'pair_identity': after['pair_identity'],
        'report': inputs['noop_reference_report'], 'source': inputs['noop_reference_source'],
        'release': inputs['noop_reference_release']}


def verify_noop_code_scope(inputs, manifest):
    """Prove the referenced numeric decoder is unchanged; lifecycle exceptions are explicit."""
    prior = document(inputs['noop_reference_package_manifest']['path'])
    require(set(prior['files']) == set(manifest['files']) and len(manifest['files']) == 190,
            'The numeric reference and candidate must have the same complete leaf domain.')
    changed_leaves = {name for name in prior['files'] if prior['files'][name] != manifest['files'][name]}
    require(changed_leaves == {'__init__.py', 'unity_animation_rigging.py'},
            'Only version registration and the reviewed native lifecycle may differ; the other 188 leaves must match.')
    require(all(isinstance(value, (tuple, list)) for value in (LIFECYCLE_CHANGED_FUNCTIONS,
            LIFECYCLE_ADDED_FUNCTIONS, LIFECYCLE_ADDED_MODULE_NAMES)), 'Bind the exact reviewed lifecycle source scope first.')
    leaf = 'unity_animation_rigging.py'
    inputs['noop_reference_native'] = pin(Path(prior['source_root']) / leaf, prior['files'][leaf])
    old_tree = ast.parse(Path(inputs['noop_reference_native']['path']).read_text(encoding='utf-8'))
    new_tree = ast.parse((Path(manifest['source_root']) / leaf).read_text(encoding='utf-8'))
    functions = lambda tree: {node.name: ast.dump(node, include_attributes=False) for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    old, new = functions(old_tree), functions(new_tree)
    changed = {name for name in old.keys() & new.keys() if old[name] != new[name]}
    added, removed = new.keys() - old.keys(), old.keys() - new.keys()
    require(not removed and changed == set(LIFECYCLE_CHANGED_FUNCTIONS) and added == set(LIFECYCLE_ADDED_FUNCTIONS),
            'An unknown native function changed; historical numeric evidence cannot be reused.')
    critical = ('_apply', '_write_target', '_read_target', 'key_current', 'capture_inputs')
    require(all(old[name] == new[name] for name in critical), 'A measured numeric apply/read/Save/capture function changed.')
    def module_nodes(tree, added_names=()):
        result, seen = [], set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): continue
            names = {target.id for target in node.targets if isinstance(target, ast.Name)} if isinstance(node, ast.Assign) else set()
            if names and names <= set(added_names):
                seen.update(names); continue
            result.append(ast.dump(node, include_attributes=False))
        return result, seen
    original_nodes, _ = module_nodes(old_tree)
    candidate_nodes, additions = module_nodes(new_tree, LIFECYCLE_ADDED_MODULE_NAMES)
    require(original_nodes == candidate_nodes and additions == set(LIFECYCLE_ADDED_MODULE_NAMES),
            'Native module data/imports changed outside the explicitly added lifecycle state.')
    return {'other_188_manifest_leaves_exact': True, 'changed_manifest_leaves': sorted(changed_leaves),
        'changed_existing_native_functions': sorted(changed), 'added_native_functions': sorted(added),
        'removed_native_functions': [], 'added_module_state': sorted(additions),
        'all_other_existing_function_ASTs_exact': True, 'numeric_functions_AST_exact': list(critical),
        'reference_native': inputs['noop_reference_native'], 'candidate_native_sha256': manifest['files'][leaf]}


def referenced_marker_and_redo(inputs):
    bindings = {
        'marker_reference_report': ('recovery_gun_undo_07734_03/original20_recovery_gun_undo_report.json', '64faf182b88775599a6cfa0848301b7b41a3b6434d301f833d68a7c30b7dfa88'),
        'marker_reference_source': ('validate_original20_recovery_gun_undo_07734c.py', '7ecfe2d41960c0b565c835cb7c0b6e634650cd74aadd4c8b068a96cd78a21806'),
        'marker_reference_release': ('resource_release_X_RECOVERY_GUN_UNDO_07734_03.json', 'b73f9e979a2f21a2112fd8be31bd25833b8e95ca1f4d2da185339a4af4b4e982'),
        'marker_reference_package_manifest': ('package_3fd79576/python_projection.json', 'bb08d3abb146836db522dcbf322ad32bff52a66dbe967f5dd62457f81b234358'),
        'redo_diagnostic_report': ('action_undo_diagnostic_07734_01/action_undo_diagnostic_report.json', 'fe2d6ce83934f804c83790b6b7439266370bb644c216b8b9ac953378f5fd946d'),
        'redo_diagnostic_source': ('inspect_original20_action_undo_07734b.py', '04fd8e062f0d08a15b8f8f5717917b29f896e069bdec4d31a0f46f86956b1993'),
        'redo_diagnostic_release': ('resource_release_X_ACTION_UNDO_DIAGNOSTIC_07734_01.json', '32a39589e80b1ddf0b69de7a2e5d777f66e013b1ae99c13ffba290e6f14fcba5'),
        'redo_diagnostic_before': ('action_undo_diagnostic_07734_01/before_curve_undo_full20_payload.json', '9036b0dc5405c9626afea4428e95e2b3c5f6fcfc876cbf74ec9b41212edd8a13'),
        'redo_diagnostic_after': ('action_undo_diagnostic_07734_01/after_curve_redo_full20_payload.json', 'e2a531dc6b6210663e8b493e1cf0ade010f10c179d673d5f0632fca43d4f4e44'),
    }
    for key, (relative, digest) in bindings.items(): inputs[key] = pin(ROUND / relative, digest)
    prior = document(inputs['marker_reference_report']['path'])
    release = document(inputs['marker_reference_release']['path'])
    same = lambda a, b: Path(a['path']).resolve() == Path(b['path']).resolve() and a['sha256'] == b['sha256'] and a['bytes'] == b['bytes']
    require(prior['completed'] is False and prior['schema'] == 'x.validation.original20-recovery-gun-undo/2'
        and prior['error'] == 'RuntimeError: Redo changed the exact edited Custom20 motion.'
        and prior['stage'] == 'gun_redo_readback' and prior['input_files_unchanged'] is True
        and prior['marker_Undo_cache_reacquired'] is True and prior['marker_Undo_exact_BF59'] is True
        and same(prior['source_inputs']['source'], inputs['marker_reference_source'])
        and same(prior['source_inputs']['package_manifest'], inputs['marker_reference_package_manifest'])
        and all(same(prior['source_inputs'][key], inputs[key]) for key in ('recovery', 'seed', 'protected_artist', 'harness')),
        'Historical .34 remains failed; only its actually completed marker lifecycle may be referenced.')
    require(release['completed'] is False and release['passed'] is False
        and same(release['report'], inputs['marker_reference_report']) and same(release['source'], inputs['marker_reference_source'])
        and release['owned_pid'] == prior['pid'] and release['retained_handle_natural_exit'] is True
        and type(release['native_exit_code']) is int and release['native_exit_code'] == 0
        and release['owned_native_gone'] is True and release['process_termination_performed'] is False,
        'Historical marker evidence lacks its actual natural END.')
    marker = next(row for row in prior['motion_boundaries'] if row['boundary'] == 'marker_Undo')
    require(all(marker[key] is True for key in ('Source_Body_motions_exact', 'pair_and_weights_exact',
        'display_and_VIEW_REFS_exact', 'exact_initial_twenty_and_BF59')), 'The referenced marker boundary is incomplete.')
    diagnostic, ended = (document(inputs[key]['path']) for key in ('redo_diagnostic_report', 'redo_diagnostic_release'))
    require(diagnostic['completed'] is True and ended['completed'] is True
        and ended['semantic_validation_pass'] is False and ended['diagnostic_only'] is True
        and same(ended['source'], inputs['redo_diagnostic_source']) and same(ended['report'], inputs['redo_diagnostic_report'])
        and ended['owned_pid'] == diagnostic['pid'] and ended['retained_handle_natural_exit'] is True
        and type(ended['native_exit_code']) is int and ended['native_exit_code'] == 0
        and ended['owned_native_gone'] is True and ended['process_termination_performed'] is False,
        'The narrow curve diagnostic needs its actual completed evidence and natural END.')
    return {'source_version': '0.77.34', 'historical_report_completed': False, 'measured_this_run': False,
        'marker_Undo_cache_reacquired': True, 'marker_Undo_exact_BF59': True, 'boundary': marker,
        'report': inputs['marker_reference_report'], 'source': inputs['marker_reference_source'],
        'release': inputs['marker_reference_release']}


def verify_capture_publish_scope(inputs, manifest):
    prior = document(inputs['marker_reference_package_manifest']['path'])
    require(set(prior['files']) == set(manifest['files']) and len(manifest['files']) == 190, 'Package leaf domain changed.')
    changed = sorted(name for name in prior['files'] if prior['files'][name] != manifest['files'][name])
    require(changed == ['__init__.py', 'unity_animation_original_inputs.py'], 'Only the reviewed .35 version and two wrappers may differ.')
    leaf = 'unity_animation_original_inputs.py'
    old = pin(Path(prior['source_root']) / leaf, prior['files'][leaf])
    inputs['capture_publish_reference_backend'] = old
    trees = [ast.parse(Path(path).read_text(encoding='utf-8')) for path in (old['path'], Path(manifest['source_root']) / leaf)]
    funcs = [{n.name: ast.dump(n, include_attributes=False) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))} for tree in trees]
    differences = sorted(name for name in funcs[0] if funcs[0][name] != funcs[1].get(name))
    require(set(funcs[0]) == set(funcs[1]) and differences == ['capture_inputs', 'publish_inputs']
        and [ast.dump(n, include_attributes=False) for n in trees[0].body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            == [ast.dump(n, include_attributes=False) for n in trees[1].body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))],
        'Unknown backend function/module change cannot reuse the historical numeric proof.')
    return {'changed_manifest_leaves': changed, 'other_188_manifest_leaves_exact': True,
        'native_entire_file_exact': True, 'changed_existing_backend_functions': differences,
        'all_other_backend_function_ASTs_exact': True, 'backend_module_AST_exact': True,
        'reference_backend': old, 'candidate_backend_sha256': manifest['files'][leaf]}


@contextmanager
def timed(report, operation):
    started = time.perf_counter()
    print('ORIGINAL20_OPERATION_BEGIN ' + operation, flush=True)
    row = {'operation': operation, 'completed': False}
    try:
        yield
        row['completed'] = True
    finally:
        row['elapsed_seconds'] = time.perf_counter() - started
        report.setdefault('operation_timings', []).append(row)
        print('ORIGINAL20_OPERATION_END ' + json.dumps(row), flush=True)


def record_public(report, name):
    report['public_UI_operators_executed'] = True
    called = report.setdefault('actual_public_UI_operator_ids', [])
    if name not in called: called.append(name)
    report['deferred_public_UI'] = [value for value in report['deferred_public_UI'] if value != name]


def publication_identity(rig, session, native):
    """Cheap same-callback identity witness; no admission or cross-Undo RNA reuse."""
    pair = session['original_inputs']
    return {'envelope': rig[native.SESSION_KEY], 'rig': rig.as_pointer(),
        'scene': session['scene'].as_pointer(),
        'references': {name: (type(value).__name__, value.as_pointer()) for name, value in rig[native._REFS_KEY].items()},
        'source': pair['source_action'].as_pointer(), 'custom': pair['custom_action'].as_pointer(),
        'source_slot': pair['source_slot'], 'custom_slot': pair['custom_slot']}


@contextmanager
def undo_view(bpy):
    # No Scene/ViewLayer/Rig/active-object override survives the operation.
    windows = list(bpy.context.window_manager.windows)
    require(len(windows) == 1, 'Use the one isolated headful Window.')
    areas = [a for a in windows[0].screen.areas if a.type == 'VIEW_3D']
    require(len(areas) == 1, 'Use the unique existing factory View3D.')
    regions = [r for r in areas[0].regions if r.type == 'WINDOW']
    require(len(regions) == 1, 'Use the existing View3D WINDOW region.')
    with bpy.context.temp_override(window=windows[0], area=areas[0], region=regions[0]):
        yield


def push_checkpoint(bpy, report, label):
    # Caller has exited all owning_context/temporary_body_display scopes.
    with undo_view(bpy):
        require(bpy.context.preferences.edit.use_global_undo and bpy.ops.ed.undo_push.poll(), 'Global Undo/checkpoint unavailable.')
        with timed(report, 'ed.undo_push ' + label):
            result = bpy.ops.ed.undo_push('EXEC_DEFAULT', False, message=label)
        require(result == {'FINISHED'}, 'Explicit Undo checkpoint failed.')
    report.setdefault('undo_checkpoints', []).append({'label': label, 'result': sorted(result)})


def native_undo_redo(bpy, report, redo=False):
    # No old RNA passed in or inspected afterwards; fresh readback is next tick.
    with undo_view(bpy):
        operator = bpy.ops.ed.redo if redo else bpy.ops.ed.undo
        require(operator.poll(), 'Native Undo/Redo poll failed.')
        with timed(report, 'ed.redo' if redo else 'ed.undo'):
            result = operator('EXEC_DEFAULT', False)
        require(result == {'FINISHED'}, 'Native Undo/Redo failed.')
        del operator
    report['Undo_Redo_performed'] = True
    report.setdefault('undo_redo_operators', []).append({'operator': 'ed.redo' if redo else 'ed.undo',
        'result': sorted(result), 'fresh_readback_deferred_to_next_timer_tick': True})


@contextmanager
def temporary_body_display(bpy, ctx, rig, package, session, report, label):
    """Reveal through the existing BODY button; restore every affected display."""
    def check(value, message):
        if not value:
            raise RuntimeError(message)

    display, native = package.bone_display, package.unity_animation_rigging
    original = __import__(package.__name__ + '.body_original_mode', fromlist=['body_original_mode'])
    pair = session['original_inputs']

    def input_motions():
        # Reuse the existing bounded Input20 fingerprint. No Body scan,
        # backend validation, capture sampling, file read or frame seek.
        return tuple((int(pair[side + '_action'].as_pointer()), pair[side + '_slot'],
                      native._motion(pair[side + '_action'], pair[side + '_slot']))
                     for side in ('source', 'custom'))

    check(ctx.active_object == rig and rig.mode == 'POSE'
          and not original.active(rig),
          'Use the existing Main Rig in Pose/Controls mode for temporary Body display.')
    collections = display._control_collections(ctx, rig, 'BODY')
    check(len(collections) == 1 and collections[0][0] == rig,
          'Temporary Body display needs the one existing owned Body collection.')
    affected = display._affected(ctx, rig)
    checkpoint = display._checkpoint(affected)
    entry_frame = (ctx.scene.frame_current, ctx.scene.frame_subframe)
    observation = {'label': label, 'completed': False,
        'affected_rigs': [target.name for target in affected],
        'public_operator': 'character_designer.bone_display', 'action': 'BODY',
        'public_operator_executed': False, 'display_restored_exactly': False,
        'Source20_Custom20_unchanged_by_show': False,
        'Source20_Custom20_unchanged_by_restore': False}
    report.setdefault('temporary_Body_display_scopes', []).append(observation)
    primary = None
    try:
        before_show = input_motions()
        if not display._controls_visible(collections):
            # BODY is a toggle. Call it only when its current group is hidden,
            # so this is the artist's normal Show Body gesture, never Hide Body.
            observation['public_operator_executed'] = True
            with timed(report, 'public Bone Display BODY'):
                result = bpy.ops.character_designer.bone_display('EXEC_DEFAULT', False, action='BODY')
            observation['operator_result'] = sorted(result)
            check(result == {'FINISHED'}, 'The public Body display operator did not finish.')
        check(display._controls_visible(collections), 'The existing Body controls are still not visible.')
        check(input_motions() == before_show, 'Showing Body changed a Source20 or Custom20 Action/slot/input.')
        check((ctx.scene.frame_current, ctx.scene.frame_subframe) == entry_frame,
              'Showing Body changed the current native key frame.')
        observation['Source20_Custom20_unchanged_by_show'] = True
        yield
        observation['completed'] = True
    except Exception as error:
        primary = error
        observation['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        if observation.get('operator_result') == ['FINISHED']:
            report['public_UI_operators_executed'] = True
            called = report.setdefault('actual_public_UI_operator_ids', [])
            if observation['public_operator'] not in called:
                called.append(observation['public_operator'])
        try:
            before_restore, input_error = None, None
            try:
                before_restore = input_motions()
            except Exception as error:
                # A broken input proof must not prevent restoring the display.
                input_error = error
            # BODY can clear solo flags on Main and Dress rigs. The official
            # complete checkpoint also retains temporary VIEW/REFS ownership.
            display._rollback(checkpoint)
            check(display._checkpoint(affected) == checkpoint,
                  'Temporary Body display did not restore the exact Main/Dress snapshots and VIEW/REFS.')
            observation['display_restored_exactly'] = True
            if input_error is not None:
                raise RuntimeError('Input20 proof was unavailable before display restore.') from input_error
            check(input_motions() == before_restore,
                  'Restoring Body display changed a Source20 or Custom20 Action/slot/input.')
            check((ctx.scene.frame_current, ctx.scene.frame_subframe) == entry_frame,
                  'Temporary Body display changed the same-frame edit/restore scope.')
            observation['Source20_Custom20_unchanged_by_restore'] = True
        except Exception as error:
            observation['completed'] = False
            observation['restore_error'] = type(error).__name__ + ': ' + str(error)
            if primary is None:
                raise
            primary.add_note('Temporary Body display restore failed: ' + str(error))


def exercise_gun_edit(bpy, ctx, rig, package, helper, baseline_dto, report, *, edited_publication_destination, snapshot):
    """Actual Gun edit/Save/publication only; subsequent public Undo owns restoration."""
    backend, native = package.unity_animation_original_inputs, package.unity_animation_rigging
    operator_ids = ('character_designer.original_inputs_edit', 'character_designer.original_inputs_save')
    witness = {'completed': False, 'public_save_count': 0, 'restored_exact_BF59': False,
        'operator_ids': list(operator_ids), 'private_curve_writes': False, 'frame_seek_during_restore': False,
        'Unity_world_equivalence_claimed': False, 'extra_publications': 0}
    report['Gun_Motion_UI_edit_Key'] = witness
    require(bpy.ops.character_designer.original_inputs_edit.poll(), 'The actual Gun Motion operator is unavailable in this owning context.')
    print('ORIGINAL20_STAGE Gun_Motion_UI_select', flush=True)
    with timed(report, 'public Gun Motion Edit'):
        result = bpy.ops.character_designer.original_inputs_edit('EXEC_DEFAULT', False, focus_gun_motion=True)
    witness['edit_operator_result'] = sorted(result)
    require(result == {'FINISHED'}, 'The actual Gun Motion operator did not finish.')
    record_public(report, operator_ids[0])
    with timed(report, 'Gun selection current'):
        session = backend.current(rig)
    require(session is not None and session['enabled'] and session['tweak_enabled']
        and session['edit_role'] == 'RIGGING' and ctx.active_object == rig and rig.mode == 'POSE'
        and native._time(ctx, session) == 0., 'Gun Motion must edit the exact first Custom20 key in its owning Pose context.')
    sides = {row['native_side']: (index, row) for index, row in enumerate(session['native_bindings'])}
    require(set(sides) == {'L', 'R'} and len(session['native_bindings']) == 2, 'Gun Motion needs exactly the captured two-arm inputs.')
    right_index, right = sides['R']; left_index, left = sides['L']
    target = rig.pose.bones[right['target']]
    require(rig.data.bones.active == target.bone
        and [pb.name for pb in rig.pose.bones if package.animation_composition._pose_selection_owner(pb).select] == [target.name],
        'The actual Gun Motion operator did not uniquely select its existing Right Target.')
    visible = [collection.is_visible_effectively for collection in target.bone.collections]
    require(not getattr(target, 'hide', target.bone.hide) and not target.bone.hide
        and ((not visible and not rig.data.collections.is_solo_active) or any(visible))
        and not target.bone.hide_select and not target.lock_location[0],
        'The selected Gun Motion Target must be visible, selectable and position-unlocked.')
    record, gun_objects = package.animation_composition_weapon.validate_owned(rig)
    require(record['rigging_session_owner'] == session['owner']
        and json.loads(record['proof_json'])['native_mount'] == right['chain'][2]
        and session['capture']['bindings'][left_index]['targetParentPath'] == session['capture']['bindings'][right_index]['tipPath'],
        'Gun Motion must use the authenticated gun mount and current Right-hand parent for Left Target.')
    sys.modules['native12_recovery_r14'].exact_initial_twenty(package, session['original_inputs'])
    with timed(report, 'Gun selection public capture'):
        require(backend.capture_inputs(ctx, session) == baseline_dto, 'Gun Motion selection changed a saved input.')
    source_before = native._motion(session['base_action'], session['base_slot'])
    custom_before = native._motion(session['input_action'], session['input_slot'])
    channel_keys = set(native._curves(session['input_action'], session['input_slot']))
    require(len(channel_keys) == 20, 'Gun Motion must retain the existing twenty scalar channels.')
    # Save all four live input transforms because the Left Target follows the
    # moving Right-hand parent. These are pose channels, never Action curves.
    ctx.view_layer.update()
    controls = [rig.pose.bones[row[key]] for row in session['native_bindings'] for key in ('target', 'pole')]
    fields = ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')
    prior = {pb.name: {field: list(getattr(pb, field)) for field in fields} for pb in controls}
    pose_bones = {'right_target': target, 'right_hand': rig.pose.bones[right['chain'][2]],
        'left_target': rig.pose.bones[left['target']], 'left_hand': rig.pose.bones[left['chain'][2]]}
    def observed():
        return {**{name: helper.base.matrix(rig.matrix_world @ pb.matrix) for name, pb in pose_bones.items()},
            **{'gun:' + obj.name: helper.base.matrix(obj.matrix_world) for obj in gun_objects}}
    before = observed()
    witness.update(target=target.name, time=0., native_key_frame=1.,
        source_motion_before=source_before, custom_motion_before=custom_before,
        captured_rig_weights=[binding['rigWeight'] for binding in session['capture']['bindings']],
        captured_weights_modified=False, owned_gun_objects=[obj.name for obj in gun_objects])
    target.location[0] = prior[target.name]['location'][0] + .001
    report['Target_Hint_edit_or_Key_or_Undo_Redo_performed'] = True
    rig.update_tag(refresh={'OBJECT'}); ctx.view_layer.update()
    changed = observed()
    deltas = {name: helper.base.delta(before[name], changed[name]) for name in before}
    witness['native_follow_matrix_deltas'] = deltas
    require(all(delta > 1e-7 for delta in deltas.values()),
        'Moving Gun Motion must visibly move its Right Target, Right hand, owned gun, Left Target and Left hand in this Blender preview.')
    require(bpy.ops.character_designer.original_inputs_save.poll(), 'Key Gun Motion is unavailable after its actual edit.')
    print('ORIGINAL20_STAGE Key_Gun_Motion_UI_edited', flush=True)
    with timed(report, 'public Key Gun Motion Save'):
        result = bpy.ops.character_designer.original_inputs_save('EXEC_DEFAULT', False)
    witness['edited_save_operator_result'] = sorted(result)
    require(result == {'FINISHED'}, 'The actual Key Gun Motion operator did not save the edit.')
    record_public(report, operator_ids[1])
    witness['public_save_count'] = 1
    snapshot('edited_after_Save')
    with timed(report, 'edited current and public capture'):
        session = backend.current(rig)
        edited = backend.capture_inputs(ctx, session)
    require(set(edited) == RETURN_FIELDS and len(edited['frames']) == 59
        and set(native._curves(session['input_action'], session['input_slot'])) == channel_keys
        and native._motion(session['input_action'], session['input_slot']) != custom_before
        and edited['frames'][0]['controls'][right_index]['targetPosition'] != baseline_dto['frames'][0]['controls'][right_index]['targetPosition']
        and native._motion(session['base_action'], session['base_slot']) == source_before,
        'Key Gun Motion must save the changed Right Target in Custom20 while retaining Source20 and strict Return14.')
    witness.update(edited_twenty_scalar_Return_verified=True, Source20_unchanged_after_edit=True)
    if edited_publication_destination is not None:
        print('ORIGINAL20_STAGE publish_actual_edited_Gun_Return', flush=True)
        identity_before = publication_identity(rig, session, native)
        with timed(report, 'publish actual edited Gun Return'):
            edited_publication = backend.publish_inputs(ctx, rig, str(edited_publication_destination))
        require(publication_identity(rig, session, native) == identity_before and session['rig'] == rig and session['scene'] == ctx.scene,
            'Publication changed the same-callback admitted owner or envelope.')
        snapshot('after_publication')
        witness.update(edited_publication=edited_publication, extra_publications=1,
            edited_publication_is_test_evidence_only=True)
        require(set(edited_publication) == {'return', 'publication'},
            'The edited Gun publisher returned no two-file ownership pins.')
        for row in edited_publication.values(): helper.pin(row['path'], row['sha256'])
        publication = helper.document(edited_publication['publication']['path'])
        pair = session['original_inputs']
        require(helper.document(edited_publication['return']['path']) == edited
            and set(edited) == RETURN_FIELDS and len(edited) == 14
            and publication['schema'] == backend.PUBLICATION_SCHEMA and publication['completed'] is True
            and publication['controlChannelCount'] == 20
            and publication['returnSha256'] == edited_publication['return']['sha256']
            and publication['sourceActionId'] == pair['source_uuid']
            and publication['targetInputActionId'] == pair['capture']['newActionId']
            and all(publication[field] == edited[field] for field in RETURN_FIELDS - {'schema', 'frames'})
            and all(publication[field] is True for field in ('sourceReadOnly', 'targetEditable', 'sourceControlsOnly', 'targetControlsOnly'))
            and native._motion(session['base_action'], session['base_slot']) == source_before,
            'The retained edited Gun Return/publication changed strict14 inputs, Source20 or controls-only identities.')
        witness['edited_Return_readback_verified'] = True
    witness.update(completed=True, restoration_method='subsequent public Undo', transform_restore_or_second_Save_performed=False)
    return {'dto': edited, 'motion': native._motion(session['input_action'], session['input_slot']), 'session': session}


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--confirm-isolated-headful', required=True, action='store_true')
    parser.add_argument('--quit-on-completion', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = Path(args.output_root).resolve()
    require(output != ROUND and output.is_relative_to(ROUND) and output.is_dir()
            and not any(output.iterdir()), 'Use a new empty owned output directory.')
    inputs = {'source': pin(__file__, args.source_sha256),
              'harness': pin(ROUND / 'validate_original20_latest_saved_controls_r14.py', R14_SHA),
              'package_manifest': pin(PACKAGE_MANIFEST, MANIFEST_SHA),
              'recovery': pin(RECOVERY, RECOVERY_SHA),
              'native12_report': pin(ROUND / 'native_original20_r13_12/original20_controls_report.json', REPORT_SHA),
              'native12_source': pin(ROUND / 'validate_original20_latest_saved_controls_r13.py', OLD_SOURCE_SHA),
              'native12_release': pin(ROUND / 'resource_release_X_NATIVE12_FAILED_GUN_VISIBILITY.json', RELEASE_SHA),
              'helper': pin(ROUND / 'original_cosha_control_round.py', HELPER_SHA)}
    require(Path(inputs['recovery']['path']) == RECOVERY.resolve()
            and inputs['recovery']['sha256'] == RECOVERY_SHA
            and inputs['harness']['sha256'] == R14_SHA
            and inputs['package_manifest']['sha256'] == MANIFEST_SHA
            and Path(inputs['harness']['path']) == ROUND / 'validate_original20_latest_saved_controls_r14.py',
            'Use the exact owned Native12 recovery, pinned .35 package and explicitly pinned R14 helper.')
    old_report, release = (document(inputs[key]['path']) for key in ('native12_report', 'native12_release'))
    require(old_report['completed'] is False and old_report['source_inputs']['source'] == inputs['native12_source']
            and old_report['Gun_Motion_UI_edit_Key_restore']['public_save_count'] == 0
            and 'Show the Right Target collection' in old_report['error']
            and release['report'] == inputs['native12_report'] and release['completed'] is False
            and release['retained_handle_natural_exit'] is True and release['native_exit_code'] == 0
            and release['owned_native_gone'] is True and release['process_termination_performed'] is False,
            'The recovery provenance must remain the failed Native12 pre-Save run with actual release.')
    for key, expected in (('prepared_report', PREPARED_SHA), ('clock_report', CLOCK_SHA),
                          ('snapshot_receipt', SNAPSHOT_SHA), ('protected_artist', ARTIST_SHA), ('seed', ARTIST_SHA)):
        row = old_report['source_inputs'][key]
        require(row['sha256'] == expected, 'Native12 input binding changed: ' + key)
        inputs[key] = pin(row['path'], expected)
    require(Path(inputs['protected_artist']['path']) == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve(),
            'Hash only the actual protected artist.')
    noop_reference = referenced_noop(inputs)
    marker_reference = referenced_marker_and_redo(inputs)
    inputs['redo_qualification_helper'] = pin(ROUND / 'original20_linear_redo_qualification.py', QUALIFICATION_SHA)
    inputs['redo_qualification_tests'] = pin(ROUND / 'test_original20_linear_redo_qualification.py', QUALIFICATION_TEST_SHA)
    inputs['redo_qualification_test_receipt'] = pin(ROUND / 'original20_linear_redo_qualification_test_receipt.json', QUALIFICATION_RECEIPT_SHA)
    manifest = document(inputs['package_manifest']['path'])
    root = Path(manifest['source_root']).resolve()
    require(manifest['schema_version'] == 1 and manifest['module'] == 'character_designer'
            and manifest['version'] == '0.77.35' and len(manifest['files']) == 190
            and root == PACKAGE_ROOT
            and all(manifest['files'].get(name) == value for name, value in RUNTIME_PINS.items()),
            'Require the exact six reviewed .35 runtime leaves in the complete pinned projection.')
    files = {}
    for relative, expected in manifest['files'].items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root) and '__pycache__' not in path.parts, 'Invalid package leaf.')
        files[relative] = pin(path, expected)
    require({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} == set(files),
            'The frozen runtime has extra or missing files.')
    noop_code_scope = verify_noop_code_scope(inputs, document(inputs['marker_reference_package_manifest']['path']))
    capture_publish_scope = verify_capture_publish_scope(inputs, manifest)
    import bpy
    require(not bpy.app.background and not bpy.data.filepath and tuple(bpy.app.version[:2]) == (5, 2)
            and len(bpy.context.window_manager.windows) == 1, 'Require one fresh isolated headful Blender 5.2 factory child.')
    require(not any(name == 'character_designer' or name.startswith('character_designer.') for name in sys.modules),
            'Another Character Designer runtime is loaded.')
    require(bpy.context.preferences.edit.use_global_undo
            and not bpy.context.preferences.filepaths.use_scripts_auto_execute,
            'Keep existing global Undo enabled and script autoexecution disabled; do not change preferences.')
    report = {'schema': 'x.validation.original20-recovery-gun-undo/3', 'completed': False,
        'scope': 'Authenticated D4CB recovery; referenced failed .33 numeric and failed .34 marker subproofs; measured .35 load/Gun Edit/Save/Undo/Redo/final Undo/save-reopen/publication. Redo alone permits the diagnostic-bound generated LINEAR handle-X rewrite.',
        'source_inputs': inputs, 'pid': os.getpid(), 'native_execution_performed': True,
        'package_manifest_version': manifest['version'], 'package_manifest_file_count': len(files),
        'recovery_opened': False, 'seed_opened': False, 'artist_opened': False, 'artist_written': False,
        'original_artist_integration_verified': False, 'full_original_preservation_oracle_run': False,
        'reference_phases_run': False, 'reimport_performed': False, 'private_curve_writes': False,
        'transform_restore_or_second_Save_performed': False, 'Undo_Redo_performed': False,
        'Unity_Apply_verified': False, 'natural_exit_verified': False,
        'natural_exit_external_retained_handle_readback_required': True,
        'noop_numeric_roundtrip_reference_verified': False, 'noop_Save_performed_this_run': False,
        'noop_Undo_performed_this_run': False, 'load_cache_reacquired_before_current': False,
        'marker_Undo_cache_reacquired': False, 'marker_Undo_exact_BF59': False,
        'marker_Undo_performed_this_run': False, 'marker_Undo_reference_verified': True,
        'Gun_Redo_qualified_Custom20': False, 'Gun_Redo_whole_fingerprint_exact': False,
        'Gun_Undo_exact_BF59': False, 'Gun_Redo_exact_edited_Return': False,
        'final_Undo_exact_BF59': False, 'save_reopen_verified': False,
        'strict14_Return_and_twenty_scalar_publication_verified': False, 'no_QA_offset_remaining': False,
        'final_closed_Source_Body_motions_exact': False}
    report['qualification_pure_tests'] = document(inputs['redo_qualification_test_receipt']['path'])
    require(report['qualification_pure_tests']['completed'] is True and report['qualification_pure_tests']['tests_run'] == 15
        and report['qualification_pure_tests']['failures'] == 0 and report['qualification_pure_tests']['errors'] == 0
        and report['qualification_pure_tests']['source']['sha256'] == QUALIFICATION_SHA
        and report['qualification_pure_tests']['tests']['sha256'] == QUALIFICATION_TEST_SHA, 'The exact portable qualification evidence changed.')
    report['noop_numeric_reference'] = noop_reference
    report['noop_reference_code_scope'] = noop_code_scope
    report['capture_publish_code_scope'] = capture_publish_scope
    report['marker_Undo_reference'] = marker_reference
    report['evidence_scope'] = {'referenced': ['.33 numeric no-op Save only; historical overall run remains failed', '.34 marker Undo subproof only; historical Redo failure remains failed'],
        'measured_this_run': ['.35 load cache before current',
            'Gun edit/Save/publication', 'Gun Undo/Redo/final Undo', 'closed BF59 save/reopen/final publication'],
        'historical_noop_Undo_not_claimed': True, 'original_preservation_oracle_not_rerun': True}
    report_path = output / 'original20_recovery_gun_undo_report.json'
    write(report_path, report)
    state = {'phase': 'open_recovery', 'baseline': None, 'marker': 'codex_original20_07734_undo_' + str(os.getpid())}
    harness = load(inputs['harness']['path'], R14_SHA, 'native12_recovery_r14')
    helper = load(inputs['helper']['path'], HELPER_SHA, 'native12_recovery_protection7098')
    report['deferred_public_UI'] = list(harness.DEFERRED_PUBLIC_UI)
    package = load(root / '__init__.py', files['__init__.py']['sha256'], 'character_designer', package=True)
    require(tuple(package.bl_info['version']) == (0, 77, 35), 'Loaded runtime version mismatch.')
    package.register()
    for name in ('animation_worklist', 'animation_worklist_target', 'animation_worklist_fingerprint',
                 'animation_composition_weapon', 'unity_animation', 'unity_animation_rigging', 'unity_animation_original_inputs'):
        module = __import__('character_designer.' + name, fromlist=[name])
        require(Path(module.__file__).resolve() == root / (name + '.py'), 'Mixed runtime module: ' + name)
        setattr(package, name, module)
    backend, native = package.unity_animation_original_inputs, package.unity_animation_rigging
    qualifier = load(inputs['redo_qualification_helper']['path'], QUALIFICATION_SHA, 'original20_linear_redo_qualification')
    diagnostic_before = document(inputs['redo_diagnostic_before']['path'])
    diagnostic_after = document(inputs['redo_diagnostic_after']['path'])
    diagnostic_qualification = qualifier.qualify_redo(diagnostic_before, diagnostic_after, diagnostic_before, diagnostic_after)
    require(diagnostic_qualification['difference_count'] == 200, 'The fixed diagnostic no longer proves exactly200 differences.')
    fingerprint = package.animation_worklist_fingerprint
    report['diagnostic_qualification'] = diagnostic_qualification
    diagnostic_masked = [fingerprint._stream_digest({'schema': fingerprint.SCHEMA,
        'action': qualifier.masked_payload(value)}) for value in (diagnostic_before, diagnostic_after)]
    require(diagnostic_masked[0] == diagnostic_masked[1] == '1c31caecb9d889445e0fea3fdd0107526681c11e1bf29a92997cf7d83c17b15d',
        'The exact diagnostic masked stream changed.')
    report['diagnostic_masked_fingerprint'] = diagnostic_masked[0]
    probe = SimpleNamespace(bpy=bpy)
    for name in ('id', 'plain'):
        setattr(probe, name, MethodType(getattr(helper.OriginalRound, name), probe))

    def pair_identity(pair):
        return {'rig': probe.id(pair['rig']), 'scene': probe.id(pair['scene']),
            'actions': {side: probe.id(pair[side + '_action']) for side in ('source', 'custom')},
            'slots': {side: pair[side + '_slot'] for side in ('source', 'custom')},
            'source_uuid': pair['source_uuid'], 'custom_uuid': pair['capture']['newActionId'],
            'bindings': probe.plain(pair['capture']['bindings'])}

    def validated_motion_pins(pair):
        # Only after this callback's real public current/capture/publish or _pair_validate.
        # Those admissions recompute and compare these complete Source/Body hashes.
        return {'Source20': pair['source_owner']['source_input_motion'],
            'original_Custom_Body': pair['body_motion'], 'original_Source_Body': pair['body_source_motion']}

    def snapshot(label, *, validate=True):
        identity = state['pair_identity']
        action = next((value for value in bpy.data.actions if probe.id(value) == identity['actions']['custom']), None)
        require(action is not None, 'The actual Custom20 identity is missing during payload retention.')
        payload = fingerprint.collect_action_payload(action, identity['slots']['custom'])
        path = output / (label + '_full20_payload.json')
        require(not path.exists(), 'Never overwrite a retained full20 payload.')
        write(path, payload)
        report.setdefault('custom20_payloads', {})[label] = {
            'payload': pin(path, hashlib.sha256(path.read_bytes()).hexdigest()), 'whole_motion_sha256': None}
        state['last_payload_label'] = label
        write(report_path, report)
        motion = native._motion(action, identity['slots']['custom'])
        require(motion == fingerprint._stream_digest({'schema': fingerprint.SCHEMA, 'action': payload}),
            'Retained full20 payload does not reproduce the unmodified product motion hash.')
        report['custom20_payloads'][label]['whole_motion_sha256'] = motion
        write(report_path, report)
        if validate: qualifier.domain(payload)
        return payload

    def display_identity(ctx, rig):
        display = package.bone_display
        return probe.plain(display._checkpoint(display._affected(ctx, rig)))

    def lifecycle(ctx, rig, label):
        # Cache first: current/seek/activate must not conceal a missing callback.
        require(native._REACQUIRE_TIMER is None and not native._REACQUIRE_PENDING,
                'The one deferred lifecycle admission has not settled before readback.')
        cached = native.display_state(rig)
        require(cached is not None and cached['rig'] == rig and cached['scene'] == ctx.scene
                and cached['enabled'] and cached['original_controls_only'], 'Undo/Redo did not reacquire the Original20 cache.')
        callbacks = {name: sum(value is callback for value in getattr(bpy.app.handlers, name)) for name, callback in (
            ('load_post', native._reacquire), ('undo_post', native._reacquire), ('redo_post', native._reacquire),
            ('frame_change_post', native._frame), ('depsgraph_update_post', native._depsgraph))}
        require(all(count == 1 for count in callbacks.values()) and not native._HANDLER_ERRORS,
                'Owned lifecycle callbacks are missing, duplicate or failed.')
        report.setdefault('lifecycle_witnesses', []).append({'boundary': label, 'callbacks': callbacks,
            'cache_checked_before_current_or_manual_activate': True, 'fresh_timer_tick': True,
            'deferred_timer_cleared': native._REACQUIRE_TIMER is None,
            'pending_empty': not native._REACQUIRE_PENDING, 'handler_errors_empty': not native._HANDLER_ERRORS})

    def boundary(ctx, rig, session, label, *, dto, admission_path, exact=False, expected_dto=None, new_session=False):
        pair = session['original_inputs']
        identity, motions = pair_identity(pair), validated_motion_pins(pair)
        require(identity == state['pair_identity'] and motions == state['immutable_motions'],
                'An input identity/binding/weight or protected Source/Body motion changed.')
        require(new_session or session['owner'] == state['owner'], 'Undo/Redo changed the persistent session owner.')
        require(native._time(ctx, session) == 0. and ctx.scene.frame_current == state['frame'][0]
                and ctx.scene.frame_subframe == state['frame'][1], 'The exact frame-zero input phase changed.')
        require(set(dto) == RETURN_FIELDS and len(dto['frames']) == 59, 'The strict14/BF59 Return changed shape.')
        if exact:
            harness.exact_initial_twenty(package, pair)
            require(dto == state['baseline'] and native._motion(pair['custom_action'], pair['custom_slot']) == state['baseline_motion'],
                    'Restored Input20/BF59 is not bit-exact; no tolerance applies to this gate.')
        if expected_dto is not None:
            require(dto == expected_dto, 'Native Redo did not restore the exact edited Return.')
        require(display_identity(ctx, rig) == state['display_identity'], 'Pre-test display and VIEW/REFS identity changed.')
        report.setdefault('motion_boundaries', []).append({'boundary': label, 'validated_motion_pins': motions, 'actual_admission_path': admission_path,
            'pair_identity': identity, 'Source_Body_motions_exact': True, 'pair_and_weights_exact': True,
            'frame': list(state['frame']), 'native_time': 0., 'exact_initial_twenty_and_BF59': exact,
            'display_and_VIEW_REFS_exact': True})
        return dto

    def open_recovery():
        require(bpy.ops.wm.open_mainfile('EXEC_DEFAULT', False, filepath=inputs['recovery']['path'], use_scripts=False, load_ui=False) == {'FINISHED'}
                and Path(bpy.data.filepath).resolve() == RECOVERY.resolve(), 'Authenticated recovery did not open.')
        report['recovery_opened'] = True
        # No saved RNA is retained in state; subsequent phases reacquire actual data.
        return 'admit'

    def authenticate():
        with harness.owning_context(bpy) as (ctx, rig):
            lifecycle(ctx, rig, 'load_post_before_current')
            report['load_cache_reacquired_before_current'] = True
            with timed(report, 'load fresh current'):
                session = backend.current(rig)
            require(session is not None and 'original_inputs' in session, 'Persistent Original20 session is absent.')
            pair = session['original_inputs']
            for pair_key, input_key in (('prepared_report', 'prepared_report'), ('clock_certificate', 'clock_report'), ('snapshot_receipt', 'snapshot_receipt')):
                require(harness.same_pin(pair[pair_key], inputs[input_key]), 'Persistent evidence changed: ' + pair_key)
            require(pair['packet']['sha256'] == PACKET_SHA, 'The captured BF packet changed.')
            inputs['packet'] = pin(pair['packet']['path'], PACKET_SHA)
            packet = package.unity_animation.load_package(pair['packet']['path'])
            require(pair['capture'] == package.animation_rigging_contract.validate_capture(packet['rigging'], packet=packet)
                    and len(pair['capture']['frames']) == 59, 'Persisted BF59 capture changed.')
            harness.exact_initial_twenty(package, pair)
            report['Action_inventory'] = inventory(bpy, helper, pair, document(inputs['snapshot_receipt']['path']))
            require(session['enabled'] and session['tweak_enabled'] and session['edit_role'] == 'RIGGING'
                    and rig.mode == 'POSE' and rig.animation_data.use_tweak_mode and native._time(ctx, session) == 0.,
                    'Recovery lost its first-key Pose/Tweak context.')
            with timed(report, 'initial baseline public capture'):
                state['baseline'] = backend.capture_inputs(ctx, session)
            state['pair_identity'], state['immutable_motions'] = pair_identity(pair), validated_motion_pins(pair)
            require(state['pair_identity'] == noop_reference['pair_identity']
                    and state['immutable_motions'] == noop_reference['source_body_motions'],
                    'Current recovered Source/Body/pair does not match the referenced numeric measurement.')
            report['noop_numeric_roundtrip_reference_verified'] = True
            state['baseline_motion'] = native._motion(pair['custom_action'], pair['custom_slot'])
            # Reapply the unchanged fixed native before the Undo baseline; Body can stay hidden.
            with timed(report, 'apply fixed native prebaseline'):
                session = backend.edit_controls(ctx, rig)
            state['owner'] = session['owner']
            state['frame'] = (ctx.scene.frame_current, ctx.scene.frame_subframe)
            state['display_identity'] = display_identity(ctx, rig)
            with timed(report, 'prebaseline public capture'):
                baseline_check = backend.capture_inputs(ctx, session)
            boundary(ctx, rig, session, 'fixed_35_prebaseline', dto=baseline_check, admission_path='public edit_controls + capture_inputs', exact=True)
            snapshot('baseline')
            write(output / 'baseline_Return.json', state['baseline'])
            report['persistent_pair_and_exact_BF20_authenticated'] = True
        push_checkpoint(bpy, report, 'Original20 .35 before Gun edit')
        return 'gun_edit'

    def marker_write():
        with harness.owning_context(bpy) as (ctx, rig):
            require(state['marker'] not in ctx.scene, 'The unique owned Scene marker already exists.')
            ctx.scene[state['marker']] = 1
        push_checkpoint(bpy, report, 'Original20 .34 after Scene lifecycle marker')
        return 'marker_undo'

    def read_undo(label, flag, next_phase, *, redo=False):
        with harness.owning_context(bpy) as (ctx, rig):
            lifecycle(ctx, rig, label)
            with timed(report, label + ' fresh current and public capture'):
                session = backend.current(rig)
                dto = backend.capture_inputs(ctx, session)
            boundary(ctx, rig, session, label, dto=dto, admission_path='fresh current + public capture_inputs', exact=not redo,
                expected_dto=state['gun_edited']['dto'] if redo else None)
            if redo:
                actual = snapshot('Redo')
                before = document(report['custom20_payloads']['post_checkpoint_before_Undo']['payload']['path'])
                qualification = qualifier.qualify_redo(before, actual, diagnostic_before, diagnostic_after)
                report['Redo_qualification'] = qualification
                left = fingerprint._stream_digest({'schema': fingerprint.SCHEMA, 'action': qualifier.masked_payload(before)})
                right = fingerprint._stream_digest({'schema': fingerprint.SCHEMA, 'action': qualifier.masked_payload(actual)})
                report['Redo_masked_fingerprint'] = {'before': left, 'after': right, 'equal': left == right,
                    'algorithm': "frozen fingerprint._stream_digest({'schema':fingerprint.SCHEMA,'action':qualifier.masked_payload(payload)})"}
                require(left == right, 'A non-qualified field changed in the original canonical fingerprint stream.')
                whole_equal = report['custom20_payloads']['post_checkpoint_before_Undo']['whole_motion_sha256'] == report['custom20_payloads']['Redo']['whole_motion_sha256']
                require(whole_equal == qualification['whole_payload_exact'], 'Whole product fingerprint and complete payload equality disagree.')
                report['Gun_Redo_whole_fingerprint_exact'] = whole_equal
                report['Gun_Redo_qualified_Custom20'] = qualification['qualified_semantic20_equal']
            report[flag] = True
        return next_phase

    def gun_edit():
        with harness.owning_context(bpy) as (ctx, rig):
            with timed(report, 'Gun entry current'):
                session = backend.current(rig)
            with temporary_body_display(bpy, ctx, rig, package, session, report, 'Gun public edit and edited Return'):
                edited = exercise_gun_edit(bpy, ctx, rig, package, helper, state['baseline'], report,
                    edited_publication_destination=output / 'edited_gun_controls_Return.json', snapshot=snapshot)
                session = edited.pop('session')
            snapshot('after_display_restore')
            state['gun_edited'] = edited
            # Same synchronous callback, freshly admitted by public Edit/current/capture/publication;
            # the display scope proves both input carriers unchanged by restoration.
            boundary(ctx, rig, session, 'Gun_edited_saved', dto=edited['dto'], admission_path='public Gun Edit/Save + current + capture_inputs + publish_inputs')
        push_checkpoint(bpy, report, 'Original20 .35 after Gun edit Save')
        snapshot('post_checkpoint_before_Undo')
        edited_payload = document(report['custom20_payloads']['edited_after_Save']['payload']['path'])
        for label in ('after_publication', 'after_display_restore', 'post_checkpoint_before_Undo'):
            require(not qualifier.full_diff(edited_payload, document(report['custom20_payloads'][label]['payload']['path'])),
                'Publication/display/checkpoint changed saved Custom20 data before Undo: ' + label)
        report['edited_payload_retained_exact_through_checkpoint'] = True
        return 'gun_undo'

    def close_save():
        with harness.owning_context(bpy) as (ctx, rig):
            with timed(report, 'final BF fresh current and public capture'):
                session = backend.current(rig)
                dto = backend.capture_inputs(ctx, session)
            boundary(ctx, rig, session, 'final_BF_before_Close', dto=dto, admission_path='fresh current + public capture_inputs', exact=True)
            with timed(report, 'public Close'):
                result = bpy.ops.character_designer.original_inputs_close('EXEC_DEFAULT', False)
            require(result == {'FINISHED'} and backend.current(rig) is None and backend.PAIR_KEY in rig,
                    'Owned preview did not close with its pair retained.')
            record_public(report, 'character_designer.original_inputs_close')
            with timed(report, 'closed full pair validation'):
                pair = backend._pair_validate(backend._pair(rig), files=True)
            harness.exact_initial_twenty(package, pair)
            require(pair_identity(pair) == state['pair_identity'] and validated_motion_pins(pair) == state['immutable_motions'],
                    'Close changed the persistent pair or protected motions.')
        clone = output / 'original20_controls_owned.blend'
        require(not clone.exists(), 'Do not overwrite a prior clone.')
        with timed(report, 'closed BF SaveCopy'):
            result = bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', False, filepath=str(clone), copy=True, check_existing=False)
        require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == RECOVERY.resolve(), 'Closed BF59 SaveCopy failed.')
        report['saved_clone'] = pin(clone, hashlib.sha256(clone.read_bytes()).hexdigest())
        return 'reopen'

    def reopen():
        clone = report['saved_clone']
        pin(clone['path'], clone['sha256'])
        require(bpy.ops.wm.open_mainfile('EXEC_DEFAULT', False, filepath=clone['path'], use_scripts=False, load_ui=False) == {'FINISHED'}
                and Path(bpy.data.filepath).resolve() == Path(clone['path']), 'Actual saved clone did not reopen.')
        return 'reopened_readback'

    def reopened_readback():
        with harness.owning_context(bpy) as (ctx, rig):
            require(native.display_state(rig) is None and backend.current(rig) is None and backend.PAIR_KEY in rig,
                    'Saved closed pair did not reopen in its closed state.')
            with timed(report, 'reopened full pair validation'):
                pair = backend._pair_validate(backend._pair(rig), files=True)
            harness.exact_initial_twenty(package, pair)
            require(pair_identity(pair) == state['pair_identity'] and validated_motion_pins(pair) == state['immutable_motions'],
                    'Reopening changed input identities or Source/Body motions.')
            report['reopened_Action_inventory'] = inventory(bpy, helper, pair, document(inputs['snapshot_receipt']['path']))
            # Reactivate existing authenticated pair; never reimport any carrier.
            with timed(report, 'reopened public edit_controls'):
                session = backend.edit_controls(ctx, rig)
            identity_before = publication_identity(rig, session, native)
            with timed(report, 'publish actual reopened BF Return'):
                published = backend.publish_inputs(ctx, rig, str(output / 'captured_controls_Return.json'))
            require(publication_identity(rig, session, native) == identity_before and session['rig'] == rig and session['scene'] == ctx.scene,
                'Final publisher changed its same-callback owner or envelope.')
            require(set(published) == {'return', 'publication'}, 'Final publication did not return two pins.')
            for row in published.values(): pin(row['path'], row['sha256'])
            dto, publication = document(published['return']['path']), document(published['publication']['path'])
            require(dto == state['baseline'] and set(dto) == RETURN_FIELDS and publication['completed'] is True
                and publication['schema'] == backend.PUBLICATION_SCHEMA and publication['controlChannelCount'] == 20
                and publication['returnSha256'] == published['return']['sha256']
                and publication['sourceActionId'] == pair['source_uuid']
                and publication['targetInputActionId'] == pair['capture']['newActionId']
                and all(publication[field] == dto[field] for field in RETURN_FIELDS - {'schema', 'frames'})
                and all(publication[field] is True for field in ('sourceReadOnly', 'targetEditable', 'sourceControlsOnly', 'targetControlsOnly')),
                'Final publication changed exact BF59/strict14/controls-only identities.')
            boundary(ctx, rig, session, 'reopened_BF59', dto=dto, admission_path='public edit_controls + publish_inputs Return readback', exact=True, new_session=True)
            report['save_reopen_verified'] = True
            report['actual_controls_only_publication'] = published
            report['strict14_Return_and_twenty_scalar_publication_verified'] = True
            with timed(report, 'final close and full pair validation'):
                backend.close_owned(ctx, rig)
                pair = backend._pair_validate(backend._pair(rig), files=True)
            harness.exact_initial_twenty(package, pair)
            require(validated_motion_pins(pair) == state['immutable_motions'] and pair_identity(pair) == state['pair_identity'],
                'Final Close changed Source/Body motions or identities.')
            report['final_closed_Source_Body_motions_exact'] = True
            report['no_QA_offset_remaining'] = True
        return 'finish'

    def finish(error=None):
        if error is not None:
            report.update(completed=False, error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
            write(report_path, report)
            try:
                if state.get('pair_identity'):
                    last = snapshot('failure_last', validate=False)
                    previous = report.get('custom20_payloads', {}).get('post_checkpoint_before_Undo')
                    if previous:
                        differences = qualifier.full_diff(document(previous['payload']['path']), last)
                        path = output / 'failure_last_structural_diff.json'
                        write(path, differences)
                        report['failure_last_structural_diff'] = pin(path, hashlib.sha256(path.read_bytes()).hexdigest())
            except Exception as payload_error:
                report['failure_payload_readback_error'] = type(payload_error).__name__ + ': ' + str(payload_error)
            # Failure retention is observational: never re-admit or sample BF59
            # after an early lifecycle failure. Success guards remain unchanged.
            try:
                rig = bpy.data.objects.get('CoshaRig')
                envelope = json.loads(rig[native.SESSION_KEY]) if rig is not None and native.SESSION_KEY in rig else {}
                payload = envelope.get('payload', {})
                report['failure_lifecycle_raw'] = {
                    'CACHE': {str(key): {field: value.get(field) for field in
                        ('owner', 'enabled', 'edit_role', 'tweak_enabled', 'preview_error')}
                        for key, value in native._CACHE.items()},
                    'HANDLER_ERRORS': dict(native._HANDLER_ERRORS), 'BUSY': sorted(native._BUSY),
                    'SUSPENDED': dict(native._SUSPENDED), 'persistent_SESSION_present': bool(envelope),
                    'deferred_timer_present': native._REACQUIRE_TIMER is not None,
                    'deferred_timer_registered': native._REACQUIRE_TIMER is not None
                        and bpy.app.timers.is_registered(native._REACQUIRE_TIMER),
                    'pending_present': bool(native._REACQUIRE_PENDING),
                    'pending_rig_pointers': sorted(native._REACQUIRE_PENDING),
                    'rig_matrix_world': [float(value) for row in rig.matrix_world for value in row]
                        if rig is not None else None,
                    'persistent_object_matrix': payload.get('object_matrix'),
                    'persistent_flags': {field: payload.get(field) for field in
                        ('enabled', 'edit_role', 'tweak_enabled', 'preview_error')},
                    'current_or_capture_called': False}
            except Exception as read_error:
                report['failure_raw_readback_error'] = type(read_error).__name__ + ': ' + str(read_error)
            try:
                allowed = {RECOVERY.resolve()}
                if 'saved_clone' in report: allowed.add(Path(report['saved_clone']['path']).resolve())
                require(bpy.data.filepath and Path(bpy.data.filepath).resolve() in allowed, 'Retain only an authenticated owned scene.')
                failure = output / 'failed_original20_recovery_gun_undo.blend'
                require(not failure.exists(), 'Never overwrite retained failure evidence.')
                active_path = Path(bpy.data.filepath).resolve()
                result = bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', False, filepath=str(failure), copy=True, check_existing=False)
                require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == active_path, 'Failure SaveCopy failed.')
                report['failure_scene'] = pin(failure, hashlib.sha256(failure.read_bytes()).hexdigest())
            except Exception as save_error:
                report['failure_scene_error'] = type(save_error).__name__ + ': ' + str(save_error)
        try:
            for row in list(inputs.values()) + list(files.values()): pin(row['path'], row['sha256'])
            if 'saved_clone' in report: pin(report['saved_clone']['path'], report['saved_clone']['sha256'])
            for row in report.get('custom20_payloads', {}).values(): pin(row['payload']['path'], row['payload']['sha256'])
            report['input_files_unchanged'] = True
        except Exception as immutable_error:
            report['immutable_input_error'] = type(immutable_error).__name__ + ': ' + str(immutable_error)
            error = immutable_error
        required = ('noop_numeric_roundtrip_reference_verified', 'load_cache_reacquired_before_current',
            'marker_Undo_reference_verified', 'Gun_Redo_qualified_Custom20', 'edited_payload_retained_exact_through_checkpoint', 'Gun_Undo_exact_BF59',
            'Gun_Redo_exact_edited_Return', 'final_Undo_exact_BF59', 'save_reopen_verified',
            'strict14_Return_and_twenty_scalar_publication_verified', 'no_QA_offset_remaining',
            'final_closed_Source_Body_motions_exact', 'input_files_unchanged')
        report['completed'] = error is None and all(report[field] is True for field in required)
        write(report_path, report)
        print('ORIGINAL20_RECOVERY_GUN_UNDO ' + json.dumps({'completed': report['completed'], 'report': str(report_path)}), flush=True)
        if args.quit_on_completion:
            def quit_owned():
                observation = {'pid': os.getpid(), 'requested_from_timer': True,
                    'completed_report': report['completed'], 'natural_exit_still_external': True}
                try:
                    observation['operator_result'] = sorted(bpy.ops.wm.quit_blender('EXEC_DEFAULT', False))
                except Exception as quit_error:
                    observation['error'] = type(quit_error).__name__ + ': ' + str(quit_error)
                write(output / 'owned_quit_observation.json', observation)
                return None
            bpy.app.timers.register(quit_owned, first_interval=3., persistent=False)
        return None

    def wait_for_owned_lifecycle(phase):
        # Record all yielded wall time, including blocking native callbacks.
        # Only a still-pending owned callback is subject to this boundary's deadline.
        # Never run current/reacquire/seek/Activate or schedule another retry.
        now = time.monotonic()
        observation = report.setdefault('lifecycle_async_wait', {
            'boundary_pending_deadline_seconds': 120., 'elapsed_seconds': 0., 'wait_count': 0, 'boundaries': {},
            'budget_reason': 'Bound a still-pending owned callback; synchronous native admission/evaluation time is not a performance acceptance gate.'})
        row = observation['boundaries'].setdefault(phase, {'wait_count': 0, 'elapsed_seconds': 0.})
        previous = state.pop('lifecycle_wait_last_yield', None)
        if previous is not None:
            started, previous_phase = previous
            elapsed = now - started
            observation['elapsed_seconds'] += elapsed
            observation['boundaries'][previous_phase]['elapsed_seconds'] += elapsed
        timer = native._REACQUIRE_TIMER
        rig = bpy.data.objects.get('CoshaRig')
        owned_pending = rig is not None and rig.as_pointer() in native._REACQUIRE_PENDING
        registered = timer is not None and bpy.app.timers.is_registered(timer)
        row.update(owned_pending=owned_pending, pending_count=len(native._REACQUIRE_PENDING),
            timer_present=timer is not None, timer_registered=registered)
        if 'first_pending_monotonic' in row:
            row['pending_observation_seconds'] = now - row['first_pending_monotonic']
        if not owned_pending or not registered:
            return False
        first_pending = row.setdefault('first_pending_monotonic', now)
        row['pending_observation_seconds'] = now - first_pending
        require(now <= first_pending + observation['boundary_pending_deadline_seconds'],
                'Owned deferred lifecycle admission is still pending after this boundary\'s 120-second deadline.')
        row['wait_count'] += 1
        observation['wait_count'] += 1
        state['lifecycle_wait_last_yield'] = (now, phase)
        print('ORIGINAL20_LIFECYCLE_WAIT ' + json.dumps({'phase': phase,
            'wait_count': observation['wait_count'], 'elapsed_seconds': observation['elapsed_seconds']}), flush=True)
        return True

    def tick():
        phase = state['phase']
        report['stage'] = phase
        write(report_path, report)
        print('ORIGINAL20_RECOVERY_STAGE ' + phase, flush=True)
        phase_started = time.perf_counter()
        try:
            if phase in ('admit', 'marker_readback', 'gun_undo_readback', 'gun_redo_readback', 'gun_final_readback') \
                    and wait_for_owned_lifecycle(phase):
                write(report_path, report)
                return .1
            if phase == 'open_recovery': next_phase = open_recovery()
            elif phase == 'admit': next_phase = authenticate()
            elif phase == 'marker_write': next_phase = marker_write()
            elif phase in ('marker_undo', 'gun_undo', 'gun_final_undo'):
                native_undo_redo(bpy, report)
                next_phase = {'marker_undo': 'marker_readback', 'gun_undo': 'gun_undo_readback', 'gun_final_undo': 'gun_final_readback'}[phase]
            elif phase == 'marker_readback': raise RuntimeError('Marker is historical evidence only in schema3.')
            elif phase == 'gun_edit': next_phase = gun_edit()
            elif phase == 'gun_undo_readback': next_phase = read_undo('Gun_Undo', 'Gun_Undo_exact_BF59', 'gun_redo')
            elif phase == 'gun_redo':
                native_undo_redo(bpy, report, redo=True)
                next_phase = 'gun_redo_readback'
            elif phase == 'gun_redo_readback': next_phase = read_undo('Gun_Redo', 'Gun_Redo_exact_edited_Return', 'gun_final_undo', redo=True)
            elif phase == 'gun_final_readback': next_phase = read_undo('final_Undo', 'final_Undo_exact_BF59', 'close_save')
            elif phase == 'close_save': next_phase = close_save()
            elif phase == 'reopen': next_phase = reopen()
            elif phase == 'reopened_readback': next_phase = reopened_readback()
            elif phase == 'finish': return finish()
            else: raise RuntimeError('Unknown owned phase: ' + phase)
            state['phase'] = next_phase
            write(report_path, report)
            return .1
        except Exception as error:
            return finish(error)
        finally:
            print('ORIGINAL20_PHASE_END ' + json.dumps({'phase': phase,
                'elapsed_seconds': time.perf_counter() - phase_started}), flush=True)

    # This one owned timer opens two authenticated files. Returning None ends it.
    bpy.app.timers.register(tick, first_interval=.1, persistent=True)


if __name__ == '__main__':
    main()
