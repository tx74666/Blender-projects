"""Definition -> Basis ring/paired-roll consumers on disposable X.blend data."""
import hashlib
import json
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_real_x_finger_layout_blender import top_strip, character_designer, layout
from character_designer import finger_definition as definition, finger_flex as flex


def activate(obj, mode):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode=mode)


path = Path(bpy.data.filepath)
disk = hashlib.sha256(path.read_bytes()).hexdigest()
character_designer.register()
obj, rig = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
activate(obj, 'OBJECT')
original = obj.data.copy()
rig_before = [(b.name, tuple(b.head_local), tuple(b.tail_local)) for b in rig.data.bones]
results = []
for side in ('L', 'R'):
    for finger in ('f_index', 'f_middle', 'f_ring', 'f_pinky', 'thumb'):
        activate(obj, 'OBJECT')
        definition.clear(bpy.context)
        layout.clear(bpy.context)
        obj.data = original.copy()
        obj.active_shape_key_index = 1
        activate(obj, 'EDIT')
        bpy.context.tool_settings.mesh_select_mode = (False, False, True)
        count = top_strip(obj, rig, side, finger)
        before = layout.fingerprint(obj)
        frame = definition.capture(bpy.context)
        assert not frame['basis'] and frame['length'] > 0
        assert layout.fingerprint(obj) == before and obj.active_shape_key_index == 1
        definition.basis_reference(bpy.context)
        definition.confirm(bpy.context)
        assert layout.fingerprint(obj) == before and obj.active_shape_key_index == 1
        activate(obj, 'OBJECT')
        obj.active_shape_key_index = 0
        activate(obj, 'EDIT')
        before = layout.fingerprint(obj)
        frame = definition.frame(bpy.context)
        layout.capture_definition(bpy.context)
        assert layout.fingerprint(obj) == before
        s = layout.state(bpy.context)
        s.joint_one, s.joint_two = .35, .69
        s.width_one, s.width_two = .022, .02
        s.three_rings, s.between_rings = True, 1
        added = layout.apply_layout(bpy.context)
        once = layout.fingerprint(obj)
        layout.apply_layout(bpy.context)
        assert layout.fingerprint(obj) == once
        assert len(obj.data.shape_keys.key_blocks) == 10 and obj.data.has_custom_normals
        # Reuse the same definition after topology changes, without recapture.
        assert abs(definition.frame(bpy.context)['length']-frame['length']) < 1e-6
        activate(rig, 'EDIT')
        for bone in rig.data.edit_bones: bone.select = bone.name.startswith(finger+'.') and bone.name.endswith('.'+side)
        calibrated = flex.apply(bpy.context)
        assert calibrated == 6
        results.append({'finger': f'{finger}.{side}', 'selected_faces': count,
                        'length': frame['length'], 'added': added, 'paired_bones': calibrated})
activate(obj, 'OBJECT')
assert rig_before == [(b.name, tuple(b.head_local), tuple(b.tail_local)) for b in rig.data.bones]
assert hashlib.sha256(path.read_bytes()).hexdigest() == disk
print('REAL_X_FINGER_DEFINITION_PASS', json.dumps(results), flush=True)
character_designer.unregister()
