"""Run sealed Actor001 unchanged, with one disclosed Stage08 parent-remap fix.

The on-disk runtime/package remains Stage06/.41. Only the sealed replacement
_remap_rna function is compiled in its original globals; all three temporary
hooks are restored. Transform reads add no seek/update or matrix/world writes.
No blend save, GUI, deployment or acceptance policy changes.
"""
import argparse
import ast
import datetime
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ACTOR = HERE/'mesh_cache_actor_admission_001.py'
ACTOR_SHA = '2322463cb2e98a37d854ad199ffed1fc14b6fd68844d3af7a77769ca7f13e02b'
if hashlib.sha256(ACTOR.read_bytes()).hexdigest() != ACTOR_SHA:
    raise RuntimeError('Historical Actor001 changed')
import mesh_cache_actor_admission_001 as actor

base, require = actor.witness, actor.require
STAGE = HERE/'staged_20261015_08'
MANIFEST_SHA = 'a8bf6d459b5c058efb32c7935199b64c010d327ef6d5d9e90831d95a99c51bf8'
SCENE_SHA = '33e84ebd52d01ea99c5cdf9bf459464a6d52ea054766bb6e2893b02304b30c7c'
REFERENCE = HERE/'mesh_cache_actor_admission_report_001.json'
REFERENCE_SHA = 'c8903b0a20245e9b48d585224c6938658f11d6d0e9f304253721fa101ff1f278'


def matrix_hex(matrix):
    return [[float(value).hex() for value in row] for row in matrix]


def matrix_delta(reference, current):
    changed, maximum = [], 0.
    for i, (left, right) in enumerate(zip(reference, current)):
        for j, (a, b) in enumerate(zip(left, right)):
            av, bv = float.fromhex(a), float.fromhex(b)
            require(math.isfinite(av) and math.isfinite(bv), 'Nonfinite diagnostic matrix')
            maximum = max(maximum, abs(av-bv))
            if a != b:
                changed.append({'row': i, 'column': j, 'source_hex': a, 'copy_hex': b,
                                'zero_sign_only': av == 0. and bv == 0.})
    return {'hex_exact': not changed, 'max_abs_delta': maximum, 'changed_elements': changed,
            'all_differences_zero_sign_only': bool(changed) and all(row['zero_sign_only'] for row in changed)}


def restore_owned_hooks(bindings):
    result = {}
    for name, owner, attribute, installed, original in bindings:
        owned = getattr(owner, attribute) is installed
        if owned:
            setattr(owner, attribute, original)
        result[name] = owned and getattr(owner, attribute) is original
    return result


def object_state(obj, reverse, graph=None):
    def plain(item):
        values = {'identity': base.logical_id(item, reverse), 'pointer': int(item.as_pointer()),
            'session_uid': item.session_uid, 'world': matrix_hex(item.matrix_world),
            'basis': matrix_hex(item.matrix_basis), 'inverse': matrix_hex(item.matrix_parent_inverse),
            'parent': base.logical_id(item.parent, reverse), 'parent_pointer': int(item.parent.as_pointer()) if item.parent else None,
            'parent_session_uid': item.parent.session_uid if item.parent else None,
            'parent_type': item.parent_type, 'parent_bone': item.parent_bone, 'parent_vertices': list(item.parent_vertices),
            'rotation_mode': item.rotation_mode}
        for name in ('location', 'scale', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle',
                     'delta_location', 'delta_scale', 'delta_rotation_euler', 'delta_rotation_quaternion'):
            values[name] = [float(value).hex() for value in getattr(item, name)]
        values['constraints'] = []
        for constraint in item.constraints:
            row = {'name': constraint.name, 'type': constraint.type, 'mute': constraint.mute,
                   'influence': float(constraint.influence).hex()}
            for field in ('target', 'subtarget', 'owner_space', 'target_space'):
                if constraint.bl_rna.properties.get(field) is not None:
                    value = getattr(constraint, field)
                    row[field] = base.logical_id(value, reverse) if field == 'target' else value
            values['constraints'].append(row)
        return values
    result = {'raw': plain(obj)}
    if obj.parent is not None:
        result['raw_parent_world'] = matrix_hex(obj.parent.matrix_world)
    if graph is not None:
        evaluated = obj.evaluated_get(graph)
        result['evaluated'] = plain(evaluated)
        if obj.parent is not None:
            parent = obj.parent.evaluated_get(graph)
            result['evaluated_parent_world'] = matrix_hex(parent.matrix_world)
            if obj.parent_type == 'BONE':
                bone = parent.pose.bones.get(obj.parent_bone)
                require(bone is not None, 'Diagnostic parent pose bone missing')
                result['evaluated_parent_pose_matrix'] = matrix_hex(bone.matrix)
    return result


def sealed_remap(globals_dict):
    manifest_path = STAGE/'source_manifest.json'
    require(base.pin(manifest_path)['sha256'] == MANIFEST_SHA, 'Stage08 manifest changed')
    package = STAGE/'addons/character_designer'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    sealed = base.verify_package_manifest(package, manifest)
    path = package/'forearm_twist_playback_scene.py'
    require(base.pin(path)['sha256'] == SCENE_SHA, 'Stage08 parent-remap source changed')
    tree = ast.parse(path.read_text(encoding='utf-8'))
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == '_remap_rna')
    scope = dict(globals_dict)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), scope)
    return scope['_remap_rna'], scope, {'manifest': base.pin(manifest_path), 'scene_source': base.pin(path),
        'package': sealed, 'function_ast_sha256': hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest(),
        'scope': 'Only _remap_rna from Stage08 is injected; Stage06/.41 package and Actor001 main remain unchanged. Stage08 additionally contains canonical HEAD .42 version metadata, which is not executed.'}


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath,
            'Fresh private background factory worker required')
    require(any(value in ('-t', '--threads') and native[i+1] == '1' for i, value in enumerate(native[:-1])), '-t 1 required')
    require(base.pin(REFERENCE)['sha256'] == REFERENCE_SHA, 'Preserve the actual Actor001 failed receipt')
    reference = json.loads(REFERENCE.read_text(encoding='utf-8-sig'))
    bad = {row['source'] for row in reference['meshes'] if row['changed_components'] == ['object_matrix_world']}
    require(len(reference['meshes']) == 69 and len(bad) == 7 and reference['completed'] is False,
            'Unexpected reference failure scope')
    controls = [row['source'] for row in reference['meshes'] if row['exact']][:2]
    selected = bad | set(controls)
    package = Path(args.addons).resolve()/'character_designer'
    manifest = json.loads(Path(args.source_manifest).read_text(encoding='utf-8-sig'))
    base.verify_package_manifest(package, manifest)
    sys.path.insert(0, str(package.parent))
    scene_module = importlib.import_module('character_designer.forearm_twist_playback_scene')
    require(Path(scene_module.__file__).resolve() == package/'forearm_twist_playback_scene.py', 'Wrong Stage06 module')
    original_remap, original_build = scene_module._remap_rna, scene_module.build_isolated_scene
    original_geometry, original_select = base.geometry_witness, actor.select_scene
    patched, scope, seal = sealed_remap(scene_module.__dict__)
    state = {'session': None, 'build_started': False}
    diagnostics = {'selected_objects': sorted(selected), 'reference_world_only_failures': sorted(bad),
                   'passing_controls': controls, 'parent_remaps': [], 'source_before_clone': {},
                   'clone_before_flatten_raw': {}, 'clone_after_flatten_before_seek_raw': {},
                   'candidate_evaluated': {}, 'world_deltas': {}, 'phases': []}
    report.update(reused_actor=base.pin(ACTOR), reference_failure=base.pin(REFERENCE),
                  wrapper=base.pin(__file__), runtime_parent_patch=seal, transform_diagnostics=diagnostics)
    started = time.perf_counter()

    def progress(phase):
        row = {'phase': phase, 'elapsed_seconds': time.perf_counter()-started}
        diagnostics['phases'].append(row)
        print('PC2_PARENT003_PHASE', phase, round(row['elapsed_seconds'], 6), flush=True)

    def remap(struct, id_map, visited, external):
        if not isinstance(struct, bpy.types.Object):
            return patched(struct, id_map, visited, external)
        reverse = {int(value.as_pointer()): key for key, value in id_map.items()}
        owner = getattr(struct, 'id_data', None)
        owned = owner is not None and int(owner.as_pointer()) in reverse
        source = reverse.get(int(struct.as_pointer()))
        capture = owned and source is not None and source.name in selected and struct.parent in id_map
        row = {'source': source.name, 'before': object_state(struct, reverse)} if capture else None
        if row is not None:
            diagnostics['parent_remaps'].append(row)
        try:
            return patched(struct, id_map, visited, external)
        finally:
            if row is not None:
                row['after'] = object_state(struct, reverse)

    def build(source_scene):
        state['build_started'] = True
        progress('build_begin')
        before = time.perf_counter()
        try:
            session = original_build(source_scene)
        finally:
            diagnostics['build_seconds'] = time.perf_counter()-before
        state['session'] = session
        try:
            reverse = {int(value.as_pointer()): key for key, value in session.id_map.items()}
            diagnostics['clone_before_flatten_raw'] = {source.name: object_state(target, reverse)
                for source, target in session.object_map.items() if source.name in selected}
            progress('build_end_before_flatten')
            return session
        except BaseException:
            # Actor001 has not received this Session yet. Our observer owns
            # failure cleanup until the successful return transfers ownership.
            try:
                session.close()
            except BaseException:
                diagnostics['build_observer_cleanup_error'] = traceback.format_exc()
            state['session'] = None
            raise

    def select(bpy_arg, scene):
        session = state['session']
        if session is not None and scene is session.scene and not diagnostics['clone_after_flatten_before_seek_raw']:
            reverse = {int(value.as_pointer()): key for key, value in session.id_map.items()}
            diagnostics['clone_after_flatten_before_seek_raw'] = {source.name: object_state(target, reverse)
                for source, target in session.object_map.items() if source.name in selected}
            progress('flatten_end_before_existing_seek')
        return original_select(bpy_arg, scene)

    def geometry(obj, reverse):
        result = original_geometry(obj, reverse)
        source = reverse.get(int(obj.as_pointer()), obj)
        if source.name in selected:
            snapshot = object_state(obj, reverse, bpy.context.evaluated_depsgraph_get())
            require(base.object_hash(snapshot['evaluated']['world']) == result['components']['object_matrix_world'],
                    'Diagnostic matrix does not match the unchanged oracle')
            if not state['build_started']:
                diagnostics['source_before_clone'][source.name] = snapshot
            elif reverse:
                diagnostics['candidate_evaluated'][source.name] = snapshot
                diagnostics['world_deltas'][source.name] = matrix_delta(
                    diagnostics['source_before_clone'][source.name]['evaluated']['world'], snapshot['evaluated']['world'])
        return result

    scene_module._remap_rna = scope['_remap_rna'] = remap
    scene_module.build_isolated_scene = build
    base.geometry_witness, actor.select_scene = geometry, select
    try:
        progress('sealed_actor001_main_begin')
        actor.main(args, report)
        progress('sealed_actor001_main_end')
    finally:
        report['hook_ownership_and_restoration'] = restore_owned_hooks((
            ('select_scene', actor, 'select_scene', select, original_select),
            ('geometry_witness', base, 'geometry_witness', geometry, original_geometry),
            ('build_isolated_scene', scene_module, 'build_isolated_scene', build, original_build),
            ('_remap_rna', scene_module, '_remap_rna', remap, original_remap)))
        report['temporary_hooks_restored'] = all(report['hook_ownership_and_restoration'].values())
        report['parent_patch_source_pins_unchanged'] = (report['wrapper'] == base.pin(__file__)
            and report['reused_actor'] == base.pin(ACTOR) and report['reference_failure'] == base.pin(REFERENCE)
            and seal['manifest'] == base.pin(STAGE/'source_manifest.json')
            and seal['package'] == base.verify_package_manifest(STAGE/'addons/character_designer',
                json.loads((STAGE/'source_manifest.json').read_text(encoding='utf-8-sig'))))
        require(report['temporary_hooks_restored'] and report['parent_patch_source_pins_unchanged'], 'Parent diagnostic cleanup/source seal failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('input', 'artist', 'addons', 'source-manifest', 'cache-dir', 'report'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema': 'x.pc2-actor-parent-remap-diagnostic/1', 'completed': False, 'diagnostic_only': True,
        'pid': os.getpid(), 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'no_artifact_save': True, 'no_adoption_or_deploy': True, 'gui_fps_verified': False,
        'limits': ['Source property scope remains Actor001 base/raw; no registered RNA/foreign payload claim.',
                   'Transform snapshot reads add no frame_set/update, world setter, TRS repair or tolerance relaxation.',
                   'All Actor001 mesh/source/cleanup gates remain unchanged; build timing is offline preparation, not playback FPS.']}
    with Path(args.report).resolve().open('x', encoding='utf-8') as stream:
        try:
            main(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
