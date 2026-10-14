"""Freeze only approved 0.77.11 + isolated Roll fix + reviewed Forearm repair.

This light source-only recipe never imports Blender, builds a ZIP, or deploys.
It refuses changed canonical input bytes and any new/missing package path.
"""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
X_ROOT = HERE.parents[1]
REPOSITORY = Path('D:/MyRepository/Blender-addons-by-Randy')
APPROVED_MANIFEST = X_ROOT / 'validation/arm_flat_fix_20261009/release_projection.json'
APPROVED_MANIFEST_SHA256 = '199b46ab6a5972b426a1daf3be9df03de4903cc270b294da20995523e59dea22'
ROLL_WORKER_SHA256 = 'fa04069126b3dd327b4f3d892f83cd8d2fc483348a0a1f13151bf2c7be5f4e3b'
FOREARM_INPUTS = {
    'forearm_twist.py': 'e8403be47320e95b7b40955e79b89d27e4ac7e39f3565f3fe7cabfe529a2cb14',
    'forearm_twist_cache.py': 'dead8b61993a7dbc9962532e91bd2822d38702e4306c41f97141e582ef6805c6',
    'forearm_twist_topology.py': '91a574cd7f688670c6c0601a19785d76f75595b22609368744c2d4eb6db12c10',
    'body_calibration_ui.py': '86d14dae2ba9d2e58b91915dbfbbc6200f3f06a112b33300992fd7561f30a058',
    'forearm_twist_edit.py': 'b33c4141e2f60231e53b3359ee205d20195d0a8b3ca3b24e5da0b8e1adcf976d',
    'unity_forearm.py': '9d90bf781675c9b6afd2161a8836a8780169ec92395eff683332d93537006aca',
}


def sha(content):
    return hashlib.sha256(content).hexdigest()


def package_files(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob('*') if path.is_file()
            and not any(part.startswith('.') or part == '__pycache__'
                        for part in path.relative_to(root).parts)
            and path.suffix not in {'.pyc', '.pyo'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=HERE / 'forearm_roll_07712_runtime/character_designer')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output.parent.exists():
        raise ValueError('Choose a new candidate directory; existing evidence is immutable.')
    if sha(APPROVED_MANIFEST.read_bytes()) != APPROVED_MANIFEST_SHA256:
        raise ValueError('The exact approved 0.77.11 manifest changed.')
    sys.path.insert(0, str(REPOSITORY / 'tools'))
    from release_projection import load_source
    approved = load_source('character_designer', APPROVED_MANIFEST, root=REPOSITORY)
    if approved.version != '0.77.11' or len(approved.files) != 152:
        raise ValueError('The approved version or complete file count changed.')
    approved_files = {name.as_posix(): data for name, data in approved.files.items()}
    approved_hashes = {name: sha(data) for name, data in approved_files.items()}

    roll_root = HERE / 'roll_only_runtime/character_designer'
    roll_receipt = HERE / 'roll_only_runtime/roll_only_projection.json'
    roll = package_files(roll_root)
    recorded_roll = json.loads(roll_receipt.read_text(encoding='utf-8'))
    if ({name: sha(data) for name, data in roll.items()} != recorded_roll['files']
            or set(roll) != set(approved_files)
            or sha(roll['unity_export_worker.py']) != ROLL_WORKER_SHA256
            or sorted(name for name in roll if sha(roll[name]) != approved_hashes[name])
            != ['unity_export_worker.py']):
        raise ValueError('The Roll candidate no longer contains only its single isolated worker fix.')

    candidate = dict(roll)
    audit = []
    differences = []
    for name, checksum in FOREARM_INPUTS.items():
        content = (REPOSITORY / 'addons/character_designer' / name).read_bytes()
        if sha(content) != checksum:
            raise ValueError('Reviewed canonical Forearm source changed: ' + name)
        compile(content, name, 'exec')
        candidate[name] = content
        before = approved_files[name].decode('utf-8').replace('\r\n', '\n')
        after = content.decode('utf-8').replace('\r\n', '\n')
        differences.append(''.join(difflib.unified_diff(
            before.splitlines(True), after.splitlines(True),
            fromfile='approved_07711/' + name, tofile='reviewed_forearm/' + name)))
        audit.append({'file': name, 'approved_sha256': approved_hashes[name],
                      'canonical_sha256': checksum, 'held_changes_in_file': False,
                      'scope': 'Reviewed local support proof, safe Setup recapture, or read-only export preparation.'})
    init = candidate['__init__.py']
    old_version = b'"version": (0, 77, 11),'
    if init.count(old_version) != 1:
        raise ValueError('The approved init version no longer has its exact single declaration.')
    candidate['__init__.py'] = init.replace(old_version, b'"version": (0, 77, 12),')
    changed = sorted(name for name, data in candidate.items() if sha(data) != approved_hashes[name])
    if (set(candidate) != set(approved_files)
            or changed != sorted((*FOREARM_INPUTS, '__init__.py', 'unity_export_worker.py'))):
        raise ValueError('The candidate changed more than its six Forearm inputs, Roll worker and version.')
    for name, content in candidate.items():
        if name.endswith('.py'):
            ast.parse(content, filename=name)

    output.mkdir(parents=True)
    for name, data in candidate.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    files = {name: sha(data) for name, data in sorted(candidate.items())}
    provenance = {
        'scope': 'APPROVED_07711_PLUS_ISOLATED_ROLL_FIX_AND_REVIEWED_FOREARM_REPAIR',
        'approved_version': approved.version,
        'approved_manifest': str(APPROVED_MANIFEST),
        'approved_manifest_sha256': APPROVED_MANIFEST_SHA256,
        'approved_source_root': str(approved.root),
        'roll_source_root': str(roll_root),
        'roll_receipt_sha256': sha(roll_receipt.read_bytes()),
        'forearm_inputs': FOREARM_INPUTS,
        'changed_files': changed,
        'excluded': 'Pending Dress/Cloth, newer worker cleanup, other canonical changes, and all Unity runtime changes.',
        'file_count': len(files),
        'native_verification': 'Pending Root serial native verification; source recipe only.',
    }
    manifest = {'schema_version': 1, 'module': 'character_designer', 'version': '0.77.12',
                'source_root': str(output), 'files': files, 'source_provenance': provenance}
    manifest_path = output.parent / 'release_projection_07712.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    verified = load_source('character_designer', manifest_path, root=REPOSITORY)
    if len(verified.files) != 152 or verified.version != '0.77.12':
        raise ValueError('The official release projection resolver rejected the frozen candidate.')
    (output.parent / 'forearm_reviewed_delta.patch').write_text(''.join(differences), encoding='utf-8')
    receipt = {'candidate': str(output), 'manifest': str(manifest_path),
               'manifest_sha256': verified.projection_sha256,
               'file_count': len(files), 'changed_files': changed, 'forearm_audit': audit,
               'Blender_started': False, 'Unity_started': False, 'deployed': False,
               'canonical_source_modified': False}
    receipt_path = output.parent / 'projection_receipt.json'
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
