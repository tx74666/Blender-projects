"""Read-only bone draw state audit; no add-on registration, saves, or RNA writes."""
import bpy
import hashlib
import json
import math
from pathlib import Path

OUT = Path(__file__).parent / 'shin_draw_0542_diagnostic.json'
SOURCE = Path(bpy.data.filepath)
rig = bpy.data.objects['CoshaRig']
names = ['thigh.L', 'shin.L', 'foot.L', 'thigh.R', 'shin.R', 'foot.R',
         'MCH_foot_heel.L', 'MCH_foot_tip.L', 'MCH_foot_ball.L', 'MCH_foot_ankle.L',
         'MCH_foot_heel.R', 'MCH_foot_tip.R', 'MCH_foot_ball.R', 'MCH_foot_ankle.R']


def value(v):
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, bpy.types.ID):
        return {'type': v.bl_rna.identifier, 'name': v.name}
    if isinstance(v, (bpy.types.Bone, bpy.types.PoseBone, bpy.types.BoneCollection)):
        return v.name
    try:
        return [value(x) for x in v]
    except TypeError:
        return str(v)


def scalar_rna(obj):
    return {p.identifier: value(getattr(obj, p.identifier))
            for p in obj.bl_rna.properties if p.identifier != 'rna_type'
            and p.type in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}}


def one(obj, name):
    pb = obj.pose.bones[name]
    b = pb.bone
    return {'same_bone_pointer': b.as_pointer() == obj.data.bones[name].as_pointer(),
            'bone': scalar_rna(b), 'pose': scalar_rna(pb),
            'bone_matrix': value(b.matrix_local), 'pose_matrix': value(pb.matrix),
            'pose_basis': value(pb.matrix_basis),
            'pose_determinant': pb.matrix.to_3x3().determinant(),
            'pose_head': value(pb.head), 'pose_tail': value(pb.tail),
            'rest_head': value(b.head_local), 'rest_tail': value(b.tail_local),
            'world_head': value(obj.matrix_world @ pb.head),
            'world_tail': value(obj.matrix_world @ pb.tail),
            'pose_color': scalar_rna(pb.color), 'pose_color_custom': scalar_rna(pb.color.custom),
            'bone_color': scalar_rna(b.color), 'bone_color_custom': scalar_rna(b.color.custom),
            'parent': b.parent.name if b.parent else None,
            'shape': value(pb.custom_shape), 'shape_transform': value(pb.custom_shape_transform),
            'collections': [{'name': c.name, 'visible': c.is_visible,
                             'effective': c.is_visible_effectively,
                             'solo': c.is_solo} for c in b.collections],
            'constraints': [dict(scalar_rna(c), target=value(getattr(c, 'target', None)))
                            for c in pb.constraints]}


def main():
    initial_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = rig.evaluated_get(depsgraph)
    result = {'source': str(SOURCE), 'version': bpy.app.version_string,
              'mode': rig.mode, 'armature': scalar_rna(rig.data),
              'rig_object': scalar_rna(rig), 'world_matrix': value(rig.matrix_world),
              'original': {n: one(rig, n) for n in names},
              'evaluated': {n: one(evaluated, n) for n in names},
              'armature_objects': [], 'views': [],
              'other_shin_geometry': []}
    for obj in bpy.context.scene.objects:
        if obj.type == 'ARMATURE':
            result['armature_objects'].append({'name': obj.name, 'data': obj.data.name,
                'visible': obj.visible_get(), 'hidden': obj.hide_get(),
                'show_in_front': obj.show_in_front, 'mode': obj.mode,
                'matrix_world': value(obj.matrix_world),
                'bone_count': len(obj.data.bones),
                'shins': [b.name for b in obj.data.bones if 'shin' in b.name.lower()]})
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type != 'VIEW_3D':
                    continue
                result['views'].append({'screen': screen.name, 'active_type': area.type,
                    'space': scalar_rna(space), 'overlay': scalar_rna(space.overlay),
                    'region': scalar_rna(space.region_3d) if space.region_3d else None,
                    'view_matrix': value(space.region_3d.view_matrix) if space.region_3d else None,
                    'window_matrix': value(space.region_3d.window_matrix) if space.region_3d else None})
    result['finite_pose_matrices'] = all(math.isfinite(x) for pb in evaluated.pose.bones
                                          for row in pb.matrix for x in row)
    result['source_unchanged'] = initial_hash == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    OUT.write_text(json.dumps(result, indent=2), encoding='utf8')
    print('SHIN_DRAW_DIAGNOSTIC', json.dumps({'report': str(OUT),
         'source_unchanged': result['source_unchanged'],
         'finite_pose_matrices': result['finite_pose_matrices'],
         'armatures': result['armature_objects']}))


if __name__ == '__main__':
    main()
