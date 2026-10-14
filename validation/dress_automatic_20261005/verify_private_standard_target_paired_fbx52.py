"""Source-only private standard target model/Action FBX component.

The pinned actual projected217 target is different from original Manual.
Source preparation retains real Direct validation/endpoint preflight/strip and
author guards. New owned native libraries isolate both complete stock workers.
The target Action has its own real snapshot-bound zero-Direct receipt. That is
not admission of the original Direct Dress or acceptance of approximation.
No public gate/worker/TRS threshold, runtime file, artist or Unity is changed.
"""
import argparse
from array import array
import ast
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
STANDARD_COMPONENT = HERE/'quantify_private_manual_standard_parent_skin52.py'
STANDARD_COMPONENT_SHA = '6d6be963f798020bb11388f3140b56e61125ea562b8d1ba796098ea63bd4e0d7'
TARGET_PROOF = HERE/'actual_private_manual_standard_parent_skin_52_20261008_143614_853_b45371187c69476495ec2a2da38aa55f/result/report.json'
TARGET_PROOF_SHA = 'f2910c70db415fd4e48a929ebfcb68b6a93e3e6e8e43010ec3dc79dc45ef8b35'
PAIR = HERE/'verify_private_paired_manual_model_fbx_component52.py'
PAIR_SHA = '9d17257560f686142ac658c1ed0ac37bd5e8e152b3f3f61eb6f4abf02299a084'
SEMANTICS = HERE/'verify_plain_rest_skin_fbx_roundtrip52_v2.py'
SEMANTICS_SHA = '14ce2040dd42f3b3a5f993761c4cf8e2c46a226b9ae2fac48ddabbdd2a796b65'
MODEL_READERS = HERE/'verify_private_plain_model_worker_fbx_component52.py'
MODEL_READERS_SHA = '8df942d20e2c3b52b1ca9cba3b3cfc134cfdf9748bd59ca3a3b0353a39b7ebaf'
MANIFEST_READER = HERE/'source_compatibility52_node_ui.py'
MANIFEST_READER_SHA = '08d36c4e561c808ed40a49e6b094085ef687a8a2e02bf5413c56ea203332507b'
STANDARD_HELPER_SHA = '100c487aace09d9846b19bc60a3fe96497bfeaf3dfa83d1a22f6907683d12780'
ROOT = 'CoshaRig'


def need(value, message):
    if not value:
        raise RuntimeError('PrivateStandardTargetFBX52: ' + message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def full_current_manifest(semantics, standard_path, standard_sha):
    """Only adapt the frozen159 wrapper ABI to the explicit new160 inventory."""
    need(semantics.MANIFEST_READER == MANIFEST_READER
         and semantics.MANIFEST_READER_SHA == MANIFEST_READER_SHA
         and sha(MANIFEST_READER) == MANIFEST_READER_SHA, 'Fixed full manifest reader differs')
    reader = load(MANIFEST_READER, 'standard_target_full_manifest160')
    need(standard_path == reader.REPOSITORY/'addons/character_designer/dress_standard_parent_candidate.py'
         and standard_sha == STANDARD_HELPER_SHA, 'Unreviewed standard helper identity')
    result = reader.current_manifest()
    need(type(result) is dict and len(result) == 160
         and result.get(str(standard_path), {}).get('sha256') == STANDARD_HELPER_SHA,
         'Complete160-file inventory or fixed standard helper differs')
    return result


def atomic_report(path, report):
    text = json.dumps(report, indent=2, allow_nan=False)
    temporary = path.with_name(path.name+'.tmp')
    for attempt in range(3):
        try:
            temporary.write_text(text, encoding='utf-8')
            temporary.replace(path)
            return
        except OSError:
            if attempt == 2:
                raise
            time.sleep(.05)


def actual_target_apply(bpy, Matrix, copied, source_poses, groups, budget, error, worker, proof, index):
    """Strictly reconstruct the measured target, not re-project original Manual."""
    wanted = {name: Matrix(rows) for name, rows in proof['samples'][index]['standard_target_217_pose_matrices'].items()}
    original = proof['samples'][index]['source_217_pose_matrices']
    need(set(wanted) == set(source_poses) == set(original)
         and max(error(source_poses[n], Matrix(original[n])) for n in wanted) <= worker.MATRIX_TOLERANCE,
         'Current original QA pose differs from the pinned actual source evidence')
    residuals = {}
    for names in groups:
        budget(); bpy.context.view_layer.update()
        evaluated = copied.evaluated_get(bpy.context.evaluated_depsgraph_get())
        parents = {n: evaluated.pose.bones[n].matrix.copy() for n in wanted}
        for name in names:
            bone = copied.data.bones[name]
            options = dict(parent_matrix=parents[bone.parent.name], parent_matrix_local=bone.parent.matrix_local) if bone.parent else {}
            basis = bone.convert_local_to_pose(wanted[name], bone.matrix_local, invert=True, **options)
            location, rotation, scale = worker._trs(basis, 'Pinned standard target '+name)
            actual_basis = Matrix.LocRotScale(location, rotation, scale)
            residuals[name] = error(basis, actual_basis)
            copied.pose.bones[name].matrix_basis = actual_basis
        bpy.context.view_layer.update()
    evaluated = copied.evaluated_get(bpy.context.evaluated_depsgraph_get())
    actual = {n: evaluated.pose.bones[n].matrix.copy() for n in wanted}
    target_error = max(error(actual[n], wanted[n]) for n in wanted)
    need(target_error <= 2e-4, 'Native target replay exceeded the unchanged worker FK tolerance')
    errors = {n: error(actual[n], source_poses[n]) for n in wanted}
    worst, local_worst = max(errors, key=errors.__getitem__), max(residuals, key=residuals.__getitem__)
    return actual, dict(all_217_pose_matrix_maxcomponent=errors[worst], worst_bone=worst,
        per_bone_matrix_maxcomponent=errors, desired_basis_TRS_residual_maxcomponent=residuals[local_worst],
        worst_desired_basis_bone=local_worst, desired_basis_residuals=residuals,
        pinned_target_replay_maxcomponent=target_error, actual_worker_TRS_gate_used=True)


def seal_pair_inputs(bpy, Matrix, copied, mesh, home, inventory, worker, helpers, v2, rest, q, base, skin,
                     report, output, metres, proof, source_action_name):
    """Publish two native libraries; original IDs remain guarded before disposal."""
    from mathutils import Vector
    samples = report['samples']
    names = sorted(copied.data.bones.keys())
    need(len(samples) == 3 and len(names) == 217 and report['non_Dress184_strict_passed'], 'Target seed is incomplete')
    reference_world = Matrix(samples[0]['standard_target_rig_world_matrix'])
    need(all(max(abs(Matrix(s['standard_target_rig_world_matrix'])[i][j]-reference_world[i][j])
             for i in range(4) for j in range(4)) <= worker.MATRIX_TOLERANCE for s in samples),
         'This fixed component requires the measured QA root to be static; do not invent a reference origin')
    copied.rotation_mode = 'QUATERNION'
    copied.delta_location = (0, 0, 0)
    copied.delta_rotation_euler = (0, 0, 0)
    copied.delta_rotation_quaternion = (1, 0, 0, 0)
    copied.delta_scale = (1, 1, 1)
    channels, previous = {}, {}
    for sample in samples:
        items = [('', Matrix(sample['standard_target_rig_world_matrix']))]
        items += [(copied.pose.bones[n].path_from_id()+'.', Matrix(sample['target_LRS_basis_matrices'][n])) for n in names]
        for prefix, matrix in items:
            location, rotation, scale = worker._trs(matrix, 'Distinct target Action '+prefix)
            if prefix in previous and rotation.dot(previous[prefix]) < 0:
                rotation.negate()
            previous[prefix] = rotation.copy()
            for field, values in (('location', location), ('rotation_quaternion', rotation), ('scale', scale)):
                for component, value in enumerate(values):
                    channels.setdefault((prefix+field, component), array('f')).append(value)
    action = bpy.data.actions.new('.QA Distinct Standard LBS Target')
    slot = action.slots.new(id_type='OBJECT', name=copied.name)
    bag = action.layers.new('Measured Standard Target').strips.new(type='KEYFRAME').channelbags.new(slot)
    for (path, component), values in channels.items():
        worker._write_curve(bag, path, component, [1, 2, 3], values)
    ad = copied.animation_data_create()
    ad.action, ad.action_slot = action, slot
    ad.use_nla, ad.action_blend_type, ad.action_influence, ad.action_extrapolation = False, 'REPLACE', 1., 'HOLD'
    rate = home.render.fps/home.render.fps_base
    need(1 <= rate <= 240, 'Fixed source rate is outside the original worker sampling contract')
    replay = []
    for index, sample in enumerate(samples):
        worker._frame(home, index+1); bpy.context.view_layer.update()
        e = copied.evaluated_get(bpy.context.evaluated_depsgraph_get())
        error = max(abs(e.pose.bones[n].matrix[i][j]-sample['standard_target_217_pose_matrices'][n][i][j])
                    for n in names for i in range(4) for j in range(4))
        root_error = max(abs(e.matrix_world[i][j]-sample['standard_target_rig_world_matrix'][i][j]) for i in range(4) for j in range(4))
        need(max(error, root_error) <= 2e-4, 'Distinct target Action changed its measured native target')
        replay.append(dict(QA_frame=index+1, all217_matrix_error=error, root_error=root_error))
    model_rig = copied.copy(); model_rig.data = copied.data.copy(); model_rig.name = '.QA Standard Model Seed'
    helpers._clear_animation(model_rig); helpers._clear_animation(model_rig.data)
    model_rig.data.pose_position = 'REST'; model_rig.matrix_world = reference_world
    for bone in model_rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4); bone.custom_shape = None
    model_mesh = mesh.copy(); model_mesh.data = mesh.data.copy(); model_mesh.name = '.QA Standard Model Dress Seed'
    model_mesh.parent = model_rig; model_mesh.matrix_parent_inverse = mesh.matrix_parent_inverse.copy()
    model_mesh.matrix_basis = mesh.matrix_basis.copy(); model_mesh.modifiers[0].object = model_rig
    need(model_mesh.data != mesh.data and len(model_mesh.data.vertices) == 3040
         and [m.type for m in model_mesh.modifiers] == ['ARMATURE']
         and model_mesh.modifiers[0].use_deform_preserve_volume is False, 'Independent target model skin differs')
    scenes = []
    for label, objects in (('model', [model_rig, model_mesh]), ('clip', [copied])):
        scene = bpy.data.scenes.new('Private Standard Target '+label)
        scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = metres
        scene.render.fps, scene.render.fps_base = home.render.fps, home.render.fps_base
        scene.frame_set(1)
        for obj in objects:
            scene.collection.objects.link(obj)
        scenes.append(scene)
    bpy.context.window.scene = scenes[0]; bpy.context.view_layer.update()
    model_reference = base.native_mesh(model_mesh, bpy.context.evaluated_depsgraph_get())
    model_skin = rest.ordered_skin(model_mesh, bpy.context.evaluated_depsgraph_get(), skin)
    normalization = Matrix.Translation(-reference_world.translation)
    refs = dict(names=names, parents={n: copied.data.bones[n].parent.name if copied.data.bones[n].parent else None for n in names},
        source_reference_world=[list(row) for row in reference_world], origin=list(reference_world.translation), metres=metres,
        normalized_root_world=[list(row) for row in normalization @ reference_world],
        normalized_Rest_world={n: [list(row) for row in normalization @ reference_world @ copied.data.bones[n].matrix_local] for n in names},
        normalized_REST_points=[list(normalization @ point) for point in model_reference['points']],
        geometry={k:v for k,v in model_reference.items() if k != 'points'}, skin=model_skin)
    need(len(refs['normalized_REST_points']) == 3040, 'Target model REST reference is incomplete')
    guard = worker._direct_export_guard()
    admission = guard.animation_host_admission(bpy.data.objects, copied, action, slot.handle)
    need(admission['source_count'] == 0 and not admission['physics_export_authorized'], 'Target still has a Direct native reverse link')
    roots = ({scenes[0], model_rig, model_mesh}, {scenes[1], copied, action})
    closures = [v2.id_reference_closure(root, bpy.data.user_map(), root) for root in roots]
    for closed in closures:
        forbidden = [(kind, item.name) for kind in ('objects', 'armatures', 'actions', 'scenes', 'meshes')
                     for item in getattr(bpy.data, kind) if item in closed and item.as_pointer() in inventory[kind]]
        need(not forbidden, 'Owned target library reaches original object/Rig/Action/Scene/Mesh IDs: '+repr(forbidden))
    clip_assets = [(kind, item.name) for kind in ('materials', 'images') for item in getattr(bpy.data, kind)
                   if item in closures[1] and item.as_pointer() in inventory[kind]]
    need(not clip_assets, 'Target Action library reaches original material/Image IDs: '+repr(clip_assets))
    paths = (output/'cdesigner-unity-standard-target'/'character.blend', output/'cdesigner-action-standard-target'/'animation.blend')
    for path, root in zip(paths, roots):
        path.parent.mkdir(); bpy.data.libraries.write(str(path), root, path_remap='ABSOLUTE', compress=True)
    receipt = guard.bind_animation_snapshot(admission, paths[1])
    report['owned_target_inputs'] = dict(model=dict(path=str(paths[0]), sha256=sha(paths[0]),
            rig=model_rig.name, rig_data=model_rig.data.name, mesh=model_mesh.name, scene=scenes[0].name),
        clip=dict(path=str(paths[1]), sha256=sha(paths[1]), rig=copied.name, action=action.name,
            rig_data=copied.data.name, slot=slot.handle, slot_identifier=slot.identifier,
            slot_target_id_type=slot.target_id_type, scene=scenes[1].name, admission=receipt),
        library_root_and_dependency_identities=[[list(q.id_name(item)) for item in sorted(closed, key=lambda x: repr(q.id_name(x)))] for closed in closures],
        no_original_object_Rig_Action_Scene_Mesh_dependencies=True,
        original_material_image_dependencies_model_only=True, target_Action_native_replay=replay,
        direct_target_receipt_scope='New owned plain target only; original Direct source remains publicly refused')
    report['distinct_target_semantics'] = dict(manual_original_preserved=False,
        simulation_baked=False, physics_omitted=True, source_action_original=source_action_name,
        actual_target_action=action.name, actual_target_rig=copied.name, actual_origin=list(reference_world.translation),
        source_package=None, source_package_verified=False, release_packet_created=False,
        Unity_Avatar_slot_GUID_localIDs_verified=False,
        limitation='Private native model/clip only; no old packet/sourceAction is reused or declared compatible')
    report['target_reference'] = refs
    report['target_job_timing'] = dict(fps=home.render.fps, fps_base=home.render.fps_base, sample_rate=rate)
    bpy.context.window.scene = home


def component_tree(standard):
    tree = standard.prepare_tree(standard.PARENT.read_text(encoding='utf-8'))
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    job = next(n for n in main.body if isinstance(n, ast.Try) and n.finalbody)
    offset = standard.index_once(job.body, 'pins.update(current_paths)')+1
    job.body[offset:offset] = standard.statements("""
pins.update({STANDARD_COMPONENT: STANDARD_COMPONENT_SHA, TARGET_PROOF: TARGET_PROOF_SHA,
             PAIR: PAIR_SHA, SEMANTICS: SEMANTICS_SHA, MODEL_READERS: MODEL_READERS_SHA,
             MANIFEST_READER: MANIFEST_READER_SHA})
need(sha(MANIFEST_READER) == MANIFEST_READER_SHA, 'Frozen manifest pin reader differs')
fixed_manifest_reader = load(MANIFEST_READER, 'standard_target_manifest_pin_reader')
pins.update({fixed_manifest_reader.DIAGNOSTIC: fixed_manifest_reader.DIAGNOSTIC_SHA,
             fixed_manifest_reader.QA: fixed_manifest_reader.QA_SHA})
parser_pins = load(MODEL_READERS, 'standard_target_parser_pin_readers').PARSER_PINS
pins.update({Path('D:/Blender5.2/5.2/scripts/addons_core/io_scene_fbx')/(name+'.py'): value
             for name, value in parser_pins.items()})
report['canonical_source_manifest_before'] = full_current_manifest(
    load(SEMANTICS, 'standard_source_manifest_reader'), STANDARD, STANDARD_SHA)
report['canonical_source_manifest_ABI_adaptation'] = dict(fixed_reader=str(MANIFEST_READER),
    fixed_reader_sha256=MANIFEST_READER_SHA, historical_wrapper_count=159, current_complete_count=160,
    new_helper=str(STANDARD), new_helper_sha256=STANDARD_SHA,
    limitation='Explicit file-inventory count ABI only; not proof of Native runtime equivalence')
""")
    offset = standard.index_once(job.body, "report['pins'] =")+1
    job.body[offset:offset] = standard.statements("""
actual_target = json.loads(TARGET_PROOF.read_text(encoding='utf-8'))
need(actual_target['quantification_complete'] and actual_target['errors'] == []
     and actual_target['non_Dress184_strict_passed'] and len(actual_target['samples']) == 3
     and all(actual_target[k] for k in ('source_77_mesh_Rest_Body12_Actions_assets_protected',
          'source_pose_channels_restored','owned_native_cleanup','private_scene_disposed','pinned_files_unchanged')),
     'Pinned actual standard target proof is incomplete')
need(all(sha(Path(path)) == value for path, value in actual_target['pins'].items()),
     'The actual target report source/input pins no longer match')
report['measured_target_provenance'] = dict(path=str(TARGET_PROOF), sha256=TARGET_PROOF_SHA,
    original_Manual_surface_0_05mm_passed=False, original_Direct_public_admission_verified=False)
""")
    loop = job.body[standard.index_once(job.body, 'for index, frame in enumerate((1.0, 2.0, 3.0)):')]
    offset = standard.index_once(loop.body, 'actual, matrices = project_native(')
    loop.body[offset:offset+1] = standard.statements("""
actual, matrices = actual_target_apply(bpy, Matrix, copied, desired, groups, budget, diag.matrix_error, worker, actual_target, index)
""")
    offset = standard.index_once(loop.body, 'local_inverse =')
    loop.body[offset:offset] = standard.statements("""
row['target_LRS_basis_matrices'] = {n: [list(values) for values in copied.pose.bones[n].matrix_basis] for n in retained}
row['source_mesh_world_matrix'] = [list(values) for values in source_mesh_world]
""")
    offset = standard.index_once(loop.body, 'report[\'samples\'].append(row)')
    loop.body[offset:offset] = standard.statements("""
from mathutils import Vector
frozen = actual_target['samples'][index]
row['target_native_geometry'] = {key: value for key, value in observed.items() if key != 'points'}
row['original_source_surface_receipt_error'] = cold.error([Vector(p) for p in frozen['source_local_points']],
    [Vector(p) for p in row['source_local_points']], metres)
row['target_surface_receipt_error'] = cold.error([Vector(p) for p in
    frozen['standard_FULL_REST_baked_LBS_surface']['candidate_source_local_points']],
    [Vector(p) for p in metric['candidate_source_local_points']], metres)
need(max(row['original_source_surface_receipt_error']['maximum_m'], row['target_surface_receipt_error']['maximum_m'])
     <= rest.LIMIT_M, 'Current source/target surface no longer reproduces the pinned actual observation')
""")
    offset = standard.index_once(job.body, "report['runtime_closure'] =")+1
    job.body[offset:offset] = standard.statements("""
seal_pair_inputs(bpy, Matrix, copied, mesh_b, home, inventory, worker, helpers, v2, rest, q, base, skin,
                 report, args.output, metres, actual_target, selected.name)
phase('owned_distinct_target_libraries_sealed')
""")
    # Private component budget only; no worker precision/safety guard is changed.
    for node in ast.walk(main):
        if isinstance(node, ast.Constant) and node.value == 90.0:
            node.value = 180.0
        elif isinstance(node, ast.Constant) and node.value == 'Use fresh owned output and at most90s soft budget':
            node.value = 'Use fresh owned output and at most180s private component soft budget'
    return ast.fix_missing_locations(tree)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-script-sha', required=True)
    parser.add_argument('--soft-seconds', type=float, default=180.)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE.resolve()) and not args.output.exists()
         and 0 < args.soft_seconds <= 180. and sha(Path(__file__).resolve()) == args.expected_script_sha,
         'Use fresh owned output, exact self SHA and at most180s soft budget')
    need(sha(STANDARD_COMPONENT) == STANDARD_COMPONENT_SHA, 'Frozen standard component changed')
    standard = load(STANDARD_COMPONENT, 'standard_target_source_preparation')
    need(sha(standard.PARENT) == standard.PARENT_SHA and sha(standard.STANDARD) == standard.STANDARD_SHA,
         'Frozen source-stage parent/helper changed')
    started = time.perf_counter()
    namespace = dict(__name__='private_distinct_standard_target_source_stage', __file__=str(Path(__file__).resolve()),
        PARENT=standard.PARENT, PARENT_SHA=standard.PARENT_SHA, STANDARD=standard.STANDARD, STANDARD_SHA=standard.STANDARD_SHA,
        STANDARD_COMPONENT=STANDARD_COMPONENT, STANDARD_COMPONENT_SHA=STANDARD_COMPONENT_SHA,
        TARGET_PROOF=TARGET_PROOF, TARGET_PROOF_SHA=TARGET_PROOF_SHA, PAIR=PAIR, PAIR_SHA=PAIR_SHA,
        SEMANTICS=SEMANTICS, SEMANTICS_SHA=SEMANTICS_SHA, MODEL_READERS=MODEL_READERS, MODEL_READERS_SHA=MODEL_READERS_SHA,
        MANIFEST_READER=MANIFEST_READER, MANIFEST_READER_SHA=MANIFEST_READER_SHA,
        full_current_manifest=full_current_manifest, actual_target_apply=actual_target_apply, seal_pair_inputs=seal_pair_inputs)
    exec(compile(component_tree(standard), str(Path(__file__).resolve()), 'exec'), namespace)
    source_exit = namespace['main']()
    report_path = args.output/'report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    report.update(scope='PRIVATE_DISTINCT_STANDARD_TARGET_MODEL_AND_ACTION_ACTUAL_FBX_COMPONENT_V1',
        source_stage_native_complete=source_exit == 0, target_FBX_component_observation_complete=False,
        target_model_worker_verified=False, target_animation_worker_verified=False, target_FBX_roundtrip_verified=False,
        target_pair_native_cleanup=False, target_pair_factory_disposed=False,
        original_Manual_equivalent=False, original_Manual_export_accepted=False,
        manual_original_preserved=False, physics_omitted=True, simulation_baked=False,
        manifest_packet_created=False, target_Direct_public_export_accepted=False,
        Unity_verified=False, Magica_verified=False, export_accepted=False)
    if source_exit != 0:
        atomic_report(report_path, report)
        return 2
    bpy = None
    report['private_adaptations'] = [
        'Source-only fixed Direct record seam; real Direct validate/capture/physical endpoint preflight/strip unchanged.',
        'Strict native replay of pinned projected217 target; distinct new LRS Action, not original Manual equivalence.',
        'New owned model/Action native libraries exclude original object/Rig/Action/Scene/Mesh dependencies.',
        'Complete stock model and animation workers execute after separate native loads; no admission/TRS/FK statements removed.',
        'Frozen underlying manifest reader retains complete160 before/after inventory including pinned standard helper; old159 wrapper untouched.',
        'Model names CoshaRig/Dress restored on owned reopened IDs only; clip export_rig_name CoshaRig uses existing worker field.']

    def phase(label):
        report['phase'] = label
        report.setdefault('phases', []).append(dict(name=label, seconds=time.perf_counter()-started))
        atomic_report(report_path, report)
        print(json.dumps(dict(StandardTargetFBX_phase=label)), flush=True)
        need(time.perf_counter()-started <= args.soft_seconds, 'Private paired component soft budget exceeded')

    try:
        import bpy as native_bpy
        from mathutils import Matrix, Vector
        bpy = native_bpy
        # Source-stage locals are intentionally not leaked. Reload only pinned readers.
        diag = load(namespace['DIAG'], 'standard_target_fixed_diag_readers')
        v2 = load(diag.V2, 'standard_target_v2_readers')
        v2.RUNTIME_PINS = dict(v2.RUNTIME_PINS); v2.RUNTIME_PINS.update(namespace['CURRENT_RUNTIME_PINS'])
        v2.RUNTIME_PINS['dress_standard_parent_candidate'] = standard.STANDARD_SHA
        rest = load(v2.REST, 'standard_target_rest_readers')
        pair = load(PAIR, 'standard_target_pair_readers')
        semantics = load(SEMANTICS, 'standard_target_semantics_readers')
        model_readers = load(MODEL_READERS, 'standard_target_model_readers')
        base = rest.readers(rest.BASE, ('native_mesh',), bpy)
        cold = rest.readers(rest.COLD, ('error',), bpy)
        skin = rest.readers(rest.V3, ('native_skin',), bpy)
        refs, inputs, timing = report['target_reference'], report['owned_target_inputs'], report['target_job_timing']
        names, parents, metres = refs['names'], refs['parents'], refs['metres']
        # Rehydrate only the native container types lost by JSON transport.
        # Values, ordering, names and weights remain exact; no remap/tolerance.
        refs['skin']['UV'] = [(name, values) for name, values in refs['skin']['UV']]
        refs['skin']['loops'] = [tuple(values) for values in refs['skin']['loops']]
        for field in ('edges', 'faces', 'triangles'):
            refs['geometry'][field] = [tuple(values) for values in refs['geometry'][field]]
            for sample in report['samples']:
                sample['target_native_geometry'][field] = [tuple(values) for values in sample['target_native_geometry'][field]]
        pair.skeleton(names, parents, names, parents)
        pins = {Path(path): value for path, value in report['pins'].items()}
        pins.update({Path(item['path']): item['sha256'] for item in (inputs['model'], inputs['clip'])})
        report['pins'] = {str(path): value for path, value in pins.items()}
        wanted_rest = refs['normalized_Rest_world']
        wanted_root = {'root': refs['normalized_root_world']}
        bpy.ops.preferences.addon_enable(module='io_scene_fbx')
        importlib.import_module('io_scene_fbx.fbx_utils_threading')._MULTITHREADING_ENABLED = False
        phase('complete_stock_model_worker_on_owned_plain_library')
        bpy.ops.wm.open_mainfile(filepath=inputs['model']['path'], load_ui=False)
        model_scene = bpy.data.scenes[inputs['model']['scene']]; bpy.context.window.scene = model_scene
        model_rig, mesh = bpy.data.objects[inputs['model']['rig']], bpy.data.objects[inputs['model']['mesh']]
        need(len(bpy.data.objects) == 2 and len(bpy.data.armatures) == 1 and not bpy.data.actions
             and mesh.parent == model_rig, 'Owned model closure contains unexpected objects/Rigs/Actions')
        model_rig.name, mesh.name = ROOT, 'Dress'
        need(model_rig.name == ROOT and mesh.name == 'Dress', 'Owned model native names collided')
        worker_model = load(v2.RUNTIME/'unity_export_worker.py', 'standard_target_complete_model_worker')
        model_stage = args.output/'model_fbx'
        model_job = dict(stage=str(model_stage), filename='standard_target_model.fbx', objects=['Dress', ROOT],
            rig=ROOT, unit_scale=metres, dress_surfaces=[], owned_keys={})
        model_result = worker_model.export_job(model_job)
        need(model_result['ok'] and model_result['objects'] == ['Dress', ROOT]
             and model_result['origin'] == refs['origin'] and model_result['unit_scale'] == metres
             and model_result['rigs'] == {ROOT:names}, 'Complete model worker identity/origin/retained set differs')
        bpy.context.view_layer.update(); graph = bpy.context.evaluated_depsgraph_get()
        native_rest = pair.rest_matrices(model_rig, names)
        pair.matrix_error(wanted_rest, native_rest, names, metres)
        pair.matrix_error(wanted_root, {'root':[list(row) for row in model_rig.matrix_world]}, ['root'], metres)
        target_mesh = dict(refs['geometry'], points=[Vector(p) for p in refs['normalized_REST_points']])
        produced, produced_skin = base.native_mesh(mesh, graph), rest.ordered_skin(mesh, graph, skin)
        semantics.geometry_semantics(target_mesh, refs['skin'], produced, produced_skin)
        semantics.skin_semantics(refs['skin'], produced_skin, 3040, len(refs['skin']['loops']), len(target_mesh['faces']))
        need(cold.error(target_mesh['points'], produced['points'], metres)['maximum_m'] <= rest.LIMIT_M,
             'Complete model worker changed target REST surface')
        model_fbx = model_stage/model_job['filename']
        need(model_fbx.is_file() and model_job['filename'] in model_result['files'], 'Complete model worker FBX artifact is absent')
        report['target_model_worker_result'] = model_result
        report['target_model_FBX'] = dict(path=str(model_fbx), sha256=sha(model_fbx),
            **pair.raw_fbx(model_fbx, names, True, metres))
        report['target_model_worker_verified'] = True
        need('FINISHED' in bpy.ops.wm.read_factory_settings(use_empty=True), 'Model worker native disposal failed')
        phase('complete_stock_animation_worker_on_owned_target_Action_library')
        bpy.ops.wm.open_mainfile(filepath=inputs['clip']['path'], load_ui=False)
        clip_home = bpy.data.scenes[inputs['clip']['scene']]; bpy.context.window.scene = clip_home
        target_rig, target_action = bpy.data.objects[inputs['clip']['rig']], bpy.data.actions[inputs['clip']['action']]
        need(len(bpy.data.objects) == len(bpy.data.armatures) == len(bpy.data.actions) == 1
             and not bpy.data.meshes and target_rig.parent is None, 'Owned Action closure contains original/extra IDs')
        worker = load(v2.RUNTIME/'animation_export_worker.py', 'standard_target_complete_animation_worker')
        clip_job = dict(rig=target_rig.name, action=target_action.name, action_slot=inputs['clip']['slot'],
            export_rig_name=ROOT, frame_start=1, frame_end=3, **timing,
            unit_scale=metres, stage=str(args.output/'clip_fbx'), filename='standard_target_action.fbx',
            name='Distinct Standard LBS Target', loop=False, dress_surfaces=[],
            dress_snapshot_path=inputs['clip']['path'])
        clip_job[worker._direct_export_guard().JOB_KEY] = inputs['clip']['admission']
        clip_result = worker.export_job(clip_job)
        need(clip_result['ok'] and clip_result['samples'] == 3 and set(clip_result['bones']) == set(names)
             and clip_result['rig'] == ROOT and clip_result['origin'] == refs['origin']
             and clip_result['unit_scale'] == metres and clip_result['maximum_bake_matrix_error'] < 2e-4,
             'Complete animation worker changed its declared target/timing/origin')
        clip_fbx = Path(clip_job['stage'])/clip_result['filename']
        need(sha(clip_fbx) == clip_result['sha256'], 'Animation writer file receipt differs')
        report['target_animation_worker_result'] = clip_result
        report['target_clip_FBX'] = dict(path=str(clip_fbx), sha256=sha(clip_fbx),
            **pair.raw_fbx(clip_fbx, names, False, metres))
        need(report['target_model_FBX']['units'] == report['target_clip_FBX']['units'], 'Model/clip FBX units differ')
        report['target_animation_worker_verified'] = True
        need('FINISHED' in bpy.ops.wm.read_factory_settings(use_empty=True), 'Animation worker native disposal failed')
        phase('actual_model_and_Action_FBX_imports_and_native_slot_binding')
        home = bpy.context.scene
        inventory = {kind:{item.as_pointer() for item in getattr(bpy.data,kind)} for kind in rest.ID_KINDS}
        imported = []
        for label, path, animate in (('model',model_fbx,False),('clip',clip_fbx,True)):
            scene = bpy.data.scenes.new('Private Standard FBX '+label)
            scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=metres
            bpy.context.window.scene=scene
            result=bpy.ops.import_scene.fbx(filepath=str(path),use_anim=animate,anim_offset=0,use_custom_props=False,
                automatic_bone_orientation=False,force_connect_children=False,ignore_leaf_bones=False)
            rigs=[o for o in scene.objects if o.type=='ARMATURE']; meshes=[o for o in scene.objects if o.type=='MESH']
            need('FINISHED' in result and len(rigs)==1 and len(meshes)==(1 if not animate else 0), 'Actual paired import inventory differs')
            arm=rigs[0]; pair.skeleton(list(arm.data.bones.keys()), {b.name:b.parent.name if b.parent else None for b in arm.data.bones},names,parents)
            need(all((b.inherit_scale,b.use_inherit_rotation,b.use_local_location)==('FULL',True,True) for b in arm.data.bones),
                 'FBX import no longer uses the declared standard parent convention')
            need(not arm.constraints and all(not b.constraints for b in arm.pose.bones), 'Imported target has constraint corrections')
            pair.matrix_error(wanted_rest,pair.rest_matrices(arm,names),names,metres)
            pair.matrix_error(wanted_root,{'root':[list(row) for row in arm.matrix_world]},['root'],metres)
            imported.append((scene,arm,meshes))
        model_scene, model_rig, meshes=imported[0]; clip_scene, clip_rig,_=imported[1]; mesh=meshes[0]
        action=clip_rig.animation_data.action if clip_rig.animation_data else None
        need(action is not None and not clip_rig.animation_data.nla_tracks
             and (model_rig.animation_data is None or (model_rig.animation_data.action is None and not model_rig.animation_data.nla_tracks)),
             'Imported Action/NLA differs')
        slot=worker._slot(clip_rig,action,None)
        need(not action.is_action_layered or (len(action.slots)==1 and slot.target_id_type=='OBJECT'), 'Imported target Action slot is ambiguous')
        report['Action_paths']=pair.bindings(worker,action,slot,clip_rig,model_rig,names)
        dress_names={'SK_Dress_Waist'}|{'SK_Dress_DEF_%02d_%02d'%(strand,segment) for strand in range(1,9) for segment in range(1,5)}
        bound={pair.transform_path(row['path'],names) for row in report['Action_paths']}
        need(len(dress_names)==33 and dress_names<=bound, 'All33 Dress curves must survive the actual FBX Take')
        report['all33_Dress_Action_paths_preserved']=True
        frames=pair.timing(clip_result,clip_scene.render.fps,clip_scene.render.fps_base,
            [k.co.x for c in worker._curves(action,slot) for k in c.keyframe_points])
        need(model_rig.rotation_mode==clip_rig.rotation_mode and all(model_rig.pose.bones[n].rotation_mode==clip_rig.pose.bones[n].rotation_mode for n in names),
             'Native imported rotation modes differ; no remap is allowed')
        model_scene.render.fps,model_scene.render.fps_base=clip_scene.render.fps,clip_scene.render.fps_base
        model_rig.data.pose_position=clip_rig.data.pose_position='POSE'
        ad=model_rig.animation_data_create(); ad.action=action
        if slot is not None: ad.action_slot=slot
        ad.use_nla,ad.action_blend_type,ad.action_influence,ad.action_extrapolation=False,'REPLACE',1.,'HOLD'
        need(ad.action==action and (slot is None or ad.action_slot==slot),'Actual native Action/slot transfer failed')
        arms=[m for m in mesh.modifiers if m.type=='ARMATURE']
        need(mesh.parent==model_rig and mesh.data.shape_keys is None and len(mesh.data.vertices)==3040
             and len(mesh.modifiers)==len(arms)==1 and arms[0].object==model_rig
             and arms[0].use_deform_preserve_volume is False, 'Actual imported model is not the declared3040 LBS skin')
        report['actual_slot_transfer']=dict(action=action.name,slot=None if slot is None else
            dict(handle=slot.handle,identifier=slot.identifier,target_id_type=slot.target_id_type),import_frames=frames,
            conversion='FBX seconds * importer integer scene.render.fps; reference0 plus three playable samples')
        normalization=Matrix.Translation(-Vector(refs['origin']))
        rows=[]
        for index,frame in enumerate(frames):
            original=None if index==0 else report['samples'][index-1]
            wanted=wanted_rest if index==0 else {n:[list(row) for row in normalization @ Matrix(original['standard_target_rig_world_matrix']) @
                Matrix(original['standard_target_217_pose_matrices'][n])] for n in names}
            measured=[]
            for scene,arm,_ in imported:
                bpy.context.window.scene=scene; worker._frame(scene,frame); bpy.context.view_layer.update()
                measured.append(pair.pose_matrices(arm,bpy.context.evaluated_depsgraph_get(),names))
            row=dict(reference=index==0,import_frame=frame,all217=True,
                target_vs_model=pair.matrix_error(wanted,measured[0][0],names,metres,strict=index==0),
                target_vs_clip=pair.matrix_error(wanted,measured[1][0],names,metres,strict=index==0),
                model_vs_clip=pair.matrix_error(measured[0][0],measured[1][0],names,metres,strict=index==0),
                target_root_vs_model=pair.matrix_error(wanted_root,measured[0][1],['root'],metres,strict=index==0),
                target_root_vs_clip=pair.matrix_error(wanted_root,measured[1][1],['root'],metres,strict=index==0),
                root_model_vs_clip=pair.matrix_error(measured[0][1],measured[1][1],['root'],metres,strict=index==0),
                model_bones_world=measured[0][0],clip_bones_world=measured[1][0],target_bones_world=wanted)
            bpy.context.window.scene=model_scene; bpy.context.view_layer.update(); graph=bpy.context.evaluated_depsgraph_get()
            observed=base.native_mesh(mesh,graph); observed_skin=rest.ordered_skin(mesh,graph,skin)
            if index==0:
                geometry_reference=target_mesh
            else:
                # Triangulation is native and pose dependent. Keep the strict
                # comparison, using the target's own actual triangle receipt
                # at this pose rather than substituting its REST tessellation.
                geometry_reference=dict(original['target_native_geometry'],points=observed['points'])
            row['same_index_geometry_semantics']=semantics.geometry_semantics(geometry_reference,refs['skin'],observed,observed_skin)
            semantics.skin_semantics(refs['skin'],observed_skin,3040,len(refs['skin']['loops']),len(target_mesh['faces']))
            if index==0:
                target_points=target_mesh['points']
            else:
                # Stored target local points use the original Dress object basis.
                # Recover their world frame from the source stage's raw object matrix.
                source_mesh_world=Matrix(original['source_mesh_world_matrix'])
                target_points=[normalization @ source_mesh_world @ Vector(p) for p in
                    original['standard_FULL_REST_baked_LBS_surface']['candidate_source_local_points']]
                original_points=[normalization @ source_mesh_world @ Vector(p) for p in original['source_local_points']]
                row['original_Manual_vs_actual_FBX_surface']=cold.error(original_points,observed['points'],metres)
                row['original_Manual_vs_target_surface']=original['standard_FULL_REST_baked_LBS_surface']
            row['target_vs_actual_FBX_surface']=cold.error(target_points,observed['points'],metres)
            need(len(observed['points'])==3040 and row['target_vs_actual_FBX_surface']['maximum_m']<=rest.LIMIT_M,
                 'Actual target skin FBX roundtrip exceeded the unchanged0.05mm target-fidelity gate')
            row['actual_FBX_same_index_points']=[list(p) for p in observed['points']]
            rows.append(row)
        report['target_FBX_samples']=rows
        report['runtime_closure_after_workers']=v2.runtime_closure(rest)
        report['target_FBX_roundtrip_verified']=True
        phase('private_target_FBX_observations_captured')
    except Exception as error:
        report['errors'].append(dict(target_FBX_error=repr(error),traceback=traceback.format_exc()))
    finally:
        if bpy is not None:
            if 'inventory' in locals() and inventory is not None:
                try:
                    report['pair_cleanup']=rest.cleanup_owned(bpy,home,inventory)
                    report['target_pair_native_cleanup']=report['pair_cleanup']['success']
                except Exception as error:
                    report['errors'].append(dict(target_owned_cleanup=repr(error)))
            try:
                result=bpy.ops.wm.read_factory_settings(use_empty=True)
                report['target_pair_factory_disposed']=('FINISHED' in result and not bpy.data.filepath
                    and all(not getattr(bpy.data,kind) for kind in ('objects','meshes','armatures','actions','images')))
            except Exception as error:
                report['errors'].append(dict(target_factory_disposal=repr(error)))
        report['canonical_source_files_exact'] = None
        report['pinned_files_unchanged'] = None
        try:
            report['canonical_source_manifest_after']=full_current_manifest(semantics, standard.STANDARD, standard.STANDARD_SHA)
            report['canonical_source_files_exact']=report['canonical_source_manifest_after']==report['canonical_source_manifest_before']
            report['pinned_files_unchanged']=all(sha(Path(path))==value for path,value in report['pins'].items())
        except Exception as error:
            report['errors'].append(dict(final_files=repr(error)))
        report['target_FBX_component_observation_complete']=(report['source_stage_native_complete']
            and report['target_model_worker_verified'] and report['target_animation_worker_verified']
            and report['target_FBX_roundtrip_verified'] and report['target_pair_native_cleanup']
            and report['target_pair_factory_disposed'] and report.get('canonical_source_files_exact',False)
            and report['pinned_files_unchanged'] and not report['errors'])
        report['total_elapsed_seconds']=time.perf_counter()-started
        atomic_report(report_path,report)
    print(json.dumps(dict(target_FBX_component_observation_complete=report['target_FBX_component_observation_complete'],errors=report['errors'])),flush=True)
    return 0 if report['target_FBX_component_observation_complete'] else 2


if __name__=='__main__':
    raise SystemExit(main())
