"""Prepared model-only PNS library/reopen/strip proof; Root alone runs Native.

Fresh public button Direct install, real Original correction, no seek/reset/bake.
Historical1751 establishes old component/ABI provenance only. Current graph is
proved anew, and the explicit current full source manifest stays exact.
No animation, FBX, Unity, artist save, final Cloth equivalence or public waiver.
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
RUNTIME = REPOSITORY/'addons/character_designer'
BASE = HERE/'verify_direct_save_reopen_snapshot52.py'
BASE_SHA = '4f107e6e47f7a81fbb17adff83940aa4ac61562363815dbd919267caeabf4741'
HISTORY = HERE/'actual_direct_save_reopen_snapshot_e0b_52_20261007_080226_267/result/report.json'
HISTORY_SHA = '1751d54e72893d8b865fe9a8cfb39a515ec28831b3317c2e2feacada40a7d74a'
OLD_PROVIDER_SHA = 'eb1ad005da9c98082b577c4dca4ab32a111ec684fa2ba27e3612b0c396205e99'
PROVIDER_SHA = 'e07634927c790323ffa70c19e52320ce0068fbd65e0447770ff515bea3fdd9c3'
SKIRT_SHA = '5f6baf35bad958d4235ebc4c1d935e38e168b1eb4deec0abe7fab462102ea742'
PLAIN_SHA = '8e2477f7cb5756ee0b479d7749344cbaa41b6a838d85f3f20792240cd54e6980'
PREVIOUS = HERE/'verify_plain_native_skin_model52.py'
PREVIOUS_SHA = 'f731777012bf9d3843fc49da86b3542a4b85b04ace5d56677e5a79550a182c36'


def need(value, message):
    if not value:
        raise RuntimeError('PNSModel52: '+message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def load(path, expected, name):
    need(sha(path) == expected, 'Frozen dependency differs: '+str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def historical_provenance(prior):
    need(type(prior) is dict and all(prior.get(k) is True for k in
         ('native_component_verified', 'native_stages_completed', 'Save_Reopen_verified',
          'plain_snapshot_verified', 'source_files_Artist_exact', 'private_scene_disposed'))
         and prior.get('errors') == [] and prior.get('source_before') == prior.get('source_after'),
         'Historical component must remain genuinely complete')
    provider = str(RUNTIME/'skirt_surface_direct.py')
    need(prior['source_before'].get(provider, {}).get('sha256') == OLD_PROVIDER_SHA
         and prior.get('FBX_verified') is False and prior.get('Unity_verified') is False
         and prior.get('animation_verified') is False, 'Historical provider/scope differs')
    return {'path': str(HISTORY), 'sha256': HISTORY_SHA, 'old_provider_sha256': OLD_PROVIDER_SHA,
            'current_source_or_native_acceptance': False, 'protected_helper_ABI_provenance_only': True}


def public_install(bpy, direct, source, rig, body, report):
    """Temporary, explicit private Setup pointers; never claim artist registration."""
    from character_designer import character_setup, skirt as ui

    context = bpy.context
    setup, state = character_setup.settings(context), ui._settings(context)
    need(setup is not None and state is not None and source.get(direct.skirt.RIG_KEY) == rig,
         'Actual registered Setup/WM pointers or selected source Rig missing')
    original = (setup.rig, setup.body, state.source)
    def pointer_names():
        return [None if item is None else item.name for item in (setup.rig, setup.body, state.source)]
    def selection():
        active = context.view_layer.objects.active
        return {'mode': context.mode, 'active': None if active is None else active.name,
                'selected': sorted(item.name for item in context.selected_objects)}
    receipt = {'private_setup_only': True, 'artist_registration_claimed': False,
               'pointer_names_before': pointer_names(), 'UI_before': selection(), 'poll': None,
               'operator_result': None, 'restored_exact': False}
    report['public_install_entry'] = receipt
    try:
        setup.rig, setup.body, state.source = rig, body, source
        direct.skirt._activate(context, source, 'OBJECT')
        need(setup.rig == rig and setup.body == body and state.source == source and ui._source(context) == source,
             'Public installation must resolve this one explicit native source/Rig/Body')
        receipt['poll'] = bpy.ops.character_designer.skirt_add_physics.poll()
        need(receipt['poll'] is True, 'Controls-only LEGACY must admit the real Add Physics button')
        result = bpy.ops.character_designer.skirt_add_physics('EXEC_DEFAULT', actual_surface=True)
        receipt['operator_result'] = sorted(result)
        need('FINISHED' in result, 'Public Add Physics did not finish; no service fallback is allowed')
        installed = direct.skirt.read_record(source)
        receipt['installed_backend'] = installed.get('physics', {}).get('backend')
        need(receipt['installed_backend'] == direct.BACKEND and installed['source'] == source.name
             and installed['rig'] == rig.name and installed['owner'] == source[direct.skirt.OWNER_KEY]
             and bpy.data.objects.get(installed['physics']['surface']['body']) == body,
             'Public button returned an unknown backend, owner, Rig or actual Body')
        return installed
    finally:
        receipt['pointer_names_used'] = pointer_names(); receipt['UI_after'] = selection()
        errors = []
        for owner, field, value in ((setup, 'rig', original[0]), (setup, 'body', original[1]), (state, 'source', original[2])):
            try:
                setattr(owner, field, value)
            except Exception as exc:
                errors.append({'field': field, 'exception': repr(exc)})
        receipt['restoration_errors'] = errors
        receipt['restored_exact'] = (setup.rig, setup.body, state.source) == original
        need(not errors and receipt['restored_exact'], 'Private Setup/WM pointer restoration failed')


def exercise(bpy, args, base, cold, p, q, direct, plain, source, rig, body, report, write, budget):
    from character_designer import skirt_physics as physics, skirt_motion_tuning as tuning
    from character_designer import skirt_original_mode
    from mathutils import Quaternion, Vector

    context = bpy.context
    frame = [context.scene.frame_current, context.scene.frame_subframe]
    metres = context.scene.unit_settings.scale_length
    need(math.isfinite(metres) and metres > 0., 'Native scene metre scale is unknown')
    author = q.Protection()
    assets = base.author_asset_receipt(author)
    installed = public_install(bpy, direct, source, rig, body, report)
    tuning.apply(context, [source], mode='MANUAL')
    installed, actual_rig, _actual, cloth = physics.validate_physics(source)
    need(actual_rig == rig and not cloth.show_viewport and not cloth.show_render,
         'Actual Manual graph must pause Cloth; no Auto/replay path is exercised')
    direct.skirt._activate(context, rig, 'POSE')
    before_edit = base.native_mesh(source, context.evaluated_depsgraph_get())
    need('FINISHED' in bpy.ops.character_designer.body_original_mode('EXEC_DEFAULT', action='ORIGINAL'),
         'Public Original entry did not complete')
    deform = {n for chain in installed['chains'] for n in chain['def']}
    weighted = sorted({source.vertex_groups[w.group].name for v in source.data.vertices for w in v.groups
                       if w.weight > 0. and source.vertex_groups[w.group].name in deform})
    need(weighted, 'No actual weighted Original DEF input')
    bone = rig.pose.bones[weighted[0]]
    bone.rotation_mode = 'QUATERNION'
    bone.rotation_quaternion = Quaternion(bone.rotation_quaternion) @ Quaternion(Vector((1., 0., 0.)), .08)
    rig.update_tag(); context.view_layer.update()
    edited = base.native_mesh(source, context.evaluated_depsgraph_get())
    need('FINISHED' in bpy.ops.character_designer.body_original_mode('EXEC_DEFAULT', action='CONTROLS'),
         'Public Controls return did not complete')
    current = base.native_mesh(source, context.evaluated_depsgraph_get())
    report['actual_original_input'] = {'weighted_bone': bone.name, 'angle_rad': .08,
        'visible_change': base.geometry_pair(cold, before_edit, edited, metres),
        'return_error': base.geometry_pair(cold, edited, current, metres),
        'correction_saved': bool(source.get(skirt_original_mode.CORRECTIONS)), 'intentional_QA_pose_only': True}
    need(len(current['points']) == 3040 and report['actual_original_input']['visible_change']['maximum_m'] > base.LIMIT_M
         and report['actual_original_input']['return_error']['maximum_m'] <= base.LIMIT_M
         and report['actual_original_input']['correction_saved'] and author.verify()['success'],
         'Actual Original correction/input or original raw/Rest/Actions protection failed')
    baseline = base.authored_contract(bpy, p, q, direct, source, rig, body)
    receipt = plain.capture(source)
    proof = receipt['direct_proof']
    need(proof['state']['mode'] == 'MANUAL' and proof['state']['pending'] is True
         and proof['state']['editing'] is False and proof['mode_value'] is False
         and proof['cloth_flags'] == [False, False], 'Real finished Manual pendingTrue scope missing')
    report['captured_model_receipt'] = receipt
    report['born_mode'] = base.mode_contract(q, direct, source, installed)
    report['cache_scope_before'] = base.private_cache_scope(direct, source, installed)
    report['identity'] = identity = {'source': source.name, 'rig': rig.name, 'body': body.name,
        'owner': installed['owner'], 'scene': context.scene.name}
    plain.validate(source, receipt); write(); budget()

    snapshot = args.output/'cdesigner-unity-pns-qa'/'character.blend'
    snapshot.parent.mkdir()
    # Retain the proven home Scene and all original authored Objects/Actions,
    # including reverse Scene memberships and unused Action assets. This is a
    # private transport component, not the eventual FBX selection inventory.
    roots = set(bpy.data.scenes) | set(bpy.data.objects) | set(bpy.data.actions)
    bpy.data.libraries.write(str(snapshot), roots, path_remap='ABSOLUTE', fake_user=False, compress=True)
    need(snapshot.is_file() and snapshot.stat().st_size > 0
         and author.verify()['success'] and base.authored_contract(bpy, p, q, direct, source, rig, body) == baseline,
         'Private library write changed native author data or produced no snapshot')
    report['library_snapshot'] = {'path': str(snapshot), 'sha256': sha(snapshot), 'bytes': snapshot.stat().st_size,
        'scene_roots': sorted(o.name for o in bpy.data.scenes), 'artist_save_called': False}
    bpy.ops.wm.open_mainfile(filepath=str(snapshot), load_ui=False)
    source, rig, body, installed = base.installed_objects(bpy, direct, identity)
    need([bpy.context.scene.frame_current, bpy.context.scene.frame_subframe] == frame,
         'Private library transport changed the actual Scene frame/subframe')
    report['reopen_original_assets'] = base.author_assets_exact(q, assets)
    report['reopen_contract_exact'] = base.authored_contract(bpy, p, q, direct, source, rig, body) == baseline
    report['reopen_mode_exact'] = base.mode_contract(q, direct, source, installed) == report['born_mode']
    report['reopen_cache_scope'] = base.private_cache_scope(direct, source, installed)
    reopened = base.native_mesh(source, bpy.context.evaluated_depsgraph_get())
    report['reopen_visible_input'] = base.geometry_pair(cold, current, reopened, metres)
    plain.validate(source, receipt)
    prepared = plain.prepare(source, receipt)
    report['prepared_receipt_exact'] = digest(prepared) == digest(receipt)
    need(report['reopen_original_assets']['success'] and report['reopen_contract_exact'] and report['reopen_mode_exact']
         and report['reopen_cache_scope'] == report['cache_scope_before']
         and report['reopen_visible_input']['maximum_m'] <= base.LIMIT_M
         and report['prepared_receipt_exact'], 'Private model reopen proof failed')
    write(); budget()

    protected = q.Protection()
    names = [n for rows in proof['roles'].values() for n in rows]
    helpers = {n: (bpy.data.objects[n].as_pointer(), bpy.data.objects[n].data.as_pointer()) for n in names}
    oracle = oracle_data = None
    try:
        oracle = source.copy(); oracle_data = source.data.copy(); oracle.data = oracle_data
        for owner in (oracle, oracle_data):
            for key in list(owner.keys()): del owner[key]
        for modifier in list(oracle.modifiers):
            if modifier.name == proof['overlay']: oracle.modifiers.remove(modifier)
        need([m.type for m in oracle.modifiers] in (['ARMATURE'], ['ARMATURE', 'SUBSURF'])
             and oracle.modifiers[0].object == rig, 'Plain oracle must contain only original native skin/Subsurf')
        oracle.name = 'PNS plain skin comparison'; bpy.context.scene.collection.objects.link(oracle)
        oracle_before = base.native_mesh(oracle, bpy.context.evaluated_depsgraph_get())
        plain.validate(source, receipt)
        report['strip'] = plain.strip(source, prepared)
        graph = bpy.context.evaluated_depsgraph_get()
        stripped, oracle_after = base.native_mesh(source, graph), base.native_mesh(oracle, graph)
        report['stripped_vs_plain_oracle'] = base.geometry_pair(cold, oracle_after, stripped, metres)
        report['plain_oracle_not_changed_by_strip'] = base.geometry_pair(cold, oracle_before, oracle_after, metres)
        report['stripped_author_contract_exact'] = base.authored_contract(bpy, p, q, direct, source, rig, body) == baseline
        report['helpers_retained_exact'] = helpers == {
            n: (bpy.data.objects[n].as_pointer(), bpy.data.objects[n].data.as_pointer()) for n in names}
        report['only_owned_output_removed'] = bpy.data.node_groups.get(proof['node_group']) is None
        report['strip_raw_Rest_Actions_protection'] = protected.verify()
        write()
        need(len(stripped['points']) == 3040 and report['stripped_vs_plain_oracle']['maximum_m'] <= base.LIMIT_M
             and report['plain_oracle_not_changed_by_strip']['maximum_m'] == 0.
             and report['stripped_author_contract_exact'] and report['helpers_retained_exact']
             and report['only_owned_output_removed'] and report['strip_raw_Rest_Actions_protection']['success'],
             'Actual model PNS/3040/Body12/Raw/Rest/Actions/helpers proof failed')
    finally:
        if oracle is not None: bpy.data.objects.remove(oracle, do_unlink=True)
        if oracle_data is not None:
            need(oracle_data.users == 0, 'Private oracle acquired outside users')
            bpy.data.meshes.remove(oracle_data)
    need(protected.verify()['success'], 'Oracle cleanup changed protected author data')
    report['native_stages_completed'] = True


def pure_checks():
    base = load(BASE, BASE_SHA, 'pns_model_readers_pure')
    need(sha(HISTORY) == HISTORY_SHA, 'Historical file bytes changed')
    prior = json.loads(HISTORY.read_text(encoding='utf-8'))
    provenance = historical_provenance(prior)
    negative_count = 0
    for field, value in (('native_component_verified', False), ('native_stages_completed', None),
                         ('private_scene_disposed', 1), ('animation_verified', True)):
        wrong = json.loads(json.dumps(prior)); wrong[field] = value
        try:
            historical_provenance(wrong)
        except RuntimeError:
            negative_count += 1
        else:
            need(False, 'Historical false/unknown/typed/scope control was accepted: '+field)
    wrong = json.loads(json.dumps(prior)); wrong['source_after'] = {}
    try:
        historical_provenance(wrong)
    except RuntimeError:
        negative_count += 1
    else:
        need(False, 'Historical source mismatch was accepted')
    own = ast.parse(Path(__file__).read_text(encoding='utf-8'))
    calls = {n.func.attr for n in ast.walk(own) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    need(not calls & {'frame_set', 'save_as_mainfile', 'bake', 'free_bake', 'reset_simulation'}, 'Forbidden scope expansion')
    functions = {n.name: n for n in ast.parse((RUNTIME/'dress_plain_native_skin.py').read_text(encoding='utf-8')).body
                 if isinstance(n, ast.FunctionDef)}
    expected = {'capture': ['source'], 'validate': ['source', 'receipt'], 'prepare': ['source', 'receipt'], 'strip': ['source', 'receipt']}
    need(all([a.arg for a in functions[n].args.args] == params for n, params in expected.items()), 'PNS actual four-hook ABI changed')
    need(base.LIMIT_M == 5e-5, 'Original physical metre guard changed')
    public_entry_controls()
    need(digest({'pending': True}) != digest({'pending': 1})
         and digest({'pending': True}) != digest({'pending': False}), 'Receipt bool/int/state identity was lost')
    print(json.dumps({'pure_model_ABI': len(expected), 'historical_negative_controls': negative_count,
        'actual_public_entry_controls': 3,
        'history_provenance_only': provenance,
        'current_provider_and_PNS_postcase_native_pins': 'NotRun', 'native_run': False}))


def public_entry_controls():
    from types import SimpleNamespace
    from unittest.mock import patch

    for case in ('complete', 'poll_false', 'wrong_body'):
        rig, body, other = (SimpleNamespace(name=name) for name in ('Main', 'Body', 'Other'))
        source = type('Source', (dict,), {} )({'rig': rig, 'owner': 'owned'})
        source.name = 'Dress'
        setup, state = SimpleNamespace(rig=None, body=other), SimpleNamespace(source=None)
        context = SimpleNamespace(mode='POSE', selected_objects=[rig],
            view_layer=SimpleNamespace(objects=SimpleNamespace(active=rig)))
        calls = []
        record = {'source': 'Dress', 'rig': 'Main', 'owner': 'owned',
                  'physics': {'backend': 'DIRECT_MAIN_CLOTH_V1', 'surface': {'body': 'Body'}}}
        def activate(ctx, selected, mode):
            ctx.mode = mode; ctx.selected_objects = [selected]; ctx.view_layer.objects.active = selected
        class Operation:
            def poll(self):
                calls.append('poll'); return case != 'poll_false'
            def __call__(self, invocation, **kwargs):
                assert invocation == 'EXEC_DEFAULT' and kwargs == {'actual_surface': True}
                assert (setup.rig, setup.body, state.source) == (rig, body, source)
                calls.append('execute'); return {'FINISHED'}
        ui = SimpleNamespace(_settings=lambda ctx: state, _source=lambda ctx: ctx.view_layer.objects.active)
        package = SimpleNamespace(character_setup=SimpleNamespace(settings=lambda ctx: setup), skirt=ui)
        direct = SimpleNamespace(BACKEND='DIRECT_MAIN_CLOTH_V1',
            skirt=SimpleNamespace(RIG_KEY='rig', OWNER_KEY='owner', _activate=activate, read_record=lambda selected: record))
        bpy = SimpleNamespace(context=context, data=SimpleNamespace(objects={'Body': other if case == 'wrong_body' else body}),
            ops=SimpleNamespace(character_designer=SimpleNamespace(skirt_add_physics=Operation())))
        report = {}
        with patch.dict(sys.modules, {'character_designer': package}):
            try:
                actual = public_install(bpy, direct, source, rig, body, report)
            except RuntimeError:
                need(case != 'complete', 'Valid actual public callback rejected')
            else:
                need(case == 'complete' and actual is record, 'Invalid public callback admitted')
        need((setup.rig, setup.body, state.source) == (None, other, None)
             and report['public_install_entry']['restored_exact'], 'Callback failure leaked private registration')
        need(calls == (['poll'] if case == 'poll_false' else ['poll', 'execute']), 'Public callback was bypassed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--artist-protection', type=Path, required=True); parser.add_argument('--artist-protection-sha', required=True)
    parser.add_argument('--expected-source-manifest-sha', required=True)
    parser.add_argument('--body-object', required=True); parser.add_argument('--dress-object', required=True)
    parser.add_argument('--soft-seconds', type=float, default=180.)
    parser.add_argument('--pure-checks', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if args.pure_checks: pure_checks(); return 0
    need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE) and not args.output.exists(), 'Fresh X output required')
    need(args.artist_protection.is_absolute() and args.artist_protection.resolve().is_relative_to(HERE), 'Explicit V3 artist receipt required')
    need(0. < args.soft_seconds <= 240., 'Bounded component only')
    for value in (args.artist_protection_sha, args.expected_source_manifest_sha):
        need(len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'Full lowercase SHA required')
    base = load(BASE, BASE_SHA, 'pns_model_readers')
    cold = load(base.COLD, base.COLD_SHA, 'pns_model_cold_locator')
    p = load(cold.COMPARATOR, cold.COMPARATOR_SHA, 'pns_model_comparator')
    disk = load(p.DISK, p.DISK_SHA, 'pns_model_disk'); manifest = load(p.SOURCE, p.SOURCE_SHA, 'pns_model_manifest')
    pins = {Path(__file__).resolve(): sha(__file__), BASE: BASE_SHA, HISTORY: HISTORY_SHA,
        PREVIOUS: PREVIOUS_SHA,
        base.COLD: base.COLD_SHA, cold.COMPARATOR: cold.COMPARATOR_SHA, cold.LOCATOR: cold.LOCATOR_SHA,
        p.QA: p.QA_SHA, p.DISK: p.DISK_SHA, p.SOURCE: p.SOURCE_SHA,
        RUNTIME/'skirt_surface_direct.py': PROVIDER_SHA, RUNTIME/'skirt.py': SKIRT_SHA,
        RUNTIME/'dress_plain_native_skin.py': PLAIN_SHA, args.artist_protection: args.artist_protection_sha}
    need(all(sha(path) == value for path, value in pins.items()), 'Postcase source/helper/self/artist pins differ; do not start Native')
    before = manifest.current_manifest()
    need(digest(before) == args.expected_source_manifest_sha, 'Explicit current complete source manifest differs')
    import bpy
    need(bpy.app.background and bpy.app.version[:2] == (5, 2) and '--factory-startup' in sys.argv
         and '--disable-autoexec' in sys.argv and not bpy.data.filepath
         and Path(bpy.app.binary_path).resolve() == Path('D:/Blender5.2/blender.exe').resolve(), 'Empty protected factory5.2 only')
    args.output.mkdir(); started = time.perf_counter()
    report = {'stage': 'PRIVATE_MODEL_PNS_LIBRARY_REOPEN52', 'native_component_verified': False,
        'native_stages_completed': False, 'accepted': False, 'effect_accepted': False, 'ART_accepted': False,
        'FBX_verified': False, 'Unity_verified': False, 'animation_verified': False, 'export_accepted': False,
        'artist_saved': False, 'deployed': False, 'timeline_seek_by_QA': False,
        'Body_attachment_preserved': False, 'final_surface_equivalent': False, 'cache_payload_preserved': 'Unmeasured',
        'source_before': before, 'source_manifest_sha256': digest(before), 'errors': [],
        'runtime': {'version': list(bpy.app.version), 'binary': bpy.app.binary_path},
        'pins': {str(path): value for path, value in pins.items()}}
    def write():
        (args.output/'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    def budget(): need(time.perf_counter()-started < args.soft_seconds, 'Bounded model component incomplete')
    try:
        report['historical_provenance'] = historical_provenance(json.loads(HISTORY.read_text(encoding='utf-8')))
        report['artist_before'] = disk.proof(args.artist_protection, args.artist_protection_sha)
        locator = load(cold.LOCATOR, cold.LOCATOR_SHA, 'pns_model_locator'); q = p.readers(bpy)
        scene, rig, body, source, _record, choices = cold.load_artist(bpy, p, locator,
            Path(report['artist_before']['receipt']['artist_path']), args.body_object, args.dress_object)
        loaded, pose = q.Protection(), q.pose_channels(rig)
        sys.path.insert(0, str(REPOSITORY/'addons'))
        package = importlib.import_module('character_designer'); package.register()
        direct = importlib.import_module('character_designer.skirt_surface_direct')
        plain = importlib.import_module('character_designer.dress_plain_native_skin')
        need(Path(direct.__file__).resolve() == (RUNTIME/'skirt_surface_direct.py').resolve()
             and Path(plain.__file__).resolve() == (RUNTIME/'dress_plain_native_skin.py').resolve()
             and loaded.verify()['success'] and q.pose_channels(rig) == pose, 'Canonical registration changed loaded author content')
        report['explicit_selection'] = choices
        exercise(bpy, args, base, cold, p, q, direct, plain, source, rig, body, report, write, budget)
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
            need(report['source_files_Artist_exact'], 'Current source/helper/self/Artist bytes changed')
        except Exception as exc: report['errors'].append({'final_guard': repr(exc)})
        report['native_component_verified'] = report['native_stages_completed'] and not report['errors'] and report.get('private_scene_disposed') is True
        report['elapsed_seconds'] = time.perf_counter()-started; write()
    print(json.dumps({'native_component_verified': report['native_component_verified'], 'errors': report['errors'],
                      'report': str(args.output/'report.json'), 'export_accepted': False}))
    return 0 if report['native_component_verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
