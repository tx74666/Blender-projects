import json
from pathlib import Path
from mathutils import Matrix

root = Path(r'D:\Blender\Projects\Character\X\outputs\unity_forearm_implementation')
source = json.loads((root/'stencil_golden.json').read_text(encoding='utf8'))
result = {'meshName':'Cosha','cases':[]}
for case in source['cases']:
    to_arm = Matrix(case['to_armature'])
    from_arm = to_arm.inverted()
    bones = []
    for name, pose in case['bone_pose_armature'].items():
        deformation = from_arm @ Matrix(pose) @ Matrix(source['bone_rest_armature'][name]).inverted() @ to_arm
        bones.append({'name':name,'matrix':[float(value) for row in deformation for value in row]})
    result['cases'].append({'name':case['name'],'bones':bones,
        'denseIds':case['dense_ids'],
        'denseExtra':[dict(zip(('x','y','z'),delta)) for delta in case['dense_extra']]})
(root/'unity_golden.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf8')
print('UNITY_GOLDEN_OK',len(result['cases']),len(result['cases'][0]['bones']),len(result['cases'][0]['denseIds']))
