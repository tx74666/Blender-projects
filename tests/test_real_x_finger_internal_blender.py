"""Disposable real X: one-click straight axes on all ten fingers, no Confirm."""
import hashlib
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_real_x_finger_layout_blender import top_strip, character_designer, layout
from character_designer import finger_bank as bank, finger_definition as definition, finger_internal as internal, finger_flex as flex

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
obj.active_shape_key_index = 1
for modifier in list(obj.modifiers):
    if modifier.type == 'ARMATURE': obj.modifiers.remove(modifier)
obj.vertex_groups.clear()
bpy.ops.object.mode_set(mode='EDIT')
C.tool_settings.mesh_select_mode = (False, False, True)
before, objects = layout.fingerprint(obj), set(bpy.data.objects.keys())
digits = (('THUMB', 'thumb'), ('INDEX', 'f_index'), ('MIDDLE', 'f_middle'), ('RING', 'f_ring'), ('PINKY', 'f_pinky'))
for side in ('L', 'R'):
    for digit, name in digits:
        # Ground truth only chooses test faces. Runtime identification is unbound.
        top_strip(obj, rig, side, name)
        assert bpy.ops.character_designer.finger_setup(action='CAPTURE') == {'FINISHED'}
        b = obj.character_designer_finger_bank
        assert b.active == digit+'.'+side
        assert all(b.slots[digit+'.'+s].guide.confirmed for s in ('L', 'R'))
        for s in ('L', 'R'):
            record = json.loads(b.slots[digit+'.'+s].guide.record)
            assert record['key'] == record['basis_key'] and len(record['internal']['path']) == 2
            bm = definition._snapshot(obj, record['basis_key'])
            try:
                volume = internal.Volume(bm, record['body'])
                a, z = map(Vector, record['internal']['path'])
                assert volume.certify((a, z), record['internal']['margin']) is not None
                assert all(volume.inside(a.lerp(z, i/100)) for i in range(101))
            finally: bm.free()
        assert not json.loads(b.survey)['warnings']
        assert layout.fingerprint(obj) == before and obj.active_shape_key_index == 1
        assert set(bpy.data.objects.keys()) == objects
        print('REAL_INTERNAL_AXIS', digit, side, 'coverage', round(record['internal']['coverage'], 4), flush=True)

# Existing Roll consumes the automatically obtained strip normal and the axis,
# without adding Confirm or Set Top Surface. It still changes roll only.
for digit, name in digits:
    bank.select(C, digit, 'L')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    C.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones: bone.select = bone.name.startswith(name+'.') and bone.name.endswith('.L')
    assert flex.apply(C) == 6
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    C.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    print('REAL_INTERNAL_PAIRED_ROLL', digit, flush=True)

# Actual topology editing retains the pre-existing Basis-only write guard.
bpy.ops.object.mode_set(mode='OBJECT')
obj.active_shape_key_index = 0
bpy.ops.object.mode_set(mode='EDIT')
for digit in ('INDEX', 'MIDDLE'):
    bank.select(C, digit, 'L')
    original = definition.frame(C, purpose='TOPOLOGY')
    layout.capture_definition(C)
    recipe = json.loads(layout.state(C).record)
    assert abs(recipe['length']-original['length']) < 1e-6
    layout.apply_layout(C)
assert set(json.loads(b.survey)['warnings']) == {'INDEX', 'MIDDLE'}
for digit, _ in digits:
    bank.select(C, digit, 'L')
    assert definition.frame(C)['internal'] and not b.slots[digit+'.L'].error
assert len(obj.data.shape_keys.key_blocks) == 10 and obj.data.has_custom_normals
assert hashlib.sha256(path.read_bytes()).hexdigest() == disk
print('REAL_X_INTERNAL_AXES_PASS', flush=True)
character_designer.unregister()
