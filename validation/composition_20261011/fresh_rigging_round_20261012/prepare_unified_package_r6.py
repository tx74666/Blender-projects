"""Prepare an explicit R6 Source successor; no work runs when imported.

The sole R5 shipped delta is the reviewed Rigging editing-data translation
domain fix. --inspect-only reads and validates Source without writing artifacts.
Capture/build needs a separate Parent instruction. This Source does not grant
native, SDK, deployment, installation, artist editing or publishing permission.
The final destination remains the existing X.blend/Rig; fresh scenes are tests.
"""
import argparse
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
ROUND = Path(__file__).resolve().parent
ROOT = ROUND.parent
OLD_PACKAGE = ROUND / 'package_3dbbdce3'
OLD_FREEZE = ROOT / 'x_rigging_source_freeze_r5_c5f2aa05.json'
OLD_FREEZE_SHA = '8f8333f085c1a370befc6f2bdfdb1f96a946c03c4fbf7a46e358a75f9ebc327b'
OLD_MANIFEST_SHA = 'd966326fda04aa9fa96f720470b5689566de73eef01c510886f8abb8051676e9'
OLD_ZIP_SHA = '70a6121c5c0d949c9f75b62937766aae97f55918c7618c554ed40eba8f295ffc'
OLD_RECEIPT_SHA = '8b290c2616f4781fe6bb16b338addc9a0e1e4b92021b0e661f53ae2e0b1b3c9f'
OLD_READBACK_SHA = '6b87680c0891a2d127de9aecf55df3063b169dfe3ba828b8dddd0c401894bde5'
OLD_MAP_SHA = '3dbbdce3e71a5e1e6d77a81d1be9338a37c4530128b7442e6fa4e48551ba5464'
OLD_WORKLIST_SHA = 'bcddead36b21313b9a7991c6c1da784b582a29380cc8ed0c184b941b7e284c53'
INIT_SHA = 'd66a88023e93c3db64f1b64cfaf8089d4c956adc0f97896c591e34a54d8e4dd2'
NATIVE_SHA = 'c5f2aa055c43d97afbe057498041e5a01d59002ebb99c271f1438f5d03a150ea'
WORKLIST_SHA = '80af33958b6326b59f5c2864a560f94e1c24a2b6d3e38f34117b2d75357689f6'
WORKLIST_TEST = 'test_animation_worklist_rigging_editing_data.py'
WORKLIST_TEST_SHA = 'f53bcee59ca3845a0567e414cd024b010d18ba10996777d86e1103033de26f68'
OWNER_PATH = ROUND / 'worklist_rigging_editing_data_source_owner_80af3395.json'
OWNER_SHA = '8e8796ebcf9943225dc05b4f6a9471441da2ecff02ea3f90370f38161f4bce4d'
PEER_PATH = ROUND / 'worklist_rigging_editing_data_source_peer_80af3395.json'
PEER_SHA = '47549e3aab444ffd3832566326fd1179c3615097071872200e5356d16e5ae77c'
FAILURE_PATH = ROUND / 'native_c5_control_01/new_official_cosha_report.json'
FAILURE_SHA = '46aae9142e5c7cd1bfbdc04315386aaa3ef4ffc442949866e7542840ab18a37a'
CLOSURE_PATH = ROUND / 'resource_release_X_COSHA_CONTROLS_R5_202610112351Z.json'
CLOSURE_SHA = '15926680c930f98dc45cce5191bc1c92bfa39fb817d204a1d9bbed232da24ea0'
ARCHIVED_DIST = REPO / 'dist/archived_candidates/character_designer-0.77.25-source-3dbbdce3-70a6121c.zip'
sys.path.insert(0, str(REPO / 'tools'))
from release_projection import load_source


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')


def record(path, expected=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    require(expected is None or re.fullmatch('[0-9a-fA-F]{64}', expected)
            and sha(raw) == expected.lower(), 'Changed Source pin: ' + str(path))
    return {'path': str(path), 'sha256': sha(raw), 'bytes': len(raw)}


def exact(row):
    require(set(row) == {'path', 'sha256', 'bytes'} and record(row['path'], row['sha256']) == row,
            'An exact three-field Source pin changed.')
    return row


def file_map(source):
    return {path.as_posix(): sha(raw) for path, raw in sorted(source.files.items())}


def map_sha(files):
    return sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def function_ast(raw, name):
    nodes = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name == name]
    require(len(nodes) == 1, 'The required native function is missing or ambiguous: ' + name)
    return ast.dump(nodes[0], include_attributes=False)


def admitted_cli(path, digest, fixed_path, fixed_digest):
    require(Path(path).resolve() == fixed_path.resolve() and digest.lower() == fixed_digest,
            'An explicit CLI pin differs from the reviewed R6 scope: ' + str(fixed_path))
    return record(path, digest)


def archive_matches(archive, source):
    payload = {'character_designer/' + path.as_posix(): raw for path, raw in source.files.items()}
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        require(zipped.testzip() is None and len(entries) == 188
                and len({entry.filename for entry in entries}) == 188
                and not any(entry.is_dir() for entry in entries), 'ZIP CRC/duplicate/full-entry check failed.')
        require({entry.filename: zipped.read(entry) for entry in entries} == payload,
                'Every ZIP byte must equal the manifest.')


def inputs(args):
    require(args.worklist_sha256.lower() == WORKLIST_SHA
            and args.worklist_test_sha256.lower() == WORKLIST_TEST_SHA,
            'The R6 runtime/test SHA must be supplied explicitly and match the reviewed fix.')
    provenance = {
        'previous_source_freeze': record(OLD_FREEZE, OLD_FREEZE_SHA),
        'previous_manifest': record(OLD_PACKAGE / 'python_projection.json', OLD_MANIFEST_SHA),
        'previous_frozen_archive': record(OLD_PACKAGE / 'character_designer-0.77.25.zip', OLD_ZIP_SHA),
        'previous_completed_package_receipt': record(OLD_PACKAGE / 'unified_package_receipt.json', OLD_RECEIPT_SHA),
        'previous_postbuild_readback': record(OLD_PACKAGE / 'postbuild_readback.json', OLD_READBACK_SHA),
        'previous_producer': record(ROUND / 'prepare_unified_package_r5.py',
            '6ccea8124d6c374073439e1ed48b7184c17899cef2f7c1c1fb3d7b14f0bce3d8'),
        'producer': record(__file__),
        'official_resolver': record(REPO / 'tools/release_projection.py',
            '052e6c765c95ba46d480bf1eeca1e1dccb7685c77a4e756202ce409d20713106'),
        'official_builder': record(REPO / 'tools/build_releases.py',
            '30759e923bde1da595f5cd9f67dd9d6f866ebb2866eb4c5f5b1747628e2872c1'),
        'worklist_owner': admitted_cli(args.worklist_owner, args.worklist_owner_sha256, OWNER_PATH, OWNER_SHA),
        'worklist_peer': admitted_cli(args.worklist_peer, args.worklist_peer_sha256, PEER_PATH, PEER_SHA),
        'failed_R5_native_report': admitted_cli(args.failure_report, args.failure_report_sha256, FAILURE_PATH, FAILURE_SHA),
        'failed_R5_native_closure': admitted_cli(args.closure_receipt, args.closure_receipt_sha256, CLOSURE_PATH, CLOSURE_SHA),
    }
    old = json.loads(OLD_FREEZE.read_bytes())
    previous_receipt = json.loads((OLD_PACKAGE / 'unified_package_receipt.json').read_bytes())
    previous_readback = json.loads((OLD_PACKAGE / 'postbuild_readback.json').read_bytes())
    require(old['schema'] == 'cdesigner.x-rigging-source-freeze/1'
            and old['source_only'] is True and old['native_execution_performed'] is False
            and len(old['source_pins']) == 19 and old['pure_tests_total'] == 262
            and sum(row['tests'] for row in old['pure_tests']) == 262,
            'R5 nineteen-source/262-unique-test ancestry changed.')
    require(previous_receipt['schema'] == 'cdesigner.unified-source-candidate/1'
            and previous_receipt['source_only'] is True and previous_receipt['native_acceptance'] is False
            and previous_receipt['source_pin_count'] == 19 and previous_receipt['file_count'] == 188
            and previous_receipt['syntax_python_files'] == 156 and previous_receipt['unique_pure_tests'] == 262
            and previous_receipt['complete_file_map_sha256'] == OLD_MAP_SHA
            and previous_readback['schema'] == 'x.validation.unified-r5-postbuild-readback/1'
            and previous_readback['passed'] is True and previous_readback['ZIP_entries'] == 188
            and previous_readback['duplicates'] == 0 and previous_readback['testzip'] == 'PASS'
            and previous_readback['all_entry_bytes_equal_manifest'] is True,
            'The completed R5 Source package evidence must remain exact and native-pending.')
    for name in ('source_freeze', 'manifest'):
        expected = provenance['previous_source_freeze' if name == 'source_freeze' else 'previous_manifest']
        require(exact(previous_receipt[name]) == expected and exact(previous_readback[name]) == expected,
                'R5 receipt/readback ancestry differs: ' + name)
    require(exact(previous_receipt['archive']['frozen_copy']) == provenance['previous_frozen_archive']
            and exact(previous_readback['zip_frozen_copy']) == provenance['previous_frozen_archive']
            and exact(previous_readback['actual_completed_file_receipt']) == provenance['previous_completed_package_receipt'],
            'R5 frozen ZIP or completed receipt binding changed.')
    exact(previous_receipt['official_build']['log'])
    for name, row in old['r5_source_provenance'].items():
        exact(row)
    for row in old['pure_tests']:
        exact(row['provenance'])
    reference_pin = exact(old['r5_source_provenance']['reference_owner'])
    recovery_pin = exact(old['r5_source_provenance']['current_native_recovery'])
    reference = json.loads(Path(reference_pin['path']).read_bytes())
    recovery = json.loads(Path(recovery_pin['path']).read_bytes())
    require(reference_pin['sha256'] == '8c632d2fc1d1f603ff955aff6b9ed1e8a57fdad44462d2e1878a7ded2afd7506'
            and recovery_pin['sha256'] == 'c426850bd7c1458c5bc5051ddf10f16390949ea0cdfc24dfebab362110e055ea'
            and reference['test_result']['total'] == reference['test_result']['passed'] == 20
            and reference['test_result']['new_added'] == 20 and reference['test_result']['failed'] == 0
            and recovery['passed'] is True and recovery['test_result']['total'] == 12
            and recovery['test_result']['exit_code'] == 0 and recovery['test_result']['actual_run'] == 1,
            'R5 reference20/current-native recovery12 exact evidence changed; neither is rerun here.')
    exact(reference['test_result']['log_pin'])
    exact(recovery['test_result']['log_pin'])
    provenance['historical_reference_owner'] = reference_pin
    provenance['historical_current_native_recovery'] = recovery_pin
    owner = json.loads(OWNER_PATH.read_bytes())
    peer = json.loads(PEER_PATH.read_bytes())
    for doc, schema in ((owner, 'x.validation.worklist-rigging-editing-data-source-owner/1'),
                       (peer, 'x.validation.worklist-rigging-editing-data-source-peer/1')):
        require(doc['schema'] == schema and doc['passed'] is True
                and doc['source_only'] is True and doc['native_execution_performed'] is False
                and doc['changed_runtime_functions'] == ['_editing_data', 'add']
                and doc['unchanged_existing_functions'] == 32
                and doc['unchanged_function_text_and_AST'] is True
                and doc['full_raw_inverse_equal'] is True and doc['top_level_AST_unchanged'] is True,
                'The owner/independent peer must close exactly the minimal reviewed Source delta.')
    require(exact(peer['owner_source_report']) == provenance['worklist_owner'],
            'Independent peer does not bind the exact owner receipt.')
    new_result = owner['test_results']['new_pure']
    ordinary_result = owner['test_results']['ordinary_regression']
    require(new_result['total'] == new_result['passed'] == 7 and new_result['failed'] == 0
            and new_result['exit_code'] == 0 and ordinary_result['total'] == ordinary_result['passed'] == 15
            and ordinary_result['failed'] == 0 and ordinary_result['exit_code'] == 0
            and ordinary_result['unique_new_cases'] == 0
            and peer['owner_test_attribution']['new_pure_reported_passes'] == 7
            and peer['owner_test_attribution']['ordinary_reported_passes'] == 15
            and peer['owner_test_attribution']['reviewer_test_executions'] == 0,
            'Seven new pure PASS and fifteen existing regressions are required, without duplicate counting.')
    for name, result in (('worklist_new_pure_log', new_result), ('worklist_ordinary_regression_log', ordinary_result)):
        provenance[name] = exact(result['raw_log'])
    require(exact(peer['owner_test_attribution']['new_pure_log']) == provenance['worklist_new_pure_log']
            and exact(peer['owner_test_attribution']['ordinary_log']) == provenance['worklist_ordinary_regression_log'],
            'Independent peer/owner test-log pins differ.')
    provenance['worklist_first_attempt_log'] = exact(owner['test_results']['first_attempt']['raw_log'])
    provenance['historical_worklist_snapshot'] = exact(owner['prior_source_snapshot'])
    require(provenance['historical_worklist_snapshot']['sha256'] == OLD_WORKLIST_SHA
            and exact(peer['prior_source_snapshot']) == provenance['historical_worklist_snapshot'],
            'The original bcd editing-data Source snapshot must remain historical and exact.')
    failure = json.loads(FAILURE_PATH.read_bytes())
    closure = json.loads(CLOSURE_PATH.read_bytes())
    require(failure['schema'] == 'x.validation.new-official-cosha-control-save/1'
            and failure['completed'] is False and failure['phase'] == 'failed_no_retry_or_publication'
            and failure['failure_phase'] == 'add_activate' and failure['native_execution_performed'] is True
            and failure['worker_performed'] is False and failure['Sync_performed'] is False
            and failure['original_Rig_acceptance'] is False
            and 'roll-decoupled hierarchy was edited' in failure['error'] and bool(failure['traceback']),
            'The actual failed R5 Add and full traceback must remain a failure, never relabelled as PASS.')
    require(closure['schema'] == 'x.validation.failed-native-closure-and-resource-release/1'
            and closure['status'] == 'ACTUAL_RELEASE' and closure['actual_native_result'] == 'FAIL'
            and closure['failure_phase'] == 'add_activate' and closure['no_retry_or_publication'] is True
            and closure['retained_handle_natural_exit'] is True and closure['native_exit_code'] == 0
            and closure['owned_pid'] == 55952 and closure['owned_native_gone'] is True
            and closure['process_termination_performed'] is False
            and all(closure[name] == 0 for name in ('worker_calls', 'SDK_calls', 'artist_writes', 'deployments')),
            'An exact actual natural-exit/failure-snapshot closure is mandatory; no resource reservation is inferred.')
    require(exact(closure['control_report']) == provenance['failed_R5_native_report'],
            'The release does not bind the actual R5 failure.')
    provenance['failed_R5_launcher_receipt'] = exact(closure['launch_receipt'])
    require(provenance['failed_R5_launcher_receipt']['sha256'] ==
            '6dc3e895e3e31eaa294c66603deb5e18db27f5e6a25761e37b396e7199ec48d7',
            'The retained-handle launcher receipt changed.')
    snapshot = {key: closure['failure_snapshot'][key] for key in ('path', 'sha256', 'bytes')}
    provenance['failed_R5_saved_scene'] = exact(snapshot)
    require(closure['failure_snapshot']['Blender_saved_notification_observed'] is True,
            'The task-owned failure Scene must have been saved with Blender success observed.')
    launcher = json.loads(Path(provenance['failed_R5_launcher_receipt']['path']).read_bytes())
    require(launcher['completed'] is False and launcher['natural_exit_verified'] is True
            and launcher['child_pid'] == 55952 and launcher['exit_code'] == 0
            and launcher['all_owned_Blender_processes_gone'] is True
            and launcher['artist_opened_or_saved'] is False and launcher['process_termination_performed'] is False
            and exact(launcher['control_report']) == provenance['failed_R5_native_report']
            and launcher['protected_files_after'] == {name: launcher['inputs'][name]
                for name in ('protected_artist', 'protected_workspace')}
            and launcher['artist_process_after'] == launcher['artist_process_before'],
            'R5 natural closure/original-file/process protection evidence is incomplete.')
    for name in ('stdout', 'stderr'):
        provenance['failed_R5_launcher_' + name] = exact(launcher[name])
    paths = {Path(row['path']).name: (Path(row['path']), row) for row in old['source_pins']}
    require(len(paths) == 19 and WORKLIST_TEST not in paths
            and paths['animation_worklist.py'][1]['sha256'] == OLD_WORKLIST_SHA,
            'Expected precisely nineteen R5 Source pins with historical bcd worklist.')
    paths[WORKLIST_TEST] = (REPO / 'tests' / WORKLIST_TEST, None)
    expected = {'animation_worklist.py': (WORKLIST_SHA, 41107), WORKLIST_TEST: (WORKLIST_TEST_SHA, 14112)}
    updated = []
    for name, (path, prior) in sorted(paths.items()):
        row = record(path)
        digest, size = expected.get(name, (prior['sha256'], prior['bytes']) if prior else ('', None))
        require(row['sha256'] == digest and row['bytes'] == size, 'Unauthorized Source delta: ' + name)
        compile(ast.parse(path.read_bytes(), filename=str(path)), str(path), 'exec')
        updated.append({**row, 'syntax': 'PASS'})
    by_name = {Path(row['path']).name: {key: row[key] for key in ('path', 'sha256', 'bytes')} for row in updated}
    require(len(updated) == 20 and by_name['unity_animation_rigging.py']['sha256'] == NATIVE_SHA,
            'Native c5 must remain exact; expected twenty Source pins (init is bound by the complete shipped map).')
    for doc in (owner, peer):
        require(set(doc['source_files']) == set(expected), 'Worklist receipt must bind exactly its runtime and new test.')
        for name, row in doc['source_files'].items():
            require(exact(row) == by_name[name], 'Owner/peer/current source pin differs: ' + name)
    for name, row in owner['held_source_and_R5_artifacts'].items():
        exact(row)
    for name, row in peer['read_only_dependency_pins'].items():
        exact(row)
    for doc in (reference, recovery):
        for name, row in doc['source_files'].items():
            require(exact(row) == by_name[name], 'Historical unchanged c5 pure evidence/current Source differs: ' + name)
    old_source = load_source('character_designer', OLD_PACKAGE / 'python_projection.json', root=REPO)
    captured = load_source('character_designer', root=REPO)
    old_hashes, hashes = file_map(old_source), file_map(captured)
    require(map_sha(old_hashes) == OLD_MAP_SHA and old_source.version == captured.version == '0.77.25'
            and len(hashes) == len(old_hashes) == 188 and set(hashes) == set(old_hashes)
            and hashes['__init__.py'] == INIT_SHA and hashes['unity_animation_rigging.py'] == NATIVE_SHA,
            'Full shipped set/version/native/init differs from the approved scope.')
    require({name for name in old_hashes if hashes[name] != old_hashes[name]} == {'animation_worklist.py'}
            and old_hashes['animation_worklist.py'] == OLD_WORKLIST_SHA
            and hashes['animation_worklist.py'] == WORKLIST_SHA,
            'The sole shipped R5 delta must be the reviewed worklist; all other 187 payloads remain exact.')
    archive_matches(OLD_PACKAGE / 'character_designer-0.77.25.zip', old_source)
    prior_native = OLD_PACKAGE / 'source/character_designer/unity_animation_rigging.py'
    provenance['historical_c5_native_source'] = record(prior_native, NATIVE_SHA)
    for name in ('_apply', '_binding_plan'):
        require(function_ast(prior_native.read_bytes(), name) == function_ast(
            Path(by_name['unity_animation_rigging.py']['path']).read_bytes(), name),
            'The exact native preview algorithm must remain unchanged: ' + name)
    py_count = 0
    for path, raw in captured.files.items():
        if path.suffix == '.py':
            compile(ast.parse(raw, filename=path.as_posix()), path.as_posix(), 'exec')
            py_count += 1
    require(py_count == 156, 'Expected the complete 156-Python candidate.')
    return {'old': old, 'updated': updated, 'captured': captured, 'hashes': hashes,
        'python_count': py_count, 'provenance': provenance, 'owner': owner, 'peer': peer,
        'unique_tests': 262 + 7, 'failure': failure, 'closure': closure}


def targets(state, args):
    package = ROUND / ('package_' + map_sha(state['hashes'])[:8])
    freeze = ROOT / ('x_rigging_source_freeze_r6_' + args.worklist_sha256.lower()[:8] + '.json')
    return package, freeze, package / 'source/character_designer', package / 'python_projection.json'


def write_new(path, raw, freeze):
    path = path.resolve()
    require(path == freeze.resolve() or path.is_relative_to(ROUND), 'New artifact leaves its owned Source scope.')
    require(not path.exists(), 'Refuse overwriting immutable Source evidence: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def capture(state, args):
    package, freeze, source_root, manifest_path = targets(state, args)
    require(not package.exists() and not freeze.exists(), 'Use unique new R6 outputs.')
    frozen = deepcopy(state['old'])
    frozen.update(created_utc=datetime.now(timezone.utc).isoformat(), source_only=True,
        native_execution_performed=False, source_pins=state['updated'],
        pure_tests_total=state['unique_tests'], previous_source_freeze=state['provenance']['previous_source_freeze'],
        r6_source_provenance=state['provenance'], source_delta={
            'prior_pins_changed': ['animation_worklist.py'], 'prior_pins_unchanged': 18,
            'added_pins': [WORKLIST_TEST], 'source_pin_count': 20,
            'runtime_replaced': ['animation_worklist.py'], 'runtime_added': [],
            'other_187_payload_files_unchanged': True},
        syntax_compilation={'source_files': 20, 'python_payload_files': 156,
            'result': 'PASS', 'target_imports': 0},
        source_pure_test_attribution={'historical_unique_tests_before': 262,
            'new_unique_pure_tests': 7, 'historical_unique_tests_after': 269,
            'tests_executed_by_this_producer': 0, 'all_269_run_against_current_candidate': False,
            'new7_owner': state['provenance']['worklist_owner'],
            'ordinary15_regression_log': state['provenance']['worklist_ordinary_regression_log'],
            'ordinary15_unique_additions': 0, 'unchanged_reference20': state['provenance']['historical_reference_owner'],
            'unchanged_recovery12': state['provenance']['historical_current_native_recovery']},
        actual_R5_native_failure={'result': 'FAIL', 'phase': 'add_activate',
            'report': state['provenance']['failed_R5_native_report'],
            'closure': state['provenance']['failed_R5_native_closure'],
            'saved_failure_scene': state['provenance']['failed_R5_saved_scene'],
            'native_success_inferred_from_source_fix': False},
        final_destination='Existing original X.blend Scene/Rig preserving modifiers, design, colors, groups and controllers; fresh scenes are isolated tests.',
        rigging_editing_data_fix={'owner': state['provenance']['worklist_owner'],
            'independent_peer': state['provenance']['worklist_peer'],
            'strict_translation_domain': 'mapping.controls.mapped_names - mapping.controls.delegated_names',
            'generated_control_hierarchy_Rest_inheritance_preserved': True,
            'ordinary_omitted_keyword_behavior_unchanged': True,
            'inventory_mapping_swap_guards_unchanged': True,
            'original_X_acceptance': False})
    for row in frozen['pure_tests']:
        row.update(executions_by_this_producer=0)
        row['r6_evidence_scope'] = 'Carried exact historical receipt and unchanged test Source; not rerun by this producer.'
        if row['file'] == 'test_animation_worklist.py':
            row.update(provenance=state['provenance']['worklist_owner'],
                historical_R5_provenance=deepcopy(next(prior['provenance'] for prior in state['old']['pure_tests']
                    if prior['file'] == row['file'])),
                r6_evidence_scope='Actual owner fifteen existing regressions PASS against 80af; no additional unique cases and no execution by this producer.')
    frozen['pure_tests'].append({'file': WORKLIST_TEST, 'tests': 7, 'result': 'PASS', 'native': False,
        'provenance': state['provenance']['worklist_owner'], 'executions_by_this_producer': 0,
        'evidence_scope': 'Actual owner seven new AST/fake-RNA pure cases PASS; not native solver, model or publication proof.'})
    require(sum(row['tests'] for row in frozen['pure_tests']) == state['unique_tests'], 'Unique test arithmetic changed.')
    frozen['limitations'] += [
        'R6 replaces only animation_worklist.py relative to the immutable R5 188-file package at unchanged 0.77.25.',
        '269 is cumulative unique pure evidence, including 262 historical cases and seven new owner cases; this producer runs zero tests and does not claim all 269 ran against R6.',
        'R5 actual Add failed before editing/Undo/reopen/reference/Sync; its report, traceback, saved Scene and natural-exit closure are retained unchanged.',
        'Source/pure fix and factory tests do not establish acceptance of the existing original X.blend/Rig.',
        'Existing artist modifiers/design/materials/colors/Bone Collections/custom shapes/controllers must remain preserved in final integration; no Rest/weights/structure repair is admitted.',
        'The recorded R5 release is historical closure, not a new resource window, launch authorization, install or deployment.']
    require(file_map(load_source('character_designer', root=REPO)) == state['hashes'], 'Canonical drift before capture.')
    for row in state['updated']:
        exact({key: row[key] for key in ('path', 'sha256', 'bytes')})
    for row in state['provenance'].values():
        exact(row)
    write_new(freeze, encoded(frozen), freeze)
    package.mkdir()
    for path, raw in state['captured'].files.items():
        write_new(source_root / path, raw, freeze)
    manifest = {'schema_version': 1, 'module': 'character_designer', 'version': '0.77.25',
        'source_root': str(source_root), 'files': state['hashes'], 'source_provenance': {
            'purpose': 'Source-only Rigging editing-data translation-domain successor; native and original-X acceptance pending',
            'source_freeze': record(freeze), 'previous_candidate': state['provenance']['previous_manifest'],
            'complete_file_map_sha256': map_sha(state['hashes']), 'producer': state['provenance']['producer'],
            'local_source_no_bump': True, 'native_acceptance': False, 'deployment_authorized': False,
            'failed_R5_native_report': state['provenance']['failed_R5_native_report'],
            'failed_R5_native_closure': state['provenance']['failed_R5_native_closure'],
            'final_destination_existing_X_Rig': True}}
    write_new(manifest_path, encoded(manifest), freeze)
    require(load_source('character_designer', manifest_path, root=REPO).files == state['captured'].files,
            'Frozen complete payload differs from the captured bytes.')
    print(json.dumps({'freeze': record(freeze), 'manifest': record(manifest_path),
        'file_map_sha256': map_sha(state['hashes']), 'files': 188, 'python_files': 156,
        'unique_pure_tests': state['unique_tests'], 'tests_executed_by_this_producer': 0,
        'all_269_run_against_current_candidate': False, 'native_acceptance': False}))


def build_and_verify(state, args):
    package, freeze, source_root, manifest_path = targets(state, args)
    manifest = json.loads(manifest_path.read_bytes())
    require(exact(manifest['source_provenance']['source_freeze']) == record(freeze)
            and exact(manifest['source_provenance']['producer']) == state['provenance']['producer'],
            'The entire frozen receipt or producing Source changed after capture.')
    frozen = json.loads(freeze.read_bytes())
    require(frozen['source_pins'] == state['updated'] and frozen['pure_tests_total'] == state['unique_tests']
            and frozen['r6_source_provenance'] == state['provenance'], 'The admitted R6 Source receipt changed.')
    require(load_source('character_designer', manifest_path, root=REPO).files == state['captured'].files,
            'Canonical/frozen bytes changed before the official build.')
    archive_literal = REPO / 'dist/character_designer-0.77.25.zip'
    dist_literal = REPO / 'dist'
    archive = archive_literal.resolve()
    archived = ARCHIVED_DIST.resolve()
    dist = dist_literal.resolve()
    require(archive.is_relative_to(dist) and archived.is_relative_to(dist)
            and dist.is_relative_to(REPO.resolve())
            and not any(path.is_symlink() or getattr(path, 'is_junction', lambda: False)()
                for path in (archive_literal, dist_literal, ARCHIVED_DIST.parent))
            and not archived.exists(), 'Resolved move targets must remain in dist without overwrite/reparse.')
    prior_dist = record(archive, OLD_ZIP_SHA)
    require(archive.read_bytes() == (OLD_PACKAGE / archive.name).read_bytes(), 'R5 dist/frozen ZIP bytes differ.')
    archived.parent.mkdir(parents=True, exist_ok=True)
    archive.rename(archived)
    require(not archive.exists() and record(archived, OLD_ZIP_SHA)['bytes'] == prior_dist['bytes'],
            'The normal verified old-dist relocation did not finish.')
    command = [sys.executable, '-B', str(REPO / 'tools/build_releases.py'), '--module',
        'character_designer', '--projection', str(manifest_path)]
    result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    write_new(package / 'official_build_log.json', encoded({'command': command, 'exit_code': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr}), freeze)
    require(result.returncode == 0, 'Official local build failed; preserve its log and all old artifacts.')
    archive_matches(archive, state['captured'])
    frozen_archive = package / archive.name
    write_new(frozen_archive, archive.read_bytes(), freeze)
    receipt = {'schema': 'cdesigner.unified-source-candidate/1', 'status': 'SOURCE_FROZEN_NATIVE_PENDING',
        'source_only': True, 'native_execution_performed': False, 'native_acceptance': False,
        'version': '0.77.25', 'manifest': record(manifest_path), 'source_root': str(source_root),
        'source_freeze': record(freeze), 'source_pin_count': 20, 'file_count': 188,
        'complete_file_map_sha256': map_sha(state['hashes']), 'syntax_python_files': 156,
        'source_bytes': sum(len(raw) for raw in state['captured'].files.values()),
        'unique_pure_tests': state['unique_tests'], 'tests_executed_by_this_producer': 0,
        'all_269_run_against_current_candidate': False, 'old_candidate_provenance': state['provenance'],
        'native_apply_and_binding_AST_exact_to_immutable_r5': True,
        'sole_runtime_R5_delta': ['animation_worklist.py'], 'other_187_payload_files_unchanged': True,
        'key_source_pins': {name: digest for name, digest in state['hashes'].items()
            if name in {'__init__.py', 'unity_animation_rigging.py', 'animation_rigging_contract.py',
                'animation_link_source.py', 'animation_rigging_setup.py', 'animation_worklist.py'} or name.endswith('.cs')},
        'old_dist_relocation': {'original_path': str(archive), 'archived': record(archived, OLD_ZIP_SHA),
            'old_frozen_copy': state['provenance']['previous_frozen_archive'], 'bytes_equal': True,
            'operation': 'Normal rename after full SHA/equal-byte/resolved-dist/no-overwrite checks.'},
        'official_build': {'command': command, 'exit_code': result.returncode,
            'log': record(package / 'official_build_log.json'), 'local_candidate_only': True},
        'archive': {'dist': record(archive), 'frozen_copy': record(frozen_archive),
            'exact_188_payload': 'PASS', 'testzip': 'PASS', 'duplicates': 0},
        'actual_R5_native_failure': frozen['actual_R5_native_failure'],
        'final_destination': frozen['final_destination'],
        'boundaries': {'deployments': 0, 'native_calls': 0, 'SDK_calls': 0, 'GUI_calls': 0,
            'workers': 0, 'artist_writes': 0, 'Git_publish': 0, 'version_changes': 0},
        'limitations': frozen['limitations']}
    write_new(package / 'unified_package_receipt.json', encoded(receipt), freeze)
    print(json.dumps({'receipt': record(package / 'unified_package_receipt.json'), 'freeze': record(freeze),
        'manifest': record(manifest_path), 'archive': record(archive), 'old_dist_archived': record(archived),
        'source_only': True, 'native_acceptance': False}))


def inspect_only(state, args):
    package, freeze, _, manifest = targets(state, args)
    print(json.dumps({'status': 'SOURCE_INSPECTED_CAPTURE_AND_BUILD_NOT_EXECUTED',
        'source_only': True, 'producer': state['provenance']['producer'],
        'proposed_package': str(package), 'proposed_freeze': str(freeze),
        'proposed_manifest': str(manifest), 'complete_file_map_sha256': map_sha(state['hashes']),
        'source_pin_count': 20, 'runtime_files': 188, 'python_files': 156,
        'sole_runtime_R5_delta': ['animation_worklist.py'], 'other_187_payload_files_unchanged': True,
        'historical_unique_pure_tests': 269, 'new_unique_pure_tests': 7,
        'tests_executed_by_this_producer': 0, 'all_269_run_against_current_candidate': False,
        'preserved_actual_R5_native_result': 'FAIL', 'failure_phase': 'add_activate',
        'native_acceptance': False, 'final_destination_existing_X_Rig': True,
        'resource_reservation_or_native_authorization_inferred': False,
        'mutations': {'capture': 0, 'build': 0, 'deploy': 0, 'native': 0, 'SDK': 0,
            'workers': 0, 'artist_writes': 0, 'Git': 0}}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--inspect-only', action='store_true')
    mode.add_argument('--capture', action='store_true')
    mode.add_argument('--build-and-verify', action='store_true')
    parser.add_argument('--worklist-sha256', required=True)
    parser.add_argument('--worklist-test-sha256', required=True)
    parser.add_argument('--worklist-owner', required=True)
    parser.add_argument('--worklist-owner-sha256', required=True)
    parser.add_argument('--worklist-peer', required=True)
    parser.add_argument('--worklist-peer-sha256', required=True)
    parser.add_argument('--failure-report', required=True)
    parser.add_argument('--failure-report-sha256', required=True)
    parser.add_argument('--closure-receipt', required=True)
    parser.add_argument('--closure-receipt-sha256', required=True)
    args = parser.parse_args()
    state = inputs(args)
    if args.inspect_only:
        inspect_only(state, args)
    elif args.capture:
        capture(state, args)
    else:
        build_and_verify(state, args)


if __name__ == '__main__':
    main()
