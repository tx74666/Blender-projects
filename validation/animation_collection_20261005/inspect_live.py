"""Read-only native Action/Worklist inventory; never activates or saves data."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
import bpy


def identity(value):
    if value is None:
        return None
    return {'name': value.name_full, 'type': value.bl_rna.identifier,
            'library': value.library.filepath if value.library else None}


def plain(value):
    if isinstance(value, bpy.types.ID):
        return identity(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, 'items'):
        return {str(k): plain(v) for k, v in value.items()}
    try:
        return [plain(v) for v in value]
    except TypeError:
        return repr(value)


def guard(context):
    return {'scene': context.scene.name_full, 'mode': context.mode,
            'frame': [context.scene.frame_current, context.scene.frame_subframe],
            'active': identity(context.view_layer.objects.active),
            'selected': sorted(o.name_full for o in context.selected_objects),
            'file': bpy.data.filepath, 'is_dirty': bpy.data.is_dirty,
            'rig_actions': {o.name_full: [identity(o.animation_data.action),
                getattr(o.animation_data.action_slot, 'identifier', None)]
                for o in bpy.data.objects if o.animation_data}}


def curves(action):
    result = []
    if action.is_action_layered:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in getattr(strip, 'channelbags', []):
                    result.extend((bag.slot_handle, c) for c in bag.fcurves)
    else:
        result.extend((None, c) for c in getattr(action, 'fcurves', []))
    return result


def action_record(action):
    records = []
    for slot, curve in curves(action):
        records.append({'slot': slot, 'path': curve.data_path, 'index': curve.array_index,
            'keys': [[*k.co, *k.handle_left, *k.handle_right, k.interpolation,
                      k.handle_left_type, k.handle_right_type] for k in curve.keyframe_points],
            'sampled': [list(p.co) for p in curve.sampled_points],
            'modifiers': [m.type for m in curve.modifiers]})
    return {**identity(action), 'users': action.users, 'fake_user': action.use_fake_user,
            'frame_range': list(action.frame_range), 'layered': action.is_action_layered,
            'slots': [{'identifier': s.identifier, 'handle': s.handle,
                       'target_id_type': s.target_id_type} for s in action.slots],
            'curve_count': len(records), 'key_count': sum(len(r['keys']) for r in records),
            'curve_paths': sorted(set(r['path'] for r in records)),
            'inspection_curve_sha256': hashlib.sha256(json.dumps(records, sort_keys=True,
                allow_nan=False).encode()).hexdigest(),
            'fingerprint_limit': 'inventory only; modifier settings/rig dependencies not a sync fingerprint',
            'properties': {k: plain(action[k]) for k in action.keys()}}


def group_record(group):
    if group is None:
        return None
    result = {}
    for prop in group.bl_rna.properties:
        if prop.identifier == 'rna_type':
            continue
        value = getattr(group, prop.identifier)
        result[prop.identifier] = ([group_record(x) for x in value]
            if prop.type == 'COLLECTION' else plain(value))
    return result


def run(previous_editor):
    context = bpy.context
    area = context.area
    assert area and area.type == 'CONSOLE', 'Run only from the coordinated X Console.'
    assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
    before = guard(context)
    facts = {'utc': datetime.now(timezone.utc).isoformat(), 'runtime': bpy.app.version_string,
             'before': before, 'actions': [action_record(a) for a in bpy.data.actions],
             'scenes': [{'name': s.name_full, 'fps': s.render.fps, 'fps_base': s.render.fps_base,
                'worklist': group_record(getattr(s, 'character_designer_animation_worklist', None))}
                for s in bpy.data.scenes],
             'addon': {'path': sys.modules['character_designer'].__file__,
                       'version': sys.modules['character_designer'].bl_info['version']}}
    area.type = previous_editor['type']
    area.ui_type = previous_editor['ui_type']
    facts['after'] = guard(context)
    facts['state_exact'] = facts['before'] == facts['after']
    facts['restored_editor'] = {'type': area.type, 'ui_type': area.ui_type}
    facts['saved'] = False
    output = Path(__file__).parent / 'live_inventory.json'
    output.write_text(json.dumps(facts, ensure_ascii=False, allow_nan=False, indent=2), encoding='utf-8')
    print('ANIMATION_INVENTORY', facts['state_exact'], len(facts['actions']), str(output))

