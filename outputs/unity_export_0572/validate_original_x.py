"""Disposable read-only verification of the saved X RGC collection migration."""
import array
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path('D:/MyRepository/Blender-addons-by-Randy')
OUT = Path('D:/Blender/Projects/Character/X/outputs/unity_export_0572')
SOURCE = Path('D:/Blender/Projects/Character/X/X.blend')
assert Path(bpy.data.filepath) == SOURCE
sys.path.insert(0, str(ROOT / 'addons'))
import character_designer
from character_designer import body_setup, bone_collections as groups


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def matrix(value):
    return tuple(tuple(row) for row in value)


def image_state(rig, meshes):
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = {}
    for obj in meshes:
        owner = obj.evaluated_get(deps)
        mesh = owner.to_mesh()
        try:
            values = array.array('f', [0.0]) * (len(mesh.vertices) * 3)
            mesh.vertices.foreach_get('co', values)
            evaluated[obj.name] = hashlib.sha256(values.tobytes()).hexdigest()
        finally:
            owner.to_mesh_clear()
    return {
        'bone_names': list(rig.data.bones.keys()),
        'rest': digest({b.name: [b.parent.name if b.parent else None, matrix(b.matrix_local), b.length, b.use_deform] for b in rig.data.bones}),
        'basis': digest({p.name: matrix(p.matrix_basis) for p in rig.pose.bones}),
        'pose': digest({p.name: matrix(p.matrix) for p in rig.pose.bones}),
        'constraints': digest({p.name: [(c.name, c.type, c.influence, c.mute,
                                      getattr(getattr(c, 'target', None), 'name', None),
                                      getattr(c, 'subtarget', None)) for c in p.constraints] for p in rig.pose.bones}),
        'custom_shapes': digest({p.name: [p.custom_shape.name if p.custom_shape else None,
                                        tuple(p.custom_shape_translation), tuple(p.custom_shape_rotation_euler),
                                        tuple(p.custom_shape_scale_xyz)] for p in rig.pose.bones}),
        'weights': {obj.name: digest([[g.name for g in obj.vertex_groups],
                                      [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices]]) for obj in meshes},
        'shape_keys': {obj.name: digest([(key.name, key.value, [tuple(v.co) for v in key.data])
                                        for key in obj.data.shape_keys.key_blocks]) if obj.data.shape_keys else None for obj in meshes},
        'evaluated_mesh_coordinates': evaluated,
    }


rig = bpy.data.objects['CoshaRig']
meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH'
          and (obj.parent == rig or any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers))]
source_before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
before = image_state(rig, meshes)
layout_before = groups.snapshot_layout(rig)
other_layouts = {obj.name: groups.snapshot_layout(obj) for obj in bpy.context.scene.objects if obj.type == 'ARMATURE' and obj != rig}
assert not body_setup.has_generated(rig), 'X still contains generated Body setup; stop without mutation.'
character_designer.register()
timer = groups._MIGRATION_TIMER
if timer is not None and bpy.app.timers.is_registered(timer):
    bpy.app.timers.unregister(timer)
groups._native_migration_once()
after = image_state(rig, meshes)
layout_after = groups.snapshot_layout(rig)
assert before == after, [key for key in before if before[key] != after[key]]
assert len(rig.data.bones) == 56, len(rig.data.bones)
assert groups.body_collection(rig) is None
assert rig.data.collections.active.name == 'Original'
assert rig.data.collections_all['Original'].is_visible_effectively
assert set(rig.data.collections_all['Original'].bones.keys()) == set(rig.data.bones.keys())
assert all(not b.hide for b in rig.data.bones)
assert all(not p.hide for p in rig.pose.bones if hasattr(p, 'hide'))
assert other_layouts == {obj.name: groups.snapshot_layout(obj) for obj in bpy.context.scene.objects if obj.type == 'ARMATURE' and obj != rig}
assert not groups.show_original_after_removal(rig)['changed']
assert source_before == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
report = {'ok': True, 'source': str(SOURCE), 'source_sha256': source_before, 'source_saved': False,
          'rig': rig.name, 'native_bones': len(rig.data.bones), 'meshes_checked': [obj.name for obj in meshes],
          'unchanged': list(before.keys()), 'other_scene_rigs_unchanged': list(other_layouts),
          'collections_before': layout_before['collections'], 'collections_after': layout_after['collections'],
          'original_active_visible': True, 'idempotent': True, 'before': before, 'after': after}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'original_x_report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('ORIGINAL_X_PASSED', json.dumps({k: report[k] for k in ('rig', 'native_bones', 'meshes_checked', 'source_saved')}))
