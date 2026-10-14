import ast, hashlib
from pathlib import Path
p=Path("D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/validate_original20_controls.py")
b=p.read_bytes()
assert hashlib.sha256(b).hexdigest()=="326f3122ef7527c03fd1c4fcbbb52255f912baeeb83e2852b6268ef05dd555e0"
t=ast.parse(b.decode("utf-8"),filename=str(p))
compile(t,str(p),"exec")
assert p.read_bytes()==b
print("AST_COMPILE_PASS harness326F source_unchanged=True target_imports=0 tests=0 native=0")
