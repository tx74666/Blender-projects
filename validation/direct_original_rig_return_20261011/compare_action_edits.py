"""Read-only full selected-slot Source/Custom comparison for the open artist file.

Run by the root through the already authorized Blender connection. This script
does not switch Scene, Action, frame, modes, channels or depsgraphs.
"""
import hashlib
import importlib
import json
from pathlib import Path

import bpy

OUT = Path(r'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011\live_action_edits.json')
fp = importlib.import_module('character_designer.animation_worklist_fingerprint')


def digest_file(path):
    path = Path(bpy.path.abspath(path))
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def signature():
    return {'filepath': bpy.data.filepath, 'dirty': bpy.data.is_dirty,
            'scene': bpy.context.scene.name, 'frame': bpy.context.scene.frame_current_final,
            'mode': bpy.context.mode, 'active': getattr(bpy.context.object, 'name', None),
            'selected': sorted(o.name for o in bpy.context.selected_objects)}


def curve_digest(curve):
    # Independent full-key/handle proof per curve; use bounded chunks and avoid
    # materializing every Action's full payload at once in the artist process.
    h = hashlib.sha256()
    def add(value):
        h.update(json.dumps(value, ensure_ascii=False, sort_keys=True,
                            separators=(',', ':'), allow_nan=False).encode('utf-8'))
        h.update(b'\n')
    add([curve.data_path, curve.array_index, curve.extrapolation, curve.mute,
         getattr(curve, 'auto_smoothing', None)])
    for key in curve.keyframe_points:
        add([list(key.co), list(key.handle_left), list(key.handle_right),
             key.interpolation, key.easing, key.handle_left_type, key.handle_right_type,
             key.type, key.amplitude, key.back, key.period])
    for key in curve.sampled_points:
        add(list(key.co))
    # The product fingerprint below additionally covers complete modifier,
    # Action/layer/strip settings. Never call this independent proof sufficient
    # for equivalence when modifiers or unsupported structures are present.
    return {'sha256': h.hexdigest(), 'key_count': len(curve.keyframe_points),
            'sample_count': len(curve.sampled_points), 'modifier_count': len(curve.modifiers),
            'muted': curve.mute}


def action_details(action, slot_handle):
    if action is None:
        return {'present': False}
    proof = fp.fingerprint_action(action, slot_handle)
    curves = list(fp._selected_curves(action, slot_handle))
    per_curve = {}
    for curve in curves:
        key = json.dumps([curve.data_path, curve.array_index], ensure_ascii=False)
        per_curve.setdefault(key, []).append(curve_digest(curve))
    return {'present': True, 'name': action.name, 'local_editable': action.library is None,
            'library': bpy.path.abspath(action.library.filepath) if action.library else None,
            'slot_handle': slot_handle, 'frame_range': list(action.frame_range),
            'curve_count': len(curves), 'key_count': sum(len(c.keyframe_points) for c in curves),
            'sample_count': sum(len(c.sampled_points) for c in curves),
            'modifier_count': sum(len(c.modifiers) for c in curves),
            'complete_motion_proof': proof, 'curve_key_handle_proof': per_curve}


before = signature()
result = {'schema': 'x.validation.live-action-edits/1', 'operation': 'read-only',
          'before': before, 'runtime': {}, 'worklists': []}
cd = importlib.import_module('character_designer')
result['runtime'] = {'blender': bpy.app.version_string, 'addon_version': list(cd.bl_info['version']),
                     'addon_path': cd.__file__, 'fingerprint_module': fp.__file__,
                     'fingerprint_module_sha256': digest_file(fp.__file__)}
for scene in bpy.data.scenes:
    saved = getattr(scene, 'character_designer_animation_worklist', None)
    if saved is None or not saved.items:
        continue
    row = {'scene': scene.name, 'worklist_rig': getattr(saved.rig, 'name', None),
           'workspace_path': saved.workspace_path, 'workspace_identity': saved.workspace_identity,
           'model_file': saved.model_file, 'model_sha256': saved.model_sha256,
           'active_index': saved.active_index, 'items': []}
    for item in saved.items:
        source = action_details(item.source_action, item.source_slot)
        custom = action_details(item.custom_action, item.custom_slot)
        sp, cp = source.get('complete_motion_proof', {}), custom.get('complete_motion_proof', {})
        source_curves = source.pop('curve_key_handle_proof', {})
        custom_curves = custom.pop('curve_key_handle_proof', {})
        differing = sorted(k for k in source_curves.keys() | custom_curves.keys()
                           if source_curves.get(k) != custom_curves.get(k))
        full_known = bool(sp.get('fingerprint_known') and cp.get('fingerprint_known') and
                          sp.get('action_fingerprint') and cp.get('action_fingerprint'))
        unchanged = bool(full_known and sp['action_fingerprint'] == cp['action_fingerprint'])
        row['items'].append({'item_id': item.item_id, 'name': item.name, 'clip_key': item.clip_key,
            'rig': getattr(item.rig, 'name', None), 'side': item.side,
            'manifest_path': item.manifest_path, 'manifest_sha256': digest_file(item.manifest_path),
            'link_identity': item.link_identity, 'export_rig_name': item.export_rig_name,
            'source_file': item.source_file, 'source_file_sha256': digest_file(item.source_file),
            'source_expected_file_sha256': item.source_hash, 'source': source, 'custom': custom,
            'complete_motion_comparison_known': full_known, 'entire_action_motion_equal': unchanged,
            'differing_curve_path_count': len(differing), 'differing_curve_paths_first_40': differing[:40],
            'independent_key_handle_curve_sets_equal': source_curves == custom_curves,
            'migration_policy': ('Re-bake the original packet on the original control Rig; old Action IDs '
                                 'remain retained as provenance.' if unchanged else
                                 'Preserve Custom Action and imported Rig/rest basis in a backup; sample '
                                 'edited world motion and re-bake to original controls. Raw curve copying '
                                 'between different Rest bases is not valid.')})
    result['worklists'].append(row)
result['after'] = signature()
result['artist_context_unchanged'] = before == result['after']
assert result['artist_context_unchanged'], 'Read-only comparison changed artist context.'
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
print(json.dumps({'output': str(OUT), 'context_unchanged': True,
                 'items': [{'scene': row['scene'], 'name': item['name'],
                            'entire_action_equal': item['entire_action_motion_equal'],
                            'comparison_known': item['complete_motion_comparison_known'],
                            'differing_curve_paths': item['differing_curve_path_count']}
                           for row in result['worklists'] for item in row['items']]},
                 ensure_ascii=False))
