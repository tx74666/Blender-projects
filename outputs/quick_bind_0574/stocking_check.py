import sys, json, hashlib, math, traceback
from pathlib import Path
import bpy
from mathutils import Quaternion

SOURCE = Path(r'D:\Blender\Projects\Character\X\X.blend')
OUT = Path(r'D:\Blender\Projects\Character\X\outputs\quick_bind_0574')
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import quick_bind, unity_export
from character_designer.selected_bone_weights import _capture_vertex_groups

report = {'source': str(SOURCE), 'module': quick_bind.__file__, 'checks': {}}
report['source_sha256_before'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()

def digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()

def mesh_state(obj):
    mesh = obj.data
    return {
        'datablock': mesh.as_pointer(),
        'coords': digest([tuple(v.co) for v in mesh.vertices]),
        'edges': digest([tuple(e.vertices) for e in mesh.edges]),
        'faces': digest([tuple(f.vertices) for f in mesh.polygons]),
        'weights': digest(_capture_vertex_groups(obj)),
        'uv': digest([(layer.name, [tuple(item.uv) for item in layer.data]) for layer in mesh.uv_layers]),
        'shape_keys': digest([(key.name, key.value, key.slider_min, key.slider_max,
                               key.relative_key.name, [tuple(v.co) for v in key.data])
                              for key in mesh.shape_keys.key_blocks] if mesh.shape_keys else []),
        'materials': [m.name if m else None for m in mesh.materials],
    }

def modifier_state(obj):
    return [(m.as_pointer(), m.persistent_uid, m.name, m.type,
             m.show_viewport, m.show_render, m.show_in_editmode,
             m.object.name if m.type == 'ARMATURE' and m.object else None,
             (m.use_deform_preserve_volume, m.use_vertex_groups, m.use_bone_envelopes,
              m.vertex_group, m.invert_vertex_group) if m.type == 'ARMATURE' else None)
            for m in obj.modifiers]

def evaluated(obj):
    obj.update_tag()
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    try:
        return [tuple(ev.matrix_world @ v.co) for v in mesh.vertices]
    finally:
        ev.to_mesh_clear()

def difference(a, b):
    assert len(a) == len(b)
    return max((sum((x-y)**2 for x,y in zip(va,vb))**.5 for va,vb in zip(a,b)), default=0)

def scope(rig):
    return [obj.name for obj in unity_export.bound_meshes(bpy.context, rig)]

try:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    obj, rig = bpy.data.objects['Stocking'], bpy.data.objects['CoshaRig']
    obj.hide_set(False)
    obj.hide_viewport = False
    rig.hide_set(False)
    rig.hide_viewport = False
    bpy.context.view_layer.update()
    before_mesh, before_mods = mesh_state(obj), modifier_state(obj)
    before_world = obj.matrix_world.copy()
    before_parent = obj.parent
    before_eval = evaluated(obj)
    before_scope = scope(rig)
    report['scene'] = {'mesh_vertices': len(obj.data.vertices), 'evaluated_vertices': len(before_eval),
                       'shape_keys': [k.name for k in obj.data.shape_keys.key_blocks] if obj.data.shape_keys else [],
                       'modifiers': before_mods, 'parent': before_parent.name if before_parent else None,
                       'frame': bpy.context.scene.frame_current, 'scope_before': before_scope}
    assert obj.name in before_scope
    assert quick_bind.binding_modifier(obj, rig)
    quick_bind.remove_binding(bpy.context, obj, rig)
    report['scene']['scope_removed'] = scope(rig)
    assert obj.name not in report['scene']['scope_removed']
    assert mesh_state(obj) == before_mesh
    assert quick_bind.has_removed_binding(obj)
    assert quick_bind.binding_modifier(obj, rig) is None
    after_remove_mods = modifier_state(obj)
    assert [(m[:7], m[8]) for m in after_remove_mods] == [(m[:7], m[8]) for m in before_mods]
    assert difference([tuple(r) for r in before_world], [tuple(r) for r in obj.matrix_world]) < 1e-6
    removed_eval = evaluated(obj)
    quick_bind.restore_removed_binding(bpy.context, obj)
    restored_eval = evaluated(obj)
    assert mesh_state(obj) == before_mesh
    assert modifier_state(obj) == before_mods
    assert obj.parent == before_parent
    assert not quick_bind.has_removed_binding(obj)
    assert scope(rig) == before_scope
    report['scene']['scope_restored'] = scope(rig)
    report['scene']['eval_restore_max_delta'] = difference(before_eval, restored_eval)
    assert report['scene']['eval_restore_max_delta'] < 1e-6
    report['checks']['stocking_remove_restore_preserves_mesh_weights_keys_modifiers'] = True
    report['checks']['export_scope_tracks_binding'] = True

    candidates = []
    for g in obj.vertex_groups:
        pb = rig.pose.bones.get(g.name)
        if pb and pb.bone.use_deform:
            total = sum(item.weight for v in obj.data.vertices for item in v.groups if item.group == g.index)
            candidates.append((total, g.name))
    candidates.sort(reverse=True)
    report['scene']['weighted_bones'] = candidates[:12]
    bone_name = next((name for _, name in candidates if 'leg' in name.lower()), candidates[0][1])
    pb = rig.pose.bones[bone_name]
    saved_basis = pb.matrix_basis.copy()
    baseline = evaluated(obj)
    from mathutils import Matrix
    pb.matrix_basis = saved_basis @ Matrix.Rotation(math.radians(18), 4, 'X')
    rig.update_tag()
    posed_bound = evaluated(obj)
    motion = difference(baseline, posed_bound)
    report['pose_test'] = {'bone': bone_name, 'degrees_local_x': 18, 'bound_motion': motion,
                           'constraints': [(c.name, c.type, c.influence) for c in pb.constraints]}
    assert motion > 1e-5, 'Test bone failed to move Stocking in evaluated scene'
    quick_bind.remove_binding(bpy.context, obj, rig)
    posed_unbound = evaluated(obj)
    pb.matrix_basis = saved_basis
    rig.update_tag()
    unposed_unbound = evaluated(obj)
    unbound_motion = difference(posed_unbound, unposed_unbound)
    report['pose_test']['unbound_motion'] = unbound_motion
    assert unbound_motion < 1e-6, 'Stocking still follows rig after removal'
    quick_bind.restore_removed_binding(bpy.context, obj)
    original_restored = evaluated(obj)
    assert difference(baseline, original_restored) < 1e-6
    pb.matrix_basis = saved_basis @ Matrix.Rotation(math.radians(18), 4, 'X')
    rig.update_tag()
    posed_restored = evaluated(obj)
    report['pose_test']['restored_pose_max_delta'] = difference(posed_bound, posed_restored)
    assert report['pose_test']['restored_pose_max_delta'] < 1e-6
    pb.matrix_basis = saved_basis
    rig.update_tag()
    assert mesh_state(obj) == before_mesh
    assert modifier_state(obj) == before_mods
    report['checks']['evaluated_skin_disconnects_and_reconnects'] = True
    report['passed'] = True
except Exception:
    report['passed'] = False
    report['error'] = traceback.format_exc()
finally:
    report['source_sha256_after'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    report['checks']['source_file_unchanged'] = report['source_sha256_before'] == report['source_sha256_after']
    report['passed'] = report.get('passed', False) and report['checks']['source_file_unchanged']
    (OUT / 'stocking_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
if not report['passed']:
    raise RuntimeError('STOCKING_BINDING_CHECK_FAILED')
print('STOCKING_BINDING_CHECK_PASSED')
