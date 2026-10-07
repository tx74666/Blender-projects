"""Collect the package and local installation proofs without touching Blender."""
import argparse
import hashlib
import sys
import json
import os
from pathlib import Path
import zipfile

from freeze_pose_release import approved_directory, frozen_json, REPO, require

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='0.77.0')
    parser.add_argument('--approved-dir')
    parser.add_argument('--projection-sha256')
    args = parser.parse_args(argv)
    folder = Path(__file__).resolve().parent
    approved = approved_directory(args.version, args.approved_dir)
    manifest_path = approved / 'release_projection.json'
    manifest_bytes = manifest_path.read_bytes()
    if args.projection_sha256:
        require(hashlib.sha256(manifest_bytes).hexdigest() == args.projection_sha256, 'Projection manifest SHA256 changed.')
    sys.path.insert(0, str(REPO / 'tools'))
    from release_projection import load_source
    verified = load_source('character_designer', manifest_path)
    require(verified.version == args.version, 'Projection does not match requested version.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    archive = REPO / 'dist' / ('character_designer-' + args.version + '.zip')
    targets = [Path(os.environ['APPDATA']) / 'Blender Foundation' / 'Blender' / '5.2' / 'scripts' / 'addons' / 'character_designer',
               Path(r'D:\Blender\Projects\Character\X\addons\character_designer')]
    def sha(data):
        return hashlib.sha256(data).hexdigest()
    with zipfile.ZipFile(archive) as package:
        archived = {i.filename.removeprefix('character_designer/'): sha(package.read(i))
                    for i in package.infolist() if not i.is_dir()}
        require(package.testzip() is None and archived == manifest['files'], 'Frozen release verification failed.')
    checked = []
    for target in targets:
        actual = {p.relative_to(target).as_posix(): sha(p.read_bytes()) for p in target.rglob('*')
                  if p.is_file() and not any(part.startswith('.') or part == '__pycache__'
                                            for part in p.relative_to(target).parts)
                  and p.suffix not in ('.pyc', '.pyo')}
        require(actual == manifest['files'], 'Deployment drift: ' + str(target))
        checked.append({'destination': str(target), 'files': len(actual), 'different_files': 0})
    receipt = {'version': manifest['version'], 'blender_executable': r'D:\Blender5.2\blender.exe',
               'projection': str(manifest_path), 'projection_sha256': sha(manifest_path.read_bytes()),
               'archive': str(archive), 'archive_sha256': sha(archive.read_bytes()),
               'destinations': checked, 'status': 'RELEASE_PROJECTION_MATCH',
               'scope': manifest['source_provenance']['scope'], 'git_commit': False, 'git_push': False}
    receipt_path = folder / 'local_release_receipt.json' if args.version == '0.77.0' else approved / 'local_release_receipt.json'
    frozen_json(receipt_path, receipt)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
