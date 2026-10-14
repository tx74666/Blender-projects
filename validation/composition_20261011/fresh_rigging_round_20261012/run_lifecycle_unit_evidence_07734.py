"""Run only portable actual-function unit tests; no bpy import or native process."""
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
OUT = Path(__file__).parent / 'lifecycle_unit_07734_03'
OUT.mkdir(exist_ok=True)
SOURCE = ROOT / 'addons/character_designer'
TESTS = [ROOT / 'tests/test_animation_rigging_recovery.py', ROOT / 'tests/test_animation_rigging_reference.py']
INPUTS = TESTS + [SOURCE / leaf for leaf in ('unity_animation_rigging.py', 'animation_composition.py',
    'bone_collections.py', 'animation_composition_weapon.py', 'forearm_twist.py')]

def pin(path):
    data = path.read_bytes()
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

started, clock = now(), time.perf_counter()
before = {str(path.relative_to(ROOT)): pin(path) for path in INPUTS}
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
passed = all(item['passed'] for item in executions) and before == after
receipt = {'schema': 'x.validation.portable-contracts/1', 'completed': True, 'passed': passed,
    'scope': 'Actual AST lifecycle/recovery and reference ownership unit tests with fake native IDs; no native Blender acceptance claimed.',
    'version_at_execution': '0.77.33', 'release_preparation_label': '0.77.34',
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
