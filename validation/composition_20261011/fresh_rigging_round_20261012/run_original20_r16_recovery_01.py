# Fallback only: do not run if the implementation agent provides matching complete unit evidence.
import ast, hashlib, json, os, sys, unittest
from pathlib import Path
from datetime import datetime, timezone
pins={"D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_original_inputs.py":"f45309023033f762ab10735ac958e14391b2807510acd92410413577aac901d9","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_rigging.py":"PENDING_FINAL_NATIVE_PIN","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/__init__.py":"PENDING_FINAL_INIT_07734_PIN","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/forearm_twist.py":"54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_original_inputs_ui.py":"38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_worklist_ui.py":"24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067","D:/MyRepository/Blender-addons-by-Randy/tests/test_animation_rigging_recovery.py":"PENDING_FINAL_RECOVERY_TEST_PIN"}
syntax_pins={"D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_original_inputs.py":"f45309023033f762ab10735ac958e14391b2807510acd92410413577aac901d9","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_rigging.py":"PENDING_FINAL_NATIVE_PIN","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/__init__.py":"PENDING_FINAL_INIT_07734_PIN","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/forearm_twist.py":"54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_original_inputs_ui.py":"38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_worklist_ui.py":"24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067","D:/MyRepository/Blender-addons-by-Randy/tests/test_animation_rigging_recovery.py":"PENDING_FINAL_RECOVERY_TEST_PIN","D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/certify_original_legacy_base_clock_latest_saved.py":"9f3647bc0e7d177e1e2dbecd0db7a49ffbf6a52b4f61c28d8b024c7c45a08155"}
out=Path("D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/pure_original20_r16_01")
now=lambda:datetime.now(timezone.utc).isoformat()
report={'schema':'x.validation.portable-contracts/1','started_utc':now(),'pid':os.getpid(),'completed':False,'passed':False,'native_execution_performed':False,'SDK':0,'GUI':False,'input_pins':pins}
if any(value.startswith('PENDING_') for value in {**pins, **syntax_pins}.values()):
    raise RuntimeError('R16 source preparation: final pins and explicit execution dispatch are required.')
for name, expected in {**pins, **syntax_pins}.items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected, name
syntax_lines=[]
for name, expected in syntax_pins.items():
    compile(ast.parse(Path(name).read_bytes(),filename=name),name,'exec')
    syntax_lines.append('AST_COMPILE_PASS '+Path(name).name+' '+expected)
syntax_lines.append('SOURCE_ONLY files=8 target_imports=0 tests=0 native=0')
(out/'syntax.txt').write_text('\n'.join(syntax_lines)+'\n',encoding='utf-8')
sys.path.insert(0,"D:/MyRepository/Blender-addons-by-Randy/tests")
suite=unittest.defaultTestLoader.loadTestsFromNames(['test_animation_rigging_recovery'])
result=unittest.TextTestRunner(verbosity=2).run(suite)
post={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in pins}
report.update(completed=True,passed=result.wasSuccessful(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),input_files_unchanged=post==pins,ended_utc=now())
report['passed']=report['passed'] and report['input_files_unchanged'] and report['skipped']==0
(out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('PORTABLE_RESULT '+json.dumps({k:report[k] for k in ('passed','tests_run','failures','errors','skipped','input_files_unchanged')}))
sys.exit(0 if report['passed'] else 1)
