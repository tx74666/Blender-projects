"""SOURCE ONLY: one future pure-helper read of the owned original snapshot.
No CD package init, registration, handlers, preview, Attach, model import,
Action creation, key edits or saves. Normal background exit is observed outside.
"""
import argparse
import hashlib
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
    if not value: raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
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
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def motion(fp, action, slot):
    proof = fp.fingerprint_action(action, slot)
    require(proof['fingerprint_known'] is True, 'Selected-slot content remains Unknown: ' + action.name)
    return proof


def pose(rig):
    return {p.name: {'rotation_mode': p.rotation_mode,
        'channels': {k: list(getattr(p, k)) for k in ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')},
        'properties': {k: p[k] for k in p.keys() if type(p[k]) in (bool, int, float)},
        'locks': {k: list(getattr(p, k)) if k in ('lock_location', 'lock_rotation', 'lock_scale') else getattr(p, k)
            for k in ('lock_location', 'lock_rotation', 'lock_scale', 'lock_rotation_w', 'lock_rotations_4d')}} for p in rig.pose.bones}


def raw_settings(block, light):
    # Detach scalar/array settings; never recurse through Bone parent/children.
    def array(value, dimensions):
        require(len(value) == dimensions[0], 'A declared RNA array dimension changed.')
        if len(dimensions) > 1:
            return [array(value[index], dimensions[1:]) for index in range(dimensions[0])]
        return light.plain([value[index] for index in range(dimensions[0])])

    value = {}
    for prop in block.bl_rna.properties:
        if prop.type in {'POINTER', 'COLLECTION'} or prop.identifier == 'rna_type':
            continue
        native = getattr(block, prop.identifier)
        if prop.is_array:
            dimensions = tuple(size for size in prop.array_dimensions if size > 0)
            require(1 <= len(dimensions) <= 3 and math.prod(dimensions) <= 10000,
                    'Unsupported or unbounded declared RNA array dimensions.')
            value[prop.identifier] = array(native, dimensions)
        else:
            value[prop.identifier] = light.plain(native)
    try: value['custom_properties'] = light.plain({str(k): block[k] for k in block.keys()})
    except TypeError as error:
        if str(error) != "bpy_struct.keys(): this type doesn't support IDProperties": raise
        value['custom_properties'] = {'$unsupported_idproperties': True}
    return value


def raw_assets(scene, rig, light, oracle):
    """Unchanged260b raw primitives only: no authenticated/derived ft imports."""
    meshes = [o for o in scene.objects if o.type == 'MESH' and (o.parent == rig or any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers))]
    widgets = {p.custom_shape for p in rig.pose.bones if p.custom_shape is not None}
    objects = sorted(set(meshes) | widgets | {rig}, key=lambda o: o.name)
    values = {'objects': {o.name: {'id': light.reference(o), 'data': light.reference(o.data) if o.data else None,
        'parent': light.reference(o.parent) if o.parent else None, 'parent_type': o.parent_type, 'parent_bone': o.parent_bone,
        'basis': [list(r) for r in o.matrix_basis], 'collections': sorted(c.name for c in o.users_collection),
        'modifiers': [light.rna_record(m) for m in o.modifiers]} for o in objects},
        'meshes': {o.name: oracle.mesh_content(o) for o in objects if o.type == 'MESH'},
        'materials': {m.name: oracle.material_content(m) for o in meshes for m in o.data.materials if m},
        'rest': {b.name: {'settings': raw_settings(b, light), 'parent': b.parent.name if b.parent else None} for b in rig.data.bones},
        'presentation': {p.name: {'bone_color': oracle.color(p.bone.color), 'pose_color': oracle.color(p.color),
            'collections': sorted(c.name for c in p.bone.collections), 'shape': oracle.identity(p.custom_shape),
            'transform': getattr(p.custom_shape_transform, 'name', None), 'size': p.use_custom_shape_bone_size,
            'scale': list(p.custom_shape_scale_xyz), 'rotation': list(p.custom_shape_rotation_euler),
            'translation': list(p.custom_shape_translation), 'wire': p.custom_shape_wire_width} for p in rig.pose.bones},
        'collections': [{'settings': raw_settings(c, light), 'parent': c.parent.name if c.parent else None, 'bones': sorted(b.name for b in c.bones)} for c in rig.data.collections_all],
        'shape_values': {o.name: {k.name: {'value': k.value, 'mute': k.mute} for k in o.data.shape_keys.key_blocks} for o in meshes if o.data.shape_keys},
        'properties': light.plain(dict(rig.items())), 'data_properties': light.plain(dict(rig.data.items()))}
    return {'raw_component_sha256': {k: oracle.digest(v) for k, v in values.items()},
        'skin_names': sorted(o.name for o in meshes), 'widget_count': len(widgets), 'derived_Forearm_controller_authentication': 'Unknown; no runtime registered.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-sha256', required=True)
    for name in EXPECTED:
        parser.add_argument('--' + name.replace('_', '-'), required=True)
        parser.add_argument('--' + name.replace('_', '-') + '-sha256', required=True)
    parser.add_argument('--output-root', required=True); parser.add_argument('--profile-root', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    inputs = {'source': pin(__file__, args.source_sha256)}
    for name, expected in EXPECTED.items():
        require(getattr(args, name + '_sha256') == expected, 'Use the actual held input: ' + name)
        inputs[name] = pin(getattr(args, name), expected)
    require(Path(inputs['protected_artist']['path']) == ARTIST.resolve(), 'Protect the real X.blend; never open it.')
    output, profile = Path(args.output_root).resolve(), Path(args.profile_root).resolve()
    require(output != ROUND and output.is_relative_to(ROUND) and output.is_dir() and not any(output.iterdir()), 'Use one new empty owned ROUND output child.')
    require(profile.is_relative_to(Path(r'D:\Codex\XV').resolve()) and profile.is_dir() and {p.name for p in profile.iterdir()} == {'CONFIG', 'DATAFILES'}, 'Use one fresh owned short profile.')
    for name in ('CONFIG', 'DATAFILES'):
        p = profile / name
        require(p.is_dir() and not any(p.iterdir()) and Path(os.environ['BLENDER_USER_' + name]).resolve() == p, 'Bind the empty owned profile ' + name)
    receipt = json.loads(Path(inputs['snapshot_receipt']['path']).read_text(encoding='utf-8-sig'))
    require(receipt['completed'] is True and receipt['backup_verified'] is True and receipt['metadata_preservation_verified'] is True
        and receipt['backup'] == inputs['seed'] and receipt['protected_artist'] == inputs['protected_artist'], 'Require actual99B successful metadata and seed1C198.')
    recorded = receipt['after']['full_worklist']['value']
    require(len(recorded['items']) == 1, 'Use the actual single-row snapshot baseline.')
    row = recorded['items'][0]
    manifest = json.loads(Path(inputs['package_manifest']['path']).read_text(encoding='utf-8-sig'))
    require(manifest['schema_version'] == 1 and manifest['module'] == 'character_designer' and manifest['version'] == '0.77.25' and len(manifest['files']) == 188, 'Use complete held R7 source.')
    root, files = Path(manifest['source_root']).resolve(), manifest['files']
    for relative, expected in files.items():
        p = (root / relative).resolve(); require(p.is_relative_to(root), 'A source path escaped its root.'); pin(p, expected)
    sys.dont_write_bytecode = True
    import bpy
    require(bpy.app.background and not bpy.data.filepath and tuple(bpy.app.version[:2]) == (5, 2), 'Require fresh background5.2 factory child; never artist process.')
    require(not any(n == 'character_designer' or n.startswith('character_designer.') for n in sys.modules), 'Do not inherit another CD runtime.')
    fp = load_helper({'path': str(root / 'animation_worklist_fingerprint.py'), 'sha256': files['animation_worklist_fingerprint.py']}, 'clock_pure_fp_r7')
    light = load_helper(receipt['source'], 'clock_snapshot6df'); oracle = load_helper(inputs['oracle'], 'clock_raw_assets260b')
    packet = json.loads(Path(inputs['packet']['path']).read_text(encoding='utf-8-sig'))
    require(len(packet['frames']) == 59, 'Use the unchanged E54559-frame packet.')
    report_path = output / 'original_legacy_base_clock_report.json'
    report = {'schema': 'x.validation.original-legacy-base-clock/1', 'completed': False, 'legacy_clock_known': False,
        'source_inputs': inputs, 'pid': os.getpid(), 'native_execution_performed': True, 'artist_opened_or_written': False,
        'package_init_executed': False, 'addon_registered': False, 'runtime_handlers_registered': False,
        'preview_Attach_generate_model_import_save_keys_performed': False, 'model_equivalence_verified': False,
        'world_runtime_certificate': 'Unknown: no registered controller/Forearm/driver namespace; native matrices are observations only.',
        'Input20_Source_or_Custom_created': False, 'natural_exit_verified': False, 'scope': 'Complete selected-slot Base content, key-clock proof and raw-asset restoration only.'}
    with report_path.open('x', encoding='utf-8') as stream: json.dump(report, stream, indent=2)
    prior, proofs, choices = None, {}, []
    try:
        require(bpy.ops.wm.open_mainfile(filepath=inputs['seed']['path'], use_scripts=False, load_ui=False) == {'FINISHED'}, 'Owned snapshot open did not finish.')
        require(Path(bpy.data.filepath).resolve() == Path(inputs['seed']['path']), 'Another file was loaded.')
        scene, rig = bpy.data.scenes.get('Scene'), bpy.data.objects.get('CoshaRig')
        require(scene is not None and rig is not None and rig.library is None and rig.data.library is None and rig in list(scene.objects), 'The exact original Scene/Rig is unavailable.')
        main_record = json.loads(rig['character_designer_worklist_main_session_v1']); refs = rig['character_designer_worklist_main_refs_v1']
        require(main_record['version'] == 1 and refs[main_record['rig']['$id']] == rig and refs[main_record['scene']['$id']] == scene
            and main_record['workspace_identity'] == recorded['workspace_identity'], 'The saved original adoption references/header changed.')
        require(rig.get('character_designer_animation_source_model_sha256') == recorded['model_sha256'] == '2ae2067c9794fc7767f6abb35b6af33df496986a006c870fc9d0dc47eaa55db5', 'The original2AE ownership changed.')
        custom = rig['character_designer_animation_link_action']; link = json.loads(rig['character_designer_animation_link'])
        require(link['action_name'] == row['custom_action']['name'] == custom.name and link['action_slot'] == row['custom_slot']
            and link['identity']['sourcePackageSha256'] == EXPECTED['packet'] and link['identity']['workItemId'].replace('-', '') == row['work_item_id'], 'The bound Custom native ID/slot/source owner changed.')
        baseline = json.loads(row['source_baseline_receipt'])
        require(baseline['schema'] == 'character-designer.animation-source-baseline/1' and baseline['workItemId'] == row['work_item_id']
            and baseline['source_hash'] == row['source_hash'] and EXPECTED['packet'] in baseline['identity'], 'The sealed Source-cache owner changed.')
        source_pin = pin(row['source_file'], baseline['source_hash'])
        sources = [a for a in bpy.data.actions if a.name == row['source_action']['name'] and a.library
            and Path(bpy.path.abspath(a.library.filepath)).resolve() == Path(source_pin['path'])]
        require(len(sources) == 1, 'The actual linked Source native ID is missing or ambiguous.')
        source = sources[0]
        for path in (recorded['workspace_path'], row['manifest_path'], row['source_file'], recorded['model_file']):
            p = Path(bpy.path.abspath(path)).resolve(); inputs['disk:' + str(p)] = pin(p, sha(p))
        view_layer = scene.view_layers.get('ViewLayer'); require(view_layer is not None and view_layer.objects.get(rig.name) == rig, 'The original ViewLayer is missing.')
        with bpy.context.temp_override(scene=scene, view_layer=view_layer):
            ctx, ad = bpy.context, rig.animation_data
            require(ad is not None and not ad.use_tweak_mode and ad.action == custom and ad.action_slot_handle == row['custom_slot'], 'Observe the saved exact active Base/slot outside Tweak.')
            prior = {'action': ad.action, 'slot': ad.action_slot, 'use_nla': ad.use_nla, 'blend': ad.action_blend_type,
                'influence': ad.action_influence, 'extrapolation': ad.action_extrapolation, 'pose': pose(rig),
                'scene_clock': (scene.render.fps, scene.render.fps_base, scene.frame_start, scene.frame_end),
                'context': light.context_record(ctx, bpy), 'constraints': {p.name: [light.rna_record(c) for c in p.constraints] for p in rig.pose.bones},
                'nla': [light.rna_record(t) for t in ad.nla_tracks], 'raw_worklist': light.plain(scene.get('character_designer_animation_worklist')),
                'assets': raw_assets(scene, rig, light, oracle)}
            choices = [('BASE_SOURCE', source, row['source_slot']), ('BASE_CUSTOM', custom, row['custom_slot'])]
            for role, action, slot in choices: proofs[role] = motion(fp, action, slot)
            report['selected_slot_proofs'] = proofs
            report['active_Base_proof'] = motion(fp, ad.action, ad.action_slot_handle)
            rate = scene.render.fps / scene.render.fps_base
            times_expected = [f32(1. + float(f['time']) * 30.) for f in packet['frames']]
            packet_rate = float(packet['sampleRate'])
            packet_rate_times = [f32(1. + float(f['time']) * packet_rate) for f in packet['frames']]
            source_curve_count, source30_mismatches, packet_rate_mismatches = 0, [], []
            with (output / 'selected_slot_curve_schedules.jsonl').open('x', encoding='utf-8') as stream:
                for role, action, slot in choices:
                    require(action.get('character_designer_unity_animation_package_sha256') == EXPECTED['packet'], 'An original packet seal changed.')
                    curves = list(fp._selected_curves(action, slot)); require(curves, 'A selected Base slot has no curves.')
                    for curve in curves:
                        times = [float(p.co.x) for p in curve.keyframe_points]; require(all(math.isfinite(v) for v in times), 'A native key time is nonfinite.')
                        stream.write(json.dumps({'role': role, 'path': curve.data_path, 'component': curve.array_index, 'key_times': times,
                            'modes': [[p.interpolation, p.easing, p.handle_left_type, p.handle_right_type] for p in curve.keyframe_points],
                            'sample_count': len(curve.sampled_points), 'modifier_count': len(curve.modifiers)}, ensure_ascii=False, allow_nan=False) + '\n')
                        if role == 'BASE_SOURCE':
                            source_curve_count += 1
                            if times != times_expected or curve.sampled_points: source30_mismatches.append([curve.data_path, curve.array_index])
                            if times != packet_rate_times or curve.sampled_points: packet_rate_mismatches.append([curve.data_path, curve.array_index])
            report.update(actual_Source_and_Custom_schedules_recorded=True, Source_curve_count=source_curve_count,
                Source30_candidate_mismatches=source30_mismatches,
                packet_rate_schedule_diagnostic={'sample_rate': packet_rate, 'Source_mismatches': packet_rate_mismatches,
                    'all_Source_curves_match': source_curve_count > 0 and not packet_rate_mismatches, 'automatic_rate_selection': False})
            require(scene.render.fps == 30 and scene.render.fps_base == 1. and rate == 30., 'Actual99B candidate is not30/1; do not guess another clock.')
            require(source_curve_count > 0 and not source30_mismatches, 'Source schedule does not prove30fps; actual schedules retained and clock remains Unknown.')
            report.update(legacy_clock_known=True, verified_legacy_action_rate=rate, proof_scope='Stored Source key-time units only; no native import marker or runtime-world equivalence.')
            names = main_record['mapped_names']; require(names and all(n in rig.pose.bones for n in names), 'A saved mapped native bone disappeared.')
            try:
                with (output / 'body_world_observations.jsonl').open('x', encoding='utf-8') as stream:
                    for role, action, slot in choices:
                        slots = [s for s in action.slots if s.handle == slot]; require(len(slots) == 1, 'A selected native Action slot disappeared.')
                        ad.action, ad.action_slot = action, slots[0]; ad.use_nla, ad.action_blend_type, ad.action_influence = False, 'REPLACE', 1.
                        for index, frame in enumerate(packet['frames']):
                            native_frame = 1. + float(frame['time']) * rate; integer = math.floor(native_frame)
                            scene.frame_set(integer, subframe=native_frame - integer); view_layer.update()
                            evaluated = rig.evaluated_get(ctx.evaluated_depsgraph_get())
                            worlds = {n: [float(v) for r in (evaluated.matrix_world @ evaluated.pose.bones[n].matrix) for v in r] for n in names}
                            require(all(math.isfinite(v) for values in worlds.values() for v in values), 'A diagnostic native world matrix is nonfinite.')
                            stream.write(json.dumps({'role': role, 'index': index, 'packet_time': frame['time'], 'native_frame': native_frame, 'worlds': worlds,
                                'runtime_equivalence': 'Unknown'}, allow_nan=False) + '\n')
                report.update(Source_world_observations=59, Custom_world_observations=59, observed_bone_count=len(names), Custom_forced_equal_Source=False, graph_Unknown_not_promoted=True)
            except Exception as error:
                report['world_observation_error_Unknown'] = type(error).__name__ + ': ' + str(error)
    except Exception as error: report.update(error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
    finally:
        try:
            if prior is not None:
                with bpy.context.temp_override(scene=scene, view_layer=view_layer):
                    ad.action, ad.action_slot = prior['action'], prior['slot']; ad.use_nla = prior['use_nla']
                    ad.action_blend_type, ad.action_influence, ad.action_extrapolation = prior['blend'], prior['influence'], prior['extrapolation']
                    frame = prior['context']['frame'] + prior['context']['subframe']; integer = math.floor(frame)
                    scene.frame_set(integer, subframe=frame - integer)
                    for name, old in prior['pose'].items():
                        p = rig.pose.bones[name]; p.rotation_mode = old['rotation_mode']
                        for field, values in old['channels'].items(): setattr(p, field, values)
                        for key, value in old['properties'].items(): p[key] = value
                        for field, value in old['locks'].items(): setattr(p, field, value)
                    view_layer.update()
                    require(ad.action == prior['action'] and ad.action_slot_handle == prior['slot'].handle and ad.use_nla == prior['use_nla']
                        and (ad.action_blend_type, ad.action_influence, ad.action_extrapolation) == (prior['blend'], prior['influence'], prior['extrapolation'])
                        and (scene.render.fps, scene.render.fps_base, scene.frame_start, scene.frame_end) == prior['scene_clock'], 'Original Action/slot/NLA evaluation settings or scene clock changed.')
                    require(light.context_record(bpy.context, bpy) == prior['context'] and pose(rig) == prior['pose'], 'Exact observed unkeyed pose/context restoration failed.')
                    require([light.rna_record(t) for t in ad.nla_tracks] == prior['nla']
                        and {p.name: [light.rna_record(c) for c in p.constraints] for p in rig.pose.bones} == prior['constraints']
                        and light.plain(scene.get('character_designer_animation_worklist')) == prior['raw_worklist'], 'Original NLA/constraints/raw Worklist changed.')
                    after_assets = raw_assets(scene, rig, light, oracle); require(after_assets == prior['assets'], 'Complete observed raw asset data changed at the restored frame.')
                    for role, action, slot in choices:
                        if role in proofs: require(motion(fp, action, slot) == proofs[role], 'Original selected-slot content changed.')
                    report.update(context_and_pose_restored=True, raw_asset_data_unchanged=True, before_assets=prior['assets'], after_assets=after_assets,
                        raw_worklist_accessible=prior['raw_worklist'] is not None, full_Worklist_RNA_and_runtime_controller_authentication='Unknown; no registration performed.')
            require(not any(n == 'character_designer' or n.startswith('character_designer.') for n in sys.modules), 'A helper unexpectedly loaded the CD package/runtime.')
            for row_pin in inputs.values(): pin(row_pin['path'], row_pin['sha256'])
            for relative, expected in files.items(): pin(root / relative, expected)
            report['input_files_unchanged'] = True
        except Exception as error: report['restoration_or_disk_guard_error'] = type(error).__name__ + ': ' + str(error)
        report['completed'] = bool(report['legacy_clock_known'] and report.get('context_and_pose_restored') and report.get('raw_asset_data_unchanged')
            and report.get('input_files_unchanged') and not report.get('error') and not report.get('restoration_or_disk_guard_error'))
        report['natural_background_shutdown_required_external_readback'] = True
        write(report_path, report)
        print('ORIGINAL_LEGACY_BASE_CLOCK ' + json.dumps({'completed': report['completed'], 'legacy_clock_known': report['legacy_clock_known'], 'report': pin(report_path, sha(report_path))}))
    if not report['completed']: raise RuntimeError(report.get('error') or report.get('restoration_or_disk_guard_error') or 'Clock certificate failed.')
    # Background returns naturally. --python-exit-code1 handles failure; a
    # quit operator FINISHED is never treated as observed natural process exit.


if __name__ == '__main__': main()
