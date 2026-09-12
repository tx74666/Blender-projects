"""Read-only inventory of an immutable saved-X copy; no addon registration/save."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
import bpy

OUT = Path(__file__).parent
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import limb_ik as limb, limb_fk_visuals as fk
from character_designer import body_detail_visuals, head_neck_visuals, root_control
from character_designer import torso_controls, spine_ik_fk, eye_controls, foot_controls


def simple(value):
    if isinstance(value, bpy.types.ID):
        return {'id_type': value.bl_rna.identifier, 'name': value.name}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, 'items'):
        return {str(k): simple(v) for k, v in value.items()}
    try:
        return [simple(v) for v in value]
    except TypeError:
        return str(value)


def props(owner):
    return {k: simple(v) for k, v in owner.items() if 'character_designer' in k}


def summary(value, depth=0):
    if isinstance(value, str):
        try:
            return summary(json.loads(value), depth)
        except (ValueError, TypeError):
            return value
    if isinstance(value, dict):
        return {k: ({'entries': len(v)} if k in {'rest', 'direct_rest', 'original', 'generated', 'vertices', 'weights', 'bone_states'} and isinstance(v, (dict, list))
                    else summary(v, depth+1)) for k, v in value.items()}
    if isinstance(value, list):
        return {'count': len(value)} if len(value) > 20 or depth > 4 else [summary(v, depth+1) for v in value]
    return value


def curves(action):
    return limb._fcurves_for_action(action)


def guarded(fn):
    try:
        result = fn()
        return {'ok': True, 'present': result is not None}
    except Exception as exc:
        return {'ok': False, 'error': str(exc)}


def main():
    source = Path(bpy.data.filepath)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    report = {'source': str(source), 'sha256': digest, 'frame': bpy.context.scene.frame_current,
              'active_object': bpy.context.object.name if bpy.context.object else None,
              'mode': bpy.context.mode, 'armatures': {}, 'meshes': {}, 'actions': [], 'drivers': []}
    modules = (fk, body_detail_visuals, head_neck_visuals, root_control,
               torso_controls, spine_ik_fk, eye_controls, foot_controls)
    for rig in bpy.data.objects:
        if rig.type != 'ARMATURE':
            continue
        r = {'bone_count': len(rig.data.bones), 'object_props': summary(props(rig)),
             'data_props': summary(props(rig.data)), 'native_bones': [], 'generated_bones': [],
             'custom_shapes': [], 'validators': {}, 'constraints': [], 'collections': [], 'animation': {}}
        report['armatures'][rig.name] = r
        for b in rig.data.bones:
            row = {'name': b.name, 'parent': b.parent.name if b.parent else None, 'deform': b.use_deform}
            pb = rig.pose.bones[b.name]
            tagged = props(b)
            if tagged.get(limb.OWNER_KEY) or any(k.endswith('_owner') for k in tagged):
                r['generated_bones'].append(dict(row, props=tagged))
            else:
                r['native_bones'].append(row)
            if pb.custom_shape:
                r['custom_shapes'].append({'bone': b.name, 'object': pb.custom_shape.name,
                    'owner': pb.custom_shape.get(limb.OWNER_KEY),
                    'anchor': pb.custom_shape_transform.name if pb.custom_shape_transform else None,
                    'display': limb._pose_shape_json_state(pb), 'bone_props': tagged,
                    'pose_props': summary(props(pb))})
            for c in pb.constraints:
                r['constraints'].append({'bone': b.name, 'name': c.name, 'type': c.type,
                    'target': getattr(getattr(c, 'target', None), 'name', None),
                    'subtarget': getattr(c, 'subtarget', None), 'mute': c.mute,
                    'influence': c.influence, 'owner_space': c.owner_space,
                    'target_space': getattr(c, 'target_space', None)})
        r['collections'] = [{'name': c.name, 'parent': c.parent.name if c.parent else None,
                            'visible': c.is_visible, 'bones': list(c.bones.keys()), 'props': props(c)}
                           for c in rig.data.collections_all]
        ad = rig.animation_data
        r['animation'] = {'active_action': ad.action.name if ad and ad.action else None,
            'nla': [{'name': t.name, 'mute': t.mute, 'strips': [{'name': s.name, 'action': s.action.name if getattr(s, 'action', None) else None} for s in t.strips]} for t in ad.nla_tracks] if ad else [],
            'drivers': len(ad.drivers) if ad else 0}
        if rig.name != 'CoshaRig':
            continue
        r['validators']['limb_inventory'] = guarded(lambda: limb._validate_inventory(rig))
        for module in modules:
            r['validators'][module.__name__.split('.')[-1]] = guarded(lambda module=module: module.validate(rig))
        record = fk.get_record(rig)
        if record:
            r['fk_dependency_check'] = guarded(lambda: fk._refuse_dependencies(rig, record))
            r['fk_display_differences'] = {}
            for name, entry in record['bindings'].items():
                pb = rig.pose.bones[name]
                actual = limb._pose_shape_json_state(pb)
                expected = entry['generated']
                r['fk_display_differences'][name] = {k: {'saved': expected.get(k), 'current': v}
                    for k, v in actual.items() if k != 'custom_shape' and v != expected.get(k)}
        try:
            sizes = fk._size_record(rig)
            r['ik_size_checks'] = {n: guarded(lambda n=n,e=e: fk._validate_size_binding(rig, sizes, n, e))
                                   for n,e in sizes['bindings'].items()} if sizes else {}
        except Exception as exc:
            r['ik_size_checks'] = {'error': str(exc)}
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            r = {'vertices': len(obj.data.vertices), 'edges': len(obj.data.edges), 'faces': len(obj.data.polygons),
                 'owner': obj.get(limb.OWNER_KEY), 'properties': summary(props(obj)),
                 'parent': obj.parent.name if obj.parent else None, 'modifiers': [],
                 'groups': [g.name for g in obj.vertex_groups]}
            for m in obj.modifiers:
                r['modifiers'].append({'name': m.name, 'type': m.type,
                    'target': getattr(getattr(m, 'object', None), 'name', None), 'viewport': m.show_viewport})
            if not obj.get(limb.OWNER_KEY):
                counts = Counter(g.group for v in obj.data.vertices for g in v.groups if g.weight > 0)
                r['positive_weight_assignments'] = {g.name: counts[g.index] for g in obj.vertex_groups if counts[g.index]}
            report['meshes'][obj.name] = r
    for action in bpy.data.actions:
        report['actions'].append({'name': action.name, 'users': action.users,
            'curves': [{'path': c.data_path, 'index': c.array_index, 'keys': len(c.keyframe_points),
                        'samples': len(c.sampled_points)} for c in curves(action)]})
    for owner in set(bpy.data.user_map()):
        ad = getattr(owner, 'animation_data', None)
        if ad:
            for c in ad.drivers:
                report['drivers'].append({'owner': owner.name, 'path': c.data_path, 'index': c.array_index,
                    'expression': c.driver.expression, 'mute': c.mute,
                    'variables': [{'name': v.name, 'type': v.type, 'targets': [
                        {'id': t.id.name if t.id else None, 'bone': t.bone_target,
                         'path': t.data_path, 'transform': t.transform_type} for t in v.targets]} for v in c.driver.variables]})
    report['scene_props'] = summary(props(bpy.context.scene))
    report['source_unchanged'] = hashlib.sha256(source.read_bytes()).hexdigest() == digest
    (OUT / 'body_setup_0545_saved_audit.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    main_rig = report['armatures'].get('CoshaRig', {})
    print('BODY_SETUP_AUDIT', json.dumps({'source': str(source), 'validators': main_rig.get('validators'),
          'FK_changes': main_rig.get('fk_display_differences'), 'source_unchanged': report['source_unchanged']}), flush=True)


if __name__ == '__main__':
    main()
