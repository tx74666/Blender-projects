import ast, hashlib, json
from pathlib import Path
pins = {"D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_original_inputs.py": "ba6078acafc2e735452dab776787f7b88720c7751837d55d620cddad56b7ef5e", "D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_rigging.py": "69bcc032fb890ecc005f75f9562df63625cb871386708dc0d29656354fd5c9f6", "D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_original_inputs_ui.py": "38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426", "D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_worklist_ui.py": "24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067", "D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/__init__.py": "857dc9cd03082876f6b19f18a944640e59caf919d0dfdbe8a92dde67499d29b0", "D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/forearm_twist.py": "54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408", "D:/MyRepository/Blender-addons-by-Randy/tests/test_original_inputs_contract.py": "6f344cc095ce15e74514904fe0a79ab23e70ba250ca80fded87abc5c391b4bfd", "D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/certify_original_legacy_base_clock_current.py": "36b03fa10bbaf21531d04a4a843e3487cf86c4dabcb284b45c06b237963c4ba8"}
for name, expected in pins.items():
    path = Path(name)
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected, name
    source = data.decode("utf-8")
    tree = ast.parse(source, filename=name)
    compile(tree, name, "exec")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    print("AST_COMPILE_PASS " + path.name + " " + expected)
print("SOURCE_ONLY files=8 target_imports=0 tests=0 native=0")
