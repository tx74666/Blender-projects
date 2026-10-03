"""Read-only real-scene switch profiling; never saves the loaded project."""
import cProfile
import hashlib
import json
import pstats
import sys
import time
from pathlib import Path

import bpy

ROOT = Path('D:/MyRepository/Blender-addons-by-Randy')
sys.path.insert(0, str(ROOT / 'addons'))
import character_designer
from character_designer import body_original_mode as mode, bone_display as display
from character_designer import forearm_twist as twist

character_designer.register()
bpy.ops.wm.open_mainfile(filepath='D:/Blender/Projects/Character/X/X.blend')
rig = bpy.data.objects['CoshaRig']
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
for obj in bpy.context.selected_objects:
    obj.select_set(False)
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
if mode.active(rig):
    mode.leave(bpy.context, rig)


def protected():
    state = []
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            mesh = obj.data
            state.append((obj.name, [(tuple(v.co), [(g.group, g.weight) for g in v.groups]) for v in mesh.vertices],
                          [tuple(e.vertices) for e in mesh.edges], [tuple(p.vertices) for p in mesh.polygons],
                          [(k.name, [tuple(p.co) for p in k.data]) for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else [],
                          [(g.name, g.index) for g in obj.vertex_groups]))
        elif obj.type == 'ARMATURE':
            state.append((obj.name, mode._channels(obj), display._snapshot(obj),
                          [(b.name, tuple(tuple(row) for row in b.matrix_local), b.parent.name if b.parent else None)
                           for b in obj.data.bones]))
    return hashlib.sha256(repr(state).encode()).hexdigest()


before = protected()
calls = 0
original_update = mode._update
mirror_calls = []
original_mirror = twist.mirror_ring_pairs


def counted_mirror(*args):
    try:
        result = original_mirror(*args)
    except ValueError as exc:
        mirror_calls.append({'success': False, 'message': str(exc)})
        raise
    mirror_calls.append({'success': True})
    return result


twist.mirror_ring_pairs = counted_mirror


def counted_update(*args):
    global calls
    calls += 1
    return original_update(*args)


mode._update = counted_update
profile = cProfile.Profile()
results = []
for cycle in range(2):
    profile.enable()
    start, count = time.perf_counter(), calls
    mode.enter(bpy.context, rig)
    entered = time.perf_counter()
    enter_calls = calls - count
    count = calls
    mode.leave(bpy.context, rig)
    end = time.perf_counter()
    profile.disable()
    results.append({'cycle': cycle, 'original_seconds': entered - start, 'controls_seconds': end - entered,
                    'original_updates': enter_calls, 'controls_updates': calls - count})
    assert protected() == before, 'Protected scene content changed in no-edit roundtrip'
stats = pstats.Stats(profile).sort_stats('cumulative')
stats.print_stats(25)
report = {'version': list(character_designer.bl_info['version']), 'cycles': results, 'protected_scene_unchanged': True,
          'native_bones': len(mode.poses.native_rest(rig)), 'total_bones': len(rig.data.bones),
          'mirror_calls': mirror_calls, 'forearm_errors': dict(twist._ERRORS)}
print('SWITCH_PERFORMANCE', json.dumps(report))
destination = Path(sys.argv[sys.argv.index('--') + 1])
destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
