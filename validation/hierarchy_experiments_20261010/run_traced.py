from pathlib import Path
import traceback
import json

folder = Path('D:/Blender/Projects/Character/X/validation/hierarchy_experiments_20261010')
script = folder / 'organize_scene.py'
try:
    exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'), {'__name__': '__main__'})
except Exception:
    report = {'status': 'FAILED', 'traceback': traceback.format_exc()}
    (folder/'cleanup_failure.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))
