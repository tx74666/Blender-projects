"""Freeze the approved 0.76.4 baseline plus this task's eight Pose files."""
import argparse
import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
BASE = ROOT.parent / 'forearm_follow_20261006' / 'candidate_source' / 'addons' / 'character_designer'
BASE_MANIFEST = BASE.parents[2] / 'release_manifest.json'
SOURCE = REPO / 'addons' / 'character_designer'
INSTALLED = Path(os.environ['APPDATA']) / 'Blender Foundation' / 'Blender' / '5.2' / 'scripts' / 'addons' / 'character_designer'
DELTA = ('__init__.py', 'animation.py', 'body_setup.py', 'limb_ik.py', 'limb_ik_fk.py',
         'control_pose_assets.py', 'control_pose_mirror.py', 'control_pose_capture.py')
def digest(data):
    return hashlib.sha256(data).hexdigest()
def files(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*')
            if p.is_file() and not any(x.startswith('.') or x == '__pycache__'
                                      for x in p.relative_to(folder).parts)
            and p.suffix not in ('.pyc', '.pyo')}

def require(condition, message):
    if not condition:
        raise ValueError(message)


def approved_directory(version, supplied=None):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Version must have three numeric parts.')
    default = 'approved_release' if version == '0.77.0' else 'approved_release_' + version.replace('.', '')
    directory = Path(supplied) if supplied else Path(default)
    directory = (directory if directory.is_absolute() else ROOT / directory).resolve()
    original = (ROOT / 'approved_release').resolve()
    if directory == ROOT.resolve() or not directory.is_relative_to(ROOT.resolve()):
        raise ValueError('ApprovedDir must be a separate directory inside this validation folder.')
    if version != '0.77.0' and (directory == original or directory.is_relative_to(original)):
        raise ValueError('New versions cannot overwrite frozen approved_release 0.77.0.')
    if version == '0.77.1' and directory.name != 'approved_release_0771':
        raise ValueError('Version 0.77.1 requires independent approved_release_0771.')
    return directory


def frozen_json(path, payload):
    if path.exists():
        if json.loads(path.read_bytes()) != payload:
            raise ValueError('Refusing replacement of frozen evidence: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8'))


def package_version(content):
    for node in ast.parse(content).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'bl_info' for t in node.targets):
            return '.'.join(map(str, ast.literal_eval(node.value)['version']))
    raise ValueError('Missing bl_info version.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='0.77.0')
    parser.add_argument('--approved-dir')
    parser.add_argument('--installed-projection', type=Path)
    parser.add_argument('--installed-projection-sha256', default='c9dcc6929f1a85c67616be6f60ba82f79561ac670591cb3025888701075771ea')
    args = parser.parse_args(argv)
    approved = approved_directory(args.version, args.approved_dir)
    DEST = approved / 'addons' / 'character_designer'
    previous = None
    baseline_manifest_bytes = BASE_MANIFEST.read_bytes()
    require(digest(baseline_manifest_bytes) == 'b9fcd0f2115a725b030e4c8f7c6a77e262e82804c5ab01c6be3c9b36ce2916e6', 'Frozen release verification failed.')
    baseline_manifest = json.loads(baseline_manifest_bytes)
    base = files(BASE)
    require(tuple(baseline_manifest['version']) == (0, 76, 4), 'Approved source baseline must stay 0.76.4.')
    expected = baseline_manifest['files']
    require({name: digest(data) for name, data in base.items()} == expected, 'Frozen release verification failed.')
    if args.version == '0.77.0':
        require(files(INSTALLED) == base, 'Installation no longer matches the approved 0.76.4 baseline.')
    else:
        previous_path = (args.installed_projection or ROOT / 'approved_release' / 'release_projection.json').resolve()
        previous_bytes = previous_path.read_bytes()
        require(digest(previous_bytes) == args.installed_projection_sha256, 'Previous projection manifest SHA256 changed.')
        sys.path.insert(0, str(REPO / 'tools'))
        from release_projection import load_source
        verified = load_source('character_designer', previous_path)
        require(verified.version == '0.77.0', 'This fix expects the approved installed 0.77.0 projection.')
        require(files(INSTALLED) == {name.as_posix(): data for name, data in verified.files.items()}, 'Installed 0.77.0 projection drift.')
        previous = {'manifest': str(previous_path), 'sha256': digest(previous_bytes), 'version': verified.version}
    canonical = files(SOURCE)
    payload = dict(base)
    payload.update({name: canonical[name] for name in DELTA})
    require(len(base) == 147 and len(payload) == 148, 'Frozen release verification failed.')
    require(package_version(payload['__init__.py']) == args.version, 'Canonical Pose files have the wrong requested version.')
    for name, data in payload.items():
        if name.endswith('.py'):
            ast.parse(data, filename=name)
    provenance = {
        'baseline_manifest': str(BASE_MANIFEST), 'baseline_manifest_sha256': digest(baseline_manifest_bytes),
        'baseline_source': str(BASE), 'baseline_version': baseline_manifest['version'],
        'installed_baseline_exact': previous is None, 'canonical_source': str(SOURCE),
        'approved_delta': {name: {'before': digest(base[name]) if name in base else None,
                                'after': digest(payload[name])} for name in DELTA},
        'excluded_pending_canonical': sorted(name for name in canonical
                                            if name not in DELTA and canonical[name] != base.get(name)),
        'scope': 'Save Pose and synchronized application; pending Dress changes excluded.',
    }
    if previous is not None:
        provenance['installed_projection_exact'] = True
        provenance['installed_projection'] = previous
    manifest = {'schema_version': 1, 'module': 'character_designer', 'version': args.version,
                'source_root': str(DEST.resolve()),
                'files': {name: digest(data) for name, data in sorted(payload.items())},
                'source_provenance': provenance}
    if DEST.exists() and files(DEST) != payload:
        raise ValueError('A different or partial frozen projection exists: ' + str(DEST))
    for path, data in ((approved / 'provenance.json', provenance), (approved / 'release_projection.json', manifest)):
        if path.exists() and json.loads(path.read_bytes()) != data:
            raise ValueError('Different frozen evidence exists: ' + str(path))
    if not DEST.exists():
        for name, data in payload.items():
            target = DEST / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(data)
    frozen_json(approved / 'provenance.json', provenance)
    frozen_json(approved / 'release_projection.json', manifest)
    print('POSE_APPROVED_PROJECTION', DEST, args.version, len(payload), 'files; excluded',
          len(provenance['excluded_pending_canonical']), '; manifest SHA256',
          digest((approved / 'release_projection.json').read_bytes()))


if __name__ == '__main__':
    main()
