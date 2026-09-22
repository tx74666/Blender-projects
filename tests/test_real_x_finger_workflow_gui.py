"""Disposable real-model View3D snapshots after the integrated workflow tests."""
import hashlib
import json
import math
import sys
import traceback
from pathlib import Path
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_real_x_finger_workflow_blender as test
from character_designer import finger_bank as bank, finger_definition as definition, finger_workflow_ui as ui

OUTPUT = Path(sys.argv[sys.argv.index('--')+1])
STATE = {}


def later(fn, seconds=1):
    def wrapped():
        try: fn()
        except Exception as exc:
            traceback.print_exc(); OUTPUT.write_text(json.dumps({'status':'FAIL', 'error':str(exc)}), encoding='utf-8')
            bpy.ops.wm.quit_blender()
    bpy.app.timers.register(wrapped, first_interval=seconds)


def setup():
    bpy.context.preferences.filepaths.use_auto_save_temporary_files = False
    bpy.context.preferences.filepaths.temporary_directory = str(OUTPUT.parent)
    test.main()
    c = bpy.context
    obj, rig = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
    STATE['poses'] = {b.name:(b.matrix_basis.copy(), b.rotation_mode) for b in rig.pose.bones}
    STATE['disk'] = hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
    for other in c.view_layer.objects: other.hide_set(other != obj)
    obj.select_set(True); c.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT'); bank.select(c, 'INDEX', 'L')
    frame = definition.frame(c)
    window = c.window_manager.windows[0]
    area = max((a for a in window.screen.areas if a.type == 'VIEW_3D'), key=lambda a:a.width*a.height)
    region = next(r for r in area.regions if r.type == 'WINDOW')
    for value in ('PRESS','RELEASE'): window.event_simulate(type='ESC', value=value, x=region.x+region.width//2, y=region.y+region.height//2)
    with c.temp_override(window=window, area=area, region=region): bpy.ops.screen.screen_full_area(use_hide_panels=False)
    area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
    STATE.update(window=window, area=area, frame=frame, index=0)
    space = area.spaces.active
    space.show_region_ui = True
    c.window_manager.character_designer.ui_page = 'RIG'
    c.window_manager.character_designer.rig_section = 'BODY'
    space.region_3d.view_location = frame['midpoint']
    space.region_3d.view_distance = frame['length']*2
    space.region_3d.view_rotation = (-frame['bend']).to_track_quat('Z','Y')
    space.region_3d.view_perspective = 'ORTHO'
    space.overlay.show_floor = False
    ui.show(c)
    later(rings)


def rings():
    area = STATE['area']
    next(r for r in area.regions if r.type == 'UI').active_panel_category = 'Character Designer'
    # Scroll this disposable sidebar down so the complete shared workflow is visible.
    region = next(r for r in area.regions if r.type == 'UI')
    for _ in range(8): STATE['window'].event_simulate(type='WHEELDOWNMOUSE', value='PRESS', x=region.x+region.width//2, y=region.y+region.height//2)
    later(rings_shot)


def rings_shot():
    bpy.ops.screen.screenshot(filepath=str(OUTPUT.with_name('real-joint-rings.png')))
    ui.hide(); bpy.ops.object.mode_set(mode='OBJECT')
    space = STATE['area'].spaces.active
    space.show_region_ui = False
    frame = STATE['frame']
    # Side/three-quarter view exposes inward joint compression.
    view = (frame['direction'].cross(frame['bend'])-frame['bend']*.45).normalized()
    space.region_3d.view_rotation = view.to_track_quat('Z','Y')
    space.region_3d.view_location = frame['midpoint']+frame['bend']*frame['length']*.18
    later(pose)


def pose():
    rig = bpy.data.objects['CoshaRig']
    angle, multiple = ((0,False),(45,False),(90,False),(45,True))[STATE['index']]
    for i in (2,3):
        b = rig.pose.bones[f'f_index.{i:02d}.L']
        b.rotation_mode='XYZ'; b.rotation_euler=(math.radians(angle) if i==2 or multiple else 0,0,0)
    bpy.context.view_layer.update()
    later(pose_shot)


def pose_shot():
    index = STATE['index']
    bpy.ops.screen.screenshot(filepath=str(OUTPUT.with_name(f'real-pose-{index}.png')))
    if index < 3:
        STATE['index']+=1; later(pose)
    else:
        for b in bpy.data.objects['CoshaRig'].pose.bones:
            b.rotation_mode=STATE['poses'][b.name][1]; b.matrix_basis=STATE['poses'][b.name][0]
        assert hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()==STATE['disk']
        OUTPUT.write_text(json.dumps({'status':'PASS','screenshots':5}), encoding='utf-8')
        bpy.ops.wm.quit_blender()


later(setup)
