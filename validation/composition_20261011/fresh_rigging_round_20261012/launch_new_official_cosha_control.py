"""Source-prepared once launcher for the isolated R5 control/save probe.

No application is started while preparing or compiling this file. At actual
invocation a fresh Parent START, live artist identity and memory admission are
mandatory. The visible headful child is never terminated by this launcher.
"""

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback


READY_SHA = 'a1d085832ee8a344d394de14b100ba2cecd2a55a4db50f33d05e0bf830193f0a'
HARNESS_SHA = 'cfaa6dc580d69dbdc7c752078752f2a3cbe89f33ec02a60c5186a196fba4cdcb'
PREPARED_SHA = '401b00d209b7806fa3c44c06fdf7e643256c64009d2abda45495a8b1cc0d4ac6'
REFERENCE_SHA = '230b9a0f460fd11c0dd93d1e63b55754916418e7d97c8ec7ecdd10b1d2833e7a'
EXE = Path(r'D:\Blender5.2\blender.exe')
OWNER = '01a12751-d08f-7630-b790-18db26fe3186'
PARENT = '01a12305-aada-7273-b72c-54a41aad77e4'
SCOPE = 'new-official-cosha-control-undo-reopen-reference'


def require(value, text):
    if not value:
        raise RuntimeError(text)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def pin(path, expected):
    path = Path(path).resolve()
    require(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected)
            and path.is_file() and sha(path) == expected, 'Pinned input changed: ' + str(path))
    return {'path': str(path), 'sha256': expected, 'bytes': path.stat().st_size}


def document(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def write(path, value, *, exclusive=False):
    with Path(path).open('x' if exclusive else 'w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def utc_filetime(value):
    """Parse an explicit aware ISO StartTime without dropping its seventh digit."""
    match = re.fullmatch(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,7}))?(Z|[+-]\d\d:\d\d)', value)
    require(match is not None, 'Supply actual timezone-aware artist creation UTC/StartTime, up to seven fractional digits.')
    base = datetime.fromisoformat(match[1] + match[3].replace('Z', '+00:00')).astimezone(timezone.utc)
    span = base - datetime(1601, 1, 1, tzinfo=timezone.utc)
    return (span.days * 86400 + span.seconds) * 10000000 + int((match[2] or '').ljust(7, '0') or '0')


def filetime_utc(value):
    seconds, ticks = divmod(value, 10000000)
    instant = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)
    return instant.strftime('%Y-%m-%dT%H:%M:%S') + '.' + str(ticks).zfill(7) + '+00:00'


class Windows:
    """Read-only OS admission; no process close/terminate or UI operations."""
    def __init__(self):
        require(os.name == 'nt', 'This once launcher requires Windows.')
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        k = self.kernel
        k.OpenProcess.argtypes, k.OpenProcess.restype = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE
        k.CloseHandle.argtypes, k.CloseHandle.restype = [wintypes.HANDLE], wintypes.BOOL
        k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        k.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        k.CreateToolhelp32Snapshot.argtypes, k.CreateToolhelp32Snapshot.restype = [wintypes.DWORD, wintypes.DWORD], wintypes.HANDLE

    def processes(self):
        class Entry(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('usage', wintypes.DWORD), ('pid', wintypes.DWORD),
                ('heap', ctypes.c_size_t), ('module', wintypes.DWORD), ('threads', wintypes.DWORD),
                ('parent', wintypes.DWORD), ('priority', wintypes.LONG), ('flags', wintypes.DWORD),
                ('exe', wintypes.WCHAR * 260)]
        k, rows = self.kernel, []
        k.Process32FirstW.argtypes = k.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
        snapshot = k.CreateToolhelp32Snapshot(2, 0)
        require(snapshot not in (None, ctypes.c_void_p(-1).value), 'Cannot read actual process inventory.')
        try:
            row = Entry()
            row.size = ctypes.sizeof(row)
            require(k.Process32FirstW(snapshot, ctypes.byref(row)), 'Cannot enumerate current processes.')
            while True:
                if row.exe.casefold() == 'blender.exe':
                    handle = k.OpenProcess(0x1000, False, row.pid)
                    require(handle, 'Cannot authenticate Blender PID ' + str(row.pid))
                    try:
                        path, length = ctypes.create_unicode_buffer(32768), wintypes.DWORD(32768)
                        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
                        require(k.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(length))
                                and k.GetProcessTimes(handle, *(ctypes.byref(v) for v in (created, exited, kernel, user))),
                                'Cannot read Blender executable/creation time.')
                        ticks = (created.dwHighDateTime << 32) | created.dwLowDateTime
                        rows.append({'pid': int(row.pid), 'parent_pid': int(row.parent),
                            'executable': str(Path(path.value).resolve()), 'creation_filetime': ticks,
                            'creation_utc': filetime_utc(ticks)})
                    finally:
                        k.CloseHandle(handle)
                if not k.Process32NextW(snapshot, ctypes.byref(row)):
                    require(ctypes.get_last_error() == 18, 'Process enumeration ended unexpectedly.')
                    break
            return rows
        finally:
            k.CloseHandle(snapshot)

    def memory(self):
        class Status(ctypes.Structure):
            _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [
                (name, ctypes.c_ulonglong) for name in ('total', 'available', 'page_total', 'page_available', 'virtual_total', 'virtual_available', 'extended')]
        value = Status()
        value.length = ctypes.sizeof(value)
        self.kernel.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(Status)]
        require(self.kernel.GlobalMemoryStatusEx(ctypes.byref(value)), 'Cannot read current physical memory.')
        return {'total_bytes': int(value.total), 'available_bytes': int(value.available),
            'available_MiB': value.available / 1048576, 'used_percent': int(value.load),
            'measured_utc': datetime.now(timezone.utc).isoformat()}

    def file_version(self, path):
        version = ctypes.WinDLL('version', use_last_error=True)
        version.GetFileVersionInfoSizeW.argtypes, version.GetFileVersionInfoSizeW.restype = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD
        version.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
        version.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]
        handle = wintypes.DWORD()
        size = version.GetFileVersionInfoSizeW(str(path), ctypes.byref(handle))
        require(size, 'The actual executable has no readable physical version resource.')
        data, pointer, length = ctypes.create_string_buffer(size), ctypes.c_void_p(), wintypes.UINT()
        require(version.GetFileVersionInfoW(str(path), 0, size, data)
                and version.VerQueryValueW(data, '\\', ctypes.byref(pointer), ctypes.byref(length))
                and length.value >= 13 * ctypes.sizeof(wintypes.DWORD), 'Cannot read the actual executable version block.')
        values = ctypes.cast(pointer, ctypes.POINTER(wintypes.DWORD))
        require(values[0] == 0xFEEF04BD, 'The physical executable version signature is invalid.')
        return [values[2] >> 16, values[2] & 65535, values[3] >> 16, values[3] & 65535]


def arguments():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('resource-token-file', 'ready-index', 'prepared-report', 'protected-artist',
                 'protected-workspace', 'source-freeze', 'package-manifest', 'reference-packet'):
        p.add_argument('--' + name, required=True)
        p.add_argument('--' + name + '-sha256', required=True)
    for name in ('launcher-sha256', 'blender-sha256', 'artist-start-time', 'unity-project-root',
                 'output-root', 'profile-root', 'launcher-evidence'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--artist-pid', type=int, required=True)
    p.add_argument('--artist-start-filetime', type=int, required=True)
    return p.parse_args()


def fresh_start(row, ready_sha):
    value = document(row['path'])
    fields = {'schema', 'status', 'token', 'actual_start_utc', 'owner_thread', 'parent_thread',
        'scope', 'native_process_limit', 'worker_allowed', 'ready_index_sha256'}
    require(fields <= set(value) and set(value) <= fields | {'free_mib', 'used_percent'}
        and value['schema'] == 'x.validation.fresh-native-resource-start/1' and value['status'] == 'ACTUAL_START'
        and isinstance(value['token'], str) and value['token'].strip()
        and value['owner_thread'] == OWNER and value['parent_thread'] == PARENT and value['scope'] == SCOPE
        and type(value['native_process_limit']) is int and value['native_process_limit'] == 1
        and value['worker_allowed'] is False and value['ready_index_sha256'] == ready_sha,
        'Use the actual new once control-only Parent START token, not any historical grant.')
    for name in ('free_mib', 'used_percent'):
        if name in value:
            require(type(value[name]) in (int, float) and math.isfinite(value[name]) and value[name] >= 0
                    and (name != 'used_percent' or value[name] <= 100), 'START memory evidence is invalid.')
    start = datetime.fromisoformat(value['actual_start_utc'].replace('Z', '+00:00'))
    require(start.tzinfo is not None and start.utcoffset() == timedelta(0)
            and 0 <= (datetime.now(timezone.utc) - start).total_seconds() <= 900,
            'The actual UTC START must be fresh within fifteen minutes.')
    pin(row['path'], row['sha256'])
    return hashlib.sha256(value['token'].encode('utf-8')).hexdigest()


def run(args):
    scope = Path(__file__).resolve().parent
    require(args.artist_pid > 0, 'Supply the actual artist PID.')
    rows = {'launcher': pin(__file__, args.launcher_sha256)}
    for name in ('resource_token_file', 'ready_index', 'prepared_report', 'protected_artist',
                 'protected_workspace', 'source_freeze', 'package_manifest', 'reference_packet'):
        rows[name] = pin(getattr(args, name), getattr(args, name + '_sha256'))
    require(rows['ready_index']['sha256'] == READY_SHA and rows['prepared_report']['sha256'] == PREPARED_SHA
            and rows['reference_packet']['sha256'] == REFERENCE_SHA, 'Use this reviewed R5/actual Prepare/reference tuple.')
    ready = document(args.ready_index)
    require(ready['schema'] == 'x.validation.new-official-cosha-source-ready/1'
            and ready['status'] == 'SOURCE_READY_FRESH_NATIVE_SCOPE_PENDING' and ready['source_only'] is True
            and ready['native_execution_performed'] is False, 'The Source ready index is not a native authorization.')
    for name, value in ready['pins'].items():
        actual = pin(value['path'], value['sha256'])
        require(actual == value, 'Ready-index input metadata changed: ' + name)
    for name in ('source_freeze', 'package_manifest'):
        require(rows[name] == ready['pins'][name], 'The supplied R5 pair differs from the actual ready index.')
    harness = ready['pins']['control_harness']
    require(harness['sha256'] == HARNESS_SHA and Path(harness['path']).resolve().parent == scope,
            'Use the final cfaa control harness beside this launcher.')
    manifest = document(args.package_manifest)
    require(type(manifest['schema_version']) is int and manifest['schema_version'] == 1
            and manifest['module'] == 'character_designer' and manifest['version'] == '0.77.25'
            and isinstance(manifest['source_provenance'], dict) and manifest['source_provenance'], 'Use the official complete R5 file map.')
    package = Path(manifest['source_root']).resolve()
    package_rows = []
    for relative, expected in manifest['files'].items():
        path = (package / relative).resolve()
        require(not Path(relative).is_absolute() and path.is_relative_to(package), 'A package leaf escaped its root.')
        package_rows.append(pin(path, expected))
    require({p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()} == set(manifest['files']),
            'The complete package gained or lost a physical leaf.')
    output, evidence, profile = (Path(getattr(args, name)).resolve() for name in ('output_root', 'launcher_evidence', 'profile_root'))
    require(output != evidence and all(p != scope and p.is_relative_to(scope) and p.is_dir()
            and not any(p.iterdir()) for p in (output, evidence))
            and not output.is_relative_to(evidence) and not evidence.is_relative_to(output),
            'Separate fresh empty ROUND children are required for native output and OS/log evidence.')
    require(profile.is_relative_to(Path(r'D:\Codex\XV').resolve()) and profile.is_dir()
            and {p.name for p in profile.iterdir()} == {'CONFIG', 'DATAFILES'}
            and all((profile / n).is_dir() and not (profile / n).is_symlink() and not any((profile / n).iterdir())
                for n in ('CONFIG', 'DATAFILES'))
            and not profile.is_relative_to(output) and not profile.is_relative_to(evidence), 'Use the separate short owned empty profile.')
    predicted = profile / 'DATAFILES/character_designer/animation_sources' / ('0' * 32) / ('0' * 64) / ('0' * 32 + '.blend')
    require(len(str(predicted).encode('utf-16-le')) // 2 < 260, 'The actual Source-cache profile would exceed 260 units.')
    for name in ('protected_artist', 'protected_workspace'):
        path = Path(rows[name]['path'])
        require(not any(path.is_relative_to(p) for p in (output, evidence, profile)), 'Protected files must stay outside owned writes.')
    rows['blender'] = pin(EXE, args.blender_sha256)
    os_reader = Windows()
    version = os_reader.file_version(EXE.resolve())
    require(version[:2] == [5, 2], 'The physical executable is not Blender 5.2.')
    artist_ticks = args.artist_start_filetime
    require(artist_ticks > 0 and abs(utc_filetime(args.artist_start_time) - artist_ticks) < 10,
            'Artist creation UTC and exact FILETIME disagree; WMI UTC may truncate below one microsecond.')
    def artist_only():
        processes = os_reader.processes()
        require(len(processes) == 1 and processes[0]['pid'] == args.artist_pid
                and processes[0]['creation_filetime'] == artist_ticks
                and Path(processes[0]['executable']).resolve() == EXE.resolve(),
                'The actual shared artist identity changed or another Blender process occupies the resource window.')
        return processes
    original_processes = artist_only()
    token_identity = fresh_start(rows['resource_token_file'], READY_SHA)
    for value in (*rows.values(), *package_rows):
        pin(value['path'], value['sha256'])
    artist_only()
    fresh_start(rows['resource_token_file'], READY_SHA)
    memory = os_reader.memory()
    measured = [memory]
    if memory['used_percent'] >= 98:
        time.sleep(2)
        memory = os_reader.memory()
        measured.append(memory)
    require(memory['available_bytes'] >= 200 * 1048576, 'Current available memory is below the admitted 200 MiB minimum.')
    claims = scope / 'launch_claims'
    require(not claims.is_symlink() and claims.resolve().parent == scope, 'The once-claim directory leaves this owned ROUND.')
    claims.mkdir(exist_ok=True)
    claim = claims / (token_identity + '.json')
    write(claim, {'schema': 'x.validation.fresh-native-start-once-claim/1', 'claimed_utc': datetime.now(timezone.utc).isoformat(),
        'resource_token': rows['resource_token_file'], 'opaque_token_sha256': token_identity,
        'launcher': rows['launcher'], 'native_output': str(output),
        'launcher_evidence': str(evidence)}, exclusive=True)
    command = [str(EXE.resolve()), '--factory-startup', '--disable-autoexec', '--threads', '1',
               '--python-exit-code', '17', '--python', harness['path'], '--']
    for name in ('prepared_report', 'protected_artist', 'source_freeze', 'package_manifest', 'reference_packet'):
        command += ['--' + name.replace('_', '-'), rows[name]['path'], '--' + name.replace('_', '-') + '-sha256', rows[name]['sha256']]
    command += ['--script-sha256', HARNESS_SHA, '--unity-project-root', str(Path(args.unity_project_root).resolve()),
                '--output-root', str(output), '--profile-root', str(profile), '--confirm-isolated-headful', '--quit-on-completion']
    env = dict(os.environ)
    env.update(BLENDER_USER_CONFIG=str(profile / 'CONFIG'), BLENDER_USER_DATAFILES=str(profile / 'DATAFILES'), PYTHONDONTWRITEBYTECODE='1')
    receipt = {'schema': 'x.validation.new-official-cosha-control-launch/1', 'completed': False,
        'natural_exit_verified': False, 'native_execution_performed': False, 'inputs': rows,
        'artist_process_before': original_processes, 'physical_executable_version': version, 'memory_admission': measured,
        'argv': command, 'profiles': {'CONFIG': str(profile / 'CONFIG'), 'DATAFILES': str(profile / 'DATAFILES')},
        'worker_allowed': False, 'artist_opened_or_saved': False, 'process_termination_performed': False}
    receipt_file = evidence / 'launch_receipt.json'
    write(receipt_file, receipt, exclusive=True)
    child = None
    try:
        with (evidence / 'stdout.log').open('xb') as stdout, (evidence / 'stderr.log').open('xb') as stderr:
            # Plain Windows argv list, shell=False, no hidden interactive window.
            fresh_start(rows['resource_token_file'], READY_SHA)
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                cwd=str(scope), env=env, shell=False)
            receipt.update(native_execution_performed=True, child_pid=child.pid, started_utc=datetime.now(timezone.utc).isoformat())
            write(receipt_file, receipt)
            print(json.dumps({'child_pid': child.pid, 'receipt': str(receipt_file), 'native_output': str(output)}), flush=True)
            while child.poll() is None:
                time.sleep(1)
            code = child.returncode
            stdout.flush()
            stderr.flush()
            os.fsync(stdout.fileno())
            os.fsync(stderr.fileno())
        receipt.update(natural_exit_verified=True, exit_code=code, exited_utc=datetime.now(timezone.utc).isoformat())
        write(receipt_file, receipt)
        protected = {name: pin(rows[name]['path'], rows[name]['sha256']) for name in ('protected_artist', 'protected_workspace')}
        remaining = artist_only()
        report = output / 'new_official_cosha_report.json'
        report_pin = pin(report, sha(report)) if report.is_file() else None
        result = document(report) if report_pin is not None else None
        if result is not None:
            require(result['schema'] == 'x.validation.new-official-cosha-control-save/1'
                    and result['native_execution_performed'] is True
                    and all(result['source_inputs'][name] == rows[name] for name in
                        ('prepared_report', 'protected_artist', 'source_freeze', 'package_manifest', 'reference_packet'))
                    and result['source_inputs']['script'] == harness,
                    'The actual native report belongs to another admitted input tuple.')
        completed = result is not None and result['completed'] is True
        receipt.update(completed=bool(code == 0 and completed), natural_exit_verified=True, exit_code=code,
            exited_utc=datetime.now(timezone.utc).isoformat(), protected_files_after=protected,
            artist_process_after=remaining, all_owned_Blender_processes_gone=True, control_report=report_pin,
            stdout=pin(evidence / 'stdout.log', sha(evidence / 'stdout.log')),
            stderr=pin(evidence / 'stderr.log', sha(evidence / 'stderr.log')))
        write(receipt_file, receipt)
        print(json.dumps({'completed': receipt['completed'], 'exit_code': code, 'receipt': pin(receipt_file, sha(receipt_file))}), flush=True)
        return 0 if receipt['completed'] else 1
    except BaseException as error:
        receipt.update(completed=False, error=str(error), traceback=traceback.format_exc(),
            child_pid=child.pid if child else None, child_exit_code=child.poll() if child else None,
            process_termination_performed=False, interrupted_child_retained=bool(child and child.poll() is None))
        write(receipt_file, receipt)
        raise


if __name__ == '__main__':
    sys.exit(run(arguments()))
