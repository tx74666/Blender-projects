"""R13 static successor of the immutable R12 capture/official-build producer.

Source preparation performs no execution. A real finalized R13 admission is required
for every CLI mode. Run only in a separately granted static capture/build window.
This producer does not launch Blender, deploy, touch artist data, or run tests.
"""
import argparse
import ast
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
OLD_PACKAGE = ROUND / 'package_815751c3'
VERSION = '0.77.31'
OLD_MAP_SHA = '815751c396c2e82723061749b49f431c6aa6779c2dc998ee6d995fedcad14921'
UNCHANGED_RUNTIME_PINS = {
    'forearm_twist.py': ('54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408', 97739),
    'animation_original_inputs_ui.py': ('38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426', 15250),
    'animation_worklist_ui.py': ('24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067', 43636),
}
SOURCE_NAMES = set(UNCHANGED_RUNTIME_PINS) | {'unity_animation_original_inputs.py', 'unity_animation_rigging.py', '__init__.py'}
ADDED = set()
CHANGED = {'unity_animation_original_inputs.py', 'unity_animation_rigging.py', '__init__.py'}
FEATURE_TESTS = (REPO / 'tests/test_original_inputs_contract.py',
                 REPO / 'tests/test_animation_rigging_recovery.py',
                 REPO / 'tests/test_original_inputs_view_body.py')
BASELINE = {
    'r12_producer': (ROUND / 'prepare_unified_package_r12.py', '840d1c301131f69761cb92cefdc4ab8f345a28f967d8f448cbbfca51996e5171'),
    'r12_freeze': (ROOT / 'x_rigging_source_freeze_r12_69bcc032.json', 'd0a0e00c312890efc6ab934f938d6ddf1e3accd1f64887963c31b469a5ac44f1'),
    'r12_manifest': (OLD_PACKAGE / 'python_projection.json', 'eb5425a2900a3d856e38a6d40573f7f838c300e2f729e42f8c8165a181df267b'),
    'r12_receipt': (OLD_PACKAGE / 'unified_package_receipt.json', '3477b53f64af18f22b772cbc2a546a0b4a321134081417e5b6a9c2e634beeb7e'),
    'r12_archive': (OLD_PACKAGE / 'character_designer-0.77.30.zip', 'e533f92c1d20d6f578f503fe35ebae3975cbed9f7ae55b2b24a4c72631379e39'),
    'r12_postreadback': (OLD_PACKAGE / 'postbuild_source_readback.json', '0dc4047496d6e44f076bdf9d60ec0eeedcd9d59a0492781136595bddf4b3be96'),
    'r12_static_release': (ROUND / 'resource_release_X_R12_STATIC_BUILD_202610121551Z.json', '9e098dbb9bbf7fa177ce65dc15868bb4b276c401fcdb033b668fdcecb62b33fd'),
    'official_resolver': (REPO / 'tools/release_projection.py', '052e6c765c95ba46d480bf1eeca1e1dccb7685c77a4e756202ce409d20713106'),
    'official_builder': (REPO / 'tools/build_releases.py', '30759e923bde1da595f5cd9f67dd9d6f866ebb2866eb4c5f5b1747628e2872c1'),
}
DESTINATION = 'Existing original X.blend/Rig; preserve modifiers, design, materials, colors, Bone Collections, custom shapes and controllers. New scenes are isolated tests only.'


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
    require(expected is None or isinstance(expected, str)
            and re.fullmatch('[0-9a-f]{64}', expected) and sha(raw) == expected,
            'Changed Source pin: ' + str(path))
    return {'path': str(path), 'sha256': sha(raw), 'bytes': len(raw)}


def exact(row):
    require(isinstance(row, dict) and set(row) == {'path', 'sha256', 'bytes'}
            and isinstance(row['path'], str) and Path(row['path']).is_absolute()
            and type(row['bytes']) is int and row['bytes'] >= 0,
            'Malformed exact three-field Source pin.')
    actual = record(row['path'], row['sha256'])
    require(actual['bytes'] == row['bytes'], 'Changed Source byte count: ' + row['path'])
    return actual


def read_proof(row):
    pin = exact(row)
    return pin, json.loads(Path(pin['path']).read_bytes())


def file_map(source):
    return {path.as_posix(): sha(raw) for path, raw in sorted(source.files.items())}


def map_sha(files):
    return sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def archive_matches(archive, source):
    payload = {'character_designer/' + path.as_posix(): raw for path, raw in source.files.items()}
    count = len(payload)
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        require(zipped.testzip() is None and len(entries) == count
                and len({entry.filename for entry in entries}) == count
                and not any(entry.is_dir() for entry in entries), 'ZIP CRC/duplicate/full-entry check failed.')
        require({entry.filename: zipped.read(entry) for entry in entries} == payload,
                'Every ZIP byte must equal the manifest.')


def verify_source_proofs(rows, current, *, peer=False):
    require(isinstance(rows, dict) and bool(rows), 'Real Source owners/peers are mandatory.')
    coverage, pins = set(), {}
    for name, row in rows.items():
        pin, doc = read_proof(row)
        schema = doc.get('schema')
        require(doc.get('source_only') is True and doc.get('native_execution_performed') is False,
                'The actual Source proof must retain its Source-only boundary.')
        if schema == 'x.validation.original20-callback-coalescing-root-source-peer/1':
            require(peer and doc['status'] == 'SourceReady_Actual167PurePASS_NativePending',
                    'The actual current backend/native callback Root Source peer changed.')
            sources = doc['source_files']
        elif schema == 'x.validation.original20-start-synchronous-setup-source-owner/1':
            require(not peer and doc['passed'] is True and doc['status'] == 'SOURCE_READY_PURE_AND_NATIVE_PENDING'
                    and doc['source_checks']['full_backend_raw_inverse_equal_A7'] is True
                    and doc['source_checks']['all_other_functions_and_top_level_text_unchanged'] is True,
                    'The actual Original20 synchronous-start Source owner changed.')
            sources = doc['source_files']
        elif schema == 'x.validation.character-designer-original20-noop-coalesced-depsgraph-source-owner/1':
            require(not peer and doc['status'] == 'SourceReadyNativePending'
                    and doc['source_readback']['two_function_raw_inverse_matches_D685'] is True
                    and doc['source_readback']['all_other_native_bytes_exact'] is True,
                    'The actual Original20 no-op/coalesced native Source owner changed.')
            sources = {**doc['source_files'], **doc['test_source_files']}
        elif schema == 'x.validation.original20-Forearm-final-mode-source-owner/1':
            require(not peer and doc['passed'] is True and doc['status'] == 'SOURCE_READY_PURE_AND_NATIVE_PENDING'
                    and doc['checks']['full_module_raw_inverse_equal_3EF'] is True
                    and doc['checks']['scope_cannot_span_timer_or_external_generator_suspend'] is True,
                    'The actual Original20-only Forearm defer Source owner changed.')
            sources = doc['source_files']
        elif schema == 'x.validation.original20-Forearm-final-mode-independent-source-peer/1':
            require(peer and doc['passed'] is True and doc['status'] == 'SourceReady_Root_checks_and_native_pending',
                    'The actual independent Original20-only Forearm defer Source peer changed.')
            sources = doc['source_files']
        elif schema == 'x.validation.original20-readonly-Body-metadata-source-owner/1':
            require(not peer and doc['passed'] is True
                    and doc['status'] == 'SOURCE_READY_PURE_TESTS_AND_NATIVE_PENDING'
                    and doc['source_checks']['full_product_raw_inverse_equal_E85'] is True
                    and doc['source_checks']['original_Armature_ownership_rejection_retained'] is True,
                    'The genuine readonly Body-metadata Source owner changed.')
            sources = doc['source_files']
        elif schema == 'x.validation.original20-readonly-Body-digest-independent-source-peer/1':
            require(peer and doc['passed'] is True and doc['status'] == 'SourceReady_Root_tests_and_native_pending',
                    'The genuine independent readonly Body-digest Source peer changed.')
            sources = doc['source_files']
        elif doc.get('source_scope_verified') is True and isinstance(doc.get('source_files'), dict):
            sources = {**doc['source_files'], **doc.get('dependencies', {}), **doc.get('dependency_source_readback', {})}
        elif schema == 'x.validation.original20-controls-source-owner/1':
            checks = doc['checks_performed_by_owner']
            require(not peer and doc['status'] == 'SourceReady'
                    and checks['bounded_NodeFS_source_review'] is True
                    and checks['exact_source_and_dependency_byte_hashes'] is True
                    and all(type(checks[key]) is int and checks[key] == 0 for key in
                        ('syntax_or_AST', 'Python_or_other_processes', 'tests', 'Blender_SDK_GUI', 'build_deploy')),
                    'The genuine backend owner must remain a zero-execution SourceReady review.')
            sources = {**doc['source_files'], **doc['dependency_source_readback']}
        elif schema == 'x.validation.original20-native-hooks-source/1':
            require(not peer and doc['status'] == 'SOURCE_REVIEWED_SYNTAX_VERIFIED_NATIVE_PENDING'
                    and doc['source_boundary']['full_byte_inverse_exact'] is True
                    and doc['source_boundary']['ordinary_packet_model_and_native_clock_guards_unchanged'] is True,
                    'The genuine native-hooks Source review changed.')
            sources = {Path(doc['source']['path']).name: doc['source']}
        elif schema == 'x.validation.original20-controls-source-peer/1':
            require(peer and doc['passed'] is True and doc['status'] == 'SourceReady'
                    and isinstance(doc['review_scope'], str) and 'Independent' in doc['review_scope'],
                    'A real independent backend Source peer is mandatory.')
            sources = {**doc['source_files'], **doc['dependencies']}
        else:
            require(not peer and schema == 'x.validation.original-rigging-input-ui-source-owner/1'
                    and doc['passed'] is True and doc['source_scope_verified'] is True,
                    'Unexpected or incomplete actual UI Source owner.')
            sources = doc['source_files']
        for filename, source in sources.items():
            actual = exact(source)
            require(Path(actual['path']).name == filename, 'Ambiguous Source proof filename.')
            if filename in current:
                require(actual == current[filename], 'Stale final Source proof: ' + filename)
                coverage.add(filename)
        pins[name] = pin
    # Existing owners/peer cover the five implementation files. Root's finalized
    # admission and the actual syntax/pure receipts bind the version entry pin.
    required = CHANGED - {'__init__.py'} if peer else set(current) - {'__init__.py'}
    require(required <= coverage, 'The actual Source proofs omit a required current implementation file.')
    return pins


def verify_input_hashes(rows, required):
    require(isinstance(rows, dict) and bool(rows), 'Actual execution must bind physical input SHA values.')
    bound = {}
    for path, digest in rows.items():
        pin = record(path, digest)
        require(pin['path'] not in bound, 'Duplicate normalized execution Source path.')
        bound[pin['path']] = pin
    for pin in required:
        require(bound.get(pin['path']) == pin, 'Actual execution did not bind final Source: ' + pin['path'])
    return bound


def inputs(args):
    provenance = {name: record(path, digest) for name, (path, digest) in BASELINE.items()}
    provenance.update(producer=record(__file__),
        final_admission=record(args.final_admission, args.final_admission_sha256.lower()))
    _, admission = read_proof(provenance['final_admission'])
    require(admission['schema'] == 'x.validation.unified-r13-final-source-admission/1'
            and admission['passed'] is True and admission['source_only'] is True
            and admission['native'] is False and admission['native_acceptance'] is False
            and admission['final_source_stable'] is True and admission['final_destination_existing_X_Rig'] is True,
            'A real finalized R13 admission is required; drafts and old R12 PASS are not admitted.')
    certificate = admission['clock_certificate']
    provenance.update(clock_source=exact(certificate['source']),
        clock_report=exact(certificate['report']), clock_release=exact(certificate['external_release']))
    candidate_map = admission['source_map_sha256']
    require(admission['version'] == VERSION and isinstance(candidate_map, str)
            and re.fullmatch('[0-9a-f]{64}', candidate_map)
            and admission['shipped_file_count'] == 190 and admission['python_file_count'] == 158,
            'Admission must bind the genuine final R13 version/full map and190/158 candidate.')
    current = admission['current_sources']
    require(set(current) == SOURCE_NAMES, 'Exactly six current runtime pins are required.')
    for name, row in current.items():
        pin = record(REPO / 'addons/character_designer' / name, row['sha256'])
        require(exact(row) == pin, 'Final runtime pin changed: ' + name)
        if name in UNCHANGED_RUNTIME_PINS:
            digest, count = UNCHANGED_RUNTIME_PINS[name]
            require(pin['sha256'] == digest and pin['bytes'] == count, 'Unchanged Forearm/UI/worklist pin drifted: ' + name)
        current[name] = pin
    feature_tests = [record(test) for test in FEATURE_TESTS]
    provenance.update({f'feature_test_{index}': test for index, test in enumerate(feature_tests)})
    pure_required = list(current.values()) + feature_tests
    syntax_required = pure_required + [provenance['clock_source']]
    source_owners = verify_source_proofs(admission['source_owners'], current)
    source_peers = verify_source_proofs(admission['source_peers'], current, peer=True)
    require(set(admission['pure_receipts']) == set(admission['pure_raw_logs']) == {'original20'},
            'The actual R13 portable receipt and raw log are mandatory.')
    provenance['actual_pure'], pure = read_proof(admission['pure_receipts']['original20'])
    provenance['actual_pure_raw_log'] = exact(admission['pure_raw_logs']['original20'])
    require(pure['schema'] == 'x.validation.portable-contracts/1' and pure['completed'] is True
            and pure['passed'] is True and pure['native_execution_performed'] is False
            and type(pure['SDK']) is int and pure['SDK'] == 0 and pure['GUI'] is False
            and pure['input_files_unchanged'] is True and type(pure['tests_run']) is int and pure['tests_run'] > 0
            and type(admission['actual_pure_tests']) is int and pure['tests_run'] == admission['actual_pure_tests']
            and all(type(pure[key]) is int and pure[key] == 0 for key in ('failures', 'errors', 'skipped')),
            'R13 requires a complete actual portable PASS; failed/fixture/prepared evidence cannot pass.')
    pure_inputs = verify_input_hashes(pure['input_pins'], pure_required)
    raw_log = Path(provenance['actual_pure_raw_log']['path']).read_text(encoding='utf-8')
    require(provenance['actual_pure_raw_log']['bytes'] > 0
            and re.search(r'Ran\s+' + str(pure['tests_run']) + r'\s+tests?\b', raw_log)
            and re.search(r'^OK\s*$', raw_log, re.MULTILINE), 'Actual unittest raw log lacks its completed PASS summary.')
    syntax = admission['syntax_compilation']
    provenance['actual_syntax_raw_log'] = exact(syntax['raw_log'])
    require(syntax['result'] == 'PASS' and type(syntax['exit_code']) is int and syntax['exit_code'] == 0
            and type(syntax['target_imports']) is int and syntax['target_imports'] == 0
            and type(syntax['source_files']) is int and syntax['source_files'] == 10,
            'The separate actual ten-Source syntax result must retain exit0 and zero target imports.')
    syntax_inputs = verify_input_hashes(syntax['input_pins'], syntax_required)
    require(len(syntax_inputs) == 10, 'Actual syntax domain must be exactly the six runtime, three affected tests and observer.')
    syntax_log = Path(provenance['actual_syntax_raw_log']['path']).read_text(encoding='utf-8')
    require(all('AST_COMPILE_PASS ' + Path(pin['path']).name + ' ' + pin['sha256'] in syntax_log for pin in syntax_required)
            and 'SOURCE_ONLY files=10 target_imports=0 tests=0 native=0' in syntax_log,
            'Actual syntax raw log does not certify the final ten Source pins.')
    certificate = admission['clock_certificate']
    require(exact(certificate['source']) == provenance['clock_source']
            and exact(certificate['report']) == provenance['clock_report']
            and exact(certificate['external_release']) == provenance['clock_release']
            and certificate['legacy_action_rate'] == 30, 'Admission historical clock pins differ from its exact certificate.')
    provenance['historical_failed_portable'], failed_pure = read_proof(admission['historical_failed_portable_receipt'])
    require(failed_pure['schema'] == 'x.validation.portable-contracts/1' and failed_pure['completed'] is True
            and failed_pure['passed'] is False and failed_pure['tests_run'] == 162 and failed_pure['errors'] == 2,
            'Historical R8 fixture failure must remain truthful failed ancestry.')
    _, clock = read_proof(provenance['clock_report'])
    _, release = read_proof(provenance['clock_release'])
    require(clock['completed'] is True and clock['legacy_clock_known'] is True
            and clock['verified_legacy_action_rate'] == 30 and clock['Source_curve_count'] == 1896
            and clock['Source30_candidate_mismatches'] == [] and clock['context_and_pose_restored'] is True
            and clock['raw_asset_data_unchanged'] is True and clock['input_files_unchanged'] is True
            and exact(clock['source_inputs']['source']) == provenance['clock_source'], 'Historical clock actual stored-key proof changed.')
    require(release['schema'] == 'x.validation.resource-release/1'
            and release['context_and_pose_restored'] is True and release['raw_asset_data_unchanged'] is True
            and release['input_files_unchanged'] is True
            and release['retained_handle_natural_exit'] is True and type(release['native_exit_code']) is int
            and release['native_exit_code'] == 0 and release['owned_native_gone'] is True
            and release['process_termination_performed'] is False and type(release['owned_pid']) is int
            and release['owned_pid'] == clock['pid']
            and isinstance(release['owned_process_filetime'], str) and re.fullmatch(r'\d+', release['owned_process_filetime'])
            and isinstance(release['native_exited_utc'], str)
            and datetime.fromisoformat(release['native_exited_utc'].replace('Z', '+00:00')).utcoffset().total_seconds() == 0
            and exact(release['clock_source']) == provenance['clock_source']
            and exact(release['clock_report']) == provenance['clock_report'], 'Historical clock actual retained-handle exit0 proof changed.')
    old = json.loads(Path(provenance['r12_freeze']['path']).read_bytes())
    old_receipt = json.loads(Path(provenance['r12_receipt']['path']).read_bytes())
    require(old['schema'] == 'cdesigner.x-rigging-source-freeze/1' and old['pure_tests_total'] == 302
            and old_receipt['file_count'] == 190 and old_receipt['syntax_python_files'] == 158
            and old_receipt['complete_file_map_sha256'] == OLD_MAP_SHA and old_receipt['native_acceptance'] is False,
            'R12 historical190/158 with carried302 ancestry changed; it is not an R13 current or native PASS.')
    failure = old['actual_R5_native_failure']
    require(failure['result'] == 'FAIL' and failure['phase'] == 'add_activate', 'Historical native failure changed.')
    for name in ('report', 'closure', 'saved_scene'):
        provenance['r5_failed_' + name] = exact(failure[name])
    # Reuse the same official R8 resolver only after the CLI has been explicitly run.
    sys.path.insert(0, str(REPO / 'tools'))
    from release_projection import load_source
    prior = load_source('character_designer', OLD_PACKAGE / 'python_projection.json', root=REPO)
    captured = load_source('character_designer', root=REPO)
    previous, hashes = file_map(prior), file_map(captured)
    require(map_sha(previous) == OLD_MAP_SHA and len(previous) == 190 and prior.version == '0.77.30'
            and map_sha(hashes) == candidate_map and len(hashes) == 190 and captured.version == VERSION,
            'Complete actual R12/R13 runtime set/version differs from the approved candidate.')
    require(set(hashes) - set(previous) == ADDED and not (set(previous) - set(hashes))
            and {name for name in previous if hashes[name] != previous[name]} == CHANGED
            and sum(hashes[name] == digest for name, digest in previous.items()) == 187,
            'Only original-input preview, native display handling and version init payloads may change; other187 must remain exact.')
    archive_matches(OLD_PACKAGE / 'character_designer-0.77.30.zip', prior)
    python_count = 0
    for name, raw in captured.files.items():
        if name.suffix == '.py':
            compile(ast.parse(raw, filename=name.as_posix()), name.as_posix(), 'exec')
            python_count += 1
    require(python_count == 158,
            'Expected the complete190/158 R13 payload.')
    return {'captured': captured, 'hashes': hashes, 'map_sha': candidate_map,
        'source_bytes': sum(len(raw) for raw in captured.files.values()), 'current': current, 'provenance': provenance,
        'admission': admission, 'old': old, 'pure': pure, 'pure_inputs': pure_inputs,
        'source_owners': source_owners, 'source_peers': source_peers, 'load_source': load_source}


def targets(state):
    package = ROUND / ('package_' + map_sha(state['hashes'])[:8])
    freeze = ROOT / ('x_rigging_source_freeze_r13_' + state['current']['unity_animation_rigging.py']['sha256'][:8] + '.json')
    return package, freeze, package / 'source/character_designer', package / 'python_projection.json'


def write_new(path, raw, freeze):
    path = path.resolve()
    require(path == freeze.resolve() or path.is_relative_to(ROUND), 'New artifact leaves owned Source scope.')
    require(not path.exists(), 'Refuse overwriting immutable Source evidence: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def capture(state):
    package, freeze, source_root, manifest_path = targets(state)
    require(not package.exists() and not freeze.exists(), 'Use unique new R13 outputs.')
    frozen = {'schema': 'cdesigner.x-rigging-source-freeze/1', 'status': 'SOURCE_FROZEN_NATIVE_PENDING',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'source_only': True,
        'native_execution_performed': False, 'canonical_repository': str(REPO), 'version': VERSION,
        'source_pins': list(state['current'].values()), 'previous_source_freeze': state['provenance']['r12_freeze'],
        'r13_source_provenance': state['provenance'], 'final_source_admission': state['admission'],
        'source_delta': {'runtime_added': sorted(ADDED), 'runtime_replaced': sorted(CHANGED),
            'runtime_deleted': [], 'other_187_payload_files_unchanged': True},
        'syntax_compilation': {'python_payload_files': 158, 'result': 'PASS', 'target_imports': 0,
            'separate_actual_source_check': state['admission']['syntax_compilation']},
        'pure_tests': state['old']['pure_tests'], 'pure_tests_total': 302,
        'cumulative_case_attribution': {'historical_R7_unique': 302,
            'actual_R13_current_tests_run': state['pure']['tests_run'], 'new_R13_unique_cases_claimed': False,
            'all_cumulative_cases_run_against_current_candidate': False},
        'actual_R13_pure': {'receipt': state['provenance']['actual_pure'],
            'raw_log': state['provenance']['actual_pure_raw_log'], 'tests_executed_by_this_producer': 0},
        'source_owners': state['source_owners'], 'source_peers': state['source_peers'],
        'historical_clock_certificate': {'report': state['provenance']['clock_report'], 'release': state['provenance']['clock_release'],
            'verified_legacy_action_rate': 30, 'new20_native_acceptance_inferred': False},
        'actual_R5_native_failure': state['old']['actual_R5_native_failure'], 'final_destination': DESTINATION,
        'boundaries': {'deployments': 0, 'native_calls': 0, 'SDK_calls': 0, 'GUI_calls': 0,
            'workers': 0, 'artist_writes': 0, 'Git_publish': 0, 'version_changes': 0},
        'limitations': ['Historical302 cases are carried exact; this producer executes zero tests.',
            'Historical clock verifies its recorded legacy30 inputs only; current-artist clock and native acceptance remain pending.',
            'Original20 native clone/public UI/Undo/save-reopen and original artist integration remain pending.',
            'R5 actual add_activate FAIL and its saved scene/natural closure remain failed ancestry.',
            'Static build and old resource receipts grant no new native/deployment/SDK resource scope.']}
    require(file_map(state['load_source']('character_designer', root=REPO)) == state['hashes'], 'Canonical drift before capture.')
    for row in state['provenance'].values():
        exact(row)
    write_new(freeze, encoded(frozen), freeze)
    package.mkdir()
    for path, raw in state['captured'].files.items():
        write_new(source_root / path, raw, freeze)
    manifest = {'schema_version': 1, 'module': 'character_designer', 'version': VERSION,
        'source_root': str(source_root), 'files': state['hashes'], 'source_provenance': {
            'purpose': 'Original20 readonly Source/editable Custom and original legacyBody reference; native pending',
            'source_freeze': record(freeze), 'previous_candidate': state['provenance']['r12_manifest'],
            'complete_file_map_sha256': state['map_sha'], 'producer': state['provenance']['producer'],
            'final_admission': state['provenance']['final_admission'], 'native_acceptance': False,
            'deployment_authorized': False, 'final_destination_existing_X_Rig': True}}
    write_new(manifest_path, encoded(manifest), freeze)
    require(state['load_source']('character_designer', manifest_path, root=REPO).files == state['captured'].files,
            'Frozen complete payload differs from captured bytes.')
    print(json.dumps({'freeze': record(freeze), 'manifest': record(manifest_path), 'files': 190,
        'python_files': 158, 'file_map_sha256': state['map_sha'], 'tests_executed_by_this_producer': 0,
        'native_acceptance': False}))


def build_and_verify(state):
    package, freeze, source_root, manifest_path = targets(state)
    manifest = json.loads(manifest_path.read_bytes())
    require(exact(manifest['source_provenance']['source_freeze']) == record(freeze)
            and exact(manifest['source_provenance']['producer']) == state['provenance']['producer']
            and exact(manifest['source_provenance']['final_admission']) == state['provenance']['final_admission'],
            'Frozen producer/final admission changed after capture.')
    frozen = json.loads(freeze.read_bytes())
    require(frozen['source_pins'] == list(state['current'].values())
            and frozen['r13_source_provenance'] == state['provenance'], 'Admitted R13 freeze changed.')
    require(state['load_source']('character_designer', manifest_path, root=REPO).files == state['captured'].files,
            'Canonical/frozen bytes changed before the official build.')
    archive = REPO / ('dist/character_designer-' + VERSION + '.zip')
    old_dist = {str(path.resolve()): record(path) for path in sorted((REPO / 'dist').glob('*.zip'))}
    if archive.exists():
        archive_matches(archive, state['captured'])
    command = [sys.executable, '-B', str(REPO / 'tools/build_releases.py'), '--module',
        'character_designer', '--projection', str(manifest_path)]
    result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False, shell=False)
    write_new(package / 'official_build_log.json', encoded({'command': command, 'exit_code': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr}), freeze)
    require(result.returncode == 0, 'Official local build failed; retain its log and all old evidence.')
    require(all(record(path) == pin for path, pin in old_dist.items()), 'An existing dist ZIP changed.')
    archive_matches(archive, state['captured'])
    require(file_map(state['load_source']('character_designer', root=REPO)) == state['hashes'],
            'Canonical190 payload drifted during the official build.')
    for row in state['provenance'].values():
        exact(row)
    for row in state['pure_inputs'].values():
        exact(row)
    for row in (*state['source_owners'].values(), *state['source_peers'].values()):
        exact(row)
    frozen_archive = package / archive.name
    write_new(frozen_archive, archive.read_bytes(), freeze)
    receipt = {'schema': 'cdesigner.unified-source-candidate/1', 'status': 'SOURCE_FROZEN_NATIVE_PENDING',
        'source_only': True, 'native_execution_performed': False, 'native_acceptance': False,
        'version': VERSION, 'manifest': record(manifest_path), 'source_root': str(source_root),
        'source_freeze': record(freeze), 'source_pin_count': len(state['current']), 'file_count': 190,
        'complete_file_map_sha256': state['map_sha'], 'syntax_python_files': 158, 'source_bytes': state['source_bytes'],
        'unique_pure_tests': 302, 'tests_executed_by_this_producer': 0,
        'all_cumulative_cases_run_against_current_candidate': False,
        'actual_current_pure_tests': state['pure']['tests_run'],
        'candidate_provenance': state['provenance'], 'cumulative_case_attribution': frozen['cumulative_case_attribution'],
        'runtime_R12_deltas': {'added': sorted(ADDED), 'replaced': sorted(CHANGED), 'deleted': []},
        'other_187_payload_files_unchanged': True, 'existing_dist_archives': old_dist,
        'old_dist_relocation': False,
        'official_build': {'command': command, 'exit_code': result.returncode,
            'log': record(package / 'official_build_log.json'), 'local_candidate_only': True},
        'archive': {'dist': record(archive), 'frozen_copy': record(frozen_archive),
            'exact_190_payload': 'PASS', 'testzip': 'PASS', 'duplicates': 0},
        'historical_clock_certificate': frozen['historical_clock_certificate'], 'actual_R5_native_failure': frozen['actual_R5_native_failure'],
        'final_destination': DESTINATION, 'boundaries': frozen['boundaries'], 'limitations': frozen['limitations']}
    write_new(package / 'unified_package_receipt.json', encoded(receipt), freeze)
    print(json.dumps({'receipt': record(package / 'unified_package_receipt.json'), 'freeze': record(freeze),
        'manifest': record(manifest_path), 'archive': record(archive), 'source_only': True, 'native_acceptance': False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--inspect-only', action='store_true')
    modes.add_argument('--capture', action='store_true')
    modes.add_argument('--build-and-verify', action='store_true')
    modes.add_argument('--capture-and-build', action='store_true',
                       help='Validate once, then capture and build serially with all boundary rechecks')
    parser.add_argument('--final-admission', required=True)
    parser.add_argument('--final-admission-sha256', required=True)
    args = parser.parse_args()
    state = inputs(args)
    if args.capture_and_build:
        capture(state)
        build_and_verify(state)
    elif args.capture:
        capture(state)
    elif args.build_and_verify:
        build_and_verify(state)
    else:
        package, freeze, _, manifest = targets(state)
        print(json.dumps({'status': 'FINAL_SOURCE_INSPECTED_CAPTURE_BUILD_NATIVE_NOT_EXECUTED',
            'producer': state['provenance']['producer'], 'final_admission': state['provenance']['final_admission'],
            'proposed_package': str(package), 'proposed_freeze': str(freeze), 'proposed_manifest': str(manifest),
            'version': VERSION, 'runtime_files': 190, 'python_files': 158, 'file_map_sha256': state['map_sha'],
            'runtime_R12_deltas': {'added': sorted(ADDED), 'replaced': sorted(CHANGED)},
            'other_187_payload_files_unchanged': True, 'actual_current_pure_tests': state['pure']['tests_run'],
            'historical_R7_unique_cases': 302, 'all_cumulative_cases_run_against_current_candidate': False,
            'tests_executed_by_this_producer': 0, 'capture': 0, 'build': 0, 'deploy': 0,
            'native': 0, 'SDK': 0, 'workers': 0, 'artist_writes': 0, 'native_acceptance': False}))


if __name__ == '__main__':
    main()
