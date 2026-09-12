"""Read-only Direct-rest and twist calibration comparison on an immutable X copy."""
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).parent
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import limb_ik as limb, forearm_twist as twist

source = Path(bpy.data.filepath)
sha = hashlib.sha256(source.read_bytes()).hexdigest()
rig = bpy.data.objects['CoshaRig']
registry = limb._load_direct_rest_registry(rig, strict=True)
original = {name: state for entry in registry['limbs'].values() for name,state in entry['original'].items()}
report = {'source': str(source), 'sha256': sha, 'meshes': {}}
for obj in bpy.data.objects:
    if obj.type != 'MESH' or twist.RECORD_KEY not in obj:
        continue
    records = twist._records(obj)
    result = report['meshes'][obj.name] = {}
    for side, record in records.items():
        if record['armature'] != rig.name:
            continue
        saved_matrices = {name: Matrix([values[i:i+4] for i in range(0,16,4)]) for name,values in record['rest']}
        data = result[side] = {'chain': record['chain'], 'enabled': record['enabled'],
            'key': record['key'], 'topology_matches': record['topology'] == twist._topology(obj.data), 'bones': {}}
        for name in record['chain']:
            bone = rig.data.bones[name]
            current = bone.matrix_local
            entry = data['bones'][name] = {'calibration_matches_current_exact': current == saved_matrices[name],
                'calibration_current_matrix_error': max(abs(current[i][j]-saved_matrices[name][i][j]) for i in range(4) for j in range(4)),
                'has_direct_original': name in original}
            if name in original:
                state = original[name]
                old_axis = (Vector(state['tail']) - Vector(state['head'])).normalized()
                current_axis = (bone.tail_local - bone.head_local).normalized()
                entry.update(rest_state_matches_original=limb._rest_state_matches(bone,state),
                    head_distance=(bone.head_local-Vector(state['head'])).length,
                    tail_distance=(bone.tail_local-Vector(state['tail'])).length,
                    axis_angle_degrees=math.degrees(current_axis.angle(old_axis)),
                    z_angle_degrees=math.degrees(current.to_3x3().col[2].angle(Vector(state['z']))),
                    parent_matches=(bone.parent.name if bone.parent else '') == state['parent'],
                    connected_matches=bone.use_connect == state['use_connect'])
report['source_unchanged'] = hashlib.sha256(source.read_bytes()).hexdigest() == sha
(OUT/'body_setup_0546_twist_rest_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('TWIST_REST_AUDIT',json.dumps(report),flush=True)
assert report['source_unchanged']
