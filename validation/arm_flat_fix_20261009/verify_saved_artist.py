"""Read a saved artist file and exercise its repaired preset in isolation.

Run with Blender --background --factory-startup --disable-autoexec --threads 2
--python-exit-code 1 --python <this file>. This script never saves any .blend.
The only output is its JSON verification receipt beside the script.
"""
import ast
import hashlib
import importlib.util
import json
import math
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

BASE = Path(__file__).resolve().parent
ARTIST = BASE.parent.parent / 'X.blend'
CHECKPOINT = BASE / 'X_before_arm_flat_fix.blend'
SOURCE = BASE / 'approved_07711'
REPORT_PATH = BASE / 'saved_artist_verified_07711.json'
VERSION = (0, 77, 11)
RAW_TOLERANCE = 2e-5
report = {'schema': 1, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
          'script': str(Path(__file__).resolve()), 'artist': str(ARTIST),
          'checkpoint': str(CHECKPOINT), 'source': str(SOURCE), 'passed': False,
          'blend_save_performed': False, 'cases': [], 'limitations': [
              'Saved disk contents and disposable native evaluation are verified; no live UI is controlled.',
              'All pose application and control resetting take place only in this background process.',
              'Posterior bending is measured in the established Cosha armature-local +Y convention.',
          ]}
rig = None
before_files = {}


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_report():
    REPORT_PATH.write_text(json.dumps(proof.plain(report) if 'proof' in globals() else report,
                                      ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def require(condition, message):
    if not condition:
        report['last_assertion'] = message
        raise AssertionError(message)


def source_version(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == 'bl_info' for target in node.targets))
    return tuple(ast.literal_eval(assignment.value)['version'])


def load(path):
    global rig
    result = bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
    require(result == {'FINISHED'} and Path(bpy.data.filepath).resolve() == path.resolve(),
            'The intended verification .blend was not loaded.')
    rig = bpy.data.objects.get('CoshaRig')
    require(rig is not None and rig.type == 'ARMATURE', 'CoshaRig is missing.')
    proof.rig = rig
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    require(not original.active(rig), 'The saved verification scene unexpectedly contains Original mode.')
    match._update(bpy.context, rig)


def all_rest():
    return {data.name: {bone.name: {
        'matrix': proof.rows(bone.matrix_local), 'head': list(bone.head_local), 'tail': list(bone.tail_local),
        'parent': bone.parent.name if bone.parent else None, 'connected': bone.use_connect,
        'deform': bone.use_deform, 'inherit_scale': bone.inherit_scale,
        'inherit_rotation': bone.use_inherit_rotation, 'local_location': bone.use_local_location,
    } for bone in data.bones} for data in bpy.data.armatures}


def shape_key_values():
    return {mesh.name: {key.name: {'value': key.value, 'mute': key.mute,
                                 'slider_min': key.slider_min, 'slider_max': key.slider_max}
                       for key in mesh.shape_keys.key_blocks}
            for mesh in bpy.data.meshes if mesh.shape_keys}


def switch_values():
    return {pb.name: pb[match.PROPERTY] for pb in rig.pose.bones if match.PROPERTY in pb}


def protected():
    return {'all_armature_rest': proof.digest(all_rest()),
            'native_rest': proof.digest(poses.native_rest(rig)),
            'mesh_weights_shape_geometry': proof.digest(proof.mesh_state()),
            'all_actions': proof.assets_state(), 'shape_key_values': shape_key_values(),
            'pole_angles': proof.poles(rig), 'switch_values': switch_values()}


def all_raw():
    return {obj.name: proof.raw_state(obj) for obj in bpy.data.objects if obj.type == 'ARMATURE'}


def compare_unrelated(before, after, allowed, label):
    require(before.keys() == after.keys(), label + ': armature object inventory changed.')
    differences = {}
    checked = 0
    fingers = []
    for object_name, channels in before.items():
        require(channels.keys() == after[object_name].keys(), label + ': pose bone inventory changed.')
        for name, state in channels.items():
            if object_name == rig.name and name in allowed:
                continue
            checked += 1
            error = proof.raw_error(state, after[object_name][name])
            if error > RAW_TOLERANCE:
                differences[object_name + '/' + name] = error
            if object_name == rig.name and name.startswith(('f_', 'thumb.')):
                fingers.append(name)
    if differences:
        report['unrelated_channel_failure'] = {'label': label, 'differences': differences}
    require(not differences, label + ': unrelated native pose channels changed, including dormant connected channels.')
    return {'pose_bones_checked': checked, 'fingers_checked': len(fingers), 'tolerance': RAW_TOLERANCE}


def restore(raw):
    for name, fields in raw.items():
        pb = rig.pose.bones[name]
        pb.rotation_mode = fields['rotation_mode']
        for prop, value in fields.items():
            if prop not in {'rotation_mode', 'ik_fk'}:
                setattr(pb, prop, value)
        if fields['ik_fk'] is not None:
            pb[match.PROPERTY] = fields['ik_fk']
    match._update(bpy.context, rig)


def geometry(side):
    start, joint, end = [rig.pose.bones[part + '.' + side].matrix.translation.copy()
                         for part in ('upper_arm', 'forearm', 'hand')]
    chord = end - start
    require(chord.length > 1e-8, 'The shoulder and wrist became coincident.')
    axis = chord.normalized()
    radial = joint - start - axis * (joint - start).dot(axis)
    back = Vector((0., 1., 0.))
    back -= axis * back.dot(axis)
    require(radial.length > 1e-8 and back.length > 1e-8, 'A drag bend projection is degenerate.')
    return {'posterior_dot': radial.normalized().dot(back.normalized()),
            'radial_ratio': radial.length / chord.length, 'direction': list(radial.normalized())}


def clear_visible_inputs(entry):
    for field in ('target', 'pole'):
        pb = rig.pose.bones[entry[field].name]
        pb.location = (0., 0., 0.)
        pb.scale = (1., 1., 1.)
        if pb.rotation_mode == 'QUATERNION':
            pb.rotation_quaternion = (1., 0., 0., 0.)
        elif pb.rotation_mode == 'AXIS_ANGLE':
            pb.rotation_axis_angle = (0., 0., 1., 0.)
        else:
            pb.rotation_euler = (0., 0., 0.)
    match._update(bpy.context, rig)


def drag_checks(case, sides, applied_raw, saved_protection, allowed):
    for side in sides:
        entry = limb_ik._validate_inventory(rig)['rigs'][('ARM', side)]
        for clear in (False, True):
            for fraction in (.02, .15, .30):
                restore(applied_raw)
                if clear:
                    clear_visible_inputs(entry)
                start = rig.pose.bones[entry['chain'][0]].matrix.translation.copy()
                wrist = rig.pose.bones[entry['chain'][2]].matrix.translation.copy()
                target = rig.pose.bones[entry['target'].name]
                wanted = target.matrix.copy()
                wanted.translation += (start - wrist) * fraction
                target.matrix = wanted
                match._update(bpy.context, rig)
                measured = geometry(side)
                case['drag'].append({'side': side, 'clear_visible_controls': clear,
                                     'retract': fraction, **measured})
                require(measured['radial_ratio'] > .02 and measured['posterior_dot'] > .97,
                        'Saved ' + side + ' arm no longer bends backward after retraction/control reset.')
                require(proof.poles(rig) == saved_protection['pole_angles'], 'A drag changed calibrated Pole angles.')
                require(switch_values() == saved_protection['switch_values'], 'A drag changed IK/FK values.')
                require(shape_key_values() == saved_protection['shape_key_values'], 'A drag changed Shape Key values.')
                compare_unrelated({'CoshaRig': applied_raw}, {'CoshaRig': proof.raw_state(rig)},
                                  allowed, case['name'] + ' drag ' + side)
    restore(applied_raw)


def main():
    global character_designer, poses, mirror, limb_ik, match, original, proof
    require(bpy.app.background, 'Run only in a disposable background Blender process.')
    require('character_designer' not in sys.modules, 'Use factory-startup without a preloaded add-on.')
    require(ARTIST.is_file() and CHECKPOINT.is_file(), 'The saved artist file or protected checkpoint is missing.')
    before_files.update({str(path): sha256(path) for path in (ARTIST, CHECKPOINT)})
    backup = json.loads((BASE / 'backup_receipt.json').read_text(encoding='utf-8'))
    require(Path(backup['backup']).resolve() == CHECKPOINT.resolve()
            and before_files[str(CHECKPOINT)] == backup['backup_sha256'], 'The fresh artist protection copy differs.')
    receipt = json.loads((BASE / 'live_fix_receipt.json').read_text(encoding='utf-8'))
    require(tuple(receipt['runtime']) == VERSION and 'FINISHED' in receipt['saved'], 'The final live save receipt is incomplete.')
    require(Path(receipt['artist']).resolve() == ARTIST.resolve(), 'The save receipt names another artist file.')
    require(receipt['artist_sha256'] == before_files[str(ARTIST)], 'The final artist file differs from its save receipt.')
    allowed = set(receipt['allowed_pose_bones'])
    require(allowed, 'The receipt lacks its reviewed pose scope.')
    manifest = json.loads((BASE / 'release_projection.json').read_text(encoding='utf-8'))
    require(manifest['version'] == '0.77.11', 'The projection manifest is not final 0.77.11.')
    package = SOURCE / 'character_designer'
    require(source_version(package / '__init__.py') == VERSION, 'The frozen approved runtime has another version.')
    for relative, expected in manifest['files'].items():
        require(sha256(package / relative) == expected, 'Frozen approved source differs: ' + relative)
    sys.path.insert(0, str(SOURCE))
    import character_designer
    require(Path(character_designer.__file__).resolve() == (package / '__init__.py').resolve(), 'An unapproved runtime was imported.')
    character_designer.register()
    from character_designer import control_pose_assets as poses, control_pose_mirror as mirror
    from character_designer import limb_ik, limb_ik_fk as match, body_original_mode as original
    spec = importlib.util.spec_from_file_location('saved_artist_protection_helpers',
        str(BASE.parent / 'arm_flat_mirror_20261008' / 'isolated_character_validation.py'))
    proof = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(proof)
    proof.poses, proof.match, proof.limb_ik = poses, match, limb_ik
    report['runtime'] = {'blender': bpy.app.version_string, 'addon_version': character_designer.bl_info['version'],
                         'module': str(package), 'projection_sha256': sha256(BASE / 'release_projection.json')}
    load(CHECKPOINT)
    before_protection, before_raw = protected(), all_raw()
    old_metadata = poses.asset_metadata(bpy.data.actions['Arm Flat'])
    load(ARTIST)
    saved_protection, saved_raw = protected(), all_raw()
    asset = bpy.data.actions['Arm Flat']
    metadata = poses.asset_metadata(asset)
    reference = json.loads((BASE / 'stable_ik_seed.json').read_text(encoding='utf-8'))
    require(metadata.get('stable_ik_bend') is True, 'Saved Arm Flat lacks explicit stable IK opt-in.')
    require(metadata.get('stable_ik_seed') == reference and set(reference) == {'ARM/L', 'ARM/R'},
            'Saved Arm Flat does not contain the verified two-sided reference seed.')
    inventory = limb_ik._validate_inventory(rig)
    seed_count = 0
    for side in 'LR':
        entry = inventory['rigs'][('ARM', side)]
        require(match.mode_for_rig(rig, entry) == 'IK', 'Both saved arm modes must remain IK.')
        require(set(reference['ARM/' + side]) == set(entry['chain']), 'Saved reference source names differ.')
        for name, state in reference['ARM/' + side].items():
            require(rig.pose.bones[name].rotation_mode == state['rotation_mode']
                    and poses._difference(rig.pose.bones[name].matrix_basis, Matrix(state['matrix_basis'])) <= 2e-6,
                    'The saved native source does not match its healthy reference: ' + name)
            seed_count += 1
    require(seed_count == 6, 'The saved asset must contain six arm source seeds.')
    stripped = {key: value for key, value in metadata.items() if key not in {'stable_ik_bend', 'stable_ik_seed'}}
    stripped_before = {key: value for key, value in old_metadata.items() if key not in {'stable_ik_bend', 'stable_ik_seed'}}
    require(stripped == stripped_before, 'An unrelated Arm Flat metadata field changed.')
    actions_normalized = saved_protection['all_actions'].copy()
    # Only the verified metadata additions are permitted; all other Action
    # properties, curves, slots and asset information remain exact.
    actions_normalized['Arm Flat'] = dict(actions_normalized['Arm Flat'])
    actions_normalized['Arm Flat']['properties'] = dict(actions_normalized['Arm Flat']['properties'])
    actions_normalized['Arm Flat']['properties'][poses.ASSET_METADATA] = (
        before_protection['all_actions']['Arm Flat']['properties'][poses.ASSET_METADATA])
    require(actions_normalized == before_protection['all_actions'], 'Protected Action content or FCurves changed.')
    for key in ('all_armature_rest', 'native_rest', 'mesh_weights_shape_geometry',
                'shape_key_values', 'pole_angles', 'switch_values'):
        require(saved_protection[key] == before_protection[key], 'Saved protected content changed: ' + key)
    report['saved_state_comparison'] = compare_unrelated(before_raw, saved_raw, allowed, 'Saved artist versus fresh checkpoint')
    report['saved_state_comparison'].update(verified_reference_sources=seed_count,
        rest_mesh_weights_shape_key_geometry_and_all_action_curves_preserved=True,
        allowed_metadata_changes=['stable_ik_bend', 'stable_ik_seed'])
    limb_ik._mode_set(bpy.context, rig, 'POSE')
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    initial = proof.raw_state(rig)
    for name, flipped, atomic, sides in (
        ('saved_current_pose', False, False, 'LR'),
        ('normal_reapply', False, False, 'L'),
        ('mirrored_reapply', True, False, 'R'),
        ('both_arms_atomic_reapply', False, True, 'LR'),
    ):
        restore(initial)
        case = {'name': name, 'passed': False, 'drag': []}
        report['cases'].append(case)
        raw_before = all_raw()
        if name != 'saved_current_pose':
            values = poses.channels(asset, rig)
            authored = mirror.mirrored_channels(rig, values, metadata=metadata) if flipped else values
            if atomic:
                authored = dict(values)
                authored.update(mirror.mirrored_channels(rig, values, metadata=metadata))
            case['apply'] = poses.apply_channels(bpy.context, rig, authored, metadata=metadata)
            match._update(bpy.context, rig)
        case['unrelated_pose_comparison'] = compare_unrelated(raw_before, all_raw(), allowed, name)
        require(protected() == saved_protection, name + ': a reapplication changed protected data.')
        applied = proof.raw_state(rig)
        drag_checks(case, sides, applied, saved_protection, allowed)
        require(protected() == saved_protection, name + ': drag verification changed protected data.')
        case['passed'] = True
        print('ARM_FLAT_SAVED_CASE_PASS', name, len(case['drag']), flush=True)
        write_report()
    restore(initial)
    require({str(path): sha256(path) for path in (ARTIST, CHECKPOINT)} == before_files,
            'A protected .blend changed during isolated verification.')
    report['drag_checks_passed'] = sum(len(case['drag']) for case in report['cases'])
    report['passed'] = True
    print('ARM_FLAT_SAVED_ARTIST_PASS', report['drag_checks_passed'], flush=True)


try:
    main()
except Exception:
    report['error'] = traceback.format_exc()
    raise
finally:
    report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    report['files_unchanged'] = {str(path): sha256(path) == expected for path, expected in before_files.items()}
    if not all(report['files_unchanged'].values()):
        report['passed'] = False
    write_report()
