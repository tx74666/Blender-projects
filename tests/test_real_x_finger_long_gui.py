"""Disposable GUI reproduction: ten-face knuckle-to-tip capture on real X."""
import hashlib
import json
import sys
import traceback
from pathlib import Path
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_real_x_finger_long_internal_blender import long_strip, character_designer, layout, bank, definition
from character_designer import finger_definition_ui as ui

OUTPUT = Path(sys.argv[sys.argv.index('--')+1])
STATE = {}


def finish(error=None):
    OUTPUT.write_text(json.dumps({'status': 'FAIL' if error else 'PASS', 'error': str(error) if error else None,
                                'version': character_designer.bl_info['version']}, indent=2), encoding='utf-8')
    if error: traceback.print_exc()
    bpy.ops.wm.quit_blender()


def guarded(fn):
    def wrapped():
        try: return fn()
        except Exception as exc: finish(exc)
    return wrapped


@guarded
def setup():
    character_designer.register()
    bpy.context.preferences.filepaths.use_auto_save_temporary_files = False
    bpy.context.preferences.filepaths.temporary_directory = str(OUTPUT.parent)
    STATE['path'] = Path(bpy.data.filepath)
    STATE['disk'] = hashlib.sha256(STATE['path'].read_bytes()).hexdigest()
    c = bpy.context
    if c.object and c.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj, rig = bpy.data.objects['Cosha'], bpy.data.objects['CoshaRig']
    for other in c.view_layer.objects: other.hide_set(other != obj)
    obj.select_set(True)
    c.view_layer.objects.active = obj
    obj.active_shape_key_index = 0
    bpy.ops.object.mode_set(mode='EDIT')
    c.tool_settings.mesh_select_mode = (False, False, True)
    STATE['digit'] = 'RING' if '--ring' in sys.argv else 'INDEX'
    assert long_strip(obj, rig, 'L', 'f_ring' if '--ring' in sys.argv else 'f_index') == 10
    STATE['before'] = layout.fingerprint(obj)
    window = c.window_manager.windows[0]
    area = max((a for a in window.screen.areas if a.type == 'VIEW_3D'), key=lambda a: a.width*a.height)
    region = next(r for r in area.regions if r.type == 'WINDOW')
    STATE.update(window=window, area=area, region=region)
    c.window_manager.character_designer.ui_page = 'RIG'
    c.window_manager.character_designer.rig_section = 'BODY'
    area.spaces.active.show_region_ui = True
    # Dismiss the file's untrusted-script notification, never enable scripts.
    for value in ('PRESS', 'RELEASE'):
        window.event_simulate(type='ESC', value=value, x=region.x+region.width//2, y=region.y+region.height//2)
    bpy.app.timers.register(capture, first_interval=1)


@guarded
def capture():
    with bpy.context.temp_override(window=STATE['window'], area=STATE['area'], region=STATE['region']):
        assert bpy.ops.character_designer.finger_setup(action='CAPTURE') == {'FINISHED'}
    bpy.app.timers.register(captured, first_interval=2)


@guarded
def captured():
    obj = bpy.context.edit_object
    s = definition.state(bpy.context)
    record = json.loads(s.record)
    assert s.confirmed and record.get('body', {}).get('root_extension'), (obj.character_designer_finger_bank.status, record.keys())
    assert not obj.character_designer_finger_bank.status
    assert not obj.character_designer_finger_bank.slots[STATE['digit']+'.R'].error
    assert layout.fingerprint(obj) == STATE['before']
    data = definition.frame(bpy.context)
    normal = Vector(record['surface'].get('centering', {}).get('normal') or record['basis'].get('normal') or (0, 0, 1))
    normal = (obj.matrix_world.to_3x3().inverted().transposed() @ normal).normalized()
    space = STATE['area'].spaces.active
    space.region_3d.view_location = data['midpoint']
    space.region_3d.view_distance = data['length']*2.8
    space.region_3d.view_rotation = normal.to_track_quat('Z', 'Y')
    space.region_3d.view_perspective = 'ORTHO'
    space.overlay.show_floor = False
    next(r for r in STATE['area'].regions if r.type == 'UI').active_panel_category = 'Character Designer'
    ui.show()
    bpy.app.timers.register(screenshot, first_interval=1)


@guarded
def screenshot():
    assert ui.cached_frame(bpy.context)[0]
    bpy.ops.screen.screenshot(filepath=str(OUTPUT.with_suffix('.png')))
    assert hashlib.sha256(STATE['path'].read_bytes()).hexdigest() == STATE['disk']
    finish()


bpy.app.timers.register(setup, first_interval=1)
