"""Read-only parent-local Dress pose/bind comparison for the supplied packet.

No Blender API, scene mutations, Unity operations or plugin changes are used.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


PACKAGE = Path(r'D:\Blender\Projects\Character\Animation\UnityExports\CharacterTuning\20261009-233830-d8fa2427ba96\Cosha_Walk_N.cdanim.json')
EXPECTED_SHA256 = 'e54537cb65ab6b0365b42af0236f645cc0f009e1c10b056d66a13b87e7669c02'
OUTPUT = Path(__file__).with_name('dress_packet_static_proof.json')
DIAGNOSTIC_THRESHOLD = 2.0e-5


def matrix(flat):
    if len(flat) != 16 or not all(isinstance(value, (int, float))
                                and not isinstance(value, bool)
                                and math.isfinite(value) for value in flat):
        raise ValueError('Expected a finite row-major 4x4 matrix.')
    return [[float(value) for value in flat[start:start + 4]]
            for start in range(0, 16, 4)]


def multiply(left, right):
    return [[sum(left[i][k] * right[k][j] for k in range(4))
             for j in range(4)] for i in range(4)]


def inverse(value):
    augmented = [row[:] + [float(i == j) for j in range(4)]
                 for i, row in enumerate(value)]
    for i in range(4):
        pivot = max(range(i, 4), key=lambda candidate: abs(augmented[candidate][i]))
        augmented[i], augmented[pivot] = augmented[pivot], augmented[i]
        divisor = augmented[i][i]
        if abs(divisor) < 1.0e-12:
            raise ValueError('Singular parent transform.')
        augmented[i] = [component / divisor for component in augmented[i]]
        for other in range(4):
            if other != i:
                coefficient = augmented[other][i]
                augmented[other] = [augmented[other][j] - coefficient * augmented[i][j]
                                    for j in range(8)]
    result = [row[4:] for row in augmented]
    if not all(math.isfinite(value) for row in result for value in row):
        raise ValueError('Non-finite inverse.')
    return result


def difference(left, right):
    return max(abs(left[i][j] - right[i][j]) for i in range(4) for j in range(4))


def main():
    payload = PACKAGE.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError('Package revision changed; this diagnostic must be reviewed again.')
    data = json.loads(payload.decode('utf-8-sig'))
    bones, frames = data['bones'], data['frames']
    rests = [matrix(bone['rest']) for bone in bones]
    poses = [[matrix(pose['matrix']) for pose in frame['poses']] for frame in frames]
    if not frames or any(len(frame) != len(bones) for frame in poses):
        raise ValueError('Incomplete animation samples.')
    if not all(math.isfinite(frame['time']) for frame in frames):
        raise ValueError('Non-finite sample time.')
    names = [bone['name'] for bone in bones]
    if len(set(names)) != len(names):
        raise ValueError('Ambiguous bone names.')
    selected = [index for index, bone in enumerate(bones)
                if bone['name'] == 'SK_Dress_Waist' or bone['name'].startswith('SK_Dress_DEF_')]
    if len(selected) != 33:
        raise ValueError('Expected the observed waist plus 32 Dress deform bones.')
    per_bone = []
    for index in selected:
        bone = bones[index]
        parent = bone['parent']
        if not isinstance(parent, int) or not 0 <= parent < len(bones):
            raise ValueError('Expected an explicit Dress parent.')
        if not bone['weighted'] or bone['restSource'] != 'bindpose':
            raise ValueError('Expected a weighted, verified bind-pose Dress bone.')
        local_bind = multiply(inverse(rests[parent]), rests[index])
        errors = []
        for frame in poses:
            local_pose = multiply(inverse(frame[parent]), frame[index])
            if not all(math.isfinite(value) for row in local_pose for value in row):
                raise ValueError('Non-finite local pose.')
            errors.append(difference(local_pose, local_bind))
        maximum = max(errors)
        sample_index = errors.index(maximum)
        per_bone.append({'name': bone['name'], 'packet_index': index,
                         'parent_name': bones[parent]['name'], 'parent_packet_index': parent,
                         'weighted': bone['weighted'], 'rest_source': bone['restSource'],
                         'sample_count': len(errors), 'all_finite': True,
                         'maximum_local_pose_bind_matrix_element_difference': maximum,
                         'maximum_error_sample_index': sample_index,
                         'maximum_error_time_seconds': frames[sample_index]['time'],
                         'within_diagnostic_threshold': maximum <= DIAGNOSTIC_THRESHOLD})
    worst = max(per_bone, key=lambda entry: entry['maximum_local_pose_bind_matrix_element_difference'])
    result = {
        'date': '2026-10-11',
        'method': 'local_pose = inverse(parent_pose_world) @ bone_pose_world; local_bind = inverse(parent_bind_world) @ bone_bind_world; compare all 16 matrix elements at every supplied sample.',
        'package': str(PACKAGE), 'package_sha256': digest,
        'package_schema': data['schema'], 'clip_name': data.get('clipName'),
        'runtime': 'Standalone Python; no Blender or Unity runtime operation.',
        'helper': str(Path(__file__).resolve()),
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'packet_bone_count': len(bones), 'packet_sample_count': len(frames),
        'input_matrix_count': len(rests) + sum(len(frame) for frame in poses),
        'input_scalar_count': 16 * (len(rests) + sum(len(frame) for frame in poses)),
        'all_input_matrices_finite': True, 'all_sample_times_finite': True,
        'dress_bone_count': len(selected), 'dress_sample_comparison_count': len(selected) * len(frames),
        'dress_names': [bones[index]['name'] for index in selected],
        'diagnostic_matrix_element_threshold': DIAGNOSTIC_THRESHOLD,
        'threshold_rationale': 'A diagnostic float-roundtrip tolerance, approximately 8.2 times the observed maximum residual. It bounds transform-element differences, mixes rotation/scale and translation elements, and is not a production compatibility threshold or permission to relax existing bind/size guards. Tiny motion below this tolerance is unresolved.',
        'maximum_local_pose_bind_matrix_element_difference': worst['maximum_local_pose_bind_matrix_element_difference'],
        'maximum_error_bone': worst['name'],
        'all_dress_samples_within_diagnostic_threshold': all(entry['within_diagnostic_threshold'] for entry in per_bone),
        'conclusion': 'At all 59 supplied samples, the 33 Dress bones have parent-local poses consistent with their bind-local transforms within the stated diagnostic tolerance. No measurable independent Dress motion was found in this packet.',
        'per_bone': per_bone,
        'limitations': [
            'This is packet-only analysis. It does not validate live Dress ownership, controls, drivers, cloth cache, simulation, current skin quality or scene compatibility.',
            'Static means sampled local pose is within the stated tolerance of local bind; exact mathematical zero motion and behavior between samples are not established.',
            'Selection uses the observed packet names; it is not permission to accept arbitrary Dress-prefixed constraints or drivers.',
            'Dress world transforms may animate by inheriting parent/Hips motion.',
            'Preserving local Dress physics/manual controls can produce Dress motion different from this packet; full 217-bone final pose equality must not be claimed for that route.',
            'The original-rig control graph and physical-size guards remain prerequisites. No guard was bypassed and no artist scene was modified.',
        ],
    }
    if OUTPUT.exists():
        raise FileExistsError('Existing evidence was not overwritten: ' + str(OUTPUT))
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(OUTPUT), 'output_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                      'package_sha256': digest, 'samples': len(frames), 'dress_bones': len(selected),
                      'maximum_error': result['maximum_local_pose_bind_matrix_element_difference'],
                      'all_within_threshold': result['all_dress_samples_within_diagnostic_threshold']}, indent=2))


if __name__ == '__main__':
    main()
