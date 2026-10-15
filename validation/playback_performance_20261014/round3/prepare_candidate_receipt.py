"""Pin the prepared candidate and existing evidence; no Blender or deployment."""
import ast
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sys
import zipfile

FOLDER = Path(__file__).resolve().parent
REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path.insert(0, str(REPO / 'tools'))
from release_projection import load_source


def pin(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'path': str(path.resolve()), 'sha256': digest.hexdigest(), 'bytes': path.stat().st_size}


def without_metadata_version(text):
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'bl_info'
                                               for target in node.targets):
            for index, key in enumerate(node.value.keys):
                if isinstance(key, ast.Constant) and key.value == 'version':
                    node.value.values[index] = ast.Constant(value='ignored metadata version')
    return ast.dump(tree, include_attributes=False)


def main():
    source = load_source('character_designer', root=REPO)
    assert source.version == '0.77.41'
    archive = REPO / 'dist' / 'character_designer-0.77.41.zip'
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        actual = {entry.filename: package.read(entry) for entry in package.infolist() if not entry.is_dir()}
    expected = {'character_designer/' + relative.as_posix(): content
                for relative, content in source.files.items()}
    assert actual == expected
    with zipfile.ZipFile(REPO / 'dist' / 'character_designer-0.77.40.zip') as old_package:
        old_init = old_package.read('character_designer/__init__.py').decode('utf-8-sig')
    init_path = REPO / 'addons' / 'character_designer' / '__init__.py'
    assert without_metadata_version(old_init) == without_metadata_version(init_path.read_text(encoding='utf-8-sig'))
    paired = json.loads((FOLDER / 'rest_and_blend_abba_report.json').read_text(encoding='utf-8'))
    native = json.loads((FOLDER / 'rest_snapshot_native_report.json').read_text(encoding='utf-8'))
    assert paired['completed'] and native['completed']
    assert all(block['outputs_equal_to_baseline'] and not block['errors'] for block in paired['blocks'])
    for record in paired['candidate_sources']:
        assert pin(record['path']) == record
    artist = pin(FOLDER.parents[2] / 'X.blend')
    assert artist == paired['artist_after'] == paired['artist_before']
    evidence_names = (
        'rest_and_blend_abba_report.json', 'rest_snapshot_native_report.json',
        'follow_math_native.log', 'rest_snapshot_native.log', 'rest_projection_native.log',
        'forearm_cache_native.log', 'forearm_recovery_native.log', 'unity_animation_native.log',
        'rest_proof_pure_receipt.json', 'matrix_reuse_candidate_receipt.json',
        'profile_rest_snapshot.py', 'live_observe.py', 'live_profiler.py',
    )
    baseline = [pin(FOLDER / 'baseline_07740' / name) for name in
                ('unity_animation.py', 'animation_worklist_target.py',
                 'forearm_twist.py', 'forearm_twist_math.py')]
    baseline_blocks = [block['median_ms'] for block in paired['blocks'] if block['label'] == 'baseline_07740']
    combined_blocks = [block['median_ms'] for block in paired['blocks'] if block['label'] == 'combined']
    receipt = {
        'schema': 'x.playback-round3-prepared-candidate/1',
        'prepared': True, 'goal_complete': False,
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'package': pin(archive), 'package_files': len(expected),
        'package_equal_to_canonical': True,
        'candidate_version': '0.77.41', 'native_measurement_metadata_version': '0.77.40',
        'post_validation_init_change': 'AST differs only in bl_info version; verified against released 0.77.40 ZIP',
        'runtime_sources': [pin(init_path)] + [pin(record['path']) for record in paired['candidate_sources']],
        'baseline_sources': baseline, 'evidence': [pin(FOLDER / name) for name in evidence_names],
        'imported_instrumentation_witness_helper': {
            **pin(FOLDER.parent / 'profile_saved_forearm_display.py'),
            'collection_scope': 'Closeout-only pin; the paired measurement did not record this auxiliary hash itself',
        },
        'artist': artist,
        'observed_background_results': {
            'baseline_block_medians_ms': baseline_blocks,
            'combined_block_medians_ms': combined_blocks,
            'midpoint_improvement_percent': (1 - (sum(combined_blocks) / len(combined_blocks))
                                                / (sum(baseline_blocks) / len(baseline_blocks))) * 100,
            'blocks': len(paired['blocks']), 'hot_frames_per_block': len(paired['frames']),
            'all_observed_outputs_equal': True,
        },
        'deployed': False, 'refreshed_live_artist': False, 'artist_saved': False,
        'live_artist_module_version': 'unobserved', 'actual_gui_fps': 'unmeasured',
        'gui_control': 'physical Escape stopped Computer Use; explicit recovery question still pending',
        'model_and_reasoning_effort': 'unrecorded',
        'pending': [
            'Observe current artist runtime and actual warmed Material/Solid/side-panel playback after resumed permission',
            'Attribute repeated frame/depsgraph and panel draw costs, then adopt worthwhile remaining optimization',
            'Validate final candidate, deploy/check, preserve artist work and verify temporary profiler cleanup',
        ],
    }
    (FOLDER / 'prepared_candidate_07741.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    work_path = FOLDER / 'current_work.json'
    work = json.loads(work_path.read_text(encoding='utf-8'))
    work.update(state='PREPARED_07741_GUI_PENDING', prepared_candidate='prepared_candidate_07741.json',
                source_version='0.77.41 prepared candidate', deployed=False, refreshed=False,
                no_version_bump_deploy_or_artist_save_yet=False,
                no_deploy_refresh_or_artist_save=True)
    work_path.write_text(json.dumps(work, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'package': receipt['package'], 'files': len(expected),
                      'background_midpoint_improvement_percent': receipt['observed_background_results']['midpoint_improvement_percent'],
                      'goal_complete': False, 'deployed': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
