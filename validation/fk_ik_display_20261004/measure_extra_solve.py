"""Same-process controlled comparison of one redundant IK/FK graph solve.

The complete graph and display policy stay on the same canonical 0.75.1 code.
Only the already-installed ensure_switching path is varied. This measures the
forced redundant solve versus the optimized path, not 0.75.0 versus 0.75.1,
and does not measure GUI click, redraw, Undo, FPS or persistent memory.
Run in isolated Blender --background --factory-startup --threads 1.
Optional arguments after --: canonical addons directory, output JSON filename.
"""
import ast
import datetime
import hashlib
import json
import math
import statistics
import sys
import time
import traceback
from array import array
from pathlib import Path

import bpy

FOLDER = Path(__file__).resolve().parent
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CANONICAL = Path(ARGS[0]).resolve() if ARGS else Path(r'D:\MyRepository\Blender-addons-by-Randy\addons')
OUTPUT = FOLDER / (ARGS[1] if len(ARGS) > 1 else 'measure_extra_solve.json')
if OUTPUT.parent.resolve() != FOLDER.resolve() or OUTPUT.suffix != '.json':
    raise RuntimeError('Keep this isolated comparison report in its validation folder.')
INPUT = FOLDER / 'X_live_input.blend'
ARTIST = FOLDER.parents[1] / 'X.blend'
PROBE = FOLDER.parent / 'original_calibration_20261004' / 'probe_current.py'
READERS = FOLDER.parent / 'native_fk_controls_20261004' / 'validate_native_fk.py'
CHANNELS = ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')
POSE_TOLERANCE = 2e-4
SURFACE_TOLERANCE = 1e-4
REST_TOLERANCE = 2e-6

sys.path.insert(0, str(CANONICAL))
import character_designer
from character_designer import (body_calibration, body_original_mode, body_setup,
    body_setup_removal, bone_color_palette, control_pose_assets, forearm_twist,
    hair_bones_rig, limb_ik, limb_ik_fk, limb_ik_fk_batch, skirt_rig,
    spine_ik_fk, torso_controls)


def load_readers():
    wanted = {'snapshot_helpers', 'exact_diffs', 'retained_meshes', 'color',
              'constraint', 'hair_dress_snapshot', 'matrix_errors', 'surface_errors',
              'native_pose', 'native_skin', 'body_animation', 'states', 'check_preserved'}
    parsed = ast.parse(READERS.read_text(encoding='utf-8'), filename=str(READERS))
    selected = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {node.name for node in selected} != wanted:
        raise RuntimeError('The proven read-only validation interface changed.')
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(READERS), 'exec'), globals())


load_readers()
H = snapshot_helpers()
plain, matrix = H['plain'], H['matrix']


def file_hash(path):
    return H['sha_file'](path)


def assert_pose_surface(rig, before, surfaces, rest_names):
    # Match the existing validation's thresholds exactly, outside timing.
    limb_ik_fk._update(bpy.context, rig)
    pose = matrix_errors(before['pose'], native_pose(rig, rest_names))
    skin = matrix_errors(before['skin'], native_skin(rig))
    surface = surface_errors(rig, surfaces)
    if (pose['missing'] or pose['added'] or skin['missing'] or skin['added']
            or pose['maximum'] > POSE_TOLERANCE or skin['maximum'] > POSE_TOLERANCE
            or surface['maximum'] > SURFACE_TOLERANCE):
        raise RuntimeError('Controlled comparison changed native pose, skin or a bound surface: '
                           + repr({'pose': pose['maximum'], 'skin': skin['maximum'],
                                   'surface': surface['maximum']}))
    return {'pose_error': pose['maximum'], 'skin_error': skin['maximum'],
            'surface_error': surface['maximum']}


def run():
    if not bpy.app.background:
        raise RuntimeError('Background only; never run a benchmark in the artist window.')
    if INPUT.resolve() == ARTIST.resolve() or not INPUT.is_file():
        raise RuntimeError('Use the independent current-scene checkpoint.')
    character_designer.register()
    bpy.ops.wm.open_mainfile(filepath=str(INPUT), load_ui=False, use_scripts=False)
    rig = bpy.data.objects['CoshaRig']
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    limb_ik._settings(bpy.context).armature = rig
    limb_ik_fk._update(bpy.context, rig)
    inventory = limb_ik._validate_inventory(rig)
    if limb_ik_fk_batch.mode_for_keys(rig, inventory) != 'FK' or body_original_mode.active(rig):
        raise RuntimeError('The identical pair baseline must be ordinary native FK, outside Original.')
    if any(rig.data.bones[item['target'].name].get(limb_ik_fk.VERSION_KEY) != limb_ik_fk.VERSION
           for item in inventory['rigs'].values()):
        raise RuntimeError('This comparison requires previously installed native switch drivers.')
    rest_names = tuple(control_pose_assets.native_rest(rig))
    surfaces = body_setup_removal._bound_surfaces(bpy.context, rig)
    before = states(rig, set(), set(), rest_names)
    checkpoint = limb_ik_fk_batch._checkpoint(bpy.context, rig, None)
    hashes = {'input': file_hash(INPUT), 'artist': file_hash(ARTIST)}
    facts = {'passed': False, 'runtime': bpy.app.version_string,
             'version': list(character_designer.bl_info['version']),
             'source': character_designer.__file__, 'threads_requested': 1,
             'comparison': 'same code and display: forced redundant installed-driver solve versus optimized',
             'scope': 'background function wall time; excludes reset, raw snapshots and external validation',
             'warmup_pairs': 1, 'measured_pairs': 3, 'samples': [], 'rounds': [], 'hashes_before': hashes,
             'reader_sha256': file_hash(READERS), 'script_sha256': file_hash(Path(__file__))}
    original_ensure, original_update = limb_ik_fk.ensure_switching, limb_ik_fk._update
    counter = {'timed': False, 'updates': 0, 'forced': 0}

    def count_update(*args, **kwargs):
        if counter['timed']:
            counter['updates'] += 1
        return original_update(*args, **kwargs)

    def redundant_ensure(*args, **kwargs):
        installed = original_ensure(*args, **kwargs)
        if installed == 0:
            # Exactly reproduce the old unnecessary invalidation and its
            # immediate batch solve, keeping the current display/graph code.
            args[0].update_tag(refresh={'OBJECT'})
            if counter['timed']:
                counter['forced'] += 1
            return 1
        return installed

    def reset():
        # Restore the exact transaction checkpoint, never match back from a
        # rounded earlier sample. Runtime remains paused during rollback.
        limb_ik_fk.ensure_switching = original_ensure
        with forearm_twist.defer_runtime(bpy.context, flush_on_exit=False):
            limb_ik_fk_batch._rollback(bpy.context, rig, checkpoint, set())
        if limb_ik_fk_batch.mode_for_keys(rig) != 'FK':
            raise RuntimeError('The comparison checkpoint did not restore native FK.')
        return assert_pose_surface(rig, before, surfaces, rest_names)

    limb_ik_fk._update = count_update
    try:
        for pair in range(4):
            conditions = ('forced_redundant_solve', 'optimized') if pair % 2 == 0 else ('optimized', 'forced_redundant_solve')
            for condition in conditions:
                reset()
                limb_ik_fk.ensure_switching = redundant_ensure if condition == 'forced_redundant_solve' else original_ensure
                for mode in ('IK', 'FK'):
                    counter.update(timed=True, updates=0, forced=0)
                    start = time.perf_counter()
                    try:
                        result = limb_ik_fk_batch.switch_all(bpy.context, rig, mode, keyframe=False)
                    finally:
                        seconds = time.perf_counter() - start
                        counter['timed'] = False
                    verification = assert_pose_surface(rig, before, surfaces, rest_names)
                    if limb_ik_fk_batch.mode_for_keys(rig) != mode or not result['changed']:
                        raise RuntimeError('A timed sample did not perform its actual mode switch.')
                    record = {'pair': pair, 'warmup': pair == 0, 'condition': condition, 'mode': mode,
                              'seconds': seconds, 'matcher_update_calls': counter['updates'],
                              'forced_redundant_solve_calls': counter['forced'], **verification}
                    facts['rounds'].append(record)
                    if pair:
                        facts['samples'].append(record)
                reset()  # Restore after each condition/pair outside timing.
        check_preserved(facts, 'final', rig, before, surfaces, set(), set(), rest_names)
        facts['hashes_after'] = {'input': file_hash(INPUT), 'artist': file_hash(ARTIST)}
        if facts['hashes_after'] != hashes:
            raise RuntimeError('An input or artist file changed during the isolated benchmark.')
        facts['summary'] = {condition: {mode: {'count': len(values),
            'median_seconds': statistics.median(values), 'minimum_seconds': min(values),
            'maximum_seconds': max(values)} for mode in ('IK', 'FK')
            for values in ([sample['seconds'] for sample in facts['samples']
                            if sample['condition'] == condition and sample['mode'] == mode],)}
            for condition in ('forced_redundant_solve', 'optimized')}
        facts['passed'] = True
        print('EXTRA_SOLVE_CONTROLLED_PASS', json.dumps(facts['summary']), flush=True)
    except Exception:
        facts['error'] = traceback.format_exc()
        raise
    finally:
        counter['timed'] = False
        limb_ik_fk.ensure_switching = original_ensure
        limb_ik_fk._update = original_update
        OUTPUT.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')


try:
    run()
except Exception:
    (FOLDER / (OUTPUT.stem + '_error.txt')).write_text(traceback.format_exc(), encoding='utf-8')
    raise
