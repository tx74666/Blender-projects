"""Finish the already checked X save after native recovered-file Save refusal."""
import datetime
import hashlib
import json
import time
import traceback
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT / 'live_refresh_save_20261005_161922_650499.json'
ARTIST = ROOT.parents[1] / 'X.blend'


def run(*, previous_editor, expected_artist_sha=None):
    report = {'status': 'starting', 'saved': False, 'prior': str(PRIOR)}
    output = ROOT / ('finish_live_save_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
    area = bpy.context.area
    restored = False
    try:
        assert not bpy.app.background and area.type == 'CONSOLE'
        assert previous_editor == {'type': 'NODE_EDITOR', 'ui_type': 'GeometryNodeTree'}
        assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
        old = json.loads(PRIOR.read_text(encoding='utf8'))
        assert old['phase'] == 'save_artist' and not old['saved']
        assert old['error'] == 'Error: Cannot change old file (file saved with @)\n'
        assert set(old['checks']) == {'after_refresh', 'after_native_foldouts', 'after_draw_measurement'}
        expected_disk = expected_artist_sha or old['artist_before']['sha256']
        assert isinstance(expected_disk, str) and len(expected_disk) == 64
        assert hashlib.sha256(ARTIST.read_bytes()).hexdigest() == expected_disk
        report['disk_sha_before'] = expected_disk
        assert hashlib.sha256(Path(old['recovery']['path']).read_bytes()).hexdigest() == old['recovery']['sha256']
        live = ROOT / 'live_refresh_save.py'
        assert hashlib.sha256(live.read_bytes()).hexdigest() == '088aeed7dba391bcc29f9c577d5890a8869c60e5cea0d2d6b96d889e926e5c48'
        scope = {'__file__': str(live), '__name__': '_cd_finish_reader'}
        exec(compile(live.read_bytes(), str(live), 'exec'), scope)
        readers = scope['load_definitions'](scope['SNAPSHOT'], '_cd_finish_asset_readers')
        modules = readers.runtime()
        assert tuple(modules['addon'].bl_info['version']) == (0, 76, 2)
        modules['addon']._validate_registration_integrity()
        readers.no_live_preview(modules)
        from character_designer import unity_export as exporter, unity_export_ui as ui
        assert not exporter.export_running()
        rig, config = ui._config(bpy.context)
        hair = readers.find_source(modules['hair_bones_rig'])
        helpers = readers.read_helpers(modules)
        helpers.ALLOWED_METADATA = set()
        before = helpers.asset_fingerprint(hair)
        assert all(before[f] == old['assets_before'][f] for f in ('sha256', 'portable_sha256', 'counts'))
        selection = readers.selection_snapshot()
        assert selection == old['selection_before']
        config_before = scope['config_state'](config)
        assert json.loads(json.dumps(config_before)) == old['config_before']
        pose = readers.full_pose(modules, helpers)
        display = readers.display_snapshot(modules)
        texts = readers.text_snapshot(modules['hair_wiggle_adapter'])
        report.update(version=[0, 76, 2], runtime=bpy.app.version_string, assets_before=before,
                      selection_before=selection, recovery_verified=True, asset_preflight_exact=True)
        readers.restore_editor(area, previous_editor)
        assert area.type == 'NODE_EDITOR' and area.ui_type == 'GeometryNodeTree'
        restored = True
        report['save_attempts'] = []
        for attempt in range(3):
            try:
                result = bpy.ops.wm.save_as_mainfile(filepath=str(ARTIST), copy=False, check_existing=False)
                report['save_attempts'].append({'attempt': attempt + 1, 'result': sorted(result)})
                break
            except RuntimeError as exc:
                report['save_attempts'].append({'attempt': attempt + 1, 'error': str(exc)})
                if str(exc) != 'Error: Cannot change old file (file saved with @)\n' or attempt == 2:
                    raise
                time.sleep(0.25)
        report['save_result'] = sorted(result)
        assert result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == ARTIST.resolve()
        report['saved'] = True
        after = helpers.asset_fingerprint(hair)
        assert all(after[f] == before[f] for f in ('sha256', 'portable_sha256', 'counts'))
        assert readers.selection_snapshot() == selection
        assert readers.display_snapshot(modules) == display
        assert readers.text_snapshot(modules['hair_wiggle_adapter']) == texts
        assert scope['config_state'](rig.character_designer_unity_export) == config_before
        pose_result = readers.check_pose(pose, modules)
        report.update(status='passed', assets_exact=True, selection_exact=True, display_exact=True,
                      texts_exact=True, export_config_exact=True, pose=pose_result,
                      editor_restored={'type': area.type, 'ui_type': area.ui_type},
                      artist_after=scope['disk'](ARTIST))
    except Exception as exc:
        report.update(status='failed', error=str(exc), traceback=traceback.format_exc())
    finally:
        if not restored and area and area.type == 'CONSOLE':
            area.type = previous_editor['type']
            area.ui_type = previous_editor['ui_type']
        report['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
        print('FINISH_FOLDOUT_SAVE', report['status'], report.get('error', ''), str(output), flush=True)
    return report
