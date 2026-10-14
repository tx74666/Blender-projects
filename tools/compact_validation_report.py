"""Compact one historical Original-leave report; retain exact bytes locally.

Preview is the default. --apply first writes and verifies a lossless XZ archive,
then replaces only the unchanged report. No Blender, Git staging, or upload.
Only the known indent=2 Original-leave schema is supported; replay inputs are
deliberately outside this tool's scope.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import tempfile
import uuid

SCHEMA = 'x.validation.original-leave-asset-transition/1'
COMPACT_SCHEMA = 'x.validation.original-leave-asset-transition-summary/1'
KEY = re.compile(rb'^( +)"((?:\\.|[^"\\])*)":')
OMIT = {'rest_full', 'mesh_raw_full'}
MAX_RETAINED_FIELD = 4 * 1024 * 1024


def fingerprint(path):
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
            size += len(block)
    return {'sha256': h.hexdigest(), 'bytes': size}


def identity(path):
    s = path.stat()
    return (s.st_size, s.st_mtime_ns, s.st_dev, s.st_ino)


@contextmanager
def deny_source_writes(path):
    """Windows source handle rejects active/new writers; permit atomic rename."""
    if os.name != 'nt':
        raise ValueError('Apply requires Windows deny-write file access')
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    handle = create(str(path), 0x80000000, 0x1 | 0x4, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        close(handle)


def extract(path):
    """Bounded extraction of the known producer's pretty-printed JSON fields."""
    result, stages, omitted = {}, {}, {}
    root = stage = field = None
    opened = closed = False
    root_rows, field_rows = [], []
    root_size = field_size = 0
    field_hash = None
    source_hash, source_size = hashlib.sha256(), 0

    def decode(rows, key):
        data = b''.join(rows).strip()
        prefix = json.dumps(key, ensure_ascii=False).encode('utf-8') + b':'
        if not data.startswith(prefix):
            raise ValueError('Unsupported JSON field format')
        value = data[len(prefix):].strip()
        if value.endswith(b','):
            value = value[:-1]
        return json.loads(value)

    def flush_field():
        nonlocal field, field_rows, field_size, field_hash
        if field is not None:
            if field in stages[stage] or field in omitted[stage]:
                raise ValueError('Duplicate phase field')
            if field in OMIT:
                omitted[stage][field] = {
                    'source_json_pointer': f'/phases/{stage}/{field}',
                    'serialized_field_bytes': field_size,
                    'serialized_field_sha256': field_hash.hexdigest(),
                    'digest_format': 'Exact UTF-8 field block including indent and separator',
                }
            else:
                stages[stage][field] = decode(field_rows, field)
        field, field_rows, field_size, field_hash = None, [], 0, None

    def flush_root():
        nonlocal root, root_rows, root_size
        if root == 'phases':
            flush_field()
        elif root is not None:
            if root in result:
                raise ValueError('Duplicate root field')
            result[root] = decode(root_rows, root)
        root, root_rows, root_size = None, [], 0

    with path.open('rb') as stream:
        for line in stream:
            if len(line) > MAX_RETAINED_FIELD:
                raise ValueError('Unsupported overlong line')
            source_hash.update(line)
            source_size += len(line)
            if closed:
                if line.strip():
                    raise ValueError('Unexpected content after document end')
                continue
            if not opened:
                if line.strip() != b'{':
                    raise ValueError('Missing document start')
                opened = True
                continue
            if line.rstrip() == b'}':
                flush_root()
                closed = True
                continue
            match = KEY.match(line)
            indent = len(match[1]) if match else None
            key = json.loads(b'"' + match[2] + b'"') if match else None
            if indent == 2:
                flush_root()
                root = key
                if root == 'phases':
                    if stages or line.strip() != b'"phases": {':
                        raise ValueError('Unsupported phases format')
                    continue
            elif root == 'phases':
                if indent == 4:
                    flush_field()
                    stage = key
                    if stage in stages or not line.rstrip().endswith(b'{'):
                        raise ValueError('Unsupported or duplicate phase')
                    stages[stage], omitted[stage] = {}, {}
                    continue
                if indent == 6:
                    flush_field()
                    if stage is None:
                        raise ValueError('Phase field outside phase')
                    field, field_hash = key, hashlib.sha256()
                elif line.rstrip() in (b'    }', b'    },', b'  }', b'  },'):
                    flush_field()
                    continue
                if field is not None:
                    field_hash.update(line)
                    field_size += len(line)
                    if field not in OMIT:
                        if field_size > MAX_RETAINED_FIELD:
                            raise ValueError('Retained field exceeds bounded memory limit')
                        field_rows.append(line)
                continue
            elif root is None:
                raise ValueError('Unsupported document format')
            root_size += len(line)
            if root_size > MAX_RETAINED_FIELD:
                raise ValueError('Root field exceeds bounded memory limit')
            root_rows.append(line)
    flush_root()
    if not closed:
        raise ValueError('Missing document end')
    if result.get('schema') != SCHEMA:
        raise ValueError('Only the historical Original-leave schema is supported')
    if set(stages) != {'before', 'after_validate', 'after_leave'}:
        raise ValueError('Only the completed three-phase leave report is supported')
    if result.get('completed') is not True or result.get('through') != 'leave':
        raise ValueError('Incomplete report or other operation cannot be compacted')
    if any(set(fields) != OMIT for fields in omitted.values()):
        raise ValueError('Missing expected full evidence fields')
    result['phases'] = stages
    return result, omitted, {'sha256': source_hash.hexdigest(), 'bytes': source_size}


def archive_verified(source, archive, original):
    archive.parent.mkdir(parents=True, exist_ok=True)

    def verify(path):
        h, size = hashlib.sha256(), 0
        with lzma.open(path, 'rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
                size += len(block)
        if {'sha256': h.hexdigest(), 'bytes': size} != original:
            raise ValueError('Archive round-trip mismatch; original was not replaced')

    if not archive.exists():
        fd, temporary = tempfile.mkstemp(prefix='.archive-', dir=archive.parent)
        try:
            with os.fdopen(fd, 'wb') as output:
                with lzma.LZMAFile(output, 'wb', preset=3) as target, source.open('rb') as input_file:
                    for block in iter(lambda: input_file.read(1024 * 1024), b''):
                        target.write(block)
                output.flush()
                os.fsync(output.fileno())
            verify(Path(temporary))
            # Atomic, exclusive publication of an already verified archive.
            # Both paths are on the same filesystem. Never overwrite a peer.
            os.link(temporary, archive)
        finally:
            Path(temporary).unlink(missing_ok=True)
    else:
        verify(archive)
    return fingerprint(archive)


def compact(report, project, apply=False, expected_sha256=None):
    if report.is_symlink():
        raise ValueError('Symlink reports are not supported')
    project, report = project.resolve(), report.resolve()
    if not report.is_relative_to(project / 'validation'):
        raise ValueError('Report must be a regular project validation file')
    initial_identity = identity(report)
    summary, omitted, original = extract(report)
    if expected_sha256 and expected_sha256 != original['sha256']:
        raise ValueError('Source SHA256 differs from expected input')
    relative = report.relative_to(project).as_posix()
    archive = project / '.validation-archives' / original['sha256'] / (report.name + '.xz')
    if not archive.resolve().is_relative_to(project / '.validation-archives') or archive.is_symlink():
        raise ValueError('Archive path escapes the local archive directory')
    summary['source_schema'] = summary['schema']
    summary['schema'] = COMPACT_SCHEMA
    summary['raw_evidence'] = {
        'availability': 'Local archive only; raw data is excluded from Git upload',
        'original': original,
        'original_report_path': relative,
        'archive_path': archive.relative_to(project).as_posix(),
        'archive_format': 'xz',
        'omitted_phase_fields': omitted,
        'changed_component_paths_scope': 'Phase-relative paths inside the original archived report',
        'transition_phases': {'validate': ['before', 'after_validate'], 'leave': ['before', 'after_leave']},
        'restore': 'Use Python lzma.open(archive_path, "rb") and copy to a NEW file; verify original.sha256 and bytes.',
    }
    result = {'report': str(report), 'original': original, 'apply': apply}
    if not apply:
        result['estimated_summary_bytes'] = len(json.dumps(summary, ensure_ascii=False, indent=2).encode('utf-8'))
        return result
    if expected_sha256 is None:
        raise ValueError('Apply requires an explicitly verified expected source SHA256')
    ignore = project / '.gitignore'
    if '/.validation-archives/' not in ignore.read_text(encoding='utf-8').splitlines():
        raise ValueError('Local archive directory must be explicitly ignored before apply')
    lock = archive.parent.parent / ('.compact-' + hashlib.sha256(relative.encode()).hexdigest() + '.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    temporary = None
    detached = None
    try:
        os.close(lock_fd)
        with deny_source_writes(report):
            if identity(report) != initial_identity or fingerprint(report) != original:
                raise ValueError('Source changed before compaction')
            saved_archive = archive_verified(report, archive, original)
            summary['raw_evidence']['archive'] = saved_archive
            summary['raw_evidence']['archive_round_trip_verified'] = True
            content = (json.dumps(summary, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            fd, temporary = tempfile.mkstemp(prefix='.compact-', dir=report.parent)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if identity(report) != initial_identity or fingerprint(report) != original:
                raise ValueError('Source changed during compaction')
            # Capture the source atomically, verify what was actually captured,
            # and publish exclusively. An external replacement is never overwritten.
            captured = archive.parent / ('.source-' + uuid.uuid4().hex + '.json')
            os.rename(report, captured)
            detached = captured
            if identity(detached) != initial_identity or fingerprint(detached) != original:
                raise ValueError('Captured source differs; preserved original remains available')
            os.link(temporary, report)
            detached.unlink()
            detached = None
            result.update(summary=fingerprint(report), archive=saved_archive,
                          archive_path=str(archive), round_trip_verified=True)
        return result
    finally:
        if detached is not None and detached.exists():
            if not report.exists():
                try:
                    os.link(detached, report)
                    detached.unlink()
                except FileExistsError:
                    pass  # Preserve both sources; never replace an external writer.
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--expected-sha256')
    args = parser.parse_args()
    print(json.dumps(compact(args.report, args.project, args.apply, args.expected_sha256), ensure_ascii=False, indent=2))
