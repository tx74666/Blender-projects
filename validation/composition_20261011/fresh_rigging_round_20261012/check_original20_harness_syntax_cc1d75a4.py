import ast, hashlib
from pathlib import Path
p=Path("D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/validate_original20_controls.py")
b=p.read_bytes()
assert hashlib.sha256(b).hexdigest()=="cc1d75a4fdf0957661beab2080f897d9a04a95bca6f7327330d30ed266ad1d49"
t=ast.parse(b.decode("utf-8"),filename=str(p))
compile(t,str(p),"exec")
assert p.read_bytes()==b
print("AST_COMPILE_PASS harnessCC1D source_unchanged=True target_imports=0 tests=0 native=0")
