"""Read-only qualification of the exact recorded .38 recovery differences.

Keep the failed strict receipt and all four snapshots immutable. Full geometry
and Action content evidence is reused from those snapshots, not sampled again.
"""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
import traceback

ROUND = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012')
STRICT_REPORT = ROUND / 'original_artist_recovery_07738_03/recovery_report.json'
STRICT_SHA = '4869aee60d85c80da77716b4fbbe0d79b9972521701a7fa113e8abcea312586e'
CONTINUATION = ROUND / 'continue_original_registration_07738c.py'
CONTINUATION_SHA = '6fc450dc8a145fb2cf87f37eaf2265b1e4f7a918ed410cb5b7cf32a51f1411db'
VERIFIER_SOURCE = ROUND / 'recover_original_registration_07738b.py'
VERIFIER_SHA = '3636e8b0f15bcf6e1df5a3b511adfd8684db265f58610b89a4a7666daad339bb'
F9_SHA = '34f4a7449d2ae68daefa0c02d584aa823a867e34e617b0afca59f7856a771b05'
MANIFEST_SHA = '0d0678388250fca04ce53164628c9460d6d237a5664d6e14c5f79ea8b337e209'
FT_SHA = '54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408'
SKIRT_UI_SHA = 'f47329a18631fc80463f64503b660b21043a1c0869ab0864aaa9db47c5e249ca'
SNAPSHOT_SHAS = {
    'fresh_full_before': 'ff34b835cf347f6dd55308c9b22d682f54139d04b4d914f546ce58329ea2b599',
    'fresh_full_after': '866747ce3f95a44389be3f71fb14b193f895a2f304b4252968d6b9486d3259a9',
    'fresh_raw_Scene_WM_Object_Action_before': '05f3bb41c1953eb2cf56236d288096637b080fb13b9792120d164111ed9449df',
    'fresh_raw_Scene_WM_Object_Action_after': 'f0388908ef247b6aa6a9fc73da4a0afc42c9acf0ffcc34864a9bcc8f94318b03',
}
MUTE_PATHS = tuple(('assets', 'CoshaRig', 'runtime_generated_outputs', 'objects', 'Cosha', 'keys',
                    'CD Forearm Twist.' + side + '.002', 'mute') for side in ('L', 'R'))
DEFAULT_PATHS = (('Scene_custom_properties', '2558108551696', 'character_designer_twist_render_lock'),
                 ('window_managers', '2556597908496', 'character_designer_dress_wiggle_advanced'))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def typed(value):
    if value is None:
        return ['null']
    if type(value) is bool:
        return ['bool', value]
    if type(value) is int:
        return ['int', str(value)]
    if type(value) is float:
        require(math.isfinite(value), 'Nonfinite numeric metadata is not qualified.')
        return ['float64', struct.pack('>d', value).hex()]
    if type(value) is str:
        return ['str', value]
    if type(value) is list:
        return ['list', [typed(item) for item in value]]
    require(type(value) is dict and all(type(key) is str for key in value), 'Only exact JSON data is qualified.')
    return ['dict', [[key, typed(value[key])] for key in sorted(value)]]


def encoded(value):
    return json.dumps(typed(value), ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def differences(before, after, path=()):
    if type(before) is dict and type(after) is dict:
        result = []
        for key in sorted(set(before) | set(after)):
            if key not in before or key not in after:
                row = {'path': list(path + (key,)), 'before_present': key in before, 'after_present': key in after}
                if key in before:
                    row['before'] = before[key]
                if key in after:
                    row['after'] = after[key]
                result.append(row)
            else:
                result.extend(differences(before[key], after[key], path + (key,)))
        return result
    if type(before) is list and type(after) is list and len(before) == len(after):
        return [row for index, (left, right) in enumerate(zip(before, after))
                for row in differences(left, right, path + (index,))]
    if encoded(before) == encoded(after):
        return []
    return [{'path': list(path), 'before_present': True, 'after_present': True, 'before': before, 'after': after}]


def parent_at(value, path):
    for component in path[:-1]:
        value = value[component]
    return value


def qualify_evidence(full_before, full_after, raw_before, raw_after, pre_failure_assets):
    """Pure exact qualification; no tolerance, generic ignore-list or bpy access."""
    full_diff = differences(full_before, full_after)
    expected_full = [{'path': list(path), 'before_present': True, 'after_present': True,
                      'before': True, 'after': False} for path in MUTE_PATHS]
    raw_diff = differences(raw_before, raw_after)
    expected_raw = [{'path': list(path), 'before_present': False, 'after_present': True, 'after': False}
                    for path in DEFAULT_PATHS]
    require(encoded(full_diff) == encoded(expected_full), 'Full preservation differences exceed the two proven Forearm mute restorations.')
    require(encoded(raw_diff) == encoded(expected_raw), 'Raw differences exceed the two proven false registration fields.')
    require(encoded(full_after['assets']) == encoded(pre_failure_assets),
            'The entire recovered asset tree differs from the actual pre-F9 failure asset tree.')
    projected_full, projected_raw = copy.deepcopy(full_after), copy.deepcopy(raw_after)
    for path in MUTE_PATHS:
        parent_at(projected_full, path)[path[-1]] = True
    for path in DEFAULT_PATHS:
        del parent_at(projected_raw, path)[path[-1]]
    require(encoded(projected_full) == encoded(full_before) and encoded(projected_raw) == encoded(raw_before),
            'Unqualified values changed outside the exact proven paths.')
    return {'qualified_preservation_verified': True, 'strict_full_capture_exact': False,
        'strict_raw_capture_exact': False, 'full_differences': full_diff, 'raw_differences': raw_diff,
        'entire_after_assets_equal_actual_pre_failure_assets': True,
        'typed_projected_full_sha256': digest(projected_full),
        'typed_projected_raw_sha256': digest(projected_raw),
        'typed_recovered_and_pre_failure_assets_sha256': digest(pre_failure_assets),
        'comparison': 'Exact JSON types, ordered lists and IEEE-754 binary64 bits; no numeric epsilon.'}


def run(*, expected_pid, external_process_filetime, authorization_token,
        external_authorization_confirmed, script_sha256, output_root):
    import bpy
    continuation = sys.modules.get('x_original_runtime_recovery_07738_03')
    require(continuation is not None and continuation.ACTIVE is not None,
            'Retain the actual continuation; do not reconstruct its native history.')
    prior = continuation.ACTIVE
    state = prior.STATE
    require(external_authorization_confirmed is True and type(authorization_token) is str and authorization_token
        and type(expected_pid) is int and expected_pid == os.getpid() == 14500
        and type(external_process_filetime) is int and external_process_filetime == state['config']['external_process_filetime'],
        'Fresh root authorization and the same original PID/FILETIME are required.')
    inputs = {'source': prior.pin(__file__, script_sha256), 'strict_recovery_report': prior.pin(STRICT_REPORT, STRICT_SHA),
              'strict_recovery_source': prior.pin(CONTINUATION, CONTINUATION_SHA),
              'strict_verifier_source': prior.pin(VERIFIER_SOURCE, VERIFIER_SHA)}
    require(Path(continuation.__file__).resolve() == CONTINUATION.resolve()
        and Path(prior.__file__).resolve() == VERIFIER_SOURCE.resolve(), 'Retained helper identity/source changed.')
    strict = prior.document(inputs['strict_recovery_report'])
    require(prior.exact_json(state['report']) == prior.exact_json(strict)
        and strict['completed'] is False and strict['phase'] == 'candidate_verification_failed'
        and strict['error'] == 'RuntimeError: Original protected assets changed during refresh.'
        and strict['pid'] == expected_pid and strict['external_process_filetime'] == external_process_filetime,
        'Use the actual unchanged strict failure; never upgrade or overwrite it.')
    for key in ('exact_original36_cleanup_completed', 'temporary_root_removed', 'standard_enable_returned',
                'continuation_of_actual_partial_cleanup', 'current_precleanup_baseline_exact_before_continuation'):
        require(strict[key] is True, 'A completed recovery prerequisite is missing: ' + key)
    require(strict['before_baseline_replaced'] is False and strict['registered_candidate_version'] == [0, 77, 38]
        and strict['standard_enable_errors'] == [] and strict['owned_RNA_classes_remaining_after_cleanup'] == [],
        'The actual cleanup/enable scope differs.')
    for key, row in strict['inputs'].items():
        inputs['recovery_' + key] = prior.pin(row['path'], row['sha256'])
    require(strict['inputs']['package_manifest']['sha256'] == MANIFEST_SHA
        and strict['inputs']['failed_refresh_receipt']['sha256'] == F9_SHA, 'The package or actual pre-failure witness changed.')
    snapshots = {}
    for key, expected in SNAPSHOT_SHAS.items():
        require(strict[key]['sha256'] == expected, 'The exact recovery snapshot changed: ' + key)
        inputs[key] = prior.pin(strict[key]['path'], expected)
        snapshots[key] = prior.document(inputs[key])
    f9 = prior.document(strict['inputs']['failed_refresh_receipt'])
    require(f9['completed'] is False and f9['phase'] == 'before_disable_07724' and f9['old_version'] == [0, 77, 24],
            'The pre-failure asset witness is not the actual failed .24-to-.36 refresh.')
    qualification = qualify_evidence(snapshots['fresh_full_before'], snapshots['fresh_full_after'],
        snapshots['fresh_raw_Scene_WM_Object_Action_before'], snapshots['fresh_raw_Scene_WM_Object_Action_after'], f9['before_assets'])
    installed, manifest = state['installed'], state['candidate']
    inputs['forearm_runtime_source'] = prior.pin(installed / 'forearm_twist.py', FT_SHA)
    inputs['dress_UI_source'] = prior.pin(installed / 'skirt_wiggle_ui.py', SKIRT_UI_SHA)
    package = state['candidate_module']
    require(sys.modules.get('character_designer') is package and tuple(package.bl_info['version']) == (0, 77, 38)
        and package.__addon_enabled__ and not bpy.app.background
        and Path(bpy.data.filepath).resolve() == prior.ARTIST.resolve(), 'The actual recovered runtime/process changed.')
    output = Path(output_root).resolve()
    require(not output.exists() and output.is_relative_to(ROUND), 'Use a new qualification-only output directory.')
    output.mkdir()
    report_path = output / 'qualified_recovery_report.json'
    report = {'schema': 'x.recovery.original-registration-qualified/1', 'completed': False,
        'phase': 'qualified_snapshot_evidence_before_fresh_live_read', 'inputs': inputs,
        'pid': expected_pid, 'external_process_filetime': external_process_filetime,
        'authorization_token': authorization_token, 'registered_candidate_version': [0, 77, 38],
        'qualification': qualification, 'strict_recovery_remains_failed': True,
        'fresh_full_postfailure_preservation_verified': False, 'fresh_raw_values_exact': False,
        'unknown_pre_failure_WM_or_Undo_preservation_claimed': False,
        'file_reload_or_save_performed': False, 'runtime_registration_or_scene_mutation_performed': False,
        'live_full_asset_or_Action_content_recapture_performed': False,
        'full_evidence_scope': 'Exact recorded 866747 full after snapshot qualified against original FF34 and pre-F9 asset tree; no full geometry/motion rescan.',
        'live_read_scope': 'Fresh light, raw Scene/WM/Object/Action properties, Scene/WM, context/pose, all native ID identities/users and natural runtime lifecycle only.'}
    def write():
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    write()
    try:
        native = sys.modules['character_designer.unity_animation_rigging']
        ft = sys.modules['character_designer.forearm_twist']
        require(native._REACQUIRE_TIMER is None and not native._REACQUIRE_PENDING and not native._HANDLER_ERRORS
            and native._REACQUIRE_GENERATION == state['pending_generation'] + 1
            and not bpy.app.timers.is_registered(state['pending_timer']), 'Natural native registration admission is not settled exactly once.')
        require(ft._RUNTIME_REGISTERED and not ft._INITIALIZE_PENDING and not ft._SCENE_CLEANUP_PENDING
            and not bpy.app.timers.is_registered(ft._complete_runtime_lifecycle), 'Forearm registration lifecycle has not settled.')
        for name in ('load_post', 'undo_post', 'redo_post'):
            require(getattr(bpy.app.handlers, name).count(native._reacquire) == 1, 'The actual native lifecycle callback is missing/duplicated.')
        for name, callback in ft._HANDLERS:
            require(getattr(bpy.app.handlers, name).count(callback) == 1, 'The actual Forearm callback is missing/duplicated.')
        package._validate_registration_integrity()
        state['refresh'].loaded_sources(package, installed, manifest)
        with state['light'].original_context(bpy, 'Scene', 'CoshaRig') as (ctx, rig):
            state['refresh'].idle(package, ctx, bpy)
            light, verifier = state['light'], state['verifier']
            observed = {'light': light.snapshot(ctx, rig, bpy, sys.modules['character_designer.unity_animation']),
                'raw': prior.corrected_raw_snapshot(bpy, state['observed']),
                'scenes': verifier.scene_capture(), 'wm': verifier.wm_capture(package),
                'context': verifier.native_context(), 'pose': verifier.native_pose_channels(),
                'all_IDs': sorted((dict(light.reference(block), users=block.users, use_fake_user=block.use_fake_user)
                                  for block in bpy.data.user_map()), key=lambda row: row['native_pointer'])}
            public_observed = verifier.public(observed)
            observed_bytes = json.dumps(public_observed, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
            observed_path = output / 'fresh_live_readonly.json'
            observed_path.write_bytes(observed_bytes)
            report['fresh_live_readonly'] = {'path': str(observed_path), 'sha256': hashlib.sha256(observed_bytes).hexdigest(), 'bytes': len(observed_bytes)}
            after = snapshots['fresh_full_after']
            for key in ('light', 'scenes', 'wm', 'context', 'pose', 'all_IDs'):
                require(encoded(public_observed[key]) == encoded(after[key]), 'Fresh live ' + key + ' changed after the actual full after snapshot.')
            require(encoded(public_observed['raw']) == encoded(snapshots['fresh_raw_Scene_WM_Object_Action_after']),
                    'The current raw properties changed after the actual full after snapshot.')
            identities = prior.native_identities(ctx, rig, light)
            require(encoded(identities) == encoded(strict['identities_before'])
                and bool(bpy.data.is_dirty) == strict['dirty_before'], 'Native identity or original dirty state changed.')
            for path in MUTE_PATHS:
                key = bpy.data.objects['Cosha'].data.shape_keys.key_blocks[path[-2]]
                require(key.mute is False, 'The current authenticated Forearm output is no longer restored.')
            require(ctx.scene.get(ft.LOCK_KEY) is False
                and ctx.window_manager.character_designer_dress_wiggle_advanced is False,
                'The two qualified runtime/default metadata values changed.')
            for row in inputs.values():
                prior.pin(row['path'], row['sha256'])
            for name, expected in manifest['files'].items():
                prior.pin(installed / name, expected)
            report.update(completed=True, phase='completed_qualified_recovery_readonly',
                qualified_preservation_verified=True, fresh_live_read_scope_exact=True,
                natural_registration_timer_completed_once=True, Forearm_lifecycle_settled=True,
                dirty_before=strict['dirty_before'], dirty_after=bool(bpy.data.is_dirty),
                identities_before=strict['identities_before'], identities_after=identities, native_identities_exact=True,
                before_light_signature=strict['before_light_signature'], after_light_signature=light.digest(observed['light']),
                original_disk_unchanged=True, input_files_unchanged=True)
    except Exception as error:
        report.update(completed=False, phase='qualification_live_check_failed', error=type(error).__name__ + ': ' + str(error),
                      traceback=traceback.format_exc())
    write()
    return {'completed': report['completed'], 'report': str(report_path), 'error': report.get('error')}
