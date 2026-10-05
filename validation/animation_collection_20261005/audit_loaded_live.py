"""Audit and restore the task's editor; save only with a caller's explicit flag."""
import datetime
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import types
import bpy

FOLDER = Path(__file__).resolve().parent
REPORT = FOLDER / 'live_loaded_r8_audit.json'
report = {'schema': 'character-designer.loaded-release-audit/1',
          'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'activation_performed': False, 'refresh_performed': False,
          'activation_source': 'unrecorded; preflight already reported 0.76.3',
          'saved': False, 'imported': False, 'action_switched': False}
audit_area = bpy.context.area
try:
    helper_path = FOLDER / 'activate_minimal_live.py'
    helper = {'__file__': str(helper_path), '__name__': '_cd_readonly_snapshot'}
    exec(compile(helper_path.read_text(encoding='utf-8'), str(helper_path), 'exec', dont_inherit=True), helper)
    require, sha, digest = helper['require'], helper['sha'], helper['digest']
    main = sys.modules['character_designer']
    require(tuple(main.bl_info['version']) == (0, 76, 3), 'Expected already-loaded 0.76.3.')
    root = Path(main.__file__).resolve().parent
    inventory_path = FOLDER / 'candidate_source_r8_inventory.json'
    before = helper['snapshot'](main)
    disk_before = sha(bpy.data.filepath)
    inventory, installed = helper['validate_inventory'](inventory_path, root)
    main._validate_registration_integrity()
    code_checks = []

    def find_code(code, qualname):
        if code.co_qualname == qualname:
            return code
        for value in code.co_consts:
            if isinstance(value, types.CodeType):
                result = find_code(value, qualname)
                if result is not None:
                    return result
        return None

    CODE_FIELDS = ('co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount',
        'co_nlocals', 'co_stacksize', 'co_flags', 'co_code', 'co_names',
        'co_varnames', 'co_freevars', 'co_cellvars', 'co_name', 'co_qualname',
        'co_firstlineno', 'co_linetable', 'co_exceptiontable')

    def same_constant(actual, expected):
        if type(actual) is not type(expected):
            return False
        if isinstance(actual, types.CodeType):
            return same_code(actual, expected)
        if isinstance(actual, tuple):
            return len(actual) == len(expected) and all(
                same_constant(a, b) for a, b in zip(actual, expected))
        if isinstance(actual, frozenset):
            if len(actual) != len(expected):
                return False
            remaining = list(expected)
            for value in actual:
                for index, candidate in enumerate(remaining):
                    if same_constant(value, candidate):
                        remaining.pop(index)
                        break
                else:
                    return False
            return not remaining
        return actual == expected

    def same_code(actual, expected):
        if type(actual) is not types.CodeType or type(expected) is not types.CodeType:
            return False
        if actual != expected:
            return False
        if actual.co_filename.replace('\\', '/').casefold() != expected.co_filename.replace('\\', '/').casefold():
            return False
        return all(getattr(actual, field) == getattr(expected, field)
                   for field in CODE_FIELDS) and same_constant(actual.co_consts, expected.co_consts)

    for short, names in (
        ('animation', helper['ANIMATION_FUNCTIONS']),
        ('animation_worklist_ui', ('_poll_scan', '_defer_scan', 'draw_worklist')),
    ):
        module = sys.modules['character_designer.' + short]
        compiled = compile(installed[short + '.py'], str(root / (short + '.py')), 'exec', dont_inherit=True)
        functions = [(name, getattr(module, name)) for name in names]
        if short == 'animation_worklist_ui':
            functions.extend((name + '.execute', getattr(module, name).execute)
                             for name in helper['NEW_OPERATORS'])
        for name, fn in functions:
            require(fn.__qualname__ == name, 'Unexpected runtime function binding: ' + name)
            expected = find_code(compiled, name)
            require(expected is not None, 'Missing compiled expected function: ' + name)
            actual = fn.__code__
            # Preserve native type-sensitive constant equality, supplement every
            # public code field and recursively verify actual source filenames.
            equal = same_code(actual, expected)
            if not equal:
                report['code_difference'] = {field: [repr(getattr(actual, field))[:600],
                                                    repr(getattr(expected, field))[:600]]
                    for field in CODE_FIELDS + ('co_consts', 'co_filename')
                    if getattr(actual, field) != getattr(expected, field)}
            require(equal, 'Loaded function does not match installed release: ' + name)
            code_checks.append(short + '.' + name)
    ui = sys.modules['character_designer.animation_worklist_ui']
    for owner, fields in helper['NEW_FIELDS'].items():
        require(fields <= set(getattr(ui, owner).bl_rna.properties.keys()),
                'Missing release RNA fields: ' + owner)
    for name in helper['NEW_OPERATORS']:
        cls = getattr(ui, name)
        require(bpy.types.Operator.bl_rna_get_subclass_py(cls.bl_rna.identifier) is cls,
                'New operator registration mismatch: ' + name)
    for short in helper['NEW_MODULES']:
        require('character_designer.' + short in sys.modules, 'Release module not loaded: ' + short)
    animation = sys.modules['character_designer.animation']
    collection = sys.modules['character_designer.animation_worklist_collection']
    require(not main.ADDON_REFRESH_PENDING and animation._job is None,
            'Refresh or animation job is active.')
    require(ui._SCAN_PENDING is None and not collection.running(), 'Collection task is active.')
    state = bpy.context.scene.character_designer_animation_worklist
    after = helper['snapshot'](main)
    require(before == after, 'Artist state changed during read-only audit.')
    require(disk_before == sha(bpy.data.filepath), 'Artist disk changed during read-only audit.')
    report.update(status='passed', version=list(main.bl_info['version']),
                  root=str(root), files_exact=len(installed), code_checks=code_checks,
                  registration_integrity=True, new_operators=4, new_rna_fields=6,
                  inventory_sha256=sha(inventory_path), candidate_sha256=inventory['candidate_sha256'],
                  snapshot_before_sha256=digest(before), snapshot_after_sha256=digest(after),
                  artist_state_preserved_during_audit=True, artist_disk_sha256=disk_before,
                  filepath=bpy.data.filepath, dirty=bpy.data.is_dirty,
                  frame=bpy.context.scene.frame_current, mode=bpy.context.mode,
                  active_object=getattr(bpy.context.active_object, 'name', None),
                  selected_objects=[obj.name for obj in bpy.context.selected_objects],
                  action_count=len(bpy.data.actions), worklist_rows=len(state.items),
                  limitations=['No before/after proof for the unrecorded earlier activation.',
                               'No live collection import, Action switch, export or save performed.'])
except Exception as exc:
    import traceback
    report.update(status='failed', error=str(exc), traceback=traceback.format_exc())
finally:
    # This Console was opened by this task in the observed Geometry Nodes area.
    # Restore only that exact current area; never touch another screen or scene.
    try:
        require(audit_area is not None and audit_area.type == 'CONSOLE',
                'Expected the task-owned temporary Console for restoration.')
        expected = deepcopy(before)
        expected['windows'] = [tuple(window[:4]) + ([
            (pointer, 'NODE_EDITOR', 'GeometryNodeTree') if pointer == audit_area.as_pointer()
            else (pointer, area_type, ui_type)
            for pointer, area_type, ui_type in window[4]],)
            for window in before['windows']]
        audit_area.type = 'NODE_EDITOR'
        audit_area.ui_type = 'GeometryNodeTree'
        restored = helper['snapshot'](main)
        require(restored == expected, 'Artist state differs after editor restoration.')
        require(disk_before == sha(bpy.data.filepath), 'Artist disk changed after editor restoration.')
        report['temporary_editor_restored'] = True
        report['artist_state_preserved_after_editor_restore'] = True
        report['snapshot_after_editor_restore_sha256'] = digest(restored)
        if globals().get('SAVE_CURRENT_X_AFTER_AUDIT', False):
            require(report['status'] == 'passed', 'Do not save after an incomplete audit.')
            require(bpy.data.filepath == r'D:\Blender\Projects\Character\X\X.blend',
                    'Save is restricted to the currently authorized artist X path.')
            report['save_authorization'] = 'Direct human message: 搞完記得保存'
            result = bpy.ops.wm.save_mainfile()
            report['save_result'] = sorted(result)
            require(result == {'FINISHED'}, 'Blender did not report FINISHED for artist save.')
            expected_saved = deepcopy(expected)
            expected_saved['dirty'] = False
            require(helper['snapshot'](main) == expected_saved,
                    'Artist state differs after native save.')
            require(not bpy.data.is_dirty, 'Blender still reports unsaved changes.')
            report.update(saved=True, dirty_before_save=report['dirty'], dirty=False,
                          artist_state_preserved_after_save=True,
                          artist_disk_before_sha256=disk_before,
                          artist_disk_sha256=sha(bpy.data.filepath),
                          artist_disk_bytes=Path(bpy.data.filepath).stat().st_size)
    except Exception as exc:
        report.update(status='failed', restoration_error=str(exc))
    report['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('CD_LOADED_AUDIT', report['status'], report.get('error', ''), str(REPORT))
