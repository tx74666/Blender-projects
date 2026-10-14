"""Factory-startup smoke of the installed CD package; never open artist files."""

from datetime import datetime, timezone
import importlib
import inspect
import json
from pathlib import Path
import traceback

import bpy


MODULE = 'character_designer'
EXPECTED = Path(r'C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\character_designer')
REPORT = Path(__file__).with_name('installed_addon_smoke.json')
DESCRIPTION = (
    'Import animations prepared in Unity. Use this workspace\'s animation rig when available; '
    'otherwise create a separate animation scene and import the character. '
    'Keep existing custom edits and the active animation')


class Layout:
    """Capture labels while drawing the factory scene's empty worklist."""

    def __init__(self):
        self.labels = []

    def box(self):
        return self

    def row(self, **_options):
        return self

    def label(self, *, text, **_options):
        self.labels.append(text)

    def operator(self, *_args, **_options):
        return None


def main():
    report = {
        'schema': 'character-designer.installed-addon-smoke/1',
        'utc': datetime.now(timezone.utc).isoformat(),
        'blender_version': bpy.app.version_string,
        'blender_executable': bpy.app.binary_path,
        'expected_addon_directory': str(EXPECTED),
        'addon_version': None,
        'addon_file': None,
        'passed': False,
        'error': '',
        'disabled': False,
        'scope': 'Factory enable, registered UI metadata, empty-scene draw, static bone-hook check, disable. No artist file, import, export, Unity or save.',
    }
    error = None
    try:
        assert bpy.app.version[:2] == (5, 2), bpy.app.version_string
        assert not bpy.data.filepath, 'Smoke must run with --factory-startup.'
        assert (EXPECTED / '__init__.py').is_file(), EXPECTED
        assert 'FINISHED' in bpy.ops.preferences.addon_enable(module=MODULE)
        addon = importlib.import_module(MODULE)
        report['addon_version'] = list(addon.bl_info['version'])
        report['addon_file'] = str(Path(addon.__file__).resolve())
        assert Path(addon.__file__).resolve().parent == EXPECTED.resolve(), addon.__file__
        assert tuple(addon.bl_info['version']) == (0, 77, 19), addon.bl_info['version']
        assert MODULE in bpy.context.preferences.addons
        description = bpy.ops.character_designer.worklist_add_ready.get_rna_type().description
        report['registered_import_prepared_description'] = description
        assert description == DESCRIPTION, description
        ui = importlib.import_module(MODULE + '.animation_worklist_ui')
        assert "box.label(text='Scene: '" in inspect.getsource(ui.draw_worklist)
        layout = Layout()
        ui.draw_worklist(layout, bpy.context)
        report['drawn_labels'] = layout.labels
        assert 'Scene: ' + bpy.context.scene.name in layout.labels, layout.labels
        source = (EXPECTED / 'animation_link_source.py').read_text(encoding='utf-8')
        assert 'bone_rest_lengths.restore(context, rig, lengths, digest, export_name,' in source
        assert (EXPECTED / 'bone_rest_lengths.py').is_file()
        report['bone_rest_lengths_hook_present'] = True
        report['passed'] = True
    except Exception as caught:
        error = caught
        report['error'] = traceback.format_exc()
    finally:
        try:
            if MODULE in bpy.context.preferences.addons:
                assert 'FINISHED' in bpy.ops.preferences.addon_disable(module=MODULE)
            report['disabled'] = MODULE not in bpy.context.preferences.addons
            assert report['disabled']
        except Exception as caught:
            report['passed'] = False
            report['disable_error'] = traceback.format_exc()
            if error is None:
                error = caught
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Installed CD smoke:', 'PASS' if report['passed'] else 'FAIL', str(REPORT))
    if error is not None:
        raise error


if __name__ == '__main__':
    main()
