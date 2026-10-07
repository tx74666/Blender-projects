"""Three real Cosha mirror cases on the protected copy; never save a .blend.

Run in a fresh process with --background --factory-startup --disable-autoexec
--threads 2 --python-exit-code 1 --python <this file>.
POSE_APPROVED_SOURCE_ROOT must point to the frozen 0.77.3 addons directory.
POSE_CHARACTER_REPORT_PATH optionally chooses the JSON receipt; the default
is a new timestamped receipt beside this script. POSE_BASELINE_SOURCE_ROOT
optionally supplies frozen 0.77.2 for its read-only old mirror comparison.
"""
import ast
from array import array
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import sys
import time
import traceback
from datetime import datetime, timezone

import bpy
from mathutils import Matrix, Quaternion, Vector

FOLDER = Path(__file__).resolve().parent
CHECKPOINT = FOLDER / 'X_before_arm_flat_mirror_repair.blend'
CHECKPOINT_SHA256 = 'a6a5a6bb25223bf391c96a9cd482312ac8e6b929546bcc759df9a8648644db05'
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
SOURCE_ENV = os.environ.get('POSE_APPROVED_SOURCE_ROOT')
SOURCE_ROOT = Path(SOURCE_ENV).resolve() if SOURCE_ENV else None
BASELINE_ENV = os.environ.get('POSE_BASELINE_SOURCE_ROOT')
BASELINE_ROOT = Path(BASELINE_ENV).resolve() if BASELINE_ENV else None
START = datetime.now(timezone.utc)
REPORT_PATH = Path(os.environ.get('POSE_CHARACTER_REPORT_PATH', str(
    FOLDER / ('isolated_character_' + START.strftime('%Y%m%d_%H%M%S_%f') + '.json')))).resolve()
LEFT = ('shoulder.L', 'upper_arm.L', 'forearm.L', 'hand.L')
RIGHT = ('shoulder.R', 'upper_arm.R', 'forearm.R', 'hand.R')
REFLECTION = Matrix.Diagonal((-1., 1., 1., 1.))
MATRIX_TOLERANCE = 4e-4
SKIN_TOLERANCE = 6e-4
RAW_TOLERANCE = 2e-5
report = {'schema': 1, 'started_at_utc': START.isoformat(), 'passed': False,
          'script': str(Path(__file__).resolve()), 'pid': os.getpid(),
          'checkpoint': str(CHECKPOINT), 'checkpoint_expected_sha256': CHECKPOINT_SHA256,
          'approved_source_root': str(SOURCE_ROOT) if SOURCE_ROOT else None,
          'report': str(REPORT_PATH), 'cases': [], 'limitations': [
              'Only an isolated artist checkpoint is loaded; no artist save or UI interaction.',
              'Oracle uses native channel evaluation on a disposable unconstrained armature, '
              'then reflects parent-relative evaluated skin increments.',
              'Third case uses a read-only hand-channel subset of Arm Flat to isolate an '
              'unselected source-side parent; it does not alter the saved asset region.',
              'Raw preservation permits float32 matching noise up to 2e-5; exact changes '
              'are also recorded. Finger evaluated motion from its parent is expected.',
          ]}
rig = None
current_case = None
initial_hashes = {}


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def plain(value):
    if isinstance(value, bpy.types.ID):
        return {'type': type(value).__name__, 'name': value.name}
    if hasattr(value, 'to_dict'):
        return {key: plain(item) for key, item in value.to_dict().items()}
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(plain(item) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else repr(value)
    try:
        return [plain(item) for item in value]
    except TypeError:
        return repr(value)


def digest(value):
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True,
                                     allow_nan=False).encode('utf-8')).hexdigest()


def rows(matrix):
    return [list(row) for row in matrix]


def matrix_error(left, right):
    return max(abs(a - b) for x, y in zip(left, right) for a, b in zip(x, y))


def angle_degrees(left, right):
    delta = left.to_quaternion().normalized().rotation_difference(right.to_quaternion().normalized())
    return math.degrees(2. * math.atan2(Vector((delta.x, delta.y, delta.z)).length, abs(delta.w)))


def update(armature):
    armature.update_tag(refresh={'OBJECT', 'DATA', 'TIME'})
    bpy.context.view_layer.update()


def evaluated(armature):
    update(armature)
    obj = armature.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return {bone.name: bone.matrix.copy() for bone in obj.pose.bones}


def raw_state(armature):
    names = ('location', 'rotation_mode', 'rotation_euler', 'rotation_quaternion',
             'rotation_axis_angle', 'scale', *poses._BBONE)
    return {bone.name: {name: plain(getattr(bone, name)) for name in names}
            | {'ik_fk': bone.get(match.PROPERTY)} for bone in armature.pose.bones}


def raw_error(left, right):
    if isinstance(left, dict) and isinstance(right, dict):
        if left.keys() != right.keys():
            return math.inf
        return max((raw_error(left[key], right[key]) for key in left), default=0.)
    if isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)):
        return max((raw_error(a, b) for a, b in zip(left, right)), default=0.) if len(left) == len(right) else math.inf
    if isinstance(left, (float, int)) and isinstance(right, (float, int)):
        return abs(left - right)
    return 0. if left == right else math.inf


def poles(armature):
    return {bone.name + '/' + constraint.name: constraint.pole_angle
            for bone in armature.pose.bones for constraint in bone.constraints
            if constraint.type == 'IK'}


def modes(armature):
    inventory = limb_ik._validate_inventory(armature)
    return {'/'.join(key): {'mode': match.mode_for_rig(armature, entry),
                           'value': armature.pose.bones[entry['target'].name].get(match.PROPERTY)}
            for key, entry in inventory['rigs'].items()}


def curves(action):
    return [{'slot': bag.slot_handle, 'path': curve.data_path, 'index': curve.array_index,
             'mute': curve.mute, 'extrapolation': curve.extrapolation,
             'keys': [(tuple(point.co), tuple(point.handle_left), tuple(point.handle_right),
                       point.interpolation, point.easing, point.handle_left_type,
                       point.handle_right_type, point.type, point.amplitude, point.back, point.period)
                      for point in curve.keyframe_points],
             'samples': [tuple(point.co) for point in curve.sampled_points]}
            for layer in action.layers for strip in layer.strips for bag in strip.channelbags
            for curve in bag.fcurves]


def assets_state():
    return {action.name: {'properties': {key: plain(action[key]) for key in action.keys()},
                         'slots': [slot.identifier for slot in action.slots],
                         'fake_user': action.use_fake_user, 'curves': curves(action),
                         'asset': None if action.asset_data is None else {
                             'catalog': action.asset_data.catalog_id,
                             'description': action.asset_data.description,
                             'author': action.asset_data.author,
                             'tags': [tag.name for tag in action.asset_data.tags]}}
            for action in bpy.data.actions}


def coordinate_digest(data):
    values = array('f', [0.]) * (len(data) * 3)
    data.foreach_get('co', values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def mesh_state():
    result = {}
    for mesh in bpy.data.meshes:
        weights = hashlib.sha256()
        for vertex in mesh.vertices:
            for group in vertex.groups:
                weights.update(struct.pack('<IIf', vertex.index, group.group, group.weight))
        result[mesh.name] = {
            'vertices': len(mesh.vertices), 'edges': len(mesh.edges), 'faces': len(mesh.polygons),
            'coordinates': coordinate_digest(mesh.vertices), 'weights': weights.hexdigest(),
            'shape_keys': [] if mesh.shape_keys is None else [
                {'name': key.name, 'relative': key.relative_key.name if key.relative_key else None,
                 'interpolation': key.interpolation, 'coordinates': coordinate_digest(key.data)}
                for key in mesh.shape_keys.key_blocks]}
    return {'data': result, 'groups': {obj.name: [(group.index, group.name) for group in obj.vertex_groups]
                                    for obj in bpy.data.objects if obj.type == 'MESH'}}


def protected_state(armature):
    return {'native_rest': digest(poses.native_rest(armature)),
            'all_rest': digest({bone.name: {'matrix': rows(bone.matrix_local),
                                           'parent': bone.parent.name if bone.parent else None,
                                           'connected': bone.use_connect}
                                for bone in armature.data.bones}),
            'meshes_vertices_weights_shape_keys': digest(mesh_state()),
            'assets_fcurves': digest(assets_state())}


def write_report():
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(plain(report), ensure_ascii=False, indent=2,
                                     allow_nan=False), encoding='utf-8')


def diagnostic():
    result = {'loaded_file': bpy.data.filepath, 'context_mode': bpy.context.mode}
    if rig is not None and bpy.data.objects.get(rig.name) is rig:
        try:
            result.update({'raw': raw_state(rig), 'poles': poles(rig), 'modes': modes(rig),
                           'evaluated': {name: rows(value) for name, value in evaluated(rig).items()}})
        except Exception as exc:
            result['diagnostic_error'] = repr(exc)
    return result


def require(condition, message):
    if not condition:
        report['last_assertion'] = message
        if current_case is not None:
            current_case['failure_diagnostic'] = diagnostic()
        else:
            report['failure_diagnostic'] = diagnostic()
        write_report()
        raise AssertionError(message)


def addon_version(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    node = next(item for item in tree.body if isinstance(item, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'bl_info' for target in item.targets))
    return tuple(ast.literal_eval(node.value)['version'])


def preflight():
    global character_designer, poses, mirror, limb_ik, match, original
    require(bpy.app.background, 'Run this script only in a disposable background Blender process.')
    require(SOURCE_ROOT is not None, 'POSE_APPROVED_SOURCE_ROOT must identify frozen 0.77.3.')
    canonical = SOURCE_ROOT / 'character_designer' / '__init__.py'
    require(canonical.is_file() and addon_version(canonical) == (0, 77, 3), 'Approved source is not frozen 0.77.3.')
    require(CHECKPOINT.is_file() and sha256(CHECKPOINT) == CHECKPOINT_SHA256, 'Protected checkpoint hash differs.')
    require(CHECKPOINT.resolve() != ARTIST.resolve(), 'The test must not load the artist file.')
    initial_hashes.update(checkpoint=sha256(CHECKPOINT), artist=sha256(ARTIST) if ARTIST.exists() else None)
    require('character_designer' not in sys.modules, 'Use a fresh factory-startup process without a preloaded add-on.')
    sys.path.insert(0, str(SOURCE_ROOT))
    import character_designer
    require(Path(character_designer.__file__).resolve() == canonical.resolve(), 'Unexpected add-on import location.')
    require(tuple(character_designer.bl_info['version']) == (0, 77, 3), 'Unexpected runtime version.')
    character_designer.register()
    from character_designer import control_pose_assets as poses, control_pose_mirror as mirror
    from character_designer import limb_ik, limb_ik_fk as match, body_original_mode as original
    report['runtime'] = {'blender': bpy.app.version_string, 'addon_version': character_designer.bl_info['version'],
                         'registration_count': 1,
                         'source_files': {name: {'path': str(SOURCE_ROOT / 'character_designer' / name),
                                                'sha256': sha256(SOURCE_ROOT / 'character_designer' / name)}
                                          for name in ('__init__.py', 'control_pose_assets.py', 'control_pose_mirror.py')}}
    write_report()


def load_case(mode):
    global rig
    rig = None
    require(sha256(CHECKPOINT) == CHECKPOINT_SHA256, 'Checkpoint changed before reload.')
    result = bpy.ops.wm.open_mainfile(filepath=str(CHECKPOINT), load_ui=False, use_scripts=False)
    require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == CHECKPOINT.resolve(), 'Protected copy was not loaded.')
    rig = bpy.data.objects.get('CoshaRig')
    require(rig is not None and rig.type == 'ARMATURE', 'CoshaRig is missing.')
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    limb_ik._mode_set(bpy.context, rig, 'POSE')
    require(not original.active(rig), 'The checkpoint unexpectedly contains an Original session.')
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    bpy.context.scene.render.threads_mode = 'FIXED'
    bpy.context.scene.render.threads = 2
    asset = bpy.data.actions.get('Arm Flat')
    require(asset is not None and asset.asset_data is not None, 'Existing Arm Flat asset is missing.')
    metadata = poses.asset_metadata(asset)
    values = poses.channels(asset, rig)
    require(metadata is not None and set(values) == set(LEFT), 'Arm Flat has an unexpected authoring region.')
    protected = protected_state(rig)
    pole_before = poles(rig)
    switch = match.switch_limb(bpy.context, rig, ('ARM', 'R'), mode, keyframe=False, sync_display=False)
    require(poles(rig) == pole_before, 'Mode preparation changed Pole Angle.')
    current_case.update({'loaded_file': bpy.data.filepath, 'frame': bpy.context.scene.frame_current,
                         'render_threads': bpy.context.scene.render.threads,
                         'asset': asset.name, 'source_names': metadata['names'],
                         'asset_curve_count': len(curves(asset)), 'mode_setup': switch,
                         'protected_initial': protected, 'poles_loaded': pole_before})
    return asset, metadata, values, protected


def native_reference(values):
    """Independent FK evaluation, without production mirror/desired_pose calls."""
    reference = rig.copy()
    reference.data = rig.data.copy()
    bpy.context.scene.collection.objects.link(reference)
    reference.select_set(False)
    reference.animation_data_clear()
    reference.data.animation_data_clear()
    for bone in reference.pose.bones:
        for constraint in list(bone.constraints):
            bone.constraints.remove(constraint)
        bone.rotation_mode = 'QUATERNION'
        bone.matrix_basis = Matrix.Identity(4)
    for name, fields in values.items():
        bone = reference.pose.bones[name]
        require(set(fields['rotation_quaternion']) == {0, 1, 2, 3}, 'Actual Arm Flat oracle needs complete quaternion capture.')
        bone.location = [fields['location'][index] for index in range(3)]
        bone.rotation_quaternion = [fields['rotation_quaternion'][index] for index in range(4)]
        bone.scale = [fields['scale'][index] for index in range(3)]
    return reference


def remove_reference(reference):
    data = reference.data
    bpy.data.objects.remove(reference, do_unlink=True)
    bpy.data.armatures.remove(data)


def skin_oracle(values, before):
    reference = native_reference(values)
    try:
        actual_source = evaluated(reference)
        source_skin = {name: pose @ reference.data.bones[name].matrix_local.inverted()
                       for name, pose in actual_source.items()}
        increments = {}
        for name in values:
            parent = reference.data.bones[name].parent
            parent_skin = source_skin[parent.name] if parent else Matrix.Identity(4)
            increments[bpy.utils.flip_name(name)] = parent_skin.inverted() @ source_skin[name]
        wanted_pose = {name: before[name].copy() for name in RIGHT}
        wanted_skin = {name: before[name] @ rig.data.bones[name].matrix_local.inverted() for name in RIGHT}
        for name in sorted(increments, key=lambda item: len(rig.pose.bones[item].parent_recursive)):
            parent = rig.data.bones[name].parent
            if parent is None:
                parent_skin = Matrix.Identity(4)
            elif parent.name in increments:
                parent_skin = wanted_skin[parent.name]
            else:
                parent_skin = before[parent.name] @ parent.matrix_local.inverted()
            wanted_skin[name] = parent_skin @ REFLECTION @ increments[name] @ REFLECTION
            wanted_pose[name] = wanted_skin[name] @ rig.data.bones[name].matrix_local
        current_case['oracle'] = {'method': 'unconstrained native source evaluation; parent-relative skin reflection',
                                  'source_increments': {name: rows(value) for name, value in increments.items()},
                                  'expected_pose': {name: rows(value) for name, value in wanted_pose.items()},
                                  'expected_skin': {name: rows(value) for name, value in wanted_skin.items()}}
        return wanted_pose, wanted_skin, increments
    finally:
        remove_reference(reference)


def old_comparison(asset, metadata, values):
    candidate = sys.modules['character_designer.control_pose_mirror']
    alias = 'character_designer._isolated_mirror_baseline_0772'
    if BASELINE_ROOT is not None:
        init = BASELINE_ROOT / 'character_designer' / '__init__.py'
        path = init.parent / 'control_pose_mirror.py'
        require(init.is_file() and addon_version(init) == (0, 77, 2) and path.is_file(), 'Baseline source is not frozen 0.77.2.')
        spec = importlib.util.spec_from_file_location(alias, path)
        old = importlib.util.module_from_spec(spec)
        sys.modules[alias] = old
        try:
            spec.loader.exec_module(old)
            result = old.mirrored_channels(rig, values, metadata=metadata)
            method = {'method': 'frozen 0.77.2 mirror module with candidate compatibility reader',
                      'module': str(path), 'sha256': sha256(path)}
        finally:
            sys.modules.pop(alias, None)
    else:
        reference = native_reference(values)
        copied_action = None
        try:
            copied_action = asset.copy()
            del copied_action[poses.ASSET_METADATA]
            copied_action.flip_with_pose(reference)
            result = poses.channels(copied_action, rig)
            method = {'method': 'Blender native full-channel Action flip, old managed mirror intermediary',
                      'baseline_module_loaded': False}
        finally:
            if copied_action is not None:
                bpy.data.actions.remove(copied_action)
            remove_reference(reference)
    require(sys.modules['character_designer.control_pose_mirror'] is candidate, 'Candidate module changed during old comparison.')
    angles = {name: angle_degrees(Quaternion([result[name]['rotation_quaternion'][index]
                                            for index in range(4)]).to_matrix().to_4x4(), Matrix.Identity(4))
              for name in RIGHT}
    current_case['old_comparison'] = method | {'local_quaternion_angles_degrees': angles,
                                               'candidate_module_preserved': True}
    require(angles['forearm.R'] > 170. and angles['hand.R'] > 170., 'Old-path 180-degree contrast was not reproduced.')


def entry_bones(entry):
    names = set()
    def visit(value):
        if isinstance(value, (bpy.types.Bone, bpy.types.PoseBone)):
            names.add(value.name)
        elif isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif isinstance(value, (tuple, list, set)):
            for item in value:
                visit(item)
        elif isinstance(value, str) and value in rig.pose.bones:
            names.add(value)
    visit(entry)
    return names


def run_case(name, mode, *, hand_only=False, contrast=False):
    global current_case
    current_case = {'name': name, 'requested_mode': mode, 'passed': False}
    report['cases'].append(current_case)
    began = time.perf_counter()
    try:
        asset, metadata, values, protected = load_case(mode)
        if hand_only:
            match.switch_limb(bpy.context, rig, ('ARM', 'L'), 'FK', keyframe=False, sync_display=False)
            source_before = evaluated(rig)['forearm.L']
            rig.pose.bones['forearm.L'].matrix_basis = (rig.pose.bones['forearm.L'].matrix_basis
                                                        @ Matrix.Rotation(.37, 4, 'X'))
            rig.pose.bones['hand.L'].matrix_basis = (rig.pose.bones['hand.L'].matrix_basis
                                                     @ Matrix.Rotation(.28, 4, 'Y'))
            changed_source = evaluated(rig)
            disturbance = matrix_error(source_before, changed_source['forearm.L'])
            current_case['source_parent_disturbance'] = {'unselected_parent': 'forearm.L',
                                                        'max_matrix_change': disturbance}
            require(disturbance > 1e-3, 'Source parent disturbance was ineffective.')
            values = {'hand.L': values['hand.L']}
        before = evaluated(rig)
        raw_before, modes_before, poles_before = raw_state(rig), modes(rig), poles(rig)
        wanted_pose, wanted_skin, increments = skin_oracle(values, before)
        if hand_only:
            source_parent_skin = before['forearm.L'] @ rig.data.bones['forearm.L'].matrix_local.inverted()
            source_hand_skin = before['hand.L'] @ rig.data.bones['hand.L'].matrix_local.inverted()
            current_increment = source_parent_skin.inverted() @ source_hand_skin
            hand_difference = matrix_error(current_increment, increments['hand.R'])
            target_parent_skin = before['forearm.R'] @ rig.data.bones['forearm.R'].matrix_local.inverted()
            parent_difference = matrix_error(REFLECTION @ source_parent_skin @ REFLECTION, target_parent_skin)
            current_case['source_parent_disturbance'].update({
                'current_hand_increment_vs_saved': hand_difference,
                'reflected_source_parent_vs_target_parent': parent_difference})
            require(hand_difference > 1e-3 and parent_difference > 1e-3,
                    'Current source parent/hand did not differ from the stored gesture and target parent.')
        if contrast:
            old_comparison(asset, metadata, values)
        mirrored = mirror.mirrored_channels(rig, values, metadata=metadata)
        current_case['mirrored_channels'] = mirrored
        require(raw_state(rig) == raw_before, 'Mirror conversion changed character channels before apply.')
        require(protected_state(rig) == protected, 'Oracle or mirror conversion changed protected data.')
        applied = poses.apply_channels(bpy.context, rig, mirrored, metadata=metadata)
        after, raw_after = evaluated(rig), raw_state(rig)
        errors = {bone: {'pose_matrix': matrix_error(after[bone], wanted_pose[bone]),
                         'skin_matrix': matrix_error(after[bone] @ rig.data.bones[bone].matrix_local.inverted(), wanted_skin[bone]),
                         'rotation_degrees': angle_degrees(after[bone], wanted_pose[bone]),
                         'position_m': (after[bone].translation - wanted_pose[bone].translation).length}
                  for bone in RIGHT}
        raw_errors = {bone: raw_error(raw_before[bone], raw_after[bone]) for bone in raw_before}
        exact_changed = [bone for bone in raw_before if raw_before[bone] != raw_after[bone]]
        meaningful_changed = [bone for bone, error in raw_errors.items() if error > RAW_TOLERANCE]
        finger_names = [bone for bone in raw_before if bone.startswith(('f_', 'thumb.'))]
        right_entry = limb_ik._validate_inventory(rig)['rigs'][('ARM', 'R')]
        allowed_raw = entry_bones(right_entry) | set(RIGHT)
        native = poses.native_rest(rig)
        descendants = set(RIGHT)
        for bone in RIGHT:
            descendants.update(child.name for child in rig.data.bones[bone].children_recursive)
        unexpected_eval = {bone: matrix_error(before[bone], after[bone]) for bone in native
                           if bone not in descendants and matrix_error(before[bone], after[bone]) > MATRIX_TOLERANCE}
        protected_after = protected_state(rig)
        current_case.update({'apply': applied, 'bone_errors': errors,
                             'max_pose_matrix_error': max(value['pose_matrix'] for value in errors.values()),
                             'max_skin_matrix_error': max(value['skin_matrix'] for value in errors.values()),
                             'max_rotation_error_degrees': max(value['rotation_degrees'] for value in errors.values()),
                             'matrix_tolerance': MATRIX_TOLERANCE, 'skin_tolerance': SKIN_TOLERANCE,
                             'modes_before': modes_before, 'modes_after': modes(rig),
                             'poles_before': poles_before, 'poles_after': poles(rig),
                             'raw_exact_changed': exact_changed, 'raw_meaningful_changed': meaningful_changed,
                             'raw_largest_errors': dict(sorted(raw_errors.items(), key=lambda item: item[1], reverse=True)[:24]),
                             'raw_allowed_names': sorted(allowed_raw),
                             'finger_raw_exact_changed': [bone for bone in finger_names if bone in exact_changed],
                             'finger_raw_checked': len(finger_names),
                             'finger_raw_max_error': max((raw_errors[bone] for bone in finger_names), default=0.),
                             'raw_preservation_tolerance': RAW_TOLERANCE,
                             'unexpected_other_native_evaluated_changes': unexpected_eval,
                             'protected_final': protected_after,
                             'actual_right_pose': {bone: rows(after[bone]) for bone in RIGHT}})
        require(all(value['pose_matrix'] <= MATRIX_TOLERANCE and value['skin_matrix'] <= SKIN_TOLERANCE
                    for value in errors.values()), 'Right Arm Flat differs from the independent skin oracle.')
        require(modes(rig) == modes_before and modes(rig)['ARM/R']['mode'] == mode, 'Applying the Pose changed a current IK/FK mode.')
        require(poles(rig) == poles_before == current_case['poles_loaded'], 'Applying the Pose changed a Pole Angle.')
        require(protected_after == protected, 'Rest, mesh data, weights, shape keys or asset FCurves changed.')
        require(finger_names and current_case['finger_raw_max_error'] <= RAW_TOLERANCE,
                'Finger raw channels changed beyond numerical matching noise, or none were checked.')
        require(set(meaningful_changed) <= allowed_raw, 'Unrelated body raw channels changed.')
        require(not unexpected_eval, 'Unrelated native evaluated bones moved.')
        require(Path(bpy.data.filepath).resolve() == CHECKPOINT.resolve(), 'An unexpected artist file was loaded.')
        current_case['passed'] = True
        print('ARM_FLAT_CHARACTER_PASS', name, flush=True)
    except Exception as exc:
        current_case.update({'error': str(exc), 'error_type': type(exc).__name__,
                             'traceback': traceback.format_exc(), 'failure_diagnostic': diagnostic()})
        print('ARM_FLAT_CHARACTER_FAIL', name, type(exc).__name__, str(exc), flush=True)
        raise
    finally:
        current_case['seconds'] = round(time.perf_counter() - began, 4)
        write_report()


def main():
    try:
        preflight()
        run_case('complete_arm_flat_fk', 'FK', contrast=True)
        run_case('complete_arm_flat_ik', 'IK')
        run_case('hand_subset_unselected_source_parent', 'FK', hand_only=True)
        require(sha256(CHECKPOINT) == CHECKPOINT_SHA256, 'Protected checkpoint file changed.')
        report['passed'] = True
    except Exception as exc:
        report.update({'error': str(exc), 'error_type': type(exc).__name__, 'traceback': traceback.format_exc()})
        raise
    finally:
        report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        report['blend_save_performed'] = False
        report['file_protection'] = {
            'checkpoint_before': initial_hashes.get('checkpoint'),
            'checkpoint_after': sha256(CHECKPOINT) if CHECKPOINT.exists() else None,
            'artist_before': initial_hashes.get('artist'),
            'artist_after': sha256(ARTIST) if ARTIST.exists() else None,
            'loaded_file_at_exit': bpy.data.filepath}
        report['file_protection']['checkpoint_unchanged'] = (
            report['file_protection']['checkpoint_after'] == CHECKPOINT_SHA256)
        report['file_protection']['artist_unchanged_during_run'] = (
            report['file_protection']['artist_before'] == report['file_protection']['artist_after'])
        if not report['file_protection']['checkpoint_unchanged']:
            report['passed'] = False
        write_report()
        print('ARM_FLAT_CHARACTER_REPORT', str(REPORT_PATH), 'PASS' if report['passed'] else 'FAIL', flush=True)


if __name__ == '__main__':
    main()
