"""Read-only isolated X probe for intentional native Rest changes.

Run with factory Blender and --disable-autoexec. Opens X_live_input.blend only,
imports canonical source without registration, writes JSON evidence only, and
never repairs Rest, edits a baseline, starts preview, or saves a blend file.
"""
import datetime
import hashlib
import json
import math
import sys
import traceback
from array import array
from pathlib import Path

import bpy
from mathutils import Vector

FOLDER = Path(__file__).resolve().parent
SOURCE = FOLDER / 'X_live_input.blend'
OUTPUT = FOLDER / 'probe_current.json'
CANONICAL = Path(r'D:\MyRepository\Blender-addons-by-Randy\addons')
sys.path.insert(0, str(CANONICAL))
import character_designer
from character_designer import (body_original_mode as original, control_pose_assets as poses,
                               forearm_twist as forearm, limb_ik)

AFFECTED = ('upper_arm.L', 'upper_arm.R')
CHAIN_NAMES = {name for side in ('L', 'R') for name in
               ('upper_arm.' + side, 'forearm.' + side, 'hand.' + side)}
CHANNELS = ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')


def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(path):
    stat = path.stat()
    return {'path': str(path), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
            'sha256': sha_file(path)}


def plain(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else repr(value)
    if isinstance(value, bpy.types.ID):
        return {'type': value.bl_rna.identifier, 'name': value.name,
                'library': value.library.filepath if value.library else None}
    if hasattr(value, 'items'):
        return {str(key): plain(item) for key, item in value.items()}
    try:
        return [plain(item) for item in value]
    except TypeError:
        return {'type': type(value).__name__, 'value': repr(value)}


def custom(owner):
    try:
        return plain(dict(owner.items()))
    except TypeError:
        return {}


def matrix(value):
    return [list(row) for row in value]


def rna_fields(owner):
    """Constraint settings only: no evaluated geometry or image pixel access."""
    fields = {}
    for prop in owner.bl_rna.properties:
        if prop.identifier == 'rna_type' or prop.type == 'COLLECTION':
            continue
        try:
            fields[prop.identifier] = plain(getattr(owner, prop.identifier))
        except (AttributeError, TypeError, ValueError, ReferenceError) as exc:
            fields[prop.identifier] = {'unavailable': str(exc)}
    return fields


def data_hash(values):
    digest = hashlib.sha256()
    for tag, value in values:
        digest.update(tag.encode('utf-8') + b'\0')
        if isinstance(value, array):
            digest.update(value.tobytes())
        else:
            digest.update(json.dumps(plain(value), ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8'))
    return digest.hexdigest()


def bulk(items, field, width, kind='f'):
    values = array(kind, [0]) * (len(items) * width)
    if values:
        items.foreach_get(field, values)
    return values


def mesh_snapshot(obj):
    mesh = obj.data
    pieces = [('vertices', bulk(mesh.vertices, 'co', 3)),
              ('edges', bulk(mesh.edges, 'vertices', 2, 'i')),
              ('loops', bulk(mesh.loops, 'vertex_index', 1, 'i')),
              ('polygons', [(p.loop_start, p.loop_total, p.material_index, p.use_smooth)
                            for p in mesh.polygons]),
              ('groups', [(g.name, g.index, g.lock_weight) for g in obj.vertex_groups]),
              ('weights', [[(g.group, g.weight) for g in v.groups] for v in mesh.vertices]),
              ('properties', custom(mesh))]
    uv = []
    for layer in mesh.uv_layers:
        coordinates = bulk(layer.data, 'uv', 2)
        pieces.append(('uv:' + layer.name, coordinates))
        uv.append({'name': layer.name, 'loops': len(layer.data),
                   'coordinates_sha256': hashlib.sha256(coordinates.tobytes()).hexdigest()})
    keys = []
    if mesh.shape_keys:
        pieces.append(('key_properties', custom(mesh.shape_keys)))
        pieces.append(('keys_relative', mesh.shape_keys.use_relative))
        for key in mesh.shape_keys.key_blocks:
            coordinates = bulk(key.data, 'co', 3)
            fields = {'name': key.name, 'relative_key': key.relative_key.name,
                      'value': key.value, 'mute': key.mute, 'vertex_group': key.vertex_group,
                      'interpolation': key.interpolation, 'slider_min': key.slider_min,
                      'slider_max': key.slider_max}
            pieces.extend([('key_fields', fields), ('key_coords:' + key.name, coordinates)])
            keys.append({**fields, 'coordinates_sha256': hashlib.sha256(coordinates.tobytes()).hexdigest()})
    return {'object': obj.name, 'data': plain(mesh), 'vertices': len(mesh.vertices),
            'edges': len(mesh.edges), 'faces': len(mesh.polygons), 'uv': uv,
            'shape_keys': keys, 'content_sha256': data_hash(pieces),
            'relationship': {'parent': plain(obj.parent), 'parent_type': obj.parent_type,
                             'parent_bone': obj.parent_bone,
                             'matrix_parent_inverse': matrix(obj.matrix_parent_inverse),
                             'matrix_world': matrix(obj.matrix_world),
                             'armature_modifiers': [{'name': mod.name, 'fields': rna_fields(mod)}
                                                    for mod in obj.modifiers if mod.type == 'ARMATURE']}}


def bone_rest(bone):
    return {'head': list(bone.head_local), 'tail': list(bone.tail_local),
            'matrix': matrix(bone.matrix_local), 'length': bone.length,
            'z': list(bone.matrix_local.to_3x3().col[2]),
            'parent': bone.parent.name if bone.parent else None, 'connected': bone.use_connect,
            'deform': bone.use_deform, 'inherit_scale': bone.inherit_scale,
            'inherit_rotation': bone.use_inherit_rotation, 'local_location': bone.use_local_location,
            'properties': custom(bone)}


def rig_snapshot(rig):
    return {'object': plain(rig), 'data': plain(rig.data), 'object_properties': custom(rig),
            'data_properties': custom(rig.data), 'rest': {b.name: bone_rest(b) for b in rig.data.bones},
            'pose': {p.name: {'mode': p.rotation_mode,
                             'channels': {field: list(getattr(p, field)) for field in CHANNELS},
                             'basis': matrix(p.matrix_basis), 'matrix': matrix(p.matrix),
                             'properties': custom(p)} for p in rig.pose.bones},
            'constraints': {p.name: [{'name': con.name, 'fields': rna_fields(con)}
                                     for con in p.constraints] for p in rig.pose.bones}}


def curve_snapshot(curve):
    return {'path': curve.data_path, 'index': curve.array_index, 'mute': curve.mute,
            'points': [{'co': list(p.co), 'interpolation': p.interpolation,
                        'left': list(p.handle_left), 'right': list(p.handle_right)}
                       for p in curve.keyframe_points],
            'modifiers': [{'type': mod.type, 'fields': rna_fields(mod)} for mod in curve.modifiers]}


def driver_snapshot(curve):
    driver = curve.driver
    return {**curve_snapshot(curve), 'type': driver.type, 'expression': driver.expression,
            'use_self': driver.use_self,
            'variables': [{'name': var.name, 'type': var.type,
                           'targets': [rna_fields(target) for target in var.targets]}
                          for var in driver.variables]}


def animation_snapshot(owner):
    animation = getattr(owner, 'animation_data', None)
    if animation is None:
        return None
    actions = limb_ik._actions_for_id(owner)
    return {'action': plain(animation.action), 'action_slot': getattr(animation.action_slot, 'identifier', None),
            'drivers': [driver_snapshot(curve) for curve in animation.drivers],
            'actions': [{'id': plain(action), 'curves': [curve_snapshot(curve)
                                                       for curve in limb_ik._fcurves_for_action(action)]}
                        for action in actions],
            'nla': [{'name': track.name, 'mute': track.mute,
                     'strips': [{'name': strip.name, 'action': plain(strip.action),
                                 'frame_start': strip.frame_start, 'frame_end': strip.frame_end}
                                for strip in track.strips]} for track in animation.nla_tracks]}


def differences(current, saved):
    result = []
    for name in sorted(set(current) | set(saved)):
        now, old = current.get(name), saved.get(name)
        if now is None or old is None:
            result.append({'bone': name, 'missing': 'current' if now is None else 'saved'})
            continue
        relation = {key: {'old': old[key], 'new': now[key]} for key in now
                    if key not in ('matrix', 'length') and old.get(key) != now[key]}
        matrix_error = max(abs(a-b) for row, before in zip(now['matrix'], old['matrix'])
                           for a, b in zip(row, before))
        length_error = now['length'] - old['length']
        if relation or matrix_error or length_error:
            result.append({'bone': name, 'relations': relation, 'matrix_max_error': matrix_error,
                           'length_delta': length_error,
                           'substantial': bool(relation or matrix_error > 2e-6 or abs(length_error) > 1e-6)})
    return result


def dependencies(rig, owned):
    result = []
    own = {(pb.name, con.name) for pb, con, _record in owned}
    owned_influence_paths = {con.path_from_id('influence') for _pb, con, _record in owned}
    chain_pairs = {('upper_arm.' + side, 'forearm.' + side) for side in ('L', 'R')}
    chain_pairs.update({('forearm.' + side, 'hand.' + side) for side in ('L', 'R')})
    for obj in bpy.data.objects:
        if obj.parent == rig and obj.parent_type == 'BONE' and obj.parent_bone in CHAIN_NAMES:
            result.append({'kind': 'bone_parent', 'object': obj.name, 'bone': obj.parent_bone})
        if obj.type == 'ARMATURE':
            for bone in obj.data.bones:
                if obj == rig and bone.parent and bone.parent.name in CHAIN_NAMES:
                    result.append({'kind': 'child_bone', 'bone': bone.name, 'parent': bone.parent.name,
                                   'ordinary_chain_child': (bone.parent.name, bone.name) in chain_pairs})
            for pb in obj.pose.bones:
                for con in pb.constraints:
                    if (obj != rig or (pb.name, con.name) not in own) and (
                            (obj == rig and pb.name in CHAIN_NAMES)
                            or limb_ik._constraint_references_controls(con, rig, CHAIN_NAMES)):
                        result.append({'kind': 'foreign_pose_constraint', 'object': obj.name,
                                       'bone': pb.name, 'fields': rna_fields(con)})
                transform = pb.custom_shape_transform
                if obj == rig and transform and transform.name in CHAIN_NAMES:
                    result.append({'kind': 'custom_shape_transform', 'bone': pb.name, 'target': transform.name})
        for con in obj.constraints:
            if limb_ik._constraint_references_controls(con, rig, CHAIN_NAMES):
                result.append({'kind': 'object_constraint', 'object': obj.name, 'fields': rna_fields(con)})
        for mod in obj.modifiers:
            for object_field, bone_field in (('object', 'subtarget'), ('object_from', 'bone_from'), ('object_to', 'bone_to')):
                if getattr(mod, object_field, None) == rig and getattr(mod, bone_field, '') in CHAIN_NAMES:
                    result.append({'kind': 'modifier', 'object': obj.name, 'modifier': mod.name,
                                   'bone': getattr(mod, bone_field)})
        for owner in (obj, obj.data, getattr(obj.data, 'shape_keys', None)):
            animation = getattr(owner, 'animation_data', None)
            if animation:
                for curve in animation.drivers:
                    writes = owner == rig and limb_ik._path_mentions_bone(curve.data_path, CHAIN_NAMES)
                    reads = any(target.id == rig and (getattr(target, 'bone_target', '') in CHAIN_NAMES
                                or limb_ik._path_mentions_bone(getattr(target, 'data_path', ''), CHAIN_NAMES))
                                for var in curve.driver.variables for target in var.targets)
                    if writes or reads:
                        result.append({'kind': 'driver', 'owner': plain(owner),
                                       'writes_chain': writes, 'reads_chain': reads,
                                       'owned_limb_influence_path': owner == rig and curve.data_path in owned_influence_paths,
                                       'driver': driver_snapshot(curve)})
    return result


def main(facts):
    if not bpy.app.background:
        raise RuntimeError('This probe is isolated background-only; artist UI must not run it.')
    if Path(character_designer.__file__).resolve().parent != CANONICAL / 'character_designer':
        raise RuntimeError('The canonical Character Designer package was not imported.')
    facts['input_before'] = fingerprint(SOURCE)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    rig, body = bpy.data.objects['CoshaRig'], bpy.data.objects['Cosha']
    if forearm._SESSION is not None or forearm.PREVIEW_KEY in body:
        raise RuntimeError('Active Forearm preview detected; this probe will not recover or cancel it.')
    facts.update({'runtime': bpy.app.version_string, 'addon_version': list(character_designer.bl_info['version']),
                  'addon_source': character_designer.__file__, 'file': bpy.data.filepath,
                  'scene': bpy.context.scene.name, 'mode': bpy.context.mode,
                  'direct_schema': rig.data.get(limb_ik.SCHEMA_KEY),
                  'original_active': original.active(rig), 'preview_active': False})
    saved_raw = rig.get(original.SESSION)
    saved = json.loads(saved_raw) if saved_raw else None
    facts['original_saved_raw'] = saved_raw
    facts['direct_saved_raw'] = rig.data.get(limb_ik.DIRECT_REST_KEY)
    registry = limb_ik._load_direct_rest_registry(rig, strict=True)
    facts['direct_registry'] = registry
    current = poses.native_rest(rig)
    facts['native_rest'] = current
    facts['native_rest_vs_original_session'] = differences(current, saved['rest']) if saved else None
    facts['affected_upper_arms'] = {}
    for name in AFFECTED:
        entries = [{'rig_id': rig_id, 'chain': entry['chain'],
                    'original': entry['original'].get(name), 'applied': entry['applied'].get(name),
                    'matches_original': limb_ik._rest_state_matches(rig.data.bones[name], entry['original'][name]),
                    'matches_applied': limb_ik._rest_state_matches(rig.data.bones[name], entry['applied'][name]),
                    'applied_mismatch': limb_ik._rest_state_mismatch_details(rig.data.bones[name], entry['applied'][name])}
                   for rig_id, entry in registry['limbs'].items() if name in entry['chain'][:2]]
        facts['affected_upper_arms'][name] = {'current': bone_rest(rig.data.bones[name]),
                                              'original_session': saved['rest'].get(name) if saved else None,
                                              'direct_entries': entries}
    owned = limb_ik._owned_constraint_records(rig, strict=True)
    facts['owned_constraints'] = [{'bone': pb.name, 'name': con.name, 'record': record,
                                  'fields': rna_fields(con)} for pb, con, record in owned]
    facts['sources_chain_geometry'] = []
    for side in ('L', 'R'):
        upper, lower, hand = [rig.data.bones[name + '.' + side] for name in ('upper_arm', 'forearm', 'hand')]
        first = (upper.tail_local - upper.head_local).normalized()
        second = (lower.tail_local - lower.head_local).normalized()
        facts['sources_chain_geometry'].append({'side': side,
            'bones': {bone.name: bone_rest(bone) for bone in (upper, lower, hand)},
            'upper_to_lower_gap': (upper.tail_local - lower.head_local).length,
            'lower_to_hand_gap': (lower.tail_local - hand.head_local).length,
            'bend_angle_radians': first.angle(second), 'bend_cross': list(first.cross(second)),
            'upper_lower_roll_axis_dot': upper.matrix_local.to_3x3().col[2].dot(lower.matrix_local.to_3x3().col[2])})
    facts['forearm_calibration_raw'] = body.get(forearm.RECORD_KEY)
    facts['forearm_calibration'] = forearm._records(body)
    facts['all_rigs'] = {obj.name: rig_snapshot(obj) for obj in bpy.data.objects if obj.type == 'ARMATURE'}
    facts['all_meshes'] = {obj.name: mesh_snapshot(obj) for obj in bpy.data.objects if obj.type == 'MESH'}
    facts['all_object_relations'] = {obj.name: {'parent': plain(obj.parent), 'parent_type': obj.parent_type,
                                               'parent_bone': obj.parent_bone, 'matrix_world': matrix(obj.matrix_world),
                                               'matrix_parent_inverse': matrix(obj.matrix_parent_inverse)}
                                   for obj in bpy.data.objects}
    facts['relevant_animation'] = {label: value for owner, label in ((rig, 'rig'), (rig.data, 'armature_data'),
                                      (body, 'body_object'), (body.data.shape_keys, 'body_shape_keys'))
                                  if owner is not None and (value := animation_snapshot(owner)) is not None}
    facts['external_dependencies'] = dependencies(rig, owned)
    for label, check in (('strict_inventory', lambda: limb_ik._validate_inventory(rig)),
                         ('original_session_rest_proof', lambda: original._validate_session_rest(rig, saved, current))):
        try:
            check()
            facts[label] = {'status': 'passed'}
        except Exception as exc:
            facts[label] = {'status': 'refused', 'error': str(exc)}
    facts['input_after'] = fingerprint(SOURCE)
    if facts['input_after'] != facts['input_before']:
        raise RuntimeError('The isolated input file changed during the read-only probe.')
    facts['input_unchanged'] = True
    facts['operations'] = {'read_only': True, 'rna_writes': False, 'rest_repaired': False,
                           'baseline_rewritten': False, 'preview_started': False, 'blend_saved': False}
    facts['status'] = 'completed'


if __name__ == '__main__':
    facts = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        main(facts)
    except Exception as exc:
        facts.update({'status': 'failed', 'error': str(exc), 'traceback': traceback.format_exc()})
        raise
    finally:
        facts['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        OUTPUT.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
        print('ORIGINAL_CURRENT_READ_ONLY_PROBE', facts['status'], str(OUTPUT), flush=True)
