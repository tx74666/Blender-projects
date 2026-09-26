"""Verify the deployed add-on in an isolated factory-startup Blender."""
import os
from pathlib import Path
import addon_utils

module = addon_utils.enable('character_designer', default_set=False, persistent=False)
assert module is not None
expected = Path(os.environ['APPDATA']) / 'Blender Foundation/Blender/5.2/scripts/addons/character_designer'
assert Path(module.__file__).resolve().parent == expected.resolve(), module.__file__
assert module.bl_info['version'] == (0, 61, 63), module.bl_info
module._validate_registration_integrity()
addon_utils.disable('character_designer', default_set=False)
print('DEPLOYED_CHARACTER_DESIGNER_0_61_63_ENABLE_DISABLE_PASS', module.__file__)
