"""Reviewed current-X display repair only; no artist pose roundtrip."""
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

# Import definition-only readers from the already reviewed GUI validator.
old = FOLDER.parent / 'native_fk_controls_20261004' / 'live_native_fk.py'
tree = ast.parse(old.read_text(encoding='utf-8'))
wanted = {'modules', 'installed_source', 'extracted', 'readers', 'no_preview', 'selection', 'require_selection', 'compare_capture'}
nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
if len(nodes) != len(wanted): raise RuntimeError('GUI reader interface changed')
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(old), 'exec'), globals())


def inspect_display(runtime, rig, facts):
    from character_designer import bone_collections, limb_fk_visuals
    inventory = runtime.limb_ik._validate_inventory(rig)
    mode = runtime.limb_ik_fk_batch.mode_for_keys(rig, inventory)
    if mode != 'FK': raise RuntimeError('Keep the current validated FK mode; no pose matching is authorized here')
    entries = {}
    for key, item in inventory['rigs'].items():
        for name in item['chain']:
            pb = rig.pose.bones[name]
            entry = {'shape': pb.custom_shape.name if pb.custom_shape else None,
                     'hide': pb.bone.hide, 'pose_hide': getattr(pb, 'hide', False),
                     'hide_select': pb.bone.hide_select,
                     'visible_collection': any(c.is_visible_effectively for c in pb.bone.collections)}
            if entry['hide'] or entry['pose_hide'] or entry['hide_select'] or not entry['visible_collection']:
                raise RuntimeError('Native FK bone remains hidden: ' + name)
            if name in item['chain'][:2] and pb.custom_shape is not None:
                raise RuntimeError('Owned ring remains on native FK bone: ' + name)
            entries[name] = entry
        for name in (item['target'].name, item['pole'].name):
            pb = rig.pose.bones[name]
            if not pb.bone.hide or (hasattr(pb, 'hide') and not pb.hide):
                raise RuntimeError('IK helper remains visible in FK: ' + name)
    area = next((a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'), None)
    if area is None: raise RuntimeError('No viewport for the guide check')
    with bpy.context.temp_override(area=area):
        guide_count = len(runtime.limb_ik._direct_pole_guide_segments(bpy.context))
    if guide_count: raise RuntimeError('An FK connecting ray remains visible')
    facts['display'] = {'mode': mode, 'native_bones': entries, 'guide_count': guide_count,
                        'marker': rig.data.get(limb_fk_visuals.NATIVE_DISPLAY_KEY)}


def pose_inputs(rig):
    return {pb.name: {'rotation_mode': pb.rotation_mode,
                     'channels': {field: list(getattr(pb, field)) for field in CHANNELS},
                     'locks': {field: list(getattr(pb, field)) for field in
                               ('lock_location', 'lock_rotation', 'lock_scale')},
                     'lock_rotation_w': pb.lock_rotation_w,
                     'lock_rotations_4d': pb.lock_rotations_4d}
            for pb in rig.pose.bones}


def require_pose_inputs(rig, saved, facts, label):
    current = pose_inputs(rig)
    differences = [name for name in set(saved) | set(current)
                   if saved.get(name) != current.get(name)]
    facts.setdefault('pose_input_checks', {})[label] = {'exact_diffs': sorted(differences)}
    if differences:
        raise RuntimeError(label + ': artist bone transform inputs changed: ' + str(differences))


def require_finite_state(state):
    for field in ('pose', 'skin'):
        for name, values in state[field].items():
            if len(values) != 4 or any(len(row) != 4 for row in values) or any(
                    not math.isfinite(value) for row in values for value in row):
                raise RuntimeError('Invalid evaluated matrix: ' + field + '/' + name)


def verify_native(read, facts, label, rig, before, surfaces, names, inputs):
    current = read.check_preserved(facts, label, rig, before, surfaces, set(), set(), names)
    require_finite_state(current)
    if facts['checks'][label]['native_rest_exact_diffs']:
        raise RuntimeError(label + ': native Rest must stay exact for this display-only operation')
    require_pose_inputs(rig, inputs, facts, label)


def compare_assets(facts, read, current, captured):
    """Gate raw artist data; protect evaluated pose against this native window below.

    Cross-process evaluated matrices are recorded, not used as a pose to restore.
    Their observed difference is not evidence of a confirmed evaluation cause.
    No in-window preservation threshold is changed.
    """
    checks = {name: read.exact_diffs(captured[field], current[field])
              for name, field in (('mesh_exact_diffs', 'meshes'),
                                  ('native_rest_exact_diffs', 'rest'),
                                  ('hair_dress_exact_diffs', 'hair_dress'),
                                  ('animation_exact_diffs', 'animation'))}
    checks.update({name + '_unchanged': current[name] == captured[name]
                   for name in ('baseline', 'calibration', 'direct_registry')})
    facts['capture_asset_comparison'] = checks
    facts['cross_process_evaluated_comparison'] = {
        field: read.matrix_errors(captured[field], current[field]) for field in ('pose', 'skin')}
    require_finite_state(current)
    require_finite_state(captured)
    if any(check['missing'] or check['added'] for check in facts['cross_process_evaluated_comparison'].values()):
        raise RuntimeError('Cross-process evaluated bone names changed')
    if any(checks[name] for name in checks if name.endswith('_diffs')) or not all(
            checks[name] for name in checks if name.endswith('_unchanged')):
        raise RuntimeError('Current raw artist data no longer match the isolated checkpoint')
    checks['passed'] = True


def main(facts):
    if bpy.app.background or bpy.context.area.type != 'CONSOLE' or Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('Use only the paused X native Python Console')
    area = bpy.context.area
    runtime = modules()
    source = installed_source(runtime)
    rig = bpy.context.view_layer.objects.active
    if rig is None or rig.name != 'CoshaRig' or bpy.context.mode not in {'OBJECT', 'POSE'}:
        raise RuntimeError('Keep CoshaRig active in Object/Pose mode')
    no_preview(runtime, rig)
    validation = json.loads((FOLDER / 'new1.json').read_text(encoding='utf-8'))
    if not validation.get('passed') or validation['version'] != [0, 75, 1]:
        raise RuntimeError('Isolated current-X validation has not passed')
    read = readers(runtime)
    selected = selection(rig)
    auto_key = bpy.context.scene.tool_settings.use_keyframe_insert_auto
    inputs_before = pose_inputs(rig)
    runtime.limb_ik_fk._update(bpy.context, rig)
    require_pose_inputs(rig, inputs_before, facts, 'initial_evaluation')
    names = tuple(runtime.control_pose_assets.native_rest(rig))
    surfaces = runtime.body_setup_removal._bound_surfaces(bpy.context, rig)
    before = read.states(rig, set(), set(), names)
    # Exact model data from the same current checkpoint must still match.
    compare_assets(facts, read, before, validation['input_state'])
    target = validation['checks']['final']
    if target.get('mesh_exact_diffs') or target.get('hair_dress_exact_diffs'):
        raise RuntimeError('Isolated data protection check failed')
    facts.update({'runtime': bpy.app.version_string, 'source': str(source),
        'version_before': list(runtime.addon.bl_info['version']), 'artist_before': read.fingerprint(ARTIST),
        'selection_before': selected, 'auto_key_before': auto_key})
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    checkpoint = FOLDER / ('X_before_display_' + stamp + '.blend')
    result = bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True, check_existing=False)
    if result != {'FINISHED'} or Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('Fresh recovery copy did not save independently')
    facts['checkpoint'] = read.fingerprint(checkpoint)
    facts['phase'] = 'refresh'
    runtime.addon._reload_addon_deferred()
    runtime = modules()
    if installed_source(runtime) != source or tuple(runtime.addon.bl_info['version']) != (0,75,1):
        raise RuntimeError('Refresh failed to load installed 0.75.1')
    if runtime.addon.ADDON_REFRESH_LAST_ERROR:
        raise RuntimeError(runtime.addon.ADDON_REFRESH_LAST_ERROR)
    runtime.addon._validate_registration_integrity()
    read = readers(runtime)
    verify_native(read, facts, 'after_refresh', rig, before, surfaces, names, inputs_before)
    facts['phase'] = 'repair_current_fk_display'
    facts['result'] = read.plain(runtime.limb_ik_fk_batch.switch_all(bpy.context, rig, 'FK', keyframe=False))
    verify_native(read, facts, 'after_display', rig, before, surfaces, names, inputs_before)
    inspect_display(runtime, rig, facts)
    require_selection(rig, selected)
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto != auto_key:
        raise RuntimeError('Auto Key preference changed')
    area.type = 'NODE_EDITOR'
    area.ui_type = 'GeometryNodeTree'
    facts['phase'] = 'save_artist'
    result = bpy.ops.wm.save_mainfile()
    facts['save_result'] = sorted(result)
    if result != {'FINISHED'} or Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('Native artist save did not finish')
    facts['artist_after'] = read.fingerprint(ARTIST)
    verify_native(read, facts, 'after_save', rig, before, surfaces, names, inputs_before)
    require_selection(rig, selected)
    facts.update({'status': 'passed', 'phase': 'complete', 'saved': True,
                  'version_after': list(runtime.addon.bl_info['version']), 'selection_after': selection(rig),
                  'auto_key_after': bpy.context.scene.tool_settings.use_keyframe_insert_auto})


facts = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'starting', 'saved': False}
try:
    main(facts)
except Exception as exc:
    facts.update({'status': 'failed', 'error': str(exc), 'traceback': traceback.format_exc()})
finally:
    facts['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (FOLDER / 'live_display.json').write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
    print('LIVE_DISPLAY', facts['status'], facts.get('phase'), facts.get('error', ''), flush=True)
