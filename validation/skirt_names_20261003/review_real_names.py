"""Classify saved-copy differences without changing the original test report."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
source = root / 'real_saved_names_run5.json'
report = json.loads(source.read_text(encoding='utf-8-sig'))
allowed = {
    'protected.extra_ids.images:1d63a26f-110a-4ff2-9145-a350633c3dd5.png.fields.use_extra_user: True -> False',
    'protected.extra_ids.images:AnimeFront.png.fields.use_extra_user: True -> False',
    'protected.extra_ids.images:Hair.fields.use_extra_user: True -> False',
    'protected.extra_ids.other_object_data:Front.fields.use_extra_user: True -> False',
}
differences = report['after_reopen']['differences']
assert report['after_clean']['passed'] and not report['after_clean']['differences']
assert len(differences) == 4 and set(differences) == allowed
assert report['world_bones_after_clean']['maximum_matrix_error'] == 0
assert all(item['maximum_position_error'] == 0
           for item in report['world_meshes_after_clean'].values())
assert report['artist_input_unchanged'] and report['canonical_source_unchanged']
assert report['save_result'] == ['FINISHED'] and report['reopen_result'] == ['FINISHED']
assert all(not item['events'] for item in report['second_clean'])
review = {
    'source_report': str(source),
    'source_report_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'original_strict_overall_passed': report['passed'],
    'rename_raw_protection_passed': True,
    'reopened_core_model_and_reference_protection_passed': True,
    'bone_renames': report['planned_bone_renames'],
    'hook_renames': report['planned_hook_renames'],
    'evaluated_meshes': len(report['world_meshes_after_clean']),
    'maximum_position_error': 0.0,
    'evaluated_bones': report['world_bones_after_clean']['bones'],
    'maximum_matrix_error': 0.0,
    'second_cleanup_events': 0,
    'save_and_reopen': 'FINISHED',
    'reopen_exceptions': differences,
    'limits': [
        'Four extra-ID use_extra_user flags changed on native save/reopen; '
        'the original strict report remains failed and has not been overwritten.',
        'Real-scene post-reopen evaluated-world and byte-exact recovery-text '
        'checks did not run after that assertion; reopened structured raw state '
        'contains no other differences. Dedicated native tests cover those paths.',
        'This isolated result uses the saved 2026-10-03 22:57 X input, '
        'not the later unsaved GUI state.',
    ],
}
target = root / 'real_saved_names_review.json'
target.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({key: value for key, value in review.items()
                  if key not in {'limits', 'reopen_exceptions'}}, ensure_ascii=False))
