import bpy, sys, json, hashlib
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import limb_ik, character_setup

SOURCE = Path(r'D:\Blender\Projects\Character\X\X.blend')
REPORT = SOURCE.parent / 'outputs/rig/head_neck_native_readonly.json'
hash_before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['CoshaRig']
bpy.context.view_layer.update()

def matrix(m): return [list(row) for row in m]
def clean(value):
    if isinstance(value, (str, int, float, bool)) or value is None: return value
    if hasattr(value, 'to_dict'): return clean(value.to_dict())
    if isinstance(value, dict): return {str(k): clean(v) for k,v in value.items()}
    if hasattr(value, 'name'): return {'name': value.name}
    try: return [clean(v) for v in value]
    except TypeError: return str(value)

def info(pb):
    bone = pb.bone
    return {'name': pb.name, 'parent': pb.parent.name if pb.parent else None,
        'children': [b.name for b in pb.children], 'use_deform': bone.use_deform,
        'hide': bone.hide, 'hide_select': bone.hide_select,
        'collections': [{'name': c.name, 'visible': c.is_visible, 'effective': c.is_visible_effectively} for c in bone.collections],
        'custom_shape': pb.custom_shape.name if pb.custom_shape else None,
        'custom_shape_transform': pb.custom_shape_transform.name if pb.custom_shape_transform else None,
        'custom_shape_scale': list(pb.custom_shape_scale_xyz), 'custom_shape_translation': list(pb.custom_shape_translation),
        'custom_shape_rotation': list(pb.custom_shape_rotation_euler), 'custom_shape_bone_size': pb.use_custom_shape_bone_size,
        'location': list(pb.location), 'rotation_mode': pb.rotation_mode, 'rotation_euler': list(pb.rotation_euler),
        'rotation_quaternion': list(pb.rotation_quaternion), 'scale': list(pb.scale),
        'lock_location': list(pb.lock_location), 'lock_rotation': list(pb.lock_rotation),
        'lock_rotation_w': pb.lock_rotation_w, 'lock_rotations_4d': pb.lock_rotations_4d, 'lock_scale': list(pb.lock_scale),
        'head_rest': list(bone.head_local), 'tail_rest': list(bone.tail_local), 'length': bone.length,
        'rest_matrix': matrix(bone.matrix_local), 'pose_matrix': matrix(pb.matrix), 'matrix_basis': matrix(pb.matrix_basis),
        'constraints': [{'name': c.name, 'type': c.type, 'influence': c.influence, 'mute': c.mute,
            'target': getattr(getattr(c, 'target', None), 'name', None), 'subtarget': getattr(c, 'subtarget', None)} for c in pb.constraints],
        'bone_properties': clean(dict(bone)), 'pose_properties': clean(dict(pb))}

native = [pb for pb in rig.pose.bones if not pb.bone.get(limb_ik.OWNER_KEY)]
head_bones = [pb for pb in native if any(word in pb.name.lower() for word in ('head', 'neck', 'eye'))]
head = rig.pose.bones.get('Head') or next(pb for pb in native if pb.name.lower() == 'head')
mesh = bpy.data.objects['Cosha']
descendants = {head.name} | {b.name for b in head.children_recursive}
def bounds(points):
    if not points: return None
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    return {'count': len(points), 'min': lo, 'max': hi, 'center': [(a+b)*.5 for a,b in zip(lo,hi)], 'extent': [b-a for a,b in zip(lo,hi)]}
def weighted_bounds(vertices, transform, names, threshold):
    indices = {g.index for g in mesh.vertex_groups if g.name in names}
    return bounds([transform @ v.co for v in vertices if sum(g.weight for g in v.groups if g.group in indices) >= threshold])
rest_to_head = head.bone.matrix_local.inverted_safe() @ rig.matrix_world.inverted_safe() @ mesh.matrix_world
geometry = {'mesh': mesh.name, 'groups': sorted(descendants), 'rest': {}, 'evaluated': {}}
for threshold in (.001, .05, .25, .5, .9):
    geometry['rest'][str(threshold)] = {'head_only': weighted_bounds(mesh.data.vertices, rest_to_head, {head.name}, threshold),
        'head_descendants': weighted_bounds(mesh.data.vertices, rest_to_head, descendants, threshold)}
dg = bpy.context.evaluated_depsgraph_get()
evaluated = mesh.evaluated_get(dg)
data = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=dg)
pose_to_head = head.matrix.inverted_safe() @ rig.matrix_world.inverted_safe() @ evaluated.matrix_world
for threshold in (.05, .5):
    geometry['evaluated'][str(threshold)] = {'head_only': weighted_bounds(data.vertices, pose_to_head, {head.name}, threshold),
        'head_descendants': weighted_bounds(data.vertices, pose_to_head, descendants, threshold)}
evaluated.to_mesh_clear()
eye_centers = {b.name: list(head.bone.matrix_local.inverted_safe() @ b.bone.head_local) for b in native if 'eye' in b.name.lower()}
eye_forward = sum((b.bone.tail_local - b.bone.head_local for b in native if 'eye' in b.name.lower()), Vector()).normalized()
head_forward = head.bone.matrix_local.inverted_safe().to_3x3() @ eye_forward
setup = character_setup.settings(bpy.context)
shared = {'rig': clean(setup.rig), 'body': clean(setup.body), 'hips': setup.hips_bone, 'head': setup.head_bone,
    'mapping_entries': [{'rig': clean(entry.rig), 'hips': entry.hips_bone, 'head': entry.head_bone, 'footwear': clean(entry.footwear)} for entry in setup.bone_mappings],
    'head_status': clean(character_setup.bone_mapping_status(bpy.context, 'HEAD', armature=rig)),
    'assets': [{'role': entry.role, 'object': clean(entry.object)} for entry in setup.assets]}
neck = head.parent
neck_transform = neck.bone.matrix_local.inverted_safe() @ rig.matrix_world.inverted_safe() @ mesh.matrix_world
geometry['neck_weight_at_least_half_local'] = weighted_bounds(mesh.data.vertices, neck_transform, {neck.name}, .5)
geometry['eye_direction_armature'] = list(eye_forward)
geometry['eye_direction_head_local'] = list(head_forward)
geometry['head_half_weight_extent_per_head_length'] = [n / head.bone.length for n in geometry['rest']['0.5']['head_only']['extent']]
report = {'source': str(SOURCE), 'source_sha256': hash_before, 'version': character_designer.bl_info['version'],
    'armature': rig.name, 'bone_count': len(rig.data.bones), 'matrix_world': matrix(rig.matrix_world),
    'armature_properties': clean(dict(rig)), 'data_property_keys': list(rig.data.keys()),
    'shared_mapping_properties': {key: clean(rig.data[key]) for key in rig.data.keys() if any(w in key.lower() for w in ('map', 'body', 'skeleton'))},
    'character_setup': shared,
    'head_neck_eyes': [info(pb) for pb in head_bones],
    'native_without_shapes': [info(pb) for pb in native if not pb.custom_shape],
    'native_with_shapes': [{'name': pb.name, 'shape': pb.custom_shape.name} for pb in native if pb.custom_shape],
    'cosha_weighted_head_geometry': geometry, 'native_eye_heads_in_head_rest_space': eye_centers,
    'source_unchanged': hashlib.sha256(SOURCE.read_bytes()).hexdigest() == hash_before, 'saved': False}
REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('HEAD_NECK_AUDIT', json.dumps({'bones': len(rig.data.bones), 'head_neck': [(pb.name, pb.parent.name if pb.parent else None, pb.custom_shape.name if pb.custom_shape else None) for pb in head_bones],
    'unshaped_native': [pb.name for pb in native if not pb.custom_shape], 'geometry': geometry, 'eye_local': eye_centers,
    'setup': shared, 'source_unchanged': report['source_unchanged'], 'report': str(REPORT)}), flush=True)
