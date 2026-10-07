"""Validate the exact repair transaction in an isolated Blender process."""
import ast
import json
import sys
from pathlib import Path
import bpy

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root.parent / 'fist_current_file_20261007' / 'approved_release_0772' / 'addons'))
import character_designer
character_designer.register()
checkpoint = root / 'X_before_mirror_diagnosis.blend'
bpy.ops.wm.open_mainfile(filepath=str(checkpoint), load_ui=False)
rig = bpy.data.objects['CoshaRig']
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
tree = ast.parse((root / 'apply_reviewed_repair.py').read_text(encoding='utf-8'))
replacements = {
    'choice': "choice = {'repair_right_arm': True, 'repair_middle_from_left': True, 'source': 'Isolated candidate transaction validation; no artist authorization implied'}",
    'artist': 'artist = checkpoint',
    'report_file': "report_file = folder / 'isolated_repair_transaction.json'",
    'recovery': "recovery = folder / 'isolated_before_transaction.blend'",
}
for node in tree.body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
        if name in replacements:
            node.value = ast.parse(replacements[name]).body[0].value
    if isinstance(node, ast.Assert) and 'bpy.context.area' in ast.unparse(node.test):
        node.test = ast.Constant(True)
ast.fix_missing_locations(tree)
exec(compile(tree, str(root / 'apply_reviewed_repair.py'), 'exec'), {'__file__': str(root / 'apply_reviewed_repair.py'), 'checkpoint':checkpoint})
print('ISOLATED_REPAIR_TRANSACTION_VALIDATED')
