"""Explicit, mandatory dependency pins for the immutable stop-settling QA.

This adapter asserts no new Cold completion or native readiness. It only binds
three globals in the frozen compiled namespace; the original main still checks
real Cold completion, disposal, actual source manifest and current Artist proof.
No native execution is performed by --pure-checks.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TAIL = HERE / 'verify_direct_cold_stop_settling_tail52.py'
TAIL_SHA = '19b9d38b720cb325fe90a403c730c03b4fb821587d3dc7ad53b16b1a0f723349'
DEPENDENCY_KEYS = ('PROVIDER_SHA', 'COLD_PROOF', 'COLD_PROOF_SHA')
OPTIONS = ('--expected-direct-sha', '--cold-report', '--cold-report-sha')


def need(value, message):
    if not value:
        raise RuntimeError('StopSettlingDependencies52: ' + message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_dependencies(expected_direct_sha, cold_report, cold_report_sha):
    need(isinstance(expected_direct_sha, str) and re.fullmatch(r'[0-9a-f]{64}', expected_direct_sha),
         'Full lowercase expected Direct SHA256 required')
    need(isinstance(cold_report_sha, str) and re.fullmatch(r'[0-9a-f]{64}', cold_report_sha),
         'Full lowercase real Cold report SHA256 required')
    path = Path(cold_report)
    need(path.is_absolute() and path.resolve().is_relative_to(HERE) and path.resolve() != HERE,
         'Explicit absolute Cold report path must remain inside this Validation directory')
    return expected_direct_sha, path.resolve(), cold_report_sha


def dependency_arguments(argv):
    separator = argv.index('--') + 1 if '--' in argv else 1
    tokens = argv[separator:]
    need(all(sum(token.split('=', 1)[0] == option for token in tokens) == 1 for option in OPTIONS),
         'Each dependency option is mandatory exactly once')
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument('--expected-direct-sha', required=True)
    parser.add_argument('--cold-report', type=Path, required=True)
    parser.add_argument('--cold-report-sha', required=True)
    args, remaining = parser.parse_known_args(tokens)
    dependencies = validate_dependencies(args.expected_direct_sha, args.cold_report, args.cold_report_sha)
    return dependencies, argv[:separator] + remaining


def load_tail():
    need(sha(TAIL) == TAIL_SHA, 'Frozen settling test differs')
    spec = importlib.util.spec_from_file_location('stop_settling_dependency_frozen_tail', TAIL)
    tail = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tail)
    return tail


def prepared_namespace(expected_direct_sha, cold_report, cold_report_sha):
    dependencies = validate_dependencies(expected_direct_sha, cold_report, cold_report_sha)
    tail = load_tail()
    result = tail.prepared_namespace()
    namespace = result[0]
    original = dict(namespace)
    namespace.update(zip(DEPENDENCY_KEYS, dependencies))
    need(all(namespace[key] is value for key, value in original.items() if key not in DEPENDENCY_KEYS)
         and tuple(namespace[key] for key in DEPENDENCY_KEYS) == dependencies,
         'Only three explicit compiled dependency globals may change')
    return result


def pure_checks():
    tail = load_tail()
    old = tail.prepared_namespace()
    expected = ('a' * 64, HERE / 'future_real_cold' / 'report.json', 'b' * 64)
    new = prepared_namespace(*expected)
    namespace = new[0]
    need(new[2:] == old[2:] and namespace['restore_body_coordinates'] is new[1].restore_body_coordinates,
         'Compiled recipe/source/restore identity differs')
    need({key for key in old[0] if key in DEPENDENCY_KEYS and namespace[key] != old[0][key]}
         == set(DEPENDENCY_KEYS), 'Dependency binding incomplete')
    need(namespace['main'].__globals__ is namespace and namespace['run_motion'].__globals__ is namespace,
         'Actual compiled globals do not receive dependencies')
    need(namespace['PINS'] == old[0]['PINS'] and namespace['__file__'] == str(TAIL)
         and namespace['sha'] is new[1].sha,
         'Frozen source pins/self/full-source reader identity differs')
    argv = ['blender.exe', '--factory-startup', '--', '--output', str(HERE / 'future_run'),
            '--expected-direct-sha', expected[0], '--cold-report', str(expected[1]), '--cold-report-sha', expected[2],
            '--soft-seconds', '240', '--render']
    deps, delegated = dependency_arguments(argv)
    need(deps == expected and delegated == argv[:3] + argv[3:5] + argv[-3:],
         'Only three dependency CLI options must be removed')
    failures = 0
    for values in (('a', expected[1], expected[2]), (expected[0], expected[1], 'b'),
                   (expected[0], Path('relative.json'), expected[2]),
                   (expected[0], HERE.parent / 'outside.json', expected[2])):
        try: validate_dependencies(*values)
        except RuntimeError: failures += 1
        else: need(False, 'Invalid explicit dependency admitted')
    for altered in (argv + ['--expected-direct-sha', expected[0]], argv[:5] + argv[7:]):
        try: dependency_arguments(altered)
        except RuntimeError: failures += 1
        else: need(False, 'Missing or duplicate dependency option admitted')
    main = ast.parse(new[3]).body[0]
    cold_guard = next(node.args[0] for node in ast.walk(main) if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id == 'need' and len(node.args) > 1
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == 'Actual completed current cold prerequisite differs')
    condition = compile(ast.Expression(cold_guard), '<unchanged-real-cold-guard>', 'eval')
    actual_prior = json.loads(old[0]['COLD_PROOF'].read_text(encoding='utf-8'))
    environment = {'prior': actual_prior, 'before': actual_prior['source_after'],
                   'args': SimpleNamespace(artist_protection_sha=actual_prior['artist_after']['sha256'])}
    need(eval(condition, {}, environment) is True, 'Actual historical completed Cold guard ABI differs')
    for key, value in (('native_component_completed', False), ('private_scene_disposed', False),
                       ('source_files_Artist_exact', False), ('errors', ['failure']), ('source_after', {})):
        changed = copy.deepcopy(actual_prior); changed[key] = value
        need(eval(condition, {}, dict(environment, prior=changed)) is False, 'Cold prerequisite guard weakened: ' + key)
    need(eval(condition, {}, dict(environment, args=SimpleNamespace(artist_protection_sha='c' * 64))) is False,
         'Current Artist proof mismatch admitted')
    print(json.dumps({'source_prepared': True, 'native_executed': False, 'Native_READY': False,
        'namespace_only_three_dependency_keys_changed': True, 'recipe_and_finally_source_exact': True,
        'mandatory_explicit_dependency_options': list(OPTIONS),
        'explicit_CLI_negative_controls': failures, 'original_Cold_guard_actual_positive': 1,
        'original_Cold_guard_negative_controls': 6, 'frozen_tail_sha256': TAIL_SHA,
        'scope': 'No future report created; native delegated main still requires actual completed fresh Cold/source/Artist proof'}))


def main():
    dependencies, delegated = dependency_arguments(sys.argv)
    expected_direct_sha, cold_report, cold_report_sha = dependencies
    need(cold_report.is_file() and sha(cold_report) == cold_report_sha, 'Specified real Cold report missing or differs')
    self_path = Path(__file__).resolve()
    before = {self_path: sha(self_path), TAIL: TAIL_SHA, cold_report: cold_report_sha}
    namespace, _base, _run, _main, _replacements = prepared_namespace(*dependencies)
    print(json.dumps({'stage': 'STOP_SETTLING_EXPLICIT_DEPENDENCY_PREPARATION',
        'adapter': {'path': str(self_path), 'sha256': before[self_path]},
        'frozen_tail': {'path': str(TAIL), 'sha256': TAIL_SHA},
        'manually_specified_dependencies': {'expected_direct_sha': expected_direct_sha,
            'cold_report': str(cold_report), 'cold_report_sha': cold_report_sha},
        'Native_READY_claimed': False, 'Cold_completion_claimed': False,
        'scope': 'Explicit pins only; delegated main must still prove native Cold completion/disposal and full current source/Artist equality'}))
    original_argv = sys.argv
    try:
        sys.argv = delegated
        return namespace['main']()
    finally:
        sys.argv = original_argv
        need(all(sha(path) == value for path, value in before.items()), 'Adapter/frozen tail/explicit Cold changed during execution')


if __name__ == '__main__':
    if '--pure-checks' in sys.argv:
        pure_checks()
    else:
        raise SystemExit(main())
