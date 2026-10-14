# Source preparation only: bind final pins before explicit execution dispatch.
import ast, hashlib
from pathlib import Path
pins={"D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_original_inputs.py":"f45309023033f762ab10735ac958e14391b2807510acd92410413577aac901d9","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_rigging.py":"77397546086392365428bcb3d87a48139aa2f36fb540e4479ec21d86109d4faf","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/__init__.py":"2fe699508d27317e9070e34fa489b29e5f7eedb1468d5fb5b8358b19d7683df4","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/forearm_twist.py":"54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_original_inputs_ui.py":"38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_worklist_ui.py":"24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067","D:/MyRepository/Blender-addons-by-Randy/tests/test_animation_rigging_recovery.py":"c1b3a3dfdc2fe003251c1241ca12043227b909630858c75d176f16eea3a12427","D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/certify_original_legacy_base_clock_latest_saved.py":"9f3647bc0e7d177e1e2dbecd0db7a49ffbf6a52b4f61c28d8b024c7c45a08155"}
if any(value.startswith('PENDING_') for value in pins.values()):
    raise RuntimeError('R16 final source pins are not bound.')
for name, expected in pins.items():
    raw=Path(name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected, name
    compile(ast.parse(raw,filename=name),name,'exec')
    print('AST_COMPILE_PASS '+Path(name).name+' '+expected)
print('SOURCE_ONLY files=8 target_imports=0 tests=0 native=0')
