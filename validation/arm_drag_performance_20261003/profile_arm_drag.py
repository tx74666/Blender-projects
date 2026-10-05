"""Isolated X arm deformation benchmark. No scene save or runtime deployment.

Run in a NEW background Blender process; do not execute on the artist window.
Example: blender --background --factory-startup --threads 2 --python this.py --
  --input scene_snapshot.blend --output result.json --repeats 6 --mode current

Measured interval: pose assignment + view-layer/dependency-graph evaluation.
Excluded: UI event delivery, Undo, viewport GPU drawing and material compilation.
Disabling a correction callback leaves its last output in this test copy only;
that condition is a diagnostic counterfactual, not a safe production workaround.
"""
import argparse
from array import array
from collections import Counter
import cProfile
import ctypes
from functools import wraps
import hashlib
import importlib
import json
import math
from pathlib import Path
import pstats
import statistics
import sys
import time
import traceback

import bpy
from mathutils import Matrix, Vector


def arguments():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--addon-root', default='C:/Users/Randy/AppData/Roaming/Blender Foundation/Blender/5.1/scripts/addons')
    parser.add_argument('--rig', default='CoshaRig')
    parser.add_argument('--body', default='Cosha')
    parser.add_argument('--bone', default='')
    parser.add_argument('--side', choices=('L', 'R'), default='L')
    parser.add_argument('--mode', choices=('current', 'controls'), default='current')
    parser.add_argument('--movement', choices=('auto', 'location', 'rotation'), default='auto')
    parser.add_argument('--repeats', type=int, default=6)
    parser.add_argument('--warmups', type=int, default=2)
    parser.add_argument('--cases', default='baseline,no_subsurf,no_forearm,no_subsurf_no_forearm')
    parser.add_argument('--sample-vertices', type=int, default=8192)
    return parser.parse_args(argv)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def event(name, **details):
    print('ARM_DRAG_EVENT', json.dumps({'event': name, 'unix_time': time.time(),
          'perf_counter': time.perf_counter(), **details}), flush=True)


def check_memory(label):
    state = memory()
    if state.get('system_available_mib', 201) < 200:
        event('memory_floor_stop', stage=label, memory=state)
        raise RuntimeError('Less than 200 MiB available at ' + label + '; stopping with partial results.')
    return state


def memory():
    if sys.platform != 'win32':
        return {'available': False}
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                    ('total_physical', ctypes.c_ulonglong), ('available_physical', ctypes.c_ulonglong),
                    ('total_pagefile', ctypes.c_ulonglong), ('available_pagefile', ctypes.c_ulonglong),
                    ('total_virtual', ctypes.c_ulonglong), ('available_virtual', ctypes.c_ulonglong),
                    ('available_extended_virtual', ctypes.c_ulonglong)]
    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('page_fault_count', ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ('peak_working_set', 'working_set', 'quota_peak_paged',
             'quota_paged', 'quota_peak_nonpaged', 'quota_nonpaged', 'pagefile', 'peak_pagefile', 'private_usage')]
    state, counters = MEMORYSTATUSEX(), PROCESS_MEMORY_COUNTERS_EX()
    state.length, counters.cb = ctypes.sizeof(state), ctypes.sizeof(counters)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    if not kernel.GlobalMemoryStatusEx(ctypes.byref(state)):
        return {'available': False, 'error': ctypes.get_last_error()}
    psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    return {'available': True, 'system_load_percent': state.load,
            'system_available_mib': state.available_physical / 1048576,
            'system_total_mib': state.total_physical / 1048576,
            'process_working_set_mib': counters.working_set / 1048576,
            'process_private_mib': counters.private_usage / 1048576,
            'process_page_fault_count': counters.page_fault_count,
            'page_fault_warning': 'Includes soft faults; this count does not prove disk paging.'}


def percentile(values, percentage):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * percentage / 100
    lower, upper = math.floor(position), math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def handler_inventory():
    return {name: [{'module': getattr(fn, '__module__', ''), 'name': getattr(fn, '__name__', repr(fn))}
                   for fn in getattr(bpy.app.handlers, name)]
            for name in ('depsgraph_update_pre', 'depsgraph_update_post', 'frame_change_pre',
                         'frame_change_post', 'load_post')}


def pose_channels(rig):
    return {pb.name: tuple(round(float(v), 12) for row in pb.matrix_basis for v in row)
            for pb in rig.pose.bones}


def object_visible(obj):
    try:
        return bool(obj.visible_get(view_layer=bpy.context.view_layer))
    except TypeError:
        return bool(obj.visible_get())


def optional_read(label, reader):
    """Nonessential metadata must not abort a valid deformation benchmark."""
    try:
        return reader()
    except Exception as exc:
        return {'available': False, 'diagnostic': label, 'error': str(exc),
                'exception_type': type(exc).__name__}


def selected_bone_inventory(rig):
    result = {'data_selection_property_available': False,
              'pose_selection_property_available': False, 'selected_data_bones': [],
              'selected_pose_bones_from_rig': []}
    for bone in rig.data.bones:
        selected = getattr(bone, 'select', None)
        if selected is not None:
            result['data_selection_property_available'] = True
            if selected:
                result['selected_data_bones'].append(bone.name)
    for bone in rig.pose.bones:
        selected = getattr(bone, 'select', None)
        if selected is not None:
            result['pose_selection_property_available'] = True
            if selected:
                result['selected_pose_bones_from_rig'].append(bone.name)
    result['note'] = 'Blender versions may store selection on PoseBone; missing properties are unavailable, not unselected.'
    return result


def inspect_drivers():
    """Read-only validity inventory; invalid alone is not a latency finding."""
    identifiers = list(bpy.context.scene.objects) + list(bpy.data.shape_keys) + [bpy.context.scene]
    seen, total, invalid, errors = set(), 0, [], []
    for identifier in identifiers:
        pointer = identifier.as_pointer()
        if pointer in seen:
            continue
        seen.add(pointer)
        animation = getattr(identifier, 'animation_data', None)
        for curve in animation.drivers if animation else ():
            total += 1
            try:
                if not curve.is_valid:
                    invalid.append({'id': identifier.name, 'data_path': curve.data_path,
                        'array_index': curve.array_index, 'expression': curve.driver.expression,
                        'driver_valid': getattr(curve.driver, 'is_valid', None),
                        'variables': [{'name': v.name, 'type': v.type,
                            'targets': [{'id': t.id.name if t.id else None,
                                'bone_target': getattr(t, 'bone_target', None),
                                'data_path': getattr(t, 'data_path', None)} for t in v.targets]}
                            for v in curve.driver.variables]})
            except Exception as exc:
                errors.append({'id': identifier.name, 'diagnostic': 'driver validity', 'error': str(exc)})
    return {'total': total, 'invalid_count': len(invalid), 'invalid': invalid,
            'diagnostic_errors': errors,
            'note': 'Read-only validity flags after graph update; does not prove a performance cause.'}


def original_structure_report(mode, rig):
    if not mode.active(rig):
        return {'active': False}
    try:
        saved = json.loads(rig[mode.SESSION])
        before_names, after_names = set(saved['bones']), set(rig.data.bones.keys())
        before, after = saved['rest'], mode.poses.native_rest(rig)
        changed = []
        for name in sorted(set(before) & set(after)):
            if before[name] == after[name]:
                continue
            fields = [field for field in set(before[name]) | set(after[name])
                      if before[name].get(field) != after[name].get(field)]
            matrix_error = max((abs(a-b) for row_a, row_b in zip(before[name].get('matrix', []), after[name].get('matrix', []))
                                for a,b in zip(row_a,row_b)), default=0.0)
            changed.append({'bone': name, 'different_fields': fields, 'matrix_max_error': matrix_error,
                            'length_delta': after[name].get('length',0) - before[name].get('length',0),
                            'non_numeric_fields': {field: {'saved': before[name].get(field), 'current': after[name].get(field)}
                              for field in fields if field not in ('matrix', 'length')}})
        return {'active': True, 'saved_bones': len(before_names), 'current_bones': len(after_names),
                'added_bones': sorted(after_names-before_names), 'missing_bones': sorted(before_names-after_names),
                'native_added': sorted(set(after)-set(before)), 'native_missing': sorted(set(before)-set(after)),
                'exact_rest_equal': before == after, 'changed_rest_bones': changed,
                'read_only': True, 'note': 'Records the guard inputs; not automatically a drag-latency explanation.'}
    except Exception as exc:
        return {'active': True, 'read_only': True, 'error': str(exc)}


def sample_mesh(obj, limit):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.data
    count = len(mesh.vertices)
    step = max(1, math.ceil(count / limit))
    world = evaluated.matrix_world
    points = [tuple(world @ mesh.vertices[i].co) for i in range(0, count, step)]
    return {'vertices': count, 'edges': len(mesh.edges), 'polygons': len(mesh.polygons),
            'stride': step, 'points': points}


def point_change(before, after):
    if len(before['points']) != len(after['points']):
        return {'valid': False, 'reason': 'Different vertex counts during movement'}
    distances = [(Vector(a) - Vector(b)).length for a, b in zip(before['points'], after['points'])]
    maximum = max(distances, default=0.0)
    return {'valid': maximum > 1e-7, 'maximum_world_distance': maximum,
            'changed_sample_vertices': sum(v > 1e-7 for v in distances),
            'sample_vertices': len(distances), 'evaluated_vertices': after['vertices'],
            'sampling_note': 'Evenly spaced evaluated vertices; maximum is a sampled lower bound.'}


class Instrumentation:
    """Only function wrappers in this background process; nested time is labelled."""
    def __init__(self, twist, limb):
        self.twist, self.limb = twist, limb
        self.originals = []
        self.times = Counter()
        self.calls = Counter()
        self.graph_events = []
        self.handlers_original = []
        for module, names in ((twist, ('update_runtime', '_calculate_object', '_prepare_runtime_records',
                                       '_calculate_records', '_weights', '_topology', '_input_mix')),
                              (limb, ('_validate_inventory',))):
            for name in names:
                if hasattr(module, name):
                    original = getattr(module, name)
                    wrapped = self.wrap(original, module.__name__ + '.' + name)
                    self.originals.append((module, name, original))
                    setattr(module, name, wrapped)
        for group in ('depsgraph_update_post', 'frame_change_post'):
            handlers = getattr(bpy.app.handlers, group)
            for index, original in enumerate(list(handlers)):
                if getattr(original, '__module__', '') == twist.__name__:
                    wrapped = self.wrap(original, group + ':' + original.__name__)
                    handlers[index] = wrapped
                    self.handlers_original.append((group, original, wrapped))
        bpy.app.handlers.depsgraph_update_post.append(self.observe)

    def wrap(self, fn, name):
        @wraps(fn)
        def measured(*args, **kwargs):
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                self.times[name] += time.perf_counter() - start
                self.calls[name] += 1
        return measured

    def observe(self, scene, graph):
        updates = list(graph.updates)
        self.graph_events.append({'updates': len(updates),
            'geometry': sum(bool(getattr(u, 'is_updated_geometry', False)) for u in updates),
            'transform': sum(bool(getattr(u, 'is_updated_transform', False)) for u in updates),
            'shading': sum(bool(getattr(u, 'is_updated_shading', False)) for u in updates),
            'ids': [u.id.name for u in updates]})

    def snapshot(self):
        return {'calls': dict(self.calls), 'nested_seconds': dict(self.times),
                'graph_events': len(self.graph_events),
                'note': 'Components are nested; do not add their durations.'}

    def reset(self):
        self.calls.clear()
        self.times.clear()
        self.graph_events.clear()

    def set_forearm(self, enabled):
        for group, original, wrapped in self.handlers_original:
            handlers = getattr(bpy.app.handlers, group)
            if enabled and wrapped not in handlers:
                handlers.insert(0, wrapped)
            elif not enabled and wrapped in handlers:
                handlers.remove(wrapped)

    def restore(self):
        if self.observe in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(self.observe)
        for group, original, wrapped in self.handlers_original:
            handlers = getattr(bpy.app.handlers, group)
            if wrapped in handlers:
                handlers[handlers.index(wrapped)] = original
            elif original not in handlers:
                handlers.append(original)
        for module, name, original in reversed(self.originals):
            setattr(module, name, original)


def stats_rows(profile, limit=22):
    stats = pstats.Stats(profile)
    rows = []
    for (filename, line, name), (primitive, calls, own, cumulative, callers) in sorted(
            stats.stats.items(), key=lambda item: item[1][3], reverse=True)[:limit]:
        rows.append({'file': filename, 'line': line, 'function': name, 'calls': calls,
                     'primitive_calls': primitive, 'own_seconds': own, 'cumulative_seconds': cumulative})
    return rows


def main(args, report):
    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    report['input'] = {'path': str(input_path), 'sha256_before': sha256(input_path),
                       'bytes': input_path.stat().st_size}
    report['memory_start'] = check_memory('before scene load')
    sys.path.insert(0, str(Path(args.addon_root).resolve()))
    addon = importlib.import_module('character_designer')
    if not hasattr(bpy.types.WindowManager, 'character_designer_forearm_twist'):
        addon.register()
    from character_designer import forearm_twist as twist, limb_ik, body_original_mode as mode
    report['runtime'] = {'blender_version': bpy.app.version_string, 'background': bpy.app.background,
        'binary': bpy.app.binary_path, 'addon_version': list(addon.bl_info.get('version', ())),
        'addon_path': addon.__file__, 'addon_sources': {name: sha256(Path(module.__file__))
           for name, module in (('init', addon), ('forearm_twist', twist), ('limb_ik', limb_ik), ('original', mode))},
        'before_load_handlers': handler_inventory()}
    bpy.ops.wm.open_mainfile(filepath=str(input_path))
    report['memory_after_load'] = memory()
    rig = bpy.data.objects.get(args.rig)
    if rig is None or rig.type != 'ARMATURE':
        raise ValueError('Requested rig missing or not ARMATURE: ' + args.rig)
    report['scene'] = {'filepath': bpy.data.filepath, 'frame': bpy.context.scene.frame_current,
       'view_layer': bpy.context.view_layer.name, 'mode_on_load': bpy.context.mode,
       'active_object': bpy.context.object.name if bpy.context.object else None,
       'selected_pose_bones': [pb.name for pb in (bpy.context.selected_pose_bones or [])],
       'active_pose_bone': bpy.context.active_pose_bone.name if bpy.context.active_pose_bone else None,
       'active_data_bone': rig.data.bones.active.name if rig.data.bones.active else None,
       'bone_selection_inventory': optional_read('bone selection', lambda: selected_bone_inventory(rig)),
       'original_session': mode.active(rig), 'bones': len(rig.data.bones),
       'constraints': sum(len(pb.constraints) for pb in rig.pose.bones),
       'visible_meshes': sum(object_visible(obj) for obj in bpy.context.scene.objects if obj.type == 'MESH'),
       'total_meshes': sum(obj.type == 'MESH' for obj in bpy.context.scene.objects),
       'threads_mode': bpy.context.scene.render.threads_mode,
       'threads_setting': bpy.context.scene.render.threads,
       'post_load_handlers': handler_inventory()}
    report['original_structure'] = original_structure_report(mode, rig)
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    if args.mode == 'controls' and mode.active(rig):
        check_memory('before isolated Controls switch')
        event('controls_switch_start')
        start = time.perf_counter()
        mode.leave(bpy.context, rig)
        report['isolated_mode_change'] = {'from': 'Original', 'to': 'Controls',
             'seconds': time.perf_counter() - start, 'artist_modified': False}
        event('controls_switch_end', seconds=report['isolated_mode_change']['seconds'])
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()
    report['drivers'] = optional_read('driver inventory', inspect_drivers)
    original_pose = pose_channels(rig)
    try:
        inventory = limb_ik._validate_inventory(rig)
        arm_record = inventory['rigs'].get(('ARM', args.side))
        target_name = arm_record['target'].name if arm_record else None
        chain = list(arm_record['chain']) if arm_record else []
        report['arm_inventory'] = {'target': target_name, 'chain': chain,
             'target_rotation_version': inventory.get('target_rotation_version'),
             'ik_fk_mode': limb_ik.limb_ik_fk.mode_for_rig(rig, arm_record) if arm_record else None,
             'target_id_properties': dict(rig.pose.bones[target_name].items()) if target_name else {},
             'chain_constraints': {name: [{'name': c.name, 'type': c.type, 'mute': c.mute,
                 'influence': c.influence} for c in rig.pose.bones[name].constraints] for name in chain}}
    except Exception as exc:
        report['arm_inventory'] = {'error': str(exc)}
        detected = limb_ik.analyze_armature(rig)['limbs']['ARM'][args.side]
        chain = [detected.get(role) for role in ('upper', 'lower', 'end') if detected.get(role)]
        target_name = None
    bound = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
             and any(mod.type == 'ARMATURE' and mod.object == rig and mod.show_viewport for mod in obj.modifiers)]
    if not bound:
        raise ValueError('No viewport meshes bound to requested rig')
    mesh_inventory = []
    arm_weights = {}
    for obj in bound:
        arm_groups = {group.index for group in obj.vertex_groups if group.name in chain}
        weighted = sum(any(g.group in arm_groups and g.weight > 1e-7 for g in vertex.groups)
                       for vertex in obj.data.vertices)
        arm_weights[obj.name] = weighted
        try:
            records = twist._records(obj) if twist.RECORD_KEY in obj else {}
            calibration = {'record_key_present': twist.RECORD_KEY in obj,
                  'side_count': len(records), 'enabled_sides': [side for side,r in records.items() if r.get('enabled', True)],
                  'managed_keys': [r.get('key') for r in records.values()]}
        except Exception as exc:
            calibration = {'record_key_present': twist.RECORD_KEY in obj, 'error': str(exc)}
        mesh_inventory.append({'name': obj.name, 'visible': object_visible(obj),
             'raw_vertices': len(obj.data.vertices), 'arm_chain_weighted_vertices': weighted,
             'matching_arm_vertex_groups': [g.name for g in obj.vertex_groups if g.index in arm_groups],
             'forearm_calibration': calibration,
             'related_custom_property_names': [key for key in obj.keys() if 'forearm' in key.lower() or 'twist' in key.lower()]})
    report['bound_mesh_inventory'] = mesh_inventory
    requested_body = next((obj for obj in bound if obj.name == args.body), None)
    valid_meshes = [obj for obj in bound if arm_weights[obj.name] > 0]
    if requested_body is not None and arm_weights[requested_body.name] > 0:
        body = requested_body
        reason = 'Requested bound body has arm-chain skin weights'
    elif valid_meshes:
        body = max(valid_meshes, key=lambda obj: (object_visible(obj), arm_weights[obj.name], len(obj.data.vertices)))
        reason = 'Requested body unavailable/unweighted: chosen by visibility and arm-chain weighted vertex count'
    else:
        raise ValueError('No bound mesh has nonzero arm-chain weights; no valid deformation witness possible')
    report['body_mesh'] = {'name': body.name, 'raw_vertices': len(body.data.vertices),
        'raw_polygons': len(body.data.polygons), 'visible': object_visible(body),
        'requested_body': args.body, 'selection_reason': reason,
        'arm_chain_weighted_vertices': arm_weights[body.name],
        'shape_keys': len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0,
        'calibrated_meshes': [obj.name for obj in bound if twist.RECORD_KEY in obj]}
    submods = [(obj, mod, mod.show_viewport) for obj in bpy.context.scene.objects if obj.type == 'MESH'
               for mod in obj.modifiers if mod.type == 'SUBSURF']
    report['subsurf'] = [{'object': obj.name, 'modifier': mod.name, 'enabled': enabled,
        'levels': mod.levels, 'render_levels': mod.render_levels,
        'visible': object_visible(obj), 'base_vertices': len(obj.data.vertices)}
        for obj, mod, enabled in submods]
    report['forearm'] = {'runtime_registered': bool(getattr(twist, '_RUNTIME_REGISTERED', False)),
        'record_property_name': twist.RECORD_KEY,
        'recorded_scene_meshes': [obj.name for obj in bpy.context.scene.objects if obj.type == 'MESH' and twist.RECORD_KEY in obj],
        'registered_handlers': [{'list': group, 'name': fn.__name__,
             'registered': fn in getattr(bpy.app.handlers, group)} for group, fn in twist._HANDLERS],
        'errors_before': dict(twist._ERRORS)}
    # Use the real current pose mode. Never benchmark an inactive hand target
    # while Original has paused the corresponding control route.
    candidate_names = [args.bone] if args.bone else []
    if not args.bone:
        selected = report['scene']['selected_pose_bones']
        if mode.active(rig):
            candidate_names += [name for name in selected if name in chain]
            candidate_names += chain[:2]
            report['candidate_reason'] = 'Original session active: native arm bone candidates; controls may be suppressed.'
        else:
            candidate_names += [target_name] + [name for name in selected if name in chain] + chain[:2]
            report['candidate_reason'] = 'Controls session: generated hand IK target preferred, then native arm fallback.'
    candidate_names = list(dict.fromkeys(name for name in candidate_names if name and name in rig.pose.bones))
    if not candidate_names:
        raise ValueError('No arm bone candidate identified; provide --bone explicitly')
    selection_attempts = []
    chosen = None
    for name in candidate_names:
        check_memory('before movement validation')
        pb = rig.pose.bones[name]
        basis = pb.matrix_basis.copy()
        movement = args.movement if args.movement != 'auto' else ('location' if name == target_name else 'rotation')
        axis = 1 if movement == 'location' else 0
        amount = 0.015 if movement == 'location' else 0.04
        bpy.context.view_layer.update()
        before = sample_mesh(body, args.sample_vertices)
        before_chain = {n: rig.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones[n].matrix.copy() for n in chain}
        if movement == 'location':
            moved = basis.copy()
            offset = Vector((0, 0, 0)); offset[axis] = amount
            moved.translation = basis.translation + offset
            pb.matrix_basis = moved
        else:
            pb.matrix_basis = basis @ Matrix.Rotation(amount, 4, 'XYZ'[axis])
        start = time.perf_counter()
        rig.update_tag(refresh={'OBJECT'})
        bpy.context.view_layer.update()
        initial_update = time.perf_counter() - start
        after = sample_mesh(body, args.sample_vertices)
        witness = point_change(before, after)
        witness['chain_matrix_max_error'] = max((max(abs(a-b) for row_a, row_b in zip(before_chain[n], rig.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones[n].matrix) for a,b in zip(row_a, row_b)) for n in chain), default=0.0)
        witness['initial_update_seconds'] = initial_update
        pb.matrix_basis = basis
        rig.update_tag(refresh={'OBJECT'})
        bpy.context.view_layer.update()
        selection_attempts.append({'bone': name, 'movement': movement, 'axis': axis, 'amount': amount,
                                   'deformation_witness': witness})
        if witness['valid'] and witness['chain_matrix_max_error'] > 1e-7:
            chosen = (pb, basis, movement, axis, amount)
            break
    report['candidate_attempts'] = selection_attempts
    if chosen is None:
        raise ValueError('Candidates did not move evaluated skin/arm chain; no valid arm benchmark performed')
    pb, basis, movement, axis, amount = chosen
    report['selection'] = {'bone': pb.name, 'movement': movement, 'axis': axis, 'amount': amount,
        'current_original_session': mode.active(rig), 'fallback_from_explicit_bone': False,
        'generated_target_fallback': bool(target_name and not mode.active(rig) and pb.name != target_name),
        'matches_initial_selected_pose_bone': pb.name in report['scene']['selected_pose_bones'],
        'is_generated_target': pb.name == target_name,
        'note': 'Actual deformed skin and arm-chain movement verified before timing.'}
    snapshots = []
    for obj in bound:
        if twist.RECORD_KEY not in obj or not obj.data.shape_keys:
            continue
        for record in twist._records(obj).values():
            key = obj.data.shape_keys.key_blocks.get(record.get('key', ''))
            if key is not None:
                coordinates = array('f', [0.0]) * (3 * len(key.data))
                key.data.foreach_get('co', coordinates)
                snapshots.append((obj, key, coordinates, key.value, key.mute))
    ins = Instrumentation(twist, limb_ik)
    report['timing'] = {'interval': 'pose assignment + view_layer.update + evaluated_depsgraph_get',
        'includes_wrappers': True, 'profiled_sample_excluded_from_percentiles': True,
        'cold_definition': 'first pose update after per-case runtime cache clear, not cold Blender launch',
        'warmup_updates': args.warmups, 'warm_samples_per_case': args.repeats,
        'cases': []}
    cases = [name.strip() for name in args.cases.split(',') if name.strip()]
    policies = {'baseline': (False, True), 'no_subsurf': (True, True),
                'no_forearm': (False, False), 'no_subsurf_no_forearm': (True, False)}

    def move(sign):
        if movement == 'location':
            changed = basis.copy()
            delta = Vector((0, 0, 0)); delta[axis] = sign * amount
            changed.translation = basis.translation + delta
            pb.matrix_basis = changed
        else:
            pb.matrix_basis = basis @ Matrix.Rotation(sign * amount, 4, 'XYZ'[axis])
        rig.update_tag(refresh={'OBJECT'})
        bpy.context.view_layer.update()
        bpy.context.evaluated_depsgraph_get()

    def timed(sign, case, sample):
        state = check_memory('before sample ' + case + ':' + str(sample))
        event('sample_start', case=case, sample=sample, memory=state)
        before_events = len(ins.graph_events)
        start, cpu_start = time.perf_counter(), time.process_time()
        move(sign)
        elapsed, cpu = time.perf_counter() - start, time.process_time() - cpu_start
        event('sample_end', case=case, sample=sample, wall_seconds=elapsed, cpu_seconds=cpu)
        return {'wall_seconds': elapsed, 'process_cpu_seconds': cpu,
                'depsgraph_callbacks': len(ins.graph_events) - before_events,
                'memory_before': state, 'memory_after': memory()}

    try:
        for case in cases:
            if case not in policies:
                raise ValueError('Unknown case: ' + case)
            no_subsurf, forearm = policies[case]
            check_memory('before case ' + case)
            event('case_start', case=case)
            ins.set_forearm(False)
            pb.matrix_basis = basis
            for obj, mod, enabled in submods:
                mod.show_viewport = False if no_subsurf else enabled
            for obj, key, coordinates, value, mute in snapshots:
                key.data.foreach_set('co', coordinates)
                key.value, key.mute = value, mute
                obj.data.shape_keys.update_tag()
                obj.data.update()
            rig.update_tag(refresh={'OBJECT'})
            bpy.context.view_layer.update()
            ins.set_forearm(forearm)
            for cache_name in ('_CACHE', '_OUTPUT_CACHE'):
                getattr(twist, cache_name, {}).clear()
            if hasattr(twist, 'validation_cache'):
                twist.validation_cache.clear()
            ins.reset()
            cold = timed(1, case, 'cache_cold')
            for index in range(args.warmups):
                check_memory('before warmup ' + case)
                move(-1 if index % 2 == 0 else 1)
            ins.reset()
            first_sign = -1 if args.warmups % 2 == 0 else 1
            samples = [timed(first_sign if index % 2 == 0 else -first_sign, case, index) for index in range(args.repeats)]
            wall = [sample['wall_seconds'] for sample in samples]
            component = ins.snapshot()
            graph_events = list(ins.graph_events)
            # Sampling occurs outside timing and cannot inflate measured updates.
            check_memory('before deformation witness ' + case)
            move(0)
            pose_before = sample_mesh(body, args.sample_vertices)
            move(1)
            pose_after = sample_mesh(body, args.sample_vertices)
            witness = point_change(pose_before, pose_after)
            profile = cProfile.Profile()
            check_memory('before profile ' + case)
            profile.enable()
            profile_start = time.perf_counter()
            move(-1)
            profile_elapsed = time.perf_counter() - profile_start
            profile.disable()
            profiler_path = Path(args.output).with_name(Path(args.output).stem + '_' + case + '.prof')
            profile.dump_stats(str(profiler_path))
            result = {'name': case, 'subsurf_disabled': no_subsurf, 'forearm_enabled': forearm,
                'forearm_handlers_present': [{'list': group, 'name': wrapped.__name__,
                    'present': wrapped in getattr(bpy.app.handlers, group)} for group, _, wrapped in ins.handlers_original],
                'cold': cold, 'samples': samples, 'p50_wall_seconds': statistics.median(wall),
                'p95_wall_seconds': percentile(wall, 95), 'min_wall_seconds': min(wall),
                'max_wall_seconds': max(wall), 'components_warm_samples': component,
                'depsgraph_update_events_warm': graph_events,
                'depsgraph_debug_stats': optional_read('depsgraph debug stats',
                    lambda: bpy.context.evaluated_depsgraph_get().debug_stats()),
                'deformation_witness': witness, 'evaluated_body': {key: value for key,value in pose_after.items() if key != 'points'},
                'profile_seconds': profile_elapsed, 'profile_path': str(profiler_path),
                'profile_top_cumulative': stats_rows(profile), 'forearm_errors': dict(twist._ERRORS),
                'memory_after_case': memory()}
            report['timing']['cases'].append(result)
            write_report(args, report)
            event('case_end', case=case, p50_seconds=result['p50_wall_seconds'],
                  p95_seconds=result['p95_wall_seconds'], memory=result['memory_after_case'])
            print('ARM_DRAG_CASE', json.dumps({'case': case, 'p50_ms': result['p50_wall_seconds'] * 1000,
                  'p95_ms': result['p95_wall_seconds'] * 1000, 'valid_deformation': witness['valid']}), flush=True)
    finally:
        ins.set_forearm(False)
        pb.matrix_basis = basis
        for obj, mod, enabled in submods:
            mod.show_viewport = enabled
        for obj, key, coordinates, value, mute in snapshots:
            key.data.foreach_set('co', coordinates)
            key.value, key.mute = value, mute
            obj.data.shape_keys.update_tag()
            obj.data.update()
        ins.restore()
        rig.update_tag(refresh={'OBJECT'})
        bpy.context.view_layer.update()
        restored_pose = pose_channels(rig)
        pose_error = max((max(abs(a-b) for a,b in zip(original_pose[name], restored_pose[name]))
                          for name in original_pose), default=0.0)
        report['restoration'] = {'input_sha256_after': sha256(input_path),
            'input_file_unchanged': sha256(input_path) == report['input']['sha256_before'],
            'pose_channels_restored': pose_error <= 1e-6, 'pose_basis_max_error': pose_error,
            'pose_reference': 'benchmark start, after any isolated Original-to-Controls switch',
            'subsurf_flags_restored': all(mod.show_viewport == enabled for obj, mod, enabled in submods),
            'save_called': False, 'handlers_after': handler_inventory()}
        report['memory_end'] = memory()
    report['status'] = 'complete'


def write_report(args, report):
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding='utf-8')


if __name__ == '__main__':
    args = arguments()
    args.repeats = max(2, min(args.repeats, 12))
    args.warmups = max(0, min(args.warmups, 3))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    report = {'schema': 1, 'status': 'started', 'args': vars(args),
        'limits': ['Background CPU/depsgraph test, not end-to-end interactive latency.',
             'Only installed Character Designer is explicitly registered; other GUI add-ons may differ.',
             'No render, frame stepping, scene save, installation change or artist-window connection.',
             'No-subdivision and no-correction cases are isolated diagnostic counterfactuals.',
             'Warm p95 uses a small sample and must not be presented as a long-term guarantee.',
             'Process page faults include soft faults; system paging requires external counters.']}
    try:
        event('benchmark_start', input=args.input, output=args.output)
        main(args, report)
    except Exception as exc:
        report['status'] = 'error'
        report['error'] = str(exc)
        report['traceback'] = traceback.format_exc()
        report['partial_results_preserved'] = True
        traceback.print_exc()
    finally:
        write_report(args, report)
        event('benchmark_end', status=report['status'], output=args.output)
        print('ARM_DRAG_RESULT', json.dumps({'status': report['status'], 'output': args.output,
              'error': report.get('error')}), flush=True)
