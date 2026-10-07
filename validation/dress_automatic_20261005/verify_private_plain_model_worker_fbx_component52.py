"""Private frozen PNS Dress + complete Main Rig through the normal model worker.

Root alone may run Native. Three local boundary adaptations: public admission,
model capture, model strip. The remaining production export_job AST is exact.
This partial model is not a character replacement or a paired Action/Unity proof.
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
import sys
import time
import traceback
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RUNTIME = Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer')
REST = HERE/'verify_plain_rest_skin_fbx_component52.py'
REST_SHA = '9b93aab9edde5cbf6065e2e8ab9bf81ef27d07a79cd7cb9b792451f466e8564f'
SEMANTICS = HERE/'verify_plain_rest_skin_fbx_roundtrip52_v2.py'
SEMANTICS_SHA = '14ce2040dd42f3b3a5f993761c4cf8e2c46a226b9ae2fac48ddabbdd2a796b65'
MANUAL = HERE/'verify_private_manual_action_fbx_component52.py'
MANUAL_SHA = '25e6e3789f44abebdfb2c73c013f912d3833349330abf7a8bcf98322d4037f3a'
IDENTITY = {'source': 'Dress', 'rig': 'CoshaRig', 'body': 'Cosha',
            'owner': '857c5aaad1ac4160953847b083deba20', 'scene': 'Scene'}
PARSER_PINS = {
    'parse_fbx': '96fe3f11b5c9b2950d9c434857e3b0db1a1b558510e2ad360b767643a69c2047',
    'data_types': '24328144f5b60338b1b47cc47ff76e8aee5c97c89ca4a419482978bb961f18fa',
    'fbx_utils_threading': '469262ab602b44119b4e7f0e2a7fe97e13f957000e239f3e5713a1c3c12f55e3',
}


def need(value, message):
    if not value:
        raise RuntimeError('PrivatePlainModel52: ' + message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def helpers():
    need(all(sha(path) == value for path, value in
             ((REST, REST_SHA), (SEMANTICS, SEMANTICS_SHA), (MANUAL, MANUAL_SHA))),
         'Frozen validation helper differs')
    return (load(REST, 'private_plain_model_rest'), load(SEMANTICS, 'private_plain_model_semantics'),
            load(MANUAL, 'private_plain_model_manual_readers'))


def private_worker_node(worker_path):
    tree = ast.parse(worker_path.read_text(encoding='utf-8'))
    original = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'export_job')
    node = copy.deepcopy(original)
    need(isinstance(node.body[0], ast.Try)
         and '_direct_export_guard().reject_model_snapshot(job, bpy.data.objects)' in ast.unparse(node.body[0]),
         'Pinned initial public model admission differs')
    admission = node.body.pop(0)
    node.name = 'private_component_export_job'
    restored = copy.deepcopy(node)
    restored.name = original.name
    restored.body.insert(0, admission)
    need(ast.dump(restored) == ast.dump(original), 'Another production worker segment changed')
    return ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), admission


def check_job(job, stage, unit_scale):
    need(type(job) is dict and set(job) == {'stage', 'filename', 'objects', 'rig', 'unit_scale',
         'dress_surfaces', 'owned_keys'} and job['stage'] == str(stage)
         and job['filename'] == 'private_plain_model_component.fbx'
         and job['objects'] == ['Dress', 'CoshaRig'] and job['rig'] == 'CoshaRig'
         and type(job['unit_scale']) in (int, float) and job['unit_scale'] == unit_scale
         and job['owned_keys'] == {'Dress': []}
         and type(job['dress_surfaces']) is list and len(job['dress_surfaces']) == 1,
         'Only the fixed partial Dress/CoshaRig model job is permitted')


def mesh_anchors(bpy):
    # The normal worker may rebind Dress.data. Keep the original Mesh ID and its
    # original group-index interpretation instead of requiring disposable RNA restore.
    return [(obj.name, SimpleNamespace(data=obj.data, vertex_groups=tuple(
        SimpleNamespace(name=g.name, index=g.index, lock_weight=g.lock_weight) for g in obj.vertex_groups)))
        for obj in bpy.data.objects if obj.type == 'MESH']


def original_mesh_state(q, anchors):
    result = {}
    for name, proxy in anchors:
        mesh, keys = proxy.data, proxy.data.shape_keys
        result[name] = {'mesh_pointer': mesh.as_pointer(), 'raw': q.digest(q.raw_mesh_content(proxy)),
            'custom': q.custom_content(dict(mesh.items())),
            'asset_metadata': q.simple_rna(mesh.asset_data) if mesh.asset_data else None,
            'keys_pointer': keys.as_pointer() if keys else None,
            'key_channels': None if keys is None else [keys.eval_time, [(k.name, k.value) for k in keys.key_blocks]],
            'key_custom': None if keys is None else q.custom_content(dict(keys.items()))}
    return result


def asset_state(bpy, q, names):
    return {'actions': {name: q.digest(q.action_content(bpy.data.actions[name])) for name in names['actions']},
        'materials': {name: {'pointer': bpy.data.materials[name].as_pointer(),
            'name': bpy.data.materials[name].name, 'use_fake_user': bpy.data.materials[name].use_fake_user,
            'use_nodes': bpy.data.materials[name].use_nodes,
            'custom': q.custom_content(dict(bpy.data.materials[name].items())),
            'asset_metadata': q.simple_rna(bpy.data.materials[name].asset_data) if bpy.data.materials[name].asset_data else None,
            'tree': bpy.data.materials[name].node_tree.as_pointer() if bpy.data.materials[name].node_tree else None,
            'nodes': None if not bpy.data.materials[name].node_tree else
                [(n.name, n.bl_idname, q.simple_rna(n)) for n in bpy.data.materials[name].node_tree.nodes],
            'links': None if not bpy.data.materials[name].node_tree else
                [(l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier)
                 for l in bpy.data.materials[name].node_tree.links]}
            for name in names['materials']},
        'images': {name: {'pointer': bpy.data.images[name].as_pointer(), 'name': bpy.data.images[name].name,
            'source': bpy.data.images[name].source, 'size': list(bpy.data.images[name].size),
            'colorspace': bpy.data.images[name].colorspace_settings.name,
            'use_fake_user': bpy.data.images[name].use_fake_user,
            'custom': q.custom_content(dict(bpy.data.images[name].items())),
            'asset_metadata': q.simple_rna(bpy.data.images[name].asset_data) if bpy.data.images[name].asset_data else None}
            for name in names['images']}}


def image_paths(bpy, names):
    return {name: {'filepath': bpy.data.images[name].filepath, 'file_format': bpy.data.images[name].file_format,
        'packed_bytes': None if bpy.data.images[name].packed_file is None else
            len(bpy.data.images[name].packed_file.data)} for name in names}


def matrices(rig, names):
    return {n: [list(row) for row in rig.matrix_world @ rig.data.bones[n].matrix_local] for n in names}


def matrix_gate(rest, first, second, names, metres):
    result = rest.matrix_errors([first[n] for n in names], [second[n] for n in names], metres)
    need(result['translation_max_m'] <= rest.LIMIT_M
         and result['linear_max_component'] <= rest.LINEAR_LIMIT
         and result['homogeneous_max_component'] <= rest.LINEAR_LIMIT, 'Complete retained Rest matrix gate failed')
    return result


def fbx_identity(fbx_path, names, metres):
    parser = importlib.import_module('io_scene_fbx.parse_fbx')
    root, version = parser.parse(str(fbx_path))
    objects = [e for e in root.elems if e.id == b'Objects']
    connections = [e for e in root.elems if e.id == b'Connections']
    settings = [e for e in root.elems if e.id == b'GlobalSettings']
    need(len(objects) == len(connections) == len(settings) == 1, 'Raw FBX root sections ambiguous')
    models = [e for e in objects[0].elems if e.id == b'Model']
    model_names = {e.props[0]: e.props[1].split(b'\x00\x01')[0].decode('utf-8') for e in models}
    need(len(model_names) == len(models) == len(names) + 2
         and set(model_names.values()) == set(names) | {'Dress', 'CoshaRig'}, 'Actual FBX model/bone names differ')
    roots = [e.props[1] for e in connections[0].elems if e.id == b'C' and e.props[0] == b'OO'
             and len(e.props) == 3 and e.props[2] == 0 and e.props[1] in model_names]
    need(len(roots) == 1 and model_names[roots[0]] == 'CoshaRig', 'Actual FBX top-level root is not CoshaRig')
    properties = [e for e in settings[0].elems if e.id == b'Properties70']
    need(len(properties) == 1, 'Actual FBX unit properties absent')
    units = {e.props[0].decode('utf-8'): e.props[-1] for e in properties[0].elems
             if e.id == b'P' and e.props[0] in (b'UnitScaleFactor', b'OriginalUnitScaleFactor')}
    need(set(units) == {'UnitScaleFactor', 'OriginalUnitScaleFactor'}
         and all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in units.values())
         and abs(units['UnitScaleFactor'] - 100. * metres) <= 1e-10, 'Actual FBX unit conversion differs')
    return {'version': version, 'root_name': 'CoshaRig', 'root_name_read_from_actual_FBX': True,
            'units': units, 'model_names': sorted(model_names.values())}


def pure_checks():
    rest, semantics, manual = helpers()
    pins = dict(rest.PINS)
    pins.update({RUNTIME/(name+'.py'): value for name, value in manual.RUNTIME_PINS.items()})
    pins.update({rest.FBX/(name+'.py'): value for name, value in PARSER_PINS.items()})
    need(all(sha(p) == value for p, value in pins.items()), 'Source/input pin differs')
    node, admission = private_worker_node(rest.WORKER)
    compile(node, str(rest.WORKER), 'exec')
    stage, metres = HERE/'not-created-pure-stage', 1.
    job = dict(stage=str(stage), filename='private_plain_model_component.fbx', objects=['Dress', 'CoshaRig'],
               rig='CoshaRig', unit_scale=metres, dress_surfaces=[{}], owned_keys={'Dress': []})
    check_job(job, stage, metres)
    rejected = []
    for field, value in (('objects', ['Dress', 'CoshaRig', 'Cosha']), ('rig', 'OtherRig'),
                         ('owned_keys', {'Dress': ['Basis']}), ('dress_surfaces', [{}, {}]),
                         ('unit_scale', True), ('filename', 'Other.fbx'), ('forearm', {})):
        altered = copy.deepcopy(job); altered[field] = value
        try:
            check_job(altered, stage, metres)
        except RuntimeError:
            rejected.append(field)
        else:
            raise RuntimeError('Private job rejection control opened: ' + field)
    need(rest.SNAPSHOT.name == 'character.blend'
         and rest.SNAPSHOT.parent.name.startswith('cdesigner-unity-'), 'Frozen input is not a legal private model snapshot')
    print(json.dumps({'source_only': True, 'worker_remaining_AST_exact': True,
        'removed_admission': ast.unparse(admission), 'fixed_pins': len(pins),
        'job_rejection_controls': rejected, 'semantic_checker_sha256': SEMANTICS_SHA,
        'Native_run': False}), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pure-checks', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--expected-script-sha')
    parser.add_argument('--soft-seconds', type=float, default=180.)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    if args.pure_checks:
        return pure_checks()
    need(args.output and args.expected_script_sha and args.output.is_absolute()
         and args.output.resolve().is_relative_to(HERE.resolve()) and not args.output.exists()
         and math.isfinite(args.soft_seconds) and 0. < args.soft_seconds <= 180., 'Use a fresh bounded private output')
    args.output.mkdir(parents=True)
    started = time.perf_counter()
    report = dict(scope='PRIVATE_FROZEN_PNS_PARTIAL_NORMAL_MODEL_WORKER_COMPONENT_ONLY',
        native_component_verified=False, FBX_component_written=False, FBX_reimport_verified=False,
        original_Mesh_Keys_exact=False, original_Action_asset_metadata_exact=False,
        owned_native_cleanup=False, private_scene_disposed=False, pinned_files_unchanged=False,
        canonical_source_files_exact=False, model_worker_remaining_AST_exact=False,
        material_texture_verified=False, public_export_verified=False, Unity_verified=False,
        export_accepted=False, animation_verified=False, paired_binding_verified=False,
        final_surface_equivalent=False, current_X_loaded=False, current_artist_validation='Unmeasured',
        whole_character_replacement=False, errors=[])

    def write():
        (args.output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')

    def phase(label):
        report['phase'] = label
        report.setdefault('phases', []).append({'name': label, 'seconds': time.perf_counter()-started})
        write(); print(json.dumps({'private_model_phase': label}), flush=True)
        need(time.perf_counter()-started <= args.soft_seconds, 'Soft component budget exceeded')

    bpy = home = inventory = anchors = names = q = before_mesh = before_assets = manifest = None
    boundary = worker = prior_record = prior_capture = prior_strip = None
    pins = {REST: REST_SHA, SEMANTICS: SEMANTICS_SHA, MANUAL: MANUAL_SHA,
            Path(__file__).resolve(): args.expected_script_sha}
    try:
        phase('frozen_input_and_actual_execution_source_manifest')
        rest, semantics, manual = helpers()
        pins.update(rest.PINS)
        pins.update({RUNTIME/(name+'.py'): value for name, value in manual.RUNTIME_PINS.items()})
        pins.update({rest.FBX/(name+'.py'): value for name, value in PARSER_PINS.items()})
        pins.update({semantics.PRIOR_FAILURE: semantics.PRIOR_FAILURE_SHA,
                     semantics.DIAGNOSTIC: semantics.DIAGNOSTIC_SHA})
        need(all(sha(p) == value for p, value in pins.items()), 'Fixed source/input/history pin differs')
        report['pins'] = {str(p): value for p, value in pins.items()}
        manifest = semantics.current_manifest()
        report['canonical_source_manifest_before'] = manifest
        reference = json.loads(rest.PROOF.read_text(encoding='utf-8'))
        need(reference['native_component_verified'] is True and not reference['errors']
             and reference['identity'] == IDENTITY, 'Fixed completed PNS identity/proof differs')
        need(rest.SNAPSHOT.name == 'character.blend' and rest.SNAPSHOT.parent.name.startswith('cdesigner-unity-'),
             'Use the actual legal frozen model snapshot without a library rewrite')
        report['provenance'] = {'input': str(rest.SNAPSHOT), 'input_sha256': pins[rest.SNAPSHOT],
            'input_proof': str(rest.PROOF), 'input_proof_sha256': pins[rest.PROOF],
            'scope': 'Frozen ab48 completed PNS input; current artist not loaded or validated',
            'semantic_checker': str(SEMANTICS), 'semantic_checker_sha256': SEMANTICS_SHA,
            'prior_strict_failure': str(semantics.PRIOR_FAILURE), 'prior_strict_failure_sha256': semantics.PRIOR_FAILURE_SHA,
            'checker_reason': 'Measured FBX raw-edge reordering and omitted zero entries use the fixed v2 semantic checker',
            'Manual_Action_Native_completed': False, 'pairing_status': 'Unmeasured'}
        import bpy as native_bpy
        from mathutils import Matrix
        bpy = native_bpy
        need(bpy.app.background and tuple(bpy.app.version) == (5, 2, 0)
             and Path(bpy.app.binary_path).resolve() == Path('D:/Blender5.2/blender.exe').resolve(),
             'Use only the fixed disposable Blender 5.2 executable')
        bpy.ops.wm.open_mainfile(filepath=str(rest.SNAPSHOT), load_ui=False)
        home = bpy.data.scenes.get(IDENTITY['scene'])
        source, rig, body = (bpy.data.objects[IDENTITY[key]] for key in ('source', 'rig', 'body'))
        need(home is not None and all(home.objects.get(o.name) == o for o in (source, rig, body))
             and source.type == body.type == 'MESH' and rig.type == 'ARMATURE'
             and rig.parent is None and source.parent == rig and source.parent_type == 'OBJECT'
             and not source.parent_bone and source.data.shape_keys is None
             and body.data.shape_keys is not None and len(body.data.shape_keys.key_blocks) == 12,
             'Fixed Dress/Body12/CoshaRig parent identity differs')
        bpy.context.window.scene = home; bpy.context.view_layer.update()
        metres = float(home.unit_settings.scale_length)
        need(math.isfinite(metres) and metres > 0., 'Source metre scale invalid')
        need(rig.animation_data is None or (rig.animation_data.action is None and not rig.animation_data.nla_tracks
             and not rig.animation_data.use_tweak_mode), 'Frozen source rig has unexpected object animation')
        inventory = {kind: {item.as_pointer() for item in getattr(bpy.data, kind)} for kind in rest.ID_KINDS}
        q = rest.readers(rest.QA, ('digest', 'id_name', 'custom_content', 'simple_rna', 'curve_content',
                                  'action_content', 'raw_mesh_content'), bpy)
        base = rest.readers(rest.BASE, ('native_mesh',), bpy)
        cold = rest.readers(rest.COLD, ('error',), bpy)
        skin = rest.readers(rest.V3, ('native_skin',), bpy)
        anchors = mesh_anchors(bpy)
        names = {kind: [o.name for o in getattr(bpy.data, kind)] for kind in ('actions', 'materials', 'images')}
        before_mesh, before_assets = original_mesh_state(q, anchors), asset_state(bpy, q, names)
        report['original_Mesh_Keys_before'] = before_mesh
        report['asset_metadata_before_digest'] = q.digest(before_assets)
        report['worker_image_paths_before'] = image_paths(bpy, names['images'])
        worker = load(rest.WORKER, 'private_plain_model_worker_helpers')
        service = worker._dress_services()  # Existing package creation; no legacy proof is manufactured.
        boundary = importlib.import_module(service.__package__+'.dress_export_snapshot')
        direct = importlib.import_module(service.__package__+'.skirt_surface_direct')
        record = direct.skirt.read_record(source)
        need(record['owner'] == IDENTITY['owner'] and record['rig'] == rig.name
             and record['physics']['backend'] == direct.BACKEND and source.get(boundary.RIG_KEY) == rig,
             'Fixed Direct ownership differs')
        direct.validate(source, rig, record)
        need(not any(m.show_viewport or m.show_render for obj in bpy.data.objects for m in obj.modifiers
                     if m.type == 'CLOTH'), 'No active Cloth is permitted in this private component')
        record_raw = source[boundary.RECORD_KEY]
        prior_record, prior_capture, prior_strip = boundary._record, worker._capture_dress_snapshot, worker._strip_dress_snapshot

        def proved_record(obj):
            need(obj == source and obj == bpy.data.objects.get('Dress') and obj.type == 'MESH'
                 and obj.get(boundary.RECORD_KEY) == record_raw and obj.get(boundary.RIG_KEY) == rig
                 and rig == bpy.data.objects.get('CoshaRig'), 'Different object/record reached the fixed private seam')
            parsed = json.loads(record_raw)
            need(parsed['owner'] == IDENTITY['owner'] and parsed['rig'] == 'CoshaRig'
                 and parsed['physics']['backend'] == direct.BACKEND, 'Fixed parsed record differs')
            direct.validate(obj, rig, parsed)
            return parsed

        boundary._record = proved_record
        proof = direct.export_capture(source)
        need(proof == reference['captured_model_receipt']['direct_proof'], 'Frozen PNS captured proof differs')
        stage = args.output/'model_stage'
        job = dict(stage=str(stage), filename='private_plain_model_component.fbx', objects=['Dress', 'CoshaRig'],
                   rig='CoshaRig', unit_scale=metres, dress_surfaces=[proof], owned_keys={'Dress': []})
        check_job(job, stage, metres)
        try:
            worker._direct_export_guard().reject_model_snapshot(job, bpy.data.objects)
        except ValueError as error:
            need('Direct Dress export validation is pending' in str(error), 'Public admission refused for another reason')
            report['public_admission_refusal'] = str(error)
        else:
            raise RuntimeError('Production public Direct model admission unexpectedly opened')

        def capture_model(actual_job, objects):
            check_job(actual_job, stage, metres)
            need(objects == [source, rig] and all(worker._DRESS_ROLE_KEY not in o for o in objects)
                 and source.get(boundary.RIG_KEY) in objects, 'Partial model inventory/owned helper differs')
            rows = boundary._proved_sources(actual_job['dress_surfaces'])
            need(len(rows) == 1 and rows[0][0] == source and rows[0][2] == proof, 'Captured fixed source differs')
            for obj, parsed, captured in rows:
                need(boundary._service_for_record(parsed) is direct, 'Actual mixed-backend service differs')
                direct.validate_snapshot(obj, captured)
                boundary._influence_animation_guard(obj, None)
                boundary._physical_animation_guard(obj, parsed, None)
                excluded = set(parsed['physics']['colliders']) | {n for ns in captured['roles'].values() for n in ns}
                need(not excluded & {o.name for o in objects}, 'Owned helper/collider is inside FBX inventory')
            report['Direct_capture_preflight'] = {'validate': True, 'export_capture': True, 'validate_snapshot': True,
                'physical_animation_guard': True, 'influence_animation_guard': True, 'fixed_record_only': True,
                'excluded_helper_names': sorted(excluded), 'proof': proof}
            return [(source, json.loads(json.dumps(proof, allow_nan=False)))]

        def strip_model(captured):
            need(len(captured) == 1 and captured[0][0] == source and captured[0][1] == proof,
                 'Only the fully captured fixed Direct source may be stripped')
            # All true proof and physical guards run before the first native write.
            rows = boundary._proved_sources([p for _o, p in captured])
            for obj, parsed, saved in rows:
                direct.validate_snapshot(obj, saved)
                boundary._influence_animation_guard(obj, None)
                boundary._physical_animation_guard(obj, parsed, None)
            omitted = [direct.strip_export_snapshot(obj, saved) for obj, _parsed, saved in rows]
            need(source[boundary.RECORD_KEY] == record_raw and omitted[0]['surface'] == 'PLAIN_NATIVE_SKIN_V1'
                 and omitted[0]['physics_omitted'] is True and omitted[0]['manual_original_preserved'] is True
                 and omitted[0]['body_attachment_omitted'] is True and omitted[0]['final_surface_equivalent'] is False,
                 'Real private strip changed its omission or deleted the record')
            report['Direct_real_strip'] = omitted
            return omitted

        worker._capture_dress_snapshot, worker._strip_dress_snapshot = capture_model, strip_model
        node, removed_admission = private_worker_node(rest.WORKER)
        exec(compile(node, str(rest.WORKER), 'exec'), worker.__dict__)
        bpy.ops.preferences.addon_enable(module='io_scene_fbx')
        # Native FBX explicitly exposes this debug/performance setting. Keep its
        # byte/geometry behavior and every worker FBX argument unchanged.
        fbx_threading = importlib.import_module('io_scene_fbx.fbx_utils_threading')
        fbx_threading._MULTITHREADING_ENABLED = False
        report['single_thread_settings'] = {'Blender_threads': 1, 'native_FBX_task_parallelism': False}
        report['model_worker_remaining_AST_exact'] = True
        report['private_adaptations'] = ['Only initial public Direct admission removed in in-memory export_job',
            'Fixed-source model capture callback with real Direct and physical gates',
            'Fixed-source model strip callback with real Direct private snapshot API']
        source_world = rig.matrix_world.copy()
        origin = source_world.translation.copy()
        translation = Matrix.Translation(-origin)
        retained = {b.name for b in rig.data.bones if not worker._is_control(b)
                    and (not bool(rig.get('character_designer_skirt_owner') or rig.get('character_designer_hair_bones_owner')
                    or rig.get('character_designer_hair_variant_version')) or b.use_deform)}
        need(len(rig.data.bones) == 346 and len(retained) == 217, 'Fixed complete retained rig prediction differs')
        bone_names = sorted(retained)
        predicted_parents = {}
        for n in bone_names:
            parent = rig.data.bones[n].parent
            while parent is not None and parent.name not in retained:
                parent = parent.parent
            predicted_parents[n] = parent.name if parent else None
        predicted_rest = {n: [list(row) for row in translation @ source_world @ rig.data.bones[n].matrix_local]
                          for n in bone_names}
        phase('actual_full_normal_model_worker')
        output = worker.private_component_export_job(job)
        report['normal_model_worker_result'] = output
        need(output['ok'] is True and output['objects'] == ['Dress', 'CoshaRig']
             and output['origin'] == list(origin) and output['unit_scale'] == metres
             and output['rigs'] == {'CoshaRig': bone_names} and set(rig.data.bones.keys()) == retained
             and rig.data.pose_position == 'REST' and not output['hair_motion']['active']
             and not output['simple_materials'] and set(output['meshes']) == {'Dress'}
             and source[boundary.RECORD_KEY] == record_raw, 'Actual normal model producer identity differs')
        native_parents = {n: rig.data.bones[n].parent.name if rig.data.bones[n].parent else None for n in bone_names}
        need(native_parents == predicted_parents, 'Full normal worker retained parent filtering differs')
        native_rest = matrices(rig, bone_names)
        report['normalization_cleanup_matrix_error'] = matrix_gate(rest, predicted_rest, native_rest, bone_names, metres)
        report['source_origin'] = list(origin)
        report['source_root_world_before'] = [list(row) for row in source_world]
        report['native_root_world_after'] = [list(row) for row in rig.matrix_world]
        expected_root = {'root': [list(row) for row in translation @ source_world]}
        report['normalization_root_matrix_error'] = matrix_gate(rest, expected_root,
            {'root': [list(row) for row in rig.matrix_world]}, ['root'], metres)
        report['worker_image_paths_after'] = image_paths(bpy, names['images'])
        report['worker_material_texture_stage'] = {'executed_unmodified': True, 'materials': output['materials'],
            'files': output['files'], 'warnings': output['warnings'], 'pixel_fidelity_checked': False,
            'private_image_filepath_and_encoding_changes_allowed': True}
        report['worker_output_files'] = []
        for filename in output['files']:
            artifact = (stage/filename).resolve()
            need(artifact.is_relative_to(stage.resolve()) and artifact.is_file(), 'Worker artifact outside its private stage')
            report['worker_output_files'].append({'file': filename, 'bytes': artifact.stat().st_size, 'sha256': sha(artifact)})
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        target, expected_skin = base.native_mesh(source, graph), rest.ordered_skin(source, graph, skin)
        need(len(target['points']) == 3040, 'Actual normal worker same-index mesh count differs')
        report['native_model_geometry_digest'] = q.digest(dict(target, points=[list(p) for p in target['points']]))
        report['native_model_skin_digest'] = q.digest(expected_skin)
        fbx_path = stage/job['filename']
        need(fbx_path.is_file() and fbx_path.stat().st_size > 0, 'Actual worker FBX missing')
        report['fbx'] = {'path': str(fbx_path), 'sha256': sha(fbx_path), 'bytes': fbx_path.stat().st_size,
            **fbx_identity(fbx_path, bone_names, metres)}
        report['FBX_component_written'] = True
        phase('actual_model_FBX_reimport')
        imported = bpy.data.scenes.new('Private Normal Model Reimport')
        imported.unit_settings.system = 'METRIC'; imported.unit_settings.scale_length = metres
        bpy.context.window.scene = imported
        result = bpy.ops.import_scene.fbx(filepath=str(fbx_path), use_anim=False, use_custom_props=False,
            automatic_bone_orientation=False, force_connect_children=False, ignore_leaf_bones=False)
        meshes = [o for o in imported.objects if o.type == 'MESH']
        rigs = [o for o in imported.objects if o.type == 'ARMATURE']
        need('FINISHED' in result and len(meshes) == len(rigs) == 1, 'Actual reimport inventory ambiguous')
        mesh, arm = meshes[0], rigs[0]
        need(set(arm.data.bones.keys()) == retained and mesh.parent == arm
             and {n: arm.data.bones[n].parent.name if arm.data.bones[n].parent else None for n in bone_names} == native_parents,
             'Complete reimport retained names/parents differ')
        arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        actual, actual_skin = base.native_mesh(mesh, graph), rest.ordered_skin(mesh, graph, skin)
        report['geometry_semantics'] = semantics.geometry_semantics(target, expected_skin, actual, actual_skin)
        report['skin_UV_named_weights_material_semantics'] = semantics.skin_semantics(expected_skin, actual_skin,
            len(target['points']), len(expected_skin['loops']), len(target['faces']))
        report['REST_reimport_error'] = cold.error(target['points'], actual['points'], metres)
        need(report['REST_reimport_error']['maximum_m'] <= rest.LIMIT_M, 'Same-index normal model geometry gate failed')
        reimport_rest = matrices(arm, bone_names)
        report['Rest_matrix_error'] = matrix_gate(rest, native_rest, reimport_rest, bone_names, metres)
        report['binding_comparison_receipt'] = {'actual_FBX_root_name': report['fbx']['root_name'],
            'Blender_reimport_display_name': arm.name, 'display_suffix_is_existing_source_collision': arm.name != 'CoshaRig',
            'source_meters_per_unit': metres, 'import_meters_per_unit': imported.unit_settings.scale_length,
            'source_origin': list(origin), 'native_normalized_root_world': report['native_root_world_after'],
            'reimport_root_world': [list(row) for row in arm.matrix_world], 'bone_names': bone_names,
            'parents': native_parents, 'native_normalized_Rest_world': native_rest,
            'reimport_normalized_Rest_world': reimport_rest, 'paired_Action_comparison_performed': False}
        report['reimport_same_index_points'] = [list(p) for p in actual['points']]
        report['reimport_named_UV'] = actual_skin['UV']
        report['reimport_named_effective_weights'] = [{n: w for n, w in row.items() if w != 0.}
                                                     for row in actual_skin['weights']]
        report['FBX_reimport_verified'] = True
        phase('finite_component_checks_complete')
    except Exception as error:
        report['errors'].append({'error': repr(error), 'traceback': traceback.format_exc()})
    finally:
        if boundary is not None and prior_record is not None:
            boundary._record = prior_record
        if worker is not None and prior_capture is not None:
            worker._capture_dress_snapshot, worker._strip_dress_snapshot = prior_capture, prior_strip
        if bpy is not None:
            if before_mesh is not None:
                try:
                    report['original_Mesh_Keys_exact'] = original_mesh_state(q, anchors) == before_mesh
                    report['original_Action_asset_metadata_exact'] = asset_state(bpy, q, names) == before_assets
                    need(report['original_Mesh_Keys_exact'] and report['original_Action_asset_metadata_exact'],
                         'Original loaded Mesh/Keys/Action/asset protection failed')
                except Exception as error:
                    report['errors'].append({'original_protection': repr(error), 'traceback': traceback.format_exc()})
            if inventory is not None:
                try:
                    # Cleanup alone releases any new baked Mesh from an original
                    # disposable Object before the inherited owned-ID cleanup.
                    # The complete producer and FBX measurements already finished.
                    rebound = []
                    for name, anchor in anchors or ():
                        obj = bpy.data.objects.get(name)
                        if obj is not None and obj.type == 'MESH' and obj.data != anchor.data:
                            obj.data = anchor.data
                            rebound.append(name)
                    report['cleanup_original_mesh_rebindings'] = rebound
                    report['cleanup'] = rest.cleanup_owned(bpy, home, inventory)
                    report['owned_native_cleanup'] = report['cleanup']['success']
                    need(report['owned_native_cleanup'], 'Owned native cleanup failed')
                    report['original_Mesh_Keys_exact'] = original_mesh_state(q, anchors) == before_mesh
                    report['original_Action_asset_metadata_exact'] = asset_state(bpy, q, names) == before_assets
                    need(report['original_Mesh_Keys_exact'] and report['original_Action_asset_metadata_exact'],
                         'Final original Mesh/Keys/Action/asset protection failed after owned cleanup')
                except Exception as error:
                    report['errors'].append({'cleanup': repr(error), 'traceback': traceback.format_exc()})
            try:
                result = bpy.ops.wm.read_factory_settings(use_empty=True)
                report['private_scene_disposed'] = ('FINISHED' in result and not bpy.data.filepath and not bpy.data.objects)
                need(report['private_scene_disposed'], 'Final factory disposal failed')
            except Exception as error:
                report['errors'].append({'factory_disposal': repr(error), 'traceback': traceback.format_exc()})
        try:
            report['pinned_files_unchanged'] = all(sha(p) == value for p, value in pins.items())
            if manifest is not None:
                after = semantics.current_manifest()
                report['canonical_source_manifest_after'] = after
                report['canonical_source_files_exact'] = after == manifest
            need(report['pinned_files_unchanged'] and report['canonical_source_files_exact'],
                 'Fixed files or complete 159-file current source changed during this execution')
            if worker is not None:
                report['runtime_closure'] = manual.runtime_closure(rest)
        except Exception as error:
            report['errors'].append({'source_protection': repr(error), 'traceback': traceback.format_exc()})
        report['native_component_verified'] = (report['FBX_reimport_verified'] and report['original_Mesh_Keys_exact']
            and report['original_Action_asset_metadata_exact'] and report['owned_native_cleanup']
            and report['private_scene_disposed'] and report['pinned_files_unchanged']
            and report['canonical_source_files_exact'] and report['model_worker_remaining_AST_exact'] and not report['errors'])
        report['elapsed_seconds'] = time.perf_counter()-started
        write()
    print(json.dumps({'native_component_verified': report['native_component_verified'], 'errors': report['errors']}), flush=True)
    return 0 if report['native_component_verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
