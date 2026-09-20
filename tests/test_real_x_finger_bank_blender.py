"""Unbound real X hand recognition and per-finger local topology lifecycle."""
import hashlib
import json
import sys
from pathlib import Path
import bpy
import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_real_x_finger_layout_blender import top_strip, character_designer, layout
from character_designer import finger_bank as bank, finger_definition as definition, finger_detect as detect, finger_flex as flex

C = bpy.context
path = Path(bpy.data.filepath)
disk = hashlib.sha256(path.read_bytes()).hexdigest()
character_designer.register()
if C.object and C.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
obj, rig = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
obj.hide_set(False)
obj.select_set(True)
C.view_layer.objects.active = obj
obj.active_shape_key_index = 0
# The names/rig are used ONLY by the test to select ground-truth input patches.
# The implementation sees geometry, not a binding or named vertex groups.
for modifier in list(obj.modifiers):
    if modifier.type == 'ARMATURE': obj.modifiers.remove(modifier)
obj.vertex_groups.clear()
bpy.ops.object.mode_set(mode='EDIT')
C.tool_settings.mesh_select_mode = (False, False, True)
before = layout.fingerprint(obj)
selected = {}
for side in ('L', 'R'):
    for digit, name in (('PINKY', 'f_pinky'), ('INDEX', 'f_index'), ('THUMB', 'thumb'), ('RING', 'f_ring'), ('MIDDLE', 'f_middle')):
        count = top_strip(obj, rig, side, name)
        bm = bmesh.from_edit_mesh(obj.data)
        selected[f'{digit}.{side}'] = [f.index for f in bm.faces if f.select]
        assert bank.capture(C) == f'{digit}.{side}'
        definition.confirm(C)
        bank.sync(C)
        assert layout.fingerprint(obj) == before
        print('REAL_BANK_CAPTURE', digit, side, count, flush=True)
b = obj.character_designer_finger_bank
assert len(b.slots) == 10 and not json.loads(b.survey)['warnings']
assert all(s.guide.confirmed and not s.error for s in b.slots)
for digit, name in (('THUMB', 'thumb'), ('INDEX', 'f_index'), ('MIDDLE', 'f_middle'), ('RING', 'f_ring'), ('PINKY', 'f_pinky')):
    bank.select(C, digit, 'L')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    C.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones: bone.select = bone.name.startswith(name+'.') and bone.name.endswith('.L')
    assert flex.apply(C) == 6
    print('REAL_BANK_PAIRED_ROLL', digit, flush=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    C.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
bank.select(C, 'INDEX', 'L')
layout.capture_definition(C)
layout.apply_layout(C)
assert set(json.loads(b.survey)['warnings']) == {'INDEX'}
for digit in detect.DIGITS:
    for side in ('L', 'R'):
        bank.select(C, digit, side)
        assert definition.frame(C)['length'] > .03
        assert not b.slots[f'{digit}.{side}'].error, (digit, side, b.slots[f'{digit}.{side}'].error)
bank.select(C, 'MIDDLE', 'L')
layout.capture_definition(C)
layout.apply_layout(C)
bank.select(C, 'INDEX', 'L')
assert definition.frame(C)['length'] > .05
assert len(obj.data.shape_keys.key_blocks) == 10 and obj.data.has_custom_normals
assert hashlib.sha256(path.read_bytes()).hexdigest() == disk
print('REAL_X_FINGER_BANK_PASS', json.dumps(json.loads(b.survey)['warnings']), flush=True)
character_designer.unregister()
