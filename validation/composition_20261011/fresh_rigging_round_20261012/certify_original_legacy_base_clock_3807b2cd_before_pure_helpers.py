"""One future owned-clone observation of legacy Base timing; never the artist.
Source preparation authorizes no execution. Background factory/disable-autoexec,
threads1 and --python-exit-code1 are launcher obligations. No save or new IDs.
"""
import argparse
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import sys
import traceback

ROUND = Path(r'D:\Blender\Projects\Character\X\validation\composition_20261011\fresh_rigging_round_20261012')
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
EXPECTED = {'snapshot_receipt': '99b08426346d77908dbed93e518bc0e2370701a0e8ee906df7d36cb072bb2949',
    'seed': '1c1984156b3d7637596382ff12359f3460f51b4b6216cd088f9dd97c1cd4bf41',
    'packet': 'e54537cb65ab6b0365b42af0236f645cc0f009e1c10b056d66a13b87e7669c02',
    'package_manifest': 'c15737192050944b27d88e9c65119331fbba8cd0de18d629b07365fbc0d83cb4',
    'oracle': '260b2bc581df220ea861d18f6b369d104561d5a3d119e21e5e52e9e230219a5d',
    'protected_artist': '3cd5619d70e8b4e21c2483884a04d352a2405f0eab02f00d34d306c81c5aa4b0'}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def pin(path, expected):
    p = Path(path).resolve()
    require(p.is_file() and sha(p) == expected, 'Pinned input changed: ' + str(p))
    return {'path': str(p), 'sha256': expected, 'bytes': p.stat().st_size}


def load_helper(row, name):
    pin(row['path'], row['sha256'])
    spec = importlib.util.spec_from_file_location(name, row['path'])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write(path, value):
    with path.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def motion(fp, action, slot):
    proof = fp.fingerprint_action(action, slot)
    require(proof['fingerprint_known'] is True, 'Selected-slot content remains Unknown: ' + action.name)
    return proof


def runtime_files(root, files):
    for relative, expected in files.items():
        p = (root / relative).resolve()
        require(p.is_relative_to(root), 'A package path escaped its source root.')
        pin(p, expected)
    for name, module in tuple(sys.modules.items()):
        if name == 'character_designer' or name.startswith('character_designer.'):
            p = Path(module.__file__).resolve()
            require(p.is_relative_to(root), 'A loaded CD module has another root: ' + name)
            pin(p, files[p.relative_to(root).as_posix()])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-sha256', required=True)
    for name in EXPECTED:
        parser.add_argument('--' + name.replace('_', '-'), required=True)
        parser.add_argument('--' + name.replace('_', '-') + '-sha256', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--profile-root', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    inputs = {'source': pin(__file__, args.source_sha256)}
    for name, expected in EXPECTED.items():
        require(getattr(args, name + '_sha256') == expected, 'Use the actual held input: ' + name)
        inputs[name] = pin(getattr(args, name), expected)
    require(Path(inputs['protected_artist']['path']) == ARTIST.resolve(), 'Protect the actual X.blend without opening it.')
    output, profile = Path(args.output_root).resolve(), Path(args.profile_root).resolve()
    require(output != ROUND and output.is_relative_to(ROUND) and output.is_dir() and not any(output.iterdir()), 'Use one new empty owned ROUND output child.')
    require(profile.is_relative_to(Path(r'D:\Codex\XV').resolve()) and profile.is_dir()
        and {p.name for p in profile.iterdir()} == {'CONFIG', 'DATAFILES'}, 'Use one fresh owned short profile.')
    for name in ('CONFIG', 'DATAFILES'):
        p = profile / name
        require(p.is_dir() and not any(p.iterdir()) and Path(os.environ['BLENDER_USER_' + name]).resolve() == p,
            'The launcher must bind the empty owned profile ' + name)
    receipt = json.loads(Path(inputs['snapshot_receipt']['path']).read_text(encoding='utf-8-sig'))
    require(receipt['completed'] is True and receipt['backup_verified'] is True and receipt['metadata_preservation_verified'] is True
        and receipt['backup'] == inputs['seed'] and receipt['protected_artist'] == inputs['protected_artist'], 'Require actual99B successful metadata and seed1C198.')
    manifest = json.loads(Path(inputs['package_manifest']['path']).read_text(encoding='utf-8-sig'))
    require(manifest['schema_version'] == 1 and manifest['module'] == 'character_designer'
        and manifest['version'] == '0.77.25' and len(manifest['files']) == 188, 'Use the complete held R7 package.')
    root, files = Path(manifest['source_root']).resolve(), manifest['files']
    sys.dont_write_bytecode = True
    import bpy
    import addon_utils
    require(bpy.app.background and not bpy.data.filepath and tuple(bpy.app.version[:2]) == (5, 2), 'Require a fresh background5.2 factory child; never an existing artist process.')
    require(not any(name == 'character_designer' or name.startswith('character_designer.') for name in sys.modules), 'The child must not inherit another CD runtime.')
    report_path = output / 'original_legacy_base_clock_report.json'
    report = {'schema': 'x.validation.original-legacy-base-clock/1', 'completed': False, 'legacy_clock_known': False,
        'source_inputs': inputs, 'pid': os.getpid(), 'native_execution_performed': True, 'artist_opened_or_written': False,
        'preview_Attach_generate_model_import_save_keys_performed': False, 'model_equivalence_verified': False,
        'natural_exit_verified': False, 'scope': 'Existing selected-slot Base clock and observed Source/Custom worlds only.'}
    with report_path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    prior, scene, rig, ctx, comp, ua, before_assets, oracle = (None,) * 8
    try:
        runtime_files(root, files)
        sys.path.insert(0, str(root.parent))
        cd = importlib.import_module('character_designer')
        require(Path(cd.__file__).resolve() == root / '__init__.py' and tuple(cd.bl_info['version']) == (0, 77, 25), 'Register only the complete frozen R7.')
        require(addon_utils.enable('character_designer', default_set=False, persistent=False) is not None
            and getattr(cd, '__addon_enabled__', False), 'Normal package registration failed.')
        bpy.ops.wm.open_mainfile(filepath=inputs['seed']['path'], use_scripts=False, load_ui=False)
        require(Path(bpy.data.filepath).resolve() == Path(inputs['seed']['path']), 'The child loaded another file.')
        from character_designer import unity_animation as ua, animation_worklist_fingerprint as fp, animation_composition as comp
        light = load_helper(receipt['source'], 'clock_snapshot_reader')
        oracle = load_helper(inputs['oracle'], 'clock_assets260b')
        scene, rig = bpy.data.scenes.get('Scene'), bpy.data.objects.get('CoshaRig')
        require(scene is not None and rig is not None and rig.library is None and rig.data.library is None
            and scene.character_designer_setup.rig == rig and scene.character_designer_animation_worklist.rig == rig,
            'Use the exact existing original Scene/setup/Main Rig; no selection/adoption repair.')
        saved = scene.character_designer_animation_worklist
        rows = [i for i in saved.items if i.item_id == '5f771ad1e0644d199cba30b6afd1ad0a']
        require(len(saved.items) == len(rows) == 1 and saved.model_sha256 == '2ae2067c9794fc7767f6abb35b6af33df496986a006c870fc9d0dc47eaa55db5', 'The saved original ownership baseline changed.')
        item = rows[0]
        require(item.rig == rig and item.work_item_id == '430266588d394b5b8d3cadc34216a965'
            and item.model_sha256 == saved.model_sha256 and rig.get('character_designer_animation_source_model_sha256') == saved.model_sha256,
            'The current original row/WorkID/model tag is not actual99B.')
        for path in (saved.workspace_path, item.manifest_path, item.source_file, saved.model_file):
            p = Path(bpy.path.abspath(path)).resolve()
            inputs['disk:' + str(p)] = pin(p, sha(p))
        packet = ua.load_package(inputs['packet']['path'])
        require(packet['_sha256'] == EXPECTED['packet'] and len(packet['frames']) == 59, 'Use the unchanged E54559-frame Base packet.')
        view_layer = scene.view_layers.get('ViewLayer')
        require(view_layer is not None and view_layer.objects.get(rig.name) == rig, 'The original ViewLayer/Rig is missing.')
        with bpy.context.temp_override(scene=scene, view_layer=view_layer):
            ctx = bpy.context
            ad = rig.animation_data
            require(ad is not None and not ad.use_tweak_mode and ad.action == item.custom_action
                and ad.action_slot_handle == item.custom_slot and not rig.get('character_designer_rigging_session_v1'), 'Observe the saved exact Base/slot outside preview/Tweak.')
            prior = comp._prior(ctx, rig)
            before_context, before_rest = light.context_record(ctx, bpy), ua._rest_state(rig.data)
            before_worklist = light.rna_record(saved)
            before_constraints = {p.name: [light.rna_record(c) for c in p.constraints] for p in rig.pose.bones}
            before_assets = oracle.asset_snapshot(scene, rig, ua)
            choices = [('SOURCE', item.source_action, item.source_slot), ('CUSTOM', item.custom_action, item.custom_slot)]
            proofs = {role: motion(fp, action, slot) for role, action, slot in choices}
            report['active_Base_proof'] = motion(fp, ad.action, ad.action_slot_handle)
            rate = scene.render.fps / scene.render.fps_base
            require(rate == 30. and scene.render.fps == 30 and scene.render.fps_base == 1., 'Actual99B Scene clock is not30/1; do not guess a replacement.')
            expected_times = [f32(1. + float(f['time']) * rate) for f in packet['frames']]
            with (output / 'selected_slot_curve_schedules.jsonl').open('x', encoding='utf-8') as stream:
                for role, action, slot in choices:
                    require(action.get(ua.PACKAGE_HASH_KEY) == EXPECTED['packet'], 'An original Base source revision changed.')
                    curves = list(fp._selected_curves(action, slot))
                    require(curves, 'An original Base slot has no keyed curve schedule.')
                    for curve in curves:
                        times = [float(p.co.x) for p in curve.keyframe_points]
                        require(all(math.isfinite(v) for v in times), 'A native key time is nonfinite.')
                        if role == 'SOURCE':
                            require(times == expected_times and not curve.sampled_points, 'Source key times do not prove the30fps legacy mapping; clock stays Unknown.')
                        row = {'role': role, 'path': curve.data_path, 'component': curve.array_index, 'key_times': times,
                            'modes': [[p.interpolation, p.easing, p.handle_left_type, p.handle_right_type] for p in curve.keyframe_points],
                            'sample_count': len(curve.sampled_points), 'modifier_count': len(curve.modifiers)}
                        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
            mapping = ua._mapping(rig, packet, scene.unit_settings.scale_length)
            authored = set(mapping.indices) - set(mapping.controls.delegated_names)
            require(len(authored) == 184 and len(mapping.controls.delegated_names) == 33, 'The actual original Body/mapped/delegated domain differs.')
            maximum = 0.
            with (output / 'body_world_samples.jsonl').open('x', encoding='utf-8') as stream:
                for role, action, slot in choices:
                    ad.action, ad.action_slot = action, comp._slot(action, slot)
                    ad.use_nla, ad.action_blend_type, ad.action_influence = False, 'REPLACE', 1.
                    for index, frame in enumerate(packet['frames']):
                        ua._set_frame(scene, 1. + float(frame['time']) * rate)
                        view_layer.update()
                        evaluated = rig.evaluated_get(ctx.evaluated_depsgraph_get())
                        expected = ua.expected_world_matrices(rig, packet, index, unit_scale=scene.unit_settings.scale_length, mapping=mapping)
                        worlds, error = {}, 0.
                        for name in sorted(authored):
                            value, desired = evaluated.matrix_world @ evaluated.pose.bones[name].matrix, expected[name]
                            require(all(math.isfinite(v) for matrix in (value, desired) for row in matrix for v in row), 'A Body world matrix is nonfinite.')
                            worlds[name] = [float(v) for row in value for v in row]
                            error = max(error, *(abs(value[r][c] - desired[r][c]) for r in range(4) for c in range(4)))
                        if role == 'SOURCE':
                            require(error <= 2e-4, 'Source Body worlds do not authenticate the candidate clock.')
                            maximum = max(maximum, error)
                        stream.write(json.dumps({'role': role, 'index': index, 'packet_time': frame['time'], 'native_frame': 1. + frame['time'] * rate,
                            'worlds': worlds, 'maximum_difference_from_Source_packet': error}, allow_nan=False) + '\n')
            report.update(legacy_clock_known=True, verified_legacy_action_rate=rate, explicit_native_marker_written=False,
                source_world_maximum_error=maximum, Source_world_samples=59, Custom_world_observations=59,
                selected_slot_proofs=proofs, Custom_forced_equal_Source=False, graph_Unknown_not_promoted=True)
    except Exception as error:
        report.update(error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
    finally:
        try:
            if prior is not None:
                with bpy.context.temp_override(scene=scene, view_layer=scene.view_layers['ViewLayer']):
                    ctx = bpy.context
                    comp._restore_prior(ctx, rig, prior)
                    # Restore the exact observed unkeyed channels AFTER frame
                    # reevaluation, not a newly authored pose or default fill.
                    for name, fields in prior['snapshot']['pose'].items():
                        p = rig.pose.bones[name]
                        p.rotation_mode = fields['rotation_mode']
                        for field, values in fields.items():
                            if field != 'rotation_mode': setattr(p, field, values)
                        for key, value in prior['pb_properties'][name].items(): p[key] = value
                    view_layer.update()
                    after_prior = comp._prior(ctx, rig)
                    require(light.plain(after_prior) == light.plain(prior) and light.context_record(ctx, bpy) == before_context, 'Exact original pose/Action/slot/NLA/context restoration failed.')
                    require(ua._rest_state(rig.data) == before_rest and light.rna_record(saved) == before_worklist
                        and {p.name: [light.rna_record(c) for c in p.constraints] for p in rig.pose.bones} == before_constraints, 'Original Rest/Worklist/constraints changed.')
                    after_assets = oracle.asset_snapshot(scene, rig, ua)
                    require(not oracle.changes(before_assets, after_assets) and before_assets == after_assets, 'Full original assets differ at the restored frame.')
                    for role, action, slot in choices: require(motion(fp, action, slot) == proofs[role], 'An original selected-slot Action changed.')
                    report.update(context_and_pose_restored=True, full_assets_unchanged=True, before_assets=before_assets, after_assets=after_assets)
            runtime_files(root, files)
            for row in inputs.values(): pin(row['path'], row['sha256'])
            report['input_files_unchanged'] = True
        except Exception as error:
            report['restoration_or_disk_guard_error'] = type(error).__name__ + ': ' + str(error)
        report['completed'] = bool(report['legacy_clock_known'] and report.get('context_and_pose_restored')
            and report.get('full_assets_unchanged') and report.get('input_files_unchanged') and not report.get('error') and not report.get('restoration_or_disk_guard_error'))
        report['natural_background_shutdown_required_external_readback'] = True
        write(report_path, report)
        print('ORIGINAL_LEGACY_BASE_CLOCK ' + json.dumps({'completed': report['completed'], 'legacy_clock_known': report['legacy_clock_known'], 'report': pin(report_path, sha(report_path))}))
    if not report['completed']:
        raise RuntimeError(report.get('error') or report.get('restoration_or_disk_guard_error') or 'Clock certificate failed.')
    # Normal background completion; --python-exit-code1 handles a failed run.
    # No quit FINISHED value is ever represented as an observed process exit.


if __name__ == '__main__':
    main()
