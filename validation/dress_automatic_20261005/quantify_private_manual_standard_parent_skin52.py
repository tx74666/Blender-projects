"""Source-prepared private FULL-parent/LBS diagnostic; Root alone may run it.

Reuse the pinned V4 input, native depth projection, readers and entire finally.
Only an independent cleaned217 Rig receives the private inheritance helper.
Measure its REST-baked3040 LBS surface and strict184 non-Dress source motion.
No FBX writer, public admission, Unity proof, approximate acceptance or save.
The frozen parent and all its historical reports remain unchanged.
"""
import ast
import hashlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
PARENT = HERE/'quantify_private_manual_trs_skin52_v4.py'
PARENT_SHA = '1720c87d718114c169268317d8c40298d647adfbf09eb56fd868c5577e1880c2'
STANDARD = Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/dress_standard_parent_candidate.py')
STANDARD_SHA = '100c487aace09d9846b19bc60a3fe96497bfeaf3dfa83d1a22f6907683d12780'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def need(value, message):
    if not value:
        raise RuntimeError('StandardParentSkin52 source seam: ' + message)


def statements(code):
    return ast.parse(code).body


def statement_key(node):
    return ast.unparse(node)


def index_once(body, prefix):
    matches = [index for index, node in enumerate(body) if statement_key(node).startswith(prefix)]
    need(len(matches) == 1, 'Expected one exact parent statement: ' + prefix)
    return matches[0]


def prepare_tree(source):
    """Fixed AST seams; no monkeypatch to canonical writer or native endpoints."""
    tree = ast.parse(source, filename=str(PARENT))
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    tries = [node for node in main.body if isinstance(node, ast.Try) and node.finalbody]
    need(len(tries) == 1, 'Pinned parent main/finally shape differs')
    job = tries[0]
    finally_before = ast.dump(ast.Module(body=job.finalbody, type_ignores=[]), include_attributes=False)

    # Extend the detached private expectation map before the parent's all-pin check.
    offset = index_once(job.body, 'pins.update(current_paths)') + 1
    job.body[offset:offset] = statements("""
v2.RUNTIME_PINS['dress_standard_parent_candidate'] = STANDARD_SHA
pins.update({PARENT: PARENT_SHA, STANDARD: STANDARD_SHA})
report['standard_parent_component'] = dict(parent_script=str(PARENT), parent_sha=PARENT_SHA,
    helper_source=str(STANDARD), helper_sha=STANDARD_SHA, source_prepared_only=True,
    original_inheritance_projection_is_not_standard_parent_proof=True,
    native_three_frame_observation_complete=False,
    FBX_roundtrip_verified=False, public_admission_verified=False, Unity_verified=False)
""")
    offset = index_once(job.body, "report['pins'] =") + 1
    job.body[offset:offset] = statements("standard = load(STANDARD, 'private_standard_parent_candidate_helpers')")

    # Keep the parent's independent clone, cleanup and source-convention checks.
    # Only then make the explicitly different standard-parent target.
    offset = index_once(job.body, 'for name in retained:') + 1
    job.body[offset:offset] = statements("""
report['standard_parent_flags'] = standard.standardize_export_copy(bpy, rig, copied, inventory, retained)
need(report['standard_parent_flags']['bone_count'] == 217
     and set(report['standard_parent_flags']['original_flags']) == set(retained)
     and set(report['standard_parent_flags']['standard_flags']) == set(retained),
     'Complete standard217 flag receipt differs')
dress_names = {'SK_Dress_Waist'} | {'SK_Dress_DEF_%02d_%02d' % (strand, segment)
                                 for strand in range(1, 9) for segment in range(1, 5)}
non_dress = sorted(set(retained) - dress_names)
need(dress_names <= set(retained) and len(dress_names) == 33 and len(non_dress) == 184,
     'Fixed33 Dress and184 non-Dress retained scope differs')
report['non_Dress184_names'] = non_dress
report['non_Dress184_matrix_tolerance'] = 2e-4
report['non_Dress184_strict_passed'] = False
""")

    # A remains only a REST reference/cleanup input; remove the unrelated C audit.
    begin = index_once(job.body, 'mesh_c = mesh_a.copy()')
    end = index_once(job.body, "mesh_b = mesh_copy(")
    need(begin < end, 'Pinned C-to-B source interval differs')
    job.body[begin:end] = []
    offset = index_once(job.body, "report['skin_modes'] =")
    job.body[offset:offset+1] = statements("""
report['skin_modes'] = dict(source_PreserveVolume=original_volume, target_PreserveVolume=False,
    target='standard FULL parent native LBS on canonical REST-baked3040; Unity/FBX unverified')
""")

    # Retain each actual source sample and the parent's real depth/native solver.
    loop_index = index_once(job.body, 'for index, frame in enumerate((1.0, 2.0, 3.0)):')
    loop = job.body[loop_index]
    need(isinstance(loop, ast.For), 'Pinned three-frame source loop differs')
    cut = index_once(loop.body, 'local_inverse =')
    loop.body[cut:] = statements("""
world_actual = copied.evaluated_get(graph).matrix_world.copy()
body_errors = {name: matrices['per_bone_matrix_maxcomponent'][name] for name in non_dress}
body_worst = max(body_errors, key=body_errors.__getitem__)
row['non_Dress184_source_vs_standard_target'] = dict(count=184,
    matrix_maxcomponent=body_errors[body_worst], worst_bone=body_worst,
    per_bone_matrix_maxcomponent=body_errors,
    world_matrices=rest.matrix_errors([source_world @ desired[name] for name in non_dress],
        [world_actual @ actual[name] for name in non_dress], metres),
    strict_tolerance=2e-4, strict_passed=body_errors[body_worst] <= 2e-4)
row['source_217_pose_matrices'] = {name: [list(values) for values in desired[name]] for name in sorted(retained)}
row['standard_target_217_pose_matrices'] = {name: [list(values) for values in actual[name]] for name in sorted(retained)}
row['source_rig_world_matrix'] = [list(values) for values in source_world]
row['standard_target_rig_world_matrix'] = [list(values) for values in world_actual]
local_inverse = source_mesh_world.inverted()
row['source_local_points'] = [list(local_inverse @ point) for point in reference['points']]
observed = base.native_mesh(mesh_b, graph)
observed_skin = rest.ordered_skin(mesh_b, graph, skin)
world_error = diag.matrix_error(mesh_b.evaluated_get(graph).matrix_world, source_mesh_world)
need(len(observed['points']) == 3040 and world_error <= worker.MATRIX_TOLERANCE
     and rest.skin_exact(reference_skin, observed_skin)
     and reference_skin['materials'] == observed_skin['materials'],
     'Standard target lost same-index3040/mesh frame/UV/material/full named weights')
metric = base.geometry_pair(cold, reference, observed, metres)
worst = metric['worst_index']
metric.update(maximum_mm=metric['maximum_m']*1000., rms_mm=metric['rms_m']*1000.,
    same_index_3040=True, ordered_topology_exact=True, all_named_skin_fields_exact=True,
    materials_exact=True, mesh_world_maxcomponent=world_error,
    diagnostic_within_original_0_05mm=metric['maximum_m'] <= rest.LIMIT_M,
    worst_source_local=list(local_inverse @ reference['points'][worst]),
    worst_candidate_local=list(local_inverse @ observed['points'][worst]),
    candidate_source_local_points=[list(local_inverse @ point) for point in observed['points']],
    comparison='Original Manual source vs standard FULL parent depth-projected REST-baked LBS target; '
               'includes inheritance/TRS/modifier-order/DQ-mode differences, no export acceptance')
row['standard_FULL_REST_baked_LBS_surface'] = metric
need(q.rest_content(copied) == cleaned_rest and q.rest_content(rig) == source_rest
     and mesh_a.modifiers[0].use_deform_preserve_volume == original_volume
     and mesh_b.modifiers[0].use_deform_preserve_volume is False
     and all(tuple(getattr(bone, field) for field in standard.FLAGS) == standard.STANDARD
             for bone in copied.data.bones),
     'Projection changed source/standard Rest fields or target LBS/inheritance convention')
report['samples'].append(row)
write()
need(row['non_Dress184_source_vs_standard_target']['strict_passed'],
     'Standard target changed non-Dress184 motion beyond the original2e-4 FK guard: ' + body_worst)
""")
    offset = index_once(job.body, "report['C_single_factor']['native_three_frame_observation_complete'] =")
    job.body[offset:offset+1] = statements("""
report['standard_parent_component']['native_three_frame_observation_complete'] = len(report['samples']) == 3
report['standard_parent_component']['source_prepared_only'] = False
report['non_Dress184_strict_passed'] = (len(report['samples']) == 3
    and all(row['non_Dress184_source_vs_standard_target']['strict_passed'] for row in report['samples']))
""")
    # No changes at all to the native restoration, owned-ID cleanup and file pins.
    need(ast.dump(ast.Module(body=job.finalbody, type_ignores=[]), include_attributes=False) == finally_before,
         'Parent finally was changed')
    final_assignment = [node for node in job.finalbody if isinstance(node, ast.Assign)
                        and ast.unparse(node.targets[0]) == "report['quantification_complete']"]
    need(len(final_assignment) == 1 and isinstance(final_assignment[0].value, ast.BoolOp),
         'Pinned final observation gate differs')
    final_assignment[0].value.values.append(ast.parse("report.get('non_Dress184_strict_passed', False)", mode='eval').body)

    candidate = index_once(main.body, "report['candidate_scope'] =")
    main.body[candidate:candidate+1] = statements("""
report['candidate_scope'] = ('Fixed failed derived Action input; real Direct validation/capture/endpoint strip; '
    'independent cleaned217 Rig with FULL/rotation/local flags and real parent-before-child native LRS projection. '
    'Only the3040 canonical REST-baked LBS target surface is measured against original Manual source. '
    'All217 matrix discrepancies are diagnostic;184 non-Dress motion retains the original2e-4 FK guard. '
    'Original217 parents/geometric Rest/names/weights remain fixed. Original TRS2e-5 gate is not changed or passed. '
    'No FBX, Unity, Magica, production binding, source Manual equivalence or approximation acceptance. '
    'This observation must precede constructing a distinct target Action for private paired FBX fidelity.')
""")
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value == 'PRIVATE_THREE_FRAME_NATIVE_TRS_SKIN_ERROR_QUANTIFICATION_V4_SINGLE_FACTOR_C_ONLY':
            node.value = 'PRIVATE_STANDARD_FULL_PARENT_NATIVE_DEPTH_LRS_AND_LBS_SKIN_DIAGNOSTIC_V1'
        if isinstance(node, ast.Constant) and node.value == 'CURRENT_RUNTIME_SINGLE_FACTOR_C_A_DIAGNOSTIC_ONLY':
            node.value = 'CURRENT_RUNTIME_STANDARD_PARENT_DIAGNOSTIC_ONLY'
    return ast.fix_missing_locations(tree)


if __name__ == '__main__':
    need(sha(PARENT) == PARENT_SHA and sha(STANDARD) == STANDARD_SHA, 'Frozen parent/helper SHA differs')
    namespace = dict(__name__='private_standard_parent_skin_component', __file__=str(Path(__file__).resolve()),
        PARENT=PARENT, PARENT_SHA=PARENT_SHA, STANDARD=STANDARD, STANDARD_SHA=STANDARD_SHA)
    exec(compile(prepare_tree(PARENT.read_text(encoding='utf-8')), str(Path(__file__).resolve()), 'exec'), namespace)
    raise SystemExit(namespace['main']())
