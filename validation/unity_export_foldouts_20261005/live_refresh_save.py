"""Paused X integration only: refresh UI code, measure drawing, preserve assets.

No material is added/removed, export is started, or pose/frame is changed.
Execute definitions from the native Console, then call run(previous_editor=...).
"""
import datetime
import hashlib
import json
import statistics
import time
import traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy

FOLDER = Path(__file__).resolve().parent
ARTIST = (FOLDER.parents[1] / 'X.blend').resolve()
VERSION = (0, 76, 2)
SNAPSHOT = FOLDER.parent / 'hair_motion_20261004' / 'live_install_refresh_config_save.py'
SNAPSHOT_SHA = '2024268eaf4a912d5b03453c8fc8ea1bcc555b8c70a900b732207ae96f26c437'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_definitions(path, name):
    scope = {'__file__': str(path), '__name__': name}
    exec(compile(path.read_bytes(), str(path), 'exec'), scope)
    return SimpleNamespace(**scope)


def disk(path):
    return {'path': str(path), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'modified_local': datetime.datetime.fromtimestamp(path.stat().st_mtime).isoformat()}


def config_state(config):
    return {'directory': config.directory, 'filename': config.filename,
            'asset_id': config.asset_id, 'last_status': config.last_status,
            'last_report': config.last_report,
            'extras': [(item.object.as_pointer() if item.object else None, item.enabled) for item in config.extras],
            'simple_materials': [(item.material.as_pointer() if item.material else None) for item in config.simple_materials],
            'foldouts': (config.show_objects, config.show_materials, config.show_warnings),
            'foldout_property_presence': {field: config.is_property_set(field)
                                         for field in ('show_objects', 'show_materials', 'show_warnings')}}


def installed_export_paths(modules, exporter, ui):
    root = modules['installed_source'].parent
    paths = {'unity_export': Path(exporter.__file__).resolve(),
             'unity_export_ui': Path(ui.__file__).resolve()}
    require(all(path.parent == root for path in paths.values()),
            'A Unity Export module is loaded from a different package.')
    return {'installed_root': str(root), **{name: str(path) for name, path in paths.items()}}


def measure(ui, exporter, rig, config):
    """Paired live native data, recording layout; never measure viewport/FPS."""
    bench = load_definitions(FOLDER / 'benchmark_foldouts.py', '_cd_foldout_live_benchmark')
    require(bench.file_hash(bench.BASELINE) == bench.BASELINE_SHA256, 'The frozen baseline changed.')
    saved = config.show_objects, config.show_materials, config.show_warnings
    presence = {field: config.is_property_set(field) for field in ('show_objects', 'show_materials', 'show_warnings')}
    result = {'scope': 'Python draw only with real artist bpy data and RecordingLayout; no click-to-screen/FPS measurement',
              'samples_per_condition': 5, 'warmups_per_condition': 1, 'conditions': {}}
    try:
        config.show_warnings = False
        with bench.private_baseline(bench.BASELINE) as (old_exporter, old_ui):
            expected = [obj.name for obj in exporter.collect_character(bpy.context, rig, config)['objects']]
            require([obj.name for obj in old_exporter.collect_character(bpy.context, rig, config)['objects']] == expected,
                    'Baseline/current character objects differ.')
            result['objects'] = expected
            for name, (objects_open, materials_open) in zip(bench.MODE_NAMES, bench.MODES):
                config.show_objects, config.show_materials = objects_open, materials_open
                times = {'baseline': [], 'current': []}
                calls = {'baseline': [], 'current': []}
                for iteration in range(6):
                    order = ('baseline', 'current') if iteration % 2 == 0 else ('current', 'baseline')
                    for label in order:
                        module = old_ui if label == 'baseline' else ui
                        with patch.object(module, '_material_choices', wraps=module._material_choices) as material_scan, \
                             patch.object(exporter, '_capture_hair_motion', side_effect=AssertionError('Panel called Hair proof')):
                            begin = time.perf_counter()
                            layout = bench.draw(module)
                            elapsed = (time.perf_counter() - begin) * 1000
                        if label == 'current':
                            require(material_scan.call_count == 0, 'Material body enumerated unused slots.')
                            if materials_open:
                                actions = [r for r in layout.records if r[0] == 'operator'
                                           and r[1] == 'character_designer.unity_simple_material']
                                chosen = {item.material.name for item in config.simple_materials if item.material}
                                require({r[3].material_name for r in actions} == chosen,
                                        'The material body does not match the saved selected materials.')
                                require(all(not r[3].enabled for r in actions), 'The body offers an unselected material.')
                        if iteration:
                            times[label].append(elapsed)
                            calls[label].append(material_scan.call_count)
                result['conditions'][name] = {label: {'samples_ms': values, 'median_ms': statistics.median(values),
                                                     'material_scans': calls[label]} for label, values in times.items()}
    finally:
        config.show_objects, config.show_materials, config.show_warnings = saved
        for field, existed in presence.items():
            if not existed:
                config.property_unset(field)
    return result


def run(*, previous_editor):
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    facts = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'status': 'starting', 'saved': False, 'phase': 'preflight', 'previous_editor': previous_editor}
    report = FOLDER / ('live_refresh_save_' + stamp + '.json')
    area = bpy.context.area
    editor_valid = False
    try:
        require(not bpy.app.background and area and area.type == 'CONSOLE', 'Use the paused native X Console.')
        require(Path(bpy.data.filepath).resolve() == ARTIST, 'Current native file must be X.blend.')
        require(bpy.context.mode in {'OBJECT', 'POSE'}, 'Finish an active edit operation first.')
        require(isinstance(previous_editor, dict) and set(previous_editor) == {'type', 'ui_type'}
                and all(isinstance(value, str) and value for value in previous_editor.values())
                and previous_editor['type'] != 'CONSOLE',
                'Supply the actually observed previous editor type and ui_type.')
        require(previous_editor['type'] in {item.identifier for item in bpy.types.Area.bl_rna.properties['type'].enum_items},
                'The previous editor type is not a native Area enum.')
        editor_valid = True
        require(hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == SNAPSHOT_SHA, 'Reviewed snapshot reader changed.')
        readers = load_definitions(SNAPSHOT, '_cd_foldout_asset_readers')
        modules = readers.runtime()
        addon = modules['addon']
        require(not addon.ADDON_REFRESH_PENDING and not bpy.app.timers.is_registered(addon._reload_addon_deferred),
                'An add-on refresh is already pending.')
        readers.no_live_preview(modules)
        facts['automatic_refresh_plan'] = readers.automatic_refresh_plan()
        from character_designer import unity_export as exporter, unity_export_ui as ui
        facts['installed_export_paths_before'] = installed_export_paths(modules, exporter, ui)
        require(not exporter.export_running(), 'Wait for the active export to finish.')
        rig, config = ui._config(bpy.context)
        hair = readers.find_source(modules['hair_bones_rig'])
        helpers = readers.read_helpers(modules)
        helpers.ALLOWED_METADATA = set()
        before = helpers.asset_fingerprint(hair)
        inputs = readers.full_pose(modules, helpers)
        display = readers.display_snapshot(modules)
        selected = readers.selection_snapshot()
        texts = readers.text_snapshot(modules['hair_wiggle_adapter'])
        export_config = config_state(config)
        facts.update(runtime=bpy.app.version_string, source=str(addon.__file__),
                     version_before=list(addon.bl_info['version']), artist_before=disk(ARTIST),
                     config_before=export_config, selection_before=selected, assets_before=before)
        recovery = FOLDER / ('X_before_foldout_refresh_' + stamp + '.blend')
        require(bpy.ops.wm.save_as_mainfile(filepath=str(recovery), copy=True, check_existing=False) == {'FINISHED'},
                'Independent recovery copy did not finish.')
        require(Path(bpy.data.filepath).resolve() == ARTIST, 'Recovery copy changed the artist filepath.')
        facts['recovery'] = disk(recovery)

        def check(label):
            current = readers.runtime()
            assets = helpers.asset_fingerprint(hair)
            require(all(assets[field] == before[field] for field in ('sha256', 'portable_sha256', 'counts')),
                    label + ': artist raw data changed.')
            pose = readers.check_pose(inputs, current)
            require(readers.display_snapshot(current) == display, label + ': rig display or constraints changed.')
            require(readers.selection_snapshot() == selected, label + ': selection changed.')
            require(readers.text_snapshot(current['hair_wiggle_adapter']) == texts, label + ': existing Texts changed.')
            require(config_state(rig.character_designer_unity_export) == export_config, label + ': export choices changed.')
            facts.setdefault('checks', {})[label] = {'assets_exact': True, 'display_exact': True,
                                                    'selection_exact': True, 'config_exact': True, 'pose': pose,
                                                    'assets_sha256': assets['sha256']}

        facts['phase'] = 'refresh'
        facts['refresh_performed'] = tuple(addon.bl_info['version']) != VERSION
        facts['refresh_reason'] = ('Loaded version differs from installed0.76.2'
                                   if facts['refresh_performed'] else '0.76.2 already loaded; validate existing runtime')
        if facts['refresh_performed']:
            addon._reload_addon_deferred()
        current = readers.runtime()
        require(tuple(current['addon'].bl_info['version']) == VERSION, 'Expected installed Character Designer0.76.2.')
        require(not current['addon'].ADDON_REFRESH_LAST_ERROR, current['addon'].ADDON_REFRESH_LAST_ERROR)
        current['addon']._validate_registration_integrity()
        facts['automatic_refresh_plan_after'] = readers.automatic_refresh_plan()
        check('after_refresh')
        from character_designer import unity_export as exporter, unity_export_ui as ui
        facts['installed_export_paths_after'] = installed_export_paths(current, exporter, ui)
        config = rig.character_designer_unity_export
        require('UNDO' not in ui.CHARACTERDESIGNER_OT_unity_export_section.bl_options, 'Foldout operator is undoable.')
        facts['phase'] = 'native_foldout_checks'
        for section, field in (('OBJECTS', 'show_objects'), ('MATERIALS', 'show_materials')):
            old = getattr(config, field)
            existed = config.is_property_set(field)
            try:
                require(bpy.ops.character_designer.unity_export_section(section=section) == {'FINISHED'}, 'Foldout failed.')
                require(getattr(config, field) != old, 'Foldout did not toggle.')
                require(bpy.ops.character_designer.unity_export_section(section=section) == {'FINISHED'}, 'Foldout failed to return.')
                require(getattr(config, field) == old, 'Foldout state did not return.')
            finally:
                setattr(config, field, old)
                if not existed:
                    config.property_unset(field)
        check('after_native_foldouts')
        facts['phase'] = 'draw_measurement'
        facts['paired_real_artist_draw'] = measure(ui, exporter, rig, config)
        check('after_draw_measurement')
        require(not ui._SIMPLE_MATERIAL_SEARCH, 'A material chooser token was leaked.')
        # Return the temporary editor before saving its artist workspace.
        readers.restore_editor(area, previous_editor)
        require(area.type == previous_editor['type'] and area.ui_type == previous_editor['ui_type'],
                'Temporary editor did not restore exactly before saving.')
        facts['editor_restored_before_save'] = {'type': area.type, 'ui_type': area.ui_type}
        facts['phase'] = 'save_artist'
        result = bpy.ops.wm.save_mainfile()
        facts['save_result'] = sorted(result)
        require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == ARTIST, 'Artist save did not finish.')
        facts['saved'] = True
        facts['artist_after'] = disk(ARTIST)
        check('after_save')
        facts.update(status='passed', phase='complete', version_after=list(current['addon'].bl_info['version']))
    except Exception as exc:
        facts.update(status='failed', error=str(exc), traceback=traceback.format_exc())
    finally:
        if editor_valid and area and area.type == 'CONSOLE':
            try:
                area.type = previous_editor['type']
                area.ui_type = previous_editor['ui_type']
                require(area.type == previous_editor['type'] and area.ui_type == previous_editor['ui_type'],
                        'The previous editor did not restore exactly after failure.')
            except Exception as exc:
                facts['editor_restore_error'] = str(exc)
                facts['editor_restore_traceback'] = traceback.format_exc()
                facts['status'] = 'failed'
        facts['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        report.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf8')
        print('LIVE_EXPORT_FOLDOUT_REFRESH', facts['status'], facts['phase'], facts.get('error', ''), str(report), flush=True)
    return facts
