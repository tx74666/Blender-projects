"""Read this task's surviving audit baseline; restore only its Console. No save."""
import gc
import hashlib
import json
from pathlib import Path
import types
import bpy

FOLDER = Path(__file__).resolve().parent
OLD_REPORT = FOLDER / 'live_loaded_r8_audit_post_save_guard_probe.json'
OUT = FOLDER / 'live_saved_state_diagnosis.json'
record = {'schema': 'character-designer.live-save-diagnosis/1',
          'saved_again': False, 'artist_mutation': False, 'baseline_source': str(OLD_REPORT)}
area = bpy.context.area
try:
    old = json.loads(OLD_REPORT.read_text(encoding='utf-8'))
    candidates = [obj.__globals__ for obj in gc.get_objects()
        if type(obj) is types.FunctionType and obj.__name__ == 'same_code'
        and obj.__code__.co_filename.replace('\\', '/').casefold() ==
            str(FOLDER / 'audit_loaded_live.py').replace('\\', '/').casefold()
        and obj.__globals__.get('report', {}).get('started_utc') == old['started_utc']]
    contexts = {id(context): context for context in candidates}
    if len(contexts) != 1:
        raise RuntimeError('Exact original in-memory audit baseline is unavailable or ambiguous.')
    context = next(iter(contexts.values()))
    expected = context['expected_saved']
    helper, main = context['helper'], context['main']
    if area is None or area.type != 'CONSOLE':
        raise RuntimeError('Expected the owned temporary Console.')
    area.type = 'NODE_EDITOR'
    area.ui_type = 'GeometryNodeTree'
    actual = helper['snapshot'](main)
    differences = []

    def diff(left, right, path='$'):
        if type(left) is not type(right):
            differences.append({'path': path, 'before_type': type(left).__name__,
                                'after_type': type(right).__name__})
            return
        if isinstance(left, dict):
            for name in sorted(set(left) | set(right)):
                if name not in left or name not in right:
                    differences.append({'path': path + '.' + str(name), 'presence_changed': True})
                else:
                    diff(left[name], right[name], path + '.' + str(name))
        elif isinstance(left, (list, tuple)):
            if len(left) != len(right):
                differences.append({'path': path, 'before_count': len(left), 'after_count': len(right)})
            else:
                for index, (a, b) in enumerate(zip(left, right)):
                    diff(a, b, path + '[' + str(index) + ']')
        elif left != right:
            differences.append({'path': path, 'before': str(left)[:500], 'after': str(right)[:500]})

    diff(expected, actual)
    record.update(status='passed' if not differences else 'failed', differences=differences,
        expected_sha256=helper['digest'](expected), actual_sha256=helper['digest'](actual),
        original_baseline_found=True, temporary_editor_restored=True,
        dirty=bpy.data.is_dirty, filepath=bpy.data.filepath,
        disk_sha256=helper['sha'](bpy.data.filepath), disk_bytes=Path(bpy.data.filepath).stat().st_size,
        save_result=old.get('save_result'), original_runtime_audit_passed=old.get('artist_state_preserved_during_audit'),
        limitation='First immediate-save check failed; its differing fields were not captured.')
except Exception as exc:
    import traceback
    record.update(status='failed', error=str(exc), traceback=traceback.format_exc())
finally:
    if area is not None and area.type == 'CONSOLE':
        area.type = 'NODE_EDITOR'
        area.ui_type = 'GeometryNodeTree'
        record['temporary_editor_restored'] = True
    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print('CD_SAVED_STATE_DIAGNOSIS', record['status'], str(OUT))
