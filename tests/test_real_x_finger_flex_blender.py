"""Disposable real-model acceptance; never saves X.blend or edits its live session."""
import hashlib
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

REPO = Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path.insert(0, str(REPO / 'addons'))
import character_designer
from character_designer import finger_flex as flex


def activate(obj, mode):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.hide_set(False)
    obj.select_set(True)
    bpy.ops.object.mode_set(mode=mode)


def asset_digest(obj):
    payload = ([tuple(v.co) for v in obj.data.vertices],
               [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices],
               [(k.name, [tuple(v.co) for v in k.data]) for k in obj.data.shape_keys.key_blocks]
               if obj.data.shape_keys else [])
    return hashlib.sha256(repr(payload).encode()).hexdigest()


path = Path(bpy.data.filepath)
disk_before = hashlib.sha256(path.read_bytes()).hexdigest()
character_designer.register()
try:
    rig, mesh = bpy.data.objects['CoshaRig'], bpy.data.objects['Cosha']
    activate(mesh, 'OBJECT')
    mesh.active_shape_key_index = 0
    before = asset_digest(mesh)
    metrics = []
    strips = 0
    for side in ('L', 'R'):
        for finger in ('f_index', 'f_middle', 'f_ring', 'f_pinky', 'thumb'):
            names = [f'{finger}.0{i}.{side}' for i in (1, 2, 3)]
            bone = rig.data.bones[names[0]]
            start = rig.matrix_world @ bone.head_local
            forward = (rig.matrix_world.to_3x3() @ (bone.tail_local - bone.head_local)).normalized()
            activate(mesh, 'EDIT')
            bm = bmesh.from_edit_mesh(mesh.data)
            bm.normal_update()
            # Select a nearby real face/lengthwise edge as a deterministic test input.
            candidates = []
            for face in bm.faces:
                normal = (mesh.matrix_world.to_3x3().inverted().transposed() @ face.normal).normalized()
                if abs(normal.dot(forward)) > .4:
                    continue
                for edge in face.edges:
                    direction = (mesh.matrix_world.to_3x3() @ (edge.verts[1].co - edge.verts[0].co)).normalized()
                    if abs(direction.dot(forward)) > .8:
                        distance = (mesh.matrix_world @ face.calc_center_median() - start).length
                        candidates.append((distance, face, edge))
            _, face, edge = min(candidates, key=lambda item: item[0])
            for f in bm.faces: f.select_set(False)
            for e in bm.edges: e.select_set(False)
            for v in bm.verts: v.select_set(False)
            bm.faces.active = face
            # Exercise real top strips as well as the single-edge input. Walk
            # through opposite cross-edges, stopping before a topology turn.
            strip = [face]
            if finger == 'f_index':
                def extend(seed, exit_edge):
                    path_faces, current, cross = [], seed, exit_edge
                    for _ in range(3):
                        adjacent = [f for f in cross.link_faces if f != current and len(f.verts) == 4]
                        if len(adjacent) != 1 or adjacent[0] in strip or adjacent[0] in path_faces:
                            break
                        other = adjacent[0]
                        if other.normal.dot(seed.normal) < .7:
                            break
                        path_faces.append(other)
                        opposite = [e for e in other.edges if not set(e.verts) & set(cross.verts)]
                        if len(opposite) != 1: break
                        current, cross = other, opposite[0]
                    return path_faces
                crosses = [e for e in face.edges if e != edge and set(e.verts) & set(edge.verts)]
                for cross in crosses:
                    strip.extend(extend(face, cross))
            if len(strip) > 1:
                for f in strip: f.select_set(True)
                strips += 1
            else:
                edge.select_set(True)
            flex.capture(bpy.context)
            if flex.guide_frame(bpy.context)[1].dot(forward) < 0:
                flex.state(bpy.context).flip_forward = True
            activate(rig, 'OBJECT')
            skin_before = {n: rig.pose.bones[n].matrix @ rig.data.bones[n].matrix_local.inverted() for n in names}
            activate(rig, 'EDIT')
            for b in rig.data.edit_bones: b.select = b.name in names
            rig.data.edit_bones.active = rig.data.edit_bones[names[0]]
            _, records = flex.plan(bpy.context)
            geometry = [(tuple(rig.data.edit_bones[n].head), tuple(rig.data.edit_bones[n].tail)) for n in names]
            assert flex.apply(bpy.context) == 3
            assert geometry == [(tuple(rig.data.edit_bones[n].head), tuple(rig.data.edit_bones[n].tail)) for n in names]
            activate(rig, 'POSE')
            bpy.context.view_layer.update()
            minimum = 1.0
            for record in records:
                name = record['name']
                pb = rig.pose.bones[name]
                skin = pb.matrix @ pb.bone.matrix_local.inverted()
                error = max(abs(skin[i][j] - skin_before[name][i][j]) for i in range(4) for j in range(4))
                assert error < 2e-5, (name, 'neutral skin changed', error)
                original_basis = pb.matrix_basis.copy()
                original_mode = pb.rotation_mode
                old = (rig.matrix_world @ pb.tail).copy()
                expected = (rig.matrix_world.to_3x3() @ pb.matrix.to_3x3()
                            @ pb.bone.matrix_local.to_3x3().inverted() @ record['bend']).normalized()
                pb.rotation_mode = 'XYZ'
                pb.rotation_euler.x = math.radians(5)
                bpy.context.view_layer.update()
                delta = rig.matrix_world @ pb.tail - old
                alignment = delta.normalized().dot(expected)
                assert alignment > .99, (name, alignment)
                minimum = min(minimum, alignment)
                pb.rotation_mode = original_mode
                pb.matrix_basis = original_basis
                bpy.context.view_layer.update()
            metrics.append({'finger': f'{finger}.{side}', 'faces': len(strip), 'positive_bend_dot': minimum})
    activate(mesh, 'OBJECT')
    assert asset_digest(mesh) == before, 'Mesh/weights/shape keys changed'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == disk_before
    assert strips == 2, 'Expected both real index-finger strip fixtures'
    print('REAL_X_FINGER_FLEX_PASS', json.dumps({'chains': metrics, 'bones': 30, 'source_unchanged': True}), flush=True)
finally:
    character_designer.unregister()
