"""Disposable integration; saved X.blend and its live session are never modified."""
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import finger_layout as layout


def top_strip(obj, rig, side, finger):
    bm = bmesh.from_edit_mesh(obj.data)
    for seq in (bm.verts, bm.edges, bm.faces):
        seq.ensure_lookup_table()
        seq.index_update()
    bones = [rig.data.bones[f'{finger}.0{i}.{side}'] for i in (1, 2, 3)]
    start = rig.matrix_world @ bones[0].head_local
    tip = rig.matrix_world @ bones[-1].tail_local
    direction = (tip-start).normalized()
    length = (tip-start).length
    candidates = []
    for face in bm.faces:
        if len(face.verts) != 4: continue
        center = obj.matrix_world @ face.calc_center_median()
        along = (center-start).dot(direction)
        radial = ((center-start)-direction*along).length
        if not .1*length < along < .85*length or radial > .3*length: continue
        cross = min(face.edges, key=lambda e: abs((obj.matrix_world.to_3x3() @ (e.verts[1].co-e.verts[0].co)).normalized().dot(direction)))
        paths = []
        for entry in [cross, next(e for e in face.edges if not set(e.verts)&set(cross.verts))]:
            path, current, incoming, last_tip = [], face, entry, None
            for _ in range(15):
                try: root, mapping, _ = layout._quad_band(current, incoming)
                except ValueError: break
                if last_tip is not None and set(root) != last_tip: break
                last_tip = set(mapping.values())
                path.append(current)
                outgoing = next(e for e in current.edges if not set(e.verts)&set(incoming.verts))
                adjacent = [f for f in outgoing.link_faces if f != current and len(f.verts) == 4]
                if len(adjacent) != 1 or adjacent[0] in path: break
                current, incoming = adjacent[0], outgoing
                center2 = obj.matrix_world @ current.calc_center_median()
                if (center2-start).dot(direction) < -.02*length or (center2-start).dot(direction) > length: break
            paths.append(path)
        strip = list(reversed(paths[0][1:]))+paths[1]
        if len(strip) >= 3: candidates.append((len(strip), -radial, strip))
    assert candidates, f'No regular sleeve for {finger}.{side}'
    strip = max(candidates, key=lambda item: item[:2])[2]
    for seq in (bm.faces, bm.edges, bm.verts):
        for element in seq: element.select_set(False)
    for face in strip: face.select_set(True)
    bmesh.update_edit_mesh(obj.data)
    return len(strip)


def main():
    path = Path(bpy.data.filepath)
    disk_before = hashlib.sha256(path.read_bytes()).hexdigest()
    character_designer.register()
    try:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        obj, rig = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
        obj.hide_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.active_shape_key_index = 0
        original_mesh = obj.data.copy()
        bones_before = [(b.name, tuple(b.head_local), tuple(b.tail_local), tuple(tuple(r) for r in b.matrix_local)) for b in rig.data.bones]
        results = []
        for side in ('L', 'R'):
            for finger in ('f_index', 'f_middle', 'f_ring', 'f_pinky', 'thumb'):
                obj.data = original_mesh.copy()
                bpy.ops.object.mode_set(mode='EDIT')
                count = top_strip(obj, rig, side, finger)
                layout.capture(bpy.context)
                settings = layout.state(bpy.context)
                settings.joint_one, settings.joint_two = .35, .69
                settings.width_one, settings.width_two = .024, .021
                settings.between_rings = 2
                added = layout.apply_layout(bpy.context)
                once = layout.fingerprint(obj)
                layout.apply_layout(bpy.context)
                assert layout.fingerprint(obj) == once
                bpy.ops.object.mode_set(mode='OBJECT')
                assert len(obj.data.shape_keys.key_blocks) == 10
                assert obj.data.has_custom_normals
                results.append({'finger': f'{finger}.{side}', 'strip_faces': count, 'added': added})
        assert bones_before == [(b.name, tuple(b.head_local), tuple(b.tail_local), tuple(tuple(r) for r in b.matrix_local)) for b in rig.data.bones]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == disk_before
        print('REAL_X_FINGER_LAYOUT_PASS', json.dumps(results), flush=True)
    finally:
        character_designer.unregister()


if __name__ == '__main__': main()
