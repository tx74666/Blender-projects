"""Root-invoked native NEW Raise authoring in its disposable Blender copy.

Importing starts nothing. run saves no .blend, launches no process and publishes
nothing. It creates a real local Action/NewAction manifest through register_b,
then keys only the declared FK inputs. This is timing QA, not pose art approval.
"""
import json
import math
from pathlib import Path
import re
import traceback
import uuid

import composition_timing_acceptance as timing

SCHEMA = 'x.validation.character-composition-raise-authoring-fixture/1'
REPORT_SCHEMA = 'x.validation.character-composition-raise-authoring/1'
FIELDS = {'schema', 'evidenceDirectory', 'preparedRaiseWorkItemId',
          'collectedHoldLoopWorkItemId', 'expectedModelSha256',
          'followingHoldPublication', 'rotationControl'}


def validate_config(config):
    timing.require(type(config) is dict and set(config) == FIELDS and config['schema'] == SCHEMA,
                   'Supply the exact genuine Raise authoring fixture.')
    held, prepared = (uuid.UUID(config[key]).hex for key in
                      ('collectedHoldLoopWorkItemId', 'preparedRaiseWorkItemId'))
    timing.require(held != prepared and all(int(value, 16) != 0 for value in (held, prepared)),
                   'Choose distinct genuine collected Loop and prepared SOURCE Raise rows.')
    timing.require(type(config['expectedModelSha256']) is str
        and re.fullmatch('[0-9a-f]{64}', config['expectedModelSha256']), 'Pin the current prepared model SHA.')
    timing.require(config['rotationControl'] is None or type(config['rotationControl']) is str,
                   'Choose null or one exact declared FK input control, never an alias.')
    # Reuse the bounded, real physical-publication admission without creating a receipt.
    timing.validate_config({'schema': timing.SCHEMA, 'evidenceDirectory': config['evidenceDirectory'],
        'holdLoopWorkItemId': held, 'followingHoldWorkItemId': held, 'raiseWorkItemId': prepared,
        'expectedModelSha256': config['expectedModelSha256'], 'poseTolerance': 2e-4,
        'inputTolerance': 1e-5, 'followingHoldPublication': config['followingHoldPublication']})
    return config


def _set_inputs(rig, scope, values):
    timing.require(len(values) == len(scope.channels), 'Every scoped input requires a real native value.')
    pending = []
    for (path, index), value in zip(scope.channels, values):
        array = rig.path_resolve(path)
        timing.require(hasattr(array, '__len__') and 0 <= index < len(array)
                       and type(value) in (int, float) and math.isfinite(value),
                       'Unsupported/nonfinite exact FK input: ' + path)
        pending.append((array, index, value))
    for array, index, value in pending:
        array[index] = value


def _key_inputs(rig, scope, frame):
    for path, index in scope.channels:
        timing.require(rig.keyframe_insert(data_path=path, index=index, frame=frame),
                       'The native selected-slot FK key failed: ' + path)


def _rotation_control(rig, scope, requested):
    matches = []
    for name in sorted(set(scope.input_by_native.values())):
        bone = rig.pose.bones[name]
        field = ('rotation_quaternion' if bone.rotation_mode == 'QUATERNION' else
                 'rotation_axis_angle' if bone.rotation_mode == 'AXIS_ANGLE' else 'rotation_euler')
        path = bone.path_from_id() + '.' + field
        if (any(channel == path for channel, _index in scope.channels)
                and not bone.bone.hide and not bone.bone.hide_select and not bone.lock_rotation[0]):
            matches.append(name)
    if requested:
        matches = [name for name in matches if name == requested]
    timing.require(matches, 'No exact visible declared FK rotation control is available.')
    return matches[0]


def _created_identity(row, spec, created):
    timing.require(created['workItemId'] == spec['editWorkItemId']
        and created['newActionId'] == spec['editNewActionId'],
        'Actual manifest IDs must preserve the exact sealed DTO strings, not a different UUID representation.')
    return {'work_item_id': created['workItemId'], 'new_action_id': created['newActionId'],
        'native_row_work_id': row.work_item_id, 'native_row_new_action_id': row.new_action_id,
        'item_id': row.item_id, 'manifest_path': row.manifest_path, 'slot': row.custom_slot}


def _author(context, row, held, held_seconds, modules, requested):
    import bpy
    from composition_session_acceptance import _view3d
    backend, ua = modules['animation_composition'], modules['unity_animation']
    held_sample = timing._isolated_samples(context, held, [held_seconds], modules)[0]
    with timing._open(context, held, modules) as (_session, _item, held_scope, _tracks):
        held_channels, held_names = tuple(held_scope.channels), tuple(held_scope.native_names)
    with timing._open(context, row, modules) as (session, _item, scope, tracks):
        timing.require(tuple(scope.channels) == held_channels and tuple(scope.native_names) == held_names,
                       'Raise and its collected Loop must have the exact same native FK input scope.')
        neutral = [scope.defaults[channel] for channel in scope.channels]
        endpoint = held_sample['inputs']
        name = _rotation_control(row.rig, scope, requested)
        start, end = backend._frame_range(session['spec'])
        before = backend._motion_hash(row.custom_action, row.custom_slot)
        keys = []
        with _view3d(context, row.rig):
            for bone in row.rig.data.bones:
                bone.select = bone.name == name
            row.rig.data.bones.active = row.rig.data.bones[name]
            for fraction in (0., .5, 1.):
                raw_frame = start + fraction * (end - start)
                scene_frame = row.rig.animation_data.nla_tweak_strip_time_to_scene(raw_frame)
                expected = tracks['EDIT'].strips[0].frame_start + (raw_frame - start) / session['spec']['editSpeed']
                timing.require(abs(scene_frame - expected) <= 1e-5,
                               'Native Raise Tweak key clock differs from its actual B-local frame.')
                ua._set_frame(context.scene, scene_frame)
                _set_inputs(row.rig, scope, endpoint if fraction == 1. else neutral)
                if fraction == .5:
                    timing.require(bpy.ops.transform.rotate('EXEC_DEFAULT', True, value=.073,
                        orient_axis='X', orient_type='LOCAL') == {'FINISHED'},
                        'The genuine middle native FK Raise transform did not finish.')
                _key_inputs(row.rig, scope, scene_frame)
                keys.append({'phase': fraction, 'B_frame': raw_frame, 'C_frame': scene_frame})
        middle = start + .5 * (end - start)
        curves = [curve for curve in backend._curves(session['edit_action'], session['edit_slot'])
                  if (curve.data_path, curve.array_index) in set(scope.channels)]
        timing.require(len(curves) == len(scope.channels)
            and all(any(abs(point.co[0] - middle) <= 1e-5 for point in curve.keyframe_points) for curve in curves),
            'A required native Raise FK channel lacks its B-local middle key.')
        backend.validate(context, row.rig)
        timing._assert_moving(session['edit_action'], session['edit_slot'], scope, session['spec'], backend)
        timing.require(backend.commit(context, row.rig), 'The genuine NEW Raise did not commit its own native Custom.')
        timing.require(backend._motion_hash(row.custom_action, row.custom_slot) != before,
                       'The native Raise keys did not change the genuine NEW Custom.')
    raw_end = timing._isolated_samples(context, row, [backend.item_spec(row)['sampleEnd']], modules)[0]
    error = timing._max_error(raw_end['pose'], held_sample['pose'], held_names)
    timing.require(error <= 2e-4, 'The independently evaluated raw Raise endpoint does not meet the collected Loop phase.')
    return {'native_FK_transform_and_keys': True, 'control': name, 'keys': keys,
        'endpoint_input_source': 'Actual collected Loop FK inputs at its own phase; no output matrix authoring.',
        'following_Hold_local_seconds': held_seconds, 'raw_endpoint_native_error': error,
        'pose_art_approval_claimed': False, 'native_upper_count': len(held_names)}


def run(context, config):
    """Register genuine NEW Raise, author native FK keys, restore prior binding."""
    import bpy
    config = validate_config(config)
    directory = Path(config['evidenceDirectory']).resolve()
    timing.require(directory.is_dir(), 'Create the dedicated isolated Raise evidence directory first.')
    path = directory / 'composition_Raise_authoring_report.json'
    timing.require(path.is_relative_to(directory) and len(str(path)) < 260,
                   'Keep Raise evidence in its dedicated short path.')
    modules = timing._modules()
    backend, worklist = modules['animation_composition'], modules['animation_worklist']
    report = {'schema': REPORT_SCHEMA, 'complete': False, 'config': config}
    row, candidate, prior, saved = None, None, None, None
    finished = False
    phase = 'authenticate_real_collected_Loop_and_prepared_SOURCE_Raise'
    try:
        held = timing._row(context, config['collectedHoldLoopWorkItemId'], modules, config['expectedModelSha256'])
        template = timing._row(context, config['preparedRaiseWorkItemId'], modules, config['expectedModelSha256'])
        hs, rs = backend.item_spec(held), backend.item_spec(template)
        timing._sealed_clocks(hs, rs, hs)
        timing.require(not held.new_animation and not template.new_animation and not rs['editNewActionId']
            and uuid.UUID(rs['holdWorkItemId']) == uuid.UUID(held.work_item_id)
            and rs['holdNewActionId'] == hs['editNewActionId'] and held.rig is template.rig,
            'Raise must be an actual prepared SOURCE template naming this genuine collected SOURCE Loop.')
        report['collected_Hold_proof'] = timing._published_hold(context, held, modules, config)
        saved, rig = worklist.state(context), template.rig
        prior = backend._prior(context, rig)
        prior_state = (saved.active_index, saved.status, saved.has_error)
        prior_sides = {item.item_id: item.side for item in saved.items}
        prior_workspace = (saved.workspace_path, saved.workspace_identity, saved.model_file, saved.model_sha256)
        protected = [(action, slot, backend._motion_hash(action, slot)) for item in saved.items
            for action, slot in ((item.custom_action, item.custom_slot), (item.source_action, item.source_slot)) if action]
        packets = [(item, backend._packet_for_item(item)['_sha256']) for item in saved.items if backend.item_spec(item)]
        phase = 'register_genuine_local_NEW_Raise_from_native_prepared_template'
        worklist.activate(context, template.item_id, 'CUSTOM')
        candidate = template.custom_action.copy()
        candidate.name = 'Raise · Local Edit'
        worklist._clean_action(candidate)
        slot = worklist._slot(candidate, template.custom_slot)
        rig.animation_data.action, rig.animation_data.action_slot = candidate, slot
        row = backend.register_b(context, template.item_id)
        new_spec = backend.item_spec(row)
        timing.require(row.new_animation and row.custom_action is candidate and row.custom_slot == slot.handle
            and row.work_item_id != template.work_item_id and row.new_action_id
            and uuid.UUID(new_spec['holdWorkItemId']) == uuid.UUID(held.work_item_id)
            and backend._packet_for_item(row)['_sha256'] == backend._packet_for_item(template)['_sha256'],
            'Official registration did not create a separate actual NEW Raise with the exact sealed native template.')
        created = backend._host('animation_worklist_new').load(row.manifest_path)
        report['actual_NEW_identity'] = _created_identity(row, new_spec, created)
        held_seconds = hs['sampleStart'] + (hs['editPhase'] % 1.) * (hs['sampleEnd'] - hs['sampleStart'])
        phase = 'author_actual_scoped_native_FK_Raise'
        report['authoring'] = _author(context, row, held, held_seconds, modules, config['rotationControl'])
        phase = 'measure_genuine_NEW_Raise_foreground_numeric_proof'
        report['numeric_proof'] = timing.measure_registered_raise(context,
            work_item_id=row.work_item_id, model_sha256=config['expectedModelSha256'])
        timing.require(all(backend._motion_hash(action, handle) == old for action, handle, old in protected)
            and all(backend._packet_for_item(item)['_sha256'] == old for item, old in packets)
            and prior_workspace == (saved.workspace_path, saved.workspace_identity, saved.model_file, saved.model_sha256),
            'Raise creation changed a protected prior Custom, Source, sealed packet or workspace.')
        report.update(protected_Customs_Sources_packets_unchanged=True,
                      genuine_official_NewAction_registration=True,
                      worker_launch_performed=False, publication_performed=False)
        finished = True
        return report
    except Exception:
        report['failure_phase'], report['traceback'] = phase, traceback.format_exc()
        raise
    finally:
        try:
            if prior is not None:
                rig = saved.rig
                if backend.active(rig):
                    backend.exit(context, rig, writeback=False)
                backend._restore_prior(context, rig, prior)
                for item in saved.items:
                    if item.item_id in prior_sides:
                        item.side = prior_sides[item.item_id]
                saved.active_index, saved.status, saved.has_error = prior_state
                context.view_layer.update()
                timing.require(backend._prior(context, rig) == prior,
                               'Raise authoring did not restore the exact prior native binding/pose/mode/NLA.')
                report['prior_state_restored'] = True
            if candidate is not None and row is None:
                candidate.use_fake_user = False
                if candidate.users == 0:
                    bpy.data.actions.remove(candidate)
            report['complete'] = finished
        except Exception:
            report['complete'] = False
            report['failure_phase'], report['traceback'] = 'restore_prior_native_state', traceback.format_exc()
            raise
        finally:
            timing._write(path, report)
