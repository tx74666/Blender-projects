import bpy
import json
from pathlib import Path

expected = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert Path(bpy.data.filepath).resolve() == expected.resolve(), bpy.data.filepath
rig = bpy.data.objects['CoshaRig']
before = {b.name: b.matrix.copy() for b in rig.pose.bones}
was_hidden = rig.hide_get()
rig.hide_set(False)
bpy.context.view_layer.update()
assert not rig.hide_get()
pose_error = max(abs(b.matrix[i][j] - before[b.name][i][j])
                 for b in rig.pose.bones for i in range(4) for j in range(4))
assert pose_error < 1e-6, pose_error
if bpy.context.area and bpy.context.area.type == 'CONSOLE':
    bpy.context.area.type = 'VIEW_3D'
for screen in bpy.data.screens:
    for area in screen.areas:
        area.tag_redraw()
saved = bpy.ops.wm.save_as_mainfile(filepath=str(expected))
assert 'FINISHED' in saved, saved
report = {'ok': True, 'was_hidden': was_hidden, 'hidden': rig.hide_get(),
          'pose_error': pose_error, 'main_saved': True, 'file': bpy.data.filepath}
(expected.parent / 'outputs/rig/body_setup_0550_display_result.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
print('BODY_DISPLAY_OK', report)
