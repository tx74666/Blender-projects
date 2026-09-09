"""Compare saved left-foot reset calibration without changing either scene file."""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import bpy
from mathutils import Matrix

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import foot_controls, limb_ik, torso_controls

BASELINE = Path(r'D:\Blender\Projects\Character\X\outputs\rig\X_left_foot_reset_preview.blend')
CURRENT = Path(r'D:\Blender\Projects\Character\X\X.blend')
REPORT = Path(r'D:\Blender\Projects\Character\X\outputs\rig\latest_x_left_foot_baseline_validation.json')
character_designer.register()


def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects['CoshaRig']
    record = foot_controls.get_record(rig, ('LEG', 'L'))
    inventory = limb_ik._validate_inventory(rig)
    leg = inventory['rigs'][('LEG', 'L')]
    names = set(record['bones'].values()) | set(leg['chain'])
    names.update(bone.name for bone in inventory['bones'] if bone.get(limb_ik.RIG_ID_KEY) == leg['rig_id'])
    state = {name: torso_controls._state(rig.data.bones[name]) for name in sorted(names)}
    pose = {name: {'location': list(rig.pose.bones[name].location),
                   'rotation_mode': rig.pose.bones[name].rotation_mode,
                   'rotation_euler': list(rig.pose.bones[name].rotation_euler),
                   'scale': list(rig.pose.bones[name].scale)}
            for name in (record['roll'], record['toe_control'], leg['target'].name)}
    widgets = {}
    for role, item in record['widgets'].items():
        pb = rig.pose.bones[record['bones'][role]]
        obj = pb.custom_shape
        widgets[role] = {'vertices': [list(vertex.co) for vertex in obj.data.vertices],
                         'edges': [list(edge.vertices) for edge in obj.data.edges],
                         'translation': list(pb.custom_shape_translation),
                         'rotation': list(pb.custom_shape_rotation_euler),
                         'scale': list(pb.custom_shape_scale_xyz),
                         'use_bone_size': pb.use_custom_shape_bone_size}
    return {'path': str(path), 'saved_mtime_local': datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            'record': record, 'bones': state, 'current_pose_channels': pose,
            'target': leg['target'].name, 'solver': record['solver'], 'widget_geometry': widgets}


digests = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (BASELINE, CURRENT)}
baseline = snapshot(BASELINE)
current = snapshot(CURRENT)
assert baseline['bones'].keys() == current['bones'].keys()
matrix_errors = {name: max(abs(a-b) for row_a, row_b in zip(state['matrix'], current['bones'][name]['matrix'])
                           for a,b in zip(row_a, row_b)) for name,state in baseline['bones'].items()}
structural_changes = [name for name,state in baseline['bones'].items()
                      if any(state[field] != current['bones'][name][field]
                             for field in ('parent','deform','connect','inherit_scale','inherit_rotation','local_location'))]
rest_exact = baseline['bones'] == current['bones']
record_exact = baseline['record'] == current['record']
changed_record_fields = [field for field in baseline['record']
                         if baseline['record'][field] != current['record'].get(field)]
calibration_settings_match = all(field in {'id', 'widget_collection', 'widgets'} for field in changed_record_fields)
widget_geometry_match = baseline['widget_geometry'] == current['widget_geometry']
report = {'baseline_path': str(BASELINE), 'current_path': str(CURRENT),
          'current_saved_mtime_local': current['saved_mtime_local'],
          'calibration_record_exact_match': record_exact,
          'changed_record_fields': changed_record_fields,
          'calibration_settings_match_ignoring_generated_resource_ids': calibration_settings_match,
          'widget_geometry_and_display_exact_match': widget_geometry_match,
          'left_leg_and_foot_rest_exact_match': rest_exact,
          'compared_bones': list(baseline['bones']),
          'rest_matrix_max_error': max(matrix_errors.values()),
          'structural_changes': structural_changes,
          'baseline_pose_channels': baseline['current_pose_channels'],
          'current_pose_channels': current['current_pose_channels'],
          'files_unchanged': {str(path): digests[str(path)] == hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in (BASELINE, CURRENT)}, 'saved': False}
REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('LEFT_FOOT_CALIBRATION_RESULT', json.dumps(report), flush=True)
assert not structural_changes and calibration_settings_match and rest_exact and widget_geometry_match
