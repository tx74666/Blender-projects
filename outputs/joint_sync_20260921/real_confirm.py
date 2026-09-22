"""Disposable in-memory confirmation on the saved asset; never save it."""
import sys, json
from pathlib import Path
sys.path.insert(0, 'D:/MyRepository/Blender-addons-by-Randy/tests')
from inspect_real_finger_joint_sync import *
from character_designer import finger_targets as targets
from mathutils import Vector

path = Path('D:/Blender/Projects/Character/X/X.blend')
saved_hash = file_hash(path)
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)
obj = bpy.data.objects['Cosha']
if C.object and C.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
for item in C.selected_objects: item.select_set(False)
obj.select_set(True); C.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')
ui.hide(); work.release(C)
_, rig = targets.owner(C)
for key in ('THUMB.L', 'THUMB.R'):
    record = json.loads(obj.character_designer_finger_bank.slots[key].guide.record)
    body = record['body']; root, tip = Vector(body['root']), Vector(body['tip'])
    axis = (tip-root).normalized(); length, radius = body['length'], body['radius']
    extent = [(Vector(p)-root).dot(axis) for p in record['basis']['path']]
    lower, upper = min(0., min(extent))-.3*length, max(length, max(extent))+.3*length
    transform = obj.matrix_world.inverted() @ rig.matrix_world
    rows = []
    for bone in targets.index(rig)[key]:
        head, tail = transform @ bone.head_local, transform @ bone.tail_local
        rows.append(dict(name=bone.name, direction=(tail-head).normalized().dot(axis), endpoints=[dict(
            t=(p-root).dot(axis), radial=(p-root-axis*(p-root).dot(axis)).length)
            for p in (head, tail)]))
    print('THUMB_RANGE', key, json.dumps(dict(length=length,radius=radius,lower=lower,upper=upper,
        radial_limit=max(2*radius,.15*length),bones=rows)), flush=True)

for digit in ('INDEX', 'MIDDLE', 'RING', 'PINKY'):
    bank.select(C, digit, 'L'); pair = work.prepare(C)
    if digit == 'INDEX':
        old_mesh, old_rig = layout.fingerprint(obj), rig_state()
        def injected(): raise RuntimeError('Injected real-asset rollback')
        try: work.apply(C, after_commit=injected)
        except RuntimeError as exc: assert 'Injected real-asset' in str(exc), str(exc)
        else: raise AssertionError('Rollback injection did not run')
        assert old_mesh == layout.fingerprint(obj) and old_rig == rig_state()
        print('REAL_ROLLBACK_PASS', flush=True)
    planned = finger_chain.plans(C, work.plans(C))
    result = work.apply(C)
    for chain in planned['chains']:
        for name, head, tail in zip(chain['names'], chain['nodes'], chain['nodes'][1:]):
            bone = rig.data.bones[name]
            assert (bone.head_local-head).length < 2e-6 and (bone.tail_local-tail).length < 2e-6
    assert len(obj.data.shape_keys.key_blocks) == 10
    before, before_rig = layout.fingerprint(obj), rig_state()
    repeated = work.apply(C)
    assert repeated['added'] == 0 and before == layout.fingerprint(obj) and before_rig == rig_state()
    print('REAL_CONFIRM_PASS', digit, json.dumps(result), flush=True)
assert saved_hash == file_hash(path)
print('SAVED_FILE_UNCHANGED', saved_hash, flush=True)
