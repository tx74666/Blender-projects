"""SOURCE ONLY: small native Subsurf/skin-order probe; Root coordinates execution.

Blender 5.2: --factory-startup --background --python THIS -- --output NEW_DIR
            --core-sha256 SHA_OF_THIS_SCRIPT
Only the fixed completed PNS QA snapshot is opened. No CD registration, FBX,
Unity, Action scan, image-pixel scan, timeline seek, Cloth simulation or save.
The old PrivateFBXv3 0.471379mm failure and 0.05mm admission limit stay intact.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / 'actual_plain_native_skin_model_v4_e0b_52_20261007_123727_962_feab010a295d467eae8019cccff98ca8/result/cdesigner-unity-pns-qa/character.blend'
SNAPSHOT_SHA = 'ab48a806f8e228f3c878da65bab59fe9cdaff2bcbca037f258cf74cacd88dc71'
WORKER = Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_export_worker.py')
WORKER_SHA = '1716ff49a231cee8c0663fd17949583eabbfb7ce79791a459682930f40744dcb'
LIMIT_M, NUMERIC_M = 0.00005, 0.00000001
OLD_MAX_M = 0.0004713791436785606
RECORD, OWNER, RIG, SOURCE = ('character_designer_skirt_' + suffix for suffix in ('v1', 'owner', 'armature', 'source'))
ROLE = 'character_designer_skirt_surface_role'
CHANNELS = ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def matrix(value):
    return [list(row) for row in value]


def rna(owner):
    # The native source_contract convention; only modifier scalar/ID RNA.
    result = {}
    for prop in owner.bl_rna.properties:
        name = prop.identifier
        if name in {'rna_type', 'is_active'} or prop.is_readonly or prop.type == 'COLLECTION':
            continue
        value = getattr(owner, name)
        if prop.type == 'POINTER':
            if value is not None and not isinstance(value, bpy.types.ID):
                continue
            value = None if value is None else {'type': value.bl_rna.identifier, 'name': value.name}
        elif prop.is_array:
            value = matrix(value) if hasattr(value, 'row') else list(value)
        elif prop.type not in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}:
            raise RuntimeError('Unsupported modifier RNA: ' + name)
        result[name] = sorted(value) if isinstance(value, set) else value
    return result


def mesh_content(mesh):
    return {'points': [list(v.co) for v in mesh.vertices],
            'edges': [list(e.vertices) for e in mesh.edges],
            'faces': [list(p.vertices) for p in mesh.polygons],
            'loops': [[v.vertex_index, v.edge_index] for v in mesh.loops],
            'UV': [[u.name, [list(x.uv) for x in u.data]] for u in mesh.uv_layers],
            'material_indices': [p.material_index for p in mesh.polygons],
            'materials': [m.name if m else None for m in mesh.materials],
            'raw_keys': None if mesh.shape_keys is None else
                [[k.name, [list(v.co) for v in k.data], k.relative_key.name, k.value, k.mute]
                 for k in mesh.shape_keys.key_blocks]}


def named_weights(obj, mesh):
    names = [g.name for g in obj.vertex_groups]
    return [names, [[[names[g.group], float(g.weight)] for g in v.groups] for v in mesh.vertices]]


def author_guard(objects, meshes, rig):
    # Raw loaded meshes/UV/keys + full named weights; no Actions or image data.
    bones = [[b.name, b.parent.name if b.parent else None, matrix(b.matrix_local),
              list(b.head_local), list(b.tail_local), b.use_deform] for b in rig.data.bones]
    poses = [[p.name, p.rotation_mode, [list(getattr(p, c)) for c in CHANNELS], matrix(p.matrix_basis)]
             for p in rig.pose.bones]
    return {'RawMeshes_UV_Keys': digest([[m.name, mesh_content(m)] for m in meshes]),
            'FullNamedWeights': digest([[o.name, named_weights(o, o.data)] for o in objects if o.type == 'MESH']),
            'boneRest': digest(bones), 'nativePose': digest(poses),
            'pose_position': rig.data.pose_position,
            'home_frame': [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe],
            'home_unit_scale_length': bpy.context.scene.unit_settings.scale_length,
            'original_source_modifiers': [rna(m) for m in bpy.data.objects['Dress'].modifiers]}


def check(report, label, passed, detail=None, required=False):
    report.setdefault('checks', {})[label] = {'evaluated': True, 'passed': bool(passed), 'detail': detail}
    if required and not passed:
        raise RuntimeError(label)


def graph():
    bpy.context.view_layer.update()
    value = bpy.context.evaluated_depsgraph_get()
    value.update()
    return value


def evaluate(obj, flags, row, label):
    for modifier in obj.modifiers:
        modifier.show_viewport = flags[modifier.type]
    dg = graph()
    evaluated = obj.evaluated_get(dg)
    effective = [[m.name, m.type, m.show_viewport,
                  m.use_deform_preserve_volume if m.type == 'ARMATURE' else None]
                 for m in evaluated.modifiers]
    check(row, label + '_effective_modifier_flags',
          all(m.show_viewport == flags[m.type] for m in evaluated.modifiers), effective, required=True)
    check(row, label + '_effective_PreserveVolume',
          all(m.use_deform_preserve_volume == row['preserve_volume']
              for m in evaluated.modifiers if m.type == 'ARMATURE'), effective, required=True)
    positions = [m.object.evaluated_get(dg).data.pose_position for m in evaluated.modifiers if m.type == 'ARMATURE']
    check(row, label + '_effective_rig_pose_position',
          positions == [row['pose_position']], positions, required=True)
    if row['pose_position'] == 'POSE':
        components = [abs(a - b) for left, right in zip(row['home_source_world'], evaluated.matrix_world)
                      for a, b in zip(left, right)]
        check(row, label + '_current_source_world_exact',
              all(math.isfinite(v) for v in components) and max(components) <= NUMERIC_M,
              {'maximum_native_matrix_component': max(components)}, required=True)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=dg)
    try:
        value = mesh_content(mesh)
        value['points'] = [list(evaluated.matrix_world @ v.co) for v in mesh.vertices]
        value['full_named_weights_SHA'] = digest(named_weights(obj, mesh))
        value['skin'] = digest([value['full_named_weights_SHA'], value['UV'], value['material_indices'], value['materials']])
        check(row, label + '_finite', all(math.isfinite(x) for p in value['points'] for x in p), required=True)
        row.setdefault('samples', {})[label] = {'vertices': len(mesh.vertices),
            'modifiers': [[m.name, m.type, m.show_viewport] for m in obj.modifiers], 'skin_SHA': value['skin']}
        return value
    finally:
        evaluated.to_mesh_clear()


def pair(left, right, metres):
    ordered = {key: left[key] == right[key] for key in ('edges', 'faces', 'loops')}
    count = len(left['points']) == len(right['points'])
    result = {'evaluated': False, 'correspondence_evaluated': True,
              'same_index_count': count, 'ordered_topology': ordered,
              'skin_exact': left['skin'] == right['skin'],
              'full_named_weights_exact': left['full_named_weights_SHA'] == right['full_named_weights_SHA'],
              'UV_exact': left['UV'] == right['UV'],
              'material_indices_exact': left['material_indices'] == right['material_indices'],
              'material_slots_exact': left['materials'] == right['materials'], 'maximum_m': None, 'rms_m': None,
              'worst_index': None, 'within_0_05mm': None, 'within_numeric_0_00001mm': None}
    if not count or not all(ordered.values()):
        result['reason'] = 'Same-index correspondence not established; no remapping attempted.'
        return result
    errors = [math.sqrt(sum((a - b) ** 2 for a, b in zip(p, q))) * metres
              for p, q in zip(left['points'], right['points'])]
    worst = max(range(len(errors)), key=errors.__getitem__) if errors else None
    maximum = errors[worst] if worst is not None else 0.0
    result.update(maximum_m=maximum, rms_m=math.sqrt(sum(e * e for e in errors) / max(1, len(errors))),
                  evaluated=True,
                  worst_index=worst, within_0_05mm=maximum <= LIMIT_M,
                  within_numeric_0_00001mm=maximum <= NUMERIC_M)
    return result


def copy_object_data(source, owned):
    obj = source.copy()
    owned['objects'].append(obj)
    data = source.data.copy()
    owned['data'].append(data)
    obj.data = data
    return obj


def copy_mesh(source, scene, name, owned, output=None, skin=None, volume=None):
    obj = copy_object_data(source, owned)
    if output is not None:
        obj.modifiers.remove(obj.modifiers.get(output))
    if skin is not None:
        old_rig = obj.modifiers[0].object
        if obj.parent == old_rig:
            obj.parent = skin
        obj.modifiers[0].object = skin
        obj.modifiers[0].use_deform_preserve_volume = volume
    obj.name = name
    scene.collection.objects.link(obj)
    for key in tuple(obj.keys()):
        if key.startswith('character_designer_'):
            del obj[key]
    bpy.context.view_layer.update()
    obj.hide_set(False)
    return obj


def dispose(objects):
    for obj in reversed(objects['objects']):
        data = obj.data
        if data not in objects['protected_data'] and data not in objects['data']:
            objects['data'].append(data)  # Worker may replace its captured clone's data.
        bpy.data.objects.remove(obj, do_unlink=True)
    for block in reversed(objects['data']):
        try:
            if block.users == 0:
                collection = bpy.data.armatures if isinstance(block, bpy.types.Armature) else bpy.data.meshes
                collection.remove(block)
            else:
                raise RuntimeError('An owned copied datablock acquired an outside user.')
        except ReferenceError:
            pass  # A captured old input was already removed by this probe.


def run_case(label, pose_position, preserve_volume, source, rig, home, originals, worker, report, baseline):
    row = {'status': 'unmeasured', 'pose_position': pose_position, 'preserve_volume': preserve_volume,
           'home_source_world': baseline['source_world'], 'comparisons': {}, 'errors': []}
    report['cases'][label] = row
    scene, observations = None, {}
    owned = {'objects': [], 'data': [], 'protected_data': set(bpy.data.meshes) | set(bpy.data.armatures)}
    try:
        scene = bpy.data.scenes.new('Skin order QA ' + label)
        scene.unit_settings.scale_length = home.unit_settings.scale_length
        # Preserve actual current frame; never call frame_set or advance Cloth.
        scene.frame_current = home.frame_current
        scene.frame_subframe = home.frame_subframe
        for obj in originals:
            if obj != source:
                scene.collection.objects.link(obj)
        bpy.context.window.scene = scene
        private_rig = copy_object_data(rig, owned)
        scene.collection.objects.link(private_rig)
        # Remap self targets only on independent rig constraint/driver copies.
        check(row, 'independent_rig_data', private_rig != rig and private_rig.data != rig.data, required=True)
        for holder in (private_rig, *private_rig.pose.bones):
            for constraint in holder.constraints:
                if hasattr(constraint, 'target') and constraint.target == rig:
                    constraint.target = private_rig
        if private_rig.animation_data:
            for curve in private_rig.animation_data.drivers:
                for variable in curve.driver.variables:
                    for target in variable.targets:
                        if target.id == rig:
                            target.id = private_rig
        dg = graph()
        actual = private_rig.evaluated_get(dg)
        components = [abs(a - b) for name in rig.data.bones.keys()
                      for left, right in zip(baseline['pose'][name], actual.pose.bones[name].matrix)
                      for a, b in zip(left, right)]
        check(row, 'copy_current_evaluated_pose_finite', all(math.isfinite(v) for v in components), required=True)
        error = max(components)
        check(row, 'copy_current_evaluated_pose_exact', error <= NUMERIC_M,
              {'maximum_native_matrix_component': error, 'all_bones': len(rig.data.bones)}, required=True)
        world_components = [abs(a - b) for left, right in zip(baseline['world'], actual.matrix_world)
                            for a, b in zip(left, right)]
        check(row, 'copy_rig_evaluated_world_finite', all(math.isfinite(v) for v in world_components), required=True)
        world_error = max(world_components)
        check(row, 'copy_rig_evaluated_world_exact', world_error <= NUMERIC_M,
              {'maximum_native_matrix_component': world_error}, required=True)
        private_rig.data.pose_position = pose_position
        native = copy_mesh(source, scene, 'QA native order', owned,
                           report['Direct_evidence']['overlay'], private_rig, preserve_volume)
        check(row, 'plain_ARM_then_SUBSURF', [m.type for m in native.modifiers] == ['ARMATURE', 'SUBSURF'], required=True)
        observations['raw800'] = evaluate(native, {'ARMATURE': False, 'SUBSURF': False}, row, 'raw800')
        observations['skin800'] = evaluate(native, {'ARMATURE': True, 'SUBSURF': False}, row, 'native800_skin')
        observations['native'] = evaluate(native, {'ARMATURE': True, 'SUBSURF': True}, row, 'native800_skin_then_Subsurf')
        check(row, 'actual_native_counts', len(observations['raw800']['points']) == 800 and
              len(observations['skin800']['points']) == 800 and len(observations['native']['points']) == 3040, required=True)
        baked = copy_mesh(native, scene, 'QA worker baked order', owned)
        warnings = []
        row['worker_receipt'] = worker._bake_mesh(bpy.context, baked, set(), warnings)
        row['worker_warnings'] = warnings
        check(row, 'worker_retains_only_ARM', [m.type for m in baked.modifiers] == ['ARMATURE'], required=True)
        observations['baked_raw'] = evaluate(baked, {'ARMATURE': False}, row, 'worker_bakedSubsurf_no_ARM')
        observations['worker'] = evaluate(baked, {'ARMATURE': True}, row, 'worker_bakedSubsurf_then_ARM')
        manual = copy_mesh(native, scene, 'QA manual bake order', owned)
        manual.modifiers[0].show_viewport = False
        dg = graph()
        data = bpy.data.meshes.new_from_object(manual.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        owned['data'].append(data)
        manual.data = data
        manual.modifiers.remove(manual.modifiers[1])
        observations['manual_raw'] = evaluate(manual, {'ARMATURE': False}, row, 'manual_bakedSubsurf_no_ARM')
        observations['manual'] = evaluate(manual, {'ARMATURE': True}, row, 'manual_bakedSubsurf_then_ARM')
        reverse = copy_mesh(native, scene, 'QA explicit reversed order', owned)
        before_order = [rna(m) for m in reverse.modifiers]
        check(row, 'reorder_copy_only', reverse != source and reverse.data != source.data, required=True)
        check(row, 'native_ObjectModifiers_move_available', callable(getattr(reverse.modifiers, 'move', None)), required=True)
        row['reorder_native_return'] = reverse.modifiers.move(1, 0)
        check(row, 'reorder_full_modifier_RNA_preserved', [rna(m) for m in reverse.modifiers] == before_order[::-1]
              and [m.type for m in reverse.modifiers] == ['SUBSURF', 'ARMATURE'], required=True)
        observations['reverse'] = evaluate(reverse, {'ARMATURE': True, 'SUBSURF': True}, row, 'explicit_Subsurf_then_ARM')
        for name, left, right in (('native_vs_worker', 'native', 'worker'),
                ('native_vs_manual', 'native', 'manual'), ('native_vs_reordered', 'native', 'reverse'),
                ('worker_vs_manual_bake_raw', 'baked_raw', 'manual_raw'),
                ('worker_vs_manual_surface', 'worker', 'manual'), ('worker_vs_reordered', 'worker', 'reverse')):
            row['comparisons'][name] = pair(observations[left], observations[right], scene.unit_settings.scale_length)
        row['status'] = 'measured' if all(c['evaluated'] for c in row['comparisons'].values()) else 'failed'
    except Exception as exc:
        row['status'] = 'failed'
        row['errors'].append({'exception': repr(exc), 'traceback': traceback.format_exc()})
    finally:
        bpy.context.window.scene = home
        try:
            dispose(owned)
            if scene is not None:
                bpy.data.scenes.remove(scene)
            row['owned_scene_disposed'] = True
        except Exception as exc:
            row['owned_scene_disposed'] = False
            row['errors'].append({'cleanup': repr(exc)})
    return observations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--core-sha256', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output / 'report.json'
    report = {'stage': 'SOURCE_ONLY_NATIVE_SKIN_MODIFIER_ORDER52', 'status': 'unmeasured',
              'cases': {}, 'errors': [], 'accepted': False, 'FBX_verified': False, 'Unity_verified': False,
              'animation_verified': False, 'artist_loaded': False, 'artist_saved': False,
              'deployed': False, 'simulation_baked': False, 'timeline_seek_by_QA': False,
              'threshold_m': LIMIT_M, 'prior_PrivateFBXv3_maximum_m': OLD_MAX_M,
              'prior_failure_disposition': 'Historical PrivateFBXv3 failure remains unaccepted; this probe never writes or upgrades that result. Its file is not reread.',
              'scope': 'Fixed completed QA snapshot; numerical mechanism probe only.',
              'unknown': ['FBX/Unity/DQ-to-LBS transport', 'other poses/animation',
                          'Body attachment/Cloth final surface', 'a safe production repair'],
              'guard_scope': 'All loaded raw mesh coordinates/ordered topology/UV/material slots/raw key coordinates/channels; full named object weights; original rig Rest/native pose. No complete Action/material/image audit.'}
    pins = {str(SNAPSHOT): SNAPSHOT_SHA, str(WORKER): WORKER_SHA, str(Path(__file__).resolve()): args.core_sha256}
    before, originals, meshes, rig = None, (), (), None
    try:
        check(report, 'background52', bpy.app.background and bpy.app.version[:2] == (5, 2), list(bpy.app.version), required=True)
        check(report, 'CD_not_imported', not any(n == 'character_designer' or n.startswith('character_designer.') for n in sys.modules), required=True)
        report['runtime'] = {'version': bpy.app.version_string, 'binary': bpy.app.binary_path,
                             'actual_model': 'unrecorded', 'reasoning_effort': 'unrecorded'}
        report['source_before'] = {path: sha(path) for path in pins}
        for path, expected in pins.items():
            check(report, 'pin:' + path, report['source_before'][path] == expected, required=True)
        bpy.ops.wm.open_mainfile(filepath=str(SNAPSHOT), load_ui=False, use_scripts=False)
        home = bpy.context.scene
        check(report, 'positive_metric_unit_scale', math.isfinite(home.unit_settings.scale_length)
              and home.unit_settings.scale_length > 0, home.unit_settings.scale_length, required=True)
        source, rig = bpy.data.objects['Dress'], bpy.data.objects['CoshaRig']
        originals, meshes = tuple(bpy.data.objects), tuple(bpy.data.meshes)
        active_cloth = [[o.name, m.name] for o in originals for m in o.modifiers
                        if m.type == 'CLOTH' and m.show_viewport]
        check(report, 'no_active_Cloth_in_snapshot_depsgraph', not active_cloth, active_cloth, required=True)
        animated_cloth = [o.name for o in originals if o.animation_data is not None
                          and any(m.type == 'CLOTH' for m in o.modifiers)]
        check(report, 'no_animated_Cloth_modifier_controls', not animated_cloth, animated_cloth, required=True)
        before = author_guard(originals, meshes, rig)
        report['author_before'] = before
        record = json.loads(source[RECORD])
        surface = record['physics']['surface']
        overlay = source.modifiers.get(surface['overlay'])
        group = overlay.node_group if overlay is not None and overlay.type == 'NODES' else None
        originals_mods = [m for m in source.modifiers if m != overlay]
        state = json.loads(source['character_designer_dress_direct_state_v1'])
        cloth = bpy.data.objects[surface['roles']['CLOTH_PROXY'][0]].modifiers[-1]
        evidence = {'overlay': surface['overlay'], 'group': surface['node_group'],
                    'native_source_mods': [rna(m) for m in originals_mods],
                    'saved_source_mods': surface['source_contract']['modifiers'],
                    'original_modifier_types': [m.type for m in source.modifiers]}
        report['Direct_evidence'] = evidence
        predicates = {'fixed_local_no_key_source': source.type == 'MESH' and source.data.shape_keys is None and not source.library and not source.data.library,
            'native_source_mods_exact': evidence['native_source_mods'] == evidence['saved_source_mods'],
            'plain_ARM_SUBSURF_only': [m.type for m in originals_mods] == ['ARMATURE', 'SUBSURF'],
            'actual_rig': source.get(RIG) == rig and originals_mods[0].object == rig,
            'Direct_backend': record['physics']['backend'] == 'DIRECT_MAIN_CLOTH_V1' and surface['version'] == 1,
            'owned_absolute_output': group is not None and group.name == surface['node_group'] and group.get(ROLE) == 'DIRECT_NODE_GROUP' and group.get(OWNER) == record['owner'] and group.get(SOURCE) == source,
            'single_native_Direct_output': [m.type for m in source.modifiers] == ['ARMATURE', 'NODES', 'SUBSURF'] and source.modifiers[1] == overlay and group is not None and group.users == 1 and not group.library and not group.override_library,
            'Manual_paused': state['mode'] == 'MANUAL' and state['editing'] is False and cloth.type == 'CLOTH' and not cloth.show_viewport and not cloth.show_render,
            'actual_POSE_PreserveVolume': rig.data.pose_position == 'POSE' and originals_mods[0].use_deform_preserve_volume is True}
        for label, result in predicates.items():
            check(report, label, result)
        if not all(predicates.values()):
            raise RuntimeError('Direct/native source evidence is incomplete; no clone strip attempted.')
        spec = importlib.util.spec_from_file_location('owned_skin_order_worker52', WORKER)
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        dg = graph()
        evaluated_rig = rig.evaluated_get(dg)
        baseline = {'world': matrix(evaluated_rig.matrix_world),
                    'pose': {b.name: matrix(b.matrix) for b in evaluated_rig.pose.bones},
                    'source_world': matrix(source.evaluated_get(dg).matrix_world)}
        report['home_evaluated_rig_baseline_SHA'] = digest(baseline)
        observed = {}
        for label, position, volume in [('Manual_DQ', 'POSE', True), ('REST_DQ', 'REST', True), ('Manual_LBS', 'POSE', False)]:
            observed[label] = run_case(label, position, volume, source, rig, home, originals, worker, report, baseline)
        cross = {}
        for path in ('native', 'worker'):
            if path in observed['Manual_DQ'] and path in observed['Manual_LBS']:
                cross[path + '_DQ_vs_LBS'] = pair(observed['Manual_DQ'][path], observed['Manual_LBS'][path], home.unit_settings.scale_length)
            else:
                cross[path + '_DQ_vs_LBS'] = {'evaluated': False, 'passed': None, 'reason': 'A prerequisite native sample was not measured.'}
        report['cross_case'] = cross
        manual_max = report['cases']['Manual_DQ']['comparisons'].get('native_vs_worker', {}).get('maximum_m')
        report['historical_maximum_reproduced'] = {'evaluated': manual_max is not None,
            'passed': None if manual_max is None else abs(manual_max - OLD_MAX_M) <= NUMERIC_M,
            'current_maximum_m': manual_max, 'historical_maximum_m': OLD_MAX_M,
            'comparison_tolerance_m': NUMERIC_M}
        report['interpretation_rules'] = {
            'order_reproduced': 'Requires same-index topology, full named weights and UV/material fields exact. Manual native-vs-reordered difference with worker-vs-reordered and worker-vs-manual within numeric tolerance isolates the stack-order mechanism from a worker-only discrepancy.',
            'REST_control': 'REST equality removes pose deformation in this snapshot; it alone does not distinguish DQ nonlinearity from spatially varying LBS weights/transforms.',
            'LBS_control': 'A residual Manual_LBS order difference proves DQ is not necessary. A changed residual magnitude only shows Preserve Volume changes this pose; it cannot independently attribute a DQ contribution. Zero here is not an all-pose commutation proof.',
            'DQ_vs_LBS': 'Cross-case differences measure Preserve Volume effect on each path. Subtracting scalar maxima is not a separable DQ error decomposition.'}
        report['status'] = 'measured' if all(r['status'] == 'measured' and r['owned_scene_disposed'] for r in report['cases'].values()) else 'failed'
    except Exception as exc:
        report['status'] = 'failed'
        report['errors'].append({'exception': repr(exc), 'traceback': traceback.format_exc()})
    finally:
        check(report, 'CD_not_imported_after', not any(n == 'character_designer' or n.startswith('character_designer.') for n in sys.modules))
        if before is not None:
            try:
                after = author_guard(originals, meshes, rig)
                report['author_after'] = after
                for key in before:
                    check(report, 'author_preserved:' + key, before[key] == after[key])
            except Exception as exc:
                report['errors'].append({'author_guard': repr(exc)})
        report['source_after'] = {}
        for path in pins:
            try:
                actual = sha(path)
                report['source_after'][path] = actual
                check(report, 'source_preserved:' + path, actual == pins[path])
            except Exception as exc:
                report['errors'].append({'source_pin': path, 'exception': repr(exc)})
        try:
            result = bpy.ops.wm.read_factory_settings(use_empty=True)
            predicates = {'native_FINISHED': 'FINISHED' in result, 'loaded_filepath_empty': bpy.data.filepath == '',
                          'QA_source_absent': bpy.data.objects.get('Dress') is None,
                          'QA_rig_absent': bpy.data.objects.get('CoshaRig') is None}
            report['factory_disposal_predicates'] = predicates
            report['factory_disposed'] = all(predicates.values())
        except Exception as exc:
            report['factory_disposed'] = False
            report['errors'].append({'factory_disposal': repr(exc)})
        if report['errors'] or not report['factory_disposed'] or any(not x['passed'] for x in report.get('checks', {}).values()):
            report['status'] = 'failed'
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        print(json.dumps({'report': str(output), 'status': report['status'], 'accepted': False}), flush=True)
    return 0 if report['status'] == 'measured' else 2


if __name__ == '__main__':
    import bpy
    raise SystemExit(main())
