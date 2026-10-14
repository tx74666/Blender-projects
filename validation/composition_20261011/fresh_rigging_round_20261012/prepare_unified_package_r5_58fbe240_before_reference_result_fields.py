"""Prepare an explicit R5 Source successor; no work runs when imported.

Final native/reference pins and their completed pure receipt are mandatory CLI
inputs. Capture/build requires a separate Parent instruction; writing this
Source is not a native, deployment, installation or publishing authorization.
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
OLD_PACKAGE = ROUND / 'package_f9e41c12'
OLD_FREEZE = ROOT / 'x_rigging_source_freeze_r4_bff52cbe.json'
OLD_FREEZE_SHA = '71fd41971f2e7c889dcb1ff7a427ddb7cd58b6560015b658c960c067c869ed89'
OLD_MANIFEST_SHA = 'ac12952c816f17ae86ac732ab18f4dcb5dc37dfa68aa39be600b27ef1d6b362f'
OLD_ZIP_SHA = 'f7abc518fe519ed0318202fb98f84f96fbec4ab8a4c7a95bf733005318d980cb'
INIT_SHA = 'd66a88023e93c3db64f1b64cfaf8089d4c956adc0f97896c591e34a54d8e4dd2'
FIXED = {
    'animation_link_source.py': ('c563543dc6c540aa7f8c97f0f8e5913ff1df2a5377bbbe118e9a1c21b8cd5708', 14481),
    'animation_rigging_setup.py': ('e5ae7c4df9bb30f4e55719285cb7721963a3ab798c7225c806a436837559df93', 13772),
    'test_animation_rigging_setup.py': ('4a253d9cad67d0423e27f7ff3538aa066d10c47a5bb4f22d7c1bf3e990a9245c', 12803),
    'test_animation_link_source_rigging_setup.py': ('df88a63fa225905f1f90fb330bab166e27fb2306f88a4be0cb120f529dc51c8c', 14228),
    'test_animation_rigging_recovery.py': ('3b9a05733b1b4dd01591a60a03a7f44f7dce272851e61c15de361501812682d9', 28692),
}
EVIDENCE = {
    'setup_owner': (ROOT / 'animation_rigging_fresh_arm_setup_owner_source_e5ae7c4d.json', '0c3b86c6e8c3d074bd735c12513a2168fd4dc910a44cd7e6ec3839de18978197'),
    'setup_peer': (ROOT / 'animation_rigging_fresh_arm_setup_peer_source_e5ae7c4d.json', '251b54e06c4ae42f8ed0179ae1e006a4968cec0307c0038f143c6e79cc1d6380'),
    'routing': (ROOT / 'animation_link_source_fresh_arm_routing_source_receipt_df88a63f.json', 'bb371718ab881bbefb5ac8aabbd178e8534febaefe24e04a211dd61077d926e2'),
    'preview_semantics': (ROUND / 'rigging_preview_semantics_source_receipt_3b9a0573.json', '141d5e27d9c1b70bd29e85736a70cfc83d21882fb271f84569cfee1ebbaf8bbe'),
    'actual_input_readonly': (ROUND / 'actual_prepared_22e92164_input_readonly.json', 'e553362d8c8193167a5ebf5a49e162d979d3f87281256ab00605277bdc1d5a65'),
    'reference_serialized_audit': (ROUND / 'preview_reference_serialized_audit_230b9a0f.json', 'e09e5c040edfa4b3315f64bf4ca0d97d3430cb58c8961aa314836c4704acbef3'),
}
ADDED = {'animation_rigging_setup.py', 'test_animation_rigging_setup.py',
         'test_animation_link_source_rigging_setup.py', 'test_animation_rigging_reference.py'}
ARCHIVED_DIST = REPO / 'dist/archived_candidates/character_designer-0.77.25-source-f9e41c12-f7abc518.zip'
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


def inputs(args):
    provenance = {'previous_source_freeze': record(OLD_FREEZE, OLD_FREEZE_SHA),
        'previous_manifest': record(OLD_PACKAGE / 'python_projection.json', OLD_MANIFEST_SHA),
        'previous_frozen_archive': record(OLD_PACKAGE / 'character_designer-0.77.25.zip', OLD_ZIP_SHA),
        'producer': record(__file__), 'official_resolver': record(REPO / 'tools/release_projection.py'),
        'official_builder': record(REPO / 'tools/build_releases.py')}
    old = json.loads(OLD_FREEZE.read_bytes())
    require(old['schema'] == 'cdesigner.x-rigging-source-freeze/1'
            and len(old['source_pins']) == 15 and old['pure_tests_total'] == 222,
            'R4 fifteen-source/222-test ancestry changed.')
    evidence = {}
    for name, (path, digest) in EVIDENCE.items():
        provenance[name] = record(path, digest)
        evidence[name] = json.loads(path.read_bytes())
    for name in ('setup_owner', 'setup_peer', 'routing', 'preview_semantics'):
        doc = evidence[name]
        require(doc['passed'] is True and doc['source_only'] is True
                and doc['native_execution_performed'] is False, 'Closed Source-only evidence required: ' + name)
    require(evidence['setup_owner']['pure_test_results']['test_count'] == 8
            and evidence['setup_owner']['pure_test_results']['exit_code'] == 0
            and evidence['routing']['actual_test_results']['total'] == 13
            and evidence['routing']['actual_test_results']['new_routing_tests'] == 7
            and evidence['routing']['actual_test_results']['existing_image_tests'] == 6
            and evidence['routing']['actual_test_results']['exit_code'] == 0
            and evidence['preview_semantics']['pure_test_results']['test_count'] == 12
            and evidence['preview_semantics']['pure_test_results']['new_preview_cases'] == 5
            and evidence['preview_semantics']['pure_test_results']['exit_code'] == 0,
            'Required pure actual results are incomplete.')
    exact(evidence['routing']['actual_test_results']['raw_log'])
    readonly = evidence['actual_input_readonly']
    provenance['actual_prepare_report'] = exact(readonly['pins']['report'])
    require(evidence['reference_serialized_audit']['status'] == 'SERIALIZED_INPUTS_MATCH_NATIVE_MAPPING_PENDING'
            and evidence['reference_serialized_audit']['runtime_operations']['native'] == 0,
            'The readonly reference evidence must not become a native acceptance claim.')
    reference_pin = record(args.reference_owner, args.reference_owner_sha256)
    reference = json.loads(Path(reference_pin['path']).read_bytes())
    require(reference['schema'] == 'x.validation.rigging-preview-reference-source-owner/1'
            and reference['source_only'] is True and reference['native_execution_performed'] is False
            and reference['apply_unchanged'] is True, 'Final native reference Source receipt is not closed.')
    counts = reference['test_result']
    require(type(counts['total']) is int and counts['total'] > 0
            and type(counts['new_added']) is int and counts['new_added'] > 0
            and counts['new_added'] <= counts['total']
            and (counts['pass'] is True or type(counts['pass']) is int and counts['pass'] == counts['total'])
            and type(counts['fail']) is int and counts['fail'] == 0,
            'Reference pure tests must actually pass; no guessed test count.')
    if counts.get('log_pin') is not None:
        exact(counts['log_pin'])
    recovery_pin = record(args.current_recovery_receipt, args.current_recovery_receipt_sha256)
    recovery = json.loads(Path(recovery_pin['path']).read_bytes())
    require(recovery['schema'] == 'cdesigner.current-native-recovery-pure/1'
            and recovery['passed'] is True and recovery['source_only'] is True
            and recovery['native_execution_performed'] is False,
            'A completed pure recovery receipt for the final current native source is mandatory.')
    recovery_result = recovery['test_result']
    require(type(recovery_result['total']) is int and recovery_result['total'] == 12
            and type(recovery_result['exit_code']) is int and recovery_result['exit_code'] == 0
            and type(recovery_result['actual_run']) is int and recovery_result['actual_run'] == 1
            and recovery['apply_and_binding_plan_AST_unchanged'] is True
            and recovery['source_pins_unchanged_after_test'] is True,
            'Current-native recovery must be one actual twelve-test PASS with unchanged Source.')
    exact(recovery_result['log_pin'])
    expected = dict(FIXED)
    expected['unity_animation_rigging.py'] = (args.native_sha256.lower(), None)
    expected['test_animation_rigging_reference.py'] = (args.reference_test_sha256.lower(), None)
    updated = []
    paths = {Path(row['path']).name: (Path(row['path']), row) for row in old['source_pins']}
    for name in ADDED:
        paths[name] = (REPO / ('addons/character_designer' if not name.startswith('test_') else 'tests') / name, None)
    require(len(paths) == 19 and set(paths) == {Path(row['path']).name for row in old['source_pins']} | ADDED,
            'Expected exactly fifteen prior plus four new Source pins.')
    for name, (path, prior) in sorted(paths.items()):
        row = record(path)
        digest, size = expected.get(name, (prior['sha256'], prior['bytes']) if prior else ('', None))
        require(row['sha256'] == digest and (size is None or row['bytes'] == size),
                'Unauthorized Source delta: ' + name)
        compile(ast.parse(path.read_bytes(), filename=str(path)), str(path), 'exec')
        updated.append({**row, 'syntax': 'PASS'})
    by_name = {Path(row['path']).name: {key: row[key] for key in ('path', 'sha256', 'bytes')} for row in updated}
    for name in ('unity_animation_rigging.py', 'test_animation_rigging_reference.py'):
        require(reference['source_files'][name] == by_name[name], 'Final reference receipt does not bind its exact current source.')
    require(set(recovery['source_files']) == {'unity_animation_rigging.py', 'test_animation_rigging_recovery.py'},
            'Current recovery must bind exactly its actual native and recovery test files.')
    for name, row in recovery['source_files'].items():
        require(exact(row) == by_name[name], 'Current recovery receipt/source three-pin differs: ' + name)
    for name in ('setup_owner', 'setup_peer', 'routing'):
        for key, row in evidence[name]['source_files'].items():
            require(row == by_name[key], 'Source evidence/current file pin differs: ' + name + ':' + key)
    prior_native = old['source_pins'][next(i for i, row in enumerate(old['source_pins'])
        if Path(row['path']).name == 'unity_animation_rigging.py')]
    frozen_native = OLD_PACKAGE / 'source/character_designer/unity_animation_rigging.py'
    provenance['historical_native_source'] = record(frozen_native, prior_native['sha256'])
    require(reference['prior_native_pin']['sha256'] == prior_native['sha256']
            and by_name['unity_animation_rigging.py']['sha256'] != prior_native['sha256']
            and function_ast(frozen_native.read_bytes(), '_apply') == function_ast(
                Path(by_name['unity_animation_rigging.py']['path']).read_bytes(), '_apply')
            and function_ast(frozen_native.read_bytes(), '_binding_plan') == function_ast(
                Path(by_name['unity_animation_rigging.py']['path']).read_bytes(), '_binding_plan'),
            'The original preview algorithm must remain exact; the old canonical pin is historical only.')
    provenance['reference_owner'] = reference_pin
    provenance['current_native_recovery'] = recovery_pin
    old_source = load_source('character_designer', OLD_PACKAGE / 'python_projection.json', root=REPO)
    captured = load_source('character_designer', root=REPO)
    old_hashes, hashes = file_map(old_source), file_map(captured)
    require(captured.version == old_source.version == '0.77.25' and len(hashes) == 188
            and set(hashes) == set(old_hashes) | {'animation_rigging_setup.py'}
            and hashes['__init__.py'] == INIT_SHA, 'Full shipped set/version/init differs from the approved scope.')
    require({name for name in old_hashes if hashes[name] != old_hashes[name]}
            == {'animation_link_source.py', 'unity_animation_rigging.py'}
            and hashes['animation_link_source.py'] == FIXED['animation_link_source.py'][0]
            and hashes['unity_animation_rigging.py'] == args.native_sha256.lower()
            and hashes['animation_rigging_setup.py'] == FIXED['animation_rigging_setup.py'][0],
            'Runtime delta exceeds the two approved replacements and one new helper.')
    py_count = 0
    for path, raw in captured.files.items():
        if path.suffix == '.py':
            compile(ast.parse(raw, filename=path.as_posix()), path.as_posix(), 'exec')
            py_count += 1
    require(py_count == 156, 'Expected the complete 156-Python candidate.')
    return {'old': old, 'updated': updated, 'captured': captured, 'hashes': hashes,
        'python_count': py_count, 'provenance': provenance, 'evidence': evidence,
        'reference': reference, 'unique_tests': 222 + 8 + 7 + 5 + counts['new_added']}


def targets(state, args):
    package = ROUND / ('package_' + map_sha(state['hashes'])[:8])
    freeze = ROOT / ('x_rigging_source_freeze_r5_' + args.native_sha256.lower()[:8] + '.json')
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
    require(not package.exists() and not freeze.exists(), 'Use unique new R5 outputs.')
    frozen = deepcopy(state['old'])
    frozen.update(created_utc=datetime.now(timezone.utc).isoformat(), source_only=True,
        native_execution_performed=False, source_pins=state['updated'],
        pure_tests_total=state['unique_tests'], previous_source_freeze=state['provenance']['previous_source_freeze'],
        r5_source_provenance=state['provenance'], source_delta={'prior_pins_changed':
            ['animation_link_source.py', 'unity_animation_rigging.py', 'test_animation_rigging_recovery.py'],
            'prior_pins_unchanged': 12, 'added_pins': sorted(ADDED), 'source_pin_count': 19,
            'runtime_replaced': ['animation_link_source.py', 'unity_animation_rigging.py'],
            'runtime_added': ['animation_rigging_setup.py'], 'other_185_payload_files_unchanged': True},
        syntax_compilation={'source_files': 19, 'python_payload_files': 156, 'result': 'PASS', 'target_imports': 0},
        actual_prepare_source_evidence={'readonly_input': state['provenance']['actual_input_readonly'],
            'report': state['provenance']['actual_prepare_report'], 'recorded_input_pins': state['evidence']['actual_input_readonly']['pins'],
            'native_original_X_acceptance': False},
        preview_semantics={'source_receipt': state['provenance']['preview_semantics'],
            'readonly_reference_serialized_audit': state['provenance']['reference_serialized_audit'],
            'native_apply_AST_exact_to_immutable_r4': True, 'preview_pure_only': True,
            'Unknown_remains_Unknown': True, 'manual_sync_policy_unchanged': True})
    for row in frozen['pure_tests']:
        row.update(executions_by_this_producer=0, evidence_scope='Carried historical exact test Source; not rerun by this producer.')
        if row['file'] == 'test_animation_rigging_recovery.py':
            row.update(tests=12, provenance=state['provenance']['current_native_recovery'],
                historical_preview_semantics_provenance=state['provenance']['preview_semantics'],
                evidence_scope='One actual current-final-native twelve-test pure PASS, bound to exact source and durable log; historical b459 semantics remain separate.')
        if row['file'] == 'test_animation_link_source_images.py':
            row.update(provenance=state['provenance']['routing'],
                evidence_scope='Actual six existing image cases rerun with routing; zero new unique cases.')
    for name, count, evidence in (('test_animation_rigging_setup.py', 8, 'setup_owner'),
            ('test_animation_link_source_rigging_setup.py', 7, 'routing'),
            ('test_animation_rigging_reference.py', state['reference']['test_result']['new_added'], 'reference_owner')):
        frozen['pure_tests'].append({'file': name, 'tests': count, 'result': 'PASS', 'native': False,
            'provenance': state['provenance'][evidence], 'executions_by_this_producer': 0})
    require(sum(row['tests'] for row in frozen['pure_tests']) == state['unique_tests'], 'Unique test arithmetic changed.')
    frozen['limitations'] += ['R5 is local Source-only at 0.77.25 with no version bump or native claim.',
        'Fresh ARM setup is restricted to the actual new imported model; original X/fork acceptance is not inherited.',
        'Current-native recovery twelve-test execution has its own exact receipt/log; historical b459 semantics and reference tests are separate and not double counted.',
        'Reference setter, preview, routing and pure PASS do not prove installed native behavior, solver parity or Unity Apply.']
    require(file_map(load_source('character_designer', root=REPO)) == state['hashes'], 'Canonical drift before capture.')
    for row in state['updated']:
        exact({key: row[key] for key in ('path', 'sha256', 'bytes')})
    write_new(freeze, encoded(frozen), freeze)
    package.mkdir()
    for path, raw in state['captured'].files.items():
        write_new(source_root / path, raw, freeze)
    manifest = {'schema_version': 1, 'module': 'character_designer', 'version': '0.77.25',
        'source_root': str(source_root), 'files': state['hashes'], 'source_provenance': {
            'purpose': 'Source-only fresh model ARM setup/reference successor; native pending',
            'source_freeze': record(freeze), 'previous_candidate': state['provenance']['previous_manifest'],
            'complete_file_map_sha256': map_sha(state['hashes']), 'producer': state['provenance']['producer'],
            'local_source_no_bump': True, 'native_acceptance': False, 'deployment_authorized': False}}
    write_new(manifest_path, encoded(manifest), freeze)
    require(load_source('character_designer', manifest_path, root=REPO).files == state['captured'].files,
            'Frozen complete payload differs from the captured bytes.')
    print(json.dumps({'freeze': record(freeze), 'manifest': record(manifest_path),
        'file_map_sha256': map_sha(state['hashes']), 'files': 188, 'python_files': 156,
        'unique_pure_tests': state['unique_tests'], 'native_acceptance': False}))


def build_and_verify(state, args):
    package, freeze, source_root, manifest_path = targets(state, args)
    manifest = json.loads(manifest_path.read_bytes())
    require(exact(manifest['source_provenance']['source_freeze']) == record(freeze)
            and exact(manifest['source_provenance']['producer']) == state['provenance']['producer'],
            'The entire frozen receipt or producing Source changed after capture.')
    frozen = json.loads(freeze.read_bytes())
    require(frozen['source_pins'] == state['updated'] and frozen['pure_tests_total'] == state['unique_tests'],
            'The admitted R5 Source receipt changed.')
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
    require(archive.read_bytes() == (OLD_PACKAGE / archive.name).read_bytes(), 'R4 dist/frozen ZIP bytes differ.')
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
    payload = {'character_designer/' + path.as_posix(): raw for path, raw in state['captured'].files.items()}
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        require(zipped.testzip() is None and len(entries) == 188
                and len({entry.filename for entry in entries}) == 188
                and not any(entry.is_dir() for entry in entries), 'ZIP CRC/duplicate/full-entry check failed.')
        require({entry.filename: zipped.read(entry) for entry in entries} == payload, 'Every ZIP byte must equal the manifest.')
    frozen_archive = package / archive.name
    write_new(frozen_archive, archive.read_bytes(), freeze)
    receipt = {'schema': 'cdesigner.unified-source-candidate/1', 'status': 'SOURCE_FROZEN_NATIVE_PENDING',
        'source_only': True, 'native_execution_performed': False, 'native_acceptance': False,
        'version': '0.77.25', 'manifest': record(manifest_path), 'source_root': str(source_root),
        'source_freeze': record(freeze), 'source_pin_count': 19, 'file_count': 188,
        'complete_file_map_sha256': map_sha(state['hashes']), 'syntax_python_files': 156,
        'source_bytes': sum(len(raw) for raw in state['captured'].files.values()),
        'unique_pure_tests': state['unique_tests'], 'tests_executed_by_this_producer': 0,
        'old_candidate_provenance': state['provenance'], 'native_apply_AST_exact_to_immutable_r4': True,
        'key_source_pins': {name: digest for name, digest in state['hashes'].items()
            if name in {'__init__.py', 'unity_animation_rigging.py', 'animation_rigging_contract.py',
                'animation_link_source.py', 'animation_rigging_setup.py'} or name.endswith('.cs')},
        'old_dist_relocation': {'original_path': str(archive), 'archived': record(archived, OLD_ZIP_SHA),
            'old_frozen_copy': state['provenance']['previous_frozen_archive'], 'bytes_equal': True,
            'operation': 'Normal rename after full SHA/equal-byte/resolved-dist/no-overwrite checks.'},
        'official_build': {'command': command, 'exit_code': result.returncode,
            'log': record(package / 'official_build_log.json'), 'local_candidate_only': True},
        'archive': {'dist': record(archive), 'frozen_copy': record(frozen_archive),
            'exact_188_payload': 'PASS', 'testzip': 'PASS', 'duplicates': 0},
        'boundaries': {'deployments': 0, 'native_calls': 0, 'SDK_calls': 0, 'GUI_calls': 0,
            'workers': 0, 'artist_writes': 0, 'Git_publish': 0, 'version_changes': 0},
        'limitations': frozen['limitations']}
    write_new(package / 'unified_package_receipt.json', encoded(receipt), freeze)
    print(json.dumps({'receipt': record(package / 'unified_package_receipt.json'), 'freeze': record(freeze),
        'manifest': record(manifest_path), 'archive': record(archive), 'old_dist_archived': record(archived),
        'source_only': True, 'native_acceptance': False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--capture', action='store_true')
    mode.add_argument('--build-and-verify', action='store_true')
    parser.add_argument('--native-sha256', required=True)
    parser.add_argument('--reference-test-sha256', required=True)
    parser.add_argument('--reference-owner', required=True)
    parser.add_argument('--reference-owner-sha256', required=True)
    parser.add_argument('--current-recovery-receipt', required=True)
    parser.add_argument('--current-recovery-receipt-sha256', required=True)
    args = parser.parse_args()
    state = inputs(args)
    (capture if args.capture else build_and_verify)(state, args)


if __name__ == '__main__':
    main()
