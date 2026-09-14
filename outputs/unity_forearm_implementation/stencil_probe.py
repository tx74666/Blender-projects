"""Read-only X.blend experiment; all mutations stay in the background process."""
import json
import hashlib
import math
import sys
import time
from array import array
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import forearm_twist as ft
from character_designer import forearm_twist_math as fm
from character_designer import forearm_twist_profile as fp

OUT = Path(r'D:\Blender\Projects\Character\X\outputs\unity_forearm_implementation')


def coords(items):
    data = array('f', [0.0]) * (3 * len(items))
    items.foreach_get('co', data)
    return data


def evaluate(obj):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev = obj.evaluated_get(dg)
    mesh = ev.to_mesh()
    try:
        return coords(mesh.vertices)
    finally:
        ev.to_mesh_clear()


def build_sparse_stencils(obj, source_ids):
    """Geometry impulses yield exact linear subdivision responses, three per eval.

    Only fixed-resolution Subdivision after Armature is supported here. No merge,
    clipping, displace, normal offsets or topology-dependent nodes are assumed linear.
    Returns CSR rows keyed by dense exported vertex, indexing the supplied sources.
    """
    started = time.perf_counter()
    clone = obj.copy()
    clone.data = obj.data.copy()
    clone.name = '.Stencil Probe'
    for name in tuple(clone.keys()):
        if name.startswith('character_designer_'):
            del clone[name]
    bpy.context.scene.collection.objects.link(clone)
    clone.animation_data_clear()
    if clone.data.shape_keys:
        clone.shape_key_clear()
    for mod in tuple(clone.modifiers):
        if mod.type == 'ARMATURE' or not mod.show_viewport:
            clone.modifiers.remove(mod)
        elif mod.type != 'SUBSURF':
            raise ValueError('Stencil prototype supports only post-skin fixed Subdivision: ' + mod.type)
    for constraint in tuple(clone.constraints):
        clone.constraints.remove(constraint)
    zero = array('f', [0.0]) * (3 * len(clone.data.vertices))
    rows = None
    try:
        for start in range(0, len(source_ids), 3):
            impulse = zero[:]
            for channel, source in enumerate(source_ids[start:start + 3]):
                impulse[3 * source + channel] = 1.0
            clone.data.vertices.foreach_set('co', impulse)
            clone.data.update()
            values = evaluate(clone)
            if rows is None:
                rows = [[] for _ in range(len(values) // 3)]
            for dest, row in enumerate(rows):
                for channel in range(min(3, len(source_ids) - start)):
                    weight = values[3 * dest + channel]
                    if abs(weight) > 1e-9:
                        row.append((start + channel, weight))
        offsets, ids, weights = [0], [], []
        for row in rows:
            ids.extend(i for i, _ in row)
            weights.extend(w for _, w in row)
            offsets.append(len(ids))
        return dict(source_ids=source_ids, offsets=offsets, source_indices=ids,
                    weights=weights, elapsed_seconds=time.perf_counter() - started,
                    dense_count=len(rows), nonempty_rows=sum(bool(row) for row in rows))
    finally:
        data = clone.data
        bpy.data.objects.remove(clone, do_unlink=True)
        if data.users == 0:
            bpy.data.meshes.remove(data)


def propagate(stencil, deltas):
    result = []
    for dest in range(stencil['dense_count']):
        d = Vector((0, 0, 0))
        for at in range(stencil['offsets'][dest], stencil['offsets'][dest + 1]):
            d += deltas[stencil['source_indices'][at]] * stencil['weights'][at]
        result.append(d)
    return result


def run():
    started = time.perf_counter()
    obj = bpy.data.objects['Cosha']
    arm = ft._check_mesh(obj)
    records = ft._records(obj)
    for handler in tuple(bpy.app.handlers.depsgraph_update_post):
        if getattr(handler, '__module__', '').startswith('character_designer'):
            bpy.app.handlers.depsgraph_update_post.remove(handler)
    for item in (obj, arm, obj.data.shape_keys):
        if item:
            item.animation_data_clear()
    for bone in arm.pose.bones:
        for constraint in tuple(bone.constraints):
            bone.constraints.remove(constraint)
        bone.matrix_basis = Matrix.Identity(4)
    for key in obj.data.shape_keys.key_blocks:
        key.value = 0
        key.mute = False
    owned = {r['key'] for r in records.values()}
    source_ids = sorted({i for r in records.values() for i in r['vertices']})
    report = {'source_file': bpy.data.filepath,
              'source_sha256': hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
              'source_vertices': len(obj.data.vertices),
              'modifiers': [{'name': m.name, 'type': m.type, 'enabled': m.show_viewport,
                             'levels': getattr(m, 'levels', None)} for m in obj.modifiers],
              'record_counts': {side: len(r['vertices']) for side, r in records.items()},
              'record_bounds': {side: {k:r.get(k) for k in ('range_start','range_end','transition')} for side,r in records.items()}}
    stencil = build_sparse_stencils(obj, source_ids)
    report['stencil'] = {k: v for k, v in stencil.items() if k not in ('source_ids','offsets','source_indices','weights')}
    report['stencil']['entries'] = len(stencil['weights'])
    (OUT / 'stencil.json').write_text(json.dumps(stencil, separators=(',', ':')), encoding='utf8')
    source_map = {v: i for i, v in enumerate(source_ids)}
    cases = []
    fixture_cases = []
    for pose in ('flat', 'bent_raised_root_swing'):
        for angle_degrees in (-90, -45, 45, 90):
            for pb in arm.pose.bones:
                pb.matrix_basis = Matrix.Identity(4)
            if pose != 'flat':
                hips = arm.pose.bones.get('Hips')
                hips.rotation_mode = 'QUATERNION'
                hips.rotation_quaternion = Quaternion(Vector((0, 0, 1)), math.radians(63))
                for record in records.values():
                    upper, lower, hand = record['chain']
                    arm.pose.bones[upper].rotation_mode = 'QUATERNION'
                    arm.pose.bones[upper].rotation_quaternion = Quaternion(Vector((1, 0, 0)), math.radians(35))
                    arm.pose.bones[lower].rotation_mode = 'QUATERNION'
                    arm.pose.bones[lower].rotation_quaternion = Quaternion(Vector((0, 0, 1)), math.radians(65))
            bpy.context.view_layer.update()
            for side, record in records.items():
                lower, hand = record['chain'][1:]
                axis = (arm.data.bones[lower].tail_local - arm.data.bones[lower].head_local).normalized()
                pivot = arm.data.bones[hand].head_local
                d_lower = arm.pose.bones[lower].matrix @ arm.data.bones[lower].matrix_local.inverted()
                rot = Quaternion(axis, math.radians(angle_degrees))
                if pose != 'flat':
                    perpendicular = axis.cross(Vector((0, 0, 1))).normalized()
                    rot = Quaternion(perpendicular, math.radians(23)) @ rot
                arm.pose.bones[hand].matrix = (d_lower @ Matrix.Translation(pivot)
                    @ rot.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
                    @ arm.data.bones[hand].matrix_local)
                bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            ft._CACHE.clear()
            ft._OUTPUT_CACHE.clear()
            ft._calculate_records(obj, dg)
            corrected_dense = evaluate(obj)
            for name in owned:
                obj.data.shape_keys.key_blocks[name].mute = True
            obj.data.shape_keys.update_tag()
            ordinary_dense = evaluate(obj)
            for name in owned:
                obj.data.shape_keys.key_blocks[name].mute = False
            dg = bpy.context.evaluated_depsgraph_get()
            base = ft._input_mix(obj, source_ids, owned, dg)
            weights = ft._weights(obj, arm, source_ids)
            ev_arm = arm.evaluated_get(dg)
            to_arm = ev_arm.matrix_world.inverted() @ obj.evaluated_get(dg).matrix_world
            from_arm = to_arm.inverted().to_3x3()
            transforms = {name: ev_arm.pose.bones[name].matrix @ arm.data.bones[name].matrix_local.inverted()
                          for name in arm.data.bones.keys()}
            deltas = [Vector((0, 0, 0)) for _ in source_ids]
            sides = []
            for side, record in records.items():
                lower, hand = record['chain'][1:]
                axis = (arm.data.bones[lower].tail_local-arm.data.bones[lower].head_local).normalized()
                pivot = arm.data.bones[hand].head_local
                angle = fm.twist_angle(transforms[lower], transforms[hand], axis)
                knots = fp.profile_knots(record['rings'])
                bounded = 'range_start' in record
                if bounded:
                    first, last = fp.record_range(record)
                else:
                    knots = [(0.,0.)] + [(p,r) for p,r in knots if 1e-6 < p < 1-1e-6] + [(1.,1.)]
                for i, p in zip(record['vertices'], record['positions']):
                    influence = fp.range_influence(p, record['rings'], first,last,record.get('transition',.1)) if bounded else 1.
                    point = to_arm @ base[i]
                    ratio = fm.profile_ratio(p, knots)
                    ordinary = fm.blended_matrix(transforms, weights[i]) @ point
                    desired = fm.desired_vertex(point, transforms, weights[i],lower,hand,axis,pivot,ratio,angle=angle)
                    deltas[source_map[i]] += influence * (from_arm @ (desired-ordinary))
                sides.append({'side':side, 'angle_degrees':math.degrees(angle),
                              'lower_deformation': [list(row) for row in transforms[lower]],
                              'hand_deformation': [list(row) for row in transforms[hand]]})
            predicted = propagate(stencil, deltas)
            actual = [Vector(corrected_dense[i:i+3])-Vector(ordinary_dense[i:i+3]) for i in range(0,len(ordinary_dense),3)]
            errors = [(a-p).length for a,p in zip(actual,predicted)]
            nonempty = {i for i in range(stencil['dense_count']) if stencil['offsets'][i] != stencil['offsets'][i+1]}
            case = {'pose':pose, 'requested_degrees':angle_degrees, 'measured':[{k:v for k,v in s.items() if k in ('side','angle_degrees')} for s in sides],
                    'max_error_m':max(errors), 'rms_error_m':math.sqrt(sum(e*e for e in errors)/len(errors)),
                    'max_actual_extra_m':max(d.length for d in actual),
                    'outside_support_max_extra_m':max((d.length for i,d in enumerate(actual) if i not in nonempty), default=0.)}
            print(json.dumps(case), flush=True)
            cases.append(case)
            fixture_cases.append({'name':pose+'_'+str(angle_degrees), 'sides':sides,
                'to_armature': [list(row) for row in to_arm],
                'bone_pose_armature': {name:[list(row) for row in ev_arm.pose.bones[name].matrix] for name in arm.data.bones.keys()},
                'source_extra': [list(d) for d in deltas],
                'dense_extra': [list(actual[i]) for i in sorted(nonempty)],
                'dense_ids': sorted(nonempty)})
    report['cases'] = cases
    report['elapsed_seconds'] = time.perf_counter()-started
    report['pass'] = all(c['max_error_m'] < 2e-6 and c['outside_support_max_extra_m'] < 2e-6 for c in cases)
    (OUT/'stencil_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    (OUT/'stencil_golden.json').write_text(json.dumps({'stencil':stencil,
        'source_basis': [list(obj.data.shape_keys.reference_key.data[i].co) for i in source_ids],
        'source_weights': {str(i):weights[i] for i in source_ids},
        'bone_rest_armature': {b.name:[list(row) for row in b.matrix_local] for b in arm.data.bones},
        'records':records, 'cases':fixture_cases},separators=(',',':')),encoding='utf8')
    print('STENCIL_RESULT ' + json.dumps(report),flush=True)


if __name__ == '__main__':
    run()
