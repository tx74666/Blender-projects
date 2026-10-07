"""One opt-in world-direction/speed change over immutable disposable Live V5.

--movement-stress means controlled walking/running/stop-turn pressure input,
not an imported clip or accepted foot-contact gait. Default and leg_raise retain
the V5 displacement expression. No physics, held/forward, or cleanup changes.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PARENT = HERE / "verify_live_direct_cloth52_disposable_fixture_v5.py"
PARENT_SHA = "53f40ddddfc89e4912835130fc14c36a1cb544eeb41f63ebed16b3b6e2b3cc7b"


def need(condition, message):
    if not condition:
        raise RuntimeError("LiveMovementStress52: " + message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parent():
    need(sha(PARENT) == PARENT_SHA, "Immutable V5 changed")
    spec = importlib.util.spec_from_file_location("live_movement_stress_frozen_v5", PARENT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def matrix4(value):
    need(isinstance(value, (list, tuple)) and len(value) == 4
         and all(isinstance(row, (list, tuple)) and len(row) == 4 for row in value)
         and all(type(x) in (float, int) and math.isfinite(x) for row in value for x in row),
         "Complete finite matrix required")
    need(list(value[3]) == [0., 0., 0., 1.], "Affine last row differs")
    return [list(row) for row in value]


def inverse3(matrix):
    a, b, c = [row[:3] for row in matrix[:3]]
    cross = lambda u, v: [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    bc, ca, ab = cross(b, c), cross(c, a), cross(a, b)
    determinant = sum(x*y for x, y in zip(a, bc))
    need(math.isfinite(determinant) and determinant > 1.e-12, "Positive nonsingular chart required")
    return [[bc[i]/determinant, ca[i]/determinant, ab[i]/determinant] for i in range(3)]


def matvec(matrix, value):
    return [sum(row[j]*value[j] for j in range(3)) for row in matrix[:3]]


def uniform_evidence(value):
    matrix = matrix4(value)
    columns = [[matrix[i][j] for i in range(3)] for j in range(3)]
    lengths = [math.sqrt(sum(x*x for x in column)) for column in columns]
    need(min(lengths) > 1.e-8 and max(lengths)-min(lengths) <= max(lengths)*1.e-6,
         "Positive uniform chart required")
    need(all(abs(sum(x*y for x, y in zip(columns[i], columns[j])))
             <= lengths[i]*lengths[j]*1.e-6 for i, j in ((0, 1), (0, 2), (1, 2))),
         "Orthogonal chart required")
    inverse = inverse3(matrix)
    return {"matrix": matrix, "axis_lengths": lengths, "inverse3": inverse,
            "positive_uniform_orthogonal": True, "scale_hardcoded_for_conversion": False}


def make_plan(args, rig_world, root_rest, metres, fps, *, rig_parentless, root_parentless,
              object_constraints_empty, root_constraints_empty, local_location, rotation_mode):
    need(args.case in ("walk", "run", "abrupt_stop_turn") and args.frames == 60,
         "Stress is restricted to the original 60-frame walking/running/stop-turn cases")
    need(type(metres) in (int, float) and math.isfinite(metres) and metres > 0.
         and type(fps) in (int, float) and fps == 30., "Native metres and exact 30fps required")
    need(all(value is True for value in (rig_parentless, root_parentless, object_constraints_empty,
                                         root_constraints_empty, local_location)) and rotation_mode == "XYZ",
         "Root/rig must be parentless and unconstrained, with existing XYZ and local location")
    world, rest = uniform_evidence(rig_world), uniform_evidence(root_rest)
    need(max(abs(length-1.) for length in rest["axis_lengths"]) <= 1.e-6,
         "Native Root Rest basis must have unit axes")
    speed = 1.2 if args.case == "walk" else 3.
    duration = (args.frames-1)/fps
    return {"case": args.case, "frames": args.frames, "fps": fps, "metres_per_world_unit": metres,
            "requested_speed_m_s": speed, "duration_seconds": duration,
            "stop_translation_progress": .55 if args.case == "abrupt_stop_turn" else 1.,
            "world_direction": [0., -1., 0.], "rig_world": world, "Root_rest": rest,
            "conversion": "inverse Root Rest 3x3 @ inverse actual Rig world 3x3 @ world delta",
            "input_kind": "Controlled walking/running/stop-turn pressure action; not imported clip",
            "gait_and_14_curves_changed": False, "physical_parameters_changed": False,
            "foot_contact_or_natural_gait_accepted": False, "accepted": False}


def native_plan(args, rig, root, home, metres):
    if not args.movement_stress or args.case == "leg_raise":
        return None
    # Native RNA reads only. No matrix setter, mode conversion, or extra seek.
    return make_plan(args, [list(row) for row in rig.matrix_world],
                     [list(row) for row in root.bone.matrix_local], metres,
                     home.render.fps/home.render.fps_base,
                     rig_parentless=rig.parent is None, root_parentless=root.parent is None,
                     object_constraints_empty=len(rig.constraints) == 0,
                     root_constraints_empty=len(root.constraints) == 0,
                     local_location=bool(root.bone.use_local_location), rotation_mode=root.rotation_mode)


def desired_distance(plan, progress):
    need(type(progress) in (int, float) and math.isfinite(progress) and 0. <= progress <= 1.,
         "Bounded original translation progress required")
    return plan["requested_speed_m_s"]*plan["duration_seconds"]*progress*plan["stop_translation_progress"]


def location_delta(move, plan):
    original_coefficient = .7 if plan["case"] == "run" else .35
    progress = move["forward_height"]/original_coefficient
    distance = desired_distance(plan, progress)/plan["metres_per_world_unit"]
    world_delta = [0., -distance, 0.]
    return matvec(plan["Root_rest"]["inverse3"], matvec(plan["rig_world"]["inverse3"], world_delta))


def measured_series(plan, rows, metres):
    if plan is None:
        return {"enabled": False, "default_or_leg_V5_displacement_unchanged": True, "accepted": False}
    need(len(rows) == plan["frames"] and [row["frame"] for row in rows] == list(range(1, plan["frames"]+1)),
         "Complete ordered native Root series required")
    matrices = [matrix4(row["Root"]) for row in rows]
    positions = [[matrix[i][3] for i in range(3)] for matrix in matrices]
    origin = positions[0]
    observations, velocities, errors = [], [], []
    for index, point in enumerate(positions):
        progress = index/(plan["frames"]-1)
        if plan["case"] == "abrupt_stop_turn":
            progress = min(progress/.55, 1.)
        desired = [0., -desired_distance(plan, progress), 0.]
        observed = [(point[i]-origin[i])*metres for i in range(3)]
        errors.append(math.dist(observed, desired))
        observations.append({"frame": index+1, "time_seconds": index/plan["fps"],
                             "actual_world_displacement_m": observed, "desired_world_displacement_m": desired})
        if index:
            velocity = [(point[i]-positions[index-1][i])*metres*plan["fps"] for i in range(3)]
            velocities.append({"first_frame": index, "last_frame": index+1,
                               "actual_world_velocity_m_s": velocity,
                               "actual_speed_m_s": math.sqrt(sum(v*v for v in velocity))})
    return {"enabled": True, "native_evaluated_Root_series": True, "samples": observations,
            "step_velocities": velocities, "maximum_desired_position_error_m": max(errors),
            "actual_final_world_displacement_m": observations[-1]["actual_world_displacement_m"],
            "actual_world_speed_min_m_s": min(row["actual_speed_m_s"] for row in velocities),
            "actual_world_speed_max_m_s": max(row["actual_speed_m_s"] for row in velocities),
            "desired_equals_observed_assumed": False, "scope": "Native world displacement/time only; not GUI FPS or gait acceptance",
            "accepted": False}


def substitutions():
    return (
        ('    old_location, old_euler = Vector(root.location), Vector(root.rotation_euler)\n',
         '    movement_plan = native_movement_plan(args,rig,root,home,metres)\n'
         '    report["world_movement_stress_plan"] = movement_plan; write()\n'
         '    old_location, old_euler = Vector(root.location), Vector(root.rotation_euler)\n'),
        ('        root.location = old_location + Vector((0.,height*move["forward_height"],0.))\n',
         '        root.location = old_location + (Vector((0.,height*move["forward_height"],0.)) if movement_plan is None else Vector(movement_location_delta(move,movement_plan)))\n'),
        ('    report["real_body_motion_response"]=response;write()\n',
         '    report["real_body_motion_response"]=response;write()\n'
         '    report["world_movement_stress_observed"] = measured_world_movement(movement_plan,root_rows,metres); write()\n'
         '    if movement_plan is not None: need(report["world_movement_stress_observed"]["maximum_desired_position_error_m"]<=guard,"actual native world travel differs from requested stress by original50um motion guard")\n'),
    )


def dynamic_source(v5, live):
    original = v5.compiled_dynamic_source(live)
    source = original
    for old, new in substitutions():
        need(source.count(old) == 1, "Unique Root-motion observation substitution differs")
        source = source.replace(old, new, 1)
    reverse = source
    for old, new in reversed(substitutions()):
        need(reverse.count(new) == 1, "Reversible Root-motion substitution differs")
        reverse = reverse.replace(new, old, 1)
    need(reverse == original, "V5 native recipe/physics/held/finally changed outside three Root-motion substitutions")
    compile(source, str(Path(__file__)), "exec")
    return source


def prepared_namespace(v5, parts, args):
    saved = v5.compiled_dynamic_source
    # V5 builds its exact real Main and restores closure/Root through the same
    # _DYNAMIC object. Temporarily replace only its source producer, not Main.
    class SourceView:
        compiled_dynamic_source = staticmethod(saved)
    try:
        v5.compiled_dynamic_source = lambda live: dynamic_source(SourceView, live)
        namespace = v5.prepared_namespace(*parts, args)
    finally:
        v5.compiled_dynamic_source = saved
    namespace["_live_private_dynamic_globals"].update(native_movement_plan=native_plan,
        movement_location_delta=location_delta, measured_world_movement=measured_series)
    namespace["__file__"] = str(Path(__file__))
    namespace["PINS"].update({PARENT: PARENT_SHA, Path(__file__): sha(Path(__file__))})
    need(namespace["main"].__globals__ is namespace and v5.compiled_dynamic_source is saved,
         "Actual Main globals or source-producer restoration differs")
    return namespace


def pure_checks(v5):
    from types import SimpleNamespace
    live = v5.load(v5.LIVE, v5.LIVE_SHA, "movement_stress_frozen_live")
    original = v5.compiled_dynamic_source(live); changed = dynamic_source(v5, live)
    need(ast.dump(ast.parse(original)) != ast.dump(ast.parse(changed)), "Stress source was not changed")
    scale = .782315731048584
    world = [[scale,0.,0.,0.], [0.,scale,0.,0.], [0.,0.,scale,0.], [0.,0.,0.,1.]]
    # A rotated Root Rest basis verifies both inverses; identity would conceal
    # omission of the Root chart. The physical scale is read, never a divisor constant.
    rest = [[0.,-1.,0.,0.], [1.,0.,0.,0.], [0.,0.,1.,0.], [0.,0.,0.,1.]]
    flags = dict(rig_parentless=True, root_parentless=True, object_constraints_empty=True,
                 root_constraints_empty=True, local_location=True, rotation_mode="XYZ")
    positives = 0
    for case in ("walk", "run", "abrupt_stop_turn"):
        args = SimpleNamespace(case=case, frames=60)
        plan = make_plan(args, world, rest, 1., 30., **flags)
        for frame in (1,19,34,35,60):
            move = live.input_recipe(case,frame,60); delta = location_delta(move,plan)
            actual = matvec(world, matvec(rest,delta))
            desired = desired_distance(plan, move["forward_height"]/(.7 if case=="run" else .35))
            need(math.dist(actual,[0.,-desired,0.])<=1.e-12, "Inverse chart/world -Y conversion failed")
        rows=[]
        for frame in range(1,61):
            move=live.input_recipe(case,frame,60); displacement=matvec(world,matvec(rest,location_delta(move,plan)))
            matrix=copy.deepcopy(world)
            for i in range(3):matrix[i][3]=displacement[i]
            rows.append({"frame":frame,"Root":matrix})
        result=measured_series(plan,rows,1.)
        need(result["maximum_desired_position_error_m"]<=1.e-12 and result["actual_final_world_displacement_m"][1]<0., "Actual-series direction/speed proof failed")
        altered=copy.deepcopy(rows);altered[19]["Root"][1][3]+=.001
        need(measured_series(plan,altered,1.)["maximum_desired_position_error_m"]>5.e-5, "Wrong measured Root motion was hidden")
        positives+=1
    negative_count=0
    for key,value in (("rig_parentless",False),("root_parentless",False),("root_constraints_empty",False),("local_location",False),("rotation_mode","QUATERNION")):
        altered=dict(flags);altered[key]=value
        try:make_plan(SimpleNamespace(case="run",frames=60),world,rest,1.,30.,**altered)
        except RuntimeError:negative_count+=1
        else:need(False,"Unsupported Root chart/controller admitted")
    for altered in ([[[-x if j==0 else x for j,x in enumerate(row)] for row in world]][0],
                    [[scale*2,0.,0.,0.], [0.,scale,0.,0.], [0.,0.,scale,0.], [0.,0.,0.,1.]]):
        try:make_plan(SimpleNamespace(case="run",frames=60),altered,rest,1.,30.,**flags)
        except RuntimeError:negative_count+=1
        else:need(False,"Negative/nonuniform Rig world admitted")
    # Exact original expression branch, not a numerical approximation.
    root_assignment=next(n for n in ast.walk(ast.parse(changed)) if isinstance(n,ast.Assign)
                         and isinstance(n.targets[0],ast.Attribute) and n.targets[0].attr=="location"
                         and isinstance(n.targets[0].value,ast.Name) and n.targets[0].value.id=="root"
                         and isinstance(n.value,ast.BinOp) and isinstance(n.value.left,ast.Name)
                         and n.value.left.id=="old_location")
    default_expr=root_assignment.value.right.body
    original_assignment=next(n for n in ast.walk(ast.parse(original)) if isinstance(n,ast.Assign)
                            and isinstance(n.targets[0],ast.Attribute) and n.targets[0].attr=="location"
                            and isinstance(n.targets[0].value,ast.Name) and n.targets[0].value.id=="root"
                            and isinstance(n.value,ast.BinOp) and isinstance(n.value.left,ast.Name)
                            and n.value.left.id=="old_location")
    need(ast.dump(default_expr)==ast.dump(original_assignment.value.right),"Default V5 displacement expression bits changed")
    for case in ("walk","run","abrupt_stop_turn","leg_raise"):
        need(native_plan(SimpleNamespace(movement_stress=False,case=case),None,None,None,None) is None,"Default read native RNA")
    need(native_plan(SimpleNamespace(movement_stress=True,case="leg_raise"),None,None,None,None) is None,"Leg displacement changed by stress flag")
    cold=v5.load(v5.COLD,v5.COLD_SHA,"movement_stress_CLI_cold")
    cli_before=list(sys.argv)
    try:
        sys.argv=[str(Path(__file__)),"--","--pure-checks","--movement-stress","--case","leg_raise",
                  "--input-proof",str(cold.INPUT_COMPONENT),"--input-proof-sha",cold.INPUT_COMPONENT_SHA,
                  "--artist-protection",str(HERE/"artist_disk_protection_20261006_1e7bb077fed2.json"),
                  "--artist-protection-sha","bc9c272c6b933ce09b02a8f1f740ba8df54e7958f98d1bc5b2fa9041c92f8f06"]
        try:arguments(v5)
        except RuntimeError as error:
            need("Movement stress is not a leg_raise option" in str(error),"Wrong CLI negative blocked before leg stress guard")
        else:need(False,"Leg_raise movement-stress CLI silently admitted")
    finally:sys.argv=cli_before
    return {"passed":True,"native":False,"reversible_source_substitutions":3,
            "world_inverse_speed_series_cases":positives,"unsupported_chart_negatives":negative_count,
            "default_expression_AST_exact":True,"leg_unchanged":True,"leg_stress_CLI_rejected":True,
            "actual_native_motion":"NotRun","accepted":False}


def arguments(v5):
    before=list(sys.argv)
    tail=before[before.index("--")+1:] if "--" in before else before[1:]
    import argparse
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument("--movement-stress",action="store_true")
    stress,remaining=parser.parse_known_args(tail)
    try:
        sys.argv=[before[0],"--",*remaining]
        args=v5.arguments()
    finally:sys.argv=before
    args.movement_stress=stress.movement_stress
    need(not args.movement_stress or args.case!="leg_raise","Movement stress is not a leg_raise option; use only the unchanged leg sign")
    if args.movement_stress and args.case!="leg_raise":need(args.frames==60,"Opt-in movement stress requires60frames")
    return args


def main():
    v5=parent();args=arguments(v5)
    if args.pure_checks:
        print(json.dumps(pure_checks(v5),allow_nan=False));return 0
    parts=v5.components(args)
    v5.paired_component_proof(args.cold_proof,args.cold_proof_sha,args.input_proof,args.input_proof_sha)
    namespace=prepared_namespace(v5,parts,args)
    return namespace["main"](args)


if __name__=="__main__":
    raise SystemExit(main())
