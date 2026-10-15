"""Root-invoked bounded current SaveCopy capture/assembler; no artist operations.

Root alone launches Native after the shared resource window is actually free.
The actual receipt gates run before importing the kernel that accesses bpy.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def preflight_sources(sha):
    """Pin the reviewed local seal before importing current policy/helper code."""
    path = HERE/'current_cache_sources_007.json'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise RuntimeError('Current source seal CLI SHA differs')
    seal = json.loads(raw)
    if seal.get('schema') != 'x.current-cache-sources/1' or Path(__file__).name not in seal.get('files', {}):
        raise RuntimeError('Current source seal missing entry')
    for name, pin in seal['files'].items():
        actual = Path(pin['path']).resolve()
        if actual != HERE/name:
            raise RuntimeError('Foreign current source path')
        digest, count = hashlib.sha256(), 0
        with actual.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                digest.update(block)
                count += len(block)
        if digest.hexdigest() != pin['sha256'] or count != pin['bytes']:
            raise RuntimeError('Reviewed current source changed: '+name)


def run(args, report):
    # Pure disk/receipt admission precedes Native source opening or cache writes.
    preflight_sources(args.source_seal_sha256)
    import mesh_cache_current_policy_007 as policy
    if args.mode == 'capture':
        prepared = policy.prepare_capture(args, report)
    else:
        prepared = policy.prepare_assembly(args, report)
    import mesh_cache_actor_current_core_007 as core
    if args.mode == 'capture':
        core.run_clip(args, report, prepared)
    else:
        core.assemble_clip(args, report, prepared)


def parser():
    result = argparse.ArgumentParser()
    modes = result.add_subparsers(dest='mode', required=True)
    capture = modes.add_parser('capture')
    for name in ('input', 'artist', 'snapshot-report', 'snapshot-sha256', 'input-sha256',
                 'tiny-report', 'tiny-sha256', 'cache-dir', 'v9-factory-report', 'v9-factory-sha256'):
        capture.add_argument('--'+name, required=True)
    capture.add_argument('--input-bytes', type=int, required=True)
    capture.add_argument('--addons', default=str(HERE/'staged_20261015_06/addons'))
    capture.add_argument('--source-manifest', default=str(HERE/'staged_20261015_06/source_manifest.json'))
    capture.add_argument('--witness', choices=('v9',), default='v9')
    assemble = modes.add_parser('assemble')
    for name in ('full30-report', 'full30-sha256', 'output', 'artist'):
        assemble.add_argument('--'+name, required=True)
    for child in (capture, assemble):
        child.add_argument('--source-seal-sha256', required=True)
        child.add_argument('--report', required=True)
    return result


if __name__ == '__main__':
    args = parser().parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema': 'x.current-pc2-full30/1' if args.mode == 'capture' else 'x.current-pc2-artifact/1',
        'completed': False, 'pid': os.getpid(),
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'root_invoked_native_entry': True, 'gui_fps_verified': False, 'no_artist_write_or_deploy': True,
        'no_artifact_save': args.mode == 'capture', 'candidate_pending_normal_reopen_gui_and_fps': True}
    # Reserve evidence before any possible publication; never overwrite a receipt.
    with Path(args.report).resolve().open('x', encoding='utf-8') as stream:
        try:
            run(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
