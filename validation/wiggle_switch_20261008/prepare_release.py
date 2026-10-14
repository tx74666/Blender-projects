"""Freeze the approved 0.77.4 package with only the canonical Wiggle changes."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
HERE = Path(__file__).resolve().parent
DEST = HERE / 'approved_release_0775' / 'addons' / 'character_designer'
CANON = REPO / 'addons' / 'character_designer'
BASE = REPO / 'dist' / 'character_designer-0.77.4.zip'


def replace_once(text, old, new):
    assert text.count(old) == 1, repr(old)
    return text.replace(old, new, 1)


with zipfile.ZipFile(BASE) as archive:
    payload = {name.split('/', 1)[1]: archive.read(name) for name in archive.namelist()
               if not name.endswith('/')}
assert len(payload) == 148
before = dict(payload)
for name in ('__init__.py', 'body_original_mode.py', 'skirt_wiggle.py', 'skirt_wiggle_ui.py'):
    payload[name] = (CANON / name).read_bytes()

text = payload['skirt.py'].decode('utf-8')
text = replace_once(text, '        from . import body_original_mode, skirt_original_mode\n',
    '        from .skirt_wiggle_ui import draw_wiggle_motion\n'
    '        draw_wiggle_motion(layout, context, source, record)\n'
    '        from . import body_original_mode, skirt_original_mode\n')
text = replace_once(text,
    '        else:\n            layout.operator("character_designer.skirt_add_physics", icon="PHYSICS")\n',
    '        elif getattr(context.window_manager, "character_designer_dress_wiggle_advanced", False):\n'
    '            layout.operator("character_designer.skirt_add_physics", icon="PHYSICS")\n')
payload['skirt.py'] = text.encode('utf-8')

text = payload['skirt_rig.py'].decode('utf-8')
text = replace_once(text, '    _activate(context, rig, "POSE")\n    wanted = record["controls"]["waist"]\n',
    '    _activate(context, rig, "POSE")\n'
    '    from . import bone_display\n'
    '    controls, deform, mechanism = _bone_collection_layout(record)\n'
    '    for name in controls | deform | mechanism:\n'
    '        bone_display._set_hidden(rig, rig.data.bones[name], name not in controls)\n'
    '    rig.data.show_bone_custom_shapes = True\n'
    '    wanted = record["controls"]["waist"]\n')
payload['skirt_rig.py'] = text.encode('utf-8')
text = replace_once(text, 'def _clear_source_properties(source):\n',
    'def _clear_source_properties(source):\n'
    '    from . import skirt_wiggle\n'
    '    source.pop(skirt_wiggle.STATE_KEY, None)\n'
    '    source.pop(skirt_wiggle.STATE_SCENE_KEY, None)\n')
text = replace_once(text, '    # No user-owned child is deleted with its generated parent.\n',
    '    from . import skirt_wiggle\n'
    '    if skirt_wiggle.STATE_KEY in obj:\n'
    '        skirt_wiggle.forget(context, obj)\n'
    '    # No user-owned child is deleted with its generated parent.\n')
payload['skirt_rig.py'] = text.encode('utf-8')

text = payload['skirt_shared_rig.py'].decode('utf-8')
text = replace_once(text, '    # Blender operator supplies Undo for a committed removal.\n',
    '    # Blender operator supplies Undo for a committed removal.\n'
    '    from . import skirt_wiggle\n'
    '    if skirt_wiggle.STATE_KEY in source:\n'
    '        skirt_wiggle.forget(context, source)\n')
payload['skirt_shared_rig.py'] = text.encode('utf-8')

text = payload['unity_export.py'].decode('utf-8')
text = replace_once(text, "    objects = collected['objects']\n    hair_motion = _capture_hair_motion(objects)\n",
    "    objects = collected['objects']\n"
    "    from . import skirt_wiggle\n"
    "    for source in objects:\n"
    "        if source.type == 'MESH':\n"
    "            skirt_wiggle.suspend(context, source=source,\n"
    "                                 reason='Model export paused automatic Dress motion.')\n"
    "    hair_motion = _capture_hair_motion(objects)\n")
payload['unity_export.py'] = text.encode('utf-8')

DEST.mkdir(parents=True, exist_ok=True)
for name, content in payload.items():
    path = DEST / name
    if path.suffix == '.py':
        ast.parse(content, filename=name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
changed = sorted(name for name in payload if payload[name] != before.get(name))
assert changed == sorted(('__init__.py', 'body_original_mode.py', 'skirt.py', 'skirt_rig.py', 'skirt_shared_rig.py',
                          'skirt_wiggle.py', 'skirt_wiggle_ui.py', 'unity_export.py')), changed
manifest = {'schema_version': 1, 'module': 'character_designer', 'version': '0.77.5',
            'source_root': str(DEST),
            'source_provenance': {'base_archive': str(BASE),
                'base_sha256': hashlib.sha256(BASE.read_bytes()).hexdigest(),
                'canonical_repository': str(REPO), 'changed_files': changed,
                'scope': 'Wiggle 2 Automatic/Manual and Dress display; held Cloth/Direct work excluded'},
            'files': {name: hashlib.sha256(content).hexdigest() for name, content in sorted(payload.items())}}
path = DEST.parents[1] / 'release_projection.json'
path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'projection': str(path), 'files': len(payload), 'changed': changed}, ensure_ascii=False))
