"""Protected X copy: fresh Forearm preview/cancel/commit and surface proof.

Root alone launches this script in --background --factory-startup. It never
saves a blend, adopts unrecorded keys, edits weights, or changes native Rest.
The old numeric profile is optional and requires exact current loop anchors.
"""
from array import array
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
REPOSITORY = Path('D:/MyRepository/Blender-addons-by-Randy')
PROJECT = HERE.parent.parent
CANDIDATE = PROJECT / 'validation/character_export_fix_20261009/forearm_roll_07712_runtime/character_designer'
MANIFEST = CANDIDATE.parent / 'release_projection_07712.json'
BACKUP_SHA = '15e3593a16ccd53a85690e3f9c862a2338b58317291e43a9a8cda7acdd25eebb'
PROJECTION_SHA = '2c6e63bfe3919a2ed224da69aede0456315fcde35c49db187fcdf5872b8e34a6'
REPORT = {}
REPORT_PATH = HERE / 'fresh_actual_report.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(value):
    import bpy
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bpy.types.ID):
        return [type(value).__name__, value.name]
    if hasattr(value, 'keys'):
        return {str(k): plain(value[k]) for k in value.keys()}
    try:
        return [plain(v) for v in value]
    except TypeError:
        return str(value)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def double_quaternion_angle(left, right):
    """Same geodesic angle using atan2, avoiding float32 acos near identity."""
    a, b = [float(v) for v in left], [float(v) for v in right]
    an, bn = math.sqrt(sum(v*v for v in a)), math.sqrt(sum(v*v for v in b))
    a, b = [v/an for v in a], [v/bn for v in b]
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    scalar = aw*bw + ax*bx + ay*by + az*bz
    vector = (aw*bx - ax*bw - ay*bz + az*by,
              aw*by + ax*bz - ay*bw - az*bx,
              aw*bz - ax*by + ay*bx - az*bw)
    return 2. * math.atan2(math.sqrt(sum(v*v for v in vector)), abs(scalar))


def coordinates(collection):
    values = array('f', [0.]) * (len(collection) * 3)
    collection.foreach_get('co', values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def rna(owner):
    result = {}
    for prop in owner.bl_rna.properties:
        if prop.identifier == 'rna_type' or prop.type == 'COLLECTION':
            continue
        try:
            result[prop.identifier] = plain(getattr(owner, prop.identifier))
        except (AttributeError, TypeError, RuntimeError):
            continue
    return result


def animation(owner):
    ad = owner.animation_data
    if ad is None:
        return None
    return {'action': ad.action.name if ad.action else None,
            'slot': getattr(getattr(ad, 'action_slot', None), 'identifier', None),
            'nla': [{'state': rna(track), 'strips': [rna(strip) for strip in track.strips]}
                    for track in ad.nla_tracks],
            'drivers': [{'path': curve.data_path, 'index': curve.array_index,
                         'type': curve.driver.type, 'expression': curve.driver.expression,
                         'use_self': curve.driver.use_self,
                         'variables': [{'name': variable.name, 'type': variable.type,
                                        'targets': [rna(target) for target in variable.targets]}
                                       for variable in curve.driver.variables]}
                        for curve in ad.drivers]}


def protected_snapshot(skip_keys=(), *, committed=False):
    """Include every artist key, mesh geometry/weight, native channel, action."""
    import bpy
    from character_designer import limb_ik, forearm_twist as runtime
    result = {'objects': {}, 'meshes': {}, 'rigs': {}, 'actions': {},
              'frame': [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe]}
    result['scene'] = {'props': {k: plain(bpy.context.scene[k]) for k in bpy.context.scene.keys()
                               if not (committed and k == runtime.LOCK_KEY)},
                       'render_lock': None if committed else bpy.context.scene.render.use_lock_interface}
    for obj in bpy.data.objects:
        props = {k: plain(obj[k]) for k in obj.keys()
                 if not (committed and obj.name == 'Cosha' and k == runtime.RECORD_KEY)}
        result['objects'][obj.name] = {
            'data': obj.data.name if obj.data else None, 'props': props,
            'animation': animation(obj),
            'basis': plain(obj.matrix_basis), 'parent_inverse': plain(obj.matrix_parent_inverse),
            'raw': {field: plain(getattr(obj, field)) for field in
                    ('location', 'rotation_mode', 'rotation_euler', 'rotation_quaternion',
                     'rotation_axis_angle', 'scale', 'delta_location', 'delta_rotation_euler',
                     'delta_rotation_quaternion', 'delta_scale', 'hide_viewport', 'hide_render', 'hide_select')},
            'parent': obj.parent.name if obj.parent else None,
            'modifiers': [rna(mod) for mod in obj.modifiers],
            'constraints': [rna(con) for con in obj.constraints]}
        if obj.type == 'MESH':
            keys = obj.data.shape_keys
            result['meshes'][obj.name] = {
                'geometry': coordinates(obj.data.vertices),
                'edges': [list(e.vertices) for e in obj.data.edges],
                'faces': [list(p.vertices) for p in obj.data.polygons],
                'weights': [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices],
                'groups': [(g.name, g.lock_weight) for g in obj.vertex_groups],
                'keys': {} if keys is None else {
                    key.name: {'coords': coordinates(key.data), 'state': {
                        k: v for k, v in rna(key).items() if k not in ('id_data',)}}
                    for key in keys.key_blocks if not (obj.name == 'Cosha' and key.name in skip_keys)},
                'active_key': obj.active_shape_key_index, 'pin': obj.show_only_shape_key}
            result['meshes'][obj.name]['animation'] = animation(keys) if keys else None
            result['meshes'][obj.name]['data_props'] = {k: plain(obj.data[k]) for k in obj.data.keys()}
        if obj.type == 'ARMATURE':
            result['rigs'][obj.name] = {
                pb.name: {'rest': plain(pb.bone.matrix_local), 'parent': pb.parent.name if pb.parent else None,
                    'connect': pb.bone.use_connect, 'deform': pb.bone.use_deform,
                    'location': plain(pb.location), 'mode': pb.rotation_mode,
                    'euler': plain(pb.rotation_euler), 'quaternion': plain(pb.rotation_quaternion),
                    'axis_angle': plain(pb.rotation_axis_angle), 'scale': plain(pb.scale),
                    'bbone': {p.identifier: plain(getattr(pb, p.identifier)) for p in pb.bl_rna.properties
                              if p.identifier.startswith('bbone_') and p.type != 'COLLECTION'},
                    'bone_props': plain(pb.bone), 'props': {k: plain(pb[k]) for k in pb.keys()},
                    'constraints': [rna(con) for con in pb.constraints]}
                for pb in obj.pose.bones}
    for action in bpy.data.actions:
        result['actions'][action.name] = {'props': {k: plain(action[k]) for k in action.keys()},
            'curves': [{'path': c.data_path, 'index': c.array_index,
                        'points': [rna(p) for p in c.keyframe_points],
                        'modifiers': [rna(m) for m in c.modifiers]} for c in limb_ik._fcurves_for_action(action)]}
    return result


def compare(before, after, label):
    if before != after:
        changed = [f'{category}/{name}' for category in before if isinstance(before[category], dict)
                   for name in set(before[category]) | set(after.get(category, {}))
                   if before[category].get(name) != after.get(category, {}).get(name)]
        raise AssertionError(f'{label}: protected state differs: {changed[:15]}')


def independent_wrist(arm, chain):
    import bpy
    from mathutils import Vector, Quaternion
    bpy.context.view_layer.update()
    pose = arm.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose
    lower, hand = chain[1:]
    lo = pose.bones[lower].matrix @ arm.data.bones[lower].matrix_local.inverted()
    hi = pose.bones[hand].matrix @ arm.data.bones[hand].matrix_local.inverted()
    axis = (arm.data.bones[lower].tail_local - arm.data.bones[lower].head_local).normalized()
    relative = lo.to_quaternion().normalized().conjugated() @ hi.to_quaternion().normalized()
    relative.normalize()
    if relative.w < 0:
        relative.negate()
    angle = math.remainder(2 * math.atan2(Vector((relative.x, relative.y, relative.z)).dot(axis), relative.w), math.tau)
    return angle, (relative @ Quaternion(axis, -angle)).normalized(), lo


def evaluated_surface(obj, *, original_vertices=False):
    """Temporarily hide only the post-skin Subdivision in this disposable copy."""
    import bpy
    from character_designer import forearm_twist as runtime
    mods = list(obj.modifiers)[1:] if original_vertices else []
    assert all(m.type == 'SUBSURF' for m in mods), 'Unexpected surface modifier: refuse changing it.'
    old_busy = runtime._BUSY
    flags = [(m, m.show_viewport) for m in mods]
    runtime._BUSY = True
    try:
        for mod, _flag in flags:
            mod.show_viewport = False
        bpy.context.view_layer.update()
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        data = evaluated.to_mesh()
        try:
            return [v.co.copy() for v in data.vertices]
        finally:
            evaluated.to_mesh_clear()
    finally:
        for mod, flag in flags:
            mod.show_viewport = flag
        bpy.context.view_layer.update()
        runtime._BUSY = old_busy


def verify_angles(obj, arm, record, report, *, direct_y=False):
    import bpy
    from mathutils import Matrix, Quaternion, Vector
    from character_designer import forearm_twist as runtime
    before_angle, before_swing, before_lower_deform = independent_wrist(arm, record['chain'])
    target = arm.pose.bones[runtime._SESSION['target']]
    original_euler = tuple(runtime._SESSION['rotation'])
    before_matrix = plain(target.matrix)
    before_basis = plain(target.matrix_basis)
    assert target.rotation_mode == 'XYZ', 'Actual Hand IK controller must keep its XYZ UI channels.'
    basis = obj.data.shape_keys.reference_key
    # All existing keys in this actual artist capture have zero value. Keep
    # that premise explicit so Basis is an independently justified input.
    owned = {r['key'] for r in runtime._records(obj).values()}
    assert all(key.value == 0 or key.name in owned or key == basis
               for key in obj.data.shape_keys.key_blocks), 'Active artist mix requires a different independent oracle.'
    baseline_surface = evaluated_surface(obj)
    to_arm = arm.matrix_world.inverted() @ obj.matrix_world
    lower = arm.data.bones[record['chain'][1]]
    axis = (lower.tail_local - lower.head_local).normalized()
    pivot = lower.tail_local
    input_frame = None
    original_basis_rotation = Matrix(before_basis).to_quaternion().normalized()
    original_hand_deform = (before_lower_deform.to_quaternion().normalized()
                            @ before_swing @ Quaternion(axis, before_angle)).normalized()
    if direct_y:
        # Independently derive the production COPY_ROTATION BEFORE contract.
        # Its hidden child cancels neutral Rest and the common CUSTOM space
        # removes the live parent. A changed input B therefore applies
        # delta = F * B_new * inverse(B_old) * inverse(F) before the hand,
        # where F = parentPose * inverse(parentRest) * targetRest. This is
        # rotation in the controller's input frame; it need not preserve the
        # numerical solver's original wrist swing about the posed forearm.
        assert target.parent is not None and target.bone.use_inherit_rotation
        assert target.bone.inherit_scale == 'FULL'
        parent = target.parent
        input_frame = (parent.matrix.to_quaternion().normalized()
                       @ parent.bone.matrix_local.to_quaternion().normalized().inverted()
                       @ target.bone.matrix_local.to_quaternion().normalized()).normalized()
        frame_error = double_quaternion_angle(
            input_frame @ original_basis_rotation, Matrix(before_matrix).to_quaternion().normalized())
        assert frame_error < 5e-4, 'Actual controller frame does not follow its native Rest/parent proof.'
        hand = arm.pose.bones[record['chain'][2]]
        active = [con for con in hand.constraints if not con.mute and con.influence > 1e-7]
        assert len(active) == 1, 'Unexpected native wrist constraint dependency.'
        con = active[0]
        helper = arm.pose.bones.get(con.subtarget)
        assert (con.type == 'COPY_ROTATION' and con.target == arm and helper and helper.parent == target
                and con.mix_mode == 'BEFORE' and con.influence == 1.
                and con.target_space == con.owner_space == 'CUSTOM'
                and con.space_object == arm and con.space_subtarget == parent.name
                and all(getattr(con, f'use_{axis_name}') for axis_name in 'xyz')
                and not any(getattr(con, f'invert_{axis_name}') for axis_name in 'xyz')), 'Actual wrist does not use the validated Auto Align parent-delta route.'
    for degrees in (45., 90.):
        if direct_y:
            # This is the actual Target Rotation / Twist (Y) UI write. The
            # numerical preview solver must not hide a misaligned local axis.
            target.rotation_euler = (original_euler[0], original_euler[1] + math.radians(degrees), original_euler[2])
            bpy.context.view_layer.update()
            runtime.update_runtime(bpy.context.scene, bpy.context.evaluated_depsgraph_get())
        else:
            runtime._test_pose(bpy.context, math.radians(degrees))
        actual, swing, lo = independent_wrist(arm, record['chain'])
        expected_angle = math.radians(degrees) + (before_angle if direct_y else 0.)
        expected_swing = before_swing
        ui_analytic = None
        if direct_y:
            assert max(abs(lo[i][j] - before_lower_deform[i][j]) for i in range(4) for j in range(4)) < 1e-6, 'UI rotation unexpectedly changed the solved forearm.'
            new_basis_rotation = target.matrix_basis.to_quaternion().normalized()
            input_delta = (input_frame @ new_basis_rotation @ original_basis_rotation.inverted()
                           @ input_frame.inverted()).normalized()
            predicted_hand = (input_delta @ original_hand_deform).normalized()
            predicted_relative = (lo.to_quaternion().normalized().inverted() @ predicted_hand).normalized()
            if predicted_relative.w < 0:
                predicted_relative.negate()
            projected = Vector((predicted_relative.x, predicted_relative.y, predicted_relative.z)).dot(axis)
            predicted_angle = math.remainder(2. * math.atan2(projected, predicted_relative.w), math.tau)
            expected_swing = (predicted_relative @ Quaternion(axis, -predicted_angle)).normalized()
            actual_hand = (lo.to_quaternion().normalized() @ swing @ Quaternion(axis, actual)).normalized()
            ui_analytic = {'input_frame': plain(input_frame), 'input_delta': plain(input_delta),
                           'predicted_hand_deform': plain(predicted_hand),
                           'predicted_twist_degrees': math.degrees(predicted_angle),
                           'predicted_swing': plain(expected_swing), 'frame_error': frame_error,
                           'whole_hand_error': double_quaternion_angle(predicted_hand, actual_hand)}
        swing_error = double_quaternion_angle(expected_swing, swing)
        sample = {'route': 'actual_ui_twist_y' if direct_y else 'preview_solver',
                  'requested_degrees': degrees, 'expected_degrees': math.degrees(expected_angle),
                  'before_degrees': math.degrees(before_angle), 'evaluated_degrees': math.degrees(actual),
                  'swing_difference': swing.rotation_difference(before_swing).angle,
                  'swing_difference_double_atan2': double_quaternion_angle(before_swing, swing),
                  'swing_error_against_expected': swing_error, 'ui_analytic': ui_analytic,
                  'before_swing': plain(before_swing), 'actual_swing': plain(swing),
                  'controller': {'name': target.name, 'rotation_mode': target.rotation_mode,
                                 'original_euler': original_euler, 'actual_euler': plain(target.rotation_euler),
                                 'location': plain(target.location), 'scale': plain(target.scale),
                                 'before_matrix': before_matrix, 'before_basis': before_basis,
                                 'actual_matrix': plain(target.matrix), 'actual_basis': plain(target.matrix_basis)},
                  'native_rest': {name: plain(arm.data.bones[name].matrix_local) for name in record['chain']},
                  'native_pose': {name: plain(arm.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones[name].matrix)
                                  for name in record['chain']}, 'phase': 'wrist_checks'}
        report.append(sample)
        if direct_y:
            assert abs(actual - predicted_angle) < 1e-4, 'UI wrist twist differs from independent parent-delta geometry.'
            assert ui_analytic['whole_hand_error'] < 5e-4, 'UI hand rotation differs from independent parent-delta geometry.'
        assert abs(actual - expected_angle) < 1e-4, 'Evaluated wrist angle does not follow controller.'
        assert swing_error < 5e-4, 'Wrist swing differs from the route-specific independent expectation.'
        assert obj.name not in runtime._ERRORS, runtime._ERRORS.get(obj.name)
        result = evaluated_surface(obj, original_vertices=True)
        assert len(result) == len(obj.data.vertices)
        pose = arm.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose
        matrices = {bone.name: pose.bones[bone.name].matrix @ bone.matrix_local.inverted()
                    for bone in arm.data.bones if bone.use_deform}
        measured = []
        errors = []
        surface_errors = []
        for ring in record['rings'][record['range_start']:record['range_end'] + 1]:
            for index in ring['vertices']:
                weights = {obj.vertex_groups[g.group].name: g.weight for g in obj.data.vertices[index].groups
                           if obj.vertex_groups[g.group].name in arm.data.bones
                           and arm.data.bones[obj.vertex_groups[g.group].name].use_deform and g.weight > 0}
                total = sum(weights.values())
                assert total > 0, 'Captured sleeve point lacks deform weights.'
                raw = to_arm @ basis.data[index].co
                expected = Vector((0., 0., 0.))
                for name, weight in weights.items():
                    fraction = (ring['ratio'] if name == record['chain'][1] else
                                ring['ratio'] - 1. if name == record['chain'][2] else 0.)
                    angle = actual * fraction
                    offset = raw - pivot
                    # Rodrigues' formula, independent of production math.
                    rotated = pivot + (offset * math.cos(angle)
                                       + axis.cross(offset) * math.sin(angle)
                                       + axis * axis.dot(offset) * (1. - math.cos(angle)))
                    expected += (weight / total) * (matrices[name] @ rotated)
                surface_errors.append(((to_arm @ result[index]) - expected).length)
                # A pure lower-bone point gives a circular-arc oracle without
                # calling any production correction or inverse-skinning math.
                if total <= 0 or weights.get(lower.name, 0) / total < .99999:
                    continue
                corrected = lo.inverted() @ (to_arm @ result[index])
                a, b = raw - pivot, corrected - pivot
                a -= axis * a.dot(axis)
                b -= axis * b.dot(axis)
                if min(a.length, b.length) < 1e-6:
                    continue
                angle = math.atan2(axis.dot(a.cross(b)), a.dot(b))
                errors.append(abs(angle - math.radians(degrees) * ring['ratio']))
                assert abs(a.length - b.length) < 3e-5, 'Sleeve lost radial distance.'
                measured.append({'vertex': index, 'ratio': ring['ratio'], 'surface_angle': math.degrees(angle)})
        assert surface_errors and max(surface_errors) < 3e-5, 'Sleeve surface did not follow independent forward skinning.'
        if errors:
            assert max(errors) < 5e-4, 'Sleeve surface did not follow the saved radial profile.'
        subdivided = evaluated_surface(obj)
        assert len(subdivided) == len(baseline_surface)
        movement = max((a-b).length for a, b in zip(subdivided, baseline_surface))
        assert movement > 1e-4, 'Actual subdivided sleeve did not move.'
        sample.update({'radial_max_error': max(errors) if errors else None,
                       'forward_skinning_max_error': max(surface_errors), 'subdivided_movement': movement,
                       'surface_samples': measured, 'phase': 'PASS'})
    if direct_y:
        target.rotation_euler = original_euler
        bpy.context.view_layer.update()
        runtime.update_runtime(bpy.context.scene, bpy.context.evaluated_depsgraph_get())


def main():
    global REPORT_PATH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-profile', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    REPORT_PATH = HERE / ('fresh_actual_historical_report.json' if args.historical_profile else 'fresh_actual_report.json')
    import bpy
    assert bpy.app.background and not bpy.data.filepath, 'Require disposable factory-startup background Blender.'
    backup = HERE / 'X_before_forearm_twist_fix.blend'
    assert sha(backup) == BACKUP_SHA, 'Protected actual input changed.'
    artist = PROJECT / 'X.blend'
    artist_sha = sha(artist)
    sys.path.insert(0, str(REPOSITORY / 'tools'))
    from release_projection import load_source
    source = load_source('character_designer', MANIFEST, root=REPOSITORY)
    assert source.root == CANDIDATE.resolve() and source.version == '0.77.12'
    assert source.projection_sha256 == PROJECTION_SHA
    sys.path.insert(0, str(CANDIDATE.parent))
    import character_designer
    assert Path(character_designer.__file__).resolve().parent == CANDIDATE.resolve()
    character_designer.register()
    bpy.ops.wm.open_mainfile(filepath=str(backup))
    from character_designer import forearm_twist as runtime
    runtime._complete_runtime_lifecycle()
    obj, arm = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
    assert len(obj.data.vertices) == 3658 and runtime._records(obj) == {} and runtime._SESSION is None
    assert bpy.context.scene.frame_current == 46
    before = protected_snapshot()
    selection = {'active': bpy.context.object.name, 'mode': bpy.context.mode,
                 'selected': [candidate.name for candidate in bpy.context.selected_objects]}
    report = REPORT
    report.update({'backup': str(backup), 'backup_sha256': BACKUP_SHA, 'projection_sha256': source.projection_sha256,
              'original_keys': list(obj.data.shape_keys.key_blocks.keys()), 'historical_profile': args.historical_profile,
              'preview': {}, 'committed': {}, 'checks': []})
    settings = bpy.context.window_manager.character_designer_forearm_twist
    saved_ui = {p.identifier: getattr(settings, p.identifier) for p in settings.bl_rna.properties
                if p.identifier not in ('rna_type', 'name') and p.type not in ('POINTER', 'COLLECTION')}
    historical = json.loads((HERE / 'historical_profile_reference.json').read_text(encoding='utf-8'))['records']

    def start():
        record = runtime.start_paired_test(bpy.context)
        report['fresh_capture'] = copy.deepcopy(record)
        report['historical_anchors'] = historical[runtime._SESSION['side']]['rings']
        assert not runtime._SESSION['pose_locked'], 'Actual controller is animated; do not overwrite it.'
        if args.historical_profile:
            old = historical[runtime._SESSION['side']]
            saved = {frozenset(r['vertices']): r['ratio'] for r in old['rings']}
            assert len(saved) == len(record['rings']) and all(frozenset(r['vertices']) in saved for r in record['rings']), 'Historical anchors do not match fresh capture; refuse profile transfer.'
            for index, ring in enumerate(record['rings']):
                runtime.set_ratio(bpy.context, index, saved[frozenset(ring['vertices'])])
            record = runtime._records(obj)[runtime._SESSION['side']]
        return record

    runtime._UI_BUSY = True
    settings.side, settings.symmetry = 'L', True
    runtime._UI_BUSY = False
    try:
        record = start()
        report['preview']['L'] = []
        verify_angles(obj, arm, record, report['preview']['L'], direct_y=True)
        verify_angles(obj, arm, record, report['preview']['L'])
        runtime.finish_test(bpy.context, False)
        compare(before, protected_snapshot(), 'Fresh preview cancellation')
        report['checks'].append('Fresh preview cancellation preserved every existing key, geometry, weight, native input and action.')
        record = start()
        runtime.finish_test(bpy.context, True)
        records = runtime._records(obj)
        assert set(records) == {'L', 'R'} and runtime._SESSION is None and runtime.PREVIEW_KEY not in obj
        new_keys = {records[s]['key'] for s in records}
        assert new_keys.isdisjoint(report['original_keys']) and len(new_keys) == 2
        # Ignore only the two proven newly owned outputs and their metadata.
        expected = copy.deepcopy(before)
        expected['objects']['Cosha']['props'].pop(runtime.RECORD_KEY, None)
        expected['scene']['props'].pop(runtime.LOCK_KEY, None)
        expected['scene']['render_lock'] = None
        compare(expected, protected_snapshot(new_keys, committed=True), 'Fresh pair commit')
        committed = protected_snapshot()
        for side in ('L', 'R'):
            if bpy.context.object and bpy.context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            for selected in bpy.context.selected_objects:
                selected.select_set(False)
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            runtime._UI_BUSY = True
            settings.side = side
            runtime._UI_BUSY = False
            record = runtime.start_paired_test(bpy.context)
            report['committed'][side] = []
            verify_angles(obj, arm, record, report['committed'][side], direct_y=True)
            verify_angles(obj, arm, record, report['committed'][side])
            runtime.finish_test(bpy.context, False)
            compare(committed, protected_snapshot(), f'Committed {side} trial cancel')
        report['records'] = runtime._records(obj)
        report['checks'].append('Both actual Hand IK controllers produced independently measured 45/90-degree sleeve rotation.')
        report['checks'].append('All four unrecorded old Forearm keys retained byte-identical coordinates and raw state.')
        report['status'] = 'PASS'
    finally:
        try:
            report['status'] = report.get('status', 'FAIL')
            if runtime._SESSION is not None:
                runtime.finish_test(bpy.context, False)
            runtime._UI_BUSY = True
            for name, value in saved_ui.items():
                setattr(settings, name, value)
            runtime._UI_BUSY = False
            runtime._restore_selection(bpy.context, selection)
            assert sha(artist) == artist_sha and sha(backup) == BACKUP_SHA, 'Input files changed.'
            assert Path(bpy.data.filepath).resolve() == backup.resolve(), 'Artist file opened for mutation.'
            report['cleanup'] = 'Preview restored; artist and protected backup bytes unchanged.'
        finally:
            REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('ACTUAL_FRESH_FOREARM_PASS', str(REPORT_PATH), report['records']['L']['key'], report['records']['R']['key'], flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        (HERE / 'fresh_actual_failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
        REPORT['status'] = 'FAIL'
        REPORT['exception'] = traceback.format_exc()
        REPORT_PATH.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
        raise
