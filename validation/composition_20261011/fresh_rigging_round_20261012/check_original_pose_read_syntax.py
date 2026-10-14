import ast
from pathlib import Path
for name in ["read_original_pose_metadata_02.py","call_original_pose_metadata_02.py"]:
 p=Path(__file__).parent/name
 compile(ast.parse(p.read_text(encoding="utf-8")),str(p),"exec")
 print("AST_COMPILE_PASS "+name)
