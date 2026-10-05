"""QA-only native input capture for fitting existing Dress bones.

Open only the sealed independent waist-attachment QA blend. Do not simulate,
bake, save a blend, edit bones, or change source weights. Owned Cloth viewport
flags are temporarily disabled to avoid treating a cold RAM cache as replay.
This capture does not claim the recorded Cloth targets were re-simulated.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import traceback

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / 'waist_body_attachment_51_20261005_094107_823/result/experimental_actual_surface.json'
EVIDENCE_SHA = 'a6618bea6487ccada08a6c52c852a788a6c277f1e8b62d9fc0a6cce42ad1e861'
sys.path.insert(0, str(HERE))
import diagnose_skin_transfer as diag
qa, skirt = diag.qa, diag.skirt


def require(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.output = args.output.resolve()
    require(args.output.is_relative_to(HERE) and args.output != HERE and not args.output.exists(), 'Use fresh QA output')
    require(bpy.app.background and '--factory-startup' in sys.argv and not bpy.data.filepath, 'Factory background only')
    require(hashlib.sha256(EVIDENCE.read_bytes()).hexdigest() == EVIDENCE_SHA, 'Frozen Cloth evidence changed')
    evidence = json.loads(EVIDENCE.read_text('utf-8'))
    sealed = Path(evidence['saved_candidate']).resolve()
    require(sealed.is_relative_to(HERE) and sealed.name.startswith('Cosha_Dress_QA_'), 'Refuse artist input')
    require(qa.file_state(sealed) == evidence['candidate_file'], 'Sealed QA blend changed')
    artist = HERE.parents[1] / 'X.blend'
    before_artist = qa.file_state(artist)
    code_before = diag.source_manifest()
    args.output.mkdir()
    report = {'status': 'starting', 'artist_operation': False, 'scene_saved': False,
              'cloth_replayed': False, 'production_effect_accepted': False,
              'evidence_path': str(EVIDENCE), 'evidence_sha256': EVIDENCE_SHA,
              'sealed_input': str(sealed), 'sealed_file': evidence['candidate_file'],
              'frames': [], 'errors': []}
    probe, flags, opened, saved_frame = None, [], False, None
    try:
        diag.character_designer.register()
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(sealed), load_ui=False), 'QA open failed')
        opened = True
        record = evidence['frozen_record']
        source, rig = bpy.data.objects[record['source']], bpy.data.objects[record['rig']]
        require(skirt.read_record(source) == record, 'Saved authoritative record changed')
        require(source.type == 'MESH' and rig.type == 'ARMATURE', 'Source/Rig type changed')
        saved_frame = (bpy.context.scene.frame_current, bpy.context.scene.frame_subframe)
        protect = qa.Protection()
        report['protected_before'] = protect.summary()
        report['source_world_before'] = diag.matrix(source.matrix_world)
        source_matrix = Matrix(record['fit']['matrix_world'])
        require(len(source.data.vertices) == 800, 'Source count changed')
        report['source_basis800_world'] = [diag.vector(source_matrix @ vertex.co) for vertex in source.data.vertices]
        reference = [source_matrix @ Vector(p) for p in record['fit']['vertices']]
        rest_error = max((Vector(a)-b).length for a,b in zip(report['source_basis800_world'], reference))
        require(rest_error < 1.e-6, 'Source raw Basis differs from saved fit vertices')
        report['basis_vs_saved_fit_max_world'] = rest_error
        groups = evidence['disposable_skin_probe']['direct_cloth_output']['raw_source_native_groups']
        report['groups33'] = groups
        report['native_weights800'] = evidence['disposable_skin_probe']['direct_cloth_output']['raw_source_native_weights800']
        names = [record['controls']['waist']] + [n for chain in record['chains'] for n in chain['def']]
        report['fitted_bone_names'] = names
        report['rest_bones'] = {n: qa.rest_content(rig)[n] for n in names}
        # The entire loaded scene is already the sealed QA scene, but explicitly
        # select only the recorded actual Cloth and legacy owned Cloth.
        actual = bpy.data.objects[evidence['actual_cloth']['object']]
        legacy = bpy.data.objects[record['physics']['proxy']]
        for obj in (actual, legacy):
            for modifier in obj.modifiers:
                if modifier.type == 'CLOTH':
                    flags.append((modifier, modifier.show_viewport, modifier.show_render))
                    modifier.show_viewport = modifier.show_render = False
        require(flags, 'Expected owned Cloth missing')
        probe = source.copy()
        probe.name = 'QA Native Fit Input Raw Skin'
        bpy.context.scene.collection.objects.link(probe)
        require(probe.data == source.data and probe != source, 'Probe source identity changed')
        armatures = [m for m in probe.modifiers if m.type == 'ARMATURE']
        require(len(armatures) == 1 and armatures[0].object == rig and armatures[0].use_deform_preserve_volume,
                'Expected sole native DQ Armature')
        arm = armatures[0]
        seen = False
        for modifier in tuple(probe.modifiers):
            if modifier == arm:
                seen = True
            elif seen:
                probe.modifiers.remove(modifier)
        require(list(probe.modifiers) == [arm], 'Unsupported pre-Armature modifiers')
        report['native_armature_parameters'] = qa.simple_rna(arm)
        body = bpy.data.objects[evidence['body_clone']['original']]
        meters = bpy.context.scene.unit_settings.scale_length
        for recorded in evidence['frames']:
            frame = recorded['frame']
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            graph = bpy.context.evaluated_depsgraph_get()
            evaluated = rig.evaluated_get(graph)
            current_source_matrix = source.evaluated_get(graph).matrix_world.copy()
            matrix_error = max(abs(x-y) for a,b in zip(current_source_matrix,source_matrix) for x,y in zip(a,b))
            recorded_rig = Matrix(recorded['evaluated_waist_evidence']['rig_evaluated_matrix_world'])
            rig_error = max(abs(x-y) for a,b in zip(evaluated.matrix_world,recorded_rig) for x,y in zip(a,b))
            require(rig_error < 1.e-6, 'Native Body input rig object differs from frozen frame')
            current_body = diag.mesh_snapshot(body,graph)
            witnesses = recorded['evaluated_body_triangle_evidence']['vertices']
            body_error = max((current_body['points'][w['evaluated_vertex_index']]-Vector(w['world'])).length for w in witnesses)
            require(body_error * meters < 5.e-6, 'Body action differs from frozen sampled frame')
            raw = diag.mesh_snapshot(probe,graph)
            require(len(raw['points']) == 800, 'Raw native skin count differs')
            report['frames'].append({'frame':frame,
                'source_evaluated_matrix_world':diag.matrix(current_source_matrix),
                'bind_world_to_current_rig_rest_input':diag.matrix(evaluated.matrix_world.inverted() @ current_source_matrix @ source_matrix.inverted()),
                'rig_evaluated_matrix_world':diag.matrix(evaluated.matrix_world),
                'source_bind_matrix_max_delta':matrix_error,'rig_recorded_matrix_max_delta':rig_error,
                'body_14_witness_max_delta_m':body_error*meters,
                'native_bones':{n:diag.bone_content(rig,evaluated,n) for n in names},
                'raw_native_cold_physics_skin800_world':[diag.vector(p) for p in raw['points']],
                'cold_physics_is_not_recorded_simulation':True})
        report['scene_unit_scale_length'] = meters
        report['status'] = 'passed'
    except BaseException:
        report['errors'].append(traceback.format_exc())
        report['status'] = 'failed'
    finally:
        if probe is not None:
            bpy.data.objects.remove(probe,do_unlink=True)
            probe = None
        for modifier, viewport, render in flags:
            modifier.show_viewport, modifier.show_render = viewport, render
        if opened and saved_frame is not None:
            bpy.context.scene.frame_set(saved_frame[0],subframe=saved_frame[1])
            bpy.context.view_layer.update()
            report['protected_after'] = protect.verify()
            require(report['protected_after']['success'], 'Capture changed protected assets')
        report['artist_disk_exact'] = qa.file_state(artist) == before_artist
        report['code_exact'] = diag.source_manifest() == code_before
        report['sealed_input_exact'] = qa.file_state(sealed) == evidence['candidate_file']
        require(report['artist_disk_exact'] and report['code_exact'] and report['sealed_input_exact'], 'Capture changed protected files')
        (args.output/'native_fit_inputs.json').write_text(json.dumps(diag.json_content(report),ensure_ascii=False,allow_nan=False,indent=2),'utf-8')
    require(report['status'] == 'passed', 'Native fit input capture failed; inspect report')


if __name__ == '__main__':
    main()
