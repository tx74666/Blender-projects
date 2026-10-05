"""Read-only initial-pose calibration from the exact stopped saved candidate.

Root schedules an isolated --background --factory-startup --disable-autoexec
process which explicitly opens the candidate before this script. This script
does not register add-ons/backends/handlers/timers, step frames, update a view
layer, apply input, alter coordinates, simulate, export or save any blend.
Only one exclusive timestamped evidence JSON is written under this directory.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time

import bpy

DIRECTORY = Path(__file__).resolve().parent
CANDIDATE = DIRECTORY / 'real_hair_preview_candidate_5_1_0_1791089528974781700.blend'
CANDIDATE_SHA = 'a7642c321e72437be30f6c6b291eaa858f7b4d45e945852ed7e03c42a5cae7d1'
HELPER = DIRECTORY / 'validate_real_hair_preview.py'
HELPER_SHA = '36495cde240e0cb49a8f49a8c1e0d3043391ae9a127c1d04214f22721dbbcc9c'
EXPECTED_RAW = 'c0a05c28207cfefb5e441686ee14b56eb5da91495bc2fe2f81a97ce9f576e4c2'
EXPECTED_UID = '331afdb7e5154ae1aaa39603a4f61768'
PREVIEW_REPORT = DIRECTORY / 'real_hair_preview_validation_51_headlocal3.json'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def vector(value):
    result = [float(item) for item in value]
    require(all(math.isfinite(item) for item in result), 'A source vector is nonfinite.')
    return result


def matrix(value):
    result = [vector(row) for row in value]
    require(len(result) == 4 and all(len(row) == 4 for row in result), 'A source matrix is not 4 by 4.')
    return result


def channels(owner, object_channels=False):
    fields = ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')
    if object_channels:
        fields += ('delta_location', 'delta_rotation_euler', 'delta_rotation_quaternion', 'delta_scale')
    return {'rotation_mode': owner.rotation_mode, **{key: vector(getattr(owner, key)) for key in fields}}


def exact_state(helper):
    """Native values only; no unset PropertyGroup pointer is dereferenced."""
    scene = bpy.context.scene
    values = {'frame': scene.frame_current, 'subframe': scene.frame_subframe,
        'autokey': scene.tool_settings.use_keyframe_insert_auto,
        'gravity': vector(scene.gravity), 'unit_scale': scene.unit_settings.scale_length,
        'fps': scene.render.fps, 'fps_base': scene.render.fps_base, 'objects': [], 'shapes': []}
    for owner in sorted(bpy.data.objects, key=lambda item: item.name_full):
        custom = helper.adapter._pose_custom(owner)[1]
        item = {'name': owner.name_full, 'channels': channels(owner, True), 'custom_numeric': custom,
            'matrix_world': matrix(owner.matrix_world), 'mode': owner.mode, 'selected': owner.select_get()}
        if owner.type == 'ARMATURE':
            item['pose'] = [{'name': bone.name, 'channels': channels(bone),
                'custom_numeric': helper.adapter._pose_custom(bone)[1],
                'matrix': matrix(bone.matrix), 'matrix_basis': matrix(bone.matrix_basis)} for bone in owner.pose.bones]
        values['objects'].append(item)
    for keys in sorted(bpy.data.shape_keys, key=lambda item: item.name_full):
        values['shapes'].append({'name': keys.name_full, 'eval_time': keys.eval_time,
            'values': [[key.name, key.value] for key in keys.key_blocks]})
    encoded = helper.encode(values, portable=True)
    raw = json.dumps(encoded, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf8')
    return hashlib.sha256(raw).hexdigest()


def pose_record(bone, rig):
    rest = bone.bone
    delta = bone.matrix @ rest.matrix_local.inverted()
    return {'name': bone.name, 'parent_name': bone.parent.name if bone.parent else None,
        'rotation_mode': bone.rotation_mode, 'local_channels': channels(bone),
        'matrix_basis': matrix(bone.matrix_basis), 'matrix_pose_armature_local': matrix(bone.matrix),
        'matrix_rest_armature_local': matrix(rest.matrix_local),
        'matrix_pose_world': matrix(rig.matrix_world @ bone.matrix),
        'head_pose_armature_local': vector(bone.head), 'tail_pose_armature_local': vector(bone.tail),
        'head_pose_world': vector(rig.matrix_world @ bone.head), 'tail_pose_world': vector(rig.matrix_world @ bone.tail),
        'head_rest_armature_local': vector(rest.head_local), 'tail_rest_armature_local': vector(rest.tail_local),
        'pose_from_rest_armature_delta': matrix(delta),
        'maximum_pose_rest_matrix_difference': max(abs(bone.matrix[row][column] - rest.matrix_local[row][column])
            for row in range(4) for column in range(4))}


def main():
    began = time.perf_counter()
    output = DIRECTORY / ('hair_source_calibration_' + str(time.time_ns()) + '.json')
    result = {'schema': 'character-designer-hair-source-calibration/1', 'ok': False,
        'blender': bpy.app.version_string, 'simulation_baked': False, 'readonly': True,
        'limitations': ['Source snapshot only; no Unity imported Rest or native physics equivalence is proven.',
            'No simulation/frame stepping/registration/export/save was performed.',
            'Matrix rows are Blender row-major; coordinates retain source armature/world spaces and source length units.']}
    try:
        require(bpy.app.background, 'Use an isolated background Blender process.')
        require(Path(bpy.data.filepath).resolve() == CANDIDATE.resolve(), 'Open the exact stopped Head-local candidate.')
        require(digest(CANDIDATE) == CANDIDATE_SHA, 'The frozen candidate file digest changed.')
        require(digest(HELPER) == HELPER_SHA, 'The fingerprint/input-proof helper is not the frozen reviewed version.')
        require(not output.exists(), 'Calibration evidence filename already exists; refusing overwrite.')
        spec = importlib.util.spec_from_file_location('_cd_readonly_source_calibration_helpers', HELPER)
        helper = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = helper
        spec.loader.exec_module(helper)
        scene = bpy.context.scene
        require(scene.frame_current == 39, 'The candidate is not at its actual saved author frame 39; do not step it.')
        source = bpy.data.objects.get('Hair')
        require(source is not None and source.type == 'MESH', 'The saved Hair source is absent.')
        require(not helper.adapter.status()['active'], 'An active preview cannot be captured as the stopped baseline.')
        before_state = exact_state(helper)
        before_raw = helper.asset_fingerprint(source)
        require(before_raw['portable_sha256'] == EXPECTED_RAW, 'The candidate raw portable asset proof differs.')
        metadata_before = {key: helper.adapter._clone(source.get(key)) for key in (
            helper.registry.REGISTRY_KEY, helper.profiles.PROFILE_KEY, helper.hair.RECORD_KEY)}
        data = helper.registry.read(source, validate=True)
        require(data['source_uid'] == EXPECTED_UID and len(data['strands']) == 32
            and sum(len(item['bones']) for item in data['strands']) == 128, 'Expected original source UID / 32 strands / 128 segments.')
        rig = source.get(helper.hair.RIG_KEY)
        require(rig is not None and rig.type == 'ARMATURE' and rig.mode != 'EDIT', 'Strict proven source armature is unavailable.')
        effective = helper.profiles.effective_all(source, registry=data)
        strategy = helper.input_strategy(rig, data)
        require(strategy['kind'] == 'unconstrained_anchor' and strategy['owner'] == strategy['anchor'],
            'The saved candidate no longer proves its actual direct Head-local input; no fallback calibration is accepted.')
        anchor = strategy['anchor']
        prior = json.loads(PREVIEW_REPORT.read_text(encoding='utf8'))
        require(prior.get('ok') is True and prior.get('source_uid') == EXPECTED_UID
            and Path(prior['recoverypath']).resolve() == CANDIDATE.resolve(), 'The passing Head-local report does not identify this candidate.')
        artist = Path(prior['artist_path']).resolve()
        require(artist != CANDIDATE.resolve() and artist.is_file(), 'The independent original artist file is unavailable for readonly hash proof.')
        artist_before = digest(artist)
        rows, ownership = [], {}
        for strand in data['strands']:
            for index, name in enumerate(strand['bones']):
                require(name not in ownership, 'Owned chains overlap native Hair bones.')
                ownership[name] = {'strand_id': strand['strand_id'], 'chain_id': strand['chain_id'], 'bone_index': index}
        for strand in data['strands']:
            for index, name in enumerate(strand['bones']):
                bone = rig.pose.bones[name]
                row = pose_record(bone, rig)
                row.update(ownership[name], strand_order=strand['order'], source_rest_proof=strand['rest'][index],
                    parent_identity=ownership.get(bone.parent.name) if bone.parent else None,
                    parent_attachment=bone.parent.name if bone.parent and bone.parent.name not in ownership else None)
                rows.append(row)
        result.update(candidate=str(CANDIDATE), candidate_sha256=CANDIDATE_SHA, artist_path=str(artist),
            artist_sha256=artist_before, helper_sha256=HELPER_SHA, source_uid=EXPECTED_UID,
            registry_topology=data['topology'], counts={'strands': 32, 'segments': len(rows)},
            scene={'name': scene.name, 'frame_current': scene.frame_current, 'frame_subframe': scene.frame_subframe,
                'fps': scene.render.fps, 'fps_base': scene.render.fps_base, 'gravity_native_scene_vector': vector(scene.gravity),
                'use_gravity': scene.use_gravity, 'source_meters_per_unit': scene.unit_settings.scale_length},
            rig={'name': rig.name, 'matrix_world': matrix(rig.matrix_world), 'matrix_basis': matrix(rig.matrix_basis),
                'local_channels': channels(rig, True), 'pose_position': rig.data.pose_position},
            input_strategy={'kind': strategy['kind'], 'owner': strategy['owner'].name, 'anchor': anchor.name,
                'axis': strategy['axis'], 'quaternion_component_order': 'wxyz', 'base_local_quaternion': vector(strategy['base']),
                'rotation_composition': 'base_local_quaternion @ local_X_pulse_quaternion',
                'trace': strategy['trace'], 'proof_diagnostics': strategy['proof_diagnostics'], 'anchor_pose': pose_record(anchor, rig)},
            strands=[{'strand_id': item['strand_id'], 'chain_id': item['chain_id'], 'order': item['order'],
                'pair_id': item['pair_id'], 'mirror_id': item['mirror_id'], 'side': item['side'], 'pair_proof': item['pair_proof'],
                'bones': item['bones'], 'anchor': item['anchor'], 'effective': effective[item['strand_id']]} for item in data['strands']],
            hair_bones=rows, raw_before=before_raw,
            maximum_hair_pose_rest_matrix_difference=max(row['maximum_pose_rest_matrix_difference'] for row in rows))
        after_raw = helper.asset_fingerprint(source)
        require(after_raw['sha256'] == before_raw['sha256'] and after_raw['portable_sha256'] == EXPECTED_RAW,
            'Readonly calibration changed raw asset data.')
        require(exact_state(helper) == before_state, 'Readonly calibration changed native pose, Shape Values, switches, selection or frame.')
        require(all(helper.adapter._clone(source.get(key)) == value for key, value in metadata_before.items()),
            'Readonly calibration changed source metadata.')
        require(digest(CANDIDATE) == CANDIDATE_SHA and digest(artist) == artist_before, 'A source blend file changed during calibration.')
        result.update(ok=True, raw_after=after_raw, exact_pose_shape_channels_frame_unchanged=True,
            exact_metadata_unchanged=True, candidate_artist_files_unchanged=True, state_sha256=before_state)
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        result['elapsed_seconds'] = time.perf_counter() - began
        with output.open('x', encoding='utf8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        print('HAIR_SOURCE_CALIBRATION', json.dumps({'ok': result['ok'], 'output': str(output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
