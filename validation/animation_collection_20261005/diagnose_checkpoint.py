import importlib.util
import json
from pathlib import Path
import sys
import bpy

ROOT = Path('D:/Blender/Projects/Character/X/Validation/animation_collection_20261005')
RUNNER = Path('D:/MyRepository/Blender-addons-by-Randy/tests/verify_animation_worklist_collection_blender.py')
spec = importlib.util.spec_from_file_location('_collection_qa_readonly_helpers', RUNNER)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
assert bpy.app.background and not bpy.data.filepath
sys.path.insert(0, str(ROOT / 'candidate_source_r7/addons'))
import character_designer
character_designer.register()
before = helpers.plain_scene(bpy.context.scene)
def transforms(scene):
    return {obj.name: dict(location=list(obj.location), rotation_mode=obj.rotation_mode,
        rotation_euler=list(obj.rotation_euler), rotation_quaternion=list(obj.rotation_quaternion),
        scale=list(obj.scale), matrix_basis=[list(row) for row in obj.matrix_basis],
        matrix_parent_inverse=[list(row) for row in obj.matrix_parent_inverse],
        parent=obj.parent.name if obj.parent else None) for obj in scene.objects}
raw_before = transforms(bpy.context.scene)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'native_r7_20261005_214820/worklist.blend'))
after = helpers.plain_scene(bpy.data.scenes['Scene'])
raw_after = transforms(bpy.data.scenes['Scene'])
bpy.data.scenes['Scene'].view_layers[0].update()
after_update = helpers.plain_scene(bpy.data.scenes['Scene'])
diffs = []
def compare(old, new, path=''):
    if type(old) is not type(new):
        diffs.append(dict(path=path, before=old, after=new))
    elif isinstance(old, dict):
        for key in sorted(set(old) | set(new)):
            compare(old.get(key), new.get(key), path + '/' + key)
    elif isinstance(old, list):
        if len(old) != len(new):
            diffs.append(dict(path=path, before=len(old), after=len(new)))
        else:
            for index, (left, right) in enumerate(zip(old, new)):
                compare(left, right, path + '/' + str(index))
    elif old != new:
        diffs.append(dict(path=path, before=old, after=new))
compare(before, after)
report = dict(before=before, after=after, differences=diffs, saved=False,
              raw_before=raw_before, raw_after=raw_after, raw_exact=raw_before == raw_after,
              after_update=after_update, evaluated_exact_after_update=before == after_update,
              fixture=str(ROOT / 'native_r7_20261005_214820/worklist.blend'))
(ROOT / 'r7_checkpoint_diagnosis.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(dict(differences=diffs, raw_exact=raw_before == raw_after,
                     evaluated_exact_after_update=before == after_update, saved=False)))
