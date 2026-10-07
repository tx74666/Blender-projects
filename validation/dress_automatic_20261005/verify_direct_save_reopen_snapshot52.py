"""One private Direct Save/Reopen and plain ARM snapshot component; Root runs BG.

No FBX/Unity/Action export, cache bake/seek, artist save or public export waiver.
The stripped oracle deliberately omits Cloth AND the raw80 Body attachment.
Native flags remain false until the final source/disk/disposal AND succeeds.
"""
import argparse
import ast
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPOSITORY = Path('D:/MyRepository/Blender-addons-by-Randy')
PROVIDER = REPOSITORY/'addons/character_designer/skirt_surface_direct.py'
COLD = HERE/'verify_direct_cold_install52_v4.py'
COLD_SHA = '4bb8e79fbad87950c75c1999e27d97657733ea42695df8e0f2b3a2ae4f58c536'
LIMIT_M = 5e-5


def need(value, message):
    if not value:
        raise RuntimeError('DirectSaveSnapshot52: ' + message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def load(path, expected, name):
    need(sha(path) == expected, 'Frozen input differs: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def json_value(value):
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False))


def cold_gate(prior, actual_manifest, receipt_sha, provider_sha):
    need(type(prior) is dict and prior.get('native_component_completed') is True
         and prior.get('private_scene_disposed') is True and prior.get('source_files_Artist_exact') is True
         and prior.get('errors') == [] and prior.get('installed_backend') == 'DIRECT_MAIN_CLOTH_V1',
         'Actual completed current Direct cold prerequisite required')
    need(prior.get('source_before') == actual_manifest == prior.get('source_after')
         and prior.get('artist_after', {}).get('sha256') == receipt_sha,
         'Actual Cold source/Artist receipt differs; no historical normalization')
    rows = [row for name, row in actual_manifest.items() if Path(name).resolve() == PROVIDER.resolve()]
    need(len(rows) == 1 and rows[0].get('sha256') == provider_sha, 'Cold actual provider fingerprint differs')


def native_mesh(obj, graph):
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
    try:
        mesh.calc_loop_triangles()
        indices = [v.index for v in mesh.vertices]
        need(indices == list(range(len(indices))), 'Native vertex indexing is not addressable')
        points = [evaluated.matrix_world @ v.co for v in mesh.vertices]
        need(points and all(math.isfinite(x) for point in points for x in point), 'Nonfinite/empty native mesh')
        return {'points': points, 'edges': [tuple(e.vertices) for e in mesh.edges],
                'faces': [tuple(f.vertices) for f in mesh.polygons],
                'triangles': [tuple(t.vertices) for t in mesh.loop_triangles]}
    finally:
        evaluated.to_mesh_clear()


def geometry_pair(cold, first, second, metres):
    need(first['edges'] == second['edges'] and first['faces'] == second['faces'], 'Native base connectivity changed')
    # Loop triangulation can depend on coordinates; saved triangles are evidence,
    # not an identity substitute for original polygon connectivity.
    return dict(cold.error(first['points'], second['points'], metres),
                triangles_exact=first['triangles'] == second['triangles'])


def author_asset_receipt(protection):
    return json_value({'meshes': protection.meshes, 'rest': protection.rests,
                       'actions': protection.actions, 'nla_assets': protection.start_nla})


def author_assets_exact(q, expected):
    """New native IDs after reopen, matching every original authored asset by ID name."""
    current = author_asset_receipt(q.Protection())
    changed = {kind: [name for name, content in rows.items() if current[kind].get(name) != content]
               for kind, rows in expected.items()}
    return {'success': not any(changed.values()), 'changed_or_missing': changed,
            'pointers_compared_across_reopen': False}


def authored_contract(bpy, p, q, direct, source, rig, body):
    """Semantic content only; native pointers/users are not cross-process proof."""
    keys = body.data.shape_keys
    need(source.data.shape_keys is None and body.data.users == 1 and keys is not None
         and len(keys.key_blocks) == 12, 'Exact no-Dress-Keys/Body12-Key scope required')
    objects = (source, rig, body)
    rest = q.rest_content(rig)
    for bone in rig.data.bones:
        rest[bone.name].update(head=list(bone.head_local), tail=list(bone.tail_local))
    return json_value({'raw': {o.name: q.digest(q.raw_mesh_content(o)) for o in (source, body)},
        'Rest': q.digest(rest), 'pose': q.pose_channels(rig), 'pose_position': rig.data.pose_position,
        'custom': {o.name: {key: q.custom_content(value) for key, value in o.items()} for o in objects},
        'parents': {o.name: direct.shared._frame(o) for o in objects},
        'bindings': {o.name: [p.animation(o, q), p.animation(o.data, q)] for o in objects},
        'Body_Key_channels': [q.simple_rna(keys), [q.simple_rna(k) for k in keys.key_blocks]],
        'Body_Key_binding': p.animation(keys, q),
        'Actions': {a.name: q.digest(q.action_content(a)) for a in bpy.data.actions},
        'constraints': {pb.name: [(c.name, c.type, direct.shared._rna(c)) for c in pb.constraints] for pb in rig.pose.bones},
        'drivers': direct.shared._drivers(rig), 'frame': [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe],
        'units': q.simple_rna(bpy.context.scene.unit_settings)})


def installed_objects(bpy, direct, identity):
    source, rig, body = (bpy.data.objects.get(identity[k]) for k in ('source', 'rig', 'body'))
    need(source is not None and rig is not None and body is not None
         and source.type == body.type == 'MESH' and rig.type == 'ARMATURE', 'Saved explicit source IDs missing')
    record = direct.skirt.read_record(source)
    need(source.get(direct.skirt.RIG_KEY) == rig and record['source'] == source.name
         and record['rig'] == rig.name and record['owner'] == identity['owner'], 'Saved source pointer/owner changed')
    need(bpy.context.scene.name == identity['scene'], 'Saved installation home Scene changed')
    direct.validate(source, rig, record)
    return source, rig, body, record


def mode_contract(q, direct, source, record):
    """Detach semantic state; capture_mode contains session-bound native RNA."""
    state = direct.capture_mode(source, record)
    return json_value({'source': q.id_name(state['source']), 'owner': state['owner'],
        'modifier': [state['modifier'].name, state['modifier'].type], 'group': q.id_name(state['group']),
        'cloth': [state['cloth'].name, state['cloth'].type], 'raw_state': state['raw_state'],
        'state': state['state'], 'socket': state['socket'],
        'overlay_flags': state['overlay_flags'], 'cloth_flags': state['cloth_flags']})


def private_cache_scope(direct, source, record):
    cloth = direct._object(source, record, 'CLOTH_PROXY').modifiers[-1]
    cache = cloth.point_cache
    values = {name: getattr(cache, name) for name in ('is_baked', 'is_baking', 'use_disk_cache', 'use_external')}
    need(all(type(value) is bool and value is False for value in values.values()),
         'Only a fresh unsealed local RAM cache may enter this private Save/Reopen check')
    return dict(values, configuration=[cache.frame_start, cache.frame_end, cache.frame_step, cache.name],
                memory_payload_preserved='Unmeasured', cross_reopen_pointer_comparable=False)


def save_private(bpy, path, output):
    path = path.resolve()
    need(path.is_relative_to(output.resolve()) and not path.exists(), 'Only new private candidate files may be saved')
    path.parent.mkdir(parents=True, exist_ok=True)
    result = bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
    need('FINISHED' in result and Path(bpy.data.filepath).resolve() == path and path.is_file(), 'Native private save did not finish')
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size, 'native_save_finished': True}


def exercise(bpy, args, p, q, cold, direct, source, rig, body, report, write, budget):
    from character_designer import skirt_physics as physics, skirt_motion_tuning as tuning
    context = bpy.context
    metres = context.scene.unit_settings.scale_length
    need(math.isfinite(metres) and metres > 0., 'Unknown native metre scale')
    # The original author assets are protected throughout this process. Fresh
    # per-session Protection instances are required after reopening native IDs.
    author = q.Protection()
    author_assets = author_asset_receipt(author)
    installed = physics.add_physics(context, source, backend=direct.BACKEND, body=body, capability='BOTH')
    tuning.apply(context, [source], mode='MANUAL')
    installed, actual_rig, c, cloth = physics.validate_physics(source)
    need(actual_rig == rig and not cloth.show_viewport and not cloth.show_render,
         'Manual private candidate must pause the new Cloth without freeing its cache')
    report['installed_author_protection'] = author.verify()
    need(report['installed_author_protection']['success'], 'Cold install changed original raw/Rest/Actions')
    identity = {'source': source.name, 'rig': rig.name, 'body': body.name,
                'owner': installed['owner'], 'scene': context.scene.name}
    baseline = authored_contract(bpy, p, q, direct, source, rig, body)
    proof = direct.export_capture(source)
    state = mode_contract(q, direct, source, installed)
    native_before = native_mesh(source, context.evaluated_depsgraph_get())
    need(len(native_before['points']) == 3040, 'Actual visible source3040 missing')
    report['identity'] = identity
    report['captured_omission'] = proof['omission']
    report['born_mode'] = state
    report['cache_scope_before'] = private_cache_scope(direct, source, installed)
    report['semantic_digest_before'] = q.digest(baseline)
    write(); budget()
    report['candidate_save'] = save_private(bpy, args.output/'Direct_Manual_candidate.blend', args.output)
    need(author.verify()['success'] and authored_contract(bpy, p, q, direct, source, rig, body) == baseline,
         'Native save changed original author content/channels')
    direct.validate_snapshot(source, proof)
    bpy.ops.wm.open_mainfile(filepath=report['candidate_save']['path'], load_ui=False)
    source, rig, body, installed = installed_objects(bpy, direct, identity)
    report['candidate_reopen_original_assets'] = author_assets_exact(q, author_assets)
    report['candidate_reopen_contract_exact'] = authored_contract(bpy, p, q, direct, source, rig, body) == baseline
    report['candidate_mode_exact'] = mode_contract(q, direct, source, installed) == state
    report['candidate_cache_scope'] = private_cache_scope(direct, source, installed)
    direct.validate_snapshot(source, proof)
    native_reopened = native_mesh(source, bpy.context.evaluated_depsgraph_get())
    report['candidate_visible_reopen'] = geometry_pair(cold, native_before, native_reopened, metres)
    write(); need(report['candidate_reopen_original_assets']['success']
                  and report['candidate_reopen_contract_exact'] and report['candidate_mode_exact']
                  and report['candidate_cache_scope'] == report['cache_scope_before']
                  and report['candidate_visible_reopen']['maximum_m'] <= LIMIT_M,
                  'Private installed candidate Save/Reopen contract or visible Manual pose failed')
    budget()
    saved = save_private(bpy, args.output/'cdesigner-unity-direct-qa'/'character.blend', args.output)
    report['snapshot_save'] = saved
    need(authored_contract(bpy, p, q, direct, source, rig, body) == baseline, 'Private snapshot save changed author data')
    bpy.ops.wm.open_mainfile(filepath=saved['path'], load_ui=False)
    source, rig, body, installed = installed_objects(bpy, direct, identity)
    report['snapshot_reopen_original_assets'] = author_assets_exact(q, author_assets)
    direct.validate_snapshot(source, proof)
    report['snapshot_reopen_contract_exact'] = authored_contract(bpy, p, q, direct, source, rig, body) == baseline
    report['snapshot_mode_exact'] = mode_contract(q, direct, source, installed) == state
    report['snapshot_cache_scope'] = private_cache_scope(direct, source, installed)
    write(); need(report['snapshot_reopen_original_assets']['success'] and report['snapshot_reopen_contract_exact']
                  and report['snapshot_mode_exact'] and report['snapshot_cache_scope'] == report['cache_scope_before'],
                  'Private snapshot reopen failed')
    protected = q.Protection()
    output_group_name = proof['node_group']
    helper_names = [name for names in proof['roles'].values() for name in names]
    helper_ids = {name: (bpy.data.objects[name].as_pointer(), bpy.data.objects[name].data.as_pointer()) for name in helper_names}
    # A separate plain native skin oracle: clear Object AND independent Mesh
    # registration before linking, and remove the copied output modifier first.
    oracle = oracle_data = None
    try:
        oracle = source.copy(); oracle_data = source.data.copy(); oracle.data = oracle_data
        for owner in (oracle, oracle_data):
            for key in list(owner.keys()): del owner[key]
        for modifier in list(oracle.modifiers):
            if modifier.name == proof['overlay']: oracle.modifiers.remove(modifier)
        need([m.type for m in oracle.modifiers] in (['ARMATURE'], ['ARMATURE', 'SUBSURF'])
             and oracle.modifiers[0].object == rig, 'Oracle must contain only the original native skin/Subsurf')
        oracle.name = 'Direct plain skin comparison'
        bpy.context.scene.collection.objects.link(oracle)
        oracle_baseline = native_mesh(oracle, bpy.context.evaluated_depsgraph_get())
        report['oracle_scope'] = {'plain_native_skin': True, 'Body_attachment': False, 'Cloth': False,
                                 'final_surface_equivalent': False, 'native_count': len(oracle_baseline['points'])}
        direct.validate_snapshot(source, proof)
        report['strip'] = direct.strip_export_snapshot(source, proof)
        need(report['strip']['body_attachment_omitted'] is True and report['strip']['physics_omitted'] is True
             and report['strip']['final_surface_equivalent'] is False and report['strip']['export_verified'] is False,
             'Strip omission boundary was misrepresented')
        graph = bpy.context.evaluated_depsgraph_get()
        stripped, oracle_now = native_mesh(source, graph), native_mesh(oracle, graph)
        report['stripped_vs_plain_oracle'] = geometry_pair(cold, oracle_now, stripped, metres)
        report['plain_oracle_not_changed_by_strip'] = geometry_pair(cold, oracle_baseline, oracle_now, metres)
        report['stripped_author_contract_exact'] = authored_contract(bpy, p, q, direct, source, rig, body) == baseline
        report['helpers_retained_exact'] = helper_ids == {
            name: (bpy.data.objects[name].as_pointer(), bpy.data.objects[name].data.as_pointer()) for name in helper_names}
        report['only_owned_output_removed'] = (bpy.data.node_groups.get(output_group_name) is None
            and [m.type for m in source.modifiers] == [m.type for m in oracle.modifiers])
        report['strip_raw_Rest_Actions_protection'] = protected.verify()
        write()
        need(report['stripped_vs_plain_oracle']['maximum_m'] <= LIMIT_M
             and report['plain_oracle_not_changed_by_strip']['maximum_m'] == 0.
             and report['stripped_author_contract_exact'] and report['helpers_retained_exact']
             and report['only_owned_output_removed'] and report['strip_raw_Rest_Actions_protection']['success'],
             'Plain native skin strip, original author data, or owned helper boundary failed')
        # Installed validation cannot be applied to the intentionally stripped
        # record. Its original ARM/parent/raw/Rest/Action contracts were checked.
        budget()
    finally:
        if oracle is not None: bpy.data.objects.remove(oracle, do_unlink=True)
        if oracle_data is not None:
            need(oracle_data.users == 0, 'Oracle Mesh gained an outside user')
            bpy.data.meshes.remove(oracle_data)
    need(protected.verify()['success'], 'Oracle cleanup changed protected source author assets')
    report['native_stages_completed'] = True


def pure_checks(args, cold, actual_manifest):
    tree = ast.parse(PROVIDER.read_text(encoding='utf-8'))
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    expected = {'export_capture': ['source'], 'validate_snapshot': ['source', 'proof'],
                'strip_export_snapshot': ['source', 'proof'], 'capture_mode': ['source', 'record'],
                'validate': ['source', 'rig', 'record']}
    need(all(name in functions and [a.arg for a in functions[name].args.args] == argspec
             for name, argspec in expected.items()), 'Actual provider hook ABI differs')
    prior = json.loads(args.cold_report.read_text(encoding='utf-8'))
    cold_gate(prior, actual_manifest, args.artist_protection_sha, args.expected_direct_sha)
    negatives = [('native_component_completed', 1), ('private_scene_disposed', None),
                 ('source_files_Artist_exact', False), ('errors', ['failed']), ('installed_backend', 'ACTUAL_SURFACE_DELTA_V1')]
    for key, value in negatives:
        wrong = dict(prior, **{key: value})
        try: cold_gate(wrong, prior['source_after'], args.artist_protection_sha, args.expected_direct_sha)
        except RuntimeError: pass
        else: need(False, 'Cold negative accepted: '+key)
    for manifest, receipt, provider in [(dict(prior['source_after'], unknown={}), args.artist_protection_sha, args.expected_direct_sha),
                                      (prior['source_after'], '0'*64, args.expected_direct_sha),
                                      (prior['source_after'], args.artist_protection_sha, '0'*64)]:
        try: cold_gate(prior, manifest, receipt, provider)
        except RuntimeError: pass
        else: need(False, 'Source/Artist/provider mismatch accepted')
    cold_text = COLD.read_text(encoding='utf-8')
    need('def load_artist(bpy, p, locator, artist, body_name, dress_name):' in cold_text,
         'Frozen explicit native locator ABI differs')
    own = ast.parse(Path(__file__).read_text(encoding='utf-8'))
    native_calls = {n.func.attr for n in ast.walk(own) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    need(not native_calls & {'frame_set', 'bake', 'free_bake', 'reset_simulation'}, 'Save component must not seek/bake/free/reset')
    print(json.dumps({'pure_actual_provider_ABI': len(expected), 'actual_Cold_positive': True,
                      'Cold_Source_Artist_negatives': len(negatives)+3, 'no_timeline_or_cache_commands': True,
                      'native_run': False, 'effect_or_export_accepted': False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--artist-protection', type=Path, required=True); parser.add_argument('--artist-protection-sha', required=True)
    parser.add_argument('--cold-report', type=Path, required=True); parser.add_argument('--cold-report-sha', required=True)
    parser.add_argument('--expected-direct-sha', required=True)
    parser.add_argument('--body-object', required=True); parser.add_argument('--dress-object', required=True)
    parser.add_argument('--soft-seconds', type=float, default=180.); parser.add_argument('--pure-checks', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE) and not args.output.exists(), 'Fresh private output directory required')
    need(args.cold_report.is_absolute() and args.cold_report.resolve().is_relative_to(HERE), 'Explicit actual Cold report in X required')
    need(args.artist_protection.is_absolute() and args.artist_protection.resolve().is_relative_to(HERE), 'Explicit current Artist receipt in X required')
    need(0. < args.soft_seconds <= 240., 'Bounded source-prepared component only')
    for value in (args.expected_direct_sha, args.cold_report_sha, args.artist_protection_sha):
        need(len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'Full lowercase SHA256 required')
    cold = load(COLD, COLD_SHA, 'direct_save_cold')
    p = load(cold.COMPARATOR, cold.COMPARATOR_SHA, 'direct_save_readers')
    disk = load(p.DISK, p.DISK_SHA, 'direct_save_disk')
    manifest = load(p.SOURCE, p.SOURCE_SHA, 'direct_save_manifest')
    pins = {Path(__file__).resolve(): sha(__file__), COLD: COLD_SHA, cold.COMPARATOR: cold.COMPARATOR_SHA,
            cold.LOCATOR: cold.LOCATOR_SHA, p.QA: p.QA_SHA, p.DISK: p.DISK_SHA, p.SOURCE: p.SOURCE_SHA,
            PROVIDER: args.expected_direct_sha, args.cold_report: args.cold_report_sha,
            args.artist_protection: args.artist_protection_sha}
    need(all(sha(path) == value for path, value in pins.items()), 'Actual source/helper/Cold/Artist/self pins differ')
    if args.pure_checks:
        pure_checks(args, cold, manifest.current_manifest()); return 0
    import bpy
    need(bpy.app.background and bpy.app.version[:2] == (5, 2) and '--factory-startup' in sys.argv
         and Path(bpy.app.binary_path).resolve() == Path('D:/Blender5.2/blender.exe').resolve()
         and '--disable-autoexec' in sys.argv and not bpy.data.filepath, 'Empty factory protected background native5.2 only')
    before = manifest.current_manifest(); started = time.perf_counter(); args.output.mkdir()
    report = {'stage': 'DIRECT_PRIVATE_SAVE_REOPEN_PLAIN_SNAPSHOT52', 'native_component_verified': False,
        'native_stages_completed': False, 'Save_Reopen_verified': False, 'plain_snapshot_verified': False,
        'accepted': False, 'effect_accepted': False, 'ART_accepted': False, 'export_accepted': False, 'FBX_verified': False,
        'Unity_verified': False, 'animation_verified': False, 'artist_saved': False, 'deployed': False,
        'final_surface_equivalent': False, 'Body_attachment_preserved_in_plain_snapshot': False,
        'cache_payload_preserved': 'Unmeasured', 'timeline_seek_by_QA': False, 'errors': [], 'source_before': before,
        'runtime': {'version': list(bpy.app.version), 'binary': bpy.app.binary_path},
        'pins': {str(path): value for path, value in pins.items()}}
    def write():
        (args.output/'report.json').write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2), encoding='utf-8')
    def budget(): need(time.perf_counter()-started < args.soft_seconds, 'Bounded native component incomplete')
    try:
        report['artist_before'] = disk.proof(args.artist_protection, args.artist_protection_sha)
        prior = json.loads(args.cold_report.read_text(encoding='utf-8'))
        cold_gate(prior, before, args.artist_protection_sha, args.expected_direct_sha)
        report['cold_prerequisite'] = {'path': str(args.cold_report), 'sha256': args.cold_report_sha, 'component_only': True}
        locator = load(cold.LOCATOR, cold.LOCATOR_SHA, 'direct_save_locator')
        q = p.readers(bpy)
        scene, rig, body, source, record, choices = cold.load_artist(bpy, p, locator,
            Path(report['artist_before']['receipt']['artist_path']), args.body_object, args.dress_object)
        loaded = q.Protection(); pose = q.pose_channels(rig)
        sys.path.insert(0, str(REPOSITORY/'addons'))
        package = importlib.import_module('character_designer'); package.register()
        direct = importlib.import_module('character_designer.skirt_surface_direct')
        need(Path(direct.__file__).resolve() == PROVIDER.resolve() and loaded.verify()['success']
             and q.pose_channels(rig) == pose, 'Canonical registration changed original author content/pose')
        report['explicit_selection'] = choices
        exercise(bpy, args, p, q, cold, direct, source, rig, body, report, write, budget)
    except Exception as exc:
        report['errors'].append({'exception': repr(exc), 'traceback': traceback.format_exc()})
    finally:
        try:
            bpy.ops.wm.read_factory_settings(use_empty=True); report['private_scene_disposed'] = True
        except Exception as exc: report['errors'].append({'disposal': repr(exc)})
        try:
            report['artist_after'] = disk.proof(args.artist_protection, args.artist_protection_sha)
            report['source_after'] = manifest.current_manifest()
            report['source_files_Artist_exact'] = report['source_after'] == before and all(sha(path) == value for path, value in pins.items())
            need(report['source_files_Artist_exact'], 'Source/helper/Cold/Artist files changed')
        except Exception as exc: report['errors'].append({'final_guard': repr(exc)})
        verified = report['native_stages_completed'] and not report['errors'] and report.get('private_scene_disposed') is True
        report['native_component_verified'] = verified
        report['Save_Reopen_verified'] = verified
        report['plain_snapshot_verified'] = verified
        report['elapsed_seconds'] = time.perf_counter()-started; write()
    print(json.dumps({'native_component_verified': report['native_component_verified'], 'errors': report['errors'],
                      'report': str(args.output/'report.json'), 'effect_or_export_accepted': False}))
    return 0 if report['native_component_verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
