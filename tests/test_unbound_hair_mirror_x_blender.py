"""Real X Hair integration in a disposable Blender process; never saves X.blend."""
import sys
import traceback
import bpy
import bmesh
from mathutils import Vector

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import mesh_mirror as mirror
from character_designer import mesh_mirror_ui as ui


def select_faces(obj, faces):
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    for seq in (bm.faces, bm.edges, bm.verts):
        for item in seq:
            item.select_set(False)
    for index in faces:
        bm.faces[index].select_set(True)
    bmesh.update_edit_mesh(obj.data)


def main():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    obj = bpy.data.objects['Hair']
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    assert not obj.vertex_groups
    assert not any(m.type == 'ARMATURE' for m in obj.modifiers)
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.index_update()
    bm.verts.index_update()
    components = list(mirror._vertex_components(bm.verts))
    source_verts = next(c for c in components if len(c) == 119 and all(v.co.x > 0 for v in c)
                        and abs(max(v.co.x for v in c)-8.7460775) < .001)
    target_verts = next(c for c in components if all(v.co.x < 0 for v in c)
                        and abs(min(v.co.x for v in c)+8.7460775) < .001)
    source_anchor = next(iter(source_verts)).co.copy()
    target_anchor = next(iter(target_verts)).co.copy()
    if '--damage-counterpart' in sys.argv:
        target_faces = sorted({f for v in target_verts for f in v.link_faces}, key=lambda f: f.index)
        for face in target_faces[40:48]:
            bm.faces.remove(face)
        root = min(bm.verts, key=lambda v: (v.co-target_anchor).length)
        loose = bm.verts.new(root.co + Vector((.015, .025, .02)))
        root = min(bm.verts, key=lambda v: (v.co-target_anchor).length)
        bm.edges.new((root, loose))
        target_verts = next(c for c in mirror._vertex_components(bm.verts) if root in c)
    if '--missing-counterpart' in sys.argv:
        bmesh.ops.delete(bm, geom=list(target_verts), context='VERTS')
        target_verts = set()
    source_root = min(bm.verts, key=lambda v: (v.co-source_anchor).length)
    source_verts = next(c for c in mirror._vertex_components(bm.verts) if source_root in c)
    for seq in (bm.verts, bm.edges, bm.faces):
        seq.index_update()
    source_ids = tuple(sorted(f.index for f in {f for v in source_verts for f in v.link_faces}))
    target_ids = tuple(sorted(f.index for f in {f for v in target_verts for f in v.link_faces}))
    target_vertex_ids = tuple(sorted(v.index for v in target_verts))
    target_count = len(target_ids)
    bm.to_mesh(mesh)
    mesh.update()
    bm.free()
    before_verts, before_faces = len(mesh.vertices), len(mesh.polygons)
    source_positions = tuple(tuple(mesh.vertices[i].co) for i in sorted({i for f in source_ids for i in mesh.polygons[f].vertices}))
    old_materials = tuple(m.name for m in mesh.materials)
    old_uv = tuple(u.name for u in mesh.uv_layers)
    # Record every non-target face geometrically, including all neighboring hair.
    untouched = [tuple(tuple(mesh.vertices[i].co) for i in p.vertices) for p in mesh.polygons if p.index not in target_ids]
    select_faces(obj, source_ids)
    plan = mirror.build_plan(bpy.context)
    print('REAL_X_CANDIDATES', [(i+1, len(c.faces), round(c.score,4), c.coverage, c.automatic) for i,c in enumerate(plan.candidates)], flush=True)
    assert not plan.needs_choice, 'This real hair counterpart must be automatically recognized'
    assert plan.target_faces == target_ids and plan.target_vertices == target_vertex_ids
    batches, labels = ui.preview_geometry(plan)
    assert batches and any('Mirror plane' in label for _,label,_ in labels)
    bpy.ops.object.mode_set(mode='OBJECT')
    selection = mirror.apply_plan(plan)
    mesh = obj.data
    assert len(mesh.polygons) == before_faces - target_count + 118
    assert tuple(tuple(mesh.vertices[i].co) for i in selection) == source_positions
    assert tuple(m.name for m in mesh.materials) == old_materials
    assert tuple(u.name for u in mesh.uv_layers) == old_uv
    after_geometries = [tuple(tuple(mesh.vertices[i].co) for i in p.vertices) for p in mesh.polygons]
    assert all(points in after_geometries for points in untouched)
    assert not obj.vertex_groups
    source_new = [p.index for p in mesh.polygons if all(i in selection for i in p.vertices)]
    select_faces(obj, source_new)
    second = mirror.build_plan(bpy.context)
    assert not second.needs_choice and len(second.target_faces) == 118
    bpy.ops.object.mode_set(mode='OBJECT')
    counts = (len(obj.data.vertices), len(obj.data.polygons))
    mirror.apply_plan(second)
    assert (len(obj.data.vertices), len(obj.data.polygons)) == counts
    print('REAL_X_HAIR_MIRROR_PASSED', {'before': (before_verts,before_faces), 'after': counts,
                                     'source_unchanged': True, 'other_hair_unchanged': True,
                                     'uv_materials_retained': True, 'second_run_no_duplicates': True}, flush=True)


try:
    main()
except Exception:
    traceback.print_exc()
    sys.exit(1)
