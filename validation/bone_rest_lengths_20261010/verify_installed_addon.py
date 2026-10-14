"""Enable the installed release in a disposable factory Blender session."""
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
ADDONS = Path(r'C:\Users\Randy\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons')
sys.path.insert(0, str(ADDONS))
expected_version = tuple(int(part) for part in os.environ.get('CD_VERIFY_INSTALLED_VERSION', '0.77.17').split('.'))
report_name = 'installed_runtime_verification.json' if expected_version == (0, 77, 17) else 'installed_runtime_verification_07718.json'
report = {'blender': bpy.app.version_string, 'saved_artist_scene': False}
try:
    result = bpy.ops.preferences.addon_enable(module='character_designer')
    assert 'FINISHED' in result
    import character_designer
    from character_designer import animation_link_source, bone_rest_lengths
    assert character_designer.bl_info['version'] == expected_version
    assert Path(character_designer.__file__).resolve().parent == ADDONS / 'character_designer'
    assert bone_rest_lengths.SCHEMA == 'cdesigner.bone-rest-lengths/1'
    assert 'bone_rest_lengths.restore(' in inspect.getsource(animation_link_source._import_prepared_source)
    report.update(version=list(character_designer.bl_info['version']),
                  installed_source=character_designer.__file__,
                  helper_sha256=hashlib.sha256(Path(bone_rest_lengths.__file__).read_bytes()).hexdigest())
    result = bpy.ops.preferences.addon_disable(module='character_designer')
    assert 'FINISHED' in result
    assert 'character_designer' not in bpy.context.preferences.addons
    report['passed'] = True
finally:
    (HERE / report_name).write_text(json.dumps(report, indent=2), encoding='utf-8')
print('INSTALLED_BONE_LENGTH_RELEASE_OK', json.dumps(report, sort_keys=True))
