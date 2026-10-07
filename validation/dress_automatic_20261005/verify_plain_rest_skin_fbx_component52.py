"""Private REST model FBX component; Root alone may run the bounded launcher.

Fixed completed PNS QA input; no current X, Action export, physics, or deployment.
Exact UV/named weights/material indices and 0.05 mm same-index REST geometry.
Material/texture fidelity and the failed current Manual surface are out of scope.
"""
import argparse
import ast
import hashlib
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
RUN = HERE/'actual_plain_native_skin_model_v4_e0b_52_20261007_123727_962_feab010a295d467eae8019cccff98ca8/result'
SNAPSHOT, PROOF = RUN/'cdesigner-unity-pns-qa/character.blend', RUN/'report.json'
WORKER = Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_export_worker.py')
FBX = Path('D:/Blender5.2/5.2/scripts/addons_core/io_scene_fbx')
V3 = HERE/'verify_plain_native_skin_fbx_component52_v3.py'
BASE = HERE/'verify_direct_save_reopen_snapshot52.py'
COLD = HERE/'verify_direct_cold_install52_v4.py'
QA = HERE/'validate_real_dress.py'
LIMIT_M = 5e-5
LINEAR_LIMIT = 5e-5  # Unitless matrix-component guard, separate from metres.
PINS = {
    SNAPSHOT: 'ab48a806f8e228f3c878da65bab59fe9cdaff2bcbca037f258cf74cacd88dc71',
    PROOF: '803b8ec6297eb51f23e4a664e76e21ff354d3d1a97748a826ec41da3bfd67aa9',
    WORKER: '1716ff49a231cee8c0663fd17949583eabbfb7ce79791a459682930f40744dcb',
    V3: '33a3b0911f4fcd8dda63075fe4f40e173d8eada6e5ae23767962f7e48e78e003',
    BASE: '4f107e6e47f7a81fbb17adff83940aa4ac61562363815dbd919267caeabf4741',
    COLD: '4bb8e79fbad87950c75c1999e27d97657733ea42695df8e0f2b3a2ae4f58c536',
    QA: '613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046',
    FBX/'__init__.py': 'b7a2c06c11267ff9baaeb30ebc6add17b044d27f754340f17345dc78d74db336',
    FBX/'export_fbx_bin.py': '8fd324e4ee0d25cc89cd53507b0f93c057b17b699601ac90f81085d5be09e44a',
    FBX/'fbx_utils.py': '66a15d79d5eaf490176b439f22fb01963efcd46e06702eff224a84135e636fb3',
    FBX/'import_fbx.py': 'e4e55c2e344959b75d840e20c4d45d079ec8fd4f4bc375491cea76e55cce8013',
}
ID_KINDS = ('scenes', 'objects', 'collections', 'meshes', 'armatures',
            'materials', 'worlds', 'node_groups', 'images', 'actions')


def need(value, message):
    if not value:
        raise RuntimeError('PlainRestFBX52: ' + message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def readers(path, names, bpy):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    need({n.name for n in nodes} == set(names), 'Pinned reader ABI differs: ' + str(path))
    scope = dict(bpy=bpy, need=need, math=math, json=json, hashlib=hashlib)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    return SimpleNamespace(**{name: scope[name] for name in names})


def author_receipt(bpy, q, originals):
    graph = bpy.context.evaluated_depsgraph_get()
    result = {}
    for obj in originals:
        row = {'object': obj.as_pointer(), 'data': obj.data.as_pointer() if obj.data else None,
               'world': [list(r) for r in obj.matrix_world]}
        if obj.type == 'MESH':
            keys = obj.data.shape_keys
            row.update(raw=q.digest(q.raw_mesh_content(obj)), key_channels=None if keys is None else
                       [keys.eval_time, [(key.name, key.value) for key in keys.key_blocks]])
        else:
            row.update(Rest=q.digest(q.rest_content(obj)), pose=q.pose_channels(obj),
                       pose_position=obj.data.pose_position, mode=obj.mode,
                       evaluated_pose={pb.name: [list(r) for r in pb.matrix]
                                       for pb in obj.evaluated_get(graph).pose.bones})
        result[obj.name] = row
    return json.loads(json.dumps(result, allow_nan=False))


def ordered_skin(obj, graph, skin_reader):
    result = skin_reader.native_skin(obj, graph)
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
    try:
        result['loops'] = [(loop.vertex_index, loop.edge_index) for loop in mesh.loops]
    finally:
        evaluated.to_mesh_clear()
    need(all(math.isfinite(w) for row in result['weights'] for w in row.values())
         and all(math.isfinite(v) for _name, uv in result['UV'] for point in uv for v in point),
         'Nonfinite native UV or weight')
    return result


def skin_exact(first, second):
    return (set(first['groups']) == set(second['groups'])
            and all(first[k] == second[k] for k in ('weights', 'UV', 'material_indices', 'loops')))


def matrix_errors(first, second, metres):
    need(len(first) == len(second) and first
         and all(math.isfinite(v) for matrix in first + second for row in matrix for v in row),
         'Incomplete or nonfinite native Rest matrices')
    return {'translation_max_m': max(abs(a[r][3] - b[r][3]) * metres
                                      for a, b in zip(first, second) for r in range(3)),
            'linear_max_component': max(abs(a[r][c] - b[r][c])
                                        for a, b in zip(first, second) for r in range(3) for c in range(3)),
            'homogeneous_max_component': max(abs(a[3][c] - b[3][c])
                                             for a, b in zip(first, second) for c in range(4))}


def cleanup_owned(bpy, home, inventory):
    bpy.context.window.scene = home
    failures = []
    # Scenes release memberships, objects release their data, then dependencies.
    for kind in ID_KINDS:
        collection = getattr(bpy.data, kind)
        for item in tuple(collection):
            if item.as_pointer() in inventory[kind]:
                continue
            name = item.name
            try:
                if kind in ('scenes', 'objects', 'collections'):
                    collection.remove(item, do_unlink=True)
                else:
                    if item.use_fake_user:
                        item.use_fake_user = False
                    need(item.users == 0, 'Owned ' + kind + ' has outside users: ' + name)
                    collection.remove(item)
            except Exception as error:
                failures.append({'kind': kind, 'name': name, 'error': repr(error)})
    remaining = {kind: [item.name for item in getattr(bpy.data, kind)
                        if item.as_pointer() not in inventory[kind]] for kind in ID_KINDS}
    return {'success': not failures and not any(remaining.values()),
            'failures': failures, 'remaining_owned_ids': remaining}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-script-sha', required=True)
    parser.add_argument('--soft-seconds', type=float, default=180.)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE.resolve())
         and not args.output.exists(), 'Use one new output beneath this fixed Validation directory')
    args.output.mkdir(parents=True)
    started = time.perf_counter()
    report = dict(scope='PRIVATE_REST_MODEL_FBX_COMPONENT_ONLY', native_component_verified=False,
                  FBX_component_written=False, FBX_reimport_verified=False, owned_native_cleanup=False,
                  private_scene_disposed=False, original_raw_keys_Rest_pose_exact=False,
                  pinned_files_unchanged=False, animation_verified=False, material_texture_verified=False,
                  final_surface_equivalent=False, public_export_verified=False, Unity_verified=False,
                  export_accepted=False, current_X_loaded=False, errors=[],
                  historical_Manual_gate={'status': 'PreservedFailure', 'maximum_m': .0004713791436785606,
                                          'rms_m': 4.0846634327929886e-05, 'REST_judgement': False})

    def write():
        (args.output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')

    def phase(label):
        report['phase'] = label
        report.setdefault('phases', []).append({'name': label, 'seconds': time.perf_counter() - started})
        write()
        print(json.dumps({'REST_FBX_phase': label}), flush=True)
        need(time.perf_counter() - started <= args.soft_seconds, 'Soft component budget exceeded')

    pins = dict(PINS)
    pins[Path(__file__).resolve()] = args.expected_script_sha
    bpy = home = inventory = originals = before = None
    try:
        phase('pinned_fixed_input')
        need(all(sha(path) == value for path, value in pins.items()), 'Fixed input/source pin differs')
        report['pins'] = {str(path): value for path, value in pins.items()}
        reference = json.loads(PROOF.read_text(encoding='utf-8'))
        need(reference['native_component_verified'] is True and not reference['errors'], 'Completed PNS QA proof absent')
        import bpy as native_bpy
        from mathutils import Matrix
        bpy = native_bpy
        need(bpy.app.background and tuple(bpy.app.version) == (5, 2, 0)
             and Path(bpy.app.binary_path).resolve() == Path('D:/Blender5.2/blender.exe').resolve(),
             'Use only the isolated fixed Blender 5.2 executable')
        identity = reference['identity']
        need(identity == {'source': 'Dress', 'rig': 'CoshaRig', 'body': 'Cosha',
                          'owner': '857c5aaad1ac4160953847b083deba20', 'scene': 'Scene'}, 'Fixed QA identity differs')
        bpy.ops.wm.open_mainfile(filepath=str(SNAPSHOT), load_ui=False)
        home = bpy.data.scenes.get(identity['scene'])
        need(home is not None, 'Recorded saved home Scene is absent')
        source, rig, body = (bpy.data.objects[identity[name]] for name in ('source', 'rig', 'body'))
        record = json.loads(source['character_designer_skirt_v1'])
        proof = reference['captured_model_receipt']['direct_proof']
        need(all(home.objects.get(obj.name) == obj for obj in (source, rig, body))
             and source.type == body.type == 'MESH' and rig.type == 'ARMATURE'
             and source.get('character_designer_skirt_armature') == rig and record['owner'] == identity['owner']
             and record['physics']['backend'] == proof['backend'] == 'DIRECT_MAIN_CLOTH_V1'
             and source.data.shape_keys is None and body.data.shape_keys is not None
             and len(body.data.shape_keys.key_blocks) == 12 and rig.parent is None
             and source.parent == rig and source.parent_type == 'OBJECT' and not source.parent_bone,
             'Fixed no-Key Dress/Body12/Main-Rig parent scope differs')
        bpy.context.window.scene = home
        bpy.context.view_layer.update()
        report['saved_home'] = {'scene': home.name, 'recorded_membership_exact': True,
                               'frame': home.frame_current, 'subframe': home.frame_subframe}
        q = readers(QA, ('digest', 'id_name', 'raw_mesh_content', 'rest_content', 'pose_channels'), bpy)
        base = readers(BASE, ('native_mesh', 'geometry_pair'), bpy)
        cold = readers(COLD, ('error',), bpy)
        skin = readers(V3, ('native_skin',), bpy)
        originals = tuple(obj for obj in bpy.data.objects if obj.type in ('MESH', 'ARMATURE'))
        inventory = {kind: {item.as_pointer() for item in getattr(bpy.data, kind)} for kind in ID_KINDS}
        before = author_receipt(bpy, q, originals)
        spec = importlib.util.spec_from_file_location('private_plain_rest_worker', WORKER)
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        phase('independent_REST_copies')
        scene = bpy.data.scenes.new('Private REST Model Component')
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = home.unit_settings.scale_length
        metres = scene.unit_settings.scale_length
        need(math.isfinite(metres) and metres > 0., 'Unknown metre scale')
        copied_rig = rig.copy()
        copied_rig.data = rig.data.copy()
        copied_rig.name = '.Private REST Rig'
        scene.collection.objects.link(copied_rig)
        clone = source.copy()
        clone.data = source.data.copy()
        clone.name = '.Private REST Dress'
        inverse, basis = source.matrix_parent_inverse.copy(), source.matrix_basis.copy()
        clone.parent = copied_rig
        clone.matrix_parent_inverse = inverse
        clone.matrix_basis = basis
        scene.collection.objects.link(clone)
        for owner in (copied_rig, copied_rig.data, clone, clone.data):
            for key in tuple(owner.keys()):
                if key.startswith('character_designer_'):
                    del owner[key]
        for obj in (copied_rig, clone):
            worker._clear_animation(obj)
            worker._clear_animation(obj.data)
            for constraint in tuple(obj.constraints):
                obj.constraints.remove(constraint)
        copied_rig.matrix_world = rig.matrix_world.copy()
        copied_rig.data.pose_position = 'REST'
        for bone in copied_rig.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
            for constraint in tuple(bone.constraints):
                bone.constraints.remove(constraint)
        overlay = clone.modifiers.get(proof['overlay'])
        need(overlay is not None and overlay.type == 'NODES' and overlay.node_group.name == proof['node_group'],
             'Proven copied Direct overlay absent')
        clone.modifiers.remove(overlay)
        need([m.type for m in clone.modifiers] == ['ARMATURE', 'SUBSURF'], 'Original native modifier stack differs')
        need(clone.modifiers[0].object == rig, 'Original skinning rig differs')
        clone.modifiers[0].object = copied_rig
        bpy.context.window.scene = scene
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        original_skin = ordered_skin(clone, graph, skin)
        rest_before_cleanup = {bone.name: copied_rig.matrix_world @ bone.matrix_local
                               for bone in copied_rig.data.bones}
        retained = worker._clean_skeleton(bpy.context, copied_rig, [copied_rig, clone])
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        retained_names = set(retained)
        need(len(retained_names) == len(retained) and retained_names == set(copied_rig.data.bones.keys())
             and retained_names <= set(rest_before_cleanup), 'Retained skeleton source names differ')
        cleanup_rest_error = matrix_errors([rest_before_cleanup[n] for n in sorted(retained_names)],
            [copied_rig.matrix_world @ copied_rig.data.bones[n].matrix_local for n in sorted(retained_names)], metres)
        report['skeleton_cleanup_Rest'] = {'source_bones': len(rest_before_cleanup),
            'retained_count': len(retained_names), 'retained_names': sorted(retained_names),
            'retained_source_names_exact': True, 'matrix_error': cleanup_rest_error}
        need(cleanup_rest_error['translation_max_m'] <= LIMIT_M
             and cleanup_rest_error['linear_max_component'] <= LINEAR_LIMIT
             and cleanup_rest_error['homogeneous_max_component'] <= LINEAR_LIMIT,
             'Skeleton cleanup changed a retained source Rest matrix')
        target = base.native_mesh(clone, graph)
        expected_skin = ordered_skin(clone, graph, skin)
        need(skin_exact(original_skin, expected_skin), 'Skeleton cleanup discarded a named weight/UV/index field')
        need(len(target['points']) == 3040 and copied_rig.data.pose_position == 'REST'
             and clone.matrix_parent_inverse == inverse and clone.data != source.data and copied_rig.data != rig.data,
             'Independent REST3040 / parent inverse scope differs')
        report['copy_scope'] = {'Rig_and_Mesh_data_independent': True, 'matrix_parent_inverse_exact': True,
                                'Rest_before_oracle': True, 'vertices': len(target['points']), 'bones': len(retained)}
        warnings = []
        report['baker'] = worker._bake_mesh(bpy.context, clone, set(), warnings)
        graph = bpy.context.evaluated_depsgraph_get()
        report['REST_bake_error'] = base.geometry_pair(cold, target, base.native_mesh(clone, graph), metres)
        need(report['REST_bake_error']['maximum_m'] <= LIMIT_M
             and skin_exact(expected_skin, ordered_skin(clone, graph, skin))
             and len(clone.modifiers) == 1 and clone.modifiers[0].type == 'ARMATURE'
             and clone.modifiers[0].object == copied_rig and clone.matrix_parent_inverse == inverse,
             'REST bake same-index geometry/UV/all named weights failed')
        report['bake_warnings'] = warnings
        bone_names = set(copied_rig.data.bones.keys())
        parents = {n: copied_rig.data.bones[n].parent.name if copied_rig.data.bones[n].parent else None for n in bone_names}
        rest = {n: copied_rig.matrix_world @ copied_rig.data.bones[n].matrix_local for n in bone_names}
        phase('model_only_FBX_writer')
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in (clone, copied_rig))
        bpy.context.view_layer.objects.active = copied_rig
        bpy.ops.preferences.addon_enable(module='io_scene_fbx')
        calls = [n for n in ast.walk(ast.parse(WORKER.read_text(encoding='utf-8')))
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'fbx']
        need(len(calls) == 1, 'Pinned model-only writer ABI ambiguous')
        filename = 'plain_rest_skin_component.fbx'
        result = eval(compile(ast.Expression(body=calls[0]), str(WORKER), 'eval'),
                      {'bpy': bpy, 'stage': args.output, 'filename': filename})
        fbx_path = args.output/filename
        need('FINISHED' in result and fbx_path.is_file() and fbx_path.stat().st_size > 0, 'Model FBX writer failed')
        report.update(FBX_component_written=True, fbx={'path': str(fbx_path), 'sha256': sha(fbx_path)})
        phase('REST_reimport')
        imported_scene = bpy.data.scenes.new('Private REST Model Reimport')
        imported_scene.unit_settings.system = 'METRIC'
        imported_scene.unit_settings.scale_length = metres
        bpy.context.window.scene = imported_scene
        result = bpy.ops.import_scene.fbx(filepath=str(fbx_path), use_anim=False, use_custom_props=False,
                    automatic_bone_orientation=False, force_connect_children=False, ignore_leaf_bones=False)
        meshes = [o for o in imported_scene.objects if o.type == 'MESH']
        rigs = [o for o in imported_scene.objects if o.type == 'ARMATURE']
        need('FINISHED' in result and len(meshes) == len(rigs) == 1, 'Imported model identity ambiguous')
        mesh, arm = meshes[0], rigs[0]
        need(set(arm.data.bones.keys()) == bone_names
             and {n: arm.data.bones[n].parent.name if arm.data.bones[n].parent else None for n in bone_names} == parents,
             'Complete retained Rest skeleton names/parents differ')
        arm.data.pose_position = 'REST'
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        report['REST_reimport_error'] = base.geometry_pair(cold, target, base.native_mesh(mesh, graph), metres)
        report['skin_UV_named_weights_material_indices_loops_exact'] = skin_exact(expected_skin, ordered_skin(mesh, graph, skin))
        report['Rest_matrix_error'] = matrix_errors([rest[n] for n in sorted(bone_names)],
            [arm.matrix_world @ arm.data.bones[n].matrix_local for n in sorted(bone_names)], metres)
        errors = report['Rest_matrix_error']
        need(report['REST_reimport_error']['maximum_m'] <= LIMIT_M
             and report['skin_UV_named_weights_material_indices_loops_exact']
             and errors['translation_max_m'] <= LIMIT_M and errors['linear_max_component'] <= LINEAR_LIMIT
             and errors['homogeneous_max_component'] <= LINEAR_LIMIT, 'REST native FBX roundtrip failed')
        report['FBX_reimport_verified'] = True
        phase('component_checks_complete')
    except Exception as error:
        report['errors'].append({'error': repr(error), 'traceback': traceback.format_exc()})
    finally:
        if bpy is not None:
            if inventory is not None:
                try:
                    report['cleanup'] = cleanup_owned(bpy, home, inventory)
                    report['owned_native_cleanup'] = report['cleanup']['success']
                except Exception as error:
                    report['errors'].append({'owned_cleanup': repr(error), 'traceback': traceback.format_exc()})
                try:
                    report['original_raw_keys_Rest_pose_exact'] = author_receipt(bpy, q, originals) == before
                except Exception as error:
                    report['errors'].append({'original_protection': repr(error), 'traceback': traceback.format_exc()})
            try:
                result = bpy.ops.wm.read_factory_settings(use_empty=True)
                report['private_scene_disposed'] = ('FINISHED' in result and not bpy.data.filepath
                    and len(bpy.data.objects) == 0)
                need(report['private_scene_disposed'], 'Native factory disposal receipt failed')
            except Exception as error:
                report['errors'].append({'factory_disposal': repr(error), 'traceback': traceback.format_exc()})
        try:
            report['pinned_files_unchanged'] = all(sha(path) == value for path, value in pins.items())
        except Exception as error:
            report['errors'].append({'pins_after': repr(error)})
        report['native_component_verified'] = (report['FBX_reimport_verified'] and report['owned_native_cleanup']
            and report['private_scene_disposed'] and report['original_raw_keys_Rest_pose_exact']
            and report['pinned_files_unchanged'] and not report['errors'])
        report['elapsed_seconds'] = time.perf_counter() - started
        write()
    print(json.dumps({'native_component_verified': report['native_component_verified'], 'errors': report['errors']}), flush=True)
    return 0 if report['native_component_verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
