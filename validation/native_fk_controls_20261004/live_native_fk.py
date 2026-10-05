"""Parent-reviewed live X integration, following passed isolated validation.

Run in the paused artist Python Console. Reads installed add-on modules only;
never opens another blend or performs artist pose probes/IK roundtrips.
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
INPUT = FOLDER / 'X_live_input.blend'
VALIDATION = FOLDER / 'validate_native_fk.json'
VALIDATOR = FOLDER / 'validate_native_fk.py'
PROBE = FOLDER.parent / 'original_calibration_20261004' / 'probe_current.py'
REPORT = FOLDER / 'live_native_fk.json'
VERSION = (0, 75, 0)
CHANNELS = ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')
POSE_TOLERANCE = 2e-4
SURFACE_TOLERANCE = 1e-4
REST_TOLERANCE = 2e-6


def modules():
    addon = sys.modules.get('character_designer')
    if addon is None:
        raise RuntimeError('The installed Character Designer runtime is not loaded.')
    result = {'addon': addon}
    for name in ('body_calibration', 'body_original_mode', 'body_rest_resync', 'body_setup', 'body_setup_removal',
                 'bone_color_palette', 'control_pose_assets', 'forearm_twist', 'hair_bones_rig',
                 'limb_ik', 'limb_ik_fk', 'limb_ik_fk_batch', 'skirt_rig', 'spine_ik_fk', 'torso_controls'):
        result[name] = importlib.import_module('character_designer.' + name)
    return SimpleNamespace(**result)


def installed_source(runtime):
    expected = (Path(bpy.utils.user_resource('SCRIPTS')) / 'addons' / 'character_designer' / '__init__.py').resolve()
    source = Path(runtime.addon.__file__).resolve()
    if source != expected:
        raise RuntimeError('Unexpected loaded Character Designer source: ' + str(source))
    for name, module in vars(runtime).items():
        if name != 'addon' and Path(module.__file__).resolve().parent != source.parent:
            raise RuntimeError('A Character Designer submodule comes from a different source: ' + name)
    return source


def extracted(path, wanted, scope):
    parsed = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    nodes = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {node.name for node in nodes} != wanted:
        raise RuntimeError('A reviewed read-only snapshot interface changed: ' + str(path))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    return {name: scope[name] for name in wanted}


def readers(runtime):
    """Extract definitions only; GUI sys.path and package registration stay intact."""
    scope = {'bpy': bpy, 'math': math, 'hashlib': hashlib, 'json': json, 'array': array,
             'CHANNELS': CHANNELS, 'limb_ik': runtime.limb_ik}
    wanted = {'sha_file', 'fingerprint', 'plain', 'custom', 'matrix', 'rna_fields',
              'data_hash', 'bulk', 'mesh_snapshot', 'bone_rest', 'curve_snapshot',
              'driver_snapshot', 'animation_snapshot', 'differences'}
    helpers = extracted(PROBE, wanted, scope)
    scope.update({name: module for name, module in vars(runtime).items() if name != 'addon'})
    scope.update({'H': helpers, 'plain': helpers['plain'], 'matrix': helpers['matrix'],
                  'POSE_TOLERANCE': POSE_TOLERANCE, 'SURFACE_TOLERANCE': SURFACE_TOLERANCE,
                  'REST_TOLERANCE': REST_TOLERANCE, 'time': time})
    wanted = {'exact_diffs', 'retained_meshes', 'color', 'constraint', 'hair_dress_snapshot',
              'matrix_errors', 'surface_errors', 'native_pose', 'native_skin', 'body_animation',
              'states', 'check_preserved'}
    functions = extracted(VALIDATOR, wanted, scope)
    return SimpleNamespace(**helpers, **functions)


def no_preview(runtime, rig):
    if runtime.body_original_mode.active(rig):
        raise RuntimeError('The current X must remain in Controls; Original is active.')
    forearm = runtime.forearm_twist
    if forearm._SESSION is not None or any(forearm.PREVIEW_KEY in obj for obj in bpy.data.objects):
        raise RuntimeError('Finish the existing Forearm preview before refreshing or saving.')


def selection(rig):
    return {'mode': bpy.context.mode, 'active_object': bpy.context.view_layer.objects.active.name,
            'selected_objects': sorted(obj.name for obj in bpy.context.selected_objects),
            'active_bone': rig.data.bones.active.name if rig.data.bones.active else None,
            'selected_bones': sorted(pb.name for pb in rig.pose.bones if pb.select)}


def require_selection(rig, saved):
    current = selection(rig)
    if current != saved:
        raise RuntimeError('The artist Object/Pose selection changed during integration: ' + str(current))


def validated_capture(read, validation):
    if (validation.get('status') != 'passed' or validation.get('addon_version') != list(VERSION)
            or not validation.get('input_unchanged') or not validation.get('artist_unchanged')
            or not validation.get('candidate_saved') or validation.get('final_mode') != 'FK'):
        raise RuntimeError('The isolated 0.75.0 current-X validation has not passed.')
    captured = read.fingerprint(INPUT)
    if validation.get('input_before') != captured or validation.get('input_after') != captured:
        raise RuntimeError('The copied input no longer matches the passed validation fingerprint.')
    for key, path in (('validator_sha256', VALIDATOR), ('snapshot_probe_sha256', PROBE)):
        if validation.get(key) and validation[key] != read.sha_file(path):
            raise RuntimeError('A verified snapshot helper changed since validation: ' + key)
    return captured


def compare_capture(facts, read, current, captured):
    """Model data must still match the exact checkpoint used for approval."""
    check = {'mesh_exact_diffs': read.exact_diffs(captured['meshes'], current['meshes']),
             'native_rest_exact_diffs': read.exact_diffs(captured['rest'], current['rest']),
             'native_rest': read.differences(current['rest'], captured['rest']),
             'native_pose': read.matrix_errors(captured['pose'], current['pose']),
             'native_skin': read.matrix_errors(captured['skin'], current['skin']),
             'hair_dress_exact_diffs': read.exact_diffs(captured['hair_dress'], current['hair_dress']),
             'animation_exact_diffs': read.exact_diffs(captured['animation'], current['animation']),
             'baseline_unchanged': current['baseline'] == captured['baseline'],
             'calibration_unchanged': current['calibration'] == captured['calibration'],
             'direct_registry_unchanged': current['direct_registry'] == captured['direct_registry']}
    facts['capture_comparison'] = check
    if (check['mesh_exact_diffs'] or check['hair_dress_exact_diffs'] or check['animation_exact_diffs']
            or any(entry['substantial'] for entry in check['native_rest'])
            or not all(check[name] for name in ('baseline_unchanged', 'calibration_unchanged', 'direct_registry_unchanged'))):
        raise RuntimeError('Current artist model/records no longer match the validated checkpoint; no refresh or repair was applied.')
    for field in ('native_pose', 'native_skin'):
        if check[field]['missing'] or check[field]['added'] or check[field]['maximum'] > POSE_TOLERANCE:
            raise RuntimeError('Current artist pose differs from the validated checkpoint: ' + field)
    check['passed'] = True


def main(facts):
    if bpy.app.background or bpy.context.window is None or bpy.context.area is None:
        raise RuntimeError('Run only in the paused native X artist window.')
    area = bpy.context.area
    if area.type != 'CONSOLE':
        raise RuntimeError('Run this reviewed integration from X\'s native Python Console.')
    if Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('The current native filepath must be X.blend; no other file will be opened.')
    if bpy.context.mode not in {'OBJECT', 'POSE'}:
        raise RuntimeError('Finish the active mesh/Edit/Weight operation before integration.')
    runtime = modules()
    source = installed_source(runtime)
    rig = bpy.data.objects.get('CoshaRig')
    if rig is None or rig.type != 'ARMATURE' or bpy.context.view_layer.objects.active != rig:
        raise RuntimeError('Keep CoshaRig as the active native artist object.')
    no_preview(runtime, rig)
    auto_key = bpy.context.scene.tool_settings.use_keyframe_insert_auto
    if auto_key:
        raise RuntimeError('Auto Key is enabled; this non-animating Spine removal requires Auto Key off.')
    if runtime.addon.ADDON_REFRESH_PENDING or bpy.app.timers.is_registered(runtime.addon._reload_addon_deferred):
        raise RuntimeError('A Refresh is already pending; let that operation finish.')
    read = readers(runtime)
    validation = json.loads(VALIDATION.read_text(encoding='utf-8'))
    capture = validated_capture(read, validation)
    runtime.limb_ik_fk._update(bpy.context, rig)
    inventory = runtime.limb_ik._validate_inventory(rig)
    if set(inventory['rigs']) != set(runtime.limb_ik_fk_batch.LIMB_KEYS):
        raise RuntimeError('The installed four native limb chains changed since validation.')
    if runtime.limb_ik_fk_batch.mode_for_keys(rig, inventory) != 'IK':
        raise RuntimeError('Expected the validated four-limb IK input before integration.')
    extension = runtime.spine_ik_fk.validate(rig)
    torso = runtime.torso_controls.validate(rig)
    if extension is None or torso is None:
        raise RuntimeError('The validated optional Spine branch/shared Bend setup is missing.')
    excluded_meshes = {entry['object'] for entry in extension['widgets'].values()}
    excluded_drivers = {entry['path'] for entry in extension['drivers']}
    if (sorted(excluded_meshes) != validation['excluded_owned_spine_widgets']
            or sorted(excluded_drivers) != validation['excluded_owned_spine_driver_paths']):
        raise RuntimeError('Optional Spine widget/driver ownership changed since validation.')
    rest_names = tuple(runtime.control_pose_assets.native_rest(rig))
    selected = selection(rig)
    before = read.states(rig, excluded_meshes, excluded_drivers, rest_names)
    compare_capture(facts, read, before, validation['input_state'])
    surfaces = runtime.body_setup_removal._bound_surfaces(bpy.context, rig)
    facts.update({'runtime': bpy.app.version_string, 'installed_source': str(source),
        'addon_before': list(runtime.addon.bl_info['version']), 'artist_before': read.fingerprint(ARTIST),
        'isolated_validation': {'path': str(VALIDATION), 'sha256': read.sha_file(VALIDATION),
                                'status': validation['status'], 'input': capture},
        'selection_before': selected, 'auto_key_before': auto_key, 'protected_input': before,
        'artist_file_opened': False, 'artist_test_rotation_performed': False,
        'artist_ik_roundtrip_performed': False})
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    checkpoint = FOLDER / ('X_before_live_native_fk_' + stamp + '.blend')
    if checkpoint.exists() or checkpoint.resolve() == ARTIST:
        raise RuntimeError('Checkpoint must be a new independent validation file.')
    facts['phase'] = 'save_fresh_independent_checkpoint'
    facts['checkpoint_save'] = sorted(bpy.ops.wm.save_as_mainfile(
        filepath=str(checkpoint), copy=True, check_existing=False))
    if facts['checkpoint_save'] != ['FINISHED'] or Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('The independent copy save did not preserve the native artist filepath.')
    facts['checkpoint'] = read.fingerprint(checkpoint)
    if read.fingerprint(ARTIST) != facts['artist_before']:
        raise RuntimeError('Artist disk file changed during independent checkpoint save.')
    read.check_preserved(facts, 'after_checkpoint', rig, before, surfaces,
                         excluded_meshes, excluded_drivers, rest_names)
    require_selection(rig, selected)
    facts['phase'] = 'refresh_installed_addon'
    runtime.addon._reload_addon_deferred()
    runtime = modules()
    if installed_source(runtime) != source or tuple(runtime.addon.bl_info['version']) != VERSION:
        raise RuntimeError('Refresh did not load the deployed installed 0.75.0 package.')
    if runtime.addon.ADDON_REFRESH_LAST_ERROR:
        raise RuntimeError('Refresh failed: ' + runtime.addon.ADDON_REFRESH_LAST_ERROR)
    runtime.addon._validate_registration_integrity()
    read = readers(runtime)  # Rebind helper globals to refreshed installed modules.
    no_preview(runtime, rig)
    read.check_preserved(facts, 'after_refresh', rig, before, surfaces,
                         excluded_meshes, excluded_drivers, rest_names)
    require_selection(rig, selected)
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto != auto_key:
        raise RuntimeError('Refresh changed the artist Auto Key preference.')
    facts['refresh'] = {'status': 'passed', 'source': str(source), 'addon': list(VERSION), 'integrity': 'passed'}
    facts['phase'] = 'atomic_spine_remove_and_native_fk'
    correctives = {'correctives': runtime.body_rest_resync._corrective_checkpoint(rig)}
    def operation():
        removed = runtime.spine_ik_fk.remove(bpy.context, rig)
        switched = runtime.limb_ik_fk_batch.switch_all(bpy.context, rig, 'FK', keyframe=False)
        if (runtime.spine_ik_fk.get_record(rig)
                or any(bone.get(runtime.limb_ik.OWNER_KEY) == runtime.spine_ik_fk.OWNER_VALUE
                       for bone in rig.data.bones)
                or any(name in bpy.data.objects for name in excluded_meshes)):
            raise RuntimeError('Optional Spine resources remain after guarded removal.')
        if runtime.limb_ik_fk_batch.mode_for_keys(rig) != 'FK':
            raise RuntimeError('All four native limb chains did not reach FK.')
        # The outer defer owns this callback, so it can publish the final pose
        # inside _atomic even though its nested batch runtime is paused.
        refresh_correctives()
        read.check_preserved(facts, 'inside_combined_transaction', rig, before, surfaces,
                             excluded_meshes, excluded_drivers, rest_names)
        return {'spine_removed': removed, 'all_fk': read.plain(switched)}
    started = time.perf_counter()
    with runtime.forearm_twist.defer_runtime(bpy.context, flush_on_exit=False) as refresh_correctives:
        try:
            facts['combined_result'] = runtime.body_setup._atomic(bpy.context, rig, operation)
        except Exception:
            # _atomic restores the graph/resources; the established native
            # corrective checkpoint restores only this character's owned
            # runtime outputs after that rollback, with handlers still paused.
            runtime.body_rest_resync.restore_correctives(correctives)
            facts['combined_failure_owned_correctives_restored'] = True
            raise
    facts['combined_seconds'] = time.perf_counter() - started
    no_preview(runtime, rig)
    facts['protected_final'] = read.check_preserved(facts, 'after_combined_commit', rig, before, surfaces,
                                                   excluded_meshes, excluded_drivers, rest_names)
    require_selection(rig, selected)
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto != auto_key:
        raise RuntimeError('The artist Auto Key preference changed during integration.')
    facts['selection_after'] = selection(rig)
    facts['auto_key_after'] = bpy.context.scene.tool_settings.use_keyframe_insert_auto
    if Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('The native artist filepath changed before saving.')
    facts['phase'] = 'restore_geometry_nodes_editor'
    area.type = 'NODE_EDITOR'
    area.ui_type = 'GeometryNodeTree'
    if area.type != 'NODE_EDITOR' or area.ui_type != 'GeometryNodeTree':
        raise RuntimeError('The temporary console could not restore Geometry Nodes; inspect before saving.')
    facts['editor_restored'] = {'type': area.type, 'ui_type': area.ui_type}
    facts['phase'] = 'save_current_artist'
    facts['artist_save_requested'] = True
    facts['artist_save_result'] = sorted(bpy.ops.wm.save_mainfile())
    if facts['artist_save_result'] != ['FINISHED'] or Path(bpy.data.filepath).resolve() != ARTIST:
        raise RuntimeError('Blender did not confirm saving current artist X.blend.')
    facts['artist_saved'] = True
    facts['artist_after'] = read.fingerprint(ARTIST)
    if facts['artist_after'] == facts['artist_before']:
        raise RuntimeError('The artist file fingerprint did not change after completed integration.')
    facts['phase'] = 'verify_native_save'
    read.check_preserved(facts, 'after_artist_save', rig, before, surfaces,
                         excluded_meshes, excluded_drivers, rest_names)
    require_selection(rig, selected)
    no_preview(runtime, rig)
    runtime.limb_ik._validate_inventory(rig)
    facts['final_mode'] = runtime.limb_ik_fk_batch.mode_for_keys(rig)
    if facts['final_mode'] != 'FK' or bpy.context.scene.tool_settings.use_keyframe_insert_auto != auto_key:
        raise RuntimeError('The final saved FK/Auto Key state changed.')
    facts.update({'status': 'passed', 'phase': 'complete'})


def run():
    facts = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'status': 'starting', 'phase': 'preflight', 'artist_saved': False,
             'artist_save_requested': False, 'backup_opened': False, 'test_scene_opened': False}
    try:
        main(facts)
    except Exception as exc:
        facts.update({'status': 'failed', 'error': str(exc), 'traceback': traceback.format_exc()})
        if facts.get('checkpoint'):
            facts['recovery_checkpoint'] = facts['checkpoint']['path']
        # The combined add-on transaction owns rollback. Never load a backup
        # or independently overwrite artist channels/Shape Keys to imitate it.
    finally:
        facts['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        REPORT.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
        print('LIVE_X_NATIVE_FK', facts['status'], facts.get('phase'), str(REPORT), flush=True)
        if facts.get('error'):
            print('LIVE_X_NATIVE_FK_ERROR', facts['error'], flush=True)
    return facts


LIVE_X_NATIVE_FK_RESULT = run()
