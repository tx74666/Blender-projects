"""Prepared-only stop60 plus a strictly frozen f60 input through f134.

Root alone may run factory BG5.2 after updating the stale cold/source pins in
a separately reviewed successor. This file keeps the original provider/cold
preflight: current source drift is rejected, never adopted implicitly.
No default/parameter changes, Dress keys, new Action, artist save or deployment.
"""
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import statistics
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE / 'verify_direct_cold_stop_body_keys52.py'
BASE_SHA = '7fb52720375b97d68508c0ff17b1b0b9c0fb6f696748689b0fe0f2291ca7527c'
STOP_REPORT = HERE / 'actual_current_cold_stop_body_keys_52_20261007_041042_233/result/report.json'
STOP_REPORT_SHA = '449c34230275fbded92dce57dd0f95c7d27ad6a0dd0c77a14afd2bc21c1b75e1'
END_INDEX = 134
TAIL_CONTACTS = (74, 104, 134)


def need(value, message):
    if not value:
        raise RuntimeError('StopSettlingTail52: ' + message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_base():
    need(sha(BASE) == BASE_SHA and sha(STOP_REPORT) == STOP_REPORT_SHA,
         'Immutable stop source/report differs')
    spec = importlib.util.spec_from_file_location('stop_tail_frozen_base', BASE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def point_content(mesh):
    points = tuple(tuple(float(v) for v in point) for point in mesh['points'])
    need(points and all(len(p) == 3 and all(math.isfinite(v) for v in p) for p in points),
         'Finite native points missing')
    return {'points': points, 'edges': copy.deepcopy(mesh['edges']),
            'faces': copy.deepcopy(mesh['faces'])}


def content_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def frozen_input_proof(pose, expected_pose, root_world, expected_root, meshes, expected_meshes):
    actual = {name: point_content(meshes[name]) for name in expected_meshes}
    result = {'raw_pose_exact': pose == expected_pose, 'native_Root_world_exact': root_world == expected_root,
              'INPUT800_exact': actual['input800'] == expected_meshes['input800'],
              'requested3040_exact': actual['requested3040'] == expected_meshes['requested3040'],
              'actual_INPUT800_sha256': content_sha(actual['input800']),
              'actual_requested3040_sha256': content_sha(actual['requested3040']),
              'accepted': False}
    result['complete'] = all(result[name] for name in
        ('raw_pose_exact', 'native_Root_world_exact', 'INPUT800_exact', 'requested3040_exact'))
    return result


def window10(rows):
    need(len(rows) == 10 and all(b['index'] == a['index'] + 1 for a, b in zip(rows, rows[1:])),
         'Ten consecutive native samples required')
    maximum = [r['final_change']['maximum_m'] for r in rows]
    rms = [r['final_change']['rms_m'] for r in rows]
    need(all(math.isfinite(v) and v >= 0 for v in maximum + rms), 'Finite final step metrics required')
    return {'first_index': rows[0]['index'], 'last_index': rows[-1]['index'], 'count': 10,
            'maximum_step_m': max(maximum), 'median_maximum_step_m': statistics.median(maximum),
            'maximum_RMS_step_m': max(rms), 'median_RMS_step_m': statistics.median(rms),
            'scope': 'Adjacent native final3040 steps; no naturalness/long-term settling acceptance',
            'accepted': False}


APPEND = '''
        # Preserve the whole original stop60 loop above. Freeze actual getters,
        # not a new time-normalized recipe or a desired pose approximation.
        frozen_pose = copy.deepcopy(q.pose_channels(rig))
        frozen_root = copy.deepcopy(samples[-1]['native_Root_world'])
        frozen_meshes = {name: _TAIL_POINT_CONTENT(previous[name])
                         for name in ('input800', 'requested3040')}
        tail = report['settling_tail'] = {
            'first_index': 61, 'last_index': 134, 'f60_native_frame': [home.frame_current, home.frame_subframe],
            'turn_completed_index': report['stop_phase_indices']['turn_completed'],
            'seconds_after_turn_at_end': (134-report['stop_phase_indices']['turn_completed'])/30.,
            'original_recipe_frames': 60, 'recipe_reparameterized': False,
            'raw_pose_sha256': _TAIL_CONTENT_SHA(frozen_pose),
            'f60_INPUT800_sha256': _TAIL_CONTENT_SHA(frozen_meshes['input800']),
            'f60_requested3040_sha256': _TAIL_CONTENT_SHA(frozen_meshes['requested3040']),
            'pose_and_targets_complete': False, 'native_completed': False, 'windows_10': [],
            'contact_indices': [74,104,134], 'accepted': False,
            'scope': 'Only fixed actual f60 input, sequential native Cloth; no same-frame fresh solve or ART claim'}
        write()
        for index in range(61,135):
            budget()
            need(q.pose_channels(rig) == frozen_pose, 'Frozen f60 raw pose changed before append frame')
            tick = time.perf_counter(); home.frame_set(start+index-1); frame_seconds = time.perf_counter()-tick
            row = sample('settling_'+str(index),index)
            row['timing']['frame_set_seconds'] = frame_seconds
            row['f60_input_hold_proof'] = _TAIL_HOLD_PROOF(q.pose_channels(rig),frozen_pose,
                row['native_Root_world'],frozen_root,previous,frozen_meshes)
            write()
            need(row['f60_input_hold_proof']['complete'], 'Append raw Root/pose/native input target differs from f60')
            if (index-60)%10 == 0 or index == 134:
                tail['windows_10'].append(_TAIL_WINDOW10(samples[-10:])); write()
        tail['pose_and_targets_complete'] = all(r['f60_input_hold_proof']['complete'] for r in samples[60:])
        tail['native_completed'] = len(samples[60:]) == 74 and tail['pose_and_targets_complete']
        need(tail['native_completed'], 'Append74 native samples/proofs incomplete')
        write()
'''


def programs(base):
    original_run = inspect.getsource(base.run_motion)
    run = original_run
    replacements = (
        ("need(cloth.point_cache.frame_step == 1 and start+59 <= cloth.point_cache.frame_end, 'Owned60-frame cache interval unavailable')",
         "need(cloth.point_cache.frame_step == 1 and start+133 <= cloth.point_cache.frame_end, 'Owned134-frame cache interval unavailable; no range mutation allowed')"),
        ('indices = critical_frames(live.input_recipe, args.case)',
         'indices = critical_frames(live.input_recipe, args.case) + [74,104,134]'),
        ("if args.render and (index == indices[1] or index == report['stop_phase_indices']['turn_completed'] or label in {'daily_end','held_manual'}):",
         "if args.render and label == 'settling_134':"),
        ("report['actual_world_motion'] = movement.measured_series(plan,[{'frame':r['index'],'Root':r['native_Root_world']} for r in samples],metres)",
         "report['actual_world_motion'] = movement.measured_series(plan,[{'frame':r['index'],'Root':r['native_Root_world']} for r in samples[:60]],metres)"),
    )
    for old, new in replacements:
        need(run.count(old) == 1, 'Unique original run ABI differs: ' + old)
        run = run.replace(old, new)
    marker = "        report['actual_world_motion'] = movement.measured_series"
    need(run.count(marker) == 1, 'Unique post-stop append point missing')
    run = run.replace(marker, APPEND + marker, 1)
    main = inspect.getsource(base.main)
    old = "pins = {HERE/n:s for n,s in PINS.items()}; pins.update({PROVIDER:PROVIDER_SHA,COLD_PROOF:COLD_PROOF_SHA,FAILED_STOP:FAILED_STOP_SHA,Path(__file__):sha(__file__)})"
    new = old + "; pins.update({_TAIL_BASE:_TAIL_BASE_SHA,_TAIL_STOP_REPORT:_TAIL_STOP_REPORT_SHA})"
    need(main.count(old) == 1, 'Original main pin ABI differs')
    main = main.replace(old, new)
    main = main.replace('CURRENT_ARTIST_CANONICAL_DIRECT_COLD_STOP_BODY_KEY_RESTORE52',
                        'CURRENT_ARTIST_CANONICAL_DIRECT_COLD_STOP_SETTLING_TAIL52')
    main = main.replace("'scope':'One cold public Direct install, unkeyed native stop60; only private QA Body Key coordinates restored; not runtime corrective fix',",
        "'scope':'Original stop60 unchanged, append fixed actual f60 pose/input61..134; Body12Key restore retained; not naturalness acceptance',\n        'preparation_state':'Original frozen source/provider/cold dependencies retained; current canonical drift must reject until Root reviews a new frozen successor',")
    return run, main, replacements


def prepared_namespace():
    base = load_base()
    run, main, replacements = programs(base)
    namespace = dict(vars(base))
    namespace.update(__file__=str(Path(__file__).resolve()), copy=copy,
        _TAIL_POINT_CONTENT=point_content, _TAIL_CONTENT_SHA=content_sha,
        _TAIL_HOLD_PROOF=frozen_input_proof, _TAIL_WINDOW10=window10,
        _TAIL_BASE=BASE, _TAIL_BASE_SHA=BASE_SHA,
        _TAIL_STOP_REPORT=STOP_REPORT, _TAIL_STOP_REPORT_SHA=STOP_REPORT_SHA)
    exec(compile(run + '\n' + main, str(Path(__file__).resolve()), 'exec'), namespace)
    return namespace, base, run, main, replacements


def pure_checks():
    namespace, base, run, main, replacements = prepared_namespace()
    original = ast.parse(inspect.getsource(base.run_motion)).body[0]
    current = ast.parse(run).body[0]
    original_recipe = next(n for n in ast.walk(original) if isinstance(n, ast.For)
        and isinstance(n.iter, ast.Call) and ast.unparse(n.iter) == 'range(1, 61)')
    current_recipe = next(n for n in ast.walk(current) if isinstance(n, ast.For)
        and isinstance(n.iter, ast.Call) and ast.unparse(n.iter) == 'range(1, 61)')
    need(ast.dump(original_recipe) == ast.dump(current_recipe), 'Original60 recipe AST changed')
    original_finally = next(n for n in original.body if isinstance(n, ast.Try)).finalbody
    current_finally = next(n for n in current.body if isinstance(n, ast.Try)).finalbody
    need(ast.dump(ast.Module(body=original_finally,type_ignores=[])) == ast.dump(ast.Module(body=current_finally,type_ignores=[])),
         'Author/12Keys/finally AST changed')
    reversed_run = run.replace(APPEND, '', 1)
    for old, new in reversed(replacements): reversed_run = reversed_run.replace(new, old, 1)
    need(reversed_run == inspect.getsource(base.run_motion), 'Unexpected run diff outside four replacements+append')
    need(namespace['run_motion'].__globals__ is namespace and namespace['main'].__globals__ is namespace
         and namespace['restore_body_coordinates'] is base.restore_body_coordinates
         and namespace['PROVIDER_SHA'] == base.PROVIDER_SHA and namespace['COLD_PROOF_SHA'] == base.COLD_PROOF_SHA,
         'Real compiled globals/restore/preflight identity changed')
    mesh = {'points':[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)], 'edges':[[0,1],[1,2],[2,0]],'faces':[[0,1,2]]}
    meshes = {'input800':mesh,'requested3040':mesh}; frozen = {n:point_content(m) for n,m in meshes.items()}
    pose = {'Root':{'mode':'XYZ','location':[0.,0.,0.]}}; root = [[1.,0.,0.,0.]]
    need(frozen_input_proof(pose,pose,root,root,meshes,frozen)['complete'], 'Exact held native content rejected')
    changed = copy.deepcopy(meshes); changed['input800']['points'][1] = (1.0000001,0.,0.)
    need(not frozen_input_proof(pose,pose,root,root,changed,frozen)['complete'], 'Nonzero native input drift admitted')
    changed_pose = copy.deepcopy(pose); changed_pose['Root']['location'][0] = 1.e-7
    need(not frozen_input_proof(changed_pose,pose,root,root,meshes,frozen)['complete'], 'Raw pose drift admitted')
    changed = copy.deepcopy(meshes); changed['requested3040']['faces'] = [[0,2,1]]
    need(not frozen_input_proof(pose,pose,root,root,changed,frozen)['complete'], 'Target topology drift admitted')
    rows = [{'index':i,'final_change':{'maximum_m':i*.001,'rms_m':i*.0001}} for i in range(61,71)]
    need(window10(rows)['count'] == 10 and window10(rows)['maximum_step_m'] == .07, 'Ten-step statistics wrong')
    prior = json.loads(STOP_REPORT.read_text(encoding='utf-8'))
    need(prior['native_motion_collection_completed'] and prior['accepted'] is False
         and prior['stop_phase_indices'] == {'translation_stopped':34,'turn_completed':44}, 'Actual stop evidence changed')
    observed_provider = sha(base.PROVIDER)
    print(json.dumps({'source_prepared':True,'pure_checks':9,'original60_recipe_AST_exact':True,
        'original_finally_12Keys_AST_exact':True,'native_executed':False,
        'original_provider_sha':base.PROVIDER_SHA,'actual_provider_sha':observed_provider,
        'original_provider_pin_matches_current':observed_provider == base.PROVIDER_SHA,
        'current_full_cold_manifest_proven':False,'Native_READY':False,
        'scope':'Prepared successor only; Root must review fresh source/provider/cold pins before any native execution'}))


if __name__ == '__main__':
    if '--pure-checks' in sys.argv:
        pure_checks()
    else:
        namespace, _base, _run, _main, _replacements = prepared_namespace()
        raise SystemExit(namespace['main']())
