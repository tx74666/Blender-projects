"""Private native TRS/skin error quantification; Root alone may run this file.

Read only the fixed failed Action snapshot. A keeps raw800 ARM->SUBSURF and
the source Preserve Volume flag. B uses the canonical REST baker then standard
LBS on3040. C independently copies A and changes only Preserve Volume DQ->LBS.
All use the same projected native rig and3040-index Manual reference at QA frames1/2/3.
C-vs-A is also measured directly; do not subtract scalar maxima to attribute DQ.
This parent-before-child native projection is a diagnostic candidate, not the
current animation writer. No FBX, approximate export admission, or artist save.
"""
import argparse
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
DIAG = HERE/'diagnose_private_manual_action_shear52.py'
DIAG_SHA = 'bc71a9c2c348b63dda88a013d8b5823fce1c858fc320a15f792f41541a89fdb0'
DIAG_REPORT = HERE/'actual_private_manual_action_shear_diag_52_20261008_035034_386_029e8205033342a784ce22d13581d47d/result/report.json'
DIAG_REPORT_SHA = '72a3f6b821f9da5e304180e5e9f9488879aab48104ee7e151899ba6778137032'
ORDER_PROBE = HERE/'probe_skin_modifier_order52_v3.py'
ORDER_PROBE_SHA = '388c6ce264648bec4755c4054478299eab86ff23e8245c98ffd926a1c9ad3aab'
FROZEN_QUANT = HERE/'quantify_private_manual_trs_skin52.py'
FROZEN_QUANT_SHA = '1c74a2e891a7231e8f72a69f578170719343d9f91e4aed0679e200c3e96dceda'
FROZEN_QUANT_REPORT = HERE/'actual_private_manual_trs_skin_quant_52_20261008_043831_696_8a359cb3a40b45c4ac11ebbf17b030a1/result/report.json'
FROZEN_QUANT_REPORT_SHA = '411c3f0183e5a0e0a333f594cbd98e88332f78844286b6cf752842df12c4eafa'
# Reviewed current runtime only; historical files/receipts stay independently pinned.
CURRENT_RUNTIME_PINS = {
    'skirt_original_mode': 'd382e40c2be9771dd0ae6ac2bf7b3b668108535c8f930e2695702ee19d7e25ff',
    'skirt_physics': '4a033b3bae40c3dba52cb4a522173c3a7532c84ca5c04ee55ad712af98a406d1',
    'skirt_surface_direct': '7ac0faf70d4cd8db6bec4bbf3c71aad4187b8b295aed542bc09534bd59dda0f5',
}



def need(value, message):
    if not value:
        raise RuntimeError('ManualTRSSkinQuant52: ' + message)


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


def depth_groups(data):
    depths = {}
    for bone in data.bones:
        chain, current = [], bone
        while current is not None:
            need(current.name not in chain, 'Copied skeleton has a parent cycle')
            chain.append(current.name)
            current = current.parent
        depths[bone.name] = len(chain)-1
    return [[name for name in sorted(depths) if depths[name] == depth]
            for depth in range(max(depths.values())+1)]


def project_native(bpy, Matrix, copied, desired, groups, budget, error):
    """Use the actual projected parent at each depth, then native FK evaluation."""
    residuals = {}
    for names in groups:
        budget()
        bpy.context.view_layer.update()
        evaluated = copied.evaluated_get(bpy.context.evaluated_depsgraph_get())
        parents = {name: evaluated.pose.bones[name].matrix.copy() for name in desired}
        for name in names:
            bone = copied.data.bones[name]
            options = (dict(parent_matrix=parents[bone.parent.name], parent_matrix_local=bone.parent.matrix_local)
                       if bone.parent else {})
            basis = bone.convert_local_to_pose(desired[name], bone.matrix_local, invert=True, **options)
            need(all(math.isfinite(value) for row in basis for value in row)
                 and abs(basis.to_3x3().determinant()) > 1e-10, 'Nonfinite/singular desired basis: ' + name)
            location, rotation, scale = basis.decompose()
            need(min(scale) > 0., 'Mirrored/nonpositive projection scale: ' + name)
            projected = Matrix.LocRotScale(location, rotation, scale)
            residuals[name] = error(basis, projected)
            copied.pose.bones[name].matrix_basis = projected
        # Siblings are independent: their parents were evaluated at earlier depths.
        bpy.context.view_layer.update()
    actual = copied.evaluated_get(bpy.context.evaluated_depsgraph_get())
    poses = {name: actual.pose.bones[name].matrix.copy() for name in desired}
    errors = {name: error(poses[name], desired[name]) for name in desired}
    worst = max(errors, key=errors.__getitem__)
    local_worst = max(residuals, key=residuals.__getitem__)
    return poses, dict(all_217_pose_matrix_maxcomponent=errors[worst], worst_bone=worst,
        per_bone_matrix_maxcomponent=errors, desired_basis_TRS_residual_maxcomponent=residuals[local_worst],
        worst_desired_basis_bone=local_worst, desired_basis_residuals=residuals)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-script-sha', required=True)
    parser.add_argument('--soft-seconds', type=float, default=90.)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE.resolve())
         and not args.output.exists() and 0. < args.soft_seconds <= 90., 'Use fresh owned output and at most90s soft budget')
    args.output.mkdir(parents=True)
    started = time.perf_counter()
    report = dict(scope='PRIVATE_THREE_FRAME_NATIVE_TRS_SKIN_ERROR_QUANTIFICATION_V2_SINGLE_FACTOR_C_ONLY', errors=[],
        quantification_complete=False, Native_started=False, native_component_verified=False,
        model_export_verified=False, FBX_roundtrip_verified=False, public_admission_verified=False,
        public_export_verified=False, production_model_binding_verified=False, Unity_verified=False,
        Magica_verified=False, simulation_baked=False, vertex_Cloth_carried_by_bones=False,
        final_surface_equivalent=False, export_accepted=False, approximate_export_accepted=False,
        current_X_loaded=False, source_77_mesh_Rest_Body12_Actions_assets_protected=False,
        source_pose_channels_restored=False, owned_native_cleanup=False, private_scene_disposed=False,
        pinned_files_unchanged=False)
    report['candidate_scope'] = ('A: native source skin mode, raw800 ARM-before-SUBSURF, same3040 indices; '
        'B: canonical REST-baked3040 then native standard LBS, includes TRS/modifier-order/DQ-mode differences. '
        'C: independent copy of raw800 A, same ARM-before-SUBSURF and projected217 rig; only Preserve Volume DQ-to-LBS. '
        'C-vs-source includes TRS and skin-mode differences; directly paired C-vs-A isolates native DQ-to-LBS. '
        'Native greedy depth projection is different from the current writer using original sampled parents. '
        'No candidate is an accepted production approximation; original2e-5 TRS rejection stays intact. '
        'Reference has physical output omitted by the real Direct strip; it is not a Legacy baseline or baked Cloth. '
        'This C/A observation uses three explicitly reviewed current runtime files; it does not claim historical A reproduction.')
    bpy = diag = v2 = rest = worker = q = boundary = home = rig = source = selected = inventory = None
    prior_record = None
    pins = {}
    initial_frame = original_channels = immutable_before = assets_before = source_after_strip = names = None

    def write():
        (args.output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')

    def budget():
        need(time.perf_counter()-started <= args.soft_seconds, 'Soft quantification budget exceeded')

    def phase(label):
        report['phase'] = label
        report.setdefault('phases', []).append(dict(name=label, seconds=time.perf_counter()-started))
        write()
        print(json.dumps(dict(ManualTRSSkin_phase=label)), flush=True)
        budget()

    try:
        need(sha(DIAG) == DIAG_SHA and sha(DIAG_REPORT) == DIAG_REPORT_SHA
             and sha(FROZEN_QUANT) == FROZEN_QUANT_SHA
             and sha(FROZEN_QUANT_REPORT) == FROZEN_QUANT_REPORT_SHA
             and sha(Path(__file__).resolve()) == args.expected_script_sha, 'Diagnostic/predecessor/self pin differs')
        diag = load(DIAG, 'manual_trs_skin_diag_helpers')
        need(sha(diag.V2) == diag.V2_SHA and sha(diag.FAILED) == diag.FAILED_SHA
             and sha(diag.DERIVED) == diag.DERIVED_SHA, 'Fixed v2/failed Action input differs')
        failed = json.loads(diag.FAILED.read_text(encoding='utf-8'))
        evidence = json.loads(DIAG_REPORT.read_text(encoding='utf-8'))
        need(evidence['diagnostic_complete'] and evidence['expected_worker_shear_refusal']
             and not evidence['errors'] and not evidence['native_component_verified']
             and all(row['all_217_pre_strip_vs_worker_pose_maxcomponent'] == 0. for row in evidence['samples']),
             'Fixed actual shear evidence differs')
        v2 = load(diag.V2, 'manual_trs_skin_v2_helpers')
        pins = {Path(path): value for path, value in failed['pins'].items()}
        current_paths = {v2.RUNTIME/(name+'.py'): value for name, value in CURRENT_RUNTIME_PINS.items()}
        need(all(path in pins and v2.RUNTIME_PINS[path.stem] == pins[path] for path in current_paths),
             'Historical runtime pin-map relationship differs')
        parent_runtime_pins = {str(path): pins[path] for path in current_paths}
        # Detach this private helper instance's expectation map. No helper file,
        # runtime function, admission guard, or unknown module pin is changed.
        v2.RUNTIME_PINS = dict(v2.RUNTIME_PINS)
        v2.RUNTIME_PINS.update(CURRENT_RUNTIME_PINS)
        pins.update(current_paths)
        report['runtime_pin_adaptation'] = dict(scope='CURRENT_RUNTIME_SINGLE_FACTOR_C_A_DIAGNOSTIC_ONLY',
            source_only_review=True, native_runtime_equivalence_verified=False,
            historical_A_reproduction_claimed=False, private_helper_pin_map_cloned=True,
            parent_runtime_pins=parent_runtime_pins,
            current_runtime_pins={str(path): value for path, value in current_paths.items()},
            reviewed_changes={
                'skirt_original_mode': 'Only explicit clear(); withdraw Direct Cloth before real channel edits.',
                'skirt_physics': 'Only clear_cache/reset_simulation/bake_steps cache invalidation and failure guards.',
                'skirt_surface_direct': 'Only add invalidate_result(); validate/deform/capture/strip unchanged.'},
            review_limit='Source paths only; these entry points are not called by this fixed Manual quantification. '
                         'No Native equivalence proof, historical A metric reproduction, or Action writer acceptance.')
        pins.update({DIAG: DIAG_SHA, DIAG_REPORT: DIAG_REPORT_SHA, diag.FAILED: diag.FAILED_SHA,
                     diag.DERIVED: diag.DERIVED_SHA, ORDER_PROBE: ORDER_PROBE_SHA,
                     FROZEN_QUANT: FROZEN_QUANT_SHA, FROZEN_QUANT_REPORT: FROZEN_QUANT_REPORT_SHA,
                     Path(__file__).resolve(): args.expected_script_sha})
        need(all(sha(path) == value for path, value in pins.items()), 'Fixed helper/runtime/input pin differs')
        report['pins'] = {str(path): value for path, value in pins.items()}
        rest = load(v2.REST, 'manual_trs_skin_rest_helpers')
        import bpy as native_bpy
        from mathutils import Matrix
        bpy = native_bpy
        need(bpy.app.background and tuple(bpy.app.version) == (5, 2, 0)
             and Path(bpy.app.binary_path).resolve() == Path('D:/Blender5.2/blender.exe').resolve(),
             'Use only disposable fixed Blender5.2')
        report['Native_started'] = True
        phase('load_fixed_derived_only')
        bpy.ops.wm.open_mainfile(filepath=str(diag.DERIVED), load_ui=False)
        home = bpy.data.scenes.get(diag.IDENTITY['scene'])
        source, rig, body = (bpy.data.objects[diag.IDENTITY[key]] for key in ('source', 'rig', 'body'))
        need(home is not None and all(home.objects.get(obj.name) == obj for obj in (source, rig, body))
             and source.parent == rig and source.parent_type == 'OBJECT' and not source.parent_bone
             and source.data.shape_keys is None and body.data.shape_keys is not None
             and len(body.data.shape_keys.key_blocks) == 12 and rig.parent is None,
             'Fixed Direct Dress/MainRig/Body12 home/parent scope differs')
        need(not any(m.show_viewport or m.show_render for obj in bpy.data.objects for m in obj.modifiers
                     if m.type == 'CLOTH'), 'Active Cloth is forbidden')
        bpy.context.window.scene = home
        bpy.context.view_layer.update()
        inventory = {kind: {item.as_pointer() for item in getattr(bpy.data, kind)} for kind in rest.ID_KINDS}
        q = rest.readers(rest.QA, ('digest', 'id_name', 'raw_mesh_content', 'rest_content', 'pose_channels'), bpy)
        base = rest.readers(rest.BASE, ('native_mesh', 'geometry_pair'), bpy)
        cold = rest.readers(rest.COLD, ('error',), bpy)
        skin = rest.readers(rest.V3, ('native_skin',), bpy)
        worker = load(v2.RUNTIME/'animation_export_worker.py', 'manual_trs_skin_animation_helpers')
        boundary = worker._dress_snapshot_helpers()
        direct = __import__(boundary.__package__ + '.skirt_surface_direct', fromlist=['skirt_surface_direct'])
        record = direct.skirt.read_record(source)
        need(record['owner'] == diag.IDENTITY['owner'] and record['rig'] == diag.IDENTITY['rig']
             and record['physics']['backend'] == direct.BACKEND, 'Fixed Direct identity differs')
        direct.validate(source, rig, record)
        selected = bpy.data.actions[diag.ACTION]
        ad = rig.animation_data
        need(ad is not None and ad.action is selected and ad.action_slot is not None
             and not ad.use_nla and not ad.nla_tracks and not ad.use_tweak_mode, 'Selected QA Action/slot/NLA differs')
        slot = worker._slot(rig, selected, ad.action_slot.handle)
        names = {kind: sorted(item.name for item in getattr(bpy.data, kind))
                 for kind in ('actions', 'materials', 'images')}
        names['meshes'] = failed['derived_snapshot_scope']['snapshot_mesh_objects']
        need(len(names['meshes']) == 77, 'Fixed snapshot77 Mesh scope differs')
        v2.snapshot_mesh_scope([tuple(item) for item in failed['derived_snapshot_scope']['snapshot_mesh_identities']],
            [q.id_name(obj) for obj in bpy.data.objects if obj.type == 'MESH'])
        immutable_before = v2.immutable_state(bpy, q, rig, names)
        assets_before = v2.asset_state(bpy, worker, names)
        need(q.digest(immutable_before) == failed['derived_snapshot_scope']['projected_immutable_digest'],
             'Fixed snapshot immutable baseline differs')
        initial_frame = home.frame_current_final
        original_channels = q.digest(q.pose_channels(rig))
        try:
            worker._direct_export_guard().animation_host_admission(bpy.data.objects, rig, selected, slot.handle)
        except ValueError as error:
            need('Direct Dress export validation is pending' in str(error), 'Public refusal has another cause')
            report['public_admission_refusal'] = str(error)
        else:
            raise RuntimeError('Public Direct admission unexpectedly opened')
        prior_record = boundary._record

        def proved_record(obj):
            raw = obj.get(boundary.RECORD_KEY)
            parsed = json.loads(raw) if type(raw) is str else None
            if isinstance(parsed, dict) and parsed.get('physics', {}).get('backend') == direct.BACKEND:
                need(obj is source and parsed['owner'] == diag.IDENTITY['owner']
                     and parsed['rig'] == rig.name and obj.get(boundary.RIG_KEY) == rig,
                     'Private record seam encountered another Direct source')
                direct.validate(obj, rig, parsed)
                return parsed
            return prior_record(obj)

        boundary._record = proved_record
        proofs = boundary.capture_animation_surfaces(bpy.context, rig, selected)
        need(len(proofs) == 1 and proofs[0]['source'] == source.name
             and boundary.snapshot_scene_roots(proofs) == {home}, 'Complete real Direct capture/home differs')
        report['strip_receipt'] = boundary.prepare_animation_snapshot(rig, proofs, selected, private_snapshot=str(diag.DERIVED))
        need(len(report['strip_receipt']) == 1 and report['strip_receipt'][0]['physics_omitted']
             and report['strip_receipt'][0]['manual_original_preserved'], 'Real strip receipt differs')
        direct._closure(source, rig, direct.skirt.read_record(source))
        source_after_strip = v2.sampled_source_state(q, worker, rig, selected)
        helpers = worker._model_helpers()
        retained = [bone.name for bone in rig.data.bones if not helpers._is_control(bone)]
        need(len(retained) == 217 and len(source.data.vertices) == 800
             and [m.type for m in source.modifiers] == ['ARMATURE', 'SUBSURF']
             and all(m.show_viewport for m in source.modifiers) and source.modifiers[0].object == rig,
             'Native raw800 ARM-before-SUBSURF/retained217 scope differs')
        original_volume = source.modifiers[0].use_deform_preserve_volume
        need(original_volume is True, 'Single-factor C requires the fixed source DQ flag to be True')
        source_rest = q.rest_content(rig)
        source_rest_world = {name: rig.matrix_world @ rig.data.bones[name].matrix_local for name in retained}
        metres = home.unit_settings.scale_length
        need(math.isfinite(metres) and metres > 0., 'Unknown positive metre scale')
        phase('independent_cleaned217_and_REST_bake')
        copied = rig.copy()
        copied.data = rig.data.copy()
        copied.name = '.QA TRS Quantification Rig'
        home.collection.objects.link(copied)
        need(copied.data != rig.data, 'Armature data is not independent')
        for block in (copied, copied.data):
            helpers._clear_animation(block)
        for holder in (copied, *copied.pose.bones):
            for constraint in tuple(holder.constraints):
                holder.constraints.remove(constraint)
        need(copied.animation_data is None and copied.data.animation_data is None
             and not copied.constraints and all(not bone.constraints for bone in copied.pose.bones),
             'Copied rig still has constraints or animation/drivers')
        copied.parent = None
        copied.matrix_world = rig.matrix_world.copy()
        for bone in copied.pose.bones:
            bone.rotation_mode = 'QUATERNION'
            bone.matrix_basis = Matrix.Identity(4)

        def mesh_copy(label):
            obj = source.copy()
            obj.data = source.data.copy()
            obj.name = label
            inverse, basis = source.matrix_parent_inverse.copy(), source.matrix_basis.copy()
            obj.parent = copied
            obj.matrix_parent_inverse, obj.matrix_basis = inverse, basis
            obj.modifiers[0].object = copied
            home.collection.objects.link(obj)
            for block in (obj, obj.data):
                helpers._clear_animation(block)
                for key in tuple(block.keys()):
                    if key.startswith('character_designer_'):
                        del block[key]
            for constraint in tuple(obj.constraints):
                obj.constraints.remove(constraint)
            need(obj.data != source.data and obj.matrix_parent_inverse == inverse and obj.matrix_basis == basis,
                 'Independent Mesh parent inverse/basis differs')
            return obj

        mesh_a = mesh_copy('.QA TRS Native Order Dress')
        copied.data.pose_position = 'REST'
        bpy.context.view_layer.objects.active = copied
        copied.select_set(True)
        if copied.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        actual_retained = helpers._clean_skeleton(bpy.context, copied, [copied, mesh_a])
        need(set(actual_retained) == set(retained) and len(actual_retained) == 217, 'Cleaned source bone identities differ')
        for name in retained:
            old, bone = rig.data.bones[name], copied.data.bones[name]
            parent = old.parent
            while parent is not None and parent.name not in retained:
                parent = parent.parent
            need((bone.parent.name if bone.parent else None) == (parent.name if parent else None)
                 and not bone.use_connect and all(getattr(bone, field) == getattr(old, field) for field in
                    ('inherit_scale', 'use_inherit_rotation', 'use_local_location', 'use_deform')),
                 'Cleaned parent/inheritance/deform convention differs: ' + name)
        for block in (copied, copied.data, *copied.data.bones):
            for key in tuple(block.keys()):
                if key.startswith('character_designer_'):
                    del block[key]
        bpy.context.view_layer.update()
        cleaned_rest = q.rest_content(copied)
        rest_error = rest.matrix_errors([source_rest_world[name] for name in sorted(retained)],
            [copied.matrix_world @ copied.data.bones[name].matrix_local for name in sorted(retained)], metres)
        need(rest_error['translation_max_m'] <= rest.LIMIT_M and rest_error['linear_max_component'] <= rest.LINEAR_LIMIT
             and rest_error['homogeneous_max_component'] <= rest.LINEAR_LIMIT, 'Cleanup changed a retained Rest matrix')
        need(q.digest(q.raw_mesh_content(mesh_a)) == q.digest(q.raw_mesh_content(source)), 'Raw800 copy lost authored mesh fields')
        report['cleaned_skeleton'] = dict(count=217, names=sorted(retained), Rest_error=rest_error,
            fields=q.digest(cleaned_rest), parents={name: row['parent'] for name, row in cleaned_rest.items()})
        # Object.copy creates independent modifier RNA; Mesh.copy owns raw data.
        # Copy the already-cleaned A, avoiding another cleanup/parent/projection path.
        mesh_c = mesh_a.copy()
        mesh_c.data = mesh_a.data.copy()
        mesh_c.name = '.QA TRS Native Order LBS Dress'
        home.collection.objects.link(mesh_c)
        need(mesh_c != mesh_a and mesh_c != source and mesh_c.data != mesh_a.data
             and mesh_c.data != source.data and mesh_c.parent == mesh_a.parent == copied
             and mesh_c.matrix_parent_inverse == mesh_a.matrix_parent_inverse
             and mesh_c.matrix_basis == mesh_a.matrix_basis and len(mesh_c.data.vertices) == 800
             and q.digest(q.raw_mesh_content(mesh_c)) == q.digest(q.raw_mesh_content(mesh_a))
             and mesh_c.animation_data is None and mesh_c.data.animation_data is None
             and not mesh_c.constraints, 'Independent raw800 C differs from A outside its owned identity')

        def modifier_parameters(obj):
            rows = []
            for modifier in obj.modifiers:
                fields = {}
                for prop in modifier.bl_rna.properties:
                    if prop.is_readonly:
                        continue
                    value = getattr(modifier, prop.identifier)
                    if prop.type == 'POINTER':
                        need(value is None or isinstance(value, bpy.types.ID),
                             'Unproved writable modifier pointer: ' + prop.identifier)
                        value = None if value is None else value.as_pointer()
                    elif prop.type == 'ENUM' and isinstance(value, set):
                        value = tuple(sorted(value))
                    elif prop.is_array:
                        value = tuple(value)
                    else:
                        need(prop.type in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'},
                             'Unproved writable modifier field: ' + prop.identifier)
                    fields[prop.identifier] = value
                rows.append(dict(type=modifier.type, fields=fields))
            return rows

        a_parameters = modifier_parameters(mesh_a)
        need([row['type'] for row in a_parameters] == ['ARMATURE', 'SUBSURF']
             and modifier_parameters(mesh_c) == a_parameters
             and all(mesh_c.modifiers[i] != mesh_a.modifiers[i] for i in range(2))
             and mesh_c.modifiers[0].object == copied, 'C modifier RNA is not an independent exact A copy')
        mesh_c.modifiers[0].use_deform_preserve_volume = False
        c_parameters = [dict(type=row['type'], fields=dict(row['fields'])) for row in a_parameters]
        c_parameters[0]['fields']['use_deform_preserve_volume'] = False
        need(modifier_parameters(mesh_c) == c_parameters and modifier_parameters(mesh_a) == a_parameters,
             'C changed writable modifier parameters beyond Preserve Volume')
        report['C_single_factor'] = dict(raw_vertices=800, evaluated_vertices_required=3040,
            shared_projected_rig=True, independent_Object_and_Mesh_and_modifiers=True,
            modifier_order=['ARMATURE', 'SUBSURF'],
            sole_writable_modifier_difference=dict(index=0, field='use_deform_preserve_volume', A=True, C=False),
            writable_modifier_fields_checked=sum(len(row['fields']) for row in a_parameters),
            A_modifier_parameters=a_parameters, C_modifier_parameters=c_parameters,
            native_three_frame_observation_complete=False, Unity_execution_verified=False)
        mesh_b = mesh_copy('.QA TRS REST Baked LBS Dress')
        graph = bpy.context.evaluated_depsgraph_get()
        rest_target = base.native_mesh(mesh_a, graph)
        rest_skin = rest.ordered_skin(mesh_a, graph, skin)
        warnings = []
        report['canonical_REST_baker'] = helpers._bake_mesh(bpy.context, mesh_b, set(), warnings)
        mesh_b.modifiers[0].use_deform_preserve_volume = False
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        report['canonical_REST_bake_error'] = base.geometry_pair(cold, rest_target, base.native_mesh(mesh_b, graph), metres)
        baked_skin = rest.ordered_skin(mesh_b, graph, skin)
        need(len(rest_target['points']) == 3040 and len(mesh_b.data.vertices) == 3040
             and [m.type for m in mesh_b.modifiers] == ['ARMATURE'] and mesh_b.modifiers[0].object == copied
             and rest.skin_exact(rest_skin, baked_skin) and rest_skin['materials'] == baked_skin['materials']
             and report['canonical_REST_bake_error']['maximum_m'] <= rest.LIMIT_M,
             'Canonical REST bake lost same-index geometry/named skin fields')
        report['skin_modes'] = dict(source_PreserveVolume=original_volume, A_PreserveVolume=original_volume,
                                   B_PreserveVolume=False, B_target='standard native LBS; Unity execution unverified',
                                   C_PreserveVolume=False, C_target='same raw800 native ARM-before-SUBSURF; only DQ-to-LBS')
        report['bake_warnings'] = warnings
        copied.data.pose_position = 'POSE'
        groups = depth_groups(copied.data)
        report['projection_depth_batches'] = len(groups)
        report['samples'] = []
        phase('three_actual_Manual_frames_and_native_projection')
        for index, frame in enumerate((1., 2., 3.)):
            budget()
            worker._frame(home, frame)
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            evaluated = rig.evaluated_get(graph)
            desired = {name: evaluated.pose.bones[name].matrix.copy() for name in retained}
            source_world = evaluated.matrix_world.copy()
            reference = base.native_mesh(source, graph)
            reference_skin = rest.ordered_skin(source, graph, skin)
            source_mesh_world = source.evaluated_get(graph).matrix_world.copy()
            need(len(reference['points']) == 3040 and diag.matrix_error(desired[diag.BONE],
                 Matrix(evidence['samples'][index]['worker_pose']['matrix'])) <= worker.MATRIX_TOLERANCE,
                 'Actual Manual pose/surface differs from fixed diagnostic evidence')
            copied.matrix_world = source_world
            actual, matrices = project_native(bpy, Matrix, copied, desired, groups, budget, diag.matrix_error)
            graph = bpy.context.evaluated_depsgraph_get()
            row = dict(sample_index=index, QA_frame=frame, projection=matrices,
                original_bone_world_matrix_error=rest.matrix_errors(
                    [source_world @ desired[name] for name in sorted(retained)],
                    [copied.evaluated_get(graph).matrix_world @ actual[name] for name in sorted(retained)], metres))
            local_inverse = source_mesh_world.inverted()
            row['source_local_points'] = [list(local_inverse @ point) for point in reference['points']]
            observed_surfaces = {}
            for label, obj in (('A_same_ARM_before_SUBSURF_TRS_only', mesh_a),
                               ('B_REST_baked_LBS_TRS_order_skinmode_total', mesh_b),
                               ('C_same_ARM_before_SUBSURF_LBS_TRS_skinmode_only', mesh_c)):
                observed = base.native_mesh(obj, graph)
                observed_skin = rest.ordered_skin(obj, graph, skin)
                world_error = diag.matrix_error(obj.evaluated_get(graph).matrix_world, source_mesh_world)
                need(len(observed['points']) == 3040 and world_error <= worker.MATRIX_TOLERANCE
                     and rest.skin_exact(reference_skin, observed_skin)
                     and reference_skin['materials'] == observed_skin['materials'],
                     'Same-index3040/mesh frame/UV/materials/full named weights differ: ' + label)
                metric = base.geometry_pair(cold, reference, observed, metres)
                worst = metric['worst_index']
                metric.update(maximum_mm=metric['maximum_m']*1000., rms_mm=metric['rms_m']*1000.,
                    same_index_3040=True, ordered_topology_exact=True, all_named_skin_fields_exact=True,
                    materials_exact=True, mesh_world_maxcomponent=world_error,
                    diagnostic_within_original_0_05mm=metric['maximum_m'] <= rest.LIMIT_M,
                    worst_source_local=list(local_inverse @ reference['points'][worst]),
                    worst_candidate_local=list(local_inverse @ observed['points'][worst]),
                    candidate_source_local_points=[list(local_inverse @ point) for point in observed['points']])
                row[label] = metric
                observed_surfaces[label] = observed
            paired = base.geometry_pair(cold, observed_surfaces['A_same_ARM_before_SUBSURF_TRS_only'],
                observed_surfaces['C_same_ARM_before_SUBSURF_LBS_TRS_skinmode_only'], metres)
            paired.update(maximum_mm=paired['maximum_m']*1000., rms_mm=paired['rms_m']*1000.,
                same_index_3040=True, ordered_topology_exact=True, all_named_skin_fields_exact=True,
                materials_exact=True, comparison='C-vs-A on the same native projected217 rig; only DQ-to-LBS')
            row['C_vs_A_single_DQ_to_LBS'] = paired
            need(q.rest_content(copied) == cleaned_rest and q.rest_content(rig) == source_rest
                 and mesh_a.modifiers[0].use_deform_preserve_volume == original_volume
                 and mesh_b.modifiers[0].use_deform_preserve_volume is False
                 and mesh_c.modifiers[0].use_deform_preserve_volume is False
                 and modifier_parameters(mesh_a) == a_parameters
                 and modifier_parameters(mesh_c) == c_parameters
                 and q.digest(q.raw_mesh_content(mesh_c)) == q.digest(q.raw_mesh_content(mesh_a)),
                 'Projection changed source/cleaned Rest fields or native skin-mode scope')
            report['samples'].append(row)
            write()
        report['C_single_factor']['native_three_frame_observation_complete'] = len(report['samples']) == 3
        report['runtime_closure'] = v2.runtime_closure(rest)
        phase('three_frame_quantification_captured')
    except Exception as error:
        report['errors'].append(dict(error=repr(error), traceback=traceback.format_exc()))
    finally:
        if boundary is not None and prior_record is not None:
            boundary._record = prior_record
        if bpy is not None:
            if initial_frame is not None and q is not None:
                try:
                    bpy.context.window.scene = home
                    worker._frame(home, initial_frame)
                    bpy.context.view_layer.update()
                    report['source_77_mesh_Rest_Body12_Actions_assets_protected'] = (
                        v2.immutable_state(bpy, q, rig, names) == immutable_before
                        and v2.asset_state(bpy, worker, names) == assets_before
                        and v2.sampled_source_state(q, worker, rig, selected) == source_after_strip)
                    report['source_pose_channels_restored'] = q.digest(q.pose_channels(rig)) == original_channels
                except Exception as error:
                    report['errors'].append(dict(source_protection=repr(error)))
            if inventory is not None:
                try:
                    report['cleanup'] = rest.cleanup_owned(bpy, home, inventory)
                    report['owned_native_cleanup'] = report['cleanup']['success']
                except Exception as error:
                    report['errors'].append(dict(owned_cleanup=repr(error)))
            try:
                result = bpy.ops.wm.read_factory_settings(use_empty=True)
                report['private_scene_disposed'] = ('FINISHED' in result and not bpy.data.filepath
                    and all(len(getattr(bpy.data, kind)) == 0 for kind in ('objects', 'meshes', 'armatures', 'actions', 'images')))
            except Exception as error:
                report['errors'].append(dict(factory_disposal=repr(error)))
        try:
            report['pinned_files_unchanged'] = bool(pins) and all(sha(path) == value for path, value in pins.items())
        except Exception as error:
            report['errors'].append(dict(pins_after=repr(error)))
        report['quantification_complete'] = (report['Native_started'] and len(report.get('samples', [])) == 3
            and report['source_77_mesh_Rest_Body12_Actions_assets_protected'] and report['source_pose_channels_restored']
            and report['owned_native_cleanup'] and report['private_scene_disposed'] and report['pinned_files_unchanged']
            and not report['errors'])
        report['elapsed_seconds'] = time.perf_counter()-started
        write()
    print(json.dumps(dict(quantification_complete=report['quantification_complete'], errors=report['errors'])), flush=True)
    return 0 if report['quantification_complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
