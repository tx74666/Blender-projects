import hashlib
import json
from pathlib import Path
import sys
import bpy
import bmesh

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
character_designer.register()
obj = bpy.data.objects['Cosha']
rig = bpy.data.objects['CoshaRig']
bpy.context.scene.character_designer_setup.rig = rig
bpy.context.scene.character_designer_setup.body = obj
def fingerprint():
    parts = [tuple(tuple(v.co) for v in obj.data.vertices),
             tuple(tuple((w.group, w.weight) for w in v.groups) for v in obj.data.vertices),
             tuple((k.name, k.value, tuple(tuple(v.co) for v in k.data)) for k in obj.data.shape_keys.key_blocks)]
    return hashlib.sha256(repr(parts).encode()).hexdigest()
before = fingerprint()
result = bpy.ops.character_designer.unity_locate_unweighted(object_name='Cosha')
assert result == {'FINISHED'}
bm = bmesh.from_edit_mesh(obj.data)
bm.verts.index_update()
selected = [v.index for v in bm.verts if v.select]
assert selected == [3574, 3575], selected
bpy.ops.object.mode_set(mode='OBJECT')
after = fingerprint()
assert before == after
report = {'passed': True, 'selected': selected, 'geometryWeightsKeysUnchanged': before == after,
          'before': before, 'after': after, 'sourceSaved': False,
          'note': 'Operator ran in isolated background Blender; live window not changed.'}
Path(r'D:\Blender\Projects\Character\X\outputs\unity_warning_diagnostics\locator_result.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('COSHA_LOCATOR_PASSED', json.dumps(report), flush=True)
