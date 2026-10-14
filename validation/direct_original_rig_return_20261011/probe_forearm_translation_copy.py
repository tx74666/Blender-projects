"""Root-launched isolated copy/connection Forearm probe; no animation bake/save."""

import argparse
from array import array
import hashlib
import importlib
import json
from pathlib import Path
import sys
import traceback

import bpy


EVIDENCE = Path(__file__).resolve().parent


def file_hash(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            result.update(chunk)
    return result.hexdigest()


def safe_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(EVIDENCE) or path.name.casefold() == 'x.blend':
        raise ValueError('Use only task-owned isolated input/report paths, never artist X.blend.')
    return path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def key_rows(forearm, obj):
    result = {}
    for side, record in forearm._records(obj).items():
        key = forearm._managed_key(obj, side, record)
        coordinates = array('f', [0.]) * (len(key.data) * 3)
        key.data.foreach_get('co', coordinates)
        result[side] = {'name': key.name, 'value': key.value, 'mute': key.mute,
                        'geometry_sha256': hashlib.sha256(coordinates.tobytes()).hexdigest()}
    return result


def signatures(forearm, rig, records):
    result = {}
    for side, record in records.items():
        actual = forearm._rest_signature(rig, record['chain'])
        saved = record['rest']
        result[side] = {'chain': record['chain'], 'saved': saved, 'actual': actual,
                        'exact_match': saved == actual,
                        'maximum_delta': max(abs(a - b) for old, new in zip(saved, actual)
                                             for a, b in zip(old[1], new[1]))}
    return result


def profile(record):
    # Saved sample positions and support are included: this probe should show
    # explicitly whether native rebind changes them, without choosing a policy.
    return {key: value for key, value in record.items()
            if key not in {'rest', 'target', 'topology', 'support_topology'}}


def runtime_once(forearm, obj, rig, report):
    old = forearm._records(obj)
    result = {'before_signatures': signatures(forearm, rig, old),
              'keys_before': key_rows(forearm, obj), 'record_sha256_before': digest(old)}
    report[obj.name] = result
    try:
        prepared = forearm._prepare_runtime_records(obj)
        result['prepared_record_changes'] = {side: sorted(key for key in old[side].keys() | fresh.keys()
            if old[side].get(key) != fresh.get(key)) for side, fresh in prepared.items() if side in old}
        result['profile_exactly_preserved'] = {side: profile(old[side]) == profile(fresh)
            for side, fresh in prepared.items() if side in old}
        result['prepared_signatures'] = signatures(forearm, rig, prepared)
        # Exercise the supported atomic rebind/output path even if preparation
        # returns unchanged records; nothing is published outside this process.
        forearm._apply_runtime_records(obj, prepared, bpy.context.evaluated_depsgraph_get())
        committed = forearm._records(obj)
        result.update(passed=True, after_signatures=signatures(forearm, rig, committed),
                      keys_after=key_rows(forearm, obj), record_sha256_after=digest(committed),
                      runtime_error=forearm._ERRORS.get(obj.name))
    except Exception as exc:
        result.update(passed=False, error_type=type(exc).__name__, error=str(exc),
                      traceback=traceback.format_exc())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--addon-root', required=True)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--packet', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source, output = safe_path(args.input), safe_path(args.report)
    if source == output:
        raise ValueError('Report must differ from the input file.')
    original_hash, packet_hash = file_hash(source), file_hash(args.packet)
    report = {'completed': False, 'schema': 'x.validation.forearm-translation-copy/1',
              'input': str(source), 'input_sha256': original_hash, 'packet_sha256': packet_hash,
              'scope': 'Disposable backup only. Official adoption then exact translation copy; no clip bake, save or artist mutation.'}
    try:
        root = safe_path(args.addon_root)
        sys.path.insert(0, str(root))
        cd = importlib.import_module('character_designer')
        if not Path(cd.__file__).resolve().is_relative_to(root):
            raise RuntimeError('Unexpected add-on runtime root.')
        cd.register()
        ua = importlib.import_module('character_designer.unity_animation')
        original = importlib.import_module('character_designer.body_original_mode')
        worklist = importlib.import_module('character_designer.animation_worklist')
        target = importlib.import_module('character_designer.animation_worklist_target')
        forearm = importlib.import_module('character_designer.forearm_twist')
        report['runtime'] = {'version': list(cd.bl_info['version']), 'blender': bpy.app.version_string,
            'module_sha256': {module.__name__: file_hash(module.__file__)
                              for module in (cd, ua, original, target, forearm)}}
        bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False, load_ui=False)
        scene, rig = bpy.data.scenes.get('Scene'), bpy.data.objects.get('CoshaRig')
        if not scene or not rig or rig.name not in scene.objects:
            raise RuntimeError('Backup lacks original Scene/CoshaRig.')
        bpy.context.window.scene = scene
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        rig.hide_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        skins = [obj for obj in scene.objects if obj.type == 'MESH' and forearm.RECORD_KEY in obj
                 and any(modifier.type == 'ARMATURE' and modifier.object is rig for modifier in obj.modifiers)]
        if not skins:
            raise RuntimeError('Expected calibrated Forearm skin meshes in isolated original Scene.')
        report['loaded_signatures'] = {obj.name: signatures(forearm, rig, forearm._records(obj)) for obj in skins}
        report['runtime_errors_loaded'] = dict(forearm._ERRORS)
        with forearm.defer_runtime(bpy.context, flush_on_exit=False):
            if original.active(rig):
                original._validate_session_rest(rig)
                if not original.leave(bpy.context, rig):
                    raise RuntimeError('Official Original leave failed.')
            report['after_official_leave_signatures'] = {
                obj.name: signatures(forearm, rig, forearm._records(obj)) for obj in skins}
            report['original_data_runtime'] = {}
            for obj in skins:
                runtime_once(forearm, obj, rig, report['original_data_runtime'])
            if not all(row['passed'] for row in report['original_data_runtime'].values()):
                raise RuntimeError('Forearm baseline fails before the translation copy.')
            worklist.connect(bpy.context, args.workspace)
            target.adopt_main_rig(bpy.context)
            packet = ua.load_package(args.packet)
            mapping = ua._mapping(rig, packet, scene.unit_settings.scale_length)
            authored = set(mapping.indices) - set(mapping.controls.delegated_names)
            original_data = rig.data
            before_rest = ua._rest_state(original_data)
            copied = original_data.copy()
            copied.name = 'CD Forearm Translation Probe'
            ua._swap_armature_data(bpy.context, rig, copied, allow_joint_translation=True,
                                   joint_translation_names=authored)
            # Same managed motion-data receipt update as restore_import_preview;
            # its authentication must pass before any runtime record recapture.
            record = target._load(rig)
            record['motion_data'], record['motion_rest'] = copied, ua._rest_state(copied)
            target._store(rig, record)
            view = target.control_rest_view(rig)
            if view is None:
                raise RuntimeError('Translation copy lacks the authenticated adoption Rest view.')
            report['adoption_rest_view_authenticated'] = True
            report['protected_original_data_unchanged'] = ua._matches_rest_state(original_data, before_rest)
            report['mapped_bind_count'], report['authored_count'] = len(mapping.indices), len(authored)
            report['connected_flags_changed'] = sorted(name for name in authored
                if original_data.bones[name].use_connect != copied.bones[name].use_connect)
            report['motion_copy_signatures'] = {
                obj.name: signatures(forearm, rig, forearm._records(obj)) for obj in skins}
            report['translation_copy_runtime'] = {}
            for obj in skins:
                runtime_once(forearm, obj, rig, report['translation_copy_runtime'])
            report['runtime_errors_final'] = dict(forearm._ERRORS)
        report['completed'] = all(row['passed'] for row in report['translation_copy_runtime'].values())
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
    finally:
        report['input_file_unchanged'] = file_hash(source) == original_hash
        report['packet_file_unchanged'] = file_hash(args.packet) == packet_hash
        output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
        print('FOREARM_TRANSLATION_COPY_PROBE ' + json.dumps({
            'completed': report['completed'], 'report': str(output), 'error': report.get('error'),
            'copy_runtime': {name: {'passed': row.get('passed'), 'error': row.get('error'),
                                    'profile_exactly_preserved': row.get('profile_exactly_preserved')}
                             for name, row in report.get('translation_copy_runtime', {}).items()}}))
    if not report['completed']:
        raise AssertionError(report.get('error', 'Translation runtime probe failed.'))


if __name__ == '__main__':
    main()
