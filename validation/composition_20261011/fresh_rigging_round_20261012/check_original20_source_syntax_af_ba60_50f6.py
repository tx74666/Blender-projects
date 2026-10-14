import ast, hashlib, json
from pathlib import Path
pins = {"D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\unity_animation_original_inputs.py":"ba6078acafc2e735452dab776787f7b88720c7751837d55d620cddad56b7ef5e","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_rigging.py":"50f6c16ac35424ae131990be363a37500419ccc7716781b2622bdbe2032d67f3","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_original_inputs_ui.py":"505d36d9747c3e965d29494f85b0fbb42e8e290d41ca927d265b8a6288ea3f82","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_worklist_ui.py":"24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/__init__.py":"cf2bced9d75881050318ce3640ba15160d45d4c42f6de55c6e265a1f1114a365","D:/MyRepository/Blender-addons-by-Randy/tests/test_original_inputs_contract.py":"6f344cc095ce15e74514904fe0a79ab23e70ba250ca80fded87abc5c391b4bfd","D:\\Blender\\Projects\\Character\\X\\validation\\composition_20261011\\fresh_rigging_round_20261012\\certify_original_legacy_base_clock.py":"af4076b3a6923e7e8b891c237221e1761fd5056c410b2f905b52fbedda8a8b5c"}
for name, expected in pins.items():
    path = Path(name)
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected, name
    source = data.decode("utf-8")
    tree = ast.parse(source, filename=name)
    compile(tree, name, "exec")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    print("AST_COMPILE_PASS " + path.name + " " + expected)
print("SOURCE_ONLY files=7 target_imports=0 tests=0 native=0")
