"""Unexecuted Source preparation for one Root-owned serial pure phase.

Core: 19 + 7 + 15. UI: 14 + 68. Every suite gets a fresh bundled Python -B.
The same approved ResourceStart can subsequently authorize the separate
original SaveCopy caller; this runner never imports/calls SDK, bpy or a worker.
"""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


ROUND = Path(__file__).resolve().parent
REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
PYTHON = Path(r'C:\Users\Randy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
OWNER_THREAD = '01a12751-d08f-7630-b790-18db26fe3186'
PARENT_THREAD = '01a12305-aada-7273-b72c-54a41aad77e4'
EXPECTED = {
    'animation_worklist.py': ('d4de3eff83abd01e74ec7c92a67ea62be0314cda757cc83ac2663e9308b13aad', 53135),
    'animation_worklist_ui.py': ('e57c2f51b072ca1aa949d80fcec57265a91edf053f60bc34a9d5e396c0c44a9c', 43229),
    'test_animation_worklist_rigging_attach.py': ('be52410c4c954d5ec9b80424b1deb350355230d3db2f3daf19510a2700c95b8f', 30907),
    'test_animation_worklist_rigging_editing_data.py': ('f53bcee59ca3845a0567e414cd024b010d18ba10996777d86e1103033de26f68', 14112),
    'test_animation_worklist_rigging_attach_ui.py': ('d7f6444b640f8d057aa8657f32a50653832b092a0223bb2ba4e4a690151fabd9', 16155),
    'test_animation_worklist.py': ('9242405a9c48f6dbec061670e9dc4b0cbd11f6ddc9b83746c9958e309aeded55', 17877),
    'test_animation_worklist_ui.py': ('c30dbe9ef756c85444f2a80cc8cccfde33a9af1fde73ce5862d542269ca2df1c', 66049),
}
SUITES = {
    'core': [('test_animation_worklist_rigging_attach.py', 19, 19),
             ('test_animation_worklist_rigging_editing_data.py', 7, 0),
             ('test_animation_worklist.py', 15, 0)],
    'ui': [('test_animation_worklist_rigging_attach_ui.py', 14, 14),
           ('test_animation_worklist_ui.py', 68, 0)],
}
FORBIDDEN_FLAGS = ('worker_allowed', 'native_allowed', 'new_blender_allowed',
                   'build_allowed', 'install_allowed', 'deploy_allowed', 'artist_disk_write_allowed')

# Audit guards run in each fresh child before unittest imports its one suite.
# Fake modules supplied by the tests remain usable. Real application imports,
# package registration and process launches fail as actual test errors.
BOOTSTRAP = r'''
import os, pathlib, sys, unittest
repo = pathlib.Path(sys.argv[1]).resolve()
product_init = (repo / 'addons/character_designer/__init__.py').resolve()
def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.exec',
                 'os.spawn', 'os.startfile', 'os.startfile/2', 'socket.connect'):
        raise RuntimeError('Pure suite forbids application/process launch: ' + event)
    if event == 'import' and args[0] in ('bpy', 'mathutils') and args[0] not in sys.modules:
        raise RuntimeError('Pure suite forbids real native import: ' + args[0])
    if event == 'exec':
        name = args[0].co_filename
        if name and not name.startswith('<'):
            path = pathlib.Path(name).resolve()
            if path == product_init or path.name == '__init__.py' and path.parent.name == 'character_designer':
                raise RuntimeError('Pure suite forbids add-on __init__/registration')
            if 'character_designer' in path.parts and not path.is_relative_to(repo / 'addons/character_designer'):
                raise RuntimeError('Pure suite forbids another candidate source import')
sys.addaudithook(audit)
sys.argv = ['unittest', '-v', sys.argv[2]]
unittest.main(module=None)
'''


def require(value, message):
    if not value:
        raise RuntimeError(message)


def utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def utc_value(value):
    require(isinstance(value, str) and re.fullmatch(
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z', value), 'An explicit UTC-Z timestamp is required.')
    return datetime.fromisoformat(value[:-1] + '+00:00')


def pin(path, expected=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    require(expected is None or re.fullmatch('[0-9a-f]{64}', expected) and digest == expected,
            'Pinned Source/ResourceStart changed: ' + str(path))
    return {'path': str(path), 'sha256': digest, 'bytes': len(raw)}


def source_pins():
    rows = {}
    for name, (digest, size) in EXPECTED.items():
        path = REPO / ('tests' if name.startswith('test_') else 'addons/character_designer') / name
        rows[name] = pin(path, digest)
        require(rows[name]['bytes'] == size, 'Pinned Source length changed: ' + name)
    return rows


def write_json(path, doc, *, first=False):
    with Path(path).open('x' if first else 'w', encoding='utf-8', newline='\n') as stream:
        json.dump(doc, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def memory():
    require(os.name == 'nt', 'The approved Windows resource reader is required.')
    class Status(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                    ('total_phys', ctypes.c_ulonglong), ('avail_phys', ctypes.c_ulonglong),
                    ('total_page', ctypes.c_ulonglong), ('avail_page', ctypes.c_ulonglong),
                    ('total_virtual', ctypes.c_ulonglong), ('avail_virtual', ctypes.c_ulonglong),
                    ('avail_extended_virtual', ctypes.c_ulonglong)]
    status = Status(); status.length = ctypes.sizeof(status)
    require(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)), 'Actual RAM read failed.')
    used = 100.0 * (status.total_phys - status.avail_phys) / status.total_phys
    return {'utc': utc(), 'available_mib': status.avail_phys / (1024 * 1024),
            'used_percent': used, 'total_bytes': status.total_phys}


def resource_gate(start_pin, start, report, phase):
    require(pin(start_pin['path'], start_pin['sha256']) == start_pin, 'ResourceStart bytes changed.')
    require(datetime.now(timezone.utc) < utc_value(start['deadline_utc']), 'The Parent-approved window expired.')
    rows = [memory()]
    if rows[0]['available_mib'] < 200 or rows[0]['used_percent'] >= 97.5:
        time.sleep(5)
        rows.append(memory())
    report['resource_reads'].append({'phase': phase, 'reads': rows, 'serial': True})
    require(rows[-1]['available_mib'] >= 200, 'Below 200 MiB; no additional suite was started.')
    require(datetime.now(timezone.utc) < utc_value(start['deadline_utc']), 'The fresh reread consumed the window.')


def admission(args):
    require(Path(sys.executable).resolve() == PYTHON.resolve(), 'Use the verified bundled Python -B.')
    require(sys.dont_write_bytecode is True, 'The helper itself must be invoked with -B.')
    require(re.fullmatch('[0-9a-f]{64}', args.resource_start_sha256)
            and isinstance(args.scope_owner_token, str) and 0 < len(args.scope_owner_token) <= 128,
            'Exact ResourceStart SHA and explicit owner token are required.')
    start_pin = pin(args.resource_start, args.resource_start_sha256)
    start = json.loads(Path(start_pin['path']).read_bytes())
    require(start['schema'] == 'x.validation.resource-start/1'
            and start['scope'] in ('original-rig-current-pure-checks', 'latest-original-artist-savecopy')
            and start['owner'] == 'Root'
            and start['status'] == 'ACTUAL_START' and start['token'] == args.scope_owner_token
            and start['owner_thread'] == OWNER_THREAD and start['parent_thread'] == PARENT_THREAD
            and start['pure_allowed'] is True
            and all(start[field] is False for field in FORBIDDEN_FLAGS),
            'A fresh explicit Root ACTUAL_START must authorize only this pure phase; no app/worker/build/artist writes.')
    if start['scope'] == 'original-rig-current-pure-checks':
        require(start['sdk_allowed'] is False, 'The pure-only window cannot authorize SDK calls.')
    created = utc_value(start['created_utc']); deadline = utc_value(start['deadline_utc'])
    now = datetime.now(timezone.utc)
    require(start['actual_start_utc'] == start['created_utc']
            and created <= now < deadline and 0 < (deadline - created).total_seconds() <= 210,
            'The actual fresh UTC start/deadline must stay within the approved 3.5-minute window.')
    output = Path(args.output_root).resolve()
    require(output != ROUND and ROUND in output.parents and not output.exists(),
            'Use a fresh exclusive evidence directory under this owned ROUND.')
    require(not Path(start_pin['path']).is_relative_to(output), 'ResourceStart is immutable input, not mutable output.')
    sources = source_pins()
    return start_pin, start, output, sources


def outcome(stdout, stderr, code, expected):
    # unittest writes its authoritative result to stderr. A fixture's stdout
    # is retained separately and cannot supply a forged result summary.
    text = stderr.decode('utf-8', errors='replace')
    counts = re.findall(r'^Ran (\d+) tests? in ([0-9]+(?:\.[0-9]+)?)s\s*$', text, re.MULTILINE)
    total = int(counts[0][0]) if len(counts) == 1 else 0
    success = len(re.findall(r'^OK\s*$', text, re.MULTILINE)) == 1
    summary = re.findall(r'^(?:FAILED|OK) \(([^)]+)\)\s*$', text, re.MULTILINE)
    details = dict((name, int(value)) for name, value in re.findall(
        r'(failures|errors|skipped)=(\d+)', summary[0])) if len(summary) == 1 else {}
    failed = details.get('failures', 0) + details.get('errors', 0)
    skipped = details.get('skipped', 0)
    ok = (code == 0 and len(counts) == 1 and total == expected and success and skipped == 0
          and not re.search(r'^FAILED|^ERROR:', text, re.MULTILINE))
    known = len(counts) == 1 and (success or len(summary) == 1)
    return {'total': total, 'passed': max(0, total - failed - skipped) if known else 0,
            'failed': failed if known else None, 'skipped': skipped if known else None,
            'complete_ok': ok, 'unittest_duration_seconds': float(counts[0][1]) if len(counts) == 1 else None}


def run(args):
    start_pin, start, output, sources = admission(args)
    report = {'schema': 'x.validation.r7-actual-serial-pure/1', 'phase': args.phase,
        'passed': False, 'completed': False, 'source_only': True, 'native_execution_performed': False,
        'sdk_calls': 0, 'worker_launches': 0, 'blender_launches': 0, 'builds': 0, 'deployments': 0,
        'artist_disk_writes': 0, 'actual_run': False, 'execution_mode': 'SERIAL_PYTHON_B',
        'runner': pin(__file__), 'resource_start': start_pin, 'scope_owner_token': args.scope_owner_token,
        'source_files': sources, 'source_pins_unchanged_after_run': False,
        'started_utc': utc(), 'helper_pid': os.getpid(), 'suites': [], 'resource_reads': [],
        'process_test_total': 0, 'process_exit_code': None, 'process_raw_log': None,
        'natural_owned_children_gone': False, 'forced_termination_performed': False,
        'no_descendant_launch_audit_enforced': True,
        'aggregate_semantics': 'One helper phase launches one fresh Python per suite serially; process_test_total is the sum of completed child unittest Ran counts, not one combined unittest invocation.'}
    resource_gate(start_pin, start, report, 'before phase claim')
    claim_dir = ROUND / 'r7_serial_pure_claims'
    claim_dir.mkdir(exist_ok=True)
    if args.phase == 'ui':
        core_claim = json.loads((claim_dir / (start_pin['sha256'] + '.core.json')).read_bytes())
        core = json.loads(Path(core_claim['receipt_path']).read_bytes())
        require(core['phase'] == 'core' and core['resource_start'] == start_pin and core['passed'] is True
                and core['completed'] is True and core['natural_owned_children_gone'] is True
                and core['process_exit_code'] == 0 and core['process_test_total'] == 41,
                'This Start requires actual completed core before UI; an active/failed core is not reusable.')
    claim_path = claim_dir / (start_pin['sha256'] + '.' + args.phase + '.json')
    receipt_path = output / 'receipt.json'
    write_json(claim_path, {'runner': report['runner'], 'phase': args.phase, 'resource_start': start_pin,
        'scope_owner_token': args.scope_owner_token, 'claimed_utc': utc(), 'helper_pid': os.getpid(),
        'receipt_path': str(receipt_path)}, first=True)
    output.mkdir(exist_ok=False)
    write_json(receipt_path, report, first=True)
    handles = []
    jobs = []
    aggregate = bytearray()
    began = time.perf_counter()
    try:
        for name, expected, unique in SUITES[args.phase]:
            require(source_pins() == sources, 'Source drift before starting a suite.')
            resource_gate(start_pin, start, report, 'before ' + name)
            row = {'file': name, 'test_file': sources[name], 'expected_total': expected,
                   'unique_new_cases': unique, 'actual_executions': 0, 'pid': None,
                   'started_utc': None, 'exited_utc': None, 'exit_code': None,
                   'total': 0, 'passed': 0, 'failed': None, 'raw_log': None,
                   'natural_exit': False, 'forced_termination': False}
            report['suites'].append(row)
            stdout_path, stderr_path = output / (name + '.stdout.raw'), output / (name + '.stderr.raw')
            command = [str(PYTHON), '-B', '-c', BOOTSTRAP, str(REPO), Path(name).stem]
            row['argv'] = command
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
            suite_began = time.perf_counter()
            with stdout_path.open('xb') as stdout_file, stderr_path.open('xb') as stderr_file:
                child = subprocess.Popen(command, cwd=REPO / 'tests', env=env,
                    stdin=subprocess.DEVNULL, stdout=stdout_file, stderr=stderr_file)
                handles.append(child)
                jobs.append((child, row, stdout_path, stderr_path, expected, suite_began))
                row['pid'], row['actual_executions'], row['started_utc'] = child.pid, 1, utc()
                report['actual_run'] = True
                write_json(receipt_path, report)
                # Never kill a child on timeout or window expiry. Preserve its
                # PID, wait for natural exit, then refuse any further suite.
                while True:
                    try:
                        code = child.wait(timeout=1)
                        break
                    except subprocess.TimeoutExpired:
                        report['waiting_child_pid'] = child.pid
                        report['window_expired_while_waiting'] = datetime.now(timezone.utc) >= utc_value(start['deadline_utc'])
                        write_json(receipt_path, report)
                stdout_file.flush(); stderr_file.flush()
                os.fsync(stdout_file.fileno()); os.fsync(stderr_file.fileno())
            row['exited_utc'], row['exit_code'], row['natural_exit'] = utc(), code, True
            row['duration_seconds'] = time.perf_counter() - suite_began
            stdout, stderr = stdout_path.read_bytes(), stderr_path.read_bytes()
            raw_path = output / (name + '.combined.raw.log')
            with raw_path.open('xb') as stream:
                stream.write(stdout); stream.write(stderr); stream.flush(); os.fsync(stream.fileno())
            aggregate.extend(stdout); aggregate.extend(stderr)
            row.update(outcome(stdout, stderr, code, expected))
            row['stdout_raw'], row['stderr_raw'], row['raw_log'] = pin(stdout_path), pin(stderr_path), pin(raw_path)
            row['raw_log_stream_order'] = 'stdout bytes then stderr bytes; raw separate streams retained; no cross-stream chronological claim'
            report['process_test_total'] = sum(suite['total'] for suite in report['suites'])
            write_json(receipt_path, report)
            require(source_pins() == sources, 'Source drift after actual suite execution.')
            require(row['complete_ok'], 'First actual suite failure/count mismatch/skip: ' + name)
            require(datetime.now(timezone.utc) < utc_value(start['deadline_utc']), 'Window expired; no next suite.')
        require(report['process_test_total'] == (41 if args.phase == 'core' else 82), 'Actual phase total differs.')
        report['source_pins_unchanged_after_run'] = source_pins() == sources
        require(report['source_pins_unchanged_after_run'], 'Final Source pins changed.')
        report['passed'], report['completed'], report['process_exit_code'] = True, True, 0
    except BaseException as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        report['process_exit_code'] = 1
    finally:
        # Retain Popen handles until every owned suite has naturally exited.
        # This includes an interruption while writing a live receipt.
        for child in handles:
            if child.poll() is None:
                child.wait()
        for child, row, stdout_path, stderr_path, expected, suite_began in jobs:
            if row['raw_log'] is None:
                stdout, stderr = stdout_path.read_bytes(), stderr_path.read_bytes()
                raw_path = output / (row['file'] + '.combined.raw.log')
                if not raw_path.exists():
                    with raw_path.open('xb') as stream:
                        stream.write(stdout); stream.write(stderr); stream.flush(); os.fsync(stream.fileno())
                row.update(outcome(stdout, stderr, child.returncode, expected))
                row.update(exited_utc=utc(), exit_code=child.returncode, natural_exit=True,
                    duration_seconds=time.perf_counter() - suite_began,
                    stdout_raw=pin(stdout_path), stderr_raw=pin(stderr_path), raw_log=pin(raw_path))
        aggregate = bytearray()
        for row in report['suites']:
            if row['raw_log'] is not None:
                aggregate.extend(Path(row['raw_log']['path']).read_bytes())
        report['process_test_total'] = sum(row['total'] for row in report['suites'])
        report['natural_owned_children_gone'] = all(child.returncode is not None for child in handles)
        report['handles_retained_until_natural_exit'] = True
        raw_path = output / 'all_suite_process_output.raw.log'
        with raw_path.open('xb') as stream:
            stream.write(aggregate); stream.flush(); os.fsync(stream.fileno())
        report['process_raw_log'] = pin(raw_path)
        report['finished_utc'], report['duration_seconds'] = utc(), time.perf_counter() - began
        report.pop('waiting_child_pid', None)
        write_json(receipt_path, report)
    print(json.dumps({'receipt': pin(receipt_path), 'passed': report['passed'],
                      'process_test_total': report['process_test_total']}, ensure_ascii=False))
    return report['process_exit_code']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=tuple(SUITES), required=True)
    parser.add_argument('--resource-start', required=True)
    parser.add_argument('--resource-start-sha256', required=True)
    parser.add_argument('--scope-owner-token', required=True)
    parser.add_argument('--output-root', required=True)
    args = parser.parse_args()
    return run(args)


if __name__ == '__main__':
    sys.exit(main())
