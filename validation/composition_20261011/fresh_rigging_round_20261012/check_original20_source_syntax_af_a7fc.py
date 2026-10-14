import ast, hashlib, json
from pathlib import Path
pins = {"D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\unity_animation_original_inputs.py":"a7fc96e0ad2e12ee8ddf425198fa3edd89006facd3abc906905b50223d7e5adf","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_rigging.py":"3ef897863611f8be69be7234aa92b39e0f8239fff9d7843547f2677bfd616da1","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_original_inputs_ui.py":"505d36d9747c3e965d29494f85b0fbb42e8e290d41ca927d265b8a6288ea3f82","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_worklist_ui.py":"24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/__init__.py":"1302068a8dbc91bd8da147b707f3bdf9a30457b8476b3350062e14b87bbf6cea","D:/MyRepository/Blender-addons-by-Randy/tests/test_original_inputs_contract.py":"d98d78d7d01fb5bd233479bd1e583f61af95d8e6f0f0013484ce39f724602b50","D:\\Blender\\Projects\\Character\\X\\validation\\composition_20261011\\fresh_rigging_round_20261012\\certify_original_legacy_base_clock.py":"af4076b3a6923e7e8b891c237221e1761fd5056c410b2f905b52fbedda8a8b5c"}
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
