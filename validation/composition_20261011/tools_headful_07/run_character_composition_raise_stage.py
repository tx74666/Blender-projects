"""Explicit second native window: immutable QA seed to genuine NEW Raise Sync.

Importing launches nothing. The root supplies actual pinned files/IDs after
three real Holds were collected and Raise was prepared. This entry opens only
the first-stage QA seed, never a UI-edited seed or the artist. It does not reopen
during execution. Only the newly registered NEW manifest may be published.
"""
import argparse
import importlib
import json
import math
from pathlib import Path
import re
import sys
import traceback
import uuid

SCHEMA = 'x.validation.character-composition-raise-stage/1'
REPORT_SCHEMA = 'x.validation.character-composition-raise-stage-report/1'
FIELDS = {'schema', 'driverSha256', 'inputBlend', 'inputBlendSha256', 'addonPackage',
    'runtimeManifest', 'runtimeManifestSha256', 'evidenceDirectory', 'numericReport',
    'numericReportSha256', 'seedBlend', 'seedBlendSha256', 'workItemId', 'sceneName',
    'rigName', 'targetGuid', 'modelSha256', 'freshWorkspace', 'raiseAuthorFixture',
    'tools', 'poseTolerance', 'inputTolerance', 'outputSeedFile'}
TOOLS = {'verify_character_composition_native', 'run_character_composition_ui_fixture',
    'run_character_composition_first_stage', 'composition_sync_acceptance',
    'composition_raise_authoring', 'composition_timing_acceptance',
    'composition_session_acceptance', 'release_projection'}
PIN_FIELDS = {'path', 'sha256'}
ROUTE_FIELDS = ('sourcePackage', 'sourcePackageSha256', 'linkManifest', 'linkGuid', 'linkId',
    'workItemId', 'editScope', 'sourceOnly', 'compositionReferenceSource', 'compositionOwnerLinkGuid',
    'clipGuid', 'clipLocalId', 'baseClipGuid', 'baseClipLocalId', 'sourceCharacterGuid', 'purpose')


def require(value, message):
    if not value:
        raise AssertionError(message)


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def _absolute(value):
    return type(value) is str and Path(value).is_absolute() and not any(ord(char) < 32 for char in value)


def _id(value):
    require(type(value) is str, 'Use the actual UUID identity, never a display label.')
    result = uuid.UUID(value)
    require(result.int != 0, 'An actual identity cannot be the zero UUID.')
    return result.hex


def validate_config(config):
    require(type(config) is dict and set(config) == FIELDS and config['schema'] == SCHEMA,
            'Use the complete explicit second-stage fixture.')
    require(all(_absolute(config[key]) for key in ('inputBlend', 'addonPackage', 'runtimeManifest',
        'evidenceDirectory', 'numericReport', 'seedBlend')),
        'Pin absolute immutable inputs and a separate fresh evidence directory.')
    require(all(_sha(config[key]) for key in ('driverSha256', 'inputBlendSha256',
        'runtimeManifestSha256', 'numericReportSha256', 'seedBlendSha256', 'modelSha256')),
        'Pin the exact approved source and input bytes.')
    require(Path(config['inputBlend']).name.lower() != 'x.blend'
        and Path(config['inputBlend']).suffix.lower() == '.blend'
        and Path(config['seedBlend']).suffix.lower() == '.blend'
        and Path(config['seedBlend']).resolve() != Path(config['inputBlend']).resolve()
        and config['rigName'] == 'CoshaRig' and type(config['sceneName']) is str and config['sceneName']
        and type(config['targetGuid']) is str and re.fullmatch('[0-9a-f]{32}', config['targetGuid']),
        'Use the actual first-stage QA seed and original native Rig, never artist X.blend.')
    _id(config['workItemId'])
    require(type(config['tools']) is dict and set(config['tools']) == TOOLS,
            'Pin all reviewed canonical helper bytes.')
    for pin in (config['freshWorkspace'], config['raiseAuthorFixture'], *config['tools'].values()):
        require(type(pin) is dict and set(pin) == PIN_FIELDS and _absolute(pin['path']) and _sha(pin['sha256']),
                'Each helper, current workspace and actual author config requires an exact pin.')
    for name, upper in (('poseTolerance', 2e-4), ('inputTolerance', 1e-5)):
        require(type(config[name]) in (int, float) and math.isfinite(config[name])
            and 0 < config[name] <= upper, 'Unsupported native timing tolerance: ' + name)
    evidence = Path(config['evidenceDirectory']).resolve()
    require(all(not Path(config[key]).resolve().is_relative_to(evidence)
        for key in ('inputBlend', 'addonPackage', 'runtimeManifest', 'numericReport', 'seedBlend')),
        'Immutable inputs must be outside the new mutable evidence directory.')
    output = config['outputSeedFile']
    require(output is None or _absolute(output) and Path(output).suffix.lower() == '.blend'
        and Path(output).resolve().is_relative_to(evidence) and len(output) < 260,
        'An optional output is a separate test copy inside owned evidence, never a reload.')
    json.dumps(config, allow_nan=False)
    return config


def validate_catalog_extension(old, fresh, *, workspace, raise_work_id, protected_work_ids):
    """Admit actual Raise preparation without replacing old sealed Sources."""
    raise_id = _id(raise_work_id)
    protected = {_id(value) for value in protected_work_ids}
    require(raise_id not in protected and workspace.workspace_identity(old) == workspace.workspace_identity(fresh),
            'New preparation must retain the full target/model workspace identity.')
    old_prepared = [row for row in old['clips'] if row.get('linkManifest') and row.get('sourcePackage')
                    and not row.get('needsRebuild')]
    require(protected <= {workspace.work_item_id(row) for row in old_prepared},
            'The initial bytes must contain the three actual prepared Hold Sources.')
    rows = [row for row in fresh['clips'] if workspace.work_item_id(row) == raise_id]
    require(len(rows) == 1 and rows[0].get('composition', {}).get('timeMode') == 'Raise'
        and rows[0].get('linkManifest') and rows[0].get('sourcePackage') and not rows[0].get('needsRebuild'),
        'The current catalog must contain one actual prepared Raise with its sealed packet/Link.')
    raised = rows[0]
    old_keys = set()
    for prior in old_prepared:
        key = workspace.row_key(prior)
        old_keys.add(key)
        matches = [row for row in fresh['clips'] if workspace.row_key(row) == key]
        require(len(matches) == 1 and workspace.route_identity(matches[0]) == workspace.route_identity(prior)
            and all(matches[0].get(field) == prior.get(field) for field in ROUTE_FIELDS)
            and matches[0].get('composition') == prior.get('composition'),
            'An original prepared scope/ID/DTO/packet/Link route changed during Raise preparation.')
    additions = []
    for row in fresh['clips']:
        if not row.get('linkManifest') or not row.get('sourcePackage') or row.get('needsRebuild'):
            continue
        if workspace.row_key(row) in old_keys:
            continue
        own_raise = workspace.work_item_id(row) == raise_id and row is raised
        companion = (row.get('composition') is None and row.get('compositionReferenceSource') is True
            and row.get('compositionOwnerLinkGuid') == raised.get('linkGuid')
            and row.get('editScope') == 'All')
        require(own_raise or companion, 'The explicit second stage cannot admit an unrelated newly prepared Source.')
        additions.append(workspace.work_item_id(row))
    return {'workspace_identity_equal': True, 'protected_prepared_source_count': len(old_prepared),
            'protected_hold_work_ids': sorted(protected), 'actual_prepared_raise_work_id': raise_id,
            'admitted_prepared_additions': additions}


def run(config, report):
    """Explicit serial native entry; root controls process launch and lifetime."""
    import bpy
    config = validate_config(config)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    native = importlib.import_module('verify_character_composition_native')
    require(native.file_hash(__file__) == config['driverSha256'], 'The approved second-stage source changed.')
    pinned = {}
    def pin(path, digest):
        result = native.pinned_file(path, digest)
        pinned[str(result)] = digest
        return result
    def read(pin_value):
        path = pin(pin_value['path'], pin_value['sha256'])
        require(path.stat().st_size <= 32 * 1024 * 1024, 'Use bounded immutable proof/config JSON.')
        return json.loads(path.read_text(encoding='utf-8'))
    for name, value in config['tools'].items():
        require(pin(value['path'], value['sha256']) == Path(__file__).resolve().with_name(name + '.py'),
                'Use the exact reviewed canonical helper: ' + name)
    ui = importlib.import_module('run_character_composition_ui_fixture')
    first = importlib.import_module('run_character_composition_first_stage')
    physical = importlib.import_module('composition_sync_acceptance')
    timing = importlib.import_module('composition_timing_acceptance')
    author = importlib.import_module('composition_raise_authoring')
    numeric = read({'path': config['numericReport'], 'sha256': config['numericReportSha256']})
    seed = numeric.get('qa_seed', {})
    source_fixture = native.validate_fixture(read({'path': numeric['fixture'], 'sha256': numeric['fixture_sha256']}))
    preservation_pin = source_fixture['preservationHelper']
    preservation = native.load_helper(pin(preservation_pin['path'], preservation_pin['sha256']),
                                      '_composition_raise_asset_auditor')
    published = read({'path': seed['physicalReport'], 'sha256': seed['physicalReportSha256']})
    seed, native_item_id = ui.validate_reports(config, numeric, published, source_fixture)
    historical_pin = numeric.get('initial_workspace_snapshot')
    require(type(historical_pin) is dict and set(historical_pin) == PIN_FIELDS
        and historical_pin['sha256'] == source_fixture['compositionWorkspaceSha256'] == seed['workspaceSha256'],
        'Retain the real initial workspace byte snapshot; do not replace its old hash with the current revision.')
    historical = read(historical_pin)
    fresh_path = pin(config['freshWorkspace']['path'], config['freshWorkspace']['sha256'])
    require(fresh_path == Path(seed['workspacePath']).resolve(), 'Prepare Raise in the same actual workspace path.')
    fresh_json = read(config['freshWorkspace'])
    author_config = author.validate_config(read(config['raiseAuthorFixture']))
    require(author_config['expectedModelSha256'] == config['modelSha256'], 'The actual Raise template model changed.')
    source_blend = pin(config['inputBlend'], config['inputBlendSha256'])
    seed_blend = pin(config['seedBlend'], config['seedBlendSha256'])
    pin(config['runtimeManifest'], config['runtimeManifestSha256'])
    _cd, report['runtime'] = native.runtime_projection(config)
    cache = Path(bpy.utils.user_resource('DATAFILES', create=True)).resolve()
    evidence = ui.claim_evidence(config, cache)
    author_directory = Path(author_config['evidenceDirectory']).resolve()
    sync_directory = evidence / 'new_raise_sync'
    require(author_directory != evidence and author_directory.is_relative_to(evidence)
        and not author_directory.exists() and not sync_directory.exists()
        and (config['outputSeedFile'] is None or not Path(config['outputSeedFile']).exists()),
        'All second-stage author/worker/save outputs must be fresh and owned.')
    first.check_memory(report, 'before_raise_native_seed_open')
    require(bpy.ops.wm.open_mainfile(filepath=str(seed_blend), use_scripts=False, load_ui=False) == {'FINISHED'},
            'Blender did not reopen the immutable first-stage QA seed.')
    scene, rig = bpy.data.scenes.get(seed['sceneName']), bpy.data.objects.get(seed['rigName'])
    require(scene is not None and rig is not None and rig.name in scene.objects
        and sorted(owner.name for owner in rig.users_scene) == seed['rigSceneNames'] and bpy.context.window is not None,
        'The seed lost an exact original/QA Scene or the original native Rig.')
    bpy.context.window.scene = scene
    modules = {name: importlib.import_module('character_designer.' + name) for name in (
        'animation_worklist', 'animation_worklist_target', 'animation_composition', 'animation_workspace',
        'animation_composition_export', 'animation_link_source', 'animation_worklist_fingerprint', 'animation_link')}
    worklist, target, composition, workspace, export, source, fingerprint, links = modules.values()
    saved = worklist.state(bpy.context)
    require(saved.rig is rig and target._load(rig)['scene'] is scene and not composition.active(rig)
        and saved.target_guid == seed['targetGuid'] and saved.model_sha256 == seed['modelSha256']
        and Path(saved.workspace_path).resolve() == fresh_path,
        'The current QA adoption must retain the actual same model/target/owner/workspace.')
    target.ensure_active(bpy.context, rig)
    # Validate actual parsed records with production schema before comparing.
    historical = workspace.parse_workspace(Path(historical_pin['path']).read_bytes())
    fresh = workspace.load_workspace(fresh_path)
    pin(fresh['modelFile'], fresh['modelSha256'].lower())
    for row in fresh['clips']:
        if row.get('linkManifest') and row.get('sourcePackage') and not row.get('needsRebuild'):
            pin(row['sourcePackage'], row['sourcePackageSha256'].lower())
            pin(row['linkManifest'], native.file_hash(row['linkManifest']))
    require(worklist._identity(historical) == worklist._identity(fresh) == saved.workspace_identity,
            'A changed workspace model/GUID cannot reuse this seed adoption.')
    report['catalog_extension'] = validate_catalog_extension(historical, fresh, workspace=workspace,
        raise_work_id=author_config['preparedRaiseWorkItemId'],
        protected_work_ids=[*seed['workItemIds'], author_config['collectedHoldLoopWorkItemId']])
    ui.select_native_row(saved, rig, config['workItemId'], native_item_id)
    protected_actions = native.action_proofs(bpy, fingerprint)
    artist_state = export._artist_state(rig, scene)
    old_binding = composition._prior(bpy.context, rig)
    ua = importlib.import_module('character_designer.unity_animation')
    protected_assets = preservation.asset_snapshot(scene, rig, ua)
    composition.connect_library(bpy.context, str(fresh_path))
    # Authenticate every actual historical prepared Hold against its current
    # Link and sealed packet; no stale native row substitutes for catalog proof.
    report['protected_hold_routes'] = []
    for work_id in [*seed['workItemIds'], author_config['collectedHoldLoopWorkItemId']]:
        hold = timing._row(bpy.context, work_id, timing._modules(), config['modelSha256'])
        clips = [row for row in fresh['clips'] if workspace.work_item_id(row) == _id(work_id)]
        require(len(clips) == 1, 'Each protected Hold requires one exact current catalog route.')
        link = links.load_link(hold.manifest_path)
        worklist._validate_route(saved, clips[0], link, hold)
        require(links._identity(link) == links._identity(json.loads(hold.link_identity)),
                'A protected native Source no longer owns the same full sealed Link identity.')
        packet = composition._packet_for_item(hold)
        scope = export.resolve_scope(bpy.context, rig, composition.item_spec(hold), packet)
        require(len(scope.mapping.indices) == 217, 'The current model must prove all 217 native bones for each genuine Hold.')
        report['protected_hold_routes'].append({'work_item_id': hold.work_item_id,
            'native_item_id': hold.item_id, 'packet_sha256': packet['_sha256'],
            'manifest_path': hold.manifest_path, 'manifest_sha256': native.file_hash(hold.manifest_path),
            'native_count': len(scope.mapping.indices)})
    report['native_count'] = 217
    author_directory.mkdir(parents=True)
    try:
        report['raise_authoring'] = author.run(bpy.context, author_config)
        actual = report['raise_authoring']['actual_NEW_identity']
        timing_config = {'schema': timing.SCHEMA, 'evidenceDirectory': str(evidence),
            'holdLoopWorkItemId': author_config['collectedHoldLoopWorkItemId'],
            'followingHoldWorkItemId': author_config['collectedHoldLoopWorkItemId'],
            'raiseWorkItemId': actual['work_item_id'], 'expectedModelSha256': config['modelSha256'],
            'poseTolerance': config['poseTolerance'], 'inputTolerance': config['inputTolerance'],
            'followingHoldPublication': author_config['followingHoldPublication']}
        report['timing'] = timing.run(bpy.context, timing_config)
        require(report['timing'].get('complete') is True, 'Real collected Loop/NEW Raise clocks did not pass.')
        expected = report['timing']['raise_numeric_proof']
        require(_id(expected['provenance']['newActionId']) == _id(actual['new_action_id'])
            and _id(expected['provenance']['originalPreparedWorkId']) == _id(author_config['preparedRaiseWorkItemId']),
            'The numeric proof must identify this actual registered NEW and its original sealed Raise template.')
        def before_worker(_context, item):
            first.check_memory(report, 'before_worker_' + item.work_item_id)
        report['physical'] = physical.run_one(bpy.context, expected['authorization'], str(sync_directory),
                                             expected, before_worker=before_worker)
        native.assert_actions(protected_actions, fingerprint)
        require(export._artist_state(rig, scene) == artist_state and composition._prior(bpy.context, rig) == old_binding,
                'The original native binding/Rest/pose/context changed during NEW Raise acceptance.')
        require(not preservation.changes(protected_assets, preservation.asset_snapshot(scene, rig, ua)),
                'Original raw assets/Rest/display/colors/widgets changed during NEW Raise acceptance.')
        if config['outputSeedFile'] is not None:
            output = Path(config['outputSeedFile']).resolve()
            require(bpy.ops.wm.save_as_mainfile(filepath=str(output), copy=True) == {'FINISHED'}
                and output.is_file() and output.stat().st_size > 0, 'Blender did not save the separate NEW Raise test copy.')
            report['output_seed'] = {'path': str(output), 'sha256': native.file_hash(output)}
        report.update(completed=True, original_actions_unchanged=True, original_native_state_unchanged=True,
            protected_original_assets_raw_exact=True,
            source_links_published=False, only_actual_registered_new_manifest_published=True,
            artist_save_performed=False, seed_reloaded_during_execution=False)
    finally:
        unchanged = all(Path(path).is_file() and native.file_hash(path) == digest for path, digest in pinned.items())
        report['immutable_inputs_unchanged'] = unchanged
        require(unchanged and native.file_hash(source_blend) == config['inputBlendSha256'],
                'An immutable artist-copy/seed/proof/workspace/config/helper input was overwritten.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    path = Path(parser.parse_args(argv).config).resolve()
    config = validate_config(json.loads(path.read_text(encoding='utf-8')))
    output = Path(config['evidenceDirectory']).resolve() / 'composition_raise_stage_report.json'
    require(not output.exists(), 'Retain prior attempts; use a fresh second-stage evidence directory.')
    report = {'schema': REPORT_SCHEMA, 'completed': False, 'config': str(path)}
    try:
        run(config, report)
    except Exception as error:
        report.update(error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
        raise
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
