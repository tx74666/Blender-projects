"""Read the protected external Pose in a temporary Main; no artist edits."""
import ast
import hashlib
import json
from pathlib import Path
import bpy
from character_designer import animation_retarget, control_pose_assets as poses

folder = Path(__file__).resolve().parent
source = Path(r'D:\Blender\Helper\Asset-Libraries\Costom\Pose Library\Saved\Actions\Fist.asset.blend')
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
if Path(bpy.data.filepath).resolve() != artist.resolve():
    raise RuntimeError('Unexpected artist file.')
rig = bpy.context.view_layer.objects.active
if rig is None or rig.name != 'CoshaRig' or rig.type != 'ARMATURE':
    raise RuntimeError('Expected CoshaRig.')
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
if source_hash != '0092ee46255e2101c72df5e78f0504bfdf789486ea72c2646c8f273cc8713cbb':
    raise RuntimeError('Protected Fist source changed.')
result = {'file': str(source), 'sha256': source_hash, 'rig': rig.name,
          'baseline_object': json.loads(rig.get(poses.BASELINE, '{}')).get('object'),
          'existing_actions': [a.name for a in bpy.data.actions]}
with bpy.types.BlendData.temp_data() as temporary:
    with temporary.libraries.load(str(source)) as (available, requested):
        result['source_actions'] = list(available.actions)
        if 'Fist' not in available.actions:
            raise RuntimeError('Expected Fist Action is missing.')
        requested.actions = ['Fist']
    action = requested.actions[0]
    curves = animation_retarget._curves(action, None)
    result.update(slots=[s.identifier for s in action.slots],
                  paths=sorted(set(c.data_path for c in curves)),
                  frames=sorted(set(float(k.co.x) for c in curves for k in c.keyframe_points)),
                  curves=len(curves), asset=bool(action.asset_data),
                  preview_size=list(action.preview.image_size) if action.preview else None,
                  metadata=action.get(poses.ASSET_METADATA))
    try:
        values = poses.channels(action, rig)
        result['names'] = sorted(values)
        result['matching_needed'] = poses._needs_control_matching(rig, values)
        result['compatible_read'] = True
    except Exception as error:
        result.update(compatible_read=False, error=repr(error))
(folder / 'inspection.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('FIST_INSPECTED', result['compatible_read'], result.get('names'), result.get('error'))
