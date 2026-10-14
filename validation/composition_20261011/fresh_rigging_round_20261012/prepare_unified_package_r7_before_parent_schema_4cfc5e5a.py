"""R7 Source draft: original-Rig prepared Attach plus the translation-domain fix.

This producer is unexecuted under the Building human-priority HOLD. A finalized,
hash-bound admission document with actual Source peers and pure run receipts is
mandatory even for --inspect-only. Draft/UI-ready receipts are not test PASS.
No action runs on import. Capture/build requires a separate Parent instruction;
this module never starts Blender/SDK/workers, deploys, or edits the artist scene.
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
BASELINE = {
    'r5_freeze': (OLD_FREEZE, '8f8333f085c1a370befc6f2bdfdb1f96a946c03c4fbf7a46e358a75f9ebc327b'),
    'r5_manifest': (OLD_PACKAGE / 'python_projection.json', 'd966326fda04aa9fa96f720470b5689566de73eef01c510886f8abb8051676e9'),
    'r5_archive': (OLD_PACKAGE / 'character_designer-0.77.25.zip', '70a6121c5c0d949c9f75b62937766aae97f55918c7618c554ed40eba8f295ffc'),
    'r5_receipt': (OLD_PACKAGE / 'unified_package_receipt.json', '8b290c2616f4781fe6bb16b338addc9a0e1e4b92021b0e661f53ae2e0b1b3c9f'),
    'r5_readback': (OLD_PACKAGE / 'postbuild_readback.json', '6b87680c0891a2d127de9aecf55df3063b169dfe3ba828b8dddd0c401894bde5'),
    'r5_producer': (ROUND / 'prepare_unified_package_r5.py', '6ccea8124d6c374073439e1ed48b7184c17899cef2f7c1c1fb3d7b14f0bce3d8'),
    'held_r6_producer': (ROUND / 'prepare_unified_package_r6.py', '08d827b270e2f27a656f66cd91bd4607b037941b2d83a79e1d8716ae037c6fa7'),
    'held_r6_preparation_owner': (ROUND / 'prepare_unified_package_r6_owner_source_08d827b2.json', 'fc75ac73540a890af292c1c04ca9e8294459c3c511f11de5610f367259821611'),
    'historical_editing_owner': (ROUND / 'worklist_rigging_editing_data_source_owner_80af3395.json', '8e8796ebcf9943225dc05b4f6a9471441da2ecff02ea3f90370f38161f4bce4d'),
    'historical_editing_peer': (ROUND / 'worklist_rigging_editing_data_source_peer_80af3395.json', '47549e3aab444ffd3832566326fd1179c3615097071872200e5356d16e5ae77c'),
    'historical_80af_snapshot': (ROUND / 'animation_worklist_80af3395_before_original_rigging_attach.py', '80af33958b6326b59f5c2864a560f94e1c24a2b6d3e38f34117b2d75357689f6'),
    'ui_source_ready_not_test_pass': (ROUND / 'worklist_rigging_attach_ui_source_ready_e57c2f51.json', 'ae81a08a43bc41bba4c610dcfcf5d33de94aa3e8729488f430d7ffb87f3677c1'),
    'core_prerun_not_test_pass': (ROUND / 'worklist_original_rigging_attach_source_owner_prerun_d4de3eff.json', '66abfefb24809500b645f4c01ea1fe0f86a514e897b7adbd7aa442a4276630e0'),
    'root_source_review_not_test_pass': (ROUND / 'original_rigging_attach_root_source_peer_d4de_e57.json', '7b389f20d7509cbe23611f2dd25881b4cd8cd1365f3167166e2be9c5fe01a4fd'),
    'r5_actual_failed_report': (ROUND / 'native_c5_control_01/new_official_cosha_report.json', '46aae9142e5c7cd1bfbdc04315386aaa3ef4ffc442949866e7542840ab18a37a'),
    'r5_actual_failed_closure': (ROUND / 'resource_release_X_COSHA_CONTROLS_R5_202610112351Z.json', '15926680c930f98dc45cce5191bc1c92bfa39fb817d204a1d9bbed232da24ea0'),
}
OLD_MAP_SHA = '3dbbdce3e71a5e1e6d77a81d1be9338a37c4530128b7442e6fa4e48551ba5464'
OLD_WORKLIST_SHA = 'bcddead36b21313b9a7991c6c1da784b582a29380cc8ed0c184b941b7e284c53'
OLD_UI_SHA = '2fe530371d479d180f787c91772adfb77f32eaacfac64f31d2807cc53cd15ac3'
INIT_SHA = 'd66a88023e93c3db64f1b64cfaf8089d4c956adc0f97896c591e34a54d8e4dd2'
NATIVE_SHA = 'c5f2aa055c43d97afbe057498041e5a01d59002ebb99c271f1438f5d03a150ea'
UI_SHA = 'e57c2f51b072ca1aa949d80fcec57265a91edf053f60bc34a9d5e396c0c44a9c'
CORE_SHA = 'd4de3eff83abd01e74ec7c92a67ea62be0314cda757cc83ac2663e9308b13aad'
ATTACH_TEST_SHA = 'be52410c4c954d5ec9b80424b1deb350355230d3db2f3daf19510a2700c95b8f'
EDITING_TEST = 'test_animation_worklist_rigging_editing_data.py'
ATTACH_TEST = 'test_animation_worklist_rigging_attach.py'
UI_TEST = 'test_animation_worklist_rigging_attach_ui.py'
EDITING_TEST_SHA = 'f53bcee59ca3845a0567e414cd024b010d18ba10996777d86e1103033de26f68'
UI_TEST_SHA = 'd7f6444b640f8d057aa8657f32a50653832b092a0223bb2ba4e4a690151fabd9'
SOURCE_NAMES = {'animation_worklist.py', 'animation_worklist_ui.py', EDITING_TEST, ATTACH_TEST, UI_TEST}
ADDED_SOURCE_NAMES = {'animation_worklist_ui.py', EDITING_TEST, ATTACH_TEST, UI_TEST}
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
    require(expected is None or isinstance(expected, str)
            and re.fullmatch('[0-9a-f]{64}', expected) and sha(raw) == expected,
            'Changed Source pin: ' + str(path))
    return {'path': str(path), 'sha256': sha(raw), 'bytes': len(raw)}


def exact(row):
    require(isinstance(row, dict) and set(row) == {'path', 'sha256', 'bytes'}
            and type(row['bytes']) is int and row['bytes'] >= 0
            and record(row['path'], row['sha256']) == row, 'An exact three-field Source pin changed.')
    return row


def source_path(name):
    return REPO / ('tests' if name.startswith('test_') else 'addons/character_designer') / name


def source_rows(doc):
    rows = doc.get('source_files', doc.get('source_pins'))
    if isinstance(rows, list):
        rows = {Path(row['path']).name: row for row in rows}
    require(isinstance(rows, dict) and bool(rows), 'A real Source receipt must bind its source_files.')
    for name, row in rows.items():
        require(Path(row['path']).name == name, 'Ambiguous Source receipt name: ' + name)
    return rows


def verify_source_proof(row, current, required, *, peer=False):
    pin = exact(row)
    doc = json.loads(Path(pin['path']).read_bytes())
    schema = doc.get('schema')
    ui_ready = schema == 'x.validation.prepared-rigging-attach-ui-source-owner/1'
    root_review = schema == 'x.validation.original-rigging-attach-root-source-peer/1'
    ordinary_source_flags = doc.get('source_only') is True and doc.get('native_execution_performed') is False
    ui_source_flags = ui_ready and doc['limits']['native_execution'] is False and doc['ownership']['writer_complete'] is True
    root_source_flags = root_review and doc['scope_verified'] is True and all(
        type(value) is int and value == 0 for value in doc['actual_run_counts'].values())
    scope_complete = (doc.get('passed') is True or doc.get('source_scope_verified') is True
        or doc.get('scope_verified') is True or ui_source_flags)
    require(isinstance(schema, str) and schema.endswith('/1') and scope_complete
            and (ordinary_source_flags or ui_source_flags or root_source_flags),
            'A real closed Source-scope owner/peer is mandatory: ' + pin['path'])
    # A Source-scope receipt with passed=false retains that value. It is never
    # treated as a test PASS: separate actual_pure_receipt gates below are required.
    bound = source_rows(doc)
    require(required <= set(bound), 'Final Source proof omits required current files.')
    for name in required:
        require(exact(bound[name]) == current[name], 'Final Source proof is stale: ' + name)
    if peer:
        require(root_source_flags or doc.get('independent_review') is True or doc.get('reviewer_test_executions') == 0
                or doc.get('reviewer_boundaries', {}).get('product_edits') == 0,
                'The Source peer must report independent read-only review, not inherited owner PASS.')
    return pin


def file_map(source):
    return {path.as_posix(): sha(raw) for path, raw in sorted(source.files.items())}


def map_sha(files):
    return sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def archive_matches(archive, source):
    payload = {'character_designer/' + path.as_posix(): raw for path, raw in source.files.items()}
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        require(zipped.testzip() is None and len(entries) == 188
                and len({entry.filename for entry in entries}) == 188
                and not any(entry.is_dir() for entry in entries), 'ZIP CRC/duplicate/full-entry check failed.')
        require({entry.filename: zipped.read(entry) for entry in entries} == payload,
                'Every ZIP byte must equal the manifest.')


def actual_pure_receipt(row, current, expected_files):
    pin = exact(row)
    doc = json.loads(Path(pin['path']).read_bytes())
    require(doc['schema'] == 'x.validation.r7-actual-serial-pure/1'
            and doc['passed'] is True and doc['source_only'] is True
            and doc['native_execution_performed'] is False and doc['actual_run'] is True
            and doc['source_pins_unchanged_after_run'] is True
            and type(doc['process_exit_code']) is int and doc['process_exit_code'] == 0
            and doc['execution_mode'] == 'SERIAL_PYTHON_B',
            'A completed actual serial pure run is required, not a prepared test or guessed PASS.')
    sources = source_rows(doc)
    require(expected_files <= set(sources), 'The actual pure receipt omits its current Source domain.')
    for name in expected_files:
        require(exact(sources[name]) == current[name], 'Pure execution source is not final: ' + name)
    suites = {}
    require(isinstance(doc['suites'], list) and bool(doc['suites']), 'Actual suite results are required.')
    for suite in doc['suites']:
        name = suite['file']
        require(name not in suites and Path(name).name == name and name.startswith('test_')
                and name.endswith('.py'), 'Duplicate/unsafe actual suite name.')
        require(exact(suite['test_file']) == record(source_path(name)), 'Actual suite test Source changed.')
        require(type(suite['total']) is int and suite['total'] > 0
                and type(suite['passed']) is int and suite['passed'] == suite['total']
                and type(suite['failed']) is int and suite['failed'] == 0
                and type(suite['exit_code']) is int and suite['exit_code'] == 0
                and type(suite['actual_executions']) is int and suite['actual_executions'] >= 1
                and type(suite['unique_new_cases']) is int and 0 <= suite['unique_new_cases'] <= suite['total'],
                'Every counted suite must be an actual complete PASS with explicit unique-case attribution.')
        require(exact(suite['raw_log'])['bytes'] > 0, 'An actual suite must retain a nonempty raw execution log.')
        suites[name] = suite
    require(type(doc['process_test_total']) is int
            and doc['process_test_total'] == sum(suite['total'] for suite in suites.values())
            and exact(doc['process_raw_log'])['bytes'] > 0,
            'Actual process totals must equal the completed suites and bind a nonempty raw log.')
    return pin, suites


def inputs(args):
    provenance = {name: record(path, digest) for name, (path, digest) in BASELINE.items()}
    provenance.update(producer=record(__file__),
        official_resolver=record(REPO / 'tools/release_projection.py', '052e6c765c95ba46d480bf1eeca1e1dccb7685c77a4e756202ce409d20713106'),
        official_builder=record(REPO / 'tools/build_releases.py', '30759e923bde1da595f5cd9f67dd9d6f866ebb2866eb4c5f5b1747628e2872c1'),
        final_admission=record(args.final_admission, args.final_admission_sha256.lower()))
    admission = json.loads(Path(provenance['final_admission']['path']).read_bytes())
    require(admission['schema'] == 'x.validation.unified-r7-final-source-admission/1'
            and admission['passed'] is True and admission['source_only'] is True
            and admission['native_execution_performed'] is False
            and admission['final_source_stable'] is True
            and admission['final_destination_existing_X_Rig'] is True,
            'Final Root/Parent admission must be complete and real; placeholders/drafts are not admitted.')
    current = admission['current_sources']
    require(set(current) == SOURCE_NAMES, 'Exactly the five final feature Source/test pins are required.')
    for name, row in current.items():
        require(exact(row) == record(source_path(name)), 'Final canonical Source path/bytes differs: ' + name)
    require(current['animation_worklist_ui.py']['sha256'] == UI_SHA
            and current['animation_worklist_ui.py']['bytes'] == 43229
            and current[EDITING_TEST]['sha256'] == EDITING_TEST_SHA and current[EDITING_TEST]['bytes'] == 14112
            and current[UI_TEST]['sha256'] == UI_TEST_SHA and current[UI_TEST]['bytes'] == 16155
            and current['animation_worklist.py']['sha256'] == CORE_SHA and current['animation_worklist.py']['bytes'] == 53135
            and current[ATTACH_TEST]['sha256'] == ATTACH_TEST_SHA and current[ATTACH_TEST]['bytes'] == 30907,
            'The final combined Attach core and fixed e57 UI/f53 editing/d7 UI test pins must be exact.')
    require(set(admission['source_owners']) == {'core', 'ui'}
            and set(admission['source_peers']) == {'root', 'parent'},
            'Real final core/UI owners and both Root/Parent Source peers are mandatory.')
    provenance['final_core_owner'] = verify_source_proof(admission['source_owners']['core'], current,
        {'animation_worklist.py', ATTACH_TEST})
    provenance['final_ui_owner'] = verify_source_proof(admission['source_owners']['ui'], current,
        {'animation_worklist_ui.py', UI_TEST})
    provenance['final_root_peer'] = verify_source_proof(admission['source_peers']['root'], current,
        SOURCE_NAMES - {EDITING_TEST}, peer=True)
    provenance['final_parent_peer'] = verify_source_proof(admission['source_peers']['parent'], current,
        {'animation_worklist.py', ATTACH_TEST}, peer=True)
    require(set(admission['pure_receipts']) == {'core', 'ui'}, 'Actual final core/UI pure receipts are mandatory.')
    provenance['actual_core_pure'], core_suites = actual_pure_receipt(admission['pure_receipts']['core'], current,
        {'animation_worklist.py', ATTACH_TEST, EDITING_TEST})
    provenance['actual_ui_pure'], ui_suites = actual_pure_receipt(admission['pure_receipts']['ui'], current,
        {'animation_worklist.py', 'animation_worklist_ui.py', UI_TEST})
    require(set(core_suites) == {ATTACH_TEST, EDITING_TEST, 'test_animation_worklist.py'}
            and set(ui_suites) == {UI_TEST, 'test_animation_worklist_ui.py'},
            'Actual core19+7+15 and UI14+68 suite receipts must all be present, with no omitted or extra suite.')
    attach = core_suites[ATTACH_TEST]
    require(attach['total'] == attach['unique_new_cases'] == 19,
            'Final Attach nineteen-case count must come from the actual finished suite, not an earlier draft.')
    require(ui_suites[UI_TEST]['total'] == ui_suites[UI_TEST]['unique_new_cases'] == 14
            and ui_suites['test_animation_worklist_ui.py']['total'] == 68
            and ui_suites['test_animation_worklist_ui.py']['unique_new_cases'] == 0
            and core_suites[EDITING_TEST]['total'] == 7 and core_suites[EDITING_TEST]['unique_new_cases'] == 0
            and core_suites['test_animation_worklist.py']['total'] == 15
            and core_suites['test_animation_worklist.py']['unique_new_cases'] == 0
            and sum(suite['total'] for suite in core_suites.values()) == 41
            and sum(suite['total'] for suite in ui_suites.values()) == 82,
            'Focused UI adds fourteen and Attach adds nineteen; existing UI/worklist/editing regressions add no unique cases.')
    allowed_new = {ATTACH_TEST: attach['total'], UI_TEST: 14}
    for name, suite in {**core_suites, **ui_suites}.items():
        require(suite['unique_new_cases'] == allowed_new.get(name, 0), 'Unexpected or duplicate new-case attribution.')
    if EDITING_TEST in core_suites:
        require(core_suites[EDITING_TEST]['total'] == 7, 'A current editing-data regression rerun must retain its seven cases.')
    unique_tests = 262 + 7 + attach['unique_new_cases'] + 14
    require(admission['unique_cases'] == {'historical_R5': 262, 'historical_80af_editing': 7,
            'actual_final_Attach': attach['unique_new_cases'], 'actual_final_UI': 14,
            'regression_unique_additions': 0, 'cumulative_total': unique_tests,
            'all_cumulative_cases_run_against_current_candidate': False},
            'Cumulative unique totals must match the actual receipts and never claim a full current rerun.')
    old = json.loads(OLD_FREEZE.read_bytes())
    require(old['schema'] == 'cdesigner.x-rigging-source-freeze/1' and len(old['source_pins']) == 19
            and old['pure_tests_total'] == sum(row['tests'] for row in old['pure_tests']) == 262,
            'Immutable R5 nineteen-pin/262-unique ancestry changed.')
    r5_receipt = json.loads(Path(provenance['r5_receipt']['path']).read_bytes())
    readback = json.loads(Path(provenance['r5_readback']['path']).read_bytes())
    require(r5_receipt['native_acceptance'] is False and r5_receipt['source_pin_count'] == 19
            and r5_receipt['file_count'] == 188 and r5_receipt['syntax_python_files'] == 156
            and r5_receipt['unique_pure_tests'] == 262 and r5_receipt['complete_file_map_sha256'] == OLD_MAP_SHA
            and readback['passed'] is True and readback['ZIP_entries'] == 188
            and readback['duplicates'] == 0 and readback['testzip'] == 'PASS'
            and readback['all_entry_bytes_equal_manifest'] is True,
            'R5 complete build evidence must remain exact and is not R7/native PASS.')
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
            and reference['test_result']['failed'] == 0 and recovery['passed'] is True
            and recovery['test_result']['total'] == 12 and recovery['test_result']['exit_code'] == 0,
            'Unchanged native c5 reference20/recovery12 actual pure receipts must remain historical and exact.')
    provenance['historical_reference20_log'] = exact(reference['test_result']['log_pin'])
    provenance['historical_recovery12_log'] = exact(recovery['test_result']['log_pin'])
    for proof in (reference, recovery):
        for name, row in proof['source_files'].items():
            require(exact(row) == record(source_path(name)), 'Historical unchanged native/test binding drifted: ' + name)
    historical_owner = json.loads(Path(provenance['historical_editing_owner']['path']).read_bytes())
    historical_peer = json.loads(Path(provenance['historical_editing_peer']['path']).read_bytes())
    historical_new = historical_owner['test_results']['new_pure']
    require(historical_owner['passed'] is True and historical_peer['passed'] is True
            and historical_new['total'] == historical_new['passed'] == 7 and historical_new['failed'] == 0
            and historical_new['exit_code'] == 0
            and historical_owner['source_files'][EDITING_TEST] == current[EDITING_TEST]
            and historical_owner['source_files']['animation_worklist.py']['sha256'] ==
                provenance['historical_80af_snapshot']['sha256'],
            'The seven historical 80af cases retain their actual provenance; they are not fabricated final-core PASS.')
    provenance['historical_editing7_log'] = exact(historical_new['raw_log'])
    require(exact(historical_peer['owner_source_report']) == provenance['historical_editing_owner'],
            'Historical 80af independent peer/owner binding changed.')
    ui_draft = json.loads(Path(provenance['ui_source_ready_not_test_pass']['path']).read_bytes())
    require(ui_draft['status'] == 'SOURCE_READY_PURE_CHECKS_PENDING'
            and ui_draft['pending_pure_checks']['execution_count'] == 0,
            'Original unexecuted UI-ready evidence must remain pending; final PASS comes only from separate actual runs.')
    failure = json.loads(Path(provenance['r5_actual_failed_report']['path']).read_bytes())
    closure = json.loads(Path(provenance['r5_actual_failed_closure']['path']).read_bytes())
    require(failure['completed'] is False and failure['phase'] == 'failed_no_retry_or_publication'
            and failure['failure_phase'] == 'add_activate' and bool(failure['traceback'])
            and failure['original_Rig_acceptance'] is False and failure['Sync_performed'] is False
            and failure['worker_performed'] is False and 'roll-decoupled hierarchy was edited' in failure['error'],
            'Actual R5 native FAIL and full traceback must remain unchanged.')
    require(closure['status'] == 'ACTUAL_RELEASE' and closure['actual_native_result'] == 'FAIL'
            and closure['failure_phase'] == 'add_activate' and closure['retained_handle_natural_exit'] is True
            and closure['native_exit_code'] == 0 and closure['owned_pid'] == 55952
            and closure['owned_native_gone'] is True and closure['process_termination_performed'] is False
            and exact(closure['control_report']) == provenance['r5_actual_failed_report'],
            'Actual failure-scene/natural-exit closure is mandatory; its old token grants no new resource window.')
    provenance['r5_actual_launcher'] = exact(closure['launch_receipt'])
    require(provenance['r5_actual_launcher']['sha256'] == '6dc3e895e3e31eaa294c66603deb5e18db27f5e6a25761e37b396e7199ec48d7',
            'Actual retained-handle launcher pin changed.')
    provenance['r5_saved_failure_scene'] = exact({key: closure['failure_snapshot'][key] for key in ('path', 'sha256', 'bytes')})
    require(closure['failure_snapshot']['Blender_saved_notification_observed'] is True,
            'The owned failed scene must remain durably saved with Blender success evidence.')
    launcher = json.loads(Path(provenance['r5_actual_launcher']['path']).read_bytes())
    require(launcher['completed'] is False and launcher['natural_exit_verified'] is True
            and launcher['all_owned_Blender_processes_gone'] is True
            and launcher['artist_opened_or_saved'] is False and launcher['process_termination_performed'] is False
            and launcher['protected_files_after'] == {name: launcher['inputs'][name]
                for name in ('protected_artist', 'protected_workspace')}
            and launcher['artist_process_before'] == launcher['artist_process_after'],
            'Original artist disk/process guard evidence must remain exact and historical.')
    provenance['r5_launcher_stdout'] = exact(launcher['stdout'])
    provenance['r5_launcher_stderr'] = exact(launcher['stderr'])
    paths = {Path(row['path']).name: (Path(row['path']), row) for row in old['source_pins']}
    require(len(paths) == 19 and not ADDED_SOURCE_NAMES.intersection(paths), 'R5 Source-pin subset changed.')
    for name in ADDED_SOURCE_NAMES:
        paths[name] = (source_path(name), None)
    updated = []
    for name, (path, previous) in sorted(paths.items()):
        pin = record(path)
        expected = current.get(name, {key: previous[key] for key in ('path', 'sha256', 'bytes')} if previous else None)
        require(pin == expected, 'Unauthorized Source-pin delta: ' + name)
        compile(ast.parse(path.read_bytes(), filename=str(path)), str(path), 'exec')
        updated.append({**pin, 'syntax': 'PASS'})
    require(len(updated) == 23, 'R7 expects nineteen R5 pins plus four added feature Source/test pins.')
    prior = load_source('character_designer', OLD_PACKAGE / 'python_projection.json', root=REPO)
    captured = load_source('character_designer', root=REPO)
    previous_hashes, hashes = file_map(prior), file_map(captured)
    require(map_sha(previous_hashes) == OLD_MAP_SHA and len(hashes) == len(previous_hashes) == 188
            and set(hashes) == set(previous_hashes) and prior.version == captured.version == '0.77.25'
            and hashes['__init__.py'] == INIT_SHA and hashes['unity_animation_rigging.py'] == NATIVE_SHA,
            'Complete R5/R7 set/version/native c5/init d66 differs from the approved scope.')
    require({name for name in hashes if hashes[name] != previous_hashes[name]} ==
                {'animation_worklist.py', 'animation_worklist_ui.py'}
            and previous_hashes['animation_worklist.py'] == OLD_WORKLIST_SHA
            and previous_hashes['animation_worklist_ui.py'] == OLD_UI_SHA
            and hashes['animation_worklist.py'] == current['animation_worklist.py']['sha256']
            and hashes['animation_worklist_ui.py'] == UI_SHA,
            'Exactly two R5 shipped deltas are admitted; all other 186 payload files must remain exact.')
    archive_matches(OLD_PACKAGE / 'character_designer-0.77.25.zip', prior)
    python_count = 0
    for name, raw in captured.files.items():
        if name.suffix == '.py':
            compile(ast.parse(raw, filename=name.as_posix()), name.as_posix(), 'exec')
            python_count += 1
    require(python_count == 156, 'Expected the complete 156-Python candidate.')
    return {'old': old, 'updated': updated, 'captured': captured, 'hashes': hashes,
        'provenance': provenance, 'admission': admission, 'current': current,
        'core_suites': core_suites, 'ui_suites': ui_suites, 'unique_tests': unique_tests}


def targets(state):
    package = ROUND / ('package_' + map_sha(state['hashes'])[:8])
    freeze = ROOT / ('x_rigging_source_freeze_r7_' + state['current']['animation_worklist.py']['sha256'][:8] + '.json')
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
    require(not package.exists() and not freeze.exists(), 'Use unique new R7 outputs.')
    frozen = deepcopy(state['old'])
    frozen.update(created_utc=datetime.now(timezone.utc).isoformat(), source_only=True,
        native_execution_performed=False, source_pins=state['updated'], pure_tests_total=state['unique_tests'],
        previous_source_freeze=state['provenance']['r5_freeze'], r7_source_provenance=state['provenance'],
        final_source_admission=state['admission'], source_delta={
            'prior_pins_changed': ['animation_worklist.py'], 'prior_pins_unchanged': 18,
            'added_pins': sorted(ADDED_SOURCE_NAMES), 'source_pin_count': 23,
            'runtime_replaced': ['animation_worklist.py', 'animation_worklist_ui.py'],
            'runtime_added': [], 'other_186_payload_files_unchanged': True},
        syntax_compilation={'source_files': 23, 'python_payload_files': 156, 'result': 'PASS', 'target_imports': 0},
        cumulative_case_attribution=state['admission']['unique_cases'],
        actual_R5_native_failure={'result': 'FAIL', 'phase': 'add_activate',
            'report': state['provenance']['r5_actual_failed_report'],
            'closure': state['provenance']['r5_actual_failed_closure'],
            'saved_scene': state['provenance']['r5_saved_failure_scene'], 'R7_native_success_inferred': False},
        final_destination='Existing original X.blend/Rig preserving modifiers, design, materials, colors, Bone Collections, custom shapes and controllers; new scenes only isolated tests.')
    for row in frozen['pure_tests']:
        row.update(executions_by_this_producer=0,
            r7_evidence_scope='Carried exact historical evidence; not a current full-suite execution by this producer.')
    for name, count, evidence in ((EDITING_TEST, 7, 'historical_editing_owner'),
            (ATTACH_TEST, state['core_suites'][ATTACH_TEST]['unique_new_cases'], 'actual_core_pure'),
            (UI_TEST, 14, 'actual_ui_pure')):
        frozen['pure_tests'].append({'file': name, 'tests': count, 'result': 'PASS', 'native': False,
            'provenance': state['provenance'][evidence], 'executions_by_this_producer': 0,
            'evidence_scope': 'Historical 80af seven-case evidence.' if name == EDITING_TEST else
                'Actual final Source-bound pure receipt; no native/artist/publication proof.'})
    require(sum(row['tests'] for row in frozen['pure_tests']) == state['unique_tests'], 'Unique test arithmetic changed.')
    frozen['limitations'] += [
        'R7 supersedes the unbuilt only80af R6 preparation; R6 inspect/claim is not R7 PASS or native authorization.',
        'Exactly animation_worklist.py and animation_worklist_ui.py differ from the immutable R5 complete188 package; native c5/init d66/version0.77.25 remain exact.',
        'Cumulative pure count is262 historical+7 historical80af+actual final Attach new cases+14 final UI cases; regression reruns add zero and no full current rerun is claimed.',
        'R5 actual Add failed before edit/Undo/reopen/reference/Sync. Its full report, saved failure Scene and natural-exit closure remain FAIL.',
        'Final integration must use the existing original X.blend/Rig, preserving all artist modifiers/design/display/control assets. Factory scenes only validate isolated mechanisms.',
        'Attach does not silently rebind old workspace/rows, alter target/model/Rest/weights, repair hierarchy, or establish original artist/solver/physical return/Unity Apply acceptance.',
        'Historical resource release and any Source PASS grant no new native/SDK/deployment resource scope.']
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
            'purpose': 'Source-only original-Rig prepared Attach and preserved translation-domain successor; native pending',
            'source_freeze': record(freeze), 'previous_candidate': state['provenance']['r5_manifest'],
            'complete_file_map_sha256': map_sha(state['hashes']), 'producer': state['provenance']['producer'],
            'final_admission': state['provenance']['final_admission'], 'local_source_no_bump': True,
            'native_acceptance': False, 'deployment_authorized': False, 'final_destination_existing_X_Rig': True}}
    write_new(manifest_path, encoded(manifest), freeze)
    require(load_source('character_designer', manifest_path, root=REPO).files == state['captured'].files,
            'Frozen complete payload differs from captured bytes.')
    print(json.dumps({'freeze': record(freeze), 'manifest': record(manifest_path),
        'file_map_sha256': map_sha(state['hashes']), 'files': 188, 'python_files': 156,
        'source_pins': 23, 'cumulative_unique_pure_tests': state['unique_tests'],
        'tests_executed_by_this_producer': 0, 'native_acceptance': False}))


def build_and_verify(state):
    package, freeze, source_root, manifest_path = targets(state)
    manifest = json.loads(manifest_path.read_bytes())
    require(exact(manifest['source_provenance']['source_freeze']) == record(freeze)
            and exact(manifest['source_provenance']['producer']) == state['provenance']['producer']
            and exact(manifest['source_provenance']['final_admission']) == state['provenance']['final_admission'],
            'Frozen receipt/producer/final admission changed after capture.')
    frozen = json.loads(freeze.read_bytes())
    require(frozen['source_pins'] == state['updated'] and frozen['pure_tests_total'] == state['unique_tests']
            and frozen['r7_source_provenance'] == state['provenance'], 'Admitted R7 Source receipt changed.')
    require(load_source('character_designer', manifest_path, root=REPO).files == state['captured'].files,
            'Canonical/frozen bytes changed before the official build.')
    archive_literal, dist_literal = REPO / 'dist/character_designer-0.77.25.zip', REPO / 'dist'
    archive, archived, dist = archive_literal.resolve(), ARCHIVED_DIST.resolve(), dist_literal.resolve()
    require(archive.is_relative_to(dist) and archived.is_relative_to(dist) and dist.is_relative_to(REPO.resolve())
            and not any(path.is_symlink() or getattr(path, 'is_junction', lambda: False)()
                for path in (archive_literal, dist_literal, ARCHIVED_DIST.parent))
            and not archived.exists(), 'Resolved move targets must stay inside dist without overwrite/reparse.')
    old_zip_sha = BASELINE['r5_archive'][1]
    prior_dist = record(archive, old_zip_sha)
    require(archive.read_bytes() == (OLD_PACKAGE / archive.name).read_bytes(), 'R5 dist/frozen ZIP bytes differ.')
    archived.parent.mkdir(parents=True, exist_ok=True)
    archive.rename(archived)
    require(not archive.exists() and record(archived, old_zip_sha)['bytes'] == prior_dist['bytes'],
            'Verified normal R5 dist relocation did not finish.')
    command = [sys.executable, '-B', str(REPO / 'tools/build_releases.py'), '--module',
        'character_designer', '--projection', str(manifest_path)]
    result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False, shell=False)
    write_new(package / 'official_build_log.json', encoded({'command': command, 'exit_code': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr}), freeze)
    require(result.returncode == 0, 'Official local build failed; retain its log and all old evidence.')
    archive_matches(archive, state['captured'])
    frozen_archive = package / archive.name
    write_new(frozen_archive, archive.read_bytes(), freeze)
    receipt = {'schema': 'cdesigner.unified-source-candidate/1', 'status': 'SOURCE_FROZEN_NATIVE_PENDING',
        'source_only': True, 'native_execution_performed': False, 'native_acceptance': False,
        'version': '0.77.25', 'manifest': record(manifest_path), 'source_root': str(source_root),
        'source_freeze': record(freeze), 'source_pin_count': 23, 'file_count': 188,
        'complete_file_map_sha256': map_sha(state['hashes']), 'syntax_python_files': 156,
        'source_bytes': sum(len(raw) for raw in state['captured'].files.values()),
        'unique_pure_tests': state['unique_tests'], 'tests_executed_by_this_producer': 0,
        'all_cumulative_cases_run_against_current_candidate': False,
        'candidate_provenance': state['provenance'], 'cumulative_case_attribution': state['admission']['unique_cases'],
        'runtime_R5_deltas': ['animation_worklist.py', 'animation_worklist_ui.py'],
        'other_186_payload_files_unchanged': True, 'native_c5_init_d66_exact': True,
        'old_dist_relocation': {'original_path': str(archive), 'archived': record(archived, old_zip_sha),
            'old_frozen_copy': state['provenance']['r5_archive'], 'bytes_equal': True},
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


def inspect_only(state):
    package, freeze, _, manifest = targets(state)
    print(json.dumps({'status': 'FINAL_SOURCE_INSPECTED_CAPTURE_BUILD_NATIVE_NOT_EXECUTED',
        'producer': state['provenance']['producer'], 'final_admission': state['provenance']['final_admission'],
        'proposed_package': str(package), 'proposed_freeze': str(freeze), 'proposed_manifest': str(manifest),
        'complete_file_map_sha256': map_sha(state['hashes']), 'source_pins': 23,
        'runtime_files': 188, 'python_files': 156,
        'runtime_R5_deltas': ['animation_worklist.py', 'animation_worklist_ui.py'],
        'other_186_payload_files_unchanged': True, 'cumulative_unique_pure_tests': state['unique_tests'],
        'cumulative_case_attribution': state['admission']['unique_cases'],
        'tests_executed_by_this_producer': 0, 'actual_R5_native_result': 'FAIL',
        'native_acceptance': False, 'final_destination_existing_X_Rig': True,
        'new_native_resource_authorization_inferred': False,
        'capture': 0, 'build': 0, 'deploy': 0, 'native': 0, 'SDK': 0, 'workers': 0, 'artist_writes': 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--inspect-only', action='store_true')
    mode.add_argument('--capture', action='store_true')
    mode.add_argument('--build-and-verify', action='store_true')
    parser.add_argument('--final-admission', required=True)
    parser.add_argument('--final-admission-sha256', required=True)
    args = parser.parse_args()
    state = inputs(args)
    if args.inspect_only:
        inspect_only(state)
    elif args.capture:
        capture(state)
    else:
        build_and_verify(state)


if __name__ == '__main__':
    main()
