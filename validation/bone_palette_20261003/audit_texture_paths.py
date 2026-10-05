"""Read the open .blend's texture references; write only a fresh JSON report.

Pass --output after Blender's -- separator for a post-save report. Existing
reports are never overwritten, so the original actual-X baseline is preserved.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys

import bpy


def input_fingerprint(path):
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    after = path.stat()
    return {
        'path': str(path), 'bytes': after.st_size, 'mtime_ns': after.st_mtime_ns,
        'sha256': digest.hexdigest(),
        'stable_during_hash': (before.st_size, before.st_mtime_ns)
                              == (after.st_size, after.st_mtime_ns),
    }


def capture_report():
    report = {
        'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'blend': bpy.data.filepath,
        'is_dirty': bool(bpy.data.is_dirty),
        'images': [],
        'materials': {},
    }
    for img in bpy.data.images:
        if img.source not in {'FILE', 'TILED'}:
            continue
        path = Path(bpy.path.abspath(img.filepath, library=img.library)).resolve()
        exists = path.is_file()
        report['images'].append({
            'name': img.name, 'path': img.filepath, 'absolute': str(path),
            'exists': exists, 'bytes': path.stat().st_size if exists else None,
            'packed': bool(img.packed_file), 'users': img.users,
        })
    for material in bpy.data.materials:
        if material.node_tree:
            names = [node.image.name for node in material.node_tree.nodes
                     if node.type == 'TEX_IMAGE' and node.image]
            if names:
                report['materials'][material.name] = names
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=Path(__file__).resolve().parent / 'texture_paths_actual_x.json')
    parser.add_argument('--reopen-readonly', action='store_true',
                        help='Reopen the same saved input with UI/scripts disabled before capture; never save.')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    output = args.output.resolve()
    if output.exists():
        parser.error(f'Report already exists: {output}. Use --output with a fresh filename.')
    if not bpy.data.filepath:
        parser.error('Open the saved actual-X .blend before running this audit.')
    input_path = Path(bpy.data.filepath).resolve()
    if not input_path.is_file():
        parser.error(f'The opened saved input does not exist: {input_path}')
    initial_dirty = bool(bpy.data.is_dirty)
    input_before = input_fingerprint(input_path)
    reopened_dirty, reopen_result = None, None
    if args.reopen_readonly:
        result = bpy.ops.wm.open_mainfile(filepath=str(input_path), load_ui=False, use_scripts=False)
        reopen_result = sorted(result)
        if result != {'FINISHED'} or Path(bpy.data.filepath).resolve() != input_path:
            raise RuntimeError('Blender did not confirm reopening the same saved input.')
        reopened_dirty = bool(bpy.data.is_dirty)
    report = capture_report()
    input_after = input_fingerprint(input_path)
    report.update(initial_is_dirty=initial_dirty,
                  reopened_readonly=bool(args.reopen_readonly),
                  reopened_is_dirty=reopened_dirty, reopen_result=reopen_result,
                  input_integrity={
                      'before': input_before, 'after': input_after,
                      'unchanged': input_before == input_after
                                   and input_before['stable_during_hash']
                                   and input_after['stable_during_hash'],
                  })
    with output.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print('TEXTURE_AUDIT', json.dumps({
        'output': str(output), 'blend': report['blend'], 'is_dirty': report['is_dirty'],
        'initial_is_dirty': initial_dirty, 'reopened_is_dirty': reopened_dirty,
        'input_unchanged': report['input_integrity']['unchanged'],
        'images': len(report['images']),
        'unresolved_unpacked': [image['name'] for image in report['images']
                                if not image['exists'] and not image['packed']],
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
