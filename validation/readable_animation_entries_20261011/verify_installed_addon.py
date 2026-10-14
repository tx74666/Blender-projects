"""Verify a real readable entry through installed CD in a disposable factory scene."""
from datetime import datetime, timezone
import importlib
import inspect
import json
import os
from pathlib import Path
import traceback

import bpy

HERE = Path(__file__).resolve().parent
INSTALLED = Path(r'C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\character_designer')
ENTRY = Path(r'D:\Blender\Projects\Character\Animation\UnityExports\Animations\RandomRealm2\Cosha\Cosha.workspace.json')

class Layout:
    def __init__(self): self.labels = []
    def box(self): return self
    def row(self, **options): return self
    def label(self, *, text, **options): self.labels.append(text)
    def operator(self, *args, **options): return None

report = {'utc': datetime.now(timezone.utc).isoformat(), 'blender': bpy.app.version_string,
          'entry': str(ENTRY), 'passed': False, 'disabled': False, 'artist_scene_loaded': False,
          'saved_artist_scene': False, 'imported_animation_or_model': False, 'unity_operations': False}
error = None
try:
    assert not bpy.data.filepath and bpy.app.version[:2] == (5, 2)
    assert 'FINISHED' in bpy.ops.preferences.addon_enable(module='character_designer')
    addon = importlib.import_module('character_designer')
    expected_version = tuple(int(part) for part in os.environ.get('CD_VERIFY_INSTALLED_VERSION', '0.77.21').split('.'))
    assert addon.bl_info['version'] == expected_version
    assert Path(addon.__file__).resolve().parent == INSTALLED
    ui = importlib.import_module('character_designer.animation_worklist_ui')
    workspace = importlib.import_module('character_designer.animation_workspace')
    report.update(version=list(addon.bl_info['version']), installed_source=addon.__file__)
    description = bpy.ops.character_designer.worklist_connect.get_rna_type().description
    assert description == 'Open a Unity animation workspace or a readable .workspace.json entry'
    layout = Layout()
    ui.draw_worklist(layout, bpy.context)
    assert 'Scene: ' + bpy.context.scene.name in layout.labels
    expected = json.loads(ENTRY.read_text(encoding='utf-8'))
    actual = workspace.load_workspace(ENTRY)
    assert actual['_manifest_path'] == expected['workspaceManifest']
    before = (len(bpy.data.objects), len(bpy.data.actions), len(bpy.data.scenes))
    assert 'FINISHED' in bpy.ops.character_designer.worklist_connect(filepath=str(ENTRY))
    saved = bpy.context.scene.character_designer_animation_worklist
    assert saved.workspace_path == expected['workspaceManifest']
    assert saved.target_name == 'Cosha'
    assert [row.name for row in saved.catalog] == ['Walk_N']
    assert saved.rig is None and not saved.items
    assert 'FINISHED' in bpy.ops.character_designer.worklist_refresh()
    assert (len(bpy.data.objects), len(bpy.data.actions), len(bpy.data.scenes)) == before
    assert (INSTALLED / 'unity_material_match.py').is_file()
    assert 'bone_rest_lengths.restore(' in (INSTALLED / 'animation_link_source.py').read_text(encoding='utf-8')
    report.update(actual_manifest_path=saved.workspace_path, character=saved.target_name,
                  catalog=[row.name for row in saved.catalog], registered_connect_description=description,
                  connect_and_refresh_passed=True, data_counts_unchanged=True, baseline_material_match_retained=True,
                  bone_length_restore_hook_retained=True, passed=True)
except Exception as caught:
    error = caught
    report['error'] = traceback.format_exc()
finally:
    try:
        if 'character_designer' in bpy.context.preferences.addons:
            assert 'FINISHED' in bpy.ops.preferences.addon_disable(module='character_designer')
        report['disabled'] = 'character_designer' not in bpy.context.preferences.addons
        assert report['disabled']
    except Exception as caught:
        report.update(passed=False, disable_error=traceback.format_exc())
        error = error or caught
    (HERE / 'installed_addon_smoke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('READABLE_WORKSPACE_INSTALLED_SMOKE', 'PASS' if report['passed'] else 'FAIL')
if error:
    raise error
