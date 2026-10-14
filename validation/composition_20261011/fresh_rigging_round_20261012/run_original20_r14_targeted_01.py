import ast, hashlib, json, os, sys, unittest
from pathlib import Path
from datetime import datetime, timezone
pins={"D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_original_inputs.py":"f45309023033f762ab10735ac958e14391b2807510acd92410413577aac901d9","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_rigging.py":"0e27de995a95b6dc32285dc90f908166d71af6d5ccaa97d9455c11c4720c8e81","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/__init__.py":"09d0cc30ca4f04a76b4cf8231dad75a290cf5d77c34211ed35fd7ce5ac4edfd9","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/forearm_twist.py":"54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_original_inputs_ui.py":"38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_worklist_ui.py":"24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067","D:/MyRepository/Blender-addons-by-Randy/tests/test_original_inputs_contract.py":"6f344cc095ce15e74514904fe0a79ab23e70ba250ca80fded87abc5c391b4bfd","D:/MyRepository/Blender-addons-by-Randy/tests/test_original_inputs_view_body.py":"7e8d1a49ae609041b273506c26dfdae30b1917327ddb1d9f47130fc474b4b405","D:/MyRepository/Blender-addons-by-Randy/tests/test_original_inputs_current.py":"8ea3df581d091144b3dfddaee9c1a190f7cba4721adc4066b639ac3b518c0931"}
syntax_pins={"D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_original_inputs.py":"f45309023033f762ab10735ac958e14391b2807510acd92410413577aac901d9","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_animation_rigging.py":"0e27de995a95b6dc32285dc90f908166d71af6d5ccaa97d9455c11c4720c8e81","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/__init__.py":"09d0cc30ca4f04a76b4cf8231dad75a290cf5d77c34211ed35fd7ce5ac4edfd9","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/forearm_twist.py":"54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_original_inputs_ui.py":"38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426","D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/animation_worklist_ui.py":"24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067","D:/MyRepository/Blender-addons-by-Randy/tests/test_original_inputs_contract.py":"6f344cc095ce15e74514904fe0a79ab23e70ba250ca80fded87abc5c391b4bfd","D:/MyRepository/Blender-addons-by-Randy/tests/test_original_inputs_view_body.py":"7e8d1a49ae609041b273506c26dfdae30b1917327ddb1d9f47130fc474b4b405","D:/MyRepository/Blender-addons-by-Randy/tests/test_original_inputs_current.py":"8ea3df581d091144b3dfddaee9c1a190f7cba4721adc4066b639ac3b518c0931","D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/certify_original_legacy_base_clock_latest_saved.py":"9f3647bc0e7d177e1e2dbecd0db7a49ffbf6a52b4f61c28d8b024c7c45a08155"}
modules=["test_original_inputs_contract","test_original_inputs_view_body","test_original_inputs_current"]
out=Path("D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012/pure_original20_r14_01")
now=lambda:datetime.now(timezone.utc).isoformat()
report={'schema':'x.validation.portable-contracts/1','started_utc':now(),'pid':os.getpid(),'completed':False,'passed':False,'native_execution_performed':False,'SDK':0,'GUI':False,'input_pins':pins}
for name, expected in {**pins, **syntax_pins}.items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected, name
syntax_lines=[]
for name, expected in syntax_pins.items():
    compile(ast.parse(Path(name).read_bytes(),filename=name),name,'exec')
    syntax_lines.append('AST_COMPILE_PASS '+Path(name).name+' '+expected)
syntax_lines.append('SOURCE_ONLY files=10 target_imports=0 tests=0 native=0')
(out/'syntax.txt').write_text('\n'.join(syntax_lines)+'\n',encoding='utf-8')
sys.path.insert(0,"D:/MyRepository/Blender-addons-by-Randy/tests")
suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
result=unittest.TextTestRunner(verbosity=2).run(suite)
post={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in pins}
report.update(completed=True,passed=result.wasSuccessful(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),input_files_unchanged=post==pins,ended_utc=now())
report['passed']=report['passed'] and report['input_files_unchanged'] and report['skipped']==0
(out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('PORTABLE_RESULT '+json.dumps({k:report[k] for k in ('passed','tests_run','failures','errors','skipped','input_files_unchanged')}))
sys.exit(0 if report['passed'] else 1)
