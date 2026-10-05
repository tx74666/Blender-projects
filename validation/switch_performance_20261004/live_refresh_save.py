"""Refresh checked 0.75.2 in paused X, preserve current artist input, save.

Timings remain the isolated paired evidence; this does not pose-benchmark or
roundtrip the artist. Run only from X's native Python Console after coordination.
"""
import ast
import datetime
import hashlib
import importlib
import json
import math
import sys
import time
import traceback
from array import array
from pathlib import Path
from types import SimpleNamespace
import bpy

FOLDER = Path(__file__).resolve().parent
ARTIST = (FOLDER.parents[1] / 'X.blend').resolve()
PROBE = FOLDER.parent / 'original_calibration_20261004' / 'probe_current.py'
VALIDATOR = FOLDER.parent / 'native_fk_controls_20261004' / 'validate_native_fk.py'
CHANNELS = ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')
POSE_TOLERANCE, SURFACE_TOLERANCE, REST_TOLERANCE = 2e-4, 1e-4, 2e-6


def extract(path, wanted):
    parsed = ast.parse(path.read_text(encoding='utf-8'))
    nodes = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {node.name for node in nodes} != wanted:
        raise RuntimeError('Reviewed native read-only interface changed.')
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), globals())


extract(FOLDER.parent / 'native_fk_controls_20261004' / 'live_native_fk.py',
        {'modules', 'installed_source', 'extracted', 'readers', 'no_preview',
         'selection', 'require_selection'})
extract(FOLDER.parent / 'fk_ik_display_20261004' / 'live_display.py',
        {'pose_inputs', 'require_pose_inputs', 'require_finite_state', 'verify_native'})


def main(facts):
    if bpy.app.background or bpy.context.area.type != 'CONSOLE' or Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('Use only the paused X native Python Console.')
    area = bpy.context.area
    runtime = modules()
    source = installed_source(runtime)
    rig = bpy.context.view_layer.objects.active
    if rig is None or rig.name != 'CoshaRig' or bpy.context.mode not in {'OBJECT', 'POSE'}:
        raise RuntimeError('Keep CoshaRig active in Object/Pose mode.')
    no_preview(runtime, rig)
    validation = json.loads((FOLDER / 'compare_switches_reverse.json').read_text(encoding='utf-8'))
    if not validation.get('passed') or validation['version'] != [0, 75, 2]:
        raise RuntimeError('Final 0.75.2 paired validation has not passed.')
    read = readers(runtime)
    selected = selection(rig)
    frame = bpy.context.scene.frame_current
    auto_key = bpy.context.scene.tool_settings.use_keyframe_insert_auto
    inputs = pose_inputs(rig)
    native_rest = runtime.control_pose_assets.native_rest(rig)
    runtime.limb_ik_fk._update(bpy.context, rig)
    require_pose_inputs(rig, inputs, facts, 'initial_evaluation')
    if runtime.control_pose_assets.native_rest(rig) != native_rest:
        raise RuntimeError('Native Rest changed during initial evaluation.')
    names = tuple(native_rest)
    surfaces = runtime.body_setup_removal._bound_surfaces(bpy.context, rig)
    before = read.states(rig, set(), set(), names)
    from character_designer import bone_display
    display_before = bone_display._snapshot(rig)
    facts.update({'runtime': bpy.app.version_string, 'source': str(source),
                  'version_before': list(runtime.addon.bl_info['version']),
                  'artist_before': read.fingerprint(ARTIST), 'selection_before': selected,
                  'frame_before': frame, 'auto_key_before': auto_key})
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    recovery = FOLDER / ('X_before_switch_perf_' + stamp + '.blend')
    saved_copy = bpy.ops.wm.save_as_mainfile(filepath=str(recovery), copy=True, check_existing=False)
    if saved_copy != {'FINISHED'} or Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('Independent current recovery copy failed.')
    facts['checkpoint'] = read.fingerprint(recovery)
    facts['phase'] = 'refresh'
    runtime.addon._reload_addon_deferred()
    runtime = modules()
    if installed_source(runtime) != source or tuple(runtime.addon.bl_info['version']) != (0,75,2):
        raise RuntimeError('Refresh did not load installed 0.75.2.')
    if runtime.addon.ADDON_REFRESH_LAST_ERROR:
        raise RuntimeError(runtime.addon.ADDON_REFRESH_LAST_ERROR)
    runtime.addon._validate_registration_integrity()
    read = readers(runtime)
    verify_native(read, facts, 'after_refresh', rig, before, surfaces, names, inputs)
    if bone_display._snapshot(rig) != display_before:
        raise RuntimeError('Artist bone display state changed during refresh.')
    require_selection(rig, selected)
    if (bpy.context.scene.frame_current != frame
            or bpy.context.scene.tool_settings.use_keyframe_insert_auto != auto_key):
        raise RuntimeError('Frame or Auto Key preference changed.')
    # Restore the observed temporary editor before saving its artist workspace.
    area.type = 'NODE_EDITOR'
    area.ui_type = 'GeometryNodeTree'
    facts['phase'] = 'save_artist'
    result = bpy.ops.wm.save_mainfile()
    facts['save_result'] = sorted(result)
    if result != {'FINISHED'} or Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('Native artist save did not finish.')
    facts['artist_after'] = read.fingerprint(ARTIST)
    verify_native(read, facts, 'after_save', rig, before, surfaces, names, inputs)
    require_selection(rig, selected)
    facts.update({'status': 'passed', 'phase': 'complete', 'saved': True,
                  'version_after': list(runtime.addon.bl_info['version']),
                  'selection_after': selection(rig), 'frame_after': bpy.context.scene.frame_current,
                  'auto_key_after': bpy.context.scene.tool_settings.use_keyframe_insert_auto,
                  'display_exact': bone_display._snapshot(rig) == display_before})


facts = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'status': 'starting', 'saved': False, 'phase': 'preflight'}
try:
    main(facts)
except Exception as exc:
    facts.update({'status': 'failed', 'error': str(exc), 'traceback': traceback.format_exc()})
finally:
    facts['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (FOLDER / 'live_refresh_save.json').write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
    print('LIVE_SWITCH_PERF_REFRESH', facts['status'], facts.get('phase'), facts.get('error', ''), flush=True)
