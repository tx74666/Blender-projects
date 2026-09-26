import bpy
import json
from pathlib import Path

area = bpy.context.area
workspace = bpy.context.workspace
assert area.type == 'CONSOLE'
assert workspace.name == 'Modeling'
assert workspace.use_filter_by_owner
report = {
    'workspace': workspace.name,
    'filter_enabled': workspace.use_filter_by_owner,
    'owners_before': list(workspace.owner_ids.keys()),
}
if 'pose_library' not in workspace.owner_ids:
    workspace.owner_ids.new('pose_library')
report['owners_after'] = list(workspace.owner_ids.keys())
report['blend_saved'] = False
Path(r'D:\Blender\Projects\Character\X\outputs\asset_library_organization\pose_menu_repair.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('Pose Library is now visible in the Modeling workspace.')
for visible_area in bpy.context.screen.areas:
    visible_area.tag_redraw()

def restore_image_editor():
    area.ui_type = 'IMAGE_EDITOR'
    area.spaces.active.ui_mode = 'PAINT'
    area.tag_redraw()

bpy.app.timers.register(restore_image_editor, first_interval=.25)
