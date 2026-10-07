"""Private single-variable air damping3->5 comparison against actual stop134.

Uses the public tuning service before the unchanged recipe and public Reset.
Original motion60, frozen input61..134, contacts/photos and author finalizers
are immutable. No production/default change; no settling/ART acceptance claim.
"""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ADAPTER = HERE/'verify_direct_cold_stop_settling_tail52_dependencies.py'
ADAPTER_SHA = 'f04d6d65e514bc1839fb3abff1d2bc4eea41f75c34636e80e9c877463faaabcf'
BASELINE = HERE/'actual_direct_cold_stop_tail_e0b_52_20261007_064740_348/result/report.json'
BASELINE_SHA = '5515a976f72ad6f5d43079432500ea1d6cc1af21efd387fcf915e0ce90d8d92c'
TUNING = Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/skirt_motion_tuning.py')
AUTHOR_FIELDS = ('raw_Dress','raw_Body','Rest','pose','pose_position','drivers','bindings','Body_Key_channels',
                'Body_Key_binding','Body_data_users','charts','frame','mode','active','selected','active_bone',
                'bone_selection','bone_collections','autokey_exact')


def need(value, message):
    if not value:
        raise RuntimeError('StopTailAir5_52: '+message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, ensure_ascii=False, separators=(',', ':'))


def load_adapter():
    need(sha(ADAPTER) == ADAPTER_SHA and sha(BASELINE) == BASELINE_SHA, 'Frozen adapter/actual baseline differs')
    spec = importlib.util.spec_from_file_location('air5_frozen_dependency_adapter', ADAPTER)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def baseline_proof(report, args, cold_path, cold_sha, expected_provider_sha):
    prior = json.loads(BASELINE.read_text(encoding='utf-8'))
    need(prior.get('native_motion_collection_completed') is True and prior.get('errors') == []
         and prior.get('private_scene_disposed') is True and prior.get('source_files_Artist_exact') is True
         and prior.get('accepted') is False and prior.get('case') == 'abrupt_stop_turn',
         'Actual completed baseline component required; effect remains unaccepted')
    restore = prior.get('author_restore', {})
    need(all(restore.get(name) is True for name in AUTHOR_FIELDS) and restore.get('errors') == []
         and restore.get('raw_Rest_Actions', {}).get('success') is True, 'Actual baseline author protection incomplete')
    tail = prior.get('settling_tail', {})
    need(tail.get('native_completed') is True and tail.get('pose_and_targets_complete') is True
         and tail.get('first_index') == 61 and tail.get('last_index') == 134
         and tail.get('contact_indices') == [74,104,134], 'Actual baseline tail134 proof incomplete')
    need(args.case == 'abrupt_stop_turn' and args.render is True, 'Only stop60/tail134 with the same terminal photos is allowed')
    need(prior.get('source_before') == report['source_before'] == prior.get('source_after')
         and prior.get('artist_after', {}).get('sha256') == args.artist_protection_sha,
         'Actual baseline full source/Artist fingerprint differs')
    cold = prior.get('cold_prerequisite', {})
    need(Path(cold.get('path', '')).resolve() == Path(cold_path).resolve()
         and cold.get('sha256') == cold_sha, 'Variant must use the same actual fresh Cold prerequisite')
    providers = [row for path,row in report['source_before'].items()
                 if Path(path).name == 'skirt_surface_direct.py']
    need(len(providers) == 1 and providers[0].get('sha256') == expected_provider_sha, 'Actual baseline provider differs')
    return {'path':str(BASELINE), 'sha256':BASELINE_SHA, 'actual_component_completed':True,
            'baseline_effect_accepted':False, 'baseline_air_damping':3.0,
            'scope':'Same actual full source, saved Artist, Cold, stop60 and frozen input61..134; no production change'}


def native_parameters(context, q, profiles, source, installed, cloth, colliders, clone):
    return json.loads(canonical({'profile':profiles.read(source,installed),
        'cloth_settings':q.simple_rna(cloth.settings), 'collision_settings':q.simple_rna(cloth.collision_settings),
        'effectors':q.simple_rna(cloth.settings.effector_weights), 'scene_gravity':list(context.scene.gravity),
        'scene_use_gravity':context.scene.use_gravity,
        'colliders':{obj.name:q.simple_rna(obj.collision) for obj in colliders+[clone]}}))


def air_change_proof(before, after):
    """Strict JSON comparison; exactly the two native/profile air fields differ."""
    need(type(before) is dict and type(after) is dict, 'Actual full native/profile receipts required')
    expected = copy.deepcopy(before)
    need(type(before['profile']['settings']['air_damping']) is float
         and type(before['cloth_settings']['air_damping']) is float
         and before['profile']['settings']['air_damping'] == before['cloth_settings']['air_damping'] == 3.,
         'Actual private cold baseline must have air damping3')
    need(before['profile']['settings']['quality'] == before['cloth_settings']['quality'] == 8
         and before['profile']['settings']['collision_quality'] == before['collision_settings']['collision_quality'] == 4
         and before['profile']['settings']['gravity'] == before['effectors']['gravity'] == 1.,
         'Original quality8/collision4/gravity1 required')
    expected['profile']['settings']['air_damping'] = 5.0
    expected['cloth_settings']['air_damping'] = 5.0
    passed = canonical(expected) == canonical(after)
    return {'passed':passed, 'allowed_changes':['profile.settings.air_damping','cloth_settings.air_damping'],
            'native_before':before['cloth_settings']['air_damping'],
            'native_after':after['cloth_settings'].get('air_damping'),
            'all_other_native_and_profile_parameters_exact':passed, 'accepted':False}


CHANGE = '''
        # Exactly one public material edit in this disposable owned installation.
        before_air = _AIR_NATIVE(context,q,profiles,source,installed,cloth,colliders,clone)
        prior_native = json.loads(_AIR_BASELINE.read_text(encoding='utf-8'))['native_defaults']
        prior_native.pop('default_parameters_accepted')
        report['air_damping_variant'] = {
            'scope':'Private air damping3->5 only; no default/production/ART/steady-state acceptance',
            'baseline':_AIR_BASELINE_PROOF(report,args,COLD_PROOF,COLD_PROOF_SHA,PROVIDER_SHA),
            'before':before_air, 'before_matches_actual_baseline':_AIR_CANONICAL(before_air)==_AIR_CANONICAL(prior_native),
            'public_apply_before_recipe_and_Reset':True, 'accepted':False}
        write()
        need(report['air_damping_variant']['before_matches_actual_baseline'], 'Actual full baseline native/profile defaults differ')
        tuning.apply(context, [source], {'air_damping': 5.0})
        installed, actual_rig, c, cloth = physics.validate_physics(source)
        need(actual_rig == rig, 'Public air tuning changed the Main Rig')
        profile = profiles.read(source,installed)
        after_air = _AIR_NATIVE(context,q,profiles,source,installed,cloth,colliders,clone)
        report['air_damping_variant']['after'] = after_air
        write()
        report['air_damping_variant']['proof'] = _AIR_PROOF(before_air,after_air)
        write()
        need(report['air_damping_variant']['proof']['passed'], 'Public tuning changed more than the single air damping field or failed readback')
'''


def prepared_namespace(expected_direct_sha, cold_path, cold_sha):
    adapter = load_adapter()
    namespace, base, run, main, replacements = adapter.prepared_namespace(expected_direct_sha,cold_path,cold_sha)
    original_run = run
    marker = "        # The one actual public cold install starts from saved controls only."
    need(run.count(marker) == 1, 'Unique pre-install baseline guard point missing')
    prefix = "        _AIR_BASELINE_PROOF(report,args,COLD_PROOF,COLD_PROOF_SHA,PROVIDER_SHA)\n"
    run = run.replace(marker,prefix+marker,1)
    marker = "        report['native_defaults'] = {"
    need(run.count(marker) == 1, 'Unique before-recipe native settings point missing')
    run = run.replace(marker,CHANGE+"        report['native_variant_parameters'] = {",1)
    old_pin = 'pins.update({_TAIL_BASE:_TAIL_BASE_SHA,_TAIL_STOP_REPORT:_TAIL_STOP_REPORT_SHA})'
    need(main.count(old_pin) == 1, 'Real compiled main pin ABI differs')
    main = main.replace(old_pin,old_pin+'; pins.update({_AIR_SELF:_AIR_SELF_SHA,_AIR_BASELINE:_AIR_BASELINE_SHA,_AIR_ADAPTER:_AIR_ADAPTER_SHA,_AIR_TAIL:_AIR_TAIL_SHA})',1)
    main = main.replace('CURRENT_ARTIST_CANONICAL_DIRECT_COLD_STOP_SETTLING_TAIL52','CURRENT_ARTIST_PRIVATE_DIRECT_STOP_TAIL_AIR5_52',1)
    namespace.update(__file__=str(Path(__file__).resolve()), _AIR_SELF=Path(__file__).resolve(),
        _AIR_SELF_SHA=sha(__file__), _AIR_BASELINE=BASELINE, _AIR_BASELINE_SHA=BASELINE_SHA,
        _AIR_ADAPTER=ADAPTER, _AIR_ADAPTER_SHA=ADAPTER_SHA,
        _AIR_TAIL=adapter.TAIL, _AIR_TAIL_SHA=adapter.TAIL_SHA,
        _AIR_BASELINE_PROOF=baseline_proof, _AIR_NATIVE=native_parameters,
        _AIR_PROOF=air_change_proof, _AIR_CANONICAL=canonical)
    exec(compile(run+'\n'+main,str(Path(__file__).resolve()),'exec'),namespace)
    return namespace,base,run,main,original_run,prefix


def pure_checks():
    prior = json.loads(BASELINE.read_text(encoding='utf-8'))
    provider_sha = next(row['sha256'] for path,row in prior['source_after'].items()
                        if Path(path).name == 'skirt_surface_direct.py')
    cold = prior['cold_prerequisite']
    namespace,base,run,main,original,prefix = prepared_namespace(provider_sha,Path(cold['path']),cold['sha256'])
    actual_cold = base.load('verify_direct_cold_install52_v4.py')
    spec = importlib.util.spec_from_file_location('air5_pure_actual_readers',actual_cold.COMPARATOR)
    readers = importlib.util.module_from_spec(spec); spec.loader.exec_module(readers)
    manifest = readers.load(readers.SOURCE,readers.SOURCE_SHA,'air5_pure_actual_manifest')
    disk = readers.load(readers.DISK,readers.DISK_SHA,'air5_pure_actual_disk')
    actual_source = manifest.current_manifest()
    actual_artist = disk.proof(Path(prior['artist_after']['path']),prior['artist_after']['sha256'])
    reverse = run.replace(prefix,'',1).replace(CHANGE,'',1).replace("report['native_variant_parameters'] = {","report['native_defaults'] = {",1)
    need(reverse == original, 'Unexpected motion/physics/Reset/contacts/finally changes')
    need(namespace['main'].__globals__ is namespace and namespace['run_motion'].__globals__ is namespace
         and namespace['restore_body_coordinates'] is base.restore_body_coordinates, 'Compiled globals/Body12 finalizer identity differs')
    tree = ast.parse(TUNING.read_text(encoding='utf-8'))
    apply = next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name == 'apply')
    need([a.arg for a in apply.args.args] == ['context','sources','changes']
         and [a.arg for a in apply.args.kwonlyargs] == ['mode'], 'Actual public tuning.apply ABI differs')
    before = copy.deepcopy(prior['native_defaults']); before.pop('default_parameters_accepted')
    after = copy.deepcopy(before); after['profile']['settings']['air_damping']=5.; after['cloth_settings']['air_damping']=5.
    need(air_change_proof(before,after)['passed'], 'Actual single-air-field positive rejected')
    negatives = [('cloth_settings','air_damping',4.),('profile.settings','air_damping',3.),
        ('cloth_settings','quality',4),('collision_settings','collision_quality',2),('effectors','gravity',.5),
        ('cloth_settings','mass',.2),('cloth_settings','quality',8.),('profile','mode','MANUAL')]
    for section,key,value in negatives:
        wrong = copy.deepcopy(after); target = wrong
        for part in section.split('.'): target = target[part]
        target[key]=value
        need(not air_change_proof(before,wrong)['passed'], 'A second changed native/profile field was accepted')
    from types import SimpleNamespace
    args = SimpleNamespace(case='abrupt_stop_turn',render=True,artist_protection_sha=prior['artist_after']['sha256'])
    need(actual_artist['sha256'] == args.artist_protection_sha
         and baseline_proof({'source_before':actual_source},args,Path(cold['path']),cold['sha256'],provider_sha)['actual_component_completed'],
         'Actual baseline full terminal gates differ')
    for invalid in [SimpleNamespace(case='walk',render=True,artist_protection_sha=args.artist_protection_sha),
                    SimpleNamespace(case=args.case,render=False,artist_protection_sha=args.artist_protection_sha)]:
        try: baseline_proof({'source_before':prior['source_before']},invalid,Path(cold['path']),cold['sha256'],provider_sha)
        except RuntimeError: pass
        else: need(False, 'Different case/missing matching terminal photos admitted')
    print(json.dumps({'source_prepared':True,'native_executed':False,'only_public_air3_to5_edit':True,
        'actual_parameter_negative_controls':len(negatives),'baseline_case_photo_negatives':2,
        'motion_tail_and_finally_reverse_exact':True,'compiled_globals_and_Body12_restore_identity':True,
        'baseline_report_sha256':BASELINE_SHA,'effect_or_settling_accepted':False}))


def main():
    adapter = load_adapter()
    dependencies,delegated = adapter.dependency_arguments(sys.argv)
    namespace,base,run,main_source,original,prefix = prepared_namespace(*dependencies)
    cold_path, cold_sha = dependencies[1:]
    need(cold_path.is_file() and sha(cold_path) == cold_sha, 'Specified actual fresh Cold report differs')
    pins = {Path(__file__).resolve():sha(__file__),ADAPTER:ADAPTER_SHA,BASELINE:BASELINE_SHA,
            adapter.TAIL:adapter.TAIL_SHA,cold_path:cold_sha}
    original_argv = sys.argv
    try:
        sys.argv = delegated
        return namespace['main']()
    finally:
        sys.argv = original_argv
        need(all(sha(path) == value for path,value in pins.items()), 'Air variant/frozen baseline/dependencies changed')


if __name__ == '__main__':
    if '--pure-checks' in sys.argv:
        pure_checks()
    else:
        raise SystemExit(main())
