"""Prepared-only current Direct motion with bulk positions and sparse full QA.

Root alone runs one case in factory Blender 5.2. No Native call is made by
--pure-checks. The frozen public installation and Body12 finally are reused.
Air3/default physics remain unchanged; measured QA costs are not GUI FPS.
"""
import ast
from array import array
import builtins
import copy
import dis
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import sys
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE / 'verify_direct_cold_stop_body_keys52.py'
BASE_SHA = '7fb52720375b97d68508c0ff17b1b0b9c0fb6f696748689b0fe0f2291ca7527c'
DEPENDENCIES = HERE / 'verify_direct_cold_stop_settling_tail52_dependencies.py'
DEPENDENCIES_SHA = 'f04d6d65e514bc1839fb3abff1d2bc4eea41f75c34636e80e9c877463faaabcf'
DELTA_MAP = HERE / 'direct_export_admission_delta_20261007/source_delta_map.json'
DELTA_MAP_SHA = '52ed01d898fc04d58f8c51fc36e9910c6cd3e67129772e7ce5ce3c043ffe8a94'
PROVIDER_SHA = 'eb1ad005da9c98082b577c4dca4ab32a111ec684fa2ba27e3612b0c396205e99'
ARTIST_RECEIPT = HERE / 'artist_disk_protection_20261007_e0b30f73fc2f.json'
ARTIST_RECEIPT_SHA = '4d092929664f9718241afabc1ba3a3c667b600eeeb3d8a98fac0aea322ff536f'
CASES = ('walk', 'run', 'abrupt_stop_turn')
GUARD_FILES = frozenset(('unity_export.py', 'unity_export_worker.py',
    'animation_export.py', 'animation_export_worker.py',
    'animation_worklist_collection.py', 'dress_export_guard.py'))


def need(value, message):
    if not value:
        raise RuntimeError('DirectBulkMotion52: ' + message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen(path, expected, name):
    need(sha(path) == expected, 'Frozen dependency differs: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sparse_indices(recipe, case):
    need(case in CASES, 'Only one reviewed motion case allowed')
    rows = {i: recipe(case, i, 60) for i in range(1, 61)}
    indices = {1, 60}
    for side in ('left', 'right'):
        indices.add(max(rows, key=lambda i: rows[i][side]))
    if case == 'abrupt_stop_turn':
        end = max(row['forward_height'] for row in rows.values())
        turn = max(row['turn'] for row in rows.values())
        need(math.isfinite(end) and end > 0. and turn == math.pi * .5,
             'Frozen stop recipe changed')
        indices.add(min(i for i, row in rows.items() if row['forward_height'] == end
                        and row['left'] == row['right'] == 0.))
        indices.add(min(i for i, row in rows.items() if row['turn'] == turn and row['stopped'] is True))
    need(len(indices) == (6 if case == 'abrupt_stop_turn' else 4), 'Sparse native schedule changed')
    return sorted(indices)


def bulk_points(obj, graph):
    """Native Float32 local coordinates; same mathutils world transform as QA."""
    from mathutils import Vector
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh()
    try:
        values = array('f', [0.]) * (3 * len(mesh.vertices))
        need(values.itemsize == 4 and values, 'Native float32 positions unavailable')
        mesh.vertices.foreach_get('co', values)
        need(all(math.isfinite(v) for v in values), 'Nonfinite bulk local positions')
        world = evaluated.matrix_world.copy()
        points = [world @ Vector(values[i:i+3]) for i in range(0, len(values), 3)]
        need(all(math.isfinite(v) for p in points for v in p), 'Nonfinite bulk world positions')
        return {'object': obj.name, 'points': points, 'matrix_world': [list(row) for row in world]}
    finally:
        evaluated.to_mesh_clear()


def full_match(bulk, full, frame, full_frame, graph_pointer, full_pointer):
    names = ('input800', 'C800', 'final3040')
    errors = {}
    for name in names:
        a = tuple(tuple(float(v) for v in p) for p in bulk[name]['points'])
        b = tuple(tuple(float(v) for v in p) for p in full[name]['points'])
        need(a and b and all(len(p) == 3 and all(math.isfinite(v) for v in p) for p in a+b),
             'Missing/nonfinite paired positions')
        errors[name] = {'counts': [len(a), len(b)], 'positions_exact': a == b,
            'maximum_world_delta': None if len(a) != len(b) else
                max(math.sqrt(sum((x-y)**2 for x,y in zip(p,q))) for p,q in zip(a,b))}
    result = {'frame_exact': frame == full_frame, 'same_native_graph':
        type(graph_pointer) is int and graph_pointer > 0 and graph_pointer == full_pointer,
        'geometry': errors, 'accepted': False}
    result['complete'] = (result['frame_exact'] and result['same_native_graph']
                          and all(row['positions_exact'] for row in errors.values()))
    return result


def contact_complete(contact):
    """Measured sparse diagnostics may show penetration; Unknown never becomes 0."""
    try:
        crossing = contact['strict_Body_crossing']
        return (crossing['status'] == 'measured' and crossing['full_surface_filter']['complete'] is True
            and type(crossing['actual_crossing_pair_count']) is int and crossing['actual_crossing_pair_count'] >= 0
            and contact['Unknown_if_incomplete'] is False
            and set(contact['unresolved_counts']) == {'coplanar_unresolved', 'degenerate_unresolved', 'boundary_unresolved'}
            and all(type(v) is int and v == 0 for v in contact['unresolved_counts'].values())
            and len(contact['closed3']) == 3 and all(type(row['all3040']['sampled_vertices']) is int
                and row['all3040']['sampled_vertices'] == 3040
                and type(row['all3040']['inside_vertices']) is int and 0 <= row['all3040']['inside_vertices'] <= 3040
                and all(type(row['all3040'][key]) in (int,float) and math.isfinite(row['all3040'][key])
                    for key in ('minimum_signed_distance_m','maximum_penetration_m'))
                and row['all3040']['maximum_penetration_m'] >= 0 for row in contact['closed3']))
    except (KeyError, TypeError, AttributeError):
        return False


def parameters(context, q, profiles, source, installed, cloth, colliders, clone):
    return {'profile': profiles.read(source, installed), 'cloth_settings': q.simple_rna(cloth.settings),
        'collision_settings': q.simple_rna(cloth.collision_settings),
        'effectors': q.simple_rna(cloth.settings.effector_weights),
        'scene_gravity': list(context.scene.gravity), 'scene_use_gravity': context.scene.use_gravity,
        'colliders': {obj.name: q.simple_rna(obj.collision) for obj in colliders+[clone]},
        'default_parameters_accepted': False}


def _strip_guard_ast(filename, text, metadata):
    tree = ast.parse(text)
    if filename == 'animation_worklist_collection.py':
        fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'export_implementation')
        tuples = [node for node in ast.walk(fn) if isinstance(node, ast.Tuple)
                  and any(isinstance(e, ast.Constant) and e.value == 'dress_export_guard.py' for e in node.elts)]
        need(len(tuples) == 1, 'Unique worklist guard fingerprint missing')
        tuples[0].elts = [e for e in tuples[0].elts if not (isinstance(e, ast.Constant) and e.value == 'dress_export_guard.py')]
    else:
        delta = next(item for item in metadata['entrypoint_additions'] if item['file'] == filename)
        removals = {ast.dump(ast.parse(item['ast']).body[0]): 0
                    for item in delta['new_statements'] + delta['module_loaders']}
        class Strip(ast.NodeTransformer):
            def visit(self, node):
                key = ast.dump(node)
                if key in removals:
                    removals[key] += 1
                    return None
                return super().visit(node)
        tree = Strip().visit(tree)
        need(all(value == 1 for value in removals.values()), 'Unique guard-only source delta changed')
    return ast.dump(tree)


def source_admission(old, current, report):
    """Exact known export-only transition; actual full manifests stay untouched."""
    need(type(old) is dict and type(current) is dict and sha(DELTA_MAP) == DELTA_MAP_SHA,
         'Missing full source manifest or exact transition map')
    changed = sorted(key for key in set(old) | set(current) if old.get(key) != current.get(key))
    proof = {'actual_changed_paths': changed, 'map': str(DELTA_MAP), 'map_sha256': DELTA_MAP_SHA,
        'physical_modules_changed': None, 'passed': False, 'native_or_export_acceptance': False}
    report['cold_source_compatibility'] = proof
    if not changed:
        proof.update(passed=True, physical_modules_changed=False, scope='Exact complete current Cold/source identity')
        return True
    metadata = json.loads(DELTA_MAP.read_text(encoding='utf-8-sig'))
    root = Path(metadata['canonical_root'])
    expected_paths = {str(root/name) for name in GUARD_FILES}
    need(set(changed) == expected_paths, 'Unknown source change; no physics/Body/UI/profile transition permitted')
    receipts = []
    for key in changed:
        path = Path(key); name = path.name; spec = metadata['changed_files'][name]
        before, after = old.get(key), current.get(key)
        need(type(after) is dict and set(after) == {'bytes','mtime_ns','sha256'}
             and type(after['bytes']) is int and after['bytes'] > 0
             and type(after['mtime_ns']) is int and type(after['sha256']) is str
             and after['sha256'] == spec['after_sha256'] and after['bytes'] == spec['after_bytes']
             and sha(path) == spec['after_sha256'], 'Actual export-only successor fingerprint differs')
        if name == 'dress_export_guard.py':
            need(before is None and spec['new_file'] is True, 'New helper existed in Cold inventory unexpectedly')
            module = ast.parse(path.read_text(encoding='utf-8-sig'))
            need(all(isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef))
                     or isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) for node in module.body),
                 'New guard has a top-level runtime operation')
            calls = [node for node in module.body if isinstance(node, ast.Assign)
                     and isinstance(node.value, ast.Call)]
            need(len(calls) == 1 and ast.unparse(calls[0].value.func) == 'frozenset', 'New guard top-level assignment has a side effect')
        else:
            need(type(before) is dict and set(before) == {'bytes','mtime_ns','sha256'}
                 and before['sha256'] == spec['before_sha256'] and before['bytes'] == spec['before_bytes'],
                 'Cold export predecessor differs from the exact transition')
            backup = Path(spec['before_backup'])
            need(sha(backup) == spec['before_sha256']
                 and _strip_guard_ast(name, path.read_text(encoding='utf-8-sig'), metadata)
                     == ast.dump(ast.parse(backup.read_text(encoding='utf-8-sig'))),
                 'Transition changes more than export admission/fingerprint')
        receipts.append({'path': key, 'before': before, 'after': after,
                         'only_export_admission_or_fingerprint': True})
    proof.update(passed=True, physical_modules_changed=False, explicit_transition=receipts,
        scope='Same verified physical implementation; six exact export/fingerprint-only files changed. Actual current before/after remains full-exact.')
    return True


SAMPLE = '''
        previous_light = None
        def sample(label, index, *, held=False):
            nonlocal previous_light
            budget(); need(not held, 'This one-case bounded check does not repeat same-frame held teleport')
            tick = time.perf_counter(); graph = context.evaluated_depsgraph_get(); graph_seconds = time.perf_counter()-tick
            tick = time.perf_counter()
            meshes = {name: _BULK_POINTS(obj, graph) for name,obj in
                      (('input800',input_obj), ('C800',c), ('final3040',source))}
            extract_seconds = time.perf_counter()-tick
            need([len(meshes[name]['points']) for name in meshes] == [800,800,3040], 'Bulk actual native index counts changed')
            micro = live.precision_guard(meshes['input800']['points'], metres)
            pin = cold.error(meshes['input800']['points'],meshes['C800']['points'],metres,ring)
            evaluated = rig.evaluated_get(graph)
            row = {'label':label, 'index':index, 'frame':[home.frame_current,home.frame_subframe],
                'native_Root_world':[list(r) for r in evaluated.matrix_world @ evaluated.pose.bones[root.name].matrix],
                'native_left_knee_world':list(evaluated.matrix_world @ evaluated.pose.bones[legs['L']['chain'][1]].head),
                'counts':{name:len(mesh['points']) for name,mesh in meshes.items()},
                'pin_current_input_error':pin, 'microguard':micro, 'pin_micro_passed':pin['maximum_m'] <= micro['metres'],
                'final_change':None if previous_light is None else cold.error(previous_light['final3040']['points'],meshes['final3040']['points'],metres),
                'timing':{'graph_get_seconds':graph_seconds,'bulk_three_position_extraction_seconds':extract_seconds},
                'accepted':False,'GUI_FPS_or_solver_only_time':False}
            samples.append(row); report['samples'] = samples; write()
            need(body.data.users == 1 and input_obj.modifiers[1].is_bound and c.modifiers[1].is_bound,
                 'Current native Body/bind isolation changed')
            need(row['pin_micro_passed'], 'Time-advancing current hard80 pin error exceeded unchanged microguard')
            if index in indices:
                budget(); tick = time.perf_counter(); complete = full_sample(label,index)
                row['timing']['sparse_full_QA_total_seconds'] = time.perf_counter()-tick
                row['paired_bulk_full_geometry'] = _BULK_MATCH(meshes,previous,row['frame'],complete['frame'],graph.as_pointer(),complete['native_graph_pointer'])
                row['sparse_contact_complete'] = _BULK_CONTACT_COMPLETE(complete.get('contact'))
                write()
                need(row['paired_bulk_full_geometry']['complete'] and row['sparse_contact_complete'],
                     'Same-graph bulk/full geometry differs or sparse contact data Unknown/incomplete')
            previous_light = meshes
            return row
'''


def programs(base):
    run = inspect.getsource(base.run_motion)
    tree = ast.parse(run); original = tree.body[0]
    old_sample = next(node for node in ast.walk(original) if isinstance(node, ast.FunctionDef) and node.name == 'sample')
    lines = run.splitlines(keepends=True)
    old_text = ''.join(lines[old_sample.lineno-1:old_sample.end_lineno])
    full = old_text.replace('def sample(', 'def full_sample(', 1)
    full = full.replace('samples.append(row); report[\'samples\'] = samples; write()',
        "row['native_graph_pointer'] = graph.as_pointer()\n            full_samples.append(row); report['full_samples'] = full_samples; write()")
    full = full.replace('            diagnose = held or index in indices or not row[\'pin_micro_passed\']',
                        '            diagnose = True')
    full = full.replace('                physics.validate_physics(source)',
        "                tick = time.perf_counter(); physics.validate_physics(source)\n                row['timing']['full_validate_seconds'] = time.perf_counter()-tick\n                actual_parameters = _BULK_PARAMETERS(context,q,profiles,source,installed,cloth,colliders,clone)\n                row['native_parameters_preserved'] = _BULK_CANONICAL(actual_parameters) == _BULK_CANONICAL(report['native_defaults'])\n                row['Body12_stage_identity_exact'] = key_identity(body) == body_coordinates['identity']\n                row['Body_basis_stage_bytes_exact'] = coordinates(body.data.vertices).tobytes() == body_coordinates['base'].tobytes()\n                write(); need(row['native_parameters_preserved'] and row['Body12_stage_identity_exact'] and row['Body_basis_stage_bytes_exact'], 'Default parameters or original Body12 identity/base changed')")
    run = ''.join(lines[:old_sample.lineno-1]) + full + SAMPLE + ''.join(lines[old_sample.end_lineno:])
    run = run.replace('indices = critical_frames(live.input_recipe, args.case)', 'indices = _BULK_INDICES(live.input_recipe, args.case)', 1)
    run = run.replace('samples, previous, held_frame = [], None, None', 'samples, full_samples, previous, held_frame = [], [], None, None', 1)
    start = run.index('        # Two deliberately held endpoint inputs:')
    end = run.index("        report['native_motion_collection_completed'] = True", start)
    run = run[:start] + "        report['bulk_full_schedule_complete'] = (len(samples) == 60 and [r['index'] for r in full_samples] == indices and all(r.get('paired_bulk_full_geometry',{}).get('complete') is True for r in samples if r['index'] in indices))\n        write(); need(report['bulk_full_schedule_complete'], 'Native60/sparse geometry-proof schedule incomplete')\n" + run[end:]
    marker = "        report['native_defaults'] ="
    need(run.count(marker) == 1, 'Actual default parameter receipt ABI changed')
    run = run.replace(marker, "        need(profile['settings']['air_damping'] == cloth.settings.air_damping == 3.0 and profile['settings']['quality'] == cloth.settings.quality == 8 and profile['settings']['collision_quality'] == cloth.collision_settings.collision_quality == 4, 'Default Air3/quality8/collision4 only; no parameter substitution')\n" + marker, 1)
    main = inspect.getsource(base.main)
    main = main.replace("choices=('abrupt_stop_turn',)", "choices=('walk','run','abrupt_stop_turn')", 1)
    main = main.replace("default=180.", "default=150.", 1).replace('args.soft_seconds <= 240.', 'args.soft_seconds <= 150.', 1)
    main = main.replace("'allowed_upper_seconds':240.", "'allowed_upper_seconds':150.", 1).replace("'external_max_seconds':300.", "'external_max_seconds':None", 1)
    marker = "pins = {HERE/n:s for n,s in PINS.items()}; pins.update({PROVIDER:PROVIDER_SHA,COLD_PROOF:COLD_PROOF_SHA,FAILED_STOP:FAILED_STOP_SHA,Path(__file__):sha(__file__)})"
    need(main.count(marker) == 1, 'Frozen main source pin ABI changed')
    main = main.replace(marker, marker + "; pins.update({_BULK_BASE:_BULK_BASE_SHA,_BULK_DEPENDENCIES:_BULK_DEPENDENCIES_SHA,_BULK_MAP:_BULK_MAP_SHA})", 1)
    need(main.count("prior['source_after'] == before") == 1, 'Unique original Cold/source comparison missing')
    main = main.replace("prior['source_after'] == before", "_BULK_SOURCE_ADMISSION(prior['source_after'],before,report)", 1)
    main = main.replace('CURRENT_ARTIST_CANONICAL_DIRECT_COLD_STOP_BODY_KEY_RESTORE52', 'CURRENT_ARTIST_CANONICAL_DIRECT_COLD_BULK_MOTION52')
    main = main.replace("'scope':'One cold public Direct install, unkeyed native stop60; only private QA Body Key coordinates restored; not runtime corrective fix',",
        "'scope':'One frozen walk/run/stop60 input; default Air3; bulk Input/C/final positions and sparse full geometry/contact QA; no held tests, GUI FPS or ART acceptance',\n        'source_prepared_only':True,'runtime_preview_performance_improved':False,")
    return run, main


def prepared_namespace(expected_sha, cold_path, cold_sha):
    dependency = frozen(DEPENDENCIES, DEPENDENCIES_SHA, 'bulk_motion_dependencies')
    expected_sha, cold_path, cold_sha = dependency.validate_dependencies(expected_sha, cold_path, cold_sha)
    need(expected_sha == PROVIDER_SHA, 'Only frozen current EB Direct implementation supported')
    base = frozen(BASE, BASE_SHA, 'bulk_motion_frozen_stop')
    run, main = programs(base)
    namespace = dict(vars(base))
    namespace.update(__file__=str(Path(__file__).resolve()), PROVIDER_SHA=expected_sha, COLD_PROOF=cold_path, COLD_PROOF_SHA=cold_sha,
        _BULK_POINTS=bulk_points, _BULK_MATCH=full_match, _BULK_CONTACT_COMPLETE=contact_complete,
        _BULK_PARAMETERS=parameters, _BULK_CANONICAL=canonical, _BULK_INDICES=sparse_indices, _BULK_SOURCE_ADMISSION=source_admission,
        _BULK_BASE=BASE, _BULK_BASE_SHA=BASE_SHA, _BULK_DEPENDENCIES=DEPENDENCIES, _BULK_DEPENDENCIES_SHA=DEPENDENCIES_SHA,
        _BULK_MAP=DELTA_MAP, _BULK_MAP_SHA=DELTA_MAP_SHA)
    exec(compile(run+'\n'+main, str(Path(__file__).resolve()), 'exec'), namespace)
    return namespace, base, run, main


def missing_globals(code, namespace):
    missing = set()
    for instruction in dis.get_instructions(code):
        if instruction.opname == 'LOAD_GLOBAL' and instruction.argval not in namespace and not hasattr(builtins, instruction.argval):
            missing.add(instruction.argval)
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            missing |= missing_globals(value, namespace)
    return missing


def pure_checks(cold_path, cold_sha):
    namespace, base, run, main = prepared_namespace(PROVIDER_SHA,cold_path,cold_sha)
    before = ast.parse(inspect.getsource(base.run_motion)).body[0]
    after = ast.parse(run).body[0]
    first_try = next(node for node in before.body if isinstance(node, ast.Try))
    current_try = next(node for node in after.body if isinstance(node, ast.Try))
    need(ast.dump(ast.Module(first_try.finalbody,[])) == ast.dump(ast.Module(current_try.finalbody,[])), 'Strict original Body12/author finally changed')
    first_loop = next(node for node in ast.walk(first_try) if isinstance(node, ast.For) and ast.unparse(node.iter) == 'range(1, 61)')
    current_loop = next(node for node in ast.walk(current_try) if isinstance(node, ast.For) and ast.unparse(node.iter) == 'range(1, 61)')
    need(ast.dump(first_loop) == ast.dump(current_loop), 'Original60 input/frame recipe changed')
    need(namespace['restore_body_coordinates'] is base.restore_body_coordinates and not missing_globals(namespace['run_motion'].__code__,namespace)
         and not missing_globals(namespace['main'].__code__,namespace), 'Actual compiled globals/restorer incomplete')
    # Run the actual parser/pin prefix, stopping immediately before import bpy.
    main_tree=ast.parse(main).body[0]
    stop=next(i for i,node in enumerate(main_tree.body) if isinstance(node,ast.Import)
              and any(alias.name=='bpy' for alias in node.names))
    parser_tree=copy.deepcopy(main_tree)
    parser_tree.name='_bulk_native_prefix'
    parser_tree.body=parser_tree.body[:stop]+[ast.Return(ast.Tuple([ast.Name('args',ast.Load()),ast.Name('pins',ast.Load())],ast.Load()))]
    ast.fix_missing_locations(parser_tree)
    parser_namespace=dict(namespace)
    exec(compile(ast.Module([parser_tree],[]),str(Path(__file__)),'exec'),parser_namespace)
    argv=sys.argv
    fresh=HERE/'bulk_source_only_no_output_created'/ 'result'
    tokens=[str(Path(__file__)), '--', '--output',str(fresh), '--artist-protection',str(ARTIST_RECEIPT),
        '--artist-protection-sha',ARTIST_RECEIPT_SHA,'--body-object','Cosha','--dress-object','Dress',
        '--case','walk','--soft-seconds','150']
    try:
        sys.argv=tokens
        parsed,pins=parser_namespace['_bulk_native_prefix']()
        need(parsed.case=='walk' and parsed.soft_seconds==150. and not fresh.exists()
             and pins[BASE]==BASE_SHA and pins[DEPENDENCIES]==DEPENDENCIES_SHA
             and pins[Path(cold_path)]==cold_sha,'Actual compiled CLI/dependency pins did not bind')
        for seconds in ('151','0','nan'):
            sys.argv=tokens[:-1]+[seconds]
            try:parser_namespace['_bulk_native_prefix']()
            except RuntimeError:pass
            else:need(False,'Native parser admitted an unbounded soft budget')
    finally:sys.argv=argv
    # Execute the actual bulk reader against only foreach_get-enabled vertices.
    mathutils_before=sys.modules.get('mathutils')
    fixture=types.ModuleType('mathutils');fixture.Vector=lambda values:tuple(values)
    class World:
        def copy(self):return self
        def __matmul__(self,value):return tuple(x+y for x,y in zip(value,(2.,3.,4.)))
        def __iter__(self):return iter(((1.,0.,0.,2.),(0.,1.,0.,3.),(0.,0.,1.,4.),(0.,0.,0.,1.)))
    class Vertices:
        def __init__(self,values):self.values=values;self.calls=[]
        def __len__(self):return len(self.values)//3
        def foreach_get(self,attribute,target):
            need(attribute=='co' and target.typecode=='f','Bulk reader did not use actual Float32 co ABI')
            self.calls.append(attribute);target[:]=array('f',self.values)
    class NativeMesh:
        def __init__(self,values):self.vertices=Vertices(values)
        def __getattr__(self,name):raise RuntimeError('Bulk unexpectedly read '+name)
    class Evaluated:
        def __init__(self,values):self.mesh=NativeMesh(values);self.matrix_world=World();self.clears=0
        def to_mesh(self):return self.mesh
        def to_mesh_clear(self):self.clears+=1
    graph=object();evaluated=Evaluated([0.,0.,0.,1.,0.,0.])
    obj=types.SimpleNamespace(name='pure native ABI',evaluated_get=lambda g:evaluated if g is graph else None)
    try:
        sys.modules['mathutils']=fixture
        result=bulk_points(obj,graph)
        need(result['points']==[(2.,3.,4.),(3.,3.,4.)] and evaluated.mesh.vertices.calls==['co']
             and evaluated.clears==1,'Actual bulk foreach_get/world/cleanup ABI failed')
        evaluated.mesh.vertices.values[0]=math.nan
        try:bulk_points(obj,graph)
        except RuntimeError:pass
        else:need(False,'Bulk admitted nonfinite native positions')
        need(evaluated.clears==2,'Bulk failure lost native temporary mesh cleanup')
    finally:
        if mathutils_before is None:sys.modules.pop('mathutils',None)
        else:sys.modules['mathutils']=mathutils_before
    live = base.load('verify_live_direct_cloth52.py')
    schedules = {case:sparse_indices(live.input_recipe,case) for case in CASES}
    need(schedules == {'walk':[1,23,38,60],'run':[1,6,55,60],'abrupt_stop_turn':[1,5,13,34,44,60]}, 'Frozen exact critical phases differ')
    meshes = {name:{'points':[(0.,0.,0.),(1.,0.,0.)]} for name in ('input800','C800','final3040')}
    need(full_match(meshes,meshes,[1,0.],[1,0.],7,7)['complete'], 'Same-graph positions control failed')
    changed=copy.deepcopy(meshes); changed['C800']['points'][1]=(1.+1.e-8,0.,0.)
    need(not full_match(meshes,changed,[1,0.],[1,0.],7,7)['complete']
         and not full_match(meshes,meshes,[1,0.],[2,0.],7,7)['complete']
         and not full_match(meshes,meshes,[1,0.],[1,0.],7,8)['complete'], 'Geometry/time/graph mismatch falsely equal')
    contact={'strict_Body_crossing':{'status':'measured','full_surface_filter':{'complete':True},'actual_crossing_pair_count':3},
        'closed3':[{'all3040':{'sampled_vertices':3040,'inside_vertices':2,
            'minimum_signed_distance_m':-.001,'maximum_penetration_m':.001}} for _ in range(3)],'Unknown_if_incomplete':False,
        'unresolved_counts':{'coplanar_unresolved':0,'degenerate_unresolved':0,'boundary_unresolved':0}}
    need(contact_complete(contact), 'Measured penetration must stay data-complete without effect acceptance')
    for modify in (lambda v:v.update(Unknown_if_incomplete=True),lambda v:v['closed3'].pop(),
                   lambda v:v['strict_Body_crossing'].update(status='Unknown'),
                   lambda v:v['strict_Body_crossing'].update(actual_crossing_pair_count=True),
                   lambda v:v['unresolved_counts'].update(boundary_unresolved=1)):
        altered=copy.deepcopy(contact);modify(altered);need(not contact_complete(altered),'Unknown/incomplete contacts admitted')
    prior=json.loads(Path(cold_path).read_text(encoding='utf-8'))
    actual_walk=HERE/'actual_current_cold_walk_pose_52_20261007_034910_198/result/report.json'
    need(sha(actual_walk)=='51c3d7f4be0e29350fb511599e6a4fbc12657d9fb0fbdd91478b95f976fa04d4',
         'Actual historical contact ABI evidence changed')
    actual_contacts=[row['contact'] for row in json.loads(actual_walk.read_text(encoding='utf-8'))['samples'] if 'contact' in row]
    need(actual_contacts and all(contact_complete(row) for row in actual_contacts),
         'Frozen real native contact schema differs from the sparse completeness gate')
    fake_profiles=types.SimpleNamespace(read=lambda *_:{'mode':'AUTOMATIC'})
    fake_q=types.SimpleNamespace(simple_rna=lambda value:dict(value))
    fake_cloth=types.SimpleNamespace(settings=types.SimpleNamespace(effector_weights={'gravity':1.}),collision_settings={'quality':4})
    fake_q.simple_rna=lambda value:dict(value) if isinstance(value,dict) else {'air_damping':3.}
    actual_defaults=parameters(types.SimpleNamespace(scene=types.SimpleNamespace(gravity=(0.,0.,-9.81),use_gravity=True)),
        fake_q,fake_profiles,None,None,fake_cloth,[],types.SimpleNamespace(name='Body',collision={'quality':4}))
    need(actual_defaults['default_parameters_accepted'] is False and canonical(actual_defaults)==canonical(copy.deepcopy(actual_defaults)),
         'Actual parameter receipt loses the original default marker')
    changed_defaults=copy.deepcopy(actual_defaults);changed_defaults['cloth_settings']['air_damping']=5.
    need(canonical(actual_defaults)!=canonical(changed_defaults),'Air/profile drift falsely equal')
    source=base.load('verify_direct_cold_install52_v4.py')
    reader_spec=importlib.util.spec_from_file_location('bulk_pure_manifest_reader',source.COMPARATOR)
    reader=importlib.util.module_from_spec(reader_spec);reader_spec.loader.exec_module(reader)
    manifest=reader.load(reader.SOURCE,reader.SOURCE_SHA,'bulk_pure_manifest')
    current=manifest.current_manifest();proof={}
    need(source_admission(prior['source_after'],current,proof), 'Actual known export-only/source transition failed')
    bad=copy.deepcopy(current); key=str(namespace['PROVIDER']); bad[key]={**bad[key],'sha256':'0'*64}
    try:source_admission(prior['source_after'],bad,{})
    except RuntimeError:pass
    else:need(False,'Physical implementation drift admitted')
    need(sha(BASE)==BASE_SHA and sha(DEPENDENCIES)==DEPENDENCIES_SHA and sha(DELTA_MAP)==DELTA_MAP_SHA,
         'Frozen dependencies drifted during pure checks')
    print(json.dumps({'SOURCE_PREPARED':True,'native_executed':False,'sparse_full_indices':schedules,
        'original60_recipe_and_finally_AST_exact':True,'actual_compiled_globals_complete':True,
        'actual_native_prefix_and_bulk_foreach_get_ABI':True,'real_native_contact_ABI':True,
        'bulk_full_geometry_and_Unknown_negative_controls':True,'actual_source_transition':proof['cold_source_compatibility'],
        'default_air3_not_modified':True,'GUI_FPS_or_speedup_claimed':False}))


def main():
    dependency=frozen(DEPENDENCIES,DEPENDENCIES_SHA,'bulk_motion_cli_dependencies')
    dependencies,delegated=dependency.dependency_arguments(sys.argv)
    need(dependencies[0]==PROVIDER_SHA and dependencies[1].is_file() and sha(dependencies[1])==dependencies[2],
         'Real current Cold/provider dependencies missing or differ')
    if '--pure-checks' in sys.argv:
        pure_checks(dependencies[1],dependencies[2]);return 0
    namespace,base,run,_main=prepared_namespace(*dependencies)
    tokens=delegated[delegated.index('--')+1:] if '--' in delegated else delegated[1:]
    need(tokens.count('--artist-protection')==1 and tokens.count('--artist-protection-sha')==1
         and Path(tokens[tokens.index('--artist-protection')+1]).resolve()==ARTIST_RECEIPT.resolve()
         and tokens[tokens.index('--artist-protection-sha')+1]==ARTIST_RECEIPT_SHA,
         'Exact current e0b typed Artist proof required; no live/save/raw equivalence implied')
    original=sys.argv
    try:
        sys.argv=delegated
        return namespace['main']()
    finally:
        sys.argv=original
        need(sha(BASE)==BASE_SHA and sha(DEPENDENCIES)==DEPENDENCIES_SHA and sha(DELTA_MAP)==DELTA_MAP_SHA,
             'Frozen preparation files changed')


if __name__=='__main__':
    raise SystemExit(main())
