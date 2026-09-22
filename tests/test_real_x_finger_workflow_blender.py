"""Read the saved character into a disposable process; never save X.blend."""
import hashlib
import json
import math
import sys
import time
from pathlib import Path
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_real_x_finger_long_internal_blender import long_strip, character_designer, bank, definition, layout
from character_designer import finger_targets as targets, finger_workflow as work, finger_workflow_ui as ui


def main():
    path = Path(bpy.data.filepath)
    disk = hashlib.sha256(path.read_bytes()).hexdigest()
    character_designer.register()
    c = bpy.context
    if c.object and c.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj, rig = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
    obj.hide_set(False); rig.hide_set(False)
    obj.select_set(True); c.view_layer.objects.active = obj
    c.scene.character_designer_setup.body, c.scene.character_designer_setup.rig = obj, rig
    obj.active_shape_key_index = 0
    bpy.ops.object.mode_set(mode='EDIT')
    c.tool_settings.mesh_select_mode = (False, False, True)
    before = layout.fingerprint(obj)
    for digit, name in (('INDEX', 'f_index'), ('MIDDLE', 'f_middle'), ('RING', 'f_ring'), ('PINKY', 'f_pinky'), ('THUMB', 'thumb')):
        count = long_strip(obj, rig, 'L', name)
        start = time.perf_counter(); key = bank.capture(c)
        print('REAL_CAPTURE', digit, key, count, time.perf_counter()-start, flush=True)
        assert key == digit+'.L'
        for side in ('L', 'R'):
            r = json.loads(obj.character_designer_finger_bank.slots[digit+'.'+side].guide.record)
            assert r['basis']['normal'] and r['internal']
    assert before == layout.fingerprint(obj)
    geometry = {b.name: (tuple(b.head_local), tuple(b.tail_local), b.parent.name if b.parent else '') for b in rig.data.bones}
    start = time.perf_counter(); result = targets.calibrate(c)
    print('REAL_ALL', time.perf_counter()-start, result, flush=True)
    if 'THUMB' not in result['success']:
        r = json.loads(obj.character_designer_finger_bank.slots['THUMB.L'].guide.record)
        print('THUMB_BODY', {k: v for k, v in r['body'].items() if k in ('root', 'tip', 'length', 'radius')}, r['basis']['path'][0], flush=True)
        for bone in targets.index(rig)['THUMB.L']: print('THUMB_BONE', bone.name, tuple(bone.head_local), tuple(bone.tail_local), flush=True)
    assert len(result['success']) == 5, result
    assert geometry == {b.name: (tuple(b.head_local), tuple(b.tail_local), b.parent.name if b.parent else '') for b in rig.data.bones}
    for digit in ('INDEX', 'MIDDLE'):
        bank.select(c, digit, 'L')
        pair = work.prepare(c)
        print('REAL_JOINTS', digit, [j.position for j in pair.joints], flush=True)
        start = time.perf_counter(); ui.show(c)
        print('REAL_RING_PREVIEW_BUILD', time.perf_counter()-start, flush=True)
        result = work.apply(c); print('REAL_GENERATE', digit, result, flush=True)
        fingerprint = layout.fingerprint(obj)
        assert work.apply(c)['added'] == 0 and layout.fingerprint(obj) == fingerprint
        print('REAL_WEIGHT_ONLY', work.apply(c, weights_only=True), flush=True)
        assert len(obj.data.shape_keys.key_blocks) == 10 and obj.data.has_custom_normals
    assert all(not s.error for s in obj.character_designer_finger_bank.slots)
    assert len(targets.calibrate(c)['success']) == 5
    for all_fingers in (False, True):
        start = time.perf_counter(); ui.show_bend(c, all_fingers=all_fingers)
        print('REAL_BEND_PREVIEW_BUILD', all_fingers, time.perf_counter()-start, len(ui._preview['labels']), flush=True)
    ui.hide()
    bpy.ops.object.mode_set(mode='OBJECT')
    # Numerical deformation smoke tests, not a visual quality guarantee.
    original_pose = {b.name: (b.matrix_basis.copy(), b.rotation_mode) for b in rig.pose.bones}
    chosen = [rig.pose.bones['f_index.02.L'], rig.pose.bones['f_index.03.L']]
    for angle, multi in ((0, False), (45, False), (90, False), (45, True)):
        for b in chosen:
            b.rotation_mode = 'XYZ'; b.rotation_euler = (0, 0, 0)
        chosen[0].rotation_euler.x = math.radians(angle)
        if multi: chosen[1].rotation_euler.x = math.radians(angle)
        c.view_layer.update()
        evaluated = obj.evaluated_get(c.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        try:
            assert all(math.isfinite(x) for v in mesh.vertices for x in v.co)
            print('REAL_POSE_FINITE', angle, multi, len(mesh.vertices), flush=True)
        finally: evaluated.to_mesh_clear()
    for b in rig.pose.bones:
        b.rotation_mode = original_pose[b.name][1]
        b.matrix_basis = original_pose[b.name][0]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == disk
    print('REAL_X_WORKFLOW_PASS', flush=True)


if __name__ == '__main__': main()
