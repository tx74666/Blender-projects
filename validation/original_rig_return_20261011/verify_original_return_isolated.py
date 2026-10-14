"""Audit Original -> Controls on a disposable current-artist snapshot only.

Run with Blender 5.2, not against the open artist process. This script refuses
X.blend, imports the installed CD, verifies its recorded runtime hashes, and
stops before Original.leave if the strict saved native Rest proof fails. The
actual packet, rest, scene units, size guard and ownership guards stay intact.
"""

import argparse
import copy
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import traceback

import bpy


EVIDENCE = Path(__file__).resolve().parent
ARTIST = EVIDENCE.parents[1] / 'X.blend'


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def within_evidence(path):
    path = Path(path).resolve()
    if not path.is_relative_to(EVIDENCE) or path == ARTIST.resolve():
        raise ValueError('All disposable blend/report paths must remain in this evidence directory.')
    return path


def plain(value):
    if isinstance(value, bpy.types.ID):
        return {'id_type': value.bl_rna.identifier, 'name': value.name_full}
    if type(value) in (str, int, float, bool) or value is None:
        return value
    if hasattr(value, '__len__'):
        try:
            return [plain(item) for item in value]
        except TypeError:
            pass
    return repr(value)


def fields(owner):
    result = {}
    for prop in owner.bl_rna.properties:
        if prop.identifier == 'rna_type' or prop.is_readonly or prop.type == 'COLLECTION':
            continue
        result[prop.identifier] = plain(getattr(owner, prop.identifier))
    return result


def graph_state(rig):
    constraints = {}
    orders = {}
    for pb in rig.pose.bones:
        orders[pb.name] = [con.name for con in pb.constraints]
        for con in pb.constraints:
            constraint_fields = fields(con)
            # Blender 5.2 RNA exposes enabled as the negative alias of mute;
            # both use CONSTRAINT_OFF. Keep both fields and prove the alias,
            # rather than ignoring independent activation-state differences.
            if ('enabled' in constraint_fields and 'mute' in constraint_fields
                    and constraint_fields['enabled'] != (not constraint_fields['mute'])):
                raise AssertionError('Constraint enabled/mute alias differs: ' + pb.name + '/' + con.name)
            constraints[pb.name + '\0' + con.name] = {'type': con.type, 'fields': constraint_fields}
    drivers = []
    for curve in rig.animation_data.drivers if rig.animation_data else ():
        drivers.append({'path': curve.data_path, 'index': curve.array_index,
                        'curve': fields(curve), 'driver': fields(curve.driver),
                        'variables': [{'fields': fields(var),
                                       'targets': [fields(target) for target in var.targets]}
                                      for var in curve.driver.variables],
                        'modifiers': [fields(modifier) for modifier in curve.modifiers],
                        'keys': [{'co': list(point.co), 'left': list(point.handle_left),
                                  'right': list(point.handle_right), 'fields': fields(point)}
                                 for point in curve.keyframe_points]})
    return {'constraints': constraints, 'constraint_orders': orders, 'drivers': drivers}


def differences(before, after, path='graph'):
    changes = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            if key not in before or key not in after:
                changes.append({'path': path + '[' + repr(key) + ']',
                                'before': before.get(key), 'after': after.get(key)})
            else:
                changes.extend(differences(before[key], after[key], path + '[' + repr(key) + ']'))
    elif isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            changes.append({'path': path + '.length', 'before': len(before), 'after': len(after)})
        for index, (left, right) in enumerate(zip(before, after)):
            changes.extend(differences(left, right, path + '[' + str(index) + ']'))
    elif before != after:
        changes.append({'path': path, 'before': before, 'after': after})
    return changes


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode('utf-8')).hexdigest()


def mutation_signature(rig, ua, original):
    ad = rig.animation_data
    return {'graph': graph_state(rig), 'rest': ua._rest_state(rig.data),
            'channels': original._channels(rig), 'world': [list(row) for row in rig.matrix_world],
            'session': rig.get(original.SESSION),
            'action': ad.action.name_full if ad and ad.action else None,
            'use_nla': ad.use_nla if ad else None,
            'frame': bpy.context.scene.frame_current_final,
            'blocks': {kind: sorted(block.name_full for block in getattr(bpy.data, kind))
                       for kind in ('objects', 'armatures', 'actions')}}


def skeleton_diagnostics(rig, packet, unit_scale, control_names):
    """Read-only diagnostics, never a replacement Mapping or relaxed guard."""
    import numpy as np
    names = {bone['name']: index for index, bone in enumerate(packet['bones'])
             if bone['name'] in rig.data.bones}
    parents = []
    for name, index in names.items():
        parent_index = packet['bones'][index]['parent']
        while parent_index >= 0 and packet['bones'][parent_index]['name'] not in names:
            parent_index = packet['bones'][parent_index]['parent']
        incoming = packet['bones'][parent_index]['name'] if parent_index >= 0 else None
        actual = rig.data.bones[name].parent
        skipped = []
        while actual and actual.name in control_names:
            skipped.append(actual.name)
            actual = actual.parent
        target = actual.name if actual else None
        parents.append({'bone': name, 'packet_parent': incoming, 'native_parent': target,
                        'skipped_validated_control_parents': skipped, 'matches': incoming == target})
    bound = [(name, index) for name, index in names.items()
             if packet['bones'][index]['restSource'] == 'bindpose']
    from character_designer import unity_animation as ua
    source = np.asarray([tuple(ua._matrix(packet['bones'][index]['rest'], name).translation)
                         for name, index in bound], dtype=np.float64)
    dest = np.asarray([tuple((rig.matrix_world @ rig.data.bones[name].matrix_local).translation)
                       for name, index in bound], dtype=np.float64)
    sc, dc = source.mean(axis=0), dest.mean(axis=0)
    x, y = source - sc, dest - dc
    u, singular, vt = np.linalg.svd(x.T @ y)
    rotation = u @ vt
    scale = float(singular.sum() / (x * x).sum())
    translation = dc - sc @ rotation * scale
    errors = np.linalg.norm(source @ rotation * scale + translation - dest, axis=1) * unit_scale
    return {'scope': 'Named bind head fit and parent comparison only; does not prove graph/sample/skin compatibility.',
            'mapped_count': len(names), 'missing_packet_bones': [bone['name'] for bone in packet['bones']
                                                               if bone['name'] not in names],
            'bind_count': len(bound), 'conversion_scale': scale, 'unit_scale': unit_scale,
            'scale_times_unit_scale': scale * unit_scale,
            'strict_size_guard_would_pass': math.isfinite(scale) and abs(scale * unit_scale - 1.0) <= 0.002,
            'max_bind_head_error_mm': float(np.max(errors)) * 1000.0,
            'rms_bind_head_error_mm': float(np.sqrt(np.mean(errors * errors))) * 1000.0,
            'native_parents': parents,
            'all_native_parents_match': all(item['matches'] for item in parents)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--package', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--runtime-evidence', default=str(EVIDENCE / 'live_control_graph.json'))
    parser.add_argument('--output-blend')
    parser.add_argument('--addon-root', help='Pinned isolated add-on directory; must match live version and module hashes.')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    input_path = within_evidence(args.input)
    report_path = within_evidence(args.report)
    output_path = within_evidence(args.output_blend) if args.output_blend else None
    if output_path == input_path:
        raise ValueError('The result file must differ from the input snapshot.')
    source_sha = file_hash(input_path)
    package_sha = file_hash(args.package)
    report = {'input_snapshot': str(input_path), 'input_sha256': source_sha,
              'packet': str(Path(args.package).resolve()), 'packet_sha256': package_sha,
              'audit_completed': False, 'original_leave_completed': False,
              'strict_rest_preflight_passed': False, 'model_repair_attempted': False,
              'scope': 'Official Original return only in disposable file; actual strict mapping without guard bypass.'}
    try:
        # Use the verified installed add-on, never the canonical working tree.
        installed = within_evidence(args.addon_root) if args.addon_root else Path(bpy.utils.user_resource('SCRIPTS')) / 'addons'
        if str(installed) not in sys.path:
            sys.path.insert(0, str(installed))
        cd = importlib.import_module('character_designer')
        if not Path(cd.__file__).resolve().is_relative_to(installed.resolve()):
            raise RuntimeError('Character Designer was not imported from the verified add-on root.')
        ua = importlib.import_module('character_designer.unity_animation')
        controls = importlib.import_module('character_designer.unity_animation_controls')
        original = importlib.import_module('character_designer.body_original_mode')
        inv_module = importlib.import_module('character_designer.forearm_original_inventory')
        runtime = json.loads(Path(args.runtime_evidence).read_text(encoding='utf-8-sig'))
        report['blender_version'] = bpy.app.version_string
        report['addon_version'] = list(cd.bl_info['version'])
        report['addon_path'] = str(Path(cd.__file__).resolve())
        if bpy.app.version[:2] != (5, 2) or report['addon_version'] != runtime['addon_version']:
            raise RuntimeError('Blender/add-on versions differ from the captured live runtime.')
        report['module_sha256'] = {}
        for name, expected in runtime['module_sha256'].items():
            module = importlib.import_module(name)
            actual = file_hash(module.__file__)
            report['module_sha256'][name] = actual
            if actual != expected:
                raise RuntimeError('Installed module differs from live evidence: ' + name)
        # Registration is process-local. It supplies the official persisted RNA
        # services; it cannot touch the user's separate open Blender process.
        cd.register()
        bpy.ops.wm.open_mainfile(filepath=str(input_path), use_scripts=False, load_ui=False)
        rig = bpy.data.objects.get('CoshaRig')
        scene = bpy.data.scenes.get('Scene')
        if rig is None or scene is None or rig.name not in scene.objects:
            raise RuntimeError('Snapshot must contain the original Scene and CoshaRig with dependencies.')
        bpy.context.window.scene = scene
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.context.view_layer.update()
        report['scene'] = scene.name
        report['frame'] = scene.frame_current_final
        report['original_session_present'] = original.active(rig)
        if not original.active(rig):
            raise RuntimeError('Snapshot does not contain the current active Original transaction.')
        saved = json.loads(rig[original.SESSION])
        report['original_saved_constraint_count'] = len(saved['constraints'])
        before_read = mutation_signature(rig, ua, original)
        original._validate_session_rest(rig, saved)
        report['strict_rest_preflight_passed'] = True
        inventory = inv_module.validate(rig)
        report['original_ownership_preflight'] = {'limbs': len(inventory['rigs']),
                                                  'records': len(inventory['records']), 'passed': True}
        if before_read != mutation_signature(rig, ua, original):
            raise AssertionError('Read-only Original preflight changed the snapshot.')
        all_rigs = [obj for obj in scene.objects if obj.type == 'ARMATURE']
        rest_before = {obj.name: ua._rest_state(obj.data) for obj in all_rigs}
        graph_before = {obj.name: graph_state(obj) for obj in all_rigs}
        expected = copy.deepcopy(graph_before)
        for entry in saved['constraints']:
            constraint_fields = expected[rig.name]['constraints'][entry['bone'] + '\0' + entry['name']]['fields']
            constraint_fields['mute'] = entry['mute']
            if 'enabled' in constraint_fields:
                constraint_fields['enabled'] = not entry['mute']
        report['constraint_enabled_alias_proof'] = {
            'source': 'https://raw.githubusercontent.com/blender/blender/v5.2.0/source/blender/makesrna/intern/rna_constraint.cc',
            'source_lines': '3447-3453',
            'meaning': 'enabled is the negative RNA alias of mute over CONSTRAINT_OFF.',
            'audit_rule': 'Both fields stay in graph comparisons. Only exact saved Original entries expect the paired change; every captured constraint proves enabled == not mute.'}
        dress_targets = original.dress_pose._resolve(bpy.context, rig, saved.get('dress_edit', []))
        dress_allowed = {}
        for entry, target, _source, _record, relations in dress_targets:
            for pb, con, _rotation in relations:
                dress_allowed[(target.name, pb.name + '\0' + con.name)] = entry['constraints'][pb.name]['mix_mode']
        native_before = {name: rig.pose.bones[name].matrix.copy() for name in saved['rest']}
        report['original_leave_result'] = bool(original.leave(bpy.context, rig))
        report['original_leave_completed'] = not original.active(rig)
        rest_after = {obj.name: ua._rest_state(obj.data) for obj in all_rigs}
        report['all_armature_rest_unchanged'] = rest_before == rest_after
        if rest_before != rest_after:
            raise AssertionError('Official Original return changed Armature Rest data.')
        graph_after = {obj.name: graph_state(obj) for obj in all_rigs}
        for (obj_name, key), restored_mode in dress_allowed.items():
            mode = graph_after[obj_name]['constraints'][key]['fields']['mix_mode']
            if mode not in (restored_mode, 'BEFORE_FULL'):
                raise AssertionError('Dress return produced an unrecorded mix mode.')
            expected[obj_name]['constraints'][key]['fields']['mix_mode'] = mode
        report['official_return_graph_changes'] = differences(graph_before, graph_after)
        report['unexpected_return_graph_changes'] = differences(expected, graph_after)
        report['graph_preserved_except_recorded_original_return_fields'] = expected == graph_after
        if expected != graph_after:
            raise AssertionError('Official return changed unapproved constraint/driver graph fields.')
        pose_error = max(max(abs(matrix[row][col] - rig.pose.bones[name].matrix[row][col])
                             for row in range(4) for col in range(4))
                         for name, matrix in native_before.items())
        report['maximum_native_pose_matrix_error'] = pose_error
        if pose_error > 4.0e-4:
            raise AssertionError('Official return failed the native pose preservation bound.')
        packet = ua.load_package(args.package)
        names = {bone['name'] for bone in packet['bones'] if bone['name'] in rig.data.bones}
        guard_state = mutation_signature(rig, ua, original)
        plan = None
        try:
            plan = controls.build_plan(rig, names)
            report['control_plan'] = {'passed': True, 'control_count': len(plan.control_names) if plan else 0}
        except Exception as exc:
            report['control_plan'] = {'passed': False, 'error_type': type(exc).__name__, 'error': str(exc)}
        try:
            mapping = ua._mapping(rig, packet, scene.unit_settings.scale_length)
            report['actual_mapping'] = {'compatible': True, 'mapped_bones': len(mapping.indices),
                                        'error_metres': mapping.error_metres}
        except Exception as exc:
            report['actual_mapping'] = {'compatible': False, 'error_type': type(exc).__name__, 'error': str(exc)}
        if guard_state != mutation_signature(rig, ua, original):
            raise AssertionError('Read-only build_plan/_mapping changed the snapshot.')
        report['mapping_state_unchanged'] = True
        control_names = set(plan.control_names) if plan else {bone.name for bone in inventory['bones']}
        if plan is None:
            from character_designer import limb_ik
            control_names.update(bone.name for bone in rig.data.bones
                                 if bone.get(limb_ik.OWNER_KEY) in limb_ik.GENERATED_CONTROL_OWNERS)
        report['independent_bind_diagnostics'] = skeleton_diagnostics(
            rig, packet, scene.unit_settings.scale_length, control_names)
        report['audit_completed'] = True
        if output_path:
            result = bpy.ops.wm.save_as_mainfile(filepath=str(output_path), check_existing=False, copy=True)
            report['isolated_output'] = str(output_path)
            report['isolated_save_result'] = sorted(result)
            if 'FINISHED' not in result or not output_path.is_file():
                raise RuntimeError('Blender did not confirm the isolated output save.')
    except Exception as exc:
        report['failure_type'] = type(exc).__name__
        report['failure'] = str(exc)
        report['traceback'] = traceback.format_exc()
    finally:
        report['input_file_unchanged'] = file_hash(input_path) == source_sha
        report['packet_file_unchanged'] = file_hash(args.package) == package_sha
        report['audit_completed'] = bool(report['audit_completed'] and report['input_file_unchanged']
                                          and report['packet_file_unchanged'] and 'failure' not in report)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        print('ORIGINAL_RETURN_ISOLATED_RESULT ' + json.dumps(
            {key: value for key, value in report.items()
             if key not in {'traceback', 'official_return_graph_changes', 'independent_bind_diagnostics'}},
            ensure_ascii=False))
    if not report['audit_completed']:
        raise RuntimeError(report.get('failure', 'Incomplete isolated audit.'))


if __name__ == '__main__':
    main()
