"""Long root-to-tip selections: references must not collapse to the quad sleeve."""
import hashlib
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_real_x_finger_layout_blender import top_strip, character_designer, layout
from character_designer import finger_definition as definition

path = Path(bpy.data.filepath)
digest = hashlib.sha256(path.read_bytes()).hexdigest()
character_designer.register()
if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
obj, rig = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
obj.hide_set(False)
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
obj.active_shape_key_index = 0
bpy.ops.object.mode_set(mode='EDIT')
bpy.context.tool_settings.mesh_select_mode = (False, False, True)
for side in ('L', 'R'):
    for finger in ('f_index', 'f_middle', 'f_ring', 'f_pinky', 'thumb'):
        top_strip(obj, rig, side, finger)
        bm = bmesh.from_edit_mesh(obj.data)
        chosen = {f for f in bm.faces if f.select}
        head = rig.matrix_world @ rig.data.bones[f'{finger}.01.{side}'].head_local
        tip = rig.matrix_world @ rig.data.bones[f'{finger}.03.{side}'].tail_local
        forward = (tip-head).normalized()
        along = lambda point: (obj.matrix_world @ point-head).dot(forward)
        original_start = min(along(v.co) for f in chosen for v in f.verts)
        # Grow two faces beyond each end of the ordinary six-quad strip,
        # following the edge whose midpoint extends furthest in that direction.
        for sign in (-1, 1):
            current = max(chosen, key=lambda f: sign*along(f.calc_center_median()))
            for _ in range(2):
                edges = [e for e in current.edges if any(f not in chosen for f in e.link_faces)]
                if not edges: break
                edge = max(edges, key=lambda e: sign*sum(along(v.co) for v in e.verts)/2)
                neighbors = [f for f in edge.link_faces if f not in chosen]
                if len(neighbors) != 1: break
                current = neighbors[0]
                chosen.add(current)
        for f in chosen: f.select_set(True)
        bmesh.update_edit_mesh(obj.data)
        before = layout.fingerprint(obj)
        data = definition.capture(bpy.context)
        assert layout.fingerprint(obj) == before
        projections = [(point-head).dot(forward) for point in data['path']]
        assert min(projections) < original_start-1e-5, 'Definition shortened to regular sleeve'
        assert max(projections)-min(projections) > (tip-head).length*.85
        print('PASS_REAL_LONG_DEFINITION', finger, side, len(chosen), data['label'], data['direction_label'], flush=True)
assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
print('REAL_X_LONG_DEFINITION_PASSED', flush=True)
character_designer.unregister()
