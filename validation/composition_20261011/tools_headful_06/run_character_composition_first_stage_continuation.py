"""Explicit continuation of pinned n11 numerics after a serializer-only fix.

Run only in a separately authorized disposable Blender process. Import does not
open a file, launch a worker, read resources, write evidence or issue a grant.
The old failed report stays immutable; fresh ownership and export are re-proved.
"""
import argparse
import ast
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import traceback
import uuid

OLD_NUMERIC_SHA = 'c5d1170c43848b5d6ccb607953c7dad0cecbeb52291a81b2d490ead3020dfb6c'
FAILURE_READBACK_SHA = '2291e1e7360b8431eafb0d2fd86b12eafe486d96a2760b58051867468a0a6189'
OLD_NATIVE_SHA = 'ce4be885e95ef720f617712ca1bacc0347872a2a1542ade6cf8f9e86d6d34632'
DRIVER_SHA = '701532d2fcc8024850811cd41e40c2b5dbd43e912ed95ab5f76824f6722521e6'
ADMISSION_FIELDS = {'schema', 'numeric_report', 'failure_readback', 'owner_review', 'peer_review', 'projection_receipt'}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pin(row):
    require(type(row) is dict and {'path', 'sha256'} <= set(row)
            and Path(row['path']).is_absolute() and type(row['sha256']) is str
            and len(row['sha256']) == 64, 'Use an explicit absolute path and full SHA-256.')
    path = Path(row['path']).resolve()
    require(path.is_file() and sha(path) == row['sha256'].lower(), 'Pinned input changed: ' + str(path))
    if 'bytes' in row:
        require(type(row['bytes']) is int and path.stat().st_size == row['bytes'], 'Pinned byte count changed.')
    return path


def load(row):
    value = json.loads(pin(row).read_text(encoding='utf-8'))
    json.dumps(value, allow_nan=False)
    return value


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def functions(path):
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    funcs = {node.name: ast.dump(node, include_attributes=False) for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    top = [ast.dump(node, include_attributes=False) for node in tree.body
           if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return funcs, top


def validate_delta(old, fixture, admission):
    reviews = [load(admission[key]) for key in ('owner_review', 'peer_review')]
    require(all(row.get('source_only') is True and row.get('native_execution_performed') is False
                and row.get('passed') is True for row in reviews), 'Require completed SOURCE-only owner and peer review.')
    facts = reviews[0]['numeric_reuse_delta']
    require(facts == reviews[1]['numeric_reuse_delta'] and facts['serialization_only'] is True
            and facts['changed_functions'] == {'animation_composition_export.py': ['begin_isolated_export']}
            and set(facts['added_functions']) == {'animation_composition_export.py'}
            and set(facts['added_functions']['animation_composition_export.py']) == {'_snapshot_editor_state', '_prepare_snapshot_editor'}
            and len(facts['added_functions']['animation_composition_export.py']) == 2,
            'Both reviewers must identify the same serialization-only function delta.')
    require(Path(pin(facts['old_projection'])) == Path(old['runtime']['manifest']).resolve()
            and facts['old_projection']['sha256'] == old['runtime']['manifest_sha256'], 'Old projection differs from n11.')
    before = load(facts['old_projection'])
    after = load({'path': fixture['runtimeManifest'], 'sha256': fixture['runtimeManifestSha256']})
    require(set(before['files']) == set(after['files']) and len(before['files']) == 167,
            'Reuse requires the exact complete 167-file native product.')
    changed = [name for name in before['files'] if before['files'][name] != after['files'][name]]
    require(changed == ['animation_composition_export.py'], 'A shared evaluator or another product source changed.')
    old_path = Path(old['runtime']['package']) / changed[0]
    new_path = Path(fixture['addonPackage']) / changed[0]
    require(sha(old_path) == before['files'][changed[0]] and sha(new_path) == after['files'][changed[0]], 'Exporter source pin changed.')
    require(reviews[0]['changed_runtime_sources'] == reviews[1]['changed_runtime_sources']
            and set(reviews[0]['changed_runtime_sources']) == set(changed), 'Review source map differs.')
    reviewed = reviews[0]['changed_runtime_sources'][changed[0]]
    require(sha(pin(reviewed)) == after['files'][changed[0]], 'New projection does not contain the reviewed exporter.')
    old_funcs, old_top = functions(old_path)
    new_funcs, new_top = functions(new_path)
    added = set(facts['added_functions'][changed[0]])
    require(old_top == new_top and set(new_funcs) == set(old_funcs) | added
            and not added & set(old_funcs) and len(added) == len(facts['added_functions'][changed[0]])
            and all(old_funcs[name] == new_funcs[name] for name in old_funcs if name != 'begin_isolated_export'),
            'Shared isolation, curves, matrices, seeds, time or numeric functions changed.')
    tree = ast.parse(new_path.read_text(encoding='utf-8'))
    begin = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'begin_isolated_export')
    wanted = ast.dump(ast.parse('_prepare_snapshot_editor(rig, original)').body[0], include_attributes=False)
    parents = [node for node in ast.walk(begin) if isinstance(node, ast.Try)]
    matches = [(node.body, index) for node in parents for index, child in enumerate(node.body)
               if ast.dump(child, include_attributes=False) == wanted]
    require(len(matches) == 1, 'Only the exact snapshot-boundary call may be added.')
    body, index = matches[0]
    require(index + 1 < len(body) and isinstance(body[index + 1], ast.Expr)
            and isinstance(body[index + 1].value, ast.Call)
            and ast.unparse(body[index + 1].value.func) == 'bpy.data.libraries.write', 'Cleanup must immediately precede snapshot serialization.')
    del body[index]
    require(ast.dump(begin, include_attributes=False) == old_funcs['begin_isolated_export'], 'Snapshot launch changed beyond one serialization call.')
    return facts


def validate_numeric(old, old_fixture):
    require(old.get('schema') == 'x.validation.character-composition-native/1'
            and old.get('completed') is False and old.get('numeric_completed') is True
            and old.get('worker_launch_performed') is False
            and old.get('fresh_workspace_cleanup') == 'historical_native_state_and_rows_restored', 'Use the immutable failed n11 numeric report.')
    flags = ('same_b_across_two_a_seek_and_object_motion', 'protected_prior_actions_unchanged',
             'protected_assets_unchanged', 'fresh_native_associations_verified', 'historical_recovery_association_unchanged')
    require(all(old.get(key) is True for key in flags), 'The old complete numerical/protection proof is required.')
    require(all(old[key]['full_scope_verified'] is True and old[key]['native_count'] == 217
                for key in ('qa_fk_preflight', 'qa_fk_post_adoption')), 'Original pre/post full217 admission is missing.')
    cases = old['cases']
    expected = {(label, obj, time) for label in ('a1', 'a2') for obj in range(2) for time in old_fixture['seekSeconds']}
    require(len(cases) == 12 and len(expected) == 12
            and {(row['reference'], row['object_motion_case'], row['seek_seconds']) for row in cases} == expected,
            'Require all twelve exact two-A/two-object/three-seek cases.')
    values, base = old['effective_values'], cases[0]['b_fingerprint']
    require(values['schema'] == 'cdesigner.composition-effective-values/1'
            and len(values['channels']) == 410 and len(values['timesSeconds']) == 4
            and all(a < b for a, b in zip(values['timesSeconds'], values['timesSeconds'][1:]))
            and len({row[0] for row in values['channels']}) == 410
            and all(len(row[1]) == len(values['timesSeconds']) for row in values['channels']), 'Incomplete numeric samples.')
    numbers = values['timesSeconds'] + [value for row in values['channels'] for value in row[1]]
    require(all(type(value) in (int, float) and math.isfinite(value) for value in numbers), 'Require all 410 by 4 samples and times to be finite numbers, excluding booleans.')
    for index, label in enumerate(('a1', 'a2')):
        rows = [row for row in cases if row['reference'] == label]
        require(all(row['native_count'] == 217 and row['b_fingerprint'] == base and base['fingerprint_known'] is True
                    and uuid.UUID(row['b_work_item_id']) == uuid.UUID(old_fixture['bWorkItemIds'][index])
                    and row['composition_export']['effectiveChannelsSha256'] == digest(values)
                    and row['composition_export']['referenceActionBeforeSha256'] == row['composition_export']['referenceActionAfterSha256']
                    and row['composition_export']['excludedReferenceEvaluation'] is True for row in rows), 'Old B/A numerical proof differs.')
    require(len({row['visible_c_sha256'] for row in cases}) > 1
            and len({row['composition_export']['referenceActionBeforeSha256'] for row in cases}) == 2,
            'The original test did not exercise two different genuine A evaluations.')


def admit(config, admission, native):
    require(type(admission) is dict and set(admission) == ADMISSION_FIELDS
            and admission['schema'] == 'x.validation.character-composition-numeric-reuse/1'
            and admission['numeric_report']['sha256'] == OLD_NUMERIC_SHA
            and admission['failure_readback']['sha256'] == FAILURE_READBACK_SHA, 'No arbitrary numeric report may authorize continuation.')
    old, failure = load(admission['numeric_report']), load(admission['failure_readback'])
    require(failure['evidence_readback_passed'] is True and failure['native_run_completed'] is False
            and failure['full_acceptance_passed'] is False and len(failure['source_rehash']) == 28, 'Use actual failed-worker source readback.')
    files = {Path(row['path']).resolve(): row for row in failure['files']}
    for row in files.values():
        pin(row)
    old_fixture = native.validate_fixture(load({'path': old['fixture'], 'sha256': old['fixture_sha256']}))
    fixture = native.validate_fixture(load(config['nativeFixture']))
    ignored = {'addonPackage', 'runtimeManifest', 'runtimeManifestSha256', 'evidenceDirectory', 'specFiles'}
    require({k: v for k, v in fixture.items() if k not in ignored} == {k: v for k, v in old_fixture.items() if k not in ignored}
            and [row['sha256'] for row in fixture['specFiles']] == [row['sha256'] for row in old_fixture['specFiles']], 'Actual model/A/B/spec/time/object inputs changed.')
    old_entry = next(load(row) for path, row in files.items() if path.name == 'source_entry_receipt.json')
    for row in failure['source_rehash']:
        require(row['matches_expected'] is True and row['sha256'] == old_entry['source_inputs'][row['path']], 'Source input is not admitted by n11.')
        pin(row)
    result = next(load(row) for path, row in files.items() if path.name == 'result.json')
    require(result['ok'] is False and result['error'] == 'Snapshot contains unowned objects; A evaluation was not excluded.', 'The prior failure differs.')
    validate_numeric(old, old_fixture)
    facts = validate_delta(old, fixture, admission)
    projection = load(admission['projection_receipt'])
    require(projection['schema'] == 'x.validation.character-composition-snapshot-serializer-projections/1'
            and projection['source_only'] is True and projection['native_execution_performed'] is False
            and projection['release_or_deployment_performed'] is False and projection['embedded_overlay_count'] == 8
            and projection['embedded_overlays_unchanged'] is True
            and projection['fix']['numeric_reuse_delta'] == facts
            and projection['fix']['owner_source_report'] == admission['owner_review']
            and projection['fix']['independent_source_review'] == admission['peer_review']
            and projection['python_projection']['path'] == fixture['runtimeManifest']
            and projection['python_projection']['sha256'] == fixture['runtimeManifestSha256'], 'The actual matched Python/full source projection closure differs.')
    old_full, new_full = load(old_entry['full_projection']), load(projection['complete_candidate'])
    require(set(old_full['files']) == set(new_full['files']) and len(old_full['files']) == 173
            and [name for name in old_full['files'] if old_full['files'][name] != new_full['files'][name]] == ['animation_composition_export.py'],
            'The complete candidate changed Unity or another product source.')
    old_config = next(load(row) for path, row in files.items() if path.name == 'first_stage_config.json')
    old_native = old_config['tools']['verify_character_composition_native']
    require(old_native['sha256'] == OLD_NATIVE_SHA, 'The original native tool is not the pinned default driver.')
    new_native = Path(config['tools']['verify_character_composition_native']['path'])
    inverse = new_native.read_text(encoding='utf-8').replace('after_numeric=None, cases_runner=None', 'after_numeric=None')
    inverse = inverse.replace("    case_runner = _run_fresh_cases if cases_runner is None else cases_runner\n    require(callable(case_runner), 'cases_runner is an explicit test-only continuation callable.')\n", '')
    inverse = inverse.replace('        case_runner(config, report, workspace_path', '        _run_fresh_cases(config, report, workspace_path')
    require(inverse == pin(old_native).read_text(encoding='utf-8'), 'Native default bodies changed beyond the explicit cases_runner seam.')
    for key in ('physicalFixture', 'loopAuthorFixture'):
        current, prior = load(config[key]), load(old_config[key])
        require({k: v for k, v in current.items() if k != 'evidenceDirectory'} ==
                {k: v for k, v in prior.items() if k != 'evidenceDirectory'}, 'Publication/Loop source authorization changed.')
    return old, fixture, facts


def run(config, admission, report):
    import bpy
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    driver = importlib.import_module('run_character_composition_first_stage')
    require(sha(driver.__file__) == DRIVER_SHA, 'The original first-stage context changed.')
    driver.validate_config(config)
    native, physical, timing = [importlib.import_module(name) for name in
        ('verify_character_composition_native', 'composition_sync_acceptance', 'composition_timing_acceptance')]
    old, fixture, facts = admit(config, admission, native)
    sync, author = physical.validate_config(load(config['physicalFixture'])), timing.validate_author_config(load(config['loopAuthorFixture']))
    require(len(sync['items']) == 2 and all(row['kind'] == 'SOURCE' for row in sync['items']), 'Use the same two actual SOURCE publications.')
    evidence = Path(fixture['evidenceDirectory']).resolve()
    outputs = [evidence / 'composition_native_report.json', evidence / 'initial_workspace.json',
        Path(sync['evidenceDirectory']), Path(author['evidenceDirectory']), Path(config['loopSyncDirectory']), Path(config['qaSeedFile'])]
    require(len(set(outputs)) == len(outputs) and all(path.is_relative_to(evidence) and path != evidence and not path.exists() for path in outputs), 'Every continuation output must be fresh and owned.')
    Path(author['evidenceDirectory']).mkdir(parents=True)
    with outputs[1].open('xb') as stream:
        stream.write(pin({'path': fixture['compositionWorkspace'], 'sha256': fixture['compositionWorkspaceSha256']}).read_bytes())
    driver.check_memory(report, 'before_fresh_ownership_and_import')
    def before_worker(_context, item):
        driver.check_memory(report, 'before_worker_' + item.work_item_id)
    def after_numeric(context, numeric):
        report['two_a_physical'] = physical.run(context, sync, numeric, before_worker=before_worker)
        driver.check_memory(report, 'before_native_loop_authoring')
        report['loop_authoring'] = timing.author_hold_loop(context, author)
        proof = report['loop_authoring']['numeric_proof']
        report['loop_physical'] = physical.run_one(context, proof['authorization'], config['loopSyncDirectory'], proof, before_worker=before_worker)
        report['qa_seed'] = native.save_qa_seed(context, numeric, config['qaSeedFile'], physical_report_path=str(Path(sync['evidenceDirectory']) / 'composition_sync_report.json'))
    def cases_runner(cfg, numeric, workspace_path, rig, scene, preservation, prior_actions, prior_assets, specs, callback):
        modules = {name: importlib.import_module('character_designer.' + name) for name in
            ('animation_worklist', 'animation_link', 'animation_link_source', 'animation_worklist_fingerprint', 'animation_composition', 'animation_composition_export')}
        worklist, links, source, fp, backend, export = modules.values()
        saved = worklist.state(bpy.context)
        target = importlib.import_module('character_designer.animation_worklist_target')
        recovery_workspace = (saved.workspace_path, saved.workspace_identity, saved.model_file, saved.model_sha256,
                              rig.get('character_designer_animation_source_model_sha256'))
        recovery_association = {key: rig[key] for key in (links.LINK_KEY, links.ACTION_KEY, links.RIG_ID_KEY) if key in rig}
        recovery_session = target.capture_session_metadata(rig)
        backend.connect_library(bpy.context, str(workspace_path))
        ids, anchors = [], []
        for index, spec in enumerate(specs):
            rows = [row for row in saved.composition_catalog if row.ready and uuid.UUID(row.work_item_id) == uuid.UUID(cfg['bWorkItemIds'][index])]
            require(len(rows) == 1, 'Fresh B route is missing or ambiguous.')
            item = backend.add_work_item(bpy.context, rows[0].clip_key, activate_new=False)
            item_id = str(item.item_id)
            ids.append(item_id)
            anchors.append(native.capture_import_anchor(bpy.context, rig, item_id, worklist, fp))
        native.assert_actions(prior_actions, fp)
        require(not preservation.protected_preview_changes(prior_assets, preservation.asset_snapshot(scene, rig, importlib.import_module('character_designer.unity_animation'))), 'Imports changed protected assets.')
        for index, (item_id, anchor, spec) in enumerate(zip(ids, anchors, specs)):
            item = native.reacquire_work_item(bpy.context, rig, item_id, worklist, anchor=anchor, fingerprint=fp)
            packet, scope = backend._packet_for_item(item), None
            scope = export.resolve_scope(bpy.context, rig, spec, packet)
            fresh = {'work_item_id': spec['editWorkItemId'], 'model_sha256': item.model_sha256,
                'packet_sha256': packet['_sha256'], 'source_rest_sha256': spec['sourceRestSha256'],
                'original_rest_sha256': scope.proof['sourceRest'], 'motion_rest_sha256': scope.proof['motionRest'],
                'native_count': len(scope.mapping.indices), 'mapping_error_metres': scope.mapping.error_metres}
            require(fresh == old['fresh_packet_proofs'][index] and backend.item_spec(item) == spec, 'Fresh native217/Rest/model/B packet/spec differs.')
            numeric.setdefault('fresh_packet_proofs', []).append(fresh)
            captured, previous = worklist._capture_rig(bpy.context, rig), source._context_state(bpy.context)
            previous_index = saved.active_index
            try:
                worklist.activate(bpy.context, item_id, 'CUSTOM')
                association = native.fresh_association_proof(bpy.context, rig, item_id, links, worklist, cfg['compositionModelSha256'], anchor=anchor, fingerprint=fp)
                require(association == old['fresh_associations'][index], 'Fresh association differs from the original route.')
                numeric.setdefault('fresh_associations', []).append(association)
                backend.enter(bpy.context, spec, item_id)
                with backend.isolated_sync(bpy.context, rig) as inputs:
                    model_helpers = export.baseline_worker()._model_helpers()
                    native_names = {bone.name for bone in inputs['rig'].data.bones if not model_helpers._is_control(bone)}
                    require(len(native_names) == cfg['expectedNativeCount'] == 217
                            and native_names == set(inputs['scope'].mapping.indices), 'The fresh isolated output must retain all 217 proved native bones.')
                    original = next(row for row in old['cases'] if row['reference'] == 'a' + str(index + 1))
                    require(inputs['effective_values'] == old['effective_values'] and inputs['b_fingerprint'] == original['b_fingerprint']
                            and inputs['composition_export'] == original['composition_export'], 'Fresh isolated B/input/A proof differs from immutable numerics.')
            finally:
                if backend.active(rig):
                    backend.exit(bpy.context, rig, writeback=False)
                worklist._restore_rig(bpy.context, rig, captured)
                source._restore_context(bpy.context, previous, playing=True)
                saved.active_index = previous_index
                bpy.context.view_layer.update()
            native.reacquire_work_item(bpy.context, rig, item_id, worklist, anchor=anchor, fingerprint=fp)
        require(recovery_workspace == (saved.workspace_path, saved.workspace_identity, saved.model_file, saved.model_sha256,
                    rig.get('character_designer_animation_source_model_sha256'))
                and recovery_association == {key: rig[key] for key in (links.LINK_KEY, links.ACTION_KEY, links.RIG_ID_KEY) if key in rig}
                and recovery_session == target.capture_session_metadata(rig), 'Fresh verification changed its captured recovery workspace/association/session.')
        numeric.update(cases=old['cases'], effective_values=old['effective_values'], numeric_completed=True,
            same_b_across_two_a_seek_and_object_motion=True, protected_prior_actions_unchanged=True,
            protected_assets_unchanged=True, fresh_native_associations_verified=True, historical_recovery_association_unchanged=True,
            worker_launch_performed=False, numeric_reuse={'source': admission['numeric_report'], 'old_report_completed': False,
                'cases_reexecuted': False, 'fresh_isolated_variants_verified': 2, 'serializer_delta': facts})
        native.assert_actions(prior_actions, fp)
        require(not preservation.protected_preview_changes(prior_assets, preservation.asset_snapshot(scene, rig, importlib.import_module('character_designer.unity_animation'))), 'Fresh isolation changed protected assets.')
        callback(bpy.context, numeric)
    report['numeric'] = {'schema': native.REPORT_SCHEMA, 'completed': False, 'fixture': str(pin(config['nativeFixture'])),
        'fixture_sha256': config['nativeFixture']['sha256'], 'initial_workspace_snapshot': {'path': str(outputs[1]), 'sha256': fixture['compositionWorkspaceSha256']}}
    try:
        native.run(fixture, report['numeric'], after_numeric=after_numeric, cases_runner=cases_runner)
    finally:
        with outputs[0].open('x', encoding='utf-8') as stream:
            json.dump(report['numeric'], stream, ensure_ascii=False, allow_nan=False, indent=2)
    require(report['numeric']['completed'] is True, 'Fresh historical outer recovery did not complete.')
    report.update(completed=True, artist_save_performed=False, original_scene_recovery_verified=True, source_packets_rewritten=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--reuse-admission', required=True)
    parser.add_argument('--reuse-admission-sha256', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    admission = load({'path': args.reuse_admission, 'sha256': args.reuse_admission_sha256})
    destination = Path(load(config['nativeFixture'])['evidenceDirectory']) / 'composition_first_stage_report.json'
    require(not destination.exists(), 'Never overwrite a prior continuation report.')
    report = {'schema': 'x.validation.character-composition-first-stage-report/1', 'completed': False,
        'config': str(config_path), 'config_sha256': sha(config_path), 'continuation': True,
        'reuse_admission': {'path': str(Path(args.reuse_admission).resolve()), 'sha256': args.reuse_admission_sha256}}
    try:
        run(config, admission, report)
    except Exception as error:
        report.update(error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
        raise
    finally:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, allow_nan=False, indent=2)


if __name__ == '__main__':
    main()
