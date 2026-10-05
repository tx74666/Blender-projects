"""Read current artist state and save a separate test copy, never repair it."""
import json
import math
from pathlib import Path
import bpy
import character_designer
from character_designer import body_original_mode as original, control_pose_assets as poses
from character_designer import limb_ik, forearm_twist

folder = Path(__file__).resolve().parent
rig = bpy.data.objects['CoshaRig']
body = bpy.data.objects['Cosha']
if forearm_twist._SESSION is not None:
    raise RuntimeError('An active Forearm preview must be resolved before saving a test copy.')
raw = rig.get(original.SESSION)
saved = json.loads(raw) if raw else None
current = poses.native_rest(rig)
differences = []
for name in sorted(set(current) | set(saved['rest'] if saved else {})):
    now = current.get(name)
    old = saved['rest'].get(name) if saved else None
    if now is None or old is None:
        differences.append({'bone': name, 'missing': 'current' if now is None else 'session'})
        continue
    if now != old:
        numeric = {'matrix_max_error': max(abs(a-b) for row, previous in zip(now['matrix'], old['matrix'])
                                          for a, b in zip(row, previous)),
                   'length_delta': now['length'] - old['length']}
        fields = {key: {'old': old[key], 'new': now[key]} for key in now
                  if key not in {'matrix', 'length'} and now[key] != old[key]}
        differences.append({'bone': name, **numeric, 'discrete_fields': fields,
                            'outside_existing_pose_tolerance': bool(fields or abs(numeric['length_delta']) > 1e-6
                                                                  or numeric['matrix_max_error'] > 2e-6)})
constraints = []
for entry in saved['constraints'] if saved else []:
    pb = rig.pose.bones.get(entry['bone'])
    con = pb.constraints.get(entry['name']) if pb else None
    constraints.append({'bone': entry['bone'], 'name': entry['name'], 'saved': entry,
                        'live': None if con is None else {'type': con.type, 'mute': con.mute,
                                                         'influence': con.influence}})
try:
    limb_ik._validate_inventory(rig)
    inventory = {'status': 'passed'}
except Exception as error:
    inventory = {'status': 'refused', 'error': str(error)}
facts = {'runtime': bpy.app.version_string, 'addon': list(character_designer.bl_info['version']),
         'addon_file': character_designer.__file__, 'artist_filepath': bpy.data.filepath,
         'scene': bpy.context.scene.name, 'mode': bpy.context.mode,
         'active_object': bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
         'session_active': original.active(rig), 'session_raw': raw,
         'native_rest_current': current, 'rest_differences': differences,
         'bone_names_equal': saved is not None and saved['bones'] == sorted(rig.data.bones.keys()),
         'native_constraints': constraints, 'strict_inventory': inventory,
         'forearm_preview_active': forearm_twist._SESSION is not None,
         'forearm_calibration': forearm_twist._records(body),
         'body_vertices': len(body.data.vertices), 'shape_keys': list(body.data.shape_keys.key_blocks.keys()) if body.data.shape_keys else [],
         'poses': {obj.name: {pb.name: {'matrix': [list(row) for row in pb.matrix],
                                     'basis': [list(row) for row in pb.matrix_basis]}
                             for pb in obj.pose.bones} for obj in bpy.data.objects if obj.type == 'ARMATURE'}}
copy_path = folder / 'X_live_input.blend'
facts['copy_save'] = sorted(bpy.ops.wm.save_as_mainfile(filepath=str(copy_path), copy=True, check_existing=False))
facts['artist_filepath_after_copy'] = bpy.data.filepath
facts['test_copy'] = str(copy_path)
(folder / 'live_state.json').write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding='utf-8')
print('ORIGINAL_LIVE_SNAPSHOT', facts['copy_save'], 'true Rest changes:',
      [item['bone'] for item in differences if item.get('outside_existing_pose_tolerance')])
