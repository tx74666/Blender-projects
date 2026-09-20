"""Root fan capture on the real saved asset; disposable Blender only."""
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_real_x_finger_layout_blender import top_strip, character_designer, layout


def main():
    path = Path(bpy.data.filepath)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    character_designer.register()
    try:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        obj, rig = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
        obj.hide_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.active_shape_key_index = 0
        original = obj.data.copy()
        bones_before = [(b.name, tuple(b.head_local), tuple(b.tail_local), tuple(tuple(r) for r in b.matrix_local)) for b in rig.data.bones]
        for side in ('L', 'R'):
            for finger in ('f_index', 'f_middle', 'f_ring', 'f_pinky', 'thumb'):
                obj.data = original.copy()
                bpy.ops.object.mode_set(mode='EDIT')
                top_strip(obj, rig, side, finger)
                bm = bmesh.from_edit_mesh(obj.data)
                selected = {f for f in bm.faces if f.select}
                head = rig.matrix_world @ rig.data.bones[f'{finger}.01.{side}'].head_local
                tip = rig.matrix_world @ rig.data.bones[f'{finger}.03.{side}'].tail_local
                forward = (tip-head).normalized()
                first = min(selected, key=lambda f: (obj.matrix_world @ f.calc_center_median()-head).dot(forward))
                entry = min(first.edges, key=lambda e: sum((obj.matrix_world @ v.co-head).dot(forward) for v in e.verts)/2)
                roots = {f for f in entry.link_faces if f not in selected}
                assert roots
                for seq in (bm.faces, bm.edges, bm.verts):
                    for element in seq: element.select_set(False)
                for face in roots: face.select_set(True)
                bmesh.update_edit_mesh(obj.data)
                settings = layout.state(bpy.context)
                settings.joint_one, settings.joint_two = .35, .69
                settings.width_one, settings.width_two = .024, .021
                settings.three_rings, settings.between_rings = True, 1
                before = layout.fingerprint(obj)
                plan = layout.capture(bpy.context)
                record = json.loads(settings.record)
                assert layout.fingerprint(obj) == before
                actual = obj.matrix_world.to_3x3() @ (Vector(record['tip'])-Vector(record['root']))
                assert actual.normalized().dot(forward) > .8
                assert record['positions'][0] > 0, 'Root was silently shortened to the safe loop'
                added = layout.apply_layout(bpy.context)
                once = layout.fingerprint(obj)
                layout.apply_layout(bpy.context)
                assert layout.fingerprint(obj) == once
                bpy.ops.object.mode_set(mode='OBJECT')
                assert len(obj.data.shape_keys.key_blocks) == 10 and obj.data.has_custom_normals
                print('PASS_REAL_ROOT', finger, side, 'root_faces', record['selection'],
                      'range', record['positions'][0], record['positions'][-1], 'moved', len(plan.get('moves', {})), 'added', added, flush=True)
        assert bones_before == [(b.name, tuple(b.head_local), tuple(b.tail_local), tuple(tuple(r) for r in b.matrix_local)) for b in rig.data.bones]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        print('REAL_X_FINGER_ROOT_RANGE_PASS', flush=True)
    finally: character_designer.unregister()


if __name__ == '__main__': main()
