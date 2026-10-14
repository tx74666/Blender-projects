"""Run the existing twelve pure recovery cases once against an exact Native pin.

This producer does not load Blender or invoke any native application/worker.
Its separate receipt distinguishes new-source execution from historical b459.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
ROUND = Path(__file__).resolve().parent
NATIVE = REPO / 'addons/character_designer/unity_animation_rigging.py'
TEST = REPO / 'tests/test_animation_rigging_recovery.py'
TEST_SHA = '3b9a05733b1b4dd01591a60a03a7f44f7dce272851e61c15de361501812682d9'
PRIOR_NATIVE = ROUND / 'package_f9e41c12/source/character_designer/unity_animation_rigging.py'
PRIOR_SHA = 'b459668d166ef0b20b488414f3ae115aa53dd4bbeaec0645aea4ebba2e64d04d'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path, expected=None):
    path = path.resolve()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    require(expected is None or digest == expected, 'Source pin changed: ' + str(path))
    return {'path': str(path), 'sha256': digest, 'bytes': len(raw)}


def function_ast(path, name):
    nodes = [node for node in ast.parse(path.read_bytes()).body
             if isinstance(node, ast.FunctionDef) and node.name == name]
    require(len(nodes) == 1, 'Missing or ambiguous function: ' + name)
    return ast.dump(nodes[0], include_attributes=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-sha256', required=True)
    args = parser.parse_args()
    require(re.fullmatch('[0-9a-f]{64}', args.native_sha256), 'Use the exact final lowercase SHA.')
    output = ROUND / ('recovery_current_native_' + args.native_sha256[:8])
    require(not output.exists(), 'Preserve the previous actual execution; no repeated run to this directory.')
    sources = {'unity_animation_rigging.py': pin(NATIVE, args.native_sha256),
               'test_animation_rigging_recovery.py': pin(TEST, TEST_SHA)}
    prior = pin(PRIOR_NATIVE, PRIOR_SHA)
    require(args.native_sha256 != PRIOR_SHA, 'This receipt must describe new Native source.')
    for name in ('_apply', '_binding_plan'):
        require(function_ast(PRIOR_NATIVE, name) == function_ast(NATIVE, name),
                'The held preview algorithm changed: ' + name)
    output.mkdir()
    command = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests',
               '-p', 'test_animation_rigging_recovery.py', '-v']
    result = subprocess.run(command, cwd=REPO, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    log = output / 'actual_test_log.txt'
    with log.open('xb') as stream:
        stream.write(result.stdout)
    matches = re.findall(rb'^Ran (\d+) tests? in ', result.stdout, re.MULTILINE)
    total = int(matches[-1]) if len(matches) == 1 else None
    unchanged = sources == {'unity_animation_rigging.py': pin(NATIVE),
                            'test_animation_rigging_recovery.py': pin(TEST)}
    passed = result.returncode == 0 and total == 12 and unchanged
    receipt = {'schema': 'cdesigner.current-native-recovery-pure/1',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'passed': passed,
        'source_only': True, 'native_execution_performed': False,
        'source_files': sources, 'prior_immutable_native': prior, 'producer': pin(Path(__file__)),
        'apply_and_binding_plan_AST_unchanged': True, 'source_pins_unchanged_after_test': unchanged,
        'test_result': {'total': total, 'exit_code': result.returncode, 'actual_run': 1,
                        'log_pin': pin(log), 'command': command},
        'scope': 'Actual existing seven recovery plus five preview semantic cases against the new Native source; no new unique cases beyond the already recorded twelve.',
        'runtime_operations': {'blender': 0, 'native': 0, 'gui': 0, 'sdk': 0,
                               'worker': 0, 'deployment': 0, 'artist_mutation_or_save': 0},
        'limitations': ['AST functions and fake RNA only; no actual solver/Blender, save/reopen, Unity Apply or original Rig acceptance.']}
    path = output / 'receipt.json'
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'receipt': pin(path), 'log': pin(log), 'passed': passed,
                      'total': total, 'exit_code': result.returncode}))
    require(passed, 'The actual new-source recovery suite did not pass; preserve its receipt/log.')


if __name__ == '__main__':
    main()
