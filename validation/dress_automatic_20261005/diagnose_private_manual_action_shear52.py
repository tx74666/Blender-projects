"""Read the fixed failed Manual snapshot; diagnose real worker shear, never export.

Root alone may run this in a disposable Blender 5.2 process. It reuses the v2
private admission seams and unchanged Direct preflight/strip and worker gates.
An expected refusal is diagnostic evidence, never Native/FBX/public acceptance.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V2 = HERE/'verify_private_manual_action_fbx_component52_v2.py'
V2_SHA = '10bae6fd1a042bce5ca60344371e1e4de54a379518e0fe8d6ba0a02a928ac373'
FAILED = HERE/'actual_private_manual_action_fbx_component_v2_52_20261008_030559_863_08d4ef178af74bc8a0f85901014c0d06/result/report.json'
FAILED_SHA = '2cff8bd542ac357826c091d790e10a6285c6d5c398156cdc981a1a5507ff5d97'
DERIVED = FAILED.parent/'cdesigner-action-manual-qa/animation.blend'
DERIVED_SHA = 'e83ddc978a04484d8f3c6cc263c5d085e5cab1d50bb1682c71046b1d6c363cc8'
BONE = 'SK_Dress_DEF_01_01'
ACTION = '.QA Private Manual Bone Action'
EXPECTED_ERROR = (BONE + ' at sample 1: shear cannot be represented by FBX TRS channels '
                  '(error 0.000189118).')
IDENTITY = dict(source='Dress', rig='CoshaRig', body='Cosha',
                owner='857c5aaad1ac4160953847b083deba20', scene='Scene')


def need(value, message):
    if not value:
        raise RuntimeError('ManualShearDiagnostic52: ' + message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def matrix_error(first, second):
    return max(abs(first[i][j] - second[i][j]) for i in range(4) for j in range(4))


def matrix_info(matrix):
    from mathutils import Matrix
    need(all(math.isfinite(value) for row in matrix for value in row), 'Non-finite diagnostic matrix')
    location, rotation, scale = matrix.decompose()
    restored = Matrix.LocRotScale(location, rotation, scale)
    columns = [matrix.to_3x3().col[index].copy() for index in range(3)]
    lengths = [column.length for column in columns]
    need(min(lengths) > 1e-12, 'Singular diagnostic matrix columns')
    dots = [columns[i].dot(columns[j])/(lengths[i]*lengths[j])
            for i, j in ((0, 1), (0, 2), (1, 2))]
    return dict(matrix=[list(row) for row in matrix], determinant=matrix.to_3x3().determinant(),
                decomposed_scale=list(scale), TRS_reconstruction_residual=matrix_error(matrix, restored),
                column_lengths=lengths, normalized_column_dots_xy_xz_yz=dots,
                maximum_column_nonorthogonality=max(abs(value) for value in dots))


def bone_info(bone):
    return dict(name=bone.name, parent=bone.parent.name if bone.parent else None,
                Rest=[list(row) for row in bone.matrix_local], length=bone.length,
                use_connect=bone.use_connect, use_deform=bone.use_deform,
                inherit_scale=bone.inherit_scale, use_inherit_rotation=bone.use_inherit_rotation,
                use_local_location=bone.use_local_location)


def basis_info(bone, poses):
    from mathutils import Matrix
    need(bone.name in poses and (bone.parent is None or bone.parent.name in poses),
         'A real sampled parent matrix is missing; do not substitute the current Pose')
    parent = (dict(parent_matrix=poses[bone.parent.name], parent_matrix_local=bone.parent.matrix_local)
              if bone.parent else {})
    basis = bone.convert_local_to_pose(poses[bone.name], bone.matrix_local, invert=True, **parent)
    restored = Matrix.LocRotScale(*basis.decompose())
    result = matrix_info(basis)
    result.update(forward_exact_basis_error=matrix_error(
        bone.convert_local_to_pose(basis, bone.matrix_local, **parent), poses[bone.name]),
        forward_TRS_basis_error=matrix_error(
        bone.convert_local_to_pose(restored, bone.matrix_local, **parent), poses[bone.name]))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-script-sha', required=True)
    parser.add_argument('--soft-seconds', type=float, default=180.)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE.resolve())
         and not args.output.exists(), 'Use one fresh owned Validation output')
    args.output.mkdir(parents=True)
    started = time.perf_counter()
    report = dict(scope='PRIVATE_MANUAL_ACTION_EXPECTED_SHEAR_DIAGNOSTIC_ONLY', errors=[],
        diagnostic_complete=False, expected_worker_shear_refusal=False, worker_export_succeeded=False,
        FBX_write_attempted=False, FBX_roundtrip_verified=False, native_component_verified=False,
        public_admission_verified=False, public_export_verified=False, production_model_binding_verified=False,
        Unity_verified=False, Magica_verified=False, simulation_baked=False, vertex_Cloth_carried_by_bones=False,
        final_surface_equivalent=False, export_accepted=False, current_X_loaded=False,
        snapshot_raw_named_weights_Rest_Body12_assets_exact=False, sampled_source_protected=False,
        owned_native_cleanup=False, private_scene_disposed=False, pinned_files_unchanged=False)
    bpy = v2 = rest = inventory = home = boundary = worker = q = rig = selected = None
    prior_record = prior_prepare = None
    pins = {}
    pre_strip = []
    pre_strip_basis = []

    def write():
        (args.output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')

    def phase(label):
        report['phase'] = label
        report.setdefault('phases', []).append(dict(name=label, seconds=time.perf_counter()-started))
        write()
        print(json.dumps(dict(ManualShear_phase=label)), flush=True)
        need(time.perf_counter()-started <= args.soft_seconds, 'Soft diagnostic budget exceeded')

    try:
        need(sha(V2) == V2_SHA and sha(FAILED) == FAILED_SHA and sha(DERIVED) == DERIVED_SHA
             and sha(Path(__file__).resolve()) == args.expected_script_sha, 'Fixed diagnostic pins differ')
        failed = json.loads(FAILED.read_text(encoding='utf-8'))
        need(failed['errors'][0]['error'] == "AnimationExportError(" + repr(EXPECTED_ERROR) + ")"
             and failed['native_component_verified'] is False
             and Path(failed['derived_Action_snapshot']['path']).resolve() == DERIVED.resolve()
             and failed['derived_Action_snapshot']['sha256'] == DERIVED_SHA,
             'The fixed report is not the expected failed worker/snapshot')
        v2 = load(V2, 'manual_shear_v2_helpers')
        need(sha(v2.REST) == v2.REST_SHA, 'REST helper pin differs before loading')
        rest = load(v2.REST, 'manual_shear_rest_helpers')
        pins = {Path(path): value for path, value in failed['pins'].items()}
        pins.update({FAILED: FAILED_SHA, DERIVED: DERIVED_SHA, Path(__file__).resolve(): args.expected_script_sha})
        need(all(sha(path) == value for path, value in pins.items()), 'Historical input/source pin differs')
        report['pins'] = {str(path): value for path, value in pins.items()}
        report['loaded_input'] = dict(path=str(DERIVED), sha256=DERIVED_SHA, failed_report_sha256=FAILED_SHA,
                                      parent_PNS_sha256=failed['derived_Action_snapshot']['parent_PNS_sha256'])
        import bpy as native_bpy
        from mathutils import Matrix
        bpy = native_bpy
        need(bpy.app.background and tuple(bpy.app.version) == (5, 2, 0)
             and Path(bpy.app.binary_path).resolve() == Path('D:/Blender5.2/blender.exe').resolve(),
             'Use only the fixed disposable Blender 5.2 executable')
        phase('load_fixed_derived_only')
        bpy.ops.wm.open_mainfile(filepath=str(DERIVED), load_ui=False)
        home = bpy.data.scenes.get(IDENTITY['scene'])
        source, rig, body = (bpy.data.objects[IDENTITY[key]] for key in ('source', 'rig', 'body'))
        need(home is not None and all(home.objects.get(obj.name) == obj for obj in (source, rig, body)),
             'Derived snapshot lost its recorded native home')
        need(not any(m.show_viewport or m.show_render for obj in bpy.data.objects for m in obj.modifiers
                     if m.type == 'CLOTH'), 'Active Cloth is forbidden before diagnostic evaluation')
        bpy.context.window.scene = home
        bpy.context.view_layer.update()
        inventory = {kind: {item.as_pointer() for item in getattr(bpy.data, kind)} for kind in rest.ID_KINDS}
        q = rest.readers(rest.QA, ('digest', 'id_name', 'raw_mesh_content', 'rest_content', 'pose_channels'), bpy)
        worker = load(v2.RUNTIME/'animation_export_worker.py', 'manual_shear_worker_helpers')
        boundary = worker._dress_snapshot_helpers()
        direct = __import__(boundary.__package__ + '.skirt_surface_direct', fromlist=['skirt_surface_direct'])
        record = direct.skirt.read_record(source)
        need(record['owner'] == IDENTITY['owner'] and record['rig'] == IDENTITY['rig']
             and record['physics']['backend'] == direct.BACKEND and source.data.shape_keys is None
             and body.data.shape_keys is not None and len(body.data.shape_keys.key_blocks) == 12,
             'Fixed Direct no-Key Dress/Body12 differs')
        direct.validate(source, rig, record)
        selected = bpy.data.actions[ACTION]
        ad = rig.animation_data
        need(ad is not None and ad.action is selected and ad.action_slot is not None
             and not ad.use_nla and not ad.nla_tracks and not ad.use_tweak_mode,
             'Derived selected Action/slot/NLA assignment differs')
        slot = worker._slot(rig, selected, ad.action_slot.handle)
        names = {kind: sorted(item.name for item in getattr(bpy.data, kind))
                 for kind in ('actions', 'materials', 'images')}
        names['meshes'] = failed['derived_snapshot_scope']['snapshot_mesh_objects']
        v2.snapshot_mesh_scope([tuple(item) for item in failed['derived_snapshot_scope']['snapshot_mesh_identities']],
            [q.id_name(obj) for obj in bpy.data.objects if obj.type == 'MESH'])
        immutable_before = v2.immutable_state(bpy, q, rig, names)
        assets_before = v2.asset_state(bpy, worker, names)
        report['snapshot_initial_immutable_digest'] = q.digest(immutable_before)
        need(report['snapshot_initial_immutable_digest'] == failed['derived_snapshot_scope']['projected_immutable_digest'],
             'Derived immutable receipt differs from the fixed pre-write projection')
        try:
            worker._direct_export_guard().animation_host_admission(bpy.data.objects, rig, selected, slot.handle)
        except ValueError as error:
            need('Direct Dress export validation is pending' in str(error), 'Public refusal has an unrelated cause')
            report['public_admission_refusal'] = str(error)
        else:
            raise RuntimeError('Public Direct admission unexpectedly opened')
        prior_record, prior_prepare = boundary._record, boundary.prepare_animation_snapshot

        def proved_record(obj):
            raw = obj.get(boundary.RECORD_KEY)
            parsed = json.loads(raw) if type(raw) is str else None
            if isinstance(parsed, dict) and parsed.get('physics', {}).get('backend') == direct.BACKEND:
                need(obj is source and obj.name == IDENTITY['source'] and parsed['owner'] == IDENTITY['owner']
                     and parsed['rig'] == IDENTITY['rig'] and obj.get(boundary.RIG_KEY) == rig,
                     'Private record seam encountered another Direct source')
                direct.validate(obj, rig, parsed)
                return parsed
            return prior_record(obj)

        boundary._record = proved_record
        boundary._physical_animation_guard(source, record, selected)
        helpers = worker._model_helpers()
        retained = [bone.name for bone in rig.data.bones if not helpers._is_control(bone)]
        need(len(retained) == 217 and BONE in retained, 'Fixed retained skeleton differs')
        report['before_strip_bone'] = bone_info(rig.data.bones[BONE])
        initial_frame = home.frame_current_final
        phase('three_real_QA_frames_before_strip')
        for frame in (1., 2., 3.):
            worker._frame(home, frame)
            bpy.context.view_layer.update()
            evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
            poses = {bone.name: bone.matrix.copy() for bone in evaluated.pose.bones}
            pre_strip.append(poses)
            pre_strip_basis.append(basis_info(rig.data.bones[BONE], poses))
        worker._frame(home, initial_frame)
        bpy.context.view_layer.update()
        need(v2.immutable_state(bpy, q, rig, names) == immutable_before
             and v2.asset_state(bpy, worker, names) == assets_before, 'Pre-strip sampling changed protected inputs')
        proofs = boundary.capture_animation_surfaces(bpy.context, rig, selected)
        need(len(proofs) == 1 and proofs[0]['source'] == source.name
             and boundary.snapshot_scene_roots(proofs) == {home}, 'Complete Direct capture/home proof differs')
        direct.validate_snapshot(source, proofs[0])
        job = dict(rig=rig.name, action=selected.name, action_slot=slot.handle,
            frame_start=1., frame_end=3., fps=home.render.fps, fps_base=home.render.fps_base,
            sample_rate=home.render.fps/home.render.fps_base, unit_scale=home.unit_settings.scale_length,
            loop=False, name=selected.name, filename='FORBIDDEN_diagnostic.fbx', export_rig_name=IDENTITY['rig'],
            stage=str(args.output/'forbidden_fbx'), dress_surfaces=proofs,
            dress_snapshot_path=str(DERIVED), unsupported_channels=[])

        def prepared_with_receipt(*values, **options):
            result = prior_prepare(*values, **options)
            direct._closure(source, rig, direct.skirt.read_record(source))
            need(len(result) == 1 and result[0]['physics_omitted'] and result[0]['manual_original_preserved'],
                 'Real strip receipt differs')
            report['source_after_strip'] = v2.sampled_source_state(q, worker, rig, selected)
            report['strip_receipt'] = result
            return result

        boundary.prepare_animation_snapshot = prepared_with_receipt
        private_tree, removed = v2.private_worker_node()
        fbx_calls = [node for node in ast.walk(private_tree) if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Attribute) and ast.unparse(node.func) == 'bpy.ops.export_scene.fbx']
        need(len(fbx_calls) == 1, 'Pinned worker FBX boundary differs')
        forbidden_line = fbx_calls[0].lineno
        worker_path = str(v2.RUNTIME/'animation_export_worker.py')
        report['private_adaptations'] = [
            dict(module=worker_path, removed_from_in_memory_copy_only=ast.unparse(removed),
                 all_other_worker_AST_unchanged=True),
            dict(module=str(v2.RUNTIME/'dress_export_snapshot.py'), function='_record',
                 scope='Only fixed Direct source; real direct.validate, capture, endpoint preflight and strip retained'),
            dict(scope='Read-only trace stops before the native FBX call if shear unexpectedly disappears',
                 writer_line=forbidden_line, worker_TRS_threshold_unchanged=worker.MATRIX_TOLERANCE)]
        exec(compile(private_tree, worker_path, 'exec'), worker.__dict__)

        def prevent_fbx(frame, event, arg):
            if event == 'line' and frame.f_lineno == forbidden_line:
                report['FBX_write_attempted'] = True
                raise RuntimeError('Unexpected worker reached the forbidden FBX write boundary')
            return prevent_fbx

        def trace_worker(frame, event, arg):
            if frame.f_code.co_name == 'private_component_export_job' and frame.f_code.co_filename == worker_path:
                return prevent_fbx
            return None

        phase('unchanged_real_worker_expected_refusal')
        prior_trace = sys.gettrace()
        try:
            sys.settrace(trace_worker)
            try:
                worker.private_component_export_job(job)
            except Exception as error:
                report['observed_worker_error'] = dict(error=repr(error), traceback=traceback.format_exc())
                need(isinstance(error, worker.AnimationExportError) and str(error) == EXPECTED_ERROR,
                     'The real worker did not fail at the exact expected shear gate')
                frames = []
                tb = error.__traceback__
                while tb is not None:
                    if tb.tb_frame.f_code.co_name == 'private_component_export_job':
                        frames.append(tb.tb_frame)
                    tb = tb.tb_next
                need(len(frames) == 1, 'Expected one real private worker traceback frame')
                local = frames[0].f_locals
                samples, export_rig, failed_bone = local['samples'], local['export_rig'], local['bone']
                need(local['rig'] is rig and failed_bone.name == BONE and local['index'] == 1
                     and len(samples) == 3 and set(local['retained']) == set(retained)
                     and all(set(poses) == set(retained) for _world, poses in samples), 'Worker failure/sample identity differs')
                source_bone, export_bone = rig.data.bones[BONE], export_rig.data.bones[BONE]
                report['actual_bones'] = dict(source=bone_info(source_bone), export=bone_info(export_bone),
                    source_parent=bone_info(source_bone.parent) if source_bone.parent else None,
                    export_parent=bone_info(export_bone.parent) if export_bone.parent else None)
                report['traceback_failed_basis'] = matrix_info(local['basis'])
                # Capture ALL original bones only by evaluating the same three
                # explicit frames. Export conversion always uses traceback samples.
                post_strip = []
                previous_scene = bpy.context.window.scene
                try:
                    bpy.context.window.scene = local['source_scene']
                    for frame in (1., 2., 3.):
                        worker._frame(local['source_scene'], frame)
                        bpy.context.view_layer.update()
                        evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
                        post_strip.append({bone.name: bone.matrix.copy() for bone in evaluated.pose.bones})
                finally:
                    bpy.context.window.scene = previous_scene
                    bpy.context.view_layer.update()
                diagnostics = []
                for index, (world, poses) in enumerate(samples):
                    pre, post = pre_strip[index], post_strip[index]
                    difference = max(matrix_error(pre[name], poses[name]) for name in retained)
                    reevaluated_difference = max(matrix_error(post[name], poses[name]) for name in retained)
                    parent_names = {bone.parent.name for bone in (source_bone, export_bone) if bone.parent}
                    need(export_bone.parent is None or export_bone.parent.name in poses,
                         'Actual worker samples omitted the export parent')
                    source_available = source_bone.parent is None or source_bone.parent.name in poses
                    unavailable = dict(unavailable='Original parent was filtered from captured worker.samples; no substitute matrix used')
                    diagnostics.append(dict(sample_index=index, original_QA_frame=index+1,
                        worker_world=matrix_info(world), worker_pose=matrix_info(poses[BONE]),
                        worker_parent_poses={name: matrix_info(poses[name]) if name in poses else unavailable
                                             for name in sorted(parent_names)},
                        before_strip_pose=matrix_info(pre[BONE]),
                        before_strip_parent_poses={name: matrix_info(pre[name]) for name in sorted(parent_names)},
                        before_strip_source_basis=pre_strip_basis[index],
                        captured_worker_source_basis=basis_info(source_bone, poses) if source_available else unavailable,
                        post_strip_all_source_re_evaluated_pose=matrix_info(post[BONE]),
                        post_strip_all_source_parent_poses={name: matrix_info(post[name]) for name in sorted(parent_names)},
                        post_strip_all_source_re_evaluated_basis=basis_info(source_bone, post),
                        actual_worker_export_basis=basis_info(export_bone, poses),
                        all_217_pre_strip_vs_worker_pose_maxcomponent=difference,
                        all_217_pre_strip_vs_worker_strict_2e5_pass=difference <= worker.MATRIX_TOLERANCE,
                        all_217_post_strip_re_evaluated_vs_captured_maxcomponent=reevaluated_difference,
                        all_217_post_strip_re_evaluated_vs_captured_strict_2e5_pass=reevaluated_difference <= worker.MATRIX_TOLERANCE))
                report['samples'] = diagnostics
                report['captured_vs_recomputed_export_basis_maxcomponent'] = matrix_error(
                    local['basis'], Matrix(diagnostics[1]['actual_worker_export_basis']['matrix']))
                need(report['captured_vs_recomputed_export_basis_maxcomponent'] <= worker.MATRIX_TOLERANCE,
                     'Recomputed export basis differs from the real captured failure')
                report['expected_worker_shear_refusal'] = True
            else:
                report['worker_export_succeeded'] = True
                raise RuntimeError('Worker unexpectedly succeeded; this diagnostic cannot accept an export')
        finally:
            sys.settrace(prior_trace)
        need(not any(args.output.rglob('*.fbx')), 'An FBX file was created by the diagnostic')
        report['runtime_closure'] = v2.runtime_closure(rest)
        report['snapshot_raw_named_weights_Rest_Body12_assets_exact'] = (
            v2.immutable_state(bpy, q, rig, names) == immutable_before
            and v2.asset_state(bpy, worker, names) == assets_before)
        report['sampled_source_protected'] = (v2.sampled_source_state(q, worker, rig, selected)
                                              == report['source_after_strip'])
        need(report['snapshot_raw_named_weights_Rest_Body12_assets_exact'] and report['sampled_source_protected'],
             'Real worker failure changed protected source data/Rest/Body channels/Actions/assets')
        phase('matrix_diagnostic_captured')
    except Exception as error:
        report['errors'].append(dict(error=repr(error), traceback=traceback.format_exc()))
    finally:
        if boundary is not None:
            if prior_record is not None:
                boundary._record = prior_record
            if prior_prepare is not None:
                boundary.prepare_animation_snapshot = prior_prepare
        if bpy is not None:
            if inventory is not None:
                try:
                    report['cleanup'] = rest.cleanup_owned(bpy, home, inventory)
                    report['owned_native_cleanup'] = report['cleanup']['success']
                except Exception as error:
                    report['errors'].append(dict(owned_cleanup=repr(error)))
            try:
                result = bpy.ops.wm.read_factory_settings(use_empty=True)
                report['factory_ID_counts'] = {kind: len(getattr(bpy.data, kind)) for kind in rest.ID_KINDS}
                report['private_scene_disposed'] = ('FINISHED' in result and not bpy.data.filepath
                    and all(len(getattr(bpy.data, kind)) == 0 for kind in ('objects', 'meshes', 'armatures', 'actions', 'images')))
            except Exception as error:
                report['errors'].append(dict(factory_disposal=repr(error)))
        try:
            report['pinned_files_unchanged'] = bool(pins) and all(sha(path) == value for path, value in pins.items())
        except Exception as error:
            report['errors'].append(dict(pins_after=repr(error)))
        report['diagnostic_complete'] = (report['expected_worker_shear_refusal']
            and report['snapshot_raw_named_weights_Rest_Body12_assets_exact'] and report['sampled_source_protected']
            and report['owned_native_cleanup'] and report['private_scene_disposed'] and report['pinned_files_unchanged']
            and not report['FBX_write_attempted'] and not report['worker_export_succeeded'] and not report['errors'])
        report['elapsed_seconds'] = time.perf_counter()-started
        write()
    print(json.dumps(dict(diagnostic_complete=report['diagnostic_complete'], errors=report['errors'])), flush=True)
    return 0 if report['diagnostic_complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
