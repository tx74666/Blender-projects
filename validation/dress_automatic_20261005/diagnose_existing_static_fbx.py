"""Read a previously generated QA FBX; no second export or artist writes.

The exact public library/job reconstruct the native pre-export reference using
the current worker. Its FBX operation is intercepted solely for this reference;
the reimported FBX must be the immutable real output from the failed QA run.
This is diagnostic evidence, not a production export acceptance.
"""
import argparse
import ast
import copy
import json
import math
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify_actual_surface_export as export_qa


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='Immutable failed surface_export.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.input, args.output = args.input.resolve(), args.output.resolve()
    export_qa.require(args.input.is_file() and args.input.is_relative_to(HERE), 'Use an existing QA report')
    export_qa.require(args.output.is_relative_to(HERE) and args.output != HERE
                      and not args.input.is_relative_to(args.output), 'Use a dedicated new QA directory')
    export_qa.require(not (args.output / 'existing_fbx_diagnostic.json').exists(), 'Do not overwrite a diagnostic')
    return args


def main(args):
    require, sha = export_qa.require, export_qa.sha
    require(bpy.app.background and '--factory-startup' in sys.argv and not bpy.data.filepath,
            'Only an empty factory background child may read this diagnostic')
    require(bpy.app.version[:2] == (5, 1), 'Use the reviewed Blender 5.1 native runtime')
    failed = json.loads(args.input.read_text(encoding='utf-8'))
    require(failed.get('success') is False and failed.get('worker_result', {}).get('ok') is True
            and failed.get('artist_disk_exact') is True and failed.get('input_qa_disk_exact') is True
            and failed.get('canonical_and_frozen_code_exact') is True,
            'Use a protected QA failure after an actual successful worker export')
    library, fbx = (Path(failed[name]['path']).resolve() for name in ('public_library_snapshot', 'fbx'))
    job_file = args.input.parent / 'public_job.json'
    for path in (library, fbx, job_file):
        require(path.is_file() and path.is_relative_to(args.input.parent.parent), 'Reference inputs must belong to that QA run')
    require(sha(library) == failed['public_library_snapshot']['sha256']
            and sha(fbx) == failed['fbx']['sha256'], 'The original native library/FBX bytes changed')
    qa, diag, addon, surface, _exporter, worker = export_qa.modules()
    roundtrip_source = Path(export_qa.__file__).resolve()
    roundtrip_sha = 'b54764c7b74e3228d60afea2be7239fd0fb60bc88cf18e337196f5f86da1ea89'
    require(sha(roundtrip_source) == roundtrip_sha, 'The reviewed native roundtrip diagnostics changed')
    before_manifest = diag.source_manifest()
    require(before_manifest == failed['source_manifest_after'], 'Canonical/frozen sources changed since the actual export')
    # The install report contains the explicit artist path; do not guess it.
    gate = json.loads(Path(failed['install_gate']['path']).read_text(encoding='utf-8'))
    artist = Path(gate['artist_path']).resolve()
    prepared = Path(gate['prepared_candidate']['path']).resolve()
    inputs = {str(path): qa.file_state(path) for path in (args.input, library, fbx, job_file, artist, prepared)}
    require(inputs[str(artist)] == failed['artist_after'], 'The artist disk changed after the failed export')
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'success': False, 'diagnostic_completed': False, 'production_export_accepted': False,
              'actual_fbx_reexported': False, 'artist_saved_by_verifier': False, 'inputs_before': inputs,
              'canonical_manifest_before': before_manifest, 'harness_sha256': sha(Path(__file__)),
              'roundtrip_source': {'path': str(roundtrip_source), 'reviewed_sha256': roundtrip_sha},
              'public_job_provenance': 'Original export did not save a job SHA; this diagnostic protects current job bytes and cross-checks recorded semantic facts',
              'checks': [], 'limits': ['Native Blender FBX reimport diagnostics only, not Unity/Magica acceptance',
                                      'Reference uses actual worker with FBX export intercepted; immutable FBX was exported by the original real QA']}
    started = time.perf_counter()
    try:
        addon.register()
        result = bpy.ops.wm.open_mainfile(filepath=str(library), load_ui=False, use_scripts=False)
        require('FINISHED' in result, 'Could not open the immutable public library')
        job = copy.deepcopy(json.loads(job_file.read_text(encoding='utf-8')))
        require(job['objects'] == failed['public_library_snapshot']['objects']
                and job['rig'] == failed['input_source']['rig']
                and job['unit_scale'] == failed['worker_result']['unit_scale']
                and job['filename'] == fbx.name
                and qa.digest(job['dress_surfaces']) == failed['captured_proof_sha256'],
                'The current job differs from the original recorded scope, scale, filename or surface proof')
        job['stage'] = str(args.output / 'reference_stage')
        reference_file = Path(job['stage']) / job['filename']

        def skip_reference_fbx(**options):
            require(Path(options['filepath']).resolve() == reference_file.resolve(), 'Unexpected reference export target')
            reference_file.parent.mkdir(parents=True, exist_ok=True)
            reference_file.write_bytes(b'Diagnostic placeholder, not an FBX')
            return {'FINISHED'}

        class Delegate:
            def __init__(self, target, **overrides):
                self.target, self.overrides = target, overrides
            def __getattr__(self, name):
                return self.overrides[name] if name in self.overrides else getattr(self.target, name)

        real_bpy = worker.bpy
        delegated = Delegate(real_bpy, ops=Delegate(real_bpy.ops, export_scene=Delegate(
            real_bpy.ops.export_scene, fbx=skip_reference_fbx)))
        with patch.object(worker, 'bpy', delegated):
            worker_result = worker.export_job(job)
        require(worker_result.get('ok') is True, 'The pre-export reference worker did not finish')
        names = failed['public_library_snapshot']['objects']
        require(len(names) == 2 and job['rig'] in names, 'Use the explicit Dress-only native scope')
        source_name = next(name for name in names if name != job['rig'])
        source, rig = bpy.data.objects[source_name], bpy.data.objects[job['rig']]
        generated = export_qa.static_mesh(source)
        require(worker_result['origin'] == failed['worker_result']['origin']
                and worker_result['unit_scale'] == failed['worker_result']['unit_scale']
                and sorted(rig.data.bones.keys()) == failed['retained_source_rest']['names'],
                'The reconstructed native reference differs in origin, scale or retained bone inventory')
        rest = {bone.name: {'parent': bone.parent.name if bone.parent else None,
                           'deform': bone.use_deform,
                           'world': [list(row) for row in rig.matrix_world @ bone.matrix_local]}
                for bone in rig.data.bones}
        report['reference'] = {'scope': names, 'origin': worker_result['origin'],
                               'unit_scale': worker_result['unit_scale'], 'bones': len(rest),
                               'vertices': len(generated['vertices']), 'rest_sha256': qa.digest(rest),
                               'mesh_sha256': qa.digest(generated)}
        importer = Path(r'D:\Blender5.1\5.1\scripts\addons_core\io_scene_fbx\import_fbx.py')
        importer_sha = 'e4e55c2e344959b75d840e20c4d45d079ec8fd4f4bc375491cea76e55cce8013'
        require(sha(importer) == importer_sha, 'The reviewed native importer source changed')
        tree = ast.parse(importer.read_text(encoding='utf-8'))
        assignments = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assign)
                       and isinstance(node.value, ast.Name) and node.value.id == 'bone_matrix'
                       and any(isinstance(target, ast.Attribute) and target.attr == 'matrix'
                               and isinstance(target.value, ast.Name) and target.value.id == 'bone'
                               for target in node.targets)]
        require(len(assignments) == 1, 'The importer no longer has the unique reviewed bone matrix assignment')
        assignment_line = assignments[0]
        traces, pending = {}, {}
        report['native_importer_matrix_assignment_trace'] = {
            'source': str(importer), 'sha256': importer_sha, 'line': assignment_line, 'bones': traces,
            'scope': 'Plain native values around the unmodified official importer EditBone.matrix assignment'}

        def matrix_values(matrix):
            return [[float(value) for value in row] for row in matrix]

        def trace(frame, event, _arg):
            if frame.f_code.co_name != 'build_skeleton' or Path(frame.f_code.co_filename).resolve() != importer:
                return None
            if event == 'line' and frame.f_lineno == assignment_line:
                bone, target = frame.f_locals['bone'], frame.f_locals['bone_matrix']
                traces[bone.name] = {'target_matrix': matrix_values(target),
                                    'before_matrix': matrix_values(bone.matrix), 'before_roll': float(bone.roll)}
                pending[id(frame)] = bone.name
            elif event == 'line' and id(frame) in pending:
                name = pending.pop(id(frame))
                bone, target = frame.f_locals['bone'], frame.f_locals['bone_matrix']
                traces[name].update({'after_matrix': matrix_values(bone.matrix), 'after_roll': float(bone.roll),
                    'assignment_matrix_max_error': max(abs(target[row][col] - bone.matrix[row][col])
                                                       for row in range(4) for col in range(4))})
            return trace

        old_trace = sys.gettrace()
        require(old_trace is None, 'Do not replace an existing trace/profiler in this private child')
        try:
            sys.settrace(trace)
            try:
                export_qa.roundtrip(fbx, generated, rest, float(job['unit_scale']), names, report, qa)
                report['all_roundtrip_guards_passed'] = True
            except Exception as error:
                require(report.get('native_static_fbx_roundtrip_diagnostics', {}).get('status')
                        == 'all_guard_metrics_collected_before_acceptance',
                        'Reimport failed before all original native guard metrics were captured')
                report['all_roundtrip_guards_passed'] = False
                report['roundtrip_error'] = {'type': type(error).__name__, 'message': str(error),
                                             'traceback': traceback.format_exc()}
        finally:
            sys.settrace(old_trace)
        require(set(traces) == set(rest) and not pending
                and all(all(key in entry for key in ('target_matrix', 'before_matrix', 'after_matrix', 'before_roll', 'after_roll', 'assignment_matrix_max_error'))
                        and all(math.isfinite(value) for key in ('target_matrix', 'before_matrix', 'after_matrix')
                                for row in entry[key] for value in row)
                        and all(math.isfinite(entry[key]) for key in
                                ('before_roll', 'after_roll', 'assignment_matrix_max_error'))
                        for entry in traces.values()),
                'Native importer assignment tracing was incomplete or nonfinite')
        report['native_importer_matrix_assignment_trace']['complete_bone_count'] = len(traces)
        report['diagnostic_completed'] = True
        report['success'] = True
    except Exception as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
    finally:
        report['inputs_after'] = {str(path): qa.file_state(Path(path)) for path in inputs}
        report['input_and_artist_disk_exact'] = inputs == report['inputs_after']
        report['canonical_manifest_after'] = diag.source_manifest()
        report['canonical_and_frozen_code_exact'] = before_manifest == report['canonical_manifest_after']
        report['harness_code_exact'] = report['harness_sha256'] == sha(Path(__file__))
        report['roundtrip_source']['after_sha256'] = sha(roundtrip_source)
        report['roundtrip_code_exact'] = sha(roundtrip_source) == roundtrip_sha
        if 'native_importer_matrix_assignment_trace' in report:
            traced = report['native_importer_matrix_assignment_trace']
            traced['after_sha256'] = sha(Path(traced['source']))
            report['native_importer_code_exact'] = traced['after_sha256'] == traced['sha256']
        else:
            report['native_importer_code_exact'] = False
        report['success'] = report['success'] and report['input_and_artist_disk_exact'] and report['canonical_and_frozen_code_exact'] and report['harness_code_exact'] and report['roundtrip_code_exact'] and report['native_importer_code_exact']
        report['elapsed_seconds'] = time.perf_counter() - started
        path = args.output / 'existing_fbx_diagnostic.json'
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'success': report['success'], 'diagnostic_completed': report['diagnostic_completed'],
                          'all_roundtrip_guards_passed': report.get('all_roundtrip_guards_passed'),
                          'report': str(path)}, ensure_ascii=False), flush=True)
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main(arguments()))
