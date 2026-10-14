"""Prepare an approved-0.77.11 copy with only the persistent skeleton Roll fix.

This ordinary Python script does not import or start Blender. The output remains
version 0.77.11 until the release owner combines validated fixes and bumps it.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil


OLD_CAPTURE = """        matrices = {bone.name: bone.matrix.copy() for bone in obj.data.edit_bones if bone.name in names}
        lengths = {bone.name: bone.length for bone in obj.data.edit_bones if bone.name in names}"""
NEW_CAPTURE = """        geometry = {bone.name: (bone.head.copy(), bone.tail.copy(), bone.roll)
                    for bone in obj.data.edit_bones if bone.name in names}"""
OLD_RESTORE = """            bone.matrix = matrices[name]
            bone.length = lengths[name]"""
NEW_RESTORE = """            # Parenting uses Armature-space geometry. Avoid decomposing the
            # bone's own matrix back into an axis/roll: native matrix/roll
            # roundtrips can reverse its roll by pi. Restore only
            # native geometry fields that actually changed during filtering.
            head, tail, roll = geometry[name]
            if bone.head != head:
                bone.head = head
            if bone.tail != tail:
                bone.tail = tail
            if bone.roll != roll:
                bone.roll = roll"""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def function(source):
    node = next(item for item in ast.parse(source).body
                if isinstance(item, ast.FunctionDef) and item.name == '_clean_skeleton')
    return ast.get_source_segment(source, node)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--canonical', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    expected = json.loads(args.manifest.read_text(encoding='utf-8'))['files']
    actual = {path.relative_to(args.approved).as_posix(): digest(path)
              for path in args.approved.rglob('*') if path.is_file()
              and '__pycache__' not in path.parts and path.suffix != '.pyc'}
    if actual != expected:
        raise ValueError('Approved file inventory or SHA differs from the frozen manifest.')
    old = (args.approved / 'unity_export_worker.py').read_bytes().decode('utf-8')
    canonical = args.canonical.read_bytes().decode('utf-8')
    if old.count(OLD_CAPTURE) != 1 or old.count(OLD_RESTORE) != 1:
        raise ValueError('The shipped worker no longer has the exact two old fragments.')
    patched = old.replace(OLD_CAPTURE, NEW_CAPTURE).replace(OLD_RESTORE, NEW_RESTORE)
    if function(patched) != function(canonical):
        raise ValueError('The two-fragment patch differs from persistent canonical _clean_skeleton.')
    compile(patched, 'unity_export_worker.py', 'exec')
    if args.output.exists():
        raise ValueError('Choose a new output directory; preserve existing evidence.')
    shutil.copytree(args.approved, args.output,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (args.output / 'unity_export_worker.py').write_bytes(patched.encode('utf-8'))
    final = {name: digest(args.output / name) for name in expected}
    changed = [name for name in expected if final[name] != expected[name]]
    if changed != ['unity_export_worker.py']:
        raise ValueError('Projection changed more than the single intended worker.')
    report = {'scope': 'APPROVED_07711_PLUS_ONLY_CLEAN_SKELETON_ROLL_FIX',
              'changed_files': changed, 'source_sha256': expected['unity_export_worker.py'],
              'patched_sha256': final['unity_export_worker.py'],
              'canonical_clean_skeleton_exact': True, 'files': final,
              'Blender_started': False, 'canonical_source_modified': False}
    receipt = args.output.parent / 'roll_only_projection.json'
    receipt.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(str(receipt))


if __name__ == '__main__':
    main()
