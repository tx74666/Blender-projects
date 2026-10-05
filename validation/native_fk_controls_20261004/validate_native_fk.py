"""Isolated real-X validation; writes an FK candidate, never the artist file.

Run canonical Blender in background with factory startup/disabled autoexec:
  --python validate_native_fk.py -- <this folder>/X_live_input.blend
"""
import ast
import datetime
import hashlib
import json
import math
import sys
import time
import traceback
from array import array
from pathlib import Path

import bpy
from mathutils import Quaternion

FOLDER = Path(__file__).resolve().parent
CANONICAL = Path(r'D:\MyRepository\Blender-addons-by-Randy\addons')
ARTIST = FOLDER.parents[1] / 'X.blend'
OUTPUT = FOLDER / 'validate_native_fk.json'
CANDIDATE = FOLDER / 'X_native_fk_candidate.blend'
PROBE = FOLDER.parent / 'original_calibration_20261004' / 'probe_current.py'
CHANNELS = ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')
POSE_TOLERANCE = 2e-4
SURFACE_TOLERANCE = 1e-4
REST_TOLERANCE = 2e-6

sys.path.insert(0, str(CANONICAL))
import character_designer
from character_designer import (body_calibration, body_original_mode, body_setup,
    body_setup_removal, bone_color_palette, control_pose_assets, forearm_twist,
    hair_bones_rig, limb_ik, limb_ik_fk, limb_ik_fk_batch, skirt_rig,
    spine_ik_fk, torso_controls)


def snapshot_helpers():
    """Reuse proven snapshot functions without executing probe imports/main."""
    wanted = {'sha_file', 'fingerprint', 'plain', 'custom', 'matrix', 'rna_fields',
              'data_hash', 'bulk', 'mesh_snapshot', 'bone_rest', 'curve_snapshot',
              'driver_snapshot', 'animation_snapshot', 'differences'}
    source = ast.parse(PROBE.read_text(encoding='utf-8-sig'), filename=str(PROBE))
    functions = [node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {node.name for node in functions} != wanted:
        raise RuntimeError('The read-only probe snapshot interface changed.')
    scope = {'bpy': bpy, 'math': math, 'hashlib': hashlib, 'json': json,
             'array': array, 'CHANNELS': CHANNELS, 'limb_ik': limb_ik}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(PROBE), 'exec'), scope)
    return {name: scope[name] for name in wanted}


H = snapshot_helpers()
plain, matrix = H['plain'], H['matrix']


def exact_diffs(old, new, path=''):
    """Return exact paths/values, including tiny numeric differences."""
    if type(old) != type(new):
        return [{'path': path, 'before': old, 'after': new}]
    if isinstance(old, dict):
        result = []
        for key in sorted(set(old) | set(new)):
            child = f'{path}.{key}' if path else str(key)
            if key not in old or key not in new:
                result.append({'path': child, 'before': old.get(key), 'after': new.get(key),
                               'missing': 'before' if key not in old else 'after'})
            else:
                result.extend(exact_diffs(old[key], new[key], child))
        return result
    if isinstance(old, list):
        if len(old) != len(new):
            return [{'path': path, 'before_count': len(old), 'after_count': len(new)}]
        return [entry for i, (a, b) in enumerate(zip(old, new))
                for entry in exact_diffs(a, b, f'{path}[{i}]')]
    return [] if old == new else [{'path': path, 'before': old, 'after': new}]


def retained_meshes(excluded):
    values = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.name in excluded:
            continue
        value = H['mesh_snapshot'](obj)
        # Modifier execution time is a read-only profiling measurement, not
        # artist data. The original helper intentionally exposes all RNA.
        for modifier in value['relationship']['armature_modifiers']:
            modifier['fields'].pop('execution_time', None)
        value['object_properties'] = H['custom'](obj)
        value['animation'] = H['animation_snapshot'](obj)
        value['key_animation'] = H['animation_snapshot'](obj.data.shape_keys) if obj.data.shape_keys else None
        values[obj.name] = value
    return values


def color(owner):
    value = owner.color
    return {'palette': value.palette, 'colored_constraints': value.custom.show_colored_constraints,
            'normal': list(value.custom.normal), 'select': list(value.custom.select),
            'active': list(value.custom.active)}


def constraint(con):
    fields = H['rna_fields'](con)
    for key in ('error_location', 'error_rotation'):
        fields.pop(key, None)  # Evaluated read-only solver diagnostics.
    return fields


def hair_dress_snapshot():
    result = {'rigs': {}, 'records': {}}
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            names = [bone.name for bone in obj.data.bones
                     if bone.get(hair_bones_rig.OWNER_KEY) == hair_bones_rig.OWNER_VALUE
                     or bone.get(skirt_rig.OWNER_KEY)]
            if names:
                result['rigs'][obj.name] = {
                    'rest': {name: H['bone_rest'](obj.data.bones[name]) for name in names},
                    'pose': {name: {'mode': obj.pose.bones[name].rotation_mode,
                                   'channels': {field: list(getattr(obj.pose.bones[name], field)) for field in CHANNELS},
                                   'properties': H['custom'](obj.pose.bones[name])}
                             for name in names},
                    'constraints': {name: [constraint(con) for con in obj.pose.bones[name].constraints]
                                    for name in names},
                    'colors': {name: {'bone': color(obj.data.bones[name]), 'pose': color(obj.pose.bones[name])}
                               for name in names}}
        for owner, label in ((obj, obj.name), (obj.data, obj.name + '.data')):
            if owner is None:
                continue
            properties = {key: plain(owner[key]) for key in owner.keys()
                          if key.startswith(('character_designer_hair_', 'character_designer_skirt_'))
                          or key == bone_color_palette.CONFIG_KEY}
            if properties:
                result['records'][label] = properties
    return result


def matrix_errors(old, new):
    errors = {name: max(abs(a - b) for x, y in zip(old[name], new[name]) for a, b in zip(x, y))
              for name in old if name in new}
    if any(not math.isfinite(value) for value in errors.values()):
        raise RuntimeError('A native pose/skinning matrix contains a non-finite difference.')
    return {'maximum': max(errors.values(), default=0.),
            'by_bone': errors, 'missing': sorted(set(old) - set(new)), 'added': sorted(set(new) - set(old))}


def surface_errors(rig, saved):
    values = {}
    for obj, old in saved:
        new = body_setup_removal._surface(bpy.context, rig, obj)
        if len(new) != len(old):
            raise RuntimeError(f'Evaluated topology changed on {obj.name}.')
        values[obj.name] = max(((a - b).length for a, b in zip(old, new)), default=0.)
        if not math.isfinite(values[obj.name]):
            raise RuntimeError(f'A non-finite evaluated vertex appeared on {obj.name}.')
    return {'maximum': max(values.values(), default=0.), 'by_object': values}


def native_pose(rig, names):
    return {name: matrix(rig.pose.bones[name].matrix) for name in names}


def native_skin(rig):
    return {name: matrix(value) for name, value in body_setup._native_skin(rig).items()}


def body_animation(rig, excluded_driver_paths):
    value = H['animation_snapshot'](rig)
    if value:
        value['drivers'] = [driver for driver in value['drivers'] if driver['path'] not in excluded_driver_paths]
    return value


def states(rig, excluded_meshes, excluded_driver_paths, rest_names):
    return {'meshes': retained_meshes(excluded_meshes),
            'rest': control_pose_assets.native_rest(rig),
            'pose': native_pose(rig, rest_names), 'skin': native_skin(rig),
            'hair_dress': hair_dress_snapshot(),
            'animation': body_animation(rig, excluded_driver_paths),
            'baseline': rig.get(control_pose_assets.BASELINE),
            'calibration': rig.get(body_calibration.KEY),
            'direct_registry': rig.data.get(limb_ik.DIRECT_REST_KEY)}


def check_preserved(facts, label, rig, before, surfaces, excluded_meshes, excluded_drivers, rest_names):
    limb_ik_fk._update(bpy.context, rig)
    now = states(rig, excluded_meshes, excluded_drivers, rest_names)
    checks = {
        'mesh_exact_diffs': exact_diffs(before['meshes'], now['meshes']),
        'native_rest_exact_diffs': exact_diffs(before['rest'], now['rest']),
        'native_rest': H['differences'](now['rest'], before['rest']),
        'native_pose': matrix_errors(before['pose'], now['pose']),
        'native_skin': matrix_errors(before['skin'], now['skin']),
        'surfaces': surface_errors(rig, surfaces),
        'hair_dress_exact_diffs': exact_diffs(before['hair_dress'], now['hair_dress']),
        'animation_exact_diffs': exact_diffs(before['animation'], now['animation']),
        'baseline_unchanged': before['baseline'] == now['baseline'],
        'calibration_unchanged': before['calibration'] == now['calibration'],
        'direct_registry_unchanged': before['direct_registry'] == now['direct_registry']}
    facts.setdefault('checks', {})[label] = checks
    if checks['mesh_exact_diffs'] or checks['hair_dress_exact_diffs'] or checks['animation_exact_diffs']:
        raise RuntimeError(f'{label}: protected mesh/Hair/Dress/animation data changed; inspect exact JSON differences.')
    if any(entry['substantial'] for entry in checks['native_rest']):
        raise RuntimeError(f'{label}: native Rest changed beyond its verified float-roundtrip tolerance.')
    for field in ('native_pose', 'native_skin'):
        if checks[field]['missing'] or checks[field]['added'] or checks[field]['maximum'] > POSE_TOLERANCE:
            raise RuntimeError(f'{label}: {field} was not preserved ({checks[field]["maximum"]:.6g}).')
    if checks['surfaces']['maximum'] > SURFACE_TOLERANCE:
        raise RuntimeError(f'{label}: evaluated surface changed ({checks["surfaces"]["maximum"]:.6g}).')
    if not all(checks[field] for field in ('baseline_unchanged', 'calibration_unchanged', 'direct_registry_unchanged')):
        raise RuntimeError(f'{label}: saved artist Rest provenance/calibration was rewritten.')
    checks['passed'] = True
    return now


def timed(facts, label, operation):
    started = time.perf_counter()
    value = operation()
    facts.setdefault('operations', []).append({'operation': label,
        'seconds': time.perf_counter() - started, 'result': plain(value)})
    return value


def rotate_probe(rig, bone_name):
    """Temporary real pose input, exact channel restore and evaluated skin test."""
    limb_ik_fk._update(bpy.context, rig)
    pb = rig.pose.bones[bone_name]
    saved = {'mode': pb.rotation_mode, 'channels': {field: tuple(getattr(pb, field)) for field in CHANNELS}}
    surfaces = body_setup_removal._bound_surfaces(bpy.context, rig)
    basis = pb.matrix_basis.copy()
    result = {'bone': bone_name, 'radians': .12, 'local_axis': 'X'}
    with forearm_twist.defer_runtime(bpy.context, flush_on_exit=False):
        try:
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = basis.to_quaternion() @ Quaternion((1., 0., 0.), .12)
            limb_ik_fk._update(bpy.context, rig)
            result['changed_surfaces'] = surface_errors(rig, surfaces)
            result['changed_basis_max_error'] = max(abs(pb.matrix_basis[i][j] - basis[i][j])
                                                    for i in range(4) for j in range(4))
        finally:
            pb.rotation_mode = saved['mode']
            for field, values in saved['channels'].items():
                setattr(pb, field, values)
            limb_ik_fk._update(bpy.context, rig)
        result['restored_surfaces'] = surface_errors(rig, surfaces)
        result['channels_restored_exactly'] = (pb.rotation_mode == saved['mode']
            and all(tuple(getattr(pb, field)) == values for field, values in saved['channels'].items()))
    if result['changed_surfaces']['maximum'] <= 1e-5:
        raise RuntimeError(f'{bone_name}: real FK rotation did not move a bound mesh.')
    if result['restored_surfaces']['maximum'] > 2e-6 or not result['channels_restored_exactly']:
        raise RuntimeError(f'{bone_name}: temporary rotation did not restore the current artist pose.')
    result['passed'] = True
    return result


def main(facts):
    if not bpy.app.background:
        raise RuntimeError('This validator is background-only; do not run it in the artist UI.')
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    source = Path(args[0]).resolve() if args else FOLDER / 'X_live_input.blend'
    if source.parent != FOLDER or source.name != 'X_live_input.blend' or source == ARTIST.resolve():
        raise RuntimeError('Only this validation folder\'s X_live_input.blend checkpoint is accepted.')
    if Path(character_designer.__file__).resolve().parent != CANONICAL / 'character_designer':
        raise RuntimeError('The canonical Character Designer package was not imported.')
    facts['input_before'] = H['fingerprint'](source)
    facts['artist_before'] = H['fingerprint'](ARTIST) if ARTIST.exists() else None
    character_designer.register()
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    rig = bpy.data.objects.get('CoshaRig')
    if rig is None or rig.type != 'ARMATURE':
        raise RuntimeError('The checkpoint does not contain CoshaRig.')
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    limb_ik._settings(bpy.context).armature = rig
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    if body_original_mode.active(rig):
        raise RuntimeError('Expected current Controls checkpoint; Original is active.')
    if forearm_twist._SESSION is not None or any(forearm_twist.PREVIEW_KEY in obj for obj in bpy.data.objects):
        raise RuntimeError('An active Forearm preview must be finished by its existing transaction.')
    limb_ik_fk._update(bpy.context, rig)
    inventory = limb_ik._validate_inventory(rig)
    if set(inventory['rigs']) != set(limb_ik_fk_batch.LIMB_KEYS):
        raise RuntimeError('Expected the installed four native arm/leg chains.')
    extension = spine_ik_fk.validate(rig)
    if extension is None:
        raise RuntimeError('Expected the previous optional Spine branch in this integration checkpoint.')
    excluded_meshes = {entry['object'] for entry in extension['widgets'].values()}
    for name in excluded_meshes:
        obj = bpy.data.objects[name]
        if obj.type != 'MESH' or obj.get(limb_ik.OWNER_KEY) != spine_ik_fk.OWNER_VALUE:
            raise RuntimeError(f'{name}: optional widget ownership is not proved.')
    excluded_drivers = {entry['path'] for entry in extension['drivers']}
    rest_names = tuple(control_pose_assets.native_rest(rig))
    surfaces = body_setup_removal._bound_surfaces(bpy.context, rig)
    before = states(rig, excluded_meshes, excluded_drivers, rest_names)
    facts.update({'runtime': bpy.app.version_string, 'addon_source': character_designer.__file__,
        'addon_version': list(character_designer.bl_info['version']),
        'validator_sha256': H['sha_file'](Path(__file__).resolve()),
        'snapshot_probe_sha256': H['sha_file'](PROBE),
        'batch_source': limb_ik_fk_batch.__file__, 'scene': bpy.context.scene.name,
        'initial_mode': limb_ik_fk_batch.mode_for_keys(rig, inventory),
        'initial_spine_mode': spine_ik_fk.mode_for_rig(rig),
        'excluded_owned_spine_widgets': sorted(excluded_meshes),
        'excluded_owned_spine_driver_paths': sorted(excluded_drivers),
        'input_state': before, 'tolerances': {'pose_matrix': POSE_TOLERANCE,
            'evaluated_surface_rig_units': SURFACE_TOLERANCE, 'rest_matrix': REST_TOLERANCE,
            'rest_length': 1e-6, 'temporary_restore_surface': 2e-6}})
    if facts['initial_mode'] != 'IK':
        raise RuntimeError('Expected all four limbs initially in IK.')
    timed(facts, 'remove_optional_spine', lambda: body_setup._atomic(
        bpy.context, rig, lambda: spine_ik_fk.remove(bpy.context, rig)))
    if spine_ik_fk.get_record(rig) or any(bone.get(limb_ik.OWNER_KEY) == spine_ik_fk.OWNER_VALUE
                                       for bone in rig.data.bones):
        raise RuntimeError('The optional owned Spine branch remains after its guarded removal.')
    if any(name in bpy.data.objects for name in excluded_meshes):
        raise RuntimeError('A removed optional Spine widget remains in bpy.data.objects.')
    check_preserved(facts, 'after_spine_remove', rig, before, surfaces,
                    excluded_meshes, excluded_drivers, rest_names)
    def switch_public(mode):
        result = bpy.ops.character_designer.body_ik_fk_switch(mode=mode)
        if result != {'FINISHED'}:
            raise RuntimeError(f'The public all-limb {mode} button did not finish.')
        return sorted(result)
    for mode, label in (('FK', 'all_fk'), ('IK', 'all_ik_roundtrip'), ('FK', 'final_all_fk')):
        timed(facts, label, lambda mode=mode: switch_public(mode))
        if limb_ik_fk_batch.mode_for_keys(rig) != mode:
            raise RuntimeError(f'{label}: the four chains did not all reach {mode}.')
        check_preserved(facts, label, rig, before, surfaces, excluded_meshes, excluded_drivers, rest_names)
    inventory = limb_ik._validate_inventory(rig)
    facts['rotation_probes'] = {}
    for key in limb_ik_fk_batch.LIMB_KEYS:
        name = inventory['rigs'][key]['chain'][0]
        facts['rotation_probes']['.'.join(key)] = rotate_probe(rig, name)
    torso = torso_controls.validate(rig)
    if not torso:
        raise RuntimeError('The shared Bend/section FK graph was lost.')
    facts['rotation_probes']['SPINE.BEND'] = rotate_probe(rig, torso['bend'])
    facts['rotation_probes']['SPINE.SECTION'] = rotate_probe(rig, torso['controls'][torso['sources'][1]])
    facts['final_state'] = check_preserved(facts, 'after_real_rotation_probes', rig, before, surfaces,
                                         excluded_meshes, excluded_drivers, rest_names)
    facts['final_mode'] = limb_ik_fk_batch.mode_for_keys(rig)
    facts['final_spine'] = {'optional_ik': spine_ik_fk.get_record(rig),
                            'bend': torso['bend'], 'sections': torso['controls']}
    result = bpy.ops.wm.save_as_mainfile(filepath=str(CANDIDATE), check_existing=False, copy=True)
    if result != {'FINISHED'} or not CANDIDATE.exists():
        raise RuntimeError('The isolated candidate save was not confirmed by Blender.')
    facts['candidate_saved'] = H['fingerprint'](CANDIDATE)
    facts['input_after'] = H['fingerprint'](source)
    facts['artist_after'] = H['fingerprint'](ARTIST) if ARTIST.exists() else None
    if facts['input_before'] != facts['input_after'] or facts['artist_before'] != facts['artist_after']:
        raise RuntimeError('The source checkpoint or artist .blend changed during validation.')
    facts['input_unchanged'] = facts['artist_unchanged'] = True
    facts['status'] = 'passed'


if __name__ == '__main__':
    facts = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'candidate_saved': False, 'artist_saved': False}
    try:
        main(facts)
    except Exception as exc:
        facts.update({'status': 'failed', 'error': str(exc), 'traceback': traceback.format_exc()})
        raise
    finally:
        facts['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        OUTPUT.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
        print('NATIVE_FK_X_VALIDATION', facts.get('status', 'failed'), str(OUTPUT), flush=True)
