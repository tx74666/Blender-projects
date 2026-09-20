"""Real root-transition strips, not just the six regular sleeve quads."""
import hashlib
import json
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_real_x_finger_layout_blender import top_strip, character_designer, layout
from character_designer import finger_bank as bank, finger_definition as definition, finger_internal as internal


def long_strip(obj, rig, side, finger):
    top_strip(obj, rig, side, finger)
    bm = bmesh.from_edit_mesh(obj.data)
    chosen = {f for f in bm.faces if f.select}
    head = rig.matrix_world @ rig.data.bones[f'{finger}.01.{side}'].head_local
    tip = rig.matrix_world @ rig.data.bones[f'{finger}.03.{side}'].tail_local
    forward = (tip-head).normalized()
    along = lambda point: (obj.matrix_world @ point-head).dot(forward)
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
    for face in chosen: face.select_set(True)
    bmesh.update_edit_mesh(obj.data)
    return len(chosen)


def main():
    c = bpy.context
    path = Path(bpy.data.filepath)
    before_disk = hashlib.sha256(path.read_bytes()).hexdigest()
    character_designer.register()
    if c.object and c.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj, rig = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
    obj.hide_set(False)
    obj.select_set(True)
    c.view_layer.objects.active = obj
    obj.active_shape_key_index = 0
    bpy.ops.object.mode_set(mode='EDIT')
    c.tool_settings.mesh_select_mode = (False, False, True)
    before = layout.fingerprint(obj)
    for side in ('L', 'R'):
        for digit, name in (('INDEX', 'f_index'), ('MIDDLE', 'f_middle'), ('RING', 'f_ring'), ('PINKY', 'f_pinky'), ('THUMB', 'thumb')):
            count = long_strip(obj, rig, side, name)
            bm = definition._snapshot(obj)
            try:
                spec = definition._selection(c, bm)
                report = bank.survey(c, obj, bm, [v.index for v in definition._input_vertices(bm, spec)])
                key = bank._resolve(report, spec, bm)
                candidate = report['candidates'][key]
                sample = definition._sample(bm, spec)
                centers, main_axis, *_ = internal.geometry(bm, candidate)
                zs = [Vector(p).dot(main_axis) for p in sample['path']]
                todo, component = [bm.faces[candidate['faces'][0]]], set()
                while todo:
                    face = todo.pop()
                    if face in component: continue
                    component.add(face)
                    todo.extend(f for e in face.edges for f in e.link_faces if f not in component)
                print('LONG_INPUT', key, count, 'proximal_extra', centers[0].dot(main_axis)-min(zs),
                      'nonmanifold', sum(not e.is_manifold for f in component for e in f.edges),
                      'z', [round((z-centers[0].dot(main_axis))/candidate['length'], 3) for z in zs], flush=True)
                if '--short-probe' in sys.argv: return
            finally: bm.free()
            try:
                assert bank.capture(c) == digit+'.'+side
                record = json.loads(definition.state(c).record)
                assert definition.state(c).confirmed
                b = obj.character_designer_finger_bank
                assert all(b.slots[digit+'.'+s].guide.record and not b.slots[digit+'.'+s].error for s in ('L', 'R'))
                bm = definition._snapshot(obj)
                try:
                    assert record['body']['root_extension']
                    assert internal.Volume(bm, record['body']).certify(record['internal']['path'], record['internal']['margin']) is not None
                    hint = record['surface'].get('centering')
                    assert hint, (key, 'no surface centering')
                    p, q = map(Vector, hint['path'])
                    axis = internal.geometry(bm, record['body'])[1]
                    side_axis = axis.cross(Vector(hint['normal'])).normalized()
                    slope = (q-p).dot(side_axis)/(q-p).dot(axis)
                    def lateral_error(result):
                        return max(abs((Vector(v)-p).dot(side_axis)-slope*(Vector(v)-p).dot(axis)) for v in result['path'])
                    old = internal.solve(bm, record['body'], record['basis']['path'])
                    error = lateral_error(record['internal'])
                    print('SURFACE_CENTER_ERROR', key, lateral_error(old), error, flush=True)
                    assert error < record['internal']['thickness']*.001
                finally: bm.free()
                print('LONG_INTERNAL_PASS', key, record['internal']['coverage'], flush=True)
            except ValueError as exc:
                if '--probe' not in sys.argv: raise
                print('LONG_INTERNAL_FAIL', key, str(exc), flush=True)
            assert layout.fingerprint(obj) == before
    if '--probe' not in sys.argv:
        for digit in ('INDEX', 'MIDDLE'):
            bank.select(c, digit, 'L')
            original = definition.frame(c, purpose='TOPOLOGY')
            layout.capture_definition(c)
            assert abs(json.loads(layout.state(c).record)['length']-original['length']) < 1e-6
            layout.apply_layout(c)
        for slot in obj.character_designer_finger_bank.slots:
            assert not slot.error, (slot.name, slot.error)
            data = definition.frame(bank.scoped(c, slot.guide))
            assert data['internal']
        assert len(obj.data.shape_keys.key_blocks) == 10 and obj.data.has_custom_normals
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before_disk
    print('REAL_X_LONG_INTERNAL_DONE', flush=True)
    character_designer.unregister()


if __name__ == '__main__': main()
