"""Verify immutable release payload and record local delivery evidence."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path.insert(0, str(REPO / 'tools'))
from release_projection import load_source

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

projection = HERE / 'release_07717' / 'release_projection_07717.json'
release = load_source('character_designer', projection, root=REPO)
baseline_path = HERE.parent / 'animation_in_front_20261010' / 'release_07716' / 'release_projection_07716.json'
baseline = load_source('character_designer', baseline_path, root=REPO)
changed = sorted(str(path).replace('\\', '/') for path, content in release.files.items()
                 if baseline.files.get(path) != content)
assert changed == ['__init__.py', 'animation_link_source.py', 'bone_rest_lengths.py', 'unity_export_worker.py']
assert not set(baseline.files) - set(release.files)
targets = [Path(r'C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\character_designer'),
           Path(r'D:\Blender\Projects\Character\X\addons\character_designer')]
# The Shoes task subsequently released 0.77.18 from this 0.77.17 projection.
# Preserve that newer delivery and verify our three runtime patch files remain
# byte-identical, rather than downgrading the shared add-on to close this task.
current_projection = HERE.parent / 'shoes_binding_20261010' / 'release_07718' / 'release_projection_07718.json'
current = load_source('character_designer', current_projection, root=REPO)
additional_changes = sorted(str(path).replace('\\', '/') for path, content in current.files.items()
                            if release.files.get(path) != content)
assert additional_changes == ['__init__.py', 'quick_bind.py']
assert current.files[Path('__init__.py')].replace(b'(0, 77, 18)', b'(0, 77, 17)', 1) == release.files[Path('__init__.py')]
assert set(current.files) == set(release.files)
for target in targets:
    assert all((target / path).read_bytes() == content for path, content in current.files.items())
    assert all((target / path).read_bytes() == release.files[path] for path in
               map(Path, ['bone_rest_lengths.py', 'animation_link_source.py', 'unity_export_worker.py']))
for path, content in release.files.items():
    if path.suffix == '.py':
        ast.parse(content, filename=str(path))
archive = REPO / 'dist' / 'character_designer-0.77.17.zip'
with zipfile.ZipFile(archive) as package:
    assert package.testzip() is None
    assert set(package.namelist()) == {'character_designer/' + path.as_posix() for path in release.files}
    assert all(package.read('character_designer/' + path.as_posix()) == content
               for path, content in release.files.items())
protected = json.loads((HERE / 'artist_file_integrity_before.json').read_text(encoding='utf-8'))
assert all(digest(Path(path)) == data['sha256'] for path, data in protected.items())
real = json.loads((HERE / 'probe_cosha_roundtrip_report_verified.json').read_text(encoding='utf-8'))
runtime = json.loads((HERE / 'installed_runtime_verification.json').read_text(encoding='utf-8'))
current_runtime = json.loads((HERE / 'installed_runtime_verification_07718.json').read_text(encoding='utf-8'))
assert real['passed'] and runtime['passed'] and current_runtime['passed']
max_mesh_delta = max(mesh['max_world_coordinate_error_meters']
                     for sample in real['samples'].values() for mesh in sample['meshes'].values())
report = {
    'date': '2026-10-10', 'version': release.version, 'files': len(release.files),
    'projection': str(projection), 'projection_sha256': release.projection_sha256,
    'changed_files_from_07716': changed, 'archive': str(archive), 'archive_sha256': digest(archive),
    'current_installed_version': current.version, 'current_projection': str(current_projection),
    'current_projection_sha256': current.projection_sha256,
    'subsequent_release_changes': additional_changes, 'bone_length_patch_retained_exactly': True,
    'destinations': [str(target) for target in targets], 'deployment_mismatches': 0,
    'deployment_backup': r'C:\Users\Randy\AppData\Local\CodexBackups\addon-deploy\20261010-190552-465068e9',
    'protected_artist_source_files': protected, 'protected_files_unchanged': True,
    'generic_blender_log': str(HERE / 'test_bone_rest_lengths_blender_final.log'),
    'real_model_report': str(HERE / 'probe_cosha_roundtrip_report_verified.json'),
    'bone_count': real['rest_comparison']['bone_count'], 'restored_terminal_bones': real['restored_bones'],
    'max_head_error': real['rest_comparison']['max_head_error'],
    'max_rest_matrix_component_error': real['rest_comparison']['max_rest_matrix_error'],
    'max_mesh_world_coordinate_component_error_meters': max_mesh_delta,
    'weights_shape_keys_inventory_unchanged': real['weights_and_shape_keys_inventory_unchanged'],
    'native_action_unchanged': real['native_action_unchanged'],
    'installed_runtime_report': str(HERE / 'installed_runtime_verification.json'),
    'current_installed_runtime_report': str(HERE / 'installed_runtime_verification_07718.json'),
    'artist_runtime_refreshed': False, 'artist_scene_modified_or_saved': False,
    'Unity_assets_written': False, 'Unity_editor_tests_or_compile': False,
    'git_committed': False, 'git_pushed': False, 'background_Blender_jobs_completed': True,
    'model_and_reasoning_effort': 'unrecorded',
    'limitations': ['Fresh CD export and new source import required; existing caches unchanged.',
                    'Only CD source import uses this metadata hook; manual FBX import is unchanged.',
                    'Actual Unity Editor roundtrip not rerun; texture and Forearm publication excluded from real-model fixture.'],
    'passed': True,
}
(HERE / 'delivery_07717.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({key: report[key] for key in ['version', 'files', 'archive_sha256', 'deployment_mismatches',
                                             'protected_files_unchanged', 'restored_terminal_bones', 'passed']}, indent=2))
