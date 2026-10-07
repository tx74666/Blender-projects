"""Verify isolated Actions using the process Main; no temporary Main writes."""
import ast
import hashlib
import json
import sys
from array import array
from pathlib import Path
import bpy

folder = Path(__file__).resolve().parent
sys.path.insert(0, r'D:\Blender\Projects\Character\X\addons')
from character_designer import animation_retarget
tree = ast.parse((folder / 'import_and_backup.py').read_text(encoding='utf-8'))
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in {'fingerprint', 'preview', 'asset_details'}]
exec(compile(ast.Module(body=functions, type_ignores=[]), 'asset_fingerprint', 'exec'))
checkpoint = folder / 'X_before_fist_import.blend'
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == '571831c555e0a363d5833a643ad36ca5660d6a19f41aa63f0e57ae0cb85ca51c'
source = Path(r'D:\Blender\Helper\Asset-Libraries\Costom\Pose Library\Saved\Actions\Fist.asset.blend')
assert hashlib.sha256(source.read_bytes()).hexdigest() == '0092ee46255e2101c72df5e78f0504bfdf789486ea72c2646c8f273cc8713cbb'

def load(path, name):
    with bpy.data.libraries.load(str(path), link=False) as (available, requested):
        assert name in available.actions, (str(path), available.actions)
        requested.actions = [name]
    action = requested.actions[0]
    assert action and action.asset_data and not action.library
    return action

fist = load(source, 'Fist')
arm = load(checkpoint, 'Arm Flat')
original = load(folder / 'arm_pose_original.asset.blend', 'Arm Flat')
external = load(folder / 'arm_pose_library.asset.blend', 'Arm Flat')
assert fingerprint(arm) == fingerprint(original) == fingerprint(external), 'Arm Action data differs'
assert preview(arm) == preview(original) == preview(external), 'Arm preview differs'
assert asset_details(arm) == asset_details(original), 'Original arm asset details differ'
expected_asset = dict(asset_details(arm), catalog_id=fist.asset_data.catalog_id)
assert asset_details(external) == expected_asset, 'External arm details differ'
destination = source.parent / 'Arm Flat.asset.blend'
data = (folder / 'arm_pose_library.asset.blend').read_bytes()
if destination.exists():
    assert destination.read_bytes() == data, 'Existing external destination differs'
else:
    with destination.open('xb') as output:
        output.write(data)
assert destination.read_bytes() == data
receipt = {'verified': True, 'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
           'external_arm': str(destination), 'external_arm_sha256': hashlib.sha256(data).hexdigest(),
           'fist_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'fist_data': fingerprint(fist), 'fist_preview': preview(fist),
           'fist_asset': asset_details(fist), 'arm_data': fingerprint(arm),
           'arm_preview': preview(arm), 'arm_asset': asset_details(arm),
           'blender_version': bpy.app.version_string, 'blender_build': bpy.app.build_hash.decode()}
(folder / 'asset_file_verification.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('FIST_SOURCE_PRESERVED_AND_ARM_EXTERNAL_VERIFIED')
