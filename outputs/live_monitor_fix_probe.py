"""Apply two validated callback bodies in-place and profile the user's edit view.

Run once in Blender's Python Console. No add-on unregister, data edit or save.
Timer/handler identities are retained when changing function bodies.
"""
import ast
import cProfile
import hashlib
import io
import json
import pstats
import statistics
import time
from pathlib import Path

import bpy
from mathutils import Quaternion
import character_designer as cd
from character_designer import finger_workflow_ui as ui, finger_layout as layout

OUT = Path(r'D:\Blender\Projects\Character\X\outputs\monitor_fix_20260921')
OUT.mkdir(exist_ok=True)
obj = bpy.context.object
area = bpy.context.area
assert obj and obj.type == 'MESH' and obj.name == 'Cosha'
assert obj.mode == 'OBJECT' and area.type == 'CONSOLE'
assert cd.bl_info['version'] == (0, 61, 42), cd.bl_info['version']
source = Path(ui.__file__)
canonical = Path(r'D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\finger_workflow_ui.py')
assert source.read_bytes() == canonical.read_bytes()
tree = ast.parse(source.read_text(encoding='utf-8'))
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'_show', '_refresh'}]
assert len(nodes) == 2
compiled = dict(ui.__dict__)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), compiled)
old_codes = {n.name: getattr(ui, n.name).__code__ for n in nodes}
for node in nodes:
    target, replacement = getattr(ui, node.name), compiled[node.name]
    assert target.__code__.co_argcount == replacement.__code__.co_argcount
    assert target.__code__.co_freevars == replacement.__code__.co_freevars
for node in nodes:
    getattr(ui, node.name).__code__ = compiled[node.name].__code__
cd.bl_info['version'] = (0, 61, 43)

baseline = layout.fingerprint(obj)
file_before = hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
eye_before = obj.character_designer_finger_workflow.preview_enabled
selection_before = sorted(o.name for o in bpy.context.selected_objects)
shape_values = [(k.name, k.value) for k in obj.data.shape_keys.key_blocks]
original_rotation = None
view = None
profile = cProfile.Profile()
ticks = []
draws = 0
started = 0.
draw_handle = None
done = False
report = dict(version=list(cd.bl_info['version']), object=obj.name,
              active=obj.character_designer_finger_bank.active,
              vertices=len(obj.data.vertices), keys=len(shape_values),
              pairs=[p.name for p in obj.character_designer_finger_workflow.pairs],
              function_patch=list(old_codes), baseline_fingerprint=baseline,
              file_before=file_before, eye_before=eye_before)


def draw_counter():
    global draws
    draws += 1


def finish(error=None):
    global done
    if done:
        return None
    done = True
    profile.disable()
    elapsed = time.perf_counter()-started
    if draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handle, 'WINDOW')
    if view is not None and original_rotation is not None:
        view.view_rotation = original_rotation
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    area.type = 'VIEW_3D'
    profile.dump_stats(str(OUT/'after.prof'))
    stats = pstats.Stats(profile)
    relevant = []
    for (file, line, name), (primitive, calls, total, cumulative, callers) in stats.stats.items():
        if 'character_designer' in file and name in {'_refresh', '_show', 'show', 'verify', 'signature', 'fingerprint'}:
            relevant.append(dict(file=file, line=line, name=name, calls=calls,
                                 own_seconds=total, cumulative_seconds=cumulative))
    stream = io.StringIO()
    pstats.Stats(profile, stream=stream).strip_dirs().sort_stats('cumtime').print_stats(35)
    (OUT/'after_profile.txt').write_text(stream.getvalue(), encoding='utf-8')
    after = layout.fingerprint(obj)
    report.update(elapsed_seconds=elapsed, error=error, profile_functions=relevant,
                  profiled_cpu_seconds=stats.total_tt, draw_callbacks=draws, redraw_ticks=len(ticks),
                  median_tick_seconds=statistics.median(ticks) if ticks else None,
                  maximum_tick_seconds=max(ticks) if ticks else None,
                  eye_after=obj.character_designer_finger_workflow.preview_enabled,
                  status=obj.character_designer_finger_workflow.status,
                  pending=ui._refresh_request is not None,
                  fingerprint_after=after, mesh_unchanged=baseline == after,
                  selected_unchanged=selection_before == sorted(o.name for o in bpy.context.selected_objects),
                  shape_values_unchanged=shape_values == [(k.name, k.value) for k in obj.data.shape_keys.key_blocks],
                  file_after=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
                  mode_after=obj.mode, editor_after=area.type)
    report['saved_file_unchanged'] = report['file_after'] == file_before
    (OUT/'live_after.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('MONITOR_FIX_PROBE_DONE', json.dumps(report))
    return None


def tick():
    global last_tick
    try:
        now = time.perf_counter()
        ticks.append(now-last_tick)
        last_tick = now
        elapsed = now-started
        if elapsed >= 8.:
            return finish()
        # Exercise navigation redraw without touching mesh/selection/settings.
        view.view_rotation = Quaternion((0, 0, 1), .025*__import__('math').sin(elapsed*2))*original_rotation
        area.tag_redraw()
        return .05
    except Exception as exc:
        return finish(repr(exc))


def start():
    global view, original_rotation, started, last_tick, draw_handle
    try:
        area.type = 'VIEW_3D'
        view = area.spaces.active.region_3d
        original_rotation = view.view_rotation.copy()
        draw_handle = bpy.types.SpaceView3D.draw_handler_add(draw_counter, (), 'WINDOW', 'POST_PIXEL')
        started = last_tick = time.perf_counter()
        profile.enable()
        bpy.ops.object.mode_set(mode='EDIT')
        ui.refresh(bpy.context)
        bpy.app.timers.register(tick, first_interval=.05)
    except Exception as exc:
        finish(repr(exc))
    return None


bpy.app.timers.register(start, first_interval=.25)
print('MONITOR_FIX_PROBE_SCHEDULED')
