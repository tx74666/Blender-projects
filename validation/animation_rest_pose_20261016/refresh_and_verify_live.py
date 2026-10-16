"""Update only changed animation UI/classes; preserve PropertyGroup instances."""
import ast
import bpy
import bmesh
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sys

folder = Path(r'D:\Blender\Projects\Character\X\validation\animation_rest_pose_20261016')
artist = Path(r'D:\Blender\Projects\Character\X\X.blend')
assert not bpy.app.background and os.getpid() == 24416
assert Path(bpy.data.filepath) == artist
assert bpy.context.mode == 'EDIT_MESH' and bpy.context.object.name == 'Shoes'
addon = sys.modules['character_designer']
ui = sys.modules['character_designer.animation_worklist_ui']
animation = sys.modules['character_designer.animation']
worklist = sys.modules['character_designer.animation_worklist']
assert tuple(addon.bl_info['version']) == (0, 77, 43)
assert not ui.scan_pending() and not ui._collection().running()
assert animation._link_idle()
rig = bpy.context.scene.character_designer_setup.rig
assert rig.name == 'CoshaRig'

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

def witness():
    obj = bpy.context.object
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    mesh = [(tuple(v.co), v.select, v.hide) for v in bm.verts]
    actions = []
    for item in bpy.context.scene.character_designer_animation_worklist.items:
        for action in (item.source_action, item.custom_action):
            if action is None:
                continue
            channels = [(curve.data_path, curve.array_index,
                         [(tuple(k.co), tuple(k.handle_left), tuple(k.handle_right), k.interpolation)
                          for k in curve.keyframe_points])
                        for layer in action.layers for strip in layer.strips
                        for bag in strip.channelbags for curve in bag.fcurves]
            actions.append((action.as_pointer(), digest(channels)))
    return {'mode': bpy.context.mode, 'object': obj.name,
            'mesh_edit_sha256': digest(mesh), 'frame': bpy.context.scene.frame_current,
            'data_pointer': rig.data.as_pointer(),
            'rest_sha256': digest([(b.name, list(map(list, b.matrix_local)), b.parent.name if b.parent else None)
                                   for b in rig.data.bones]),
            'pose_sha256': digest([(pb.name, list(map(list, pb.matrix_basis))) for pb in rig.pose.bones]),
            'active_action': rig.animation_data.action.as_pointer() if rig.animation_data and rig.animation_data.action else None,
            'actions': actions}

before = witness()
# Return the temporary Console to the original Geometry Node editor before saving.
for area in bpy.context.screen.areas:
    if area.type == 'CONSOLE' and area.y < 100:
        area.type = 'NODE_EDITOR'
        area.ui_type = 'GeometryNodeTree'
assert bpy.ops.wm.save_mainfile('EXEC_DEFAULT') == {'FINISHED'}
backup = folder / 'artist_before_rest_display.blend'
assert not backup.exists()
shutil.copy2(artist, backup)
backup_hash = hashlib.sha256(backup.read_bytes()).hexdigest()
assert backup_hash == hashlib.sha256(artist.read_bytes()).hexdigest()

old_work_classes = ui.WORKLIST_CLASSES
old_panel = animation.CHARACTERDESIGNER_PT_animation
old_restore = ui.CHARACTERDESIGNER_OT_worklist_restore_main_rig
old_use = ui.CHARACTERDESIGNER_OT_worklist_use_main_rig
old_list = ui.CHARACTERDESIGNER_UL_animation_worklist
old_ui_globals = ui.__dict__.copy()
old_animation_globals = animation.__dict__.copy()
old_work_globals = worklist.__dict__.copy()
old_main_classes = addon.CLASSES
old_main_work = addon.WORKLIST_CLASSES
old_main_animation = addon.ANIMATION_CLASSES
registered, unregistered = [], []

def replace_class(old, new):
    if old is not None:
        bpy.utils.unregister_class(old)
        unregistered.append(old)
    bpy.utils.register_class(new)
    registered.append(new)

try:
    importlib.invalidate_caches()
    importlib.import_module('character_designer.animation_rest_pose')
    importlib.reload(worklist)
    ui_path = Path(ui.__file__)
    tree = ast.parse(ui_path.read_bytes(), filename=str(ui_path))
    names = {'_active_side', '_draw_worklist_actions', 'draw_worklist',
             'CHARACTERDESIGNER_OT_worklist_pose_position',
             'CHARACTERDESIGNER_OT_worklist_restore_main_rig',
             'CHARACTERDESIGNER_OT_worklist_use_main_rig'}
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
             and node.name in names]
    assert {node.name for node in nodes} == names
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ui_path), 'exec', dont_inherit=True), ui.__dict__)
    replace_class(old_use, ui.CHARACTERDESIGNER_OT_worklist_use_main_rig)
    replace_class(old_restore, ui.CHARACTERDESIGNER_OT_worklist_restore_main_rig)
    replace_class(None, ui.CHARACTERDESIGNER_OT_worklist_pose_position)
    bpy.utils.unregister_class(old_list)
    unregistered.append(old_list)
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'WORKLIST_CLASSES' for t in node.targets))
    exec(compile(ast.Module(body=[assignment], type_ignores=[]), str(ui_path), 'exec', dont_inherit=True), ui.__dict__)
    index = addon.CLASSES.index(old_work_classes[0])
    assert addon.CLASSES[index:index + len(old_work_classes)] == old_work_classes
    addon.CLASSES = addon.CLASSES[:index] + ui.WORKLIST_CLASSES + addon.CLASSES[index + len(old_work_classes):]
    addon.WORKLIST_CLASSES = ui.WORKLIST_CLASSES
    panel_tree = ast.parse(Path(animation.__file__).read_bytes())
    panel_node = next(node for node in panel_tree.body if isinstance(node, ast.ClassDef)
                      and node.name == 'CHARACTERDESIGNER_PT_animation')
    exec(compile(ast.Module(body=[panel_node], type_ignores=[]), animation.__file__, 'exec', dont_inherit=True), animation.__dict__)
    panel = animation.CHARACTERDESIGNER_PT_animation
    replace_class(old_panel, panel)
    animation.ANIMATION_CLASSES = tuple(panel if cls is old_panel else cls for cls in animation.ANIMATION_CLASSES)
    addon.ANIMATION_CLASSES = animation.ANIMATION_CLASSES
    addon.CLASSES = tuple(panel if cls is old_panel else cls for cls in addon.CLASSES)
    assert witness() == before, 'UI refresh changed artist content'
except Exception:
    for cls in reversed(registered):
        bpy.utils.unregister_class(cls)
    ui.__dict__.clear()
    ui.__dict__.update(old_ui_globals)
    animation.__dict__.clear()
    animation.__dict__.update(old_animation_globals)
    worklist.__dict__.clear()
    worklist.__dict__.update(old_work_globals)
    addon.CLASSES, addon.WORKLIST_CLASSES, addon.ANIMATION_CLASSES = old_main_classes, old_main_work, old_main_animation
    for cls in unregistered:
        bpy.utils.register_class(cls)
    raise

addon.bl_info['version'] = (0, 77, 44)
addon.ADDON_LOADED_SIGNATURE = addon._source_signature()
addon.ADDON_REFRESH_LAST_STATE = False
from character_designer import animation_rest_pose as rest
assert bpy.ops.character_designer.worklist_pose_position(position='REST') == {'FINISHED'}
assert rest.is_rest(rig) and witness() == before
assert bpy.ops.character_designer.worklist_pose_position(position='POSE') == {'FINISHED'}
assert not rest.is_rest(rig) and witness() == before
assert bpy.ops.character_designer.worklist_pose_position(position='REST') == {'FINISHED'}
assert rest.is_rest(rig) and witness() == before
assert bpy.ops.wm.save_mainfile('EXEC_DEFAULT') == {'FINISHED'}
for area in bpy.context.screen.areas:
    area.tag_redraw()
report = {'passed': True, 'pid': os.getpid(), 'version': addon.bl_info['version'],
          'filepath': bpy.data.filepath, 'backup': str(backup), 'backup_sha256': backup_hash,
          'artist_sha256': hashlib.sha256(artist.read_bytes()).hexdigest(),
          'before': before, 'after': witness(), 'pose_position': rig.data.pose_position,
          'rest_pose_roundtrip_passed': True, 'save_result': 'FINISHED',
          'property_groups_reregistered': False, 'full_addon_refresh': False,
          'scope': 'Animation UI operators/panel and worklist functions only'}
(folder / 'live_delivery.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
