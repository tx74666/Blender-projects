"""Fresh user-preferences startup check: no manual add-on enable or scene save."""
import hashlib
import json
from pathlib import Path
import sys

import bpy

path = Path(bpy.data.filepath)
before = hashlib.sha256(path.read_bytes()).hexdigest()
module = sys.modules.get('character_designer')
assert module is not None, 'Character Designer did not start from saved preferences'
assert module.bl_info['version'] == (0, 38, 0), module.bl_info
assert 'scripts\\addons\\character_designer' in module.__file__, module.__file__
module._validate_registration_integrity()
assert hasattr(bpy.context.window_manager, 'character_designer_hair_bones')
assert bpy.context.window_manager.character_designer_hair_bones.bone_count == 4
bpy.context.scene.frame_set(bpy.context.scene.frame_current)
from character_designer import forearm_twist
assert forearm_twist._RUNTIME_REGISTERED
assert not forearm_twist._INITIALIZE_PENDING
assert not forearm_twist._ERRORS, forearm_twist._ERRORS
assert hashlib.sha256(path.read_bytes()).hexdigest() == before
print('INSTALLED_HAIR_STARTUP_PASS=' + json.dumps({
    'version': module.bl_info['version'], 'module': module.__file__,
    'hair_operators_registered': True, 'forearm_runtime_errors': len(forearm_twist._ERRORS),
    'input_unchanged': before,
}), flush=True)
