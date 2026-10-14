"""Read two pinned owned files without CD registration; retain full metadata/diff.

This compares reopened files only. The failing live pre-Close baseline was not
retained, so an empty diff cannot establish that the actual failure disappeared.
No save, scene edit, frame seek, add-on registration or original X open.
"""
import argparse
import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback
from types import MethodType, SimpleNamespace

ROUND = Path(__file__).resolve().parent
RECOVERY = ROUND / 'native_original20_r13_12/unverified_native12_quit_recovery.blend'
RECOVERY_SHA = 'd4cb2b7c8fb4667baa11e9f6cd7956076ef010f511069ea9c912a01e3d2dc5a6'
CLOSED = ROUND / 'close_continuation_07736_02/original20_controls_owned.blend'
CLOSED_SHA = '1a88703e43f1af5804b62356b460eeb4d6388fea32334bd5ed91ab50e306876a'
RUNNER = ROUND / 'validate_original20_close_continuation_07736b.py'
RUNNER_SHA = '8a60aff37b890a63c28b671347f1842a1a24a7369ae868d20efd047f36b0fbe1'
HELPER = ROUND / 'original_cosha_control_round.py'
HELPER_SHA = '7098c3b20a5a115423913ce91268cc4fd9a57adab9973c9c6c2000e2afd2d468'
FAILED_REPORT = ROUND / 'close_continuation_07736_02/original20_recovery_gun_undo_report.json'
FAILED_REPORT_SHA = '9d553efe9ad82505b26a82fda4eaa086f511b4b8d39a529bb7240316d9c8e763'
FAILED_RELEASE = ROUND / 'resource_release_X_CLOSE_CONTINUATION_07736_02.json'
FAILED_RELEASE_SHA = 'df7250fe550113f8abd09c94659a9eec97717d80ebbedef3e7e0fdc667e2c845'
RECORD = 'character_designer_composition_weapon_v1'
OWNER = 'character_designer_composition_weapon_owner'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path, expected):
    path = Path(path).resolve()
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    require(actual == expected.lower(), 'Immutable input changed: ' + str(path))
    return {'path': str(path), 'sha256': actual, 'bytes': len(data)}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def saved(path, value):
    require(not path.exists(), 'Never overwrite diagnostic output: ' + str(path))
    write(path, value)
    return pin(path, hashlib.sha256(path.read_bytes()).hexdigest())


def exact_metadata_reader(bpy):
    """Compile only the exact five serializer/metadata definitions, no modules."""
    from mathutils import Color, Euler, Matrix, Quaternion, Vector
    helper_tree = ast.parse(HELPER.read_text(encoding='utf-8'))
    cls = next(node for node in helper_tree.body if isinstance(node, ast.ClassDef) and node.name == 'OriginalRound')
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in ('id', 'plain', 'rna')]
    require({node.name for node in methods} == {'id', 'plain', 'rna'}, 'Pinned helper methods are incomplete.')
    ns = {'Path': Path, 'math': math, 'require': require, 'digest': digest, 'bpy': bpy,
        'Color': Color, 'Euler': Euler, 'Matrix': Matrix, 'Quaternion': Quaternion, 'Vector': Vector}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(HELPER), 'exec'), ns)
    plain = ns['plain']
    probe = SimpleNamespace(bpy=bpy)
    for name in ('id', 'plain', 'rna'):
        setattr(probe, name, MethodType(ns[name], probe))
    ns.update(probe=probe, helper=SimpleNamespace(OriginalRound=SimpleNamespace(plain=plain)))
    runner_tree = ast.parse(RUNNER.read_text(encoding='utf-8'))
    main = next(node for node in runner_tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    selected = [node for node in main.body if isinstance(node, ast.FunctionDef) and node.name in ('exact_plain', 'metadata')]
    require({node.name for node in selected} == {'exact_plain', 'metadata'}, 'Pinned runner serializer/metadata definitions are incomplete.')
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(RUNNER), 'exec'), ns)
    probe.plain = MethodType(ns['exact_plain'], probe)
    return ns['metadata'], probe


def differences(before, after, path=()):
    """Retain every differing field, with exact values and no ignored keys."""
    if type(before) is not type(after):
        return [{'path': list(path), 'kind': 'type', 'before': before, 'after': after}]
    rows = []
    if isinstance(before, dict):
        for key in sorted(before.keys() | after.keys()):
            if key not in before:
                rows.append({'path': list(path + (key,)), 'kind': 'added', 'after': after[key]})
            elif key not in after:
                rows.append({'path': list(path + (key,)), 'kind': 'removed', 'before': before[key]})
            else:
                rows.extend(differences(before[key], after[key], path + (key,)))
    elif isinstance(before, list):
        for index in range(max(len(before), len(after))):
            if index >= len(before):
                rows.append({'path': list(path + (index,)), 'kind': 'added', 'after': after[index]})
            elif index >= len(after):
                rows.append({'path': list(path + (index,)), 'kind': 'removed', 'before': before[index]})
            else:
                rows.extend(differences(before[index], after[index], path + (index,)))
    elif before != after:
        rows.append({'path': list(path), 'kind': 'value', 'before': before, 'after': after})
    return rows


def locate_rna_property(bpy, rig, path):
    """Annotate only directly traceable modifier/color paths in the second file."""
    try:
        if len(path) >= 4 and path[0] == 'objects' and path[2] == 'modifiers':
            value = bpy.data.objects[path[1]].modifiers[path[3]]
            rest = path[4:]
        elif len(path) >= 2 and path[0] in ('bone_colors', 'pose_colors'):
            bones = rig.data.bones if path[0] == 'bone_colors' else rig.pose.bones
            value, rest = bones[path[1]].color, path[2:]
        else:
            return {'located': False, 'reason': 'Metadata identity/domain field, not a directly traversed RNA property.'}
        last = None
        for token in rest:
            if isinstance(value, bpy.types.ID):
                break  # Metadata deliberately treats ID identity as a terminal.
            if type(token) is int:
                value = value[token]
                continue
            prop = value.bl_rna.properties.get(token)
            require(prop is not None, 'No corresponding RNA property: ' + token)
            last = {'located': True, 'observed_in': 'closed_saved_clone',
                'owner_rna_type': value.bl_rna.identifier, 'identifier': prop.identifier,
                'type': prop.type, 'is_readonly': prop.is_readonly}
            value = getattr(value, token)
        return last or {'located': False, 'reason': 'Diff identifies an RNA container without a terminal property.'}
    except Exception as exc:
        return {'located': False, 'reason': type(exc).__name__ + ': ' + str(exc)}


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--output-root', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = Path(args.output_root).resolve()
    require(output != ROUND and output.is_relative_to(ROUND) and output.is_dir() and not any(output.iterdir()),
        'Use a new empty owned diagnostic output directory.')
    inputs = {key: pin(path, expected) for key, path, expected in (
        ('source', __file__, args.source_sha256), ('recovery', RECOVERY, RECOVERY_SHA),
        ('closed_clone', CLOSED, CLOSED_SHA), ('runner', RUNNER, RUNNER_SHA), ('helper', HELPER, HELPER_SHA),
        ('failed_report', FAILED_REPORT, FAILED_REPORT_SHA), ('failed_release', FAILED_RELEASE, FAILED_RELEASE_SHA))}
    failed = json.loads(FAILED_REPORT.read_text(encoding='utf-8'))
    release = json.loads(FAILED_RELEASE.read_text(encoding='utf-8'))
    require(failed['completed'] is False and failed['stage'] == 'reopened_readback'
        and failed['error'] == 'RuntimeError: Close/reopen changed existing IDs/colors/modifiers.'
        and failed['saved_clone']['sha256'] == CLOSED_SHA and failed['public_Close_success'] is True
        and failed['extra_Scene_reference_Close_rejected_without_mutation'] is True
        and release['retained_handle_natural_exit'] is True and release['native_exit_code'] == 0
        and release['owned_native_gone'] is True and release['process_termination_performed'] is False
        and release['owned_pid'] == failed['pid'] and release['report']['sha256'] == FAILED_REPORT_SHA,
        'The diagnostic must remain bound to the actual failed reopen after successful Close/Save.')
    import bpy
    require(bpy.app.background and not bpy.data.filepath and tuple(bpy.app.version[:2]) == (5, 2)
        and not bpy.context.preferences.filepaths.use_scripts_auto_execute,
        'Use a factory-startup background Blender 5.2 with autoexecution disabled.')
    def no_cd():
        require(not any(name == 'character_designer' or name.startswith('character_designer.') for name in sys.modules),
            'Character Designer must not be imported or registered by this diagnostic.')
    no_cd()
    report = {'schema': 'x.validation.original20-close-metadata-diagnostic/1', 'completed': False,
        'pid': os.getpid(), 'source_inputs': inputs, 'native_execution_performed': True,
        'diagnostic_only': True, 'candidate_registered': False, 'scene_saved': False, 'scene_edits_performed': False,
        'original_X_opened': False, 'frame_seek_performed': False, 'live_pre_Close_baseline_measured': False,
        'reopen_failure_resolved': False,
        'scope': 'Two pinned owned files reopened without CD; exact same serializer/metadata function as failed runner. No new ignored fields.',
        'limitation': 'The failing live baseline was not retained. An empty reopened-file diff cannot reproduce or resolve the actual failure.'}
    report_path = output / 'close_metadata_diagnostic_report.json'
    write(report_path, report)

    @contextmanager
    def timed(label):
        row = {'operation': label, 'started_utc': datetime.now(timezone.utc).isoformat(), 'completed': False}
        report.setdefault('operations', []).append(row)
        write(report_path, report)
        print('CLOSE_METADATA_BEGIN ' + label, flush=True)
        start = time.perf_counter()
        try:
            yield
            row['completed'] = True
        finally:
            row.update(ended_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter() - start)
            write(report_path, report)
            print('CLOSE_METADATA_END ' + json.dumps(row), flush=True)

    try:
        metadata, probe = exact_metadata_reader(bpy)
        names = None
        values = {}
        for label, source in (('clean_D4CB', inputs['recovery']), ('closed_saved_clone', inputs['closed_clone'])):
            report['stage'] = label
            with timed(label + ' open read-only'):
                result = bpy.ops.wm.open_mainfile('EXEC_DEFAULT', False, filepath=source['path'], use_scripts=False, load_ui=False)
            require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == Path(source['path']), 'Pinned owned file did not open.')
            no_cd()
            rig, scene = bpy.data.objects.get('CoshaRig'), bpy.data.scenes.get('Scene')
            require(rig is not None and scene is not None and rig.type == 'ARMATURE' and scene.objects.get(rig.name) == rig,
                'Expected original Scene/CoshaRig identity is missing.')
            record = rig.get(RECORD)
            if label == 'clean_D4CB':
                require(record is not None and record.get('scene') == scene, 'Clean recovery lacks its owning weapon record.')
                owned = tuple(record['objects'].values())
                require(owned and all(isinstance(obj, bpy.types.Object) and obj.get(OWNER) == record['owner'] for obj in owned)
                    and set(record['collection'].objects) == set(owned), 'Weapon exclusion must follow exact record-owned Objects.')
                names = sorted(obj.name for obj in bpy.data.objects if obj not in set(owned))
                report['excluded_record_owned_weapon_objects'] = [probe.id(obj) for obj in owned]
                report['record_owner'] = record['owner']
                report['protected_object_names'] = names
            else:
                require(record is None, 'The saved closed clone still has a weapon record.')
                report['closed_object_domain'] = sorted(obj.name for obj in bpy.data.objects)
            with timed(label + ' exact metadata read'):
                values[label] = metadata(rig, names)
            report[label + '_metadata'] = saved(output / (label + '_metadata.json'), values[label])
            report[label + '_metadata_sha256'] = digest(values[label])
            write(report_path, report)
        with timed('complete recursive field diff'):
            diff = differences(values['clean_D4CB'], values['closed_saved_clone'])
            for row in diff:
                row['rna_property'] = locate_rna_property(bpy, rig, row['path'])
            report['differences'] = saved(output / 'metadata_diff.json', diff)
            report['difference_count'] = len(diff)
            report['reopened_files_metadata_exact'] = not diff
            report['observation'] = ('No difference between the two reopened-file snapshots; actual live failure not reproduced.'
                if not diff else 'Reopened-file differences retained verbatim; no field has been ignored or qualified.')
        with timed('immutable source and blend pins after read'):
            for row in inputs.values(): pin(row['path'], row['sha256'])
        report['input_files_unchanged'] = True
        report['completed'] = True
    except Exception as exc:
        report.update(completed=False, error=type(exc).__name__ + ': ' + str(exc), traceback=traceback.format_exc())
        write(report_path, report)
        raise
    finally:
        write(report_path, report)
        print('CLOSE_METADATA_DIAGNOSTIC ' + json.dumps({'completed': report['completed'], 'report': str(report_path)}), flush=True)


if __name__ == '__main__':
    main()
