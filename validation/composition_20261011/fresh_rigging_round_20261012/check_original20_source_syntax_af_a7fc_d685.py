import ast, hashlib, json
from pathlib import Path
pins = {"D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\unity_animation_original_inputs.py":"a7fc96e0ad2e12ee8ddf425198fa3edd89006facd3abc906905b50223d7e5adf","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_rigging.py":"d6851b82169497a628439ae4b8be05954bfd101c952dcbbdff557c8e548c0038","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_original_inputs_ui.py":"505d36d9747c3e965d29494f85b0fbb42e8e290d41ca927d265b8a6288ea3f82","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_worklist_ui.py":"24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/__init__.py":"92b7aa29e90edee41c4171aea7e0eddc0f9f037636f258443c24c6b3f1a982e5","D:/MyRepository/Blender-addons-by-Randy/tests/test_original_inputs_contract.py":"d98d78d7d01fb5bd233479bd1e583f61af95d8e6f0f0013484ce39f724602b50","D:\\Blender\\Projects\\Character\\X\\validation\\composition_20261011\\fresh_rigging_round_20261012\\certify_original_legacy_base_clock.py":"af4076b3a6923e7e8b891c237221e1761fd5056c410b2f905b52fbedda8a8b5c"}
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
