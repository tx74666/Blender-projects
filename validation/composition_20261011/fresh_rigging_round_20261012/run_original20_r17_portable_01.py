"""Run only portable actual-function unit tests; no bpy import or native process."""
import ast
import os
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(r'D:/MyRepository/Blender-addons-by-Randy')
OUT = Path(__file__).parent / 'pure_original20_r17_01'
OUT.mkdir(exist_ok=False)
SOURCE = ROOT / 'addons/character_designer'
TESTS = [Path(row['path']) for row in [{"path":"D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_animation_rigging_recovery.py","sha256":"c1b3a3dfdc2fe003251c1241ca12043227b909630858c75d176f16eea3a12427","bytes":64811},{"path":"D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_animation_rigging_reference.py","sha256":"64d180533257c17638e5cca26d877712a33c5d21cf348964a73cabbbf50f94b7","bytes":31762},{"path":"D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_original_inputs_current.py","sha256":"8ea3df581d091144b3dfddaee9c1a190f7cba4721adc4066b639ac3b518c0931","bytes":7029},{"path":"D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_original_inputs_contract.py","sha256":"30b43a3fe8021819e5573e63ef9ab5454403c4248015b35b76e9ae3340c70370","bytes":32118}]]
EXPECTED = {"D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\unity_animation_original_inputs.py":"f2f6e1693c7fab0cb8ffaa479a3af19f5c4392f66119844183c32a61f91b1473","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\unity_animation_rigging.py":"77397546086392365428bcb3d87a48139aa2f36fb540e4479ec21d86109d4faf","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\__init__.py":"c9b05b3fc01a8686c0a48b0cb487e245adf76f21b53df6b5a2a53f56ca9319fa","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\forearm_twist.py":"54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\animation_original_inputs_ui.py":"38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\animation_worklist_ui.py":"24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067","D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_animation_rigging_recovery.py":"c1b3a3dfdc2fe003251c1241ca12043227b909630858c75d176f16eea3a12427","D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_animation_rigging_reference.py":"64d180533257c17638e5cca26d877712a33c5d21cf348964a73cabbbf50f94b7","D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_original_inputs_current.py":"8ea3df581d091144b3dfddaee9c1a190f7cba4721adc4066b639ac3b518c0931","D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_original_inputs_contract.py":"30b43a3fe8021819e5573e63ef9ab5454403c4248015b35b76e9ae3340c70370","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\animation_composition.py":"4a4081287e70050e93a65a138726fdd586d72ab32a90bbfa0e32d7b0cb1a4055","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\bone_collections.py":"c4f2814eb4981e032f5343ae01e4fc16f1536247ea7d1a4e9ee4d91292795452","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\animation_composition_weapon.py":"9551956548f20607331179034b44dc679888fc85da035fe1f6342e37de580d9c","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\animation_rigging_contract.py":"bff52cbe97530662fcee5e4ca248c1fe09e781f73588627cecda62c777d3c179"}
SYNTAX = {"D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\unity_animation_original_inputs.py":"f2f6e1693c7fab0cb8ffaa479a3af19f5c4392f66119844183c32a61f91b1473","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\unity_animation_rigging.py":"77397546086392365428bcb3d87a48139aa2f36fb540e4479ec21d86109d4faf","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\__init__.py":"c9b05b3fc01a8686c0a48b0cb487e245adf76f21b53df6b5a2a53f56ca9319fa","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\forearm_twist.py":"54c3bcccc1e7559a77f0d53773d46bf8137781ace139a50a93d9fb8eb2cdb408","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\animation_original_inputs_ui.py":"38a370bbcd37b3e7e39b02a0c9697cf460e4344ebbef622efd9144f12fd88426","D:\\MyRepository\\Blender-addons-by-Randy\\addons\\character_designer\\animation_worklist_ui.py":"24bae694878e88ef9dda1b9eaf5e69e702756beb4ee42eb1f561194e990a4067","D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_animation_rigging_recovery.py":"c1b3a3dfdc2fe003251c1241ca12043227b909630858c75d176f16eea3a12427","D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_animation_rigging_reference.py":"64d180533257c17638e5cca26d877712a33c5d21cf348964a73cabbbf50f94b7","D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_original_inputs_current.py":"8ea3df581d091144b3dfddaee9c1a190f7cba4721adc4066b639ac3b518c0931","D:\\MyRepository\\Blender-addons-by-Randy\\tests\\test_original_inputs_contract.py":"30b43a3fe8021819e5573e63ef9ab5454403c4248015b35b76e9ae3340c70370","D:\\Blender\\Projects\\Character\\X\\validation\\composition_20261011\\fresh_rigging_round_20261012\\certify_original_legacy_base_clock_latest_saved.py":"9f3647bc0e7d177e1e2dbecd0db7a49ffbf6a52b4f61c28d8b024c7c45a08155"}
INPUTS = [Path(name) for name in EXPECTED]

def pin(path):
    data = path.read_bytes()
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

started, clock = now(), time.perf_counter()
before = {str(path.relative_to(ROOT)): pin(path) for path in INPUTS}
for name, digest in {**EXPECTED, **SYNTAX}.items():
    if pin(Path(name))['sha256'] != digest: raise RuntimeError('Source pin drift: ' + name)
syntax_lines = []
for name, digest in SYNTAX.items():
    compile(ast.parse(Path(name).read_bytes(), filename=name), name, 'exec')
    syntax_lines.append('AST_COMPILE_PASS ' + Path(name).name + ' ' + digest)
syntax_lines.append('SOURCE_ONLY files=11 target_imports=0 tests=0 native=0')
(OUT / 'syntax.txt').write_text('\n'.join(syntax_lines) + '\n', encoding='utf-8')
executions = []
for index, path in enumerate(TESTS):
    suite_start, suite_clock = now(), time.perf_counter()
    spec = importlib.util.spec_from_file_location('portable_lifecycle_suite_' + str(index), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    raw = stream.getvalue()
    log = OUT / (path.stem + '.log')
    log.write_text(raw, encoding='utf-8')
    executions.append({'test_source': before[str(path.relative_to(ROOT))], 'started_utc': suite_start,
        'finished_utc': now(), 'elapsed_seconds': time.perf_counter() - suite_clock,
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped), 'passed': result.wasSuccessful(), 'raw_log': pin(log), 'raw_output': raw})
    print(raw, end='')
after = {str(path.relative_to(ROOT)): pin(path) for path in INPUTS}
passed = all(item['passed'] and item['skipped'] == 0 for item in executions) and before == after and sum(item['tests_run'] for item in executions) == 74
receipt = {'schema': 'x.validation.portable-contracts/1', 'completed': True, 'passed': passed,
    'scope': 'Actual recovery30/reference20/current10/public capture-publish14 portable checks; graph/Body proof/curve RNA fault seams remain explicit. No native Blender acceptance or speedup claimed.',
    'version_at_execution': '0.77.35', 'release_preparation_label': '0.77.35', 'pid': os.getpid(),
    'native_execution_performed': False, 'sdk_calls': 0, 'gui_used': False,
    'blender_launched': False, 'solver_or_frame_evaluation_performed': False,
    'started_utc': started, 'finished_utc': now(), 'elapsed_seconds': time.perf_counter() - clock,
    'command_argv': [sys.executable, '-B', str(Path(__file__).resolve())], 'workdir': str(Path.cwd()),
    'runner': pin(Path(__file__)), 'input_pins': before, 'input_files_unchanged': before == after,
    'input_pins_after': after, 'executions': executions, 'exit_code': 0 if passed else 1,
    **{key: sum(item[key] for item in executions) for key in ('tests_run', 'failures', 'errors', 'skipped')}}
destination = OUT / 'portable_contracts_receipt.json'
destination.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'receipt': pin(destination), 'passed': passed, 'tests_run': receipt['tests_run']}))
raise SystemExit(receipt['exit_code'])
