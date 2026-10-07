"""SOURCE_PREPARED: pair only two actual terminal PASS component FBX artifacts.

No artist .blend is loaded. No export, runtime/public guard or Unity is changed.
The three playable samples prove this private imported Action binds this partial
Dress model; no dynamic source-surface/vertex-Cloth equivalence is claimed.
"""
import argparse
import ast
import copy
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MODEL = HERE/'verify_private_plain_model_worker_fbx_component52.py'
MODEL_SHA = '8df942d20e2c3b52b1ca9cba3b3cfc134cfdf9748bd59ca3a3b0353a39b7ebaf'
MANUAL = HERE/'verify_private_manual_action_fbx_component52_v2.py'
MANUAL_SHA = '10bae6fd1a042bce5ca60344371e1e4de54a379518e0fe8d6ba0a02a928ac373'
INPUT_SHA = 'ab48a806f8e228f3c878da65bab59fe9cdaff2bcbca037f258cf74cacd88dc71'
ROOT = 'CoshaRig'
REST_M = LINEAR = 5e-5
PLAYABLE_COMPONENT = 4e-4  # Existing Manual component native matrix gate.
MODEL_TRUE = ('native_component_verified', 'FBX_component_written', 'FBX_reimport_verified',
    'original_Mesh_Keys_exact', 'original_Action_asset_metadata_exact', 'owned_native_cleanup',
    'private_scene_disposed', 'pinned_files_unchanged', 'canonical_source_files_exact', 'model_worker_remaining_AST_exact')
MANUAL_TRUE = ('native_component_verified', 'FBX_roundtrip_verified', 'input_author_restored',
    'snapshot_raw_named_weights_Rest_Body12_assets_exact', 'sampled_source_protected',
    'owned_native_cleanup', 'private_scene_disposed', 'pinned_files_unchanged')
COMMON_FALSE = ('public_export_verified', 'Unity_verified', 'export_accepted', 'final_surface_equivalent', 'current_X_loaded')


def need(value, message):
    if not value:
        raise RuntimeError('PrivatePairedManual52: ' + message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def same_hash(actual, expected):
    need(type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected) and actual == expected, 'Artifact/source hash differs')


def historical_manifest_changes(historical, current, pins):
    need(type(historical) is dict and type(current) is dict, 'Historical/current full source audit is absent')
    return [{'path': path, 'historical_model_state': historical.get(path), 'paired_start_state': current.get(path),
             'in_fixed_actual_pins': Path(path).resolve() in pins}
            for path in sorted(set(historical) | set(current)) if historical.get(path) != current.get(path)]


def flags(report, true_names, false_names):
    need(type(report) is dict and all(report.get(k) is True for k in true_names)
         and all(report.get(k) is False for k in false_names) and report.get('errors') == [], 'Actual component flags/errors differ')


def terminal(receipt, run, script_sha):
    need(type(receipt) is dict and type(receipt.get('PID')) is int and receipt['PID'] > 0
         and type(receipt.get('ExitCode')) is int and receipt['ExitCode'] == 0
         and receipt.get('TimedOut') is False and receipt.get('NativeReportPassed') is True
         and receipt.get('ChildGone') is True and receipt.get('ScriptSha256') == script_sha
         and receipt.get('SnapshotSha256') == INPUT_SHA and Path(receipt.get('Run', '')).resolve() == run
         and finite(receipt.get('ElapsedSeconds')) and 0. < receipt['ElapsedSeconds'] <= 240.,
         'Actual component process receipt is not the fixed successful terminal child')


def report_input(path, expected_sha, kind, rest):
    path = path.resolve()
    need(path.is_relative_to(HERE) and path.name == 'report.json' and path.parent.name == 'result', 'Use an actual component result/report.json')
    same_hash(sha(path), expected_sha)
    report = json.loads(path.read_text(encoding='utf-8'))
    run, process = path.parent.parent, path.parent.parent/'process.json'
    receipt = json.loads(process.read_text(encoding='utf-8-sig'))
    is_model = kind == 'model'
    flags(report, MODEL_TRUE if is_model else MANUAL_TRUE, COMMON_FALSE)
    expected_scope = ('PRIVATE_FROZEN_PNS_PARTIAL_NORMAL_MODEL_WORKER_COMPONENT_ONLY' if is_model
        else 'PRIVATE_MANUAL_BONE_ACTION_FBX_COMPONENT_V2_FIXED_ROOT_CLOSURE_ONLY')
    need(report.get('scope') == expected_scope, 'Old REST rig or another component scope is not a paired input')
    terminal(receipt, run, MODEL_SHA if is_model else MANUAL_SHA)
    need(receipt.get('Stage') == ('actual_private_plain_model_worker_fbx_component' if is_model
         else 'actual_private_manual_action_fbx_component') and receipt.get('Case') ==
         ('PRIVATE_frozen_ab48_partial_Dress_CoshaRig_normal_model' if is_model else 'Private_Manual_bone_Action'),
         'Component process stage/case differs')
    if is_model:
        flags(report, (), ('paired_binding_verified', 'material_texture_verified', 'animation_verified', 'whole_character_replacement'))
        need(report.get('current_artist_validation') == 'Unmeasured', 'Model report claims current artist validation')
    else:
        flags(report, (), ('public_admission_verified', 'production_model_binding_verified', 'Magica_verified',
                           'simulation_baked', 'vertex_Cloth_carried_by_bones', 'material_texture_roundtrip_verified'))
    raw_pins = report.get('pins')
    need(type(raw_pins) is dict and raw_pins, 'Component fixed file pins absent')
    pins = {Path(p).resolve(): value for p, value in raw_pins.items()}
    need(len(pins) == len(raw_pins) and pins.get(rest.SNAPSHOT.resolve()) == INPUT_SHA
         and pins.get((MODEL if is_model else MANUAL).resolve()) == (MODEL_SHA if is_model else MANUAL_SHA),
         'Component input/script identity pins differ')
    for pinned, value in pins.items():
        same_hash(sha(pinned), value)
    artifact = Path(report['fbx']['path']).resolve()
    expected = path.parent/('model_stage/private_plain_model_component.fbx' if is_model else 'fbx/private_manual_bone_action.fbx')
    need(artifact == expected.resolve(), 'Actual FBX is outside its component private stage')
    same_hash(sha(artifact), report['fbx']['sha256'])
    pins.update({path: expected_sha, process: sha(process), artifact: report['fbx']['sha256']})
    return report, receipt, artifact, pins


def skeleton(names, parents, wanted_names, wanted_parents):
    need(len(names) == 217 and len(set(names)) == 217 and set(names) == set(wanted_names)
         and set(parents) == set(names) and parents == wanted_parents
         and all(p is None or p in parents for p in parents.values()), 'Complete 217 bone names/parents differ')
    for name in names:
        seen = set()
        while name is not None:
            need(name not in seen, 'Bone hierarchy contains a cycle')
            seen.add(name); name = parents[name]


def root_name(name):
    need(name == ROOT, 'Actual FBX root must be CoshaRig; old private REST rig is refused')


def matrix_error(first, second, names, metres, strict=True):
    need(set(first) == set(second) == set(names) and names and finite(metres) and metres > 0,
         'Matrix names or metre scale incomplete')
    for values in (first, second):
        need(all(len(values[n]) == 4 and all(len(row) == 4 and all(finite(x) for x in row)
                                          for row in values[n]) for n in names), 'Nonfinite/incomplete 4x4 matrix')
    result = {'translation_max_m': max(abs(first[n][r][3]-second[n][r][3])*metres for n in names for r in range(3)),
        'linear_max_component': max(abs(first[n][r][c]-second[n][r][c]) for n in names for r in range(3) for c in range(3)),
        'homogeneous_max_component': max(abs(first[n][3][c]-second[n][3][c]) for n in names for c in range(4)),
        'maximum_native_component': max(abs(first[n][r][c]-second[n][r][c]) for n in names for r in range(4) for c in range(4))}
    if strict:
        need(result['translation_max_m'] <= REST_M and result['linear_max_component'] <= LINEAR
             and result['homogeneous_max_component'] <= LINEAR, 'Strict model Rest/root matrix gate exceeded')
    else:
        need(result['maximum_native_component'] < PLAYABLE_COMPONENT, 'Imported paired playable matrices differ')
    return result


def timing(result, fps, fps_base, keys):
    rate, duration = result.get('effective_sample_rate'), result.get('duration')
    need(finite(rate) and rate > 0. and finite(duration) and duration > 0.
         and result.get('samples') == 3 and type(result['samples']) is int
         and result.get('has_reference_frame') is True and result.get('reference_frame') == 0
         and result.get('playable_first_frame') == 1 and result.get('playable_last_frame') == 3
         and finite(fps) and fps > 0. and finite(fps_base) and fps_base > 0.
         and abs(fps/fps_base-rate) < 2e-5 and abs(rate*duration-2.) < 1e-10
         and keys and all(finite(k) for k in keys) and abs(min(keys)) < 2e-4
         and abs(max(keys)/fps-(duration+1./rate)) < 2e-5, 'Reference/three-frame time binding differs')
    return [i/rate*fps for i in range(4)]


def raw_fbx(path, names, has_mesh, metres):
    parsed, version = importlib.import_module('io_scene_fbx.parse_fbx').parse(str(path))
    def section(identifier):
        found = [e for e in parsed.elems if e.id == identifier]
        need(len(found) == 1, 'Actual FBX section missing/ambiguous')
        return found[0]
    nodes = [e for e in section(b'Objects').elems if e.id == b'Model']
    mapping = {e.props[0]: e.props[1].split(b'\x00\x01')[0].decode('utf-8') for e in nodes}
    wanted = set(names) | {ROOT} | ({'Dress'} if has_mesh else set())
    need(len(mapping) == len(nodes) == len(wanted) and set(mapping.values()) == wanted, 'Actual FBX model/bone inventory differs')
    roots = [e.props[1] for e in section(b'Connections').elems if e.id == b'C' and len(e.props) == 3
             and e.props[0] == b'OO' and e.props[2] == 0 and e.props[1] in mapping]
    need(len(roots) == 1, 'Actual FBX root ambiguous')
    root_name(mapping[roots[0]])
    properties = [e for e in section(b'GlobalSettings').elems if e.id == b'Properties70']
    need(len(properties) == 1, 'Actual FBX units absent')
    units = {e.props[0].decode('utf-8'): e.props[-1] for e in properties[0].elems
        if e.id == b'P' and e.props[0] in (b'UnitScaleFactor', b'OriginalUnitScaleFactor')}
    need(set(units) == {'UnitScaleFactor', 'OriginalUnitScaleFactor'}
         and all(finite(v) and v > 0. for v in units.values())
         and abs(units['UnitScaleFactor']-100.*metres) <= 1e-10, 'Actual FBX metre conversion differs')
    return {'version': version, 'root_name': ROOT, 'units': units, 'model_names': sorted(mapping.values())}


def rest_matrices(rig, names):
    return {n: [list(row) for row in rig.matrix_world @ rig.data.bones[n].matrix_local] for n in names}


def pose_matrices(rig, graph, names):
    evaluated = rig.evaluated_get(graph)
    return ({n: [list(row) for row in evaluated.matrix_world @ evaluated.pose.bones[n].matrix] for n in names},
            {'root': [list(row) for row in evaluated.matrix_world]})


def transform_path(path, names):
    transforms = ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')
    tree = ast.parse(path, mode='eval').body
    if isinstance(tree, ast.Name):
        need(path in transforms, 'Action root path is not a supported rig transform')
        return None
    need(isinstance(tree, ast.Attribute) and tree.attr in transforms
         and isinstance(tree.value, ast.Subscript), 'Action includes a non-transform path')
    value = tree.value
    need(isinstance(value.value, ast.Attribute) and value.value.attr == 'bones'
         and isinstance(value.value.value, ast.Name) and value.value.value.id == 'pose'
         and isinstance(value.slice, ast.Constant) and type(value.slice.value) is str
         and value.slice.value in names, 'Action bone path is outside the paired skeleton')
    return value.slice.value


def bindings(worker, action, slot, rig, other, names):
    curves = worker._curves(action, slot)
    need(curves and not any(c.mute for c in curves), 'Imported Action selected slot has missing/muted curves')
    seen, bones, result = set(), set(), []
    for curve in curves:
        path, index = curve.data_path, curve.array_index
        bone = transform_path(path, names)
        if bone is not None:
            bones.add(bone)
        pair = (path, index)
        need(pair not in seen, 'Duplicate selected Action channel')
        seen.add(pair)
        for target in (rig, other):
            value = target.path_resolve(path)
            need(type(index) is int and 0 <= index < len(value), 'Action component/path cannot resolve on both rigs')
        result.append({'path': path, 'component': index})
    need(bones == set(names), 'Imported Action does not bind all 217 retained bones')
    return result


def pure_checks():
    names = [f'b{i}' for i in range(217)]; parents = {n: None if i == 0 else names[i-1] for i, n in enumerate(names)}
    identity = [[float(i == j) for j in range(4)] for i in range(4)]
    matrices = {n: copy.deepcopy(identity) for n in names}
    skeleton(names, parents, names, parents); matrix_error(matrices, matrices, names, 1.)
    source = dict(effective_sample_rate=30., duration=2./30., samples=3, has_reference_frame=True,
                  reference_frame=0, playable_first_frame=1, playable_last_frame=3)
    need(timing(source, 30., 1., [0., 1., 2., 3.]) == [0., 1., 2., 3.], 'Pure time fixture differs')
    need(transform_path('location', names) is None and transform_path('pose.bones["b0"].rotation_euler', names) == 'b0',
         'Actual root/bone transform paths must resolve separately')
    closure, unrelated = str(HERE/'pure_fixed_closure.py'), str(HERE/'pure_unrelated_pose.py')
    fixed = {Path(closure).resolve(): '0'*64}
    historical = {closure: {'sha256': '0'*64}, unrelated: {'sha256': '0'*64}}
    current = copy.deepcopy(historical); current[unrelated]['sha256'] = '1'*64
    changes = historical_manifest_changes(historical, current, fixed)
    need(len(changes) == 1 and changes[0]['path'] == unrelated and changes[0]['in_fixed_actual_pins'] is False,
         'An unrelated historical source difference must remain visible without invalidating actual FBX evidence')
    same_hash(current[closure]['sha256'], fixed[Path(closure).resolve()])
    changed_closure = copy.deepcopy(current); changed_closure[closure]['sha256'] = '2'*64
    changed_parent = dict(parents); changed_parent[names[-1]] = None
    changed_rest = copy.deepcopy(matrices); changed_rest[names[-1]][0][3] = REST_M*1.01
    changed_linear = copy.deepcopy(matrices); changed_linear[names[-1]][0][0] += LINEAR*1.01
    wrong_time = dict(source, playable_first_frame=0)
    controls = [
        ('missing_bone', lambda: skeleton(names[:-1], parents, names, parents)),
        ('wrong_parent', lambda: skeleton(names, changed_parent, names, parents)),
        ('Rest_translation_over_gate', lambda: matrix_error(matrices, changed_rest, names, 1.)),
        ('Rest_linear_over_gate', lambda: matrix_error(matrices, changed_linear, names, 1.)),
        ('wrong_root', lambda: root_name('.Private REST Rig')),
        ('artifact_hash', lambda: same_hash('0'*64, '1'*64)),
        ('time_binding', lambda: timing(wrong_time, 30., 1., [0., 1., 2., 3.])),
        ('wrong_rate', lambda: timing(source, 24., 1., [0., 1., 2., 3.])),
        ('short_take', lambda: timing(source, 30., 1., [0., 1., 2.])),
        ('unknown_bone_path', lambda: transform_path('pose.bones["Other"].location', names)),
        ('nontransform_path', lambda: transform_path('pose.bones["b0"].constraints["Copy"].influence', names)),
        ('actual_pinned_source_difference', lambda: same_hash(changed_closure[closure]['sha256'], fixed[Path(closure).resolve()])),
    ]
    rejected = []
    for label, call in controls:
        try:
            call()
        except RuntimeError:
            rejected.append(label)
        else:
            raise RuntimeError('Pure refusal control unexpectedly passed: '+label)
    print(json.dumps({'SOURCE_PREPARED': True, 'Native_run': False, 'actual_PASS_receipts_created': False,
                      'unrelated_historical_difference_audited_and_allowed': True, 'pure_refusal_controls': rejected}), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pure-checks', action='store_true')
    parser.add_argument('--model-report', type=Path); parser.add_argument('--model-report-sha')
    parser.add_argument('--manual-report', type=Path); parser.add_argument('--manual-report-sha')
    parser.add_argument('--output', type=Path); parser.add_argument('--expected-script-sha')
    parser.add_argument('--soft-seconds', type=float, default=180.)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
    if args.pure_checks:
        return pure_checks()
    need(args.output and args.expected_script_sha and args.model_report and args.manual_report
         and args.output.is_absolute() and args.output.resolve().is_relative_to(HERE) and not args.output.exists()
         and finite(args.soft_seconds) and 0. < args.soft_seconds <= 180., 'Use fresh bounded output and actual frozen report parameters')
    args.output.mkdir(parents=True); started = time.perf_counter()
    report = dict(scope='PRIVATE_ACTUAL_MODEL_MANUAL_FBX_PAIR_COMPONENT_ONLY', native_component_verified=False,
        actual_reports_and_processes_verified=False, full_Rest_binding_verified=False,
        full_Action_paths_verified=False, four_frame_paired_matrices_verified=False,
        observable_Dress_skin_motion=False, owned_native_cleanup=False, private_scene_disposed=False,
        pinned_files_unchanged=False, canonical_source_files_exact=False, current_X_loaded=False,
        current_artist_validation='Unmeasured', dynamic_source_surface_equivalent=False,
        input_oracle_dynamic_surface_measured=False,
        Unity_verified=False, public_export_verified=False, export_accepted=False,
        final_surface_equivalent=False, vertex_Cloth_carried_by_bones=False, material_texture_verified=False,
        whole_character_replacement=False, errors=[])
    def write():
        (args.output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    def phase(label):
        report['phase'] = label; write(); print(json.dumps({'paired_phase': label}), flush=True)
        need(time.perf_counter()-started <= args.soft_seconds, 'Paired component soft budget exceeded')
    pins = {MODEL: MODEL_SHA, MANUAL: MANUAL_SHA, Path(__file__).resolve(): args.expected_script_sha}
    bpy = home = inventory = manifest = semantics = rest = None
    try:
        phase('actual_terminal_reports_and_artifacts')
        for path, expected in pins.items():
            same_hash(sha(path), expected)
        model = load(MODEL, 'paired_model_readers'); rest, semantics, old_manual = model.helpers()
        model_report, model_process, model_fbx, model_pins = report_input(args.model_report, args.model_report_sha, 'model', rest)
        manual_report, manual_process, manual_fbx, manual_pins = report_input(args.manual_report, args.manual_report_sha, 'manual', rest)
        shared = set(model_pins) & set(manual_pins)
        need(shared and all(model_pins[p] == manual_pins[p] for p in shared), 'Intersecting actual component pins differ')
        pins.update(model_pins); pins.update(manual_pins)
        manifest = semantics.current_manifest()
        report['canonical_source_manifest_before'] = manifest
        report['source_changes_since_historical_model'] = historical_manifest_changes(
            model_report['canonical_source_manifest_after'], manifest, pins)
        report['historical_source_comparison_scope'] = ('Audit only. Both actual reports entire pins and their '
            'intersection require current exact SHA; this paired run entire source before/after remains exact.')
        receipt = model_report['binding_comparison_receipt']
        root_name(receipt['actual_FBX_root_name']); root_name(model_report['fbx']['root_name'])
        names, parents = receipt['bone_names'], receipt['parents']
        skeleton(names, parents, names, parents)
        result = manual_report['worker_result']
        need(result.get('rig') == ROOT and result.get('source_rig') == ROOT and set(result['bones']) == set(names)
             and result['unit_scale'] == receipt['source_meters_per_unit'] == receipt['import_meters_per_unit']
             and result['origin'] == receipt['source_origin'] == model_report['source_origin'], 'Actual reports root/bone/unit/origin differ')
        metres = float(result['unit_scale'])
        report['actual_inputs'] = {'model_report': str(args.model_report.resolve()), 'model_report_sha256': args.model_report_sha,
            'manual_report': str(args.manual_report.resolve()), 'manual_report_sha256': args.manual_report_sha,
            'model_process': model_process, 'manual_process': manual_process,
            'model_FBX': str(model_fbx), 'model_FBX_sha256': sha(model_fbx),
            'manual_FBX': str(manual_fbx), 'manual_FBX_sha256': sha(manual_fbx),
            'frozen_ab48_input_sha256': INPUT_SHA, 'frozen_input_loaded': False,
            'intersecting_pin_count': len(shared), 'source_origin': result['origin'], 'meters_per_unit': metres}
        report['actual_reports_and_processes_verified'] = True
        import bpy as native_bpy
        bpy = native_bpy
        need(bpy.app.background and tuple(bpy.app.version) == (5, 2, 0)
             and Path(bpy.app.binary_path).resolve() == Path('D:/Blender5.2/blender.exe').resolve(), 'Use only disposable fixed Blender 5.2')
        reset = bpy.ops.wm.read_factory_settings(use_empty=True)
        need('FINISHED' in reset and not bpy.data.objects and not bpy.data.filepath, 'Pair starts in an empty factory scene')
        home = bpy.context.scene
        inventory = {kind: {item.as_pointer() for item in getattr(bpy.data, kind)} for kind in rest.ID_KINDS}
        bpy.ops.preferences.addon_enable(module='io_scene_fbx')
        importlib.import_module('io_scene_fbx.fbx_utils_threading')._MULTITHREADING_ENABLED = False
        report['actual_model_FBX_identity'] = raw_fbx(model_fbx, names, True, metres)
        report['actual_manual_FBX_identity'] = raw_fbx(manual_fbx, names, False, metres)
        need(report['actual_model_FBX_identity']['units'] == report['actual_manual_FBX_identity']['units'], 'Actual FBX unit headers differ')
        report['native_import_settings'] = {'anim_offset': 0, 'use_custom_props': False,
            'automatic_bone_orientation': False, 'force_connect_children': False, 'ignore_leaf_bones': False,
            'model_use_anim': False, 'Manual_use_anim': True}
        imported = []
        for label, fbx_path, animate in (('model', model_fbx, False), ('manual', manual_fbx, True)):
            scene = bpy.data.scenes.new('Private Paired '+label); scene.unit_settings.system = 'METRIC'
            scene.unit_settings.scale_length = metres; bpy.context.window.scene = scene
            value = bpy.ops.import_scene.fbx(filepath=str(fbx_path), use_anim=animate, anim_offset=0,
                use_custom_props=False, automatic_bone_orientation=False, force_connect_children=False, ignore_leaf_bones=False)
            rigs = [o for o in scene.objects if o.type == 'ARMATURE']; meshes = [o for o in scene.objects if o.type == 'MESH']
            need('FINISHED' in value and len(rigs) == 1 and len(meshes) == (1 if label == 'model' else 0)
                 and len(scene.objects) == len(rigs)+len(meshes), 'Actual FBX import inventory differs')
            rig = rigs[0]
            actual_parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
            skeleton(list(rig.data.bones.keys()), actual_parents, names, parents)
            need(not rig.constraints and all(not b.constraints for b in rig.pose.bones), 'Imported pair must have no constraint corrections')
            imported.append((scene, rig, meshes))
        model_scene, model_rig, meshes = imported[0]; clip_scene, clip_rig, _ = imported[1]
        report['imported_display_names'] = {'model': model_rig.name, 'manual': clip_rig.name,
            'suffix_due_to_second_import_is_not_FBX_root_rename': True}
        model_rest, clip_rest = rest_matrices(model_rig, names), rest_matrices(clip_rig, names)
        report['Rest_cross_output_error'] = matrix_error(model_rest, clip_rest, names, metres)
        report['Rest_model_receipt_error'] = matrix_error(receipt['reimport_normalized_Rest_world'], model_rest, names, metres)
        report['Rest_native_normalized_model_error'] = matrix_error(receipt['native_normalized_Rest_world'], model_rest, names, metres)
        roots = [{'root': [list(row) for row in rig.matrix_world]} for rig in (model_rig, clip_rig)]
        report['root_cross_output_error'] = matrix_error(roots[0], roots[1], ['root'], metres)
        report['root_model_receipt_error'] = matrix_error({'root': receipt['reimport_root_world']}, roots[0], ['root'], metres)
        report['root_native_normalized_model_error'] = matrix_error({'root': receipt['native_normalized_root_world']}, roots[0], ['root'], metres)
        report['full_Rest_binding_verified'] = True
        report['paired_Rest_receipt'] = {'bone_names': names, 'parents': parents, 'model_world': model_rest,
            'manual_world': clip_rest, 'model_root': roots[0], 'manual_root': roots[1]}
        worker = model.load(model.RUNTIME/'animation_export_worker.py', 'paired_actual_animation_readers')
        action = clip_rig.animation_data.action if clip_rig.animation_data else None
        need(action is not None and not clip_rig.animation_data.nla_tracks
             and (model_rig.animation_data is None or (model_rig.animation_data.action is None and not model_rig.animation_data.nla_tracks)),
             'Actual imported pair selected Action/NLA differs')
        slot = worker._slot(clip_rig, action, None)
        need(not action.is_action_layered or (len(action.slots) == 1 and slot.target_id_type == 'OBJECT'), 'Imported Action slot ambiguous')
        report['Action_path_bindings'] = bindings(worker, action, slot, clip_rig, model_rig, names)
        report['full_Action_paths_verified'] = True
        keys = [k.co.x for c in worker._curves(action, slot) for k in c.keyframe_points]
        frames = timing(result, clip_scene.render.fps, clip_scene.render.fps_base, keys)
        model_scene.render.fps, model_scene.render.fps_base = clip_scene.render.fps, clip_scene.render.fps_base
        # Bind the actual imported Action/slot. A different rotation mode is an
        # explicit blocker; no transform remapping or handwritten correction.
        need(model_rig.rotation_mode == clip_rig.rotation_mode and all(model_rig.pose.bones[n].rotation_mode
             == clip_rig.pose.bones[n].rotation_mode for n in names), 'Actual imported rotation modes differ before Action transfer')
        model_rig.data.pose_position = clip_rig.data.pose_position = 'POSE'
        ad = model_rig.animation_data_create(); ad.action = action
        if slot is not None:
            ad.action_slot = slot
        ad.use_nla, ad.action_blend_type, ad.action_influence, ad.action_extrapolation = False, 'REPLACE', 1., 'HOLD'
        need(ad.action == action and (slot is None or ad.action_slot == slot), 'Native Action/slot transfer failed')
        report['actual_Action_transfer'] = {'action': action.name, 'slot': None if slot is None else
            {'handle': slot.handle, 'identifier': slot.identifier, 'target_id_type': slot.target_id_type},
            'source_rig': clip_rig.name, 'target_rig': model_rig.name, 'frames': frames,
            'effective_sample_rate': result['effective_sample_rate'], 'playable_duration_seconds': result['duration'],
            'reference_frame': 0, 'three_playable_Take_times_seconds': [i/result['effective_sample_rate'] for i in range(1, 4)],
            'three_playable_elapsed_seconds': [i/result['effective_sample_rate'] for i in range(3)],
            'mapping': 'FBX seconds * importer integer scene.render.fps; identical imported Action curves on both rigs'}
        base = rest.readers(rest.BASE, ('native_mesh',), bpy)
        cold = rest.readers(rest.COLD, ('error',), bpy)
        mesh, points, samples, relative = meshes[0], [], [], []
        need(mesh.parent == model_rig and mesh.data.shape_keys is None
             and len(mesh.data.vertices) == 3040 and any(m.type == 'ARMATURE' and m.object == model_rig for m in mesh.modifiers),
             'Actual partial Dress skin target differs')
        def_names = sorted(n for n in names if n.startswith('SK_Dress_DEF_'))
        need('Hips' in names and len(def_names) == 32, 'Fixed 32 Dress DEF/Hips scope differs')
        phase('reference_and_three_playable_paired_samples')
        for index, frame in enumerate(frames):
            matrices = []
            for scene, rig in ((model_scene, model_rig), (clip_scene, clip_rig)):
                bpy.context.window.scene = scene; worker._frame(scene, frame); bpy.context.view_layer.update()
                graph = bpy.context.evaluated_depsgraph_get(); matrices.append(pose_matrices(rig, graph, names))
                if scene == model_scene:
                    points.append(base.native_mesh(mesh, graph)['points'])
                    evaluated = rig.evaluated_get(graph)
                    hip_inverse = evaluated.pose.bones['Hips'].matrix.inverted()
                    relative.append({n: [list(row) for row in hip_inverse @ evaluated.pose.bones[n].matrix] for n in def_names})
            row = {'reference': index == 0, 'playable_index': None if index == 0 else index-1, 'import_frame': frame,
                'full_bone_error': matrix_error(matrices[0][0], matrices[1][0], names, metres, strict=index == 0),
                'root_error': matrix_error(matrices[0][1], matrices[1][1], ['root'], metres, strict=index == 0),
                'model_bones_world': matrices[0][0], 'manual_bones_world': matrices[1][0],
                'model_root': matrices[0][1], 'manual_root': matrices[1][1],
                'model_same_index_points': [list(p) for p in points[-1]]}
            need(len(points[-1]) == 3040, 'Paired sample same-index vertex count differs')
            if index == 0:
                from mathutils import Vector
                row['model_reference_mesh_receipt_error'] = cold.error(points[0],
                    [Vector(p) for p in model_report['reimport_same_index_points']], metres)
                need(row['model_reference_mesh_receipt_error']['maximum_m'] <= REST_M, 'Transferred reference changed actual model REST mesh')
                row['model_reference_Rest_error'] = matrix_error(model_rest, matrices[0][0], names, metres)
            else:
                row['model_mesh_change_from_reference'] = cold.error(points[0], points[-1], metres)
            samples.append(row)
        relative_motion = max(abs(relative[i][n][r][c]-relative[1][n][r][c])
            for i in (2, 3) for n in def_names for r in range(4) for c in range(4))
        skin_motion = max(cold.error(points[1], points[i], metres)['maximum_m'] for i in (2, 3))
        need(relative_motion > 1e-5 and skin_motion > 1e-8, 'Actual transferred Dress skin/manual-relative-Hips motion is unobservable')
        report.update(four_frame_paired_matrices_verified=True, observable_Dress_skin_motion=True,
            samples=samples, Dress_relative_Hips_motion_maxcomponent=relative_motion,
            Dress_skin_change_from_first_playable_maximum_m=skin_motion)
        phase('private_pair_checks_complete')
    except Exception as error:
        report['errors'].append({'error': repr(error), 'traceback': traceback.format_exc()})
    finally:
        if bpy is not None:
            if inventory is not None:
                try:
                    report['cleanup'] = rest.cleanup_owned(bpy, home, inventory)
                    report['owned_native_cleanup'] = report['cleanup']['success']
                except Exception as error:
                    report['errors'].append({'cleanup': repr(error)})
            try:
                value = bpy.ops.wm.read_factory_settings(use_empty=True)
                report['private_scene_disposed'] = 'FINISHED' in value and not bpy.data.filepath and not bpy.data.objects
            except Exception as error:
                report['errors'].append({'factory_disposal': repr(error)})
        try:
            report['pinned_files_unchanged'] = all(sha(p) == value for p, value in pins.items())
            if manifest is not None:
                report['canonical_source_manifest_after'] = semantics.current_manifest()
                report['canonical_source_files_exact'] = report['canonical_source_manifest_after'] == manifest
            need(report['pinned_files_unchanged'] and report['canonical_source_files_exact'], 'Actual artifacts/pins/current full source changed')
        except Exception as error:
            report['errors'].append({'input_source_protection': repr(error)})
        report['pins'] = {str(p): value for p, value in pins.items()}
        report['native_component_verified'] = (all(report[k] for k in ('actual_reports_and_processes_verified',
            'full_Rest_binding_verified', 'full_Action_paths_verified', 'four_frame_paired_matrices_verified',
            'observable_Dress_skin_motion', 'owned_native_cleanup', 'private_scene_disposed',
            'pinned_files_unchanged', 'canonical_source_files_exact')) and not report['errors'])
        report['elapsed_seconds'] = time.perf_counter()-started; write()
    print(json.dumps({'native_component_verified': report['native_component_verified'], 'errors': report['errors']}), flush=True)
    return 0 if report['native_component_verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
