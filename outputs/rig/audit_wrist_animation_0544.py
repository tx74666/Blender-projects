"""Read current saved rig animation references, without registration or mutation."""
import bpy
import hashlib
import json
from pathlib import Path

NAMES = {'CTRL_hand_IK.L', 'CTRL_hand_IK.R', 'hand.L', 'hand.R',
         'forearm.L', 'forearm.R', 'upper_arm.L', 'upper_arm.R', 'CTRL_master'}
OUT = Path(__file__).parent


def curves(action):
    if hasattr(action, 'fcurves'):
        return list(action.fcurves)
    return [c for layer in action.layers for strip in layer.strips
            for bag in getattr(strip, 'channelbags', ()) for c in bag.fcurves]


def mentions(path):
    return any('pose.bones[' + json.dumps(n) + ']' in path for n in NAMES)


def curve_info(c):
    return {'path': c.data_path, 'index': c.array_index,
            'keys': len(c.keyframe_points), 'samples': len(c.sampled_points),
            'mute': c.mute, 'modifiers': [m.type for m in c.modifiers]}


def main():
    source = Path(bpy.data.filepath)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    rig = bpy.data.objects['CoshaRig']
    report = {'source': str(source), 'sha256': digest, 'rig': rig.name, 'frame': bpy.context.scene.frame_current,
              'animation': {}, 'relevant_actions': [], 'drivers_writing_rig': [],
              'drivers_reading_relevant_bones': [], 'other_constraint_readers': []}
    used = set()
    for owner in (rig, rig.data):
        animation = owner.animation_data
        entry = {'active_action': animation.action.name if animation and animation.action else None,
                 'nla_tracks': []}
        if animation and animation.action:
            used.add(animation.action)
        def strip_info(strip):
            action = getattr(strip, 'action', None)
            if action:
                used.add(action)
            return {'name': strip.name, 'type': strip.type, 'action': action.name if action else None,
                    'mute': strip.mute, 'influence': strip.influence,
                    'children': [strip_info(c) for c in getattr(strip, 'strips', ())]}
        if animation:
            entry['nla_tracks'] = [{'name': t.name, 'mute': t.mute, 'solo': t.is_solo,
                                   'strips': [strip_info(s) for s in t.strips]} for t in animation.nla_tracks]
            entry['drivers_count'] = len(animation.drivers)
        report['animation'][owner.bl_rna.identifier + ':' + owner.name] = entry
    for action in bpy.data.actions:
        relevant = [c for c in curves(action) if mentions(c.data_path)]
        if action in used or relevant:
            report['relevant_actions'].append({'name': action.name, 'assigned_to_rig': action in used,
                'users': action.users, 'all_curve_count': len(curves(action)),
                'relevant_curves': [curve_info(c) for c in relevant],
                'rig_transform_curves': [curve_info(c) for c in curves(action) if action in used
                    and c.data_path in {'location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale'}]})
    ids = set(bpy.data.user_map())
    for owner in ids:
        animation = getattr(owner, 'animation_data', None)
        if animation:
            for c in animation.drivers:
                if owner == rig and (mentions(c.data_path) or c.data_path in {'location', 'rotation_euler', 'rotation_quaternion', 'scale'}):
                    report['drivers_writing_rig'].append(dict(curve_info(c), expression=c.driver.expression))
                reads = []
                for var in c.driver.variables:
                    for target in var.targets:
                        if target.id == rig and (target.bone_target in NAMES or mentions(target.data_path)
                            or target.data_path in {'location', 'rotation_euler', 'rotation_quaternion', 'scale'}):
                            reads.append({'name': var.name, 'type': var.type, 'bone_target': target.bone_target,
                                          'data_path': target.data_path, 'transform_space': target.transform_space})
                if reads:
                    report['drivers_reading_relevant_bones'].append({'owner': owner.bl_rna.identifier + ':' + owner.name,
                         **curve_info(c), 'expression': c.driver.expression, 'reads': reads})
    for obj in bpy.data.objects:
        owners = [(obj.name, obj)] + ([(obj.name + '/' + pb.name, pb) for pb in obj.pose.bones] if obj.pose else [])
        for name, owner in owners:
            for c in owner.constraints:
                if getattr(c, 'target', None) == rig and getattr(c, 'subtarget', '') in NAMES:
                    report['other_constraint_readers'].append({'owner': name, 'name': c.name, 'type': c.type,
                        'subtarget': c.subtarget, 'mute': c.mute, 'influence': c.influence})
    report['source_unchanged'] = hashlib.sha256(source.read_bytes()).hexdigest() == digest
    (OUT / 'wrist_animation_0544_audit.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print('WRIST_ANIMATION_AUDIT', json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
