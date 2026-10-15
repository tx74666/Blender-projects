"""Private helper-only bake differential; source-only until Root runs it.

No scene/artifact save exists in this runner. ``practical005`` applies only the
pre-recorded source/live screen; Bake still reports exact live equivalence.
``exact`` requires bit-exact full geometry.
All original scripts remain independent and unchanged.
"""
import argparse
import datetime
import importlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_validation_support_v5 as witness
import native_bone_support as geometry
from private_playback_native_runner_v6 import (ALL_FRAMES, EXPECTED_INPUTS, isolation, select_scene, source_animation_layout, assert_fixed_source_reference_coverage)

# The old geometry helper is read-only. This worker-local dependency binding
# selects the extended witness without editing its historical source file.
geometry.base = witness
POLICY_PATH = HERE / 'BONE_ADOPTION_CRITERIA_005.md'
POLICY_SHA256 = 'de3dd16156b876db23f2f0e9aaeb70c7a1019ce51a991da588937ba400af7893'
REPLAY_SEQUENCES = (
    ('forward', tuple(range(1, 31))),
    ('reverse', tuple(range(30, 0, -1))),
    ('jump', (1, 30, 7, 23, 2, 29, 15, 3, 26, 1)),
    ('loop', (29, 30, 1, 2, 29, 30, 1, 2)),
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def geometry_gate(comparison, policy, converted=()):
    require(policy in ('exact', 'practical005'), 'Select an explicit supported geometry policy')
    require(comparison['strict_nonvector_outputs_exact'], 'A strict nonvector output changed')
    failures = []
    for name, fields in comparison['meshes'].items():
        for field, metrics in fields.items():
            if metrics['exact']:
                continue
            if policy == 'exact' or name not in converted:
                failures.append(name + ':' + field + ':not-exact')
                continue
            if field == 'vertex_coordinates':
                diagonal = metrics['source_bbox_diagonal']
                maximum, rms = metrics['max_error_fraction_of_bbox_diagonal'], metrics['rms_error_fraction_of_bbox_diagonal']
                passed = (math.isfinite(diagonal) and diagonal > 0 and maximum is not None and rms is not None
                          and math.isfinite(maximum) and math.isfinite(rms) and maximum <= 1e-6 and rms <= 2e-7)
            else:
                maximum, rms = metrics['max_vector_error'], metrics['rms_vector_error']
                passed = math.isfinite(maximum) and math.isfinite(rms) and maximum <= 5e-5 and rms <= 1e-5
            if not passed:
                failures.append(name + ':' + field + ':screen-exceeded')
    return {'passed': not failures, 'failures': failures, 'policy': policy,
            'exact': comparison['all_coordinates_and_normals_exact']}


def replay_native(scene, frame):
    """Only native animation evaluation: no manual helper or core execution."""
    import bpy
    select_scene(scene)
    began = time.perf_counter_ns()
    scene.frame_set(frame)
    advanced = time.perf_counter_ns()
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    finished = time.perf_counter_ns()
    return graph, {'frame_advance_ms': (advanced-began)/1e6,
                   'native_update_ms': (finished-advanced)/1e6,
                   'native_pipeline_ms': (finished-began)/1e6}


def full_action_state(action, bake, excluded=()):
    excluded = set(excluded)
    state = bake._action_state(action, excluded)
    # Blender 5.2 has no Action.fcurves API. An empty unrelated Action can
    # report legacy, but no populated legacy clip is admitted by this runner.
    legacy = ()
    if action.is_action_legacy:
        require(getattr(action, 'is_empty', False) is True,
                'Nonempty legacy Actions are unsupported; no empty-layer curve proof is accepted')
        legacy = ('explicit-native-empty-action',)
    return state, legacy, bake._properties(action)


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native, 'Private factory-startup worker required')
    require(any(value in ('-t', '--threads') and native[index+1] == '1'
                for index, value in enumerate(native[:-1])), 'Explicit native -t 1 required')
    source_file, artist_file = Path(args.input).resolve(), Path(args.artist).resolve()
    require(source_file != artist_file and not os.path.samefile(source_file, artist_file),
            'Never open the artist or a hard link to it')
    before_input, before_artist = witness.pin(source_file), witness.pin(artist_file)
    require(EXPECTED_INPUTS.get(before_input['sha256']) == before_input['bytes'], 'Unaccepted saved input')
    package = Path(args.addons).resolve() / 'character_designer'
    manifest_path = Path(args.source_manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    require(manifest.get('schema') == 'x.frozen-playback-source-seal/1', 'Unexpected source seal')
    source_seal = witness.verify_package_manifest(package, manifest)
    decision_policy = witness.pin(POLICY_PATH)
    require(decision_policy['sha256'] == POLICY_SHA256, 'Pre-native geometry decision policy changed')
    witness_pins = witness.witness_dependency_pins()
    report.update(input_before=before_input, artist_before=before_artist,
                  source_manifest=witness.pin(manifest_path), source_seal=source_seal,
                  scripts={path.name: witness.pin(path) for path in
                           (Path(__file__), Path(witness.__file__), Path(geometry.__file__),
                            HERE/'native_source_reference_witness_v5.py', HERE/'private_playback_native_runner_v6.py')},
                  blender=bpy.app.version_string, geometry_policy=args.geometry_policy,
                  decision_policy=decision_policy, witness_dependency_pins=witness_pins,
                  geometry_policy_description='bit-exact coordinates and all normals' if args.geometry_policy == 'exact'
                  else 'Root005 fixed source/live engineering screen; exact Bake equivalence remains separate',
                  preparations=[], live_checks=[], bake_receipts=[], replay_checks=[], cleanups=[])
    sys.path.insert(0, str(package.parent))
    addon = importlib.import_module('character_designer')
    runtime = importlib.import_module('character_designer.forearm_twist')
    core = importlib.import_module('character_designer.forearm_twist_playback_core')
    bone = importlib.import_module('character_designer.forearm_twist_bone_preview')
    bake = importlib.import_module('character_designer.forearm_twist_bone_bake')
    builder = importlib.import_module('character_designer.forearm_twist_playback_scene').build_isolated_scene
    require(Path(addon.__file__).resolve().parent == package, 'Imported a different addon package')
    report['version'] = list(addon.bl_info['version'])
    registered, source_scene, session = False, None, None
    templates, plans, previews, samplers, private_ids = [], [], {}, {}, set()
    initial_output = initial_props = initial_context = source_actions = None
    source_pairs, source_rigs = [], {}
    handlers_before = witness.handler_snapshot()
    forbidden_saved = []

    def action_proof(actions):
        return {str(bake._id(action)): bake._hash(full_action_state(action, bake)) for action in actions}

    def context_proof():
        layer = source_scene.view_layers[0]
        active = layer.objects.active
        return {'filepath': bpy.data.filepath, 'frame': source_scene.frame_current,
                'subframe': float(source_scene.frame_subframe).hex(),
                'active': bake._id(active) if active is not None else None,
                'selected': sorted(bake._id(obj) for obj in source_scene.objects if obj.select_get(view_layer=layer)),
                'rig_active_animation': {name: {'rig': bake._id(rig),
                    'action': bake._id(rig.animation_data.action),
                    'slot': rig.animation_data.action_slot.handle,
                    'identifier': rig.animation_data.action_slot.identifier} for name, rig in source_rigs.items()}}

    def evaluate_source(frame, subframe=0.0):
        select_scene(source_scene)
        source_scene.frame_set(frame, subframe=subframe)
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        for _name, obj in source_pairs:
            if obj.type == 'MESH' and runtime.RECORD_KEY in obj:
                runtime._calculate_object(obj, graph)
        bpy.context.view_layer.update()
        require(not runtime._ERRORS, 'Source authoring errors: ' + repr(runtime._ERRORS))

    def protect_source(output, props, context):
        select_scene(source_scene)
        bpy.context.view_layer.update()
        comparison = witness.compare_witness(output, witness.frame_witness(source_scene, source_pairs, runtime, {}))
        require(comparison['exact'] and props == witness.source_property_witness(source_scene),
                'Private source native output, raw/registered RNA or referenced foreign payload changed')
        require(context == context_proof(), 'Private source context/active Action/slot changed')
        require(source_actions == action_proof(source_action_ids), 'Original Action contents/slots changed')
        return {'exact': True, 'source_properties_sha256': props['sha256'],
                'registered_reference_sha256': props['registered_source_and_external_objects']['sha256']}

    def close_private():
        nonlocal session, private_ids
        errors = []
        for sampler in samplers.values():
            try:
                sampler.close()
            except BaseException:
                errors.append(traceback.format_exc())
        samplers.clear()
        for info in previews.values():
            try:
                info['preview'].close()
            except BaseException:
                errors.append(traceback.format_exc())
        previews.clear()
        for plan in plans:
            bone.discard_plan(plan)
        plans.clear()
        for template in templates:
            core.discard_template(template)
        templates.clear()
        if source_scene is not None:
            select_scene(source_scene)
        if session is not None:
            try:
                session.close()
            except BaseException:
                errors.append(traceback.format_exc())
        remaining = sorted(private_ids & witness.native_id_pointers())
        report['cleanups'].append({'errors': errors, 'remaining_private_pointers': remaining,
                                   'all_owned_ids_removed': not remaining})
        require(not errors and not remaining, 'Disposable bake cleanup failed; foreign IDs are never deleted')
        session, private_ids = None, set()

    try:
        addon.register()
        registered = True
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(source_file)), 'Private input open failed')
        require(Path(bpy.data.filepath).resolve() == source_file, 'Opened a different file')
        source_scene = bpy.context.scene
        require(source_scene.frame_start == 1 and source_scene.frame_end == 30
                and source_scene.render.fps == 30 and source_scene.render.fps_base == 1.0,
                'Only the admitted 1-30, 30 FPS clip is supported')
        source_pairs = [(obj.name, obj) for obj in source_scene.objects]
        calibrated = [obj for _name, obj in source_pairs if obj.type == 'MESH' and runtime.RECORD_KEY in obj]
        require(calibrated, 'No calibrated source owner')
        source_rigs = {obj.name: runtime._check_mesh(obj) for obj in calibrated}
        require(len({rig.as_pointer() for rig in source_rigs.values()}) == len(source_rigs),
                'Multiple calibrated meshes sharing one rig require a coordinated future bake builder')
        for rig in source_rigs.values():
            ad = rig.animation_data
            require(ad is not None and ad.action is not None and ad.action_slot is not None,
                    'Every calibrated rig needs an explicit active Action and slot')
        source_action_ids = tuple(bpy.data.actions)
        source_actions = action_proof(source_action_ids)
        report['initial_source_animation_layout'] = source_animation_layout(source_scene)
        report['worker_dirty_at_open'] = bpy.data.is_dirty
        start_frame, start_subframe = source_scene.frame_current, source_scene.frame_subframe
        converted_source = {obj.name: {'managed_names': tuple(record['key'] for record in runtime._records(obj).values())}
                            for obj in calibrated}
        rig_names = {obj.name: tuple(b.name for b in obj.data.bones) for _name, obj in source_pairs if obj.type == 'ARMATURE'}

        with runtime.defer_runtime(bpy.context, flush_on_exit=False):
            evaluate_source(start_frame, start_subframe)
            initial_context = context_proof()
            initial_output = witness.frame_witness(source_scene, source_pairs, runtime, {})
            initial_props = witness.source_property_witness(source_scene)
            report['initial_source_reference_coverage'] = assert_fixed_source_reference_coverage(source_scene, initial_props, before_input)
            golden, golden_vectors = {}, {}
            for frame in ALL_FRAMES:
                evaluate_source(frame)
                golden[frame], raw = geometry.bone_frame_witness(source_scene, source_pairs, runtime, {}, converted_source, rig_names)
                golden_vectors[frame] = {name: geometry.compressed_vectors(values) for name, values in raw.items()}
                require(source_actions == action_proof(source_action_ids), 'Source golden evaluation changed an Action')
                if frame in (10, 20, 30):
                    print('BAKE_SOURCE_GOLDEN', frame, 30, flush=True)
            protected_output = witness.frame_witness(source_scene, source_pairs, runtime, {})
            protected_props, protected_context = witness.source_property_witness(source_scene), context_proof()
            old_ids, began = witness.native_id_pointers(), time.perf_counter_ns()
            source_plans = {}
            for obj in calibrated:
                template = core.capture(obj, bpy.context.evaluated_depsgraph_get())
                templates.append(template)
                plan = bone.plan_from_template(template)
                plans.append(plan)
                source_plans[obj] = (template, plan)
            captured = time.perf_counter_ns()
            try:
                session = builder(source_scene)
            finally:
                private_ids = witness.native_id_pointers() - old_ids
            scene, objects, eligible, reverse = isolation(session, source_scene, runtime)
            select_scene(scene)
            bpy.context.view_layer.update()
            build, converted = {}, {}
            for source, target in eligible.items():
                source_rig, (template, plan) = source_rigs[source.name], source_plans[source]
                rig = objects[source_rig]
                preview = bone.build_isolated_preview(target, rig, plan, template=template,
                    isolated_scene=scene, source_mesh=source, source_rig=source_rig, disposable=True)
                # Own the successfully issued controller before any later
                # sampler admission/read can fail and leave it unclosed.
                previews[source.name] = {'preview': preview, 'source': source, 'target': target}
                names = {name for side in plan.sides for name in (side.lower, side.hand)}
                previews[source.name]['inverses'] = {name: rig.data.bones[name].matrix_local.inverted() for name in names}
                sampler = bake.HelperBakeSampler(session, preview, source_rig=source_rig,
                                                source_action=source_rig.animation_data.action)
                samplers[source.name] = sampler
                converted[source.name] = {'managed_names': plan.managed_key_names,
                                         'mask_copies': dict(preview.mask_copies), 'bone_route': True}
                build[source.name] = {'weights': geometry.weight_rewrite_witness(source, target, rig, plan, preview),
                    'dormant': geometry.dormant_managed_keys(target, plan.managed_key_names)}
            pairs = [(source.name, target) for source, target in objects.items()]
            report['preparations'].append({'source_capture_ms': (captured-began)/1e6,
                'clone_bone_sampler_ms': (time.perf_counter_ns()-captured)/1e6})
            report['source_unchanged_by_preparation'] = protect_source(protected_output, protected_props, protected_context)

            def candidate_static_guards():
                for name, info in previews.items():
                    preview = info['preview']
                    bone.check_built_preview(preview)
                    preview._guard()
                    require(geometry.weight_rewrite_witness(info['source'], info['target'], preview.rig,
                            preview.plan, preview) == build[name]['weights'], 'Approved raw weights/masks changed')
                    require(geometry.dormant_managed_keys(info['target'], preview.plan.managed_key_names)
                            == build[name]['dormant'], 'Dormant corrective coordinates changed')

            def compare(golden_frame, compressed, current, raw):
                result = geometry.compare_frames(golden_frame, compressed, current, raw, converted_names=converted)
                for name in raw:
                    require(golden_frame['scope'][name]['evaluated_object_world_matrix_hex']
                            == current['scope'][name]['evaluated_object_world_matrix_hex'], 'An evaluated mesh world transform changed')
                result['declared_geometry_screen'] = geometry_gate(result, args.geometry_policy, converted)
                return result

            live, live_vectors, desired = {}, {}, {}
            for frame in ALL_FRAMES:
                graph, _timing = replay_native(scene, frame)
                for name, info in previews.items():
                    preview = info['preview']
                    evaluated = preview.rig.evaluated_get(graph)
                    transforms = {bone_name: evaluated.pose.bones[bone_name].matrix @ inverse
                                  for bone_name, inverse in info['inverses'].items()}
                    preview.update_from_deformations(transforms)
                bpy.context.view_layer.update()
                graph = bpy.context.evaluated_depsgraph_get()
                matrices = {}
                for name, info in previews.items():
                    preview = info['preview']
                    verified = preview.verify_evaluated(graph)
                    require(verified['completed'] and verified['within_tolerance'], 'Live helper matrix verification failed')
                    samplers[name].collect(frame, graph)
                    matrices[name] = verified
                candidate_static_guards()
                live[frame], raw = geometry.bone_frame_witness(scene, pairs, runtime, reverse, converted, rig_names)
                live_vectors[frame] = {name: geometry.compressed_vectors(values) for name, values in raw.items()}
                desired[frame] = {name: {key: matrix.copy() for key, matrix in info['preview']._desired_deformations.items()}
                                  for name, info in previews.items()}
                same = compare(golden[frame], golden_vectors[frame], live[frame], raw)
                report['live_checks'].append({'frame': frame, 'matrix_verification': matrices, **same})
                if frame in (10, 20, 30):
                    print('BAKE_LIVE_SAMPLES', frame, 30, flush=True)
            report['source_unchanged_by_live_collection'] = protect_source(protected_output, protected_props, protected_context)
            source_live_exact = all(row['all_coordinates_and_normals_exact'] for row in report['live_checks'])
            report['source_to_live_geometry_exact'] = source_live_exact
            require(all(row['declared_geometry_screen']['passed'] for row in report['live_checks']),
                    'Declared source/live geometry policy failed; no append performed')

            select_scene(scene)
            target_actions = tuple(target for source, target in session.id_map.items() if isinstance(source, bpy.types.Action))
            before_action = {action.as_pointer(): full_action_state(action, bake) for action in target_actions}
            old_curves = {action.as_pointer(): {curve.as_pointer() for bag in bake._bags(action) for curve in bag.fcurves}
                          for action in target_actions}
            for name, sampler in samplers.items():
                receipt = sampler.append()
                require(receipt['completed'] and receipt['existing_animation_unchanged'] and receipt['source_unchanged'],
                        'Helper append proof failed')
                report['bake_receipts'].append({'owner': name, **receipt})
            for action in target_actions:
                added = {curve.as_pointer() for bag in bake._bags(action) for curve in bag.fcurves} - old_curves[action.as_pointer()]
                require(full_action_state(action, bake, added) == before_action[action.as_pointer()],
                        'Preexisting private Action channels/slots changed')
            baked_action_proof = action_proof(target_actions)
            report['baked_actions_sha256'] = witness.object_hash(baked_action_proof)

            # These worker-only tripwires turn any accidental helper/core call
            # into failure during the native-only replay, including callbacks.
            def forbidden(*_args, **_kwargs):
                raise RuntimeError('Manual helper/authoring/core execution is forbidden during baked replay')
            for owner, name in [(runtime, '_calculate_object'), (core, 'capture'), (core, 'prepare')]:
                forbidden_saved.append((owner, name, getattr(owner, name)))
                setattr(owner, name, forbidden)
            for info in previews.values():
                preview = info['preview']
                for name in ('update_from_deformations', 'verify_evaluated'):
                    forbidden_saved.append((preview, name, getattr(preview, name)))
                    setattr(preview, name, forbidden)
            baked_first, baked_first_vectors = {}, {}
            for sequence, frames in REPLAY_SEQUENCES:
                for index, frame in enumerate(frames):
                    graph, timing = replay_native(scene, frame)
                    candidate_static_guards()
                    matrix_checks = {}
                    for name, info in previews.items():
                        preview, checks = info['preview'], []
                        evaluated = preview.rig.evaluated_get(graph)
                        for helper in preview.plan.helpers:
                            pose = evaluated.pose.bones[preview.helper_names[helper.key]]
                            current = pose.matrix @ preview._rest[helper.key].inverted()
                            difference = bone.matrix_difference(current, desired[frame][name][helper.key], tolerance=2e-6)
                            require(difference['within_tolerance'], 'Native baked helper matrix exceeded fixed tolerance')
                            checks.append(difference)
                        matrix_checks[name] = {'within_tolerance': True, 'helper_count': len(checks),
                            'max_abs': max((item['max_abs'] for item in checks), default=0.)}
                    current, raw = geometry.bone_frame_witness(scene, pairs, runtime, reverse, converted, rig_names)
                    same_live = compare(live[frame], live_vectors[frame], current, raw)
                    same_source = compare(golden[frame], golden_vectors[frame], current, raw)
                    if frame not in baked_first:
                        baked_first[frame] = current
                        baked_first_vectors[frame] = {name: geometry.compressed_vectors(values) for name, values in raw.items()}
                        same_repeat = {'first_baked_observation': True}
                    else:
                        same_repeat = compare(baked_first[frame], baked_first_vectors[frame], current, raw)
                        require(same_repeat['all_coordinates_and_normals_exact'],
                                'Repeated native baked output did not reproduce its own exact candidate hashes')
                    require(baked_action_proof == action_proof(target_actions), 'Native replay changed Action content/slots')
                    report['replay_checks'].append({'sequence': sequence, 'index': index, 'frame': frame,
                        'timing_excludes_witnesses': timing, 'helper_matrix_oracle': matrix_checks,
                        'versus_live': same_live, 'versus_source': same_source, 'versus_first_baked': same_repeat})
                report['source_unchanged_after_' + sequence] = protect_source(protected_output, protected_props, protected_context)
                print('BAKE_NATIVE_REPLAY', sequence, len(frames), flush=True)
            live_bake_exact = all(row['versus_live']['all_coordinates_and_normals_exact'] for row in report['replay_checks'])
            source_bake_exact = all(row['versus_source']['all_coordinates_and_normals_exact'] for row in report['replay_checks'])
            report.update(live_to_baked_geometry_exact=live_bake_exact,
                          source_to_baked_geometry_exact=source_bake_exact,
                          strict_nonvector_outputs_exact=True, existing_actions_slots_curves_unchanged=True,
                          native_only_replay_sequences_completed=True,
                          source_live_declared_screen_passed=True,
                          source_bake_declared_screen_passed=all(row['versus_source']['declared_geometry_screen']['passed']
                                                                for row in report['replay_checks']),
                          bake_exact_live_equivalence=live_bake_exact,
                          geometry_accepted=False, artifact_eligible=False,
                          gui_fps_verified=False, subframes_verified=False)
            if args.geometry_policy == 'exact':
                require(source_live_exact and live_bake_exact and source_bake_exact,
                        'Exact geometry policy refused baked replay differences; retained for review')
    finally:
        errors = []
        for owner, name, original in reversed(forbidden_saved):
            setattr(owner, name, original)
        forbidden_saved.clear()
        try:
            close_private()
        except BaseException:
            errors.append(traceback.format_exc())
        if source_scene is not None and initial_context is not None:
            try:
                with runtime.defer_runtime(bpy.context, flush_on_exit=False):
                    evaluate_source(initial_context['frame'], float.fromhex(initial_context['subframe']))
                    restored = protect_source(initial_output, initial_props, initial_context)
                    report['source_restored_exact'] = restored['exact']
                    report['worker_dirty_at_end'] = bpy.data.is_dirty
            except BaseException:
                errors.append(traceback.format_exc())
        if registered:
            try:
                addon.unregister()
            except BaseException:
                errors.append(traceback.format_exc())
        checks = {'runtime_guard_released': not runtime._BUSY,
                  'handlers_restored_exact': handlers_before == witness.handler_snapshot(),
                  'known_lifecycle_timer_removed': not bpy.app.timers.is_registered(runtime._complete_runtime_lifecycle),
                  'templates_released': not len(core._ISSUED_TEMPLATES),
                  'plans_released': not len(bone._ISSUED_PLANS),
                  'built_controllers_released': not len(bone._BUILT_PREVIEWS),
                  'owned_ids_removed': all(row['all_owned_ids_removed'] and not row['errors'] for row in report['cleanups'])}
        report['cleanup'] = {'errors': errors, **checks}
        report['input_after'], report['artist_after'] = witness.pin(source_file), witness.pin(artist_file)
        report['input_disk_unchanged'] = before_input == report['input_after']
        report['artist_disk_unchanged'] = before_artist == report['artist_after']
        report['staged_source_unchanged'] = source_seal == witness.verify_package_manifest(package, manifest)
        report['runner_dependencies_unchanged'] = report['scripts'] == {
            name: witness.pin(item['path']) for name, item in report['scripts'].items()}
        report['witness_dependencies_unchanged'] = witness_pins == witness.witness_dependency_pins()
        report['decision_policy_unchanged'] = decision_policy == witness.pin(POLICY_PATH)
        require(not errors and all(checks.values()), 'Native worker cleanup failed')
        if initial_output is not None:
            require(report.get('source_restored_exact'), 'Private source state did not restore exactly')
        require(report['input_disk_unchanged'] and report['artist_disk_unchanged'] and report['staged_source_unchanged']
                and report['witness_dependencies_unchanged'] and report['decision_policy_unchanged']
                and report['runner_dependencies_unchanged'],
                'Protected input, artist disk or staged source changed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('input', 'artist', 'addons', 'source-manifest', 'report'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--geometry-policy', choices=('exact', 'practical005'), required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report_path = Path(args.report).resolve()
    require(not report_path.exists(), 'Never overwrite evidence')
    protected_paths = {Path(value).resolve() for value in (args.input, args.artist, args.source_manifest, __file__)}
    require(report_path not in protected_paths, 'Report cannot replace protected input/source')
    report = {'schema': 'x.private-helper-bone-bake/1', 'completed': False, 'pid': os.getpid(),
              'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'model_and_reasoning_effort': 'unrecorded', 'no_artist_open_or_save': True,
              'scene_save_supported': False, 'artifact_write_supported': False,
              'no_deploy': True, 'performance_acceptance': False,
              'limits': ['Private background only; neither GUI FPS nor authoring adoption is certified.',
                         'The artist process is never opened or accessed; disk pins are checked before/after.',
                         'Worker dirty state is observed, not claimed to be restored by temporary-ID removal.',
                         'Practical005 is a fixed source/live screen, never an exact Bake waiver or artist adoption.',
                         'Bake/live exact failures remain reported separately; no artifact-writing branch exists.',
                         'Only integer frames 1-30 are covered; subframes, physics and other clips are unsupported.',
                         'Raw geometry arrays are compressed only in worker memory; reports contain hashes/metrics.']}
    try:
        main(args, report)
        report['completed'] = True
    except BaseException:
        report['error'] = traceback.format_exc()
        raise
    finally:
        payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
        with report_path.open('x', encoding='utf-8') as stream:
            stream.write(payload)
