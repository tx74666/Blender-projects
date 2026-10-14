"""Pure qualification checks against retained real Blender metadata; no bpy/import."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'validate_original20_close_continuation_07736d.py'
BEFORE = ROOT / 'metadata_live_reopen_07736_01/live_D4CB_after_capture_metadata.json'
AFTER = ROOT / 'metadata_live_reopen_07736_01/closed_saved_clone_metadata.json'
DIFF = ROOT / 'metadata_live_reopen_07736_01/live_metadata_diff.json'
REVERSE_BEFORE = ROOT / 'close_continuation_07736_03/live_before_Close_metadata.json'
REVERSE_AFTER = ROOT / 'close_continuation_07736_03/reopened_closed_BF59_metadata.json'


def main():
    started = datetime.now(timezone.utc).isoformat()
    paths = [Path(__file__), SOURCE, BEFORE, AFTER, DIFF, REVERSE_BEFORE, REVERSE_AFTER]
    pins = [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size} for p in paths]
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    compile(tree, str(SOURCE), 'exec')
    names = {'require', 'metadata_encoding', 'metadata_differences', 'qualify_metadata_boundary'}
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(selected) == len(names)
    namespace = {'json': json}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SOURCE), 'exec'), namespace)
    before, after, real_diff = [json.loads(p.read_text(encoding='utf-8')) for p in (BEFORE, AFTER, DIFF)]
    assert pins[2]['sha256'] == '96b2a4f1c6f5ee541f7833d5ac2ba4aee9272d0087c32c5ea5a88307622aab98'
    assert pins[3]['sha256'] == '8b1841ebb97c8984188118e04f95ddc3621006f59a73ab86e8537054ce7accf5'
    rows = []

    def check(name, first, second, label, expected):
        diff = namespace['metadata_differences'](first, second)
        for item in diff:
            item['rna_property'] = real_diff[0]['rna_property'] if item['path'][:5] == real_diff[0]['path'][:5] else {'located': False}
        try:
            row = namespace['qualify_metadata_boundary'](first, second, label, diff, before, after)
            accepted, error = row['qualified_metadata_preservation_verified'], None
        except RuntimeError as exc:
            accepted, error = False, str(exc)
        assert accepted is expected, (name, accepted, expected, error)
        rows.append({'name': name, 'passed': True, 'accepted': accepted, 'difference_count': len(diff), 'error': error})
        print('PASS ' + name)

    check('raw first Close exact', before, deepcopy(before), 'closed_BF59', True)
    check('actual warning at reopened closed boundary', before, after, 'reopened_closed_BF59', True)
    check('actual warning at final closed boundary', before, after, 'final_closed_BF59', True)
    check('same warning before reopen rejected', before, after, 'closed_BF59', False)
    reverse_before, reverse_after = [json.loads(p.read_text(encoding='utf-8')) for p in (REVERSE_BEFORE, REVERSE_AFTER)]
    assert pins[5]['sha256'] == pins[3]['sha256'] and pins[6]['sha256'] == pins[2]['sha256']
    check('actual reverse warning at reopened boundary', reverse_before, reverse_after, 'reopened_closed_BF59', True)
    check('actual reverse warning at final boundary', reverse_before, reverse_after, 'final_closed_BF59', True)
    check('reverse warning before reopen rejected', reverse_before, reverse_after, 'closed_BF59', False)
    changed = deepcopy(reverse_after)
    changed['objects']['Dress_Backup']['modifiers'][0].update(show_viewport=1)
    check('reverse plus boolean-to-integer rejected', reverse_before, changed, 'reopened_closed_BF59', False)
    changed = deepcopy(reverse_after)
    changed['objects']['Dress_Backup']['modifiers'][0]['properties']['inputs']['Socket_6'].update(value=-0.0)
    check('reverse plus signed-zero change rejected', reverse_before, changed, 'reopened_closed_BF59', False)
    for name, change in (
        ('bone color change', lambda x: x['bone_colors'][next(iter(x['bone_colors']))].update(palette='THEME01')),
        ('node group change', lambda x: x['objects']['Dress_Backup']['modifiers'][0]['node_group']['native_id'].update(name='Changed')),
        ('node parameter change', lambda x: x['objects']['Dress_Backup']['modifiers'][0]['properties']['inputs']['Socket_5'].update(value=17)),
        ('different warning text', lambda x: x['objects']['Dress_Backup']['modifiers'][0]['node_warnings'][0].update(message='Different')),
        ('different Object identity', lambda x: x['objects']['Dress_Backup']['id'].update(name='Other')),
        ('boolean to integer', lambda x: x['objects']['Dress_Backup']['modifiers'][0].update(show_viewport=1)),
        ('positive to negative zero', lambda x: x['objects']['Dress_Backup']['modifiers'][0]['properties']['inputs']['Socket_6'].update(value=-0.0)),
    ):
        changed = deepcopy(after)
        change(changed)
        check(name, before, changed, 'reopened_closed_BF59', False)
    first, second = deepcopy(before), deepcopy(after)
    for value in (first, second):
        value['objects']['Dress_Backup']['modifiers'][0]['persistent_uid'] += 1
    check('same warning on a different modifier UID rejected', first, second, 'reopened_closed_BF59', False)
    assert all(hashlib.sha256(Path(p['path']).read_bytes()).hexdigest() == p['sha256'] for p in pins)
    result = {'schema': 'x.validation.close-metadata-qualification-pure/1', 'completed': True, 'passed': True,
        'started_utc': started, 'ended_utc': datetime.now(timezone.utc).isoformat(), 'tests_run': len(rows),
        'failures': 0, 'native_execution_performed': False, 'SDK_calls': 0, 'GUI': False,
        'input_files_unchanged': True, 'input_pins': pins, 'checks': rows}
    (ROOT / 'close_metadata_qualification_07736d_receipt.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('PASS: ' + str(len(rows)) + ' pure metadata checks; no native execution.')


if __name__ == '__main__':
    main()
