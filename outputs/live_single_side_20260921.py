import json
import time
from pathlib import Path
import bpy
import character_designer as addon
from character_designer import finger_bank as bank, finger_workflow as work
from character_designer import finger_workflow_ui as ui, finger_definition_ui as guides
from character_designer import finger_layout as layout
C = bpy.context
area = C.area
obj = bank.active_object(C)
b = obj.character_designer_finger_bank
state = obj.character_designer_finger_workflow
rig = C.scene.character_designer_setup.rig
original = b.active
before = (obj.data.as_pointer(), layout.fingerprint(obj), state.results,
          tuple((p.name, p.recipe, work.parameters(p)) for p in state.pairs),
          tuple((bone.name, tuple(v for row in bone.matrix_local for v in row)) for bone in rig.data.bones),
          tuple((key.name, key.value) for key in obj.data.shape_keys.key_blocks))
C.view_layer.update()
report = dict(version=addon.bl_info['version'], original=original, sides={})
try:
    if guides.overlays_enabled(C): guides.show(invalidate=False)
    for side in ('L', 'R'):
        b.active = original.split('.')[0]+'.'+side
        start = time.perf_counter()
        ui.show(C)
        guides._display_request = C.scene, obj
        guides._refresh_display()
        report['sides'][side] = dict(
            active=b.active, frames=[f['bank_key'] for f in guides.display_frames(C)],
            planned=list(ui._preview['allocations']),
            visible=ui.joint_preview_visible(C), status=state.status,
            groups=len(ui._preview['groups']), elapsed_ms=(time.perf_counter()-start)*1000)
        assert report['sides'][side]['planned'] == [b.active]
        assert all(key.endswith('.'+side) for key in report['sides'][side]['frames'])
except Exception as exc:
    report['error'] = str(exc)
finally:
    b.active = original
    try:
        ui.show(C)
        guides._display_request = C.scene, obj
        guides._refresh_display()
    except Exception as exc: report['restore_error'] = str(exc)
    after = (obj.data.as_pointer(), layout.fingerprint(obj), state.results,
             tuple((p.name, p.recipe, work.parameters(p)) for p in state.pairs),
             tuple((bone.name, tuple(v for row in bone.matrix_local for v in row)) for bone in rig.data.bones),
             tuple((key.name, key.value) for key in obj.data.shape_keys.key_blocks))
    report['unchanged_mesh_bones_keys_parameters_results'] = before == after
    report['vertices'] = len(obj.data.vertices)
    report['shape_keys'] = len(obj.data.shape_keys.key_blocks)
    Path(r'D:\Blender\Projects\Character\X\outputs\live_single_side_20260921.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    area.type = 'VIEW_3D'
