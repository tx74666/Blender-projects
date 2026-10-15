"""Read-only current SaveCopy cache contract, fixed integer1–30/30FPS.

The old fixed40644 loaders are deliberately unused. Geometry numbers retain
the original complete oracle; explicit ID routes normalize shader identities.
All caches/resources remain dependencies on this local machine.
"""
import importlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_cache_artifact_contract_005 as generic
import mesh_cache_current_input_007 as current_input
import mesh_cache_view_layer_adapter_006 as visibility

base, require = generic.base, generic.require
json_value, logical = generic.json_value, generic.logical
scene_state, modifier_state = generic.scene_state, generic.modifier_state
dependency_closure = generic.dependency_closure
check_serialized_dependencies = generic.check_serialized_dependencies
verify_pin, verify_pin_group = generic.verify_pin, generic.verify_pin_group
FRAMES, CACHE_SETTINGS, PORTABLE_SHA = generic.FRAMES, generic.CACHE_SETTINGS, generic.PORTABLE_SHA
SCHEMA = 'x.current-pc2-artifact-contract/1'
FULL_SCHEMA = 'x.current-pc2-full30/1'
RECEIPT_SCHEMA = 'x.current-pc2-artifact/1'
SOURCE_FILES = (
    'mesh_cache_actor_current_core_008.py', 'mesh_cache_current_input_007.py',
    'mesh_cache_current_contract_008.py', 'mesh_cache_current_policy_008.py',
    'mesh_cache_current_runner_008.py', 'mesh_cache_shader_witness_009.py', 'mesh_cache_shader_witness_008.py',
    'mesh_cache_shader_witness_007.py', 'mesh_cache_actor_current_core_007.py',
    'mesh_cache_current_core_extraction_007.json',
    'mesh_cache_current_core_extraction_008.json', 'mesh_cache_actor_full30_002.py',
    'mesh_cache_artifact_assembler_005.py', 'mesh_cache_artifact_contract_005.py',
    'mesh_cache_artifact_contract_006.py', 'mesh_cache_actor_full30_004.py',
    'mesh_cache_view_layer_adapter_006.py', 'native_artifact_action_witness_008.py',
    'mesh_cache_actor_admission_001.py', 'mesh_cache_pc2_factory_001.py',
    'native_validation_support.py', 'native_validation_support_v9.py',
    'native_source_reference_witness_v9.py')
_ACCEPTED, _SHADERS = {}, {}


def verify_sources(pin):
    verify_pin(pin)
    seal = json.loads(Path(pin['path']).read_text(encoding='utf-8-sig'))
    require(seal.get('schema') == 'x.current-cache-sources/1'
        and set(seal.get('files', {})) == set(SOURCE_FILES), 'Current source seal coverage differs')
    for name, item in seal['files'].items():
        require(Path(item['path']).resolve() == HERE/name, 'Foreign current source route')
        verify_pin(item)
    return seal['files']


def validate_tiny(path, sha):
    pin = base.pin(path)
    require(pin['sha256'] == sha, 'Tiny006 receipt SHA differs')
    report = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    require(report.get('schema') == 'x.native-view-layer-copy-fixture/1'
        and report.get('completed') is True and 'error' not in report
        and all(report.get(key) is True for key in ('old_hidden_state_lost', 'source_exact', 'all_visits_exact')),
        'Actual completed Base006 native fixture required')
    require([(row['frame'], row['exact']) for row in report['visits']] == [(1, True), (2, True), (1, True)],
        'Tiny006 visits differ')
    cleanup = report.get('cleanup', {})
    require(cleanup.get('errors') == [] and set(cleanup) == {'errors', 'owned_ids_removed',
        'handlers_unchanged', 'scripts_unchanged', 'stage09_unchanged'}
        and all(value is True for key, value in cleanup.items() if key != 'errors'), 'Tiny006 cleanup failed')
    verify_pin_group(report['scripts'])
    require(report['scripts'].get('native_view_layer_copy_fixture_006.py', {}).get('sha256')
        == 'a15e9787dfca98fff21b72027f773f26dc389acb5717e15c16b782919c50a6df', 'Different tiny006 producer')
    seal = report['visibility_override']
    require(seal['manifest']['sha256'] == visibility.MANIFEST_SHA
        and seal['scene_source']['sha256'] == visibility.SCENE_SHA, 'Tiny006 Stage09 differs')
    verify_pin(seal['manifest'])
    verify_pin(seal['scene_source'])
    return pin


def _source_pin_group(report):
    sources = verify_sources(report['current_source_seal'])
    require(report['current_sources'] == sources, 'Current source set differs from explicit seal')
    require(report['current_scene_source_proof'] == current_input.scene_source_proof(), 'Current Stage06/08/09 proof differs')
    return sources


def _resources(report):
    seen = {}
    for frame in report['golden']:
        for resource in frame['shader']['resources']:
            item = resource.get('external')
            if item is not None:
                require(item['path'] not in seen or seen[item['path']] == item, 'Conflicting shader resource pin')
                seen[item['path']] = item
    return list(seen.values())


def load_full30(path, sha):
    """Actual current native PASS, before any input open or artifact writes."""
    pin = base.pin(path)
    require(pin['sha256'] == sha, 'Current Full30 receipt SHA differs')
    report = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    require(report.get('schema') == FULL_SCHEMA and report.get('completed') is True and 'error' not in report
        and str(report.get('blender', '')).startswith('5.2')
        and not any(key in report for key in ('primary_error', 'secondary_cleanup_error', 'cleanup_error')),
        'Actual completed current Blender5.2 Full30 required')
    _source_pin_group(report)
    snapshot, snapshot_pin = current_input.load_snapshot(report['current_snapshot_receipt']['path'],
        report['current_snapshot_receipt']['sha256'], report['input_before']['sha256'], report['input_before']['bytes'])
    require(snapshot['copy'] == report['input_before'] and snapshot_pin == report['current_snapshot_receipt']
        and snapshot['source_identity'] == report['current_snapshot_identity'], 'Current capture identity differs')
    validate_tiny(report['tiny_fixture_receipt']['path'], report['tiny_fixture_receipt']['sha256'])
    require(report.get('witness_mode') == 'v9' and report.get('witness_adapter', {}).get('actual_witness') == 'v9', 'Actual V9 required')
    require(report.get('current_frame_domain') == {'frames': list(FRAMES), 'fps': 30, 'fps_base': 1.0}
        and report['saved_frame'] == snapshot['source_identity']['frame'][0], 'Current clip/frame domain differs')
    flags = ('clip_static_exact', 'all_replay_geometry_exact', 'all_replay_visibility_exact',
        'all_replay_materials_exact', 'current_sources_unchanged', 'current_scene_sources_unchanged',
        'current_resources_final_before_cleanup_exact', 'source_protection_complete')
    require(all(report.get(key) is True for key in flags) and report.get('static_deltas') == [], 'Current clip gates failed')
    expected_cleanup = {'owned_ids_removed', 'handlers_restored_exact', 'input_disk_unchanged',
        'artist_disk_unchanged', 'source_manifest_unchanged', 'source_package_unchanged', 'scripts_unchanged',
        'cache_files_unchanged', 'source_witness_dependencies_unchanged', 'v8_factory_receipt_unchanged', 'v8_factory_sources_unchanged'}
    cleanup = report.get('cleanup', {})
    require(set(cleanup) == expected_cleanup | {'errors'} and cleanup['errors'] == []
        and all(cleanup[key] is True for key in expected_cleanup), 'Current clip cleanup incomplete')
    for label in ('source_after_golden', 'source_after_candidate', 'source_after_timing', 'source_after_cleanup'):
        row = report.get(label, {})
        require(row.get('output', {}).get('exact') is True and row.get('source_properties_exact') is True
            and row.get('material_source_exact') is True and row.get('changed_property_components') == [], 'Source proof failed: '+label)
    for key in ('scripts', 'adapter_sources', 'v8_factory_sources', 'source_witness_dependencies'):
        verify_pin_group(report[key])
    for key in ('geometry_oracle', 'input_before', 'source_manifest', 'v9_factory_receipt'):
        verify_pin(report[key])
    require(report['v9_factory_receipt'] == report.get('v8_factory_receipt'), 'Disclosed V9 alias differs')
    chooser = importlib.import_module('mesh_cache_actor_full30_004')
    chooser.validate_factory(json.loads(Path(report['v9_factory_receipt']['path']).read_text(encoding='utf-8-sig')))
    require(report['source_manifest']['sha256'] == chooser.STAGE06_SHA, 'Current authoring Stage06 differs')
    require(report['source_package'] == base.verify_package_manifest(
        Path(report['source_manifest']['path']).parent/'addons/character_designer',
        json.loads(Path(report['source_manifest']['path']).read_text(encoding='utf-8-sig'))), 'Authoring package differs')
    golden = report.get('golden', [])
    require([row.get('frame') for row in golden] == list(FRAMES), 'All30 current golden frames required')
    names = set(golden[0]['meshes'])
    require(names and all(set(row['meshes']) == names for row in golden), 'Complete current mesh coverage differs')
    caches = report.get('cache_files', [])
    require(len(caches) == len(names) and {row['source'] for row in caches} == names
        and len({row['path'] for row in caches}) == len(names), 'Unique complete current PC2 mapping required')
    for item in caches:
        verify_pin(item)
    visits = [(block, frame) for block, frames in importlib.import_module('mesh_cache_actor_full30_002').replay_visits() for frame in frames]
    require([(row.get('block'), row.get('frame')) for row in report['replay']] == visits
        and [(row.get('frame'), row.get('exact')) for row in report['visibility_replay']] == [(frame, True) for _, frame in visits]
        and [(row.get('frame'), row.get('exact')) for row in report['shader_replay']] == [(frame, True) for _, frame in visits],
        'All150 current geometry/visibility/material visits required')
    indexed = {row['frame']: row['meshes'] for row in golden}
    for visit in report['replay']:
        rows = visit['meshes']
        require(len(rows) == len(names) and {row['mesh'] for row in rows} == names, 'Replay current mesh coverage differs')
        for row in rows:
            expected = indexed[visit['frame']][row['mesh']]['sha256']
            require(row.get('exact') is True and row.get('changed_components') == []
                and row.get('source_sha256') == expected and row.get('cache_sha256') == expected, 'Replay content not bit exact')
    for row in report['shader_replay']:
        expected = golden[row['frame']-1]['shader']['sha256']
        require(row['source_sha256'] == expected and row['target_sha256'] == expected, 'Replay shader content differs')
    for item in _resources(report):
        verify_pin(item)
    _ACCEPTED[(pin['path'], pin['sha256'])] = report
    return report, pin


def accepted(contract):
    pin = contract['accepted_full30_report']
    key = (pin['path'], pin['sha256'])
    if key not in _ACCEPTED:
        load_full30(pin['path'], pin['sha256'])
    return _ACCEPTED[key]


def check_visibility(scene, contract, all_layers=True):
    return visibility.check_visibility(scene, contract['visibility'], all_layers=all_layers)


def check_binding(scene, contract):
    require(contract.get('schema') == SCHEMA and contract['scene']['frames'] == list(FRAMES)
        and contract['scene']['saved_frame'] == 1, 'Wrong current clip contract')
    require(scene_state(scene) == {key: contract['scene'][key] for key in scene_state(scene)}, 'Scene settings differ')
    rows = contract['objects']
    names = set(accepted(contract)['golden'][0]['meshes'])
    require(len(rows) == len(names) and {row['source_name'] for row in rows} == names
        and len({row['target_name'] for row in rows}) == len(rows), 'Current cache mapping differs')
    require({obj.name_full for obj in scene.objects if obj.type == 'MESH'} == {row['target_name'] for row in rows}, 'Mesh membership differs')
    for row in rows:
        obj = scene.objects.get(row['target_name'])
        require(obj is not None and obj.type == 'MESH' and obj.data.name_full == row['target_data_name']
            and obj.data.shape_keys is None and len(obj.modifiers) == 1, 'Flattened mesh binding differs')
        require('character_designer_forearm_twist_v1' not in obj, 'Mesh remains enrolled in authoring runtime')
        mod = obj.modifiers[0]
        require(mod.type == 'MESH_CACHE' and mod.name == row['modifier']['name']
            and modifier_state(mod) == CACHE_SETTINGS and str(Path(mod.filepath).resolve()) == row['cache']['path'], 'PC2 settings differ')
    check_visibility(scene, contract, all_layers=False)
    return {'healthy': True, 'meshes': len(rows), 'scene': scene.name_full}


def _shader(scene, contract):
    import bpy
    require(bpy.context.scene is scene, 'Shader capture requires the current Scene depsgraph')
    module = importlib.import_module('mesh_cache_shader_witness_009')
    key = (int(scene.as_pointer()), scene.session_uid)
    if key not in _SHADERS:
        _SHADERS[key] = module.ShaderWitness()
    witness = _SHADERS[key]
    value = json_value(witness.capture(scene, contract['shader_id_mapping'], depsgraph=bpy.context.evaluated_depsgraph_get()))
    return witness, value


def verify_shader_resources(scene, contract):
    # A source-protection callback may currently own the Source depsgraph.
    # Revalidate already-captured readers without evaluating the target there.
    key = (int(scene.as_pointer()), scene.session_uid)
    if key not in _SHADERS:
        _shader(scene, contract)
    witness = _SHADERS[key]
    return witness.verify_resources()


def check_frame(scene, contract, frame):
    """Complete unchanged numerical oracle plus current material graph; no seek/update."""
    import bpy
    require(frame in FRAMES and scene.frame_current == frame and float(scene.frame_subframe) == 0.
        and bpy.context.scene is scene, 'Current evaluated integer frame/Scene differs')
    check_binding(scene, contract)
    expected_frame = accepted(contract)['golden'][frame-1]
    golden = expected_frame['meshes']
    material_map = {tuple(row['target']): row['source'] for row in contract['material_id_map']}
    graph, rows = bpy.context.evaluated_depsgraph_get(), []
    for mapping in contract['objects']:
        obj = scene.objects[mapping['target_name']]
        current = base.oracle().evaluated_shoes(obj)
        materials = []
        for material in obj.evaluated_get(graph).data.materials:
            if material is None:
                materials.append(None)
            else:
                key = tuple(logical(material))
                require(key in material_map, 'Unmapped serialized evaluated material')
                materials.append(material_map[key])
        current['components']['materials'] = base.object_hash(materials)
        current['sha256'] = base.object_hash(current['components'])
        expected = golden[mapping['source_name']]
        changed = sorted(key for key in set(expected['components']) | set(current['components'])
            if expected['components'].get(key) != current['components'].get(key))
        rows.append({'source_name': mapping['source_name'], 'exact': not changed, 'changed_components': changed,
            'expected_sha256': expected['sha256'], 'current_sha256': current['sha256']})
    _, shader = _shader(scene, contract)
    shader_exact = shader == expected_frame['shader']
    return {'exact': all(row['exact'] for row in rows) and shader_exact, 'frame': frame, 'meshes': rows,
        'visibility_exact': True, 'shader_exact': shader_exact, 'shader_sha256': shader['sha256']}


def animation_state(scene, contract):
    verify_shader_resources(scene, contract)
    return generic.animation_state(scene, contract)


def verify_external_pins(receipt):
    verify_pin(receipt['accepted_full30_report'])
    report, _ = load_full30(receipt['accepted_full30_report']['path'], receipt['accepted_full30_report']['sha256'])
    verify_pin_group(receipt['dependency_pins'])
    verify_pin(receipt['current_source_seal'])
    require(receipt['current_sources'] == verify_sources(receipt['current_source_seal']), 'Writer sources differ')
    verify_pin(receipt['artist_before'])
    verify_pin(receipt['input_before'])
    package = receipt['reopen_contract']['package']
    verify_pin(package['manifest'])
    require(base.verify_package_manifest(package['path'], json.loads(Path(package['manifest']['path']).read_text(encoding='utf-8-sig')))
        == package['files'], 'Normal runtime package changed')
    for item in receipt.get('external_concrete_files', []):
        verify_pin(item)
    if receipt.get('artifact_published'):
        verify_pin(receipt['artifact'])
    return {'verified': True, 'pc2_files': len(report['cache_files']), 'current_material_resources': True}


def load_published_receipt(path, sha):
    pin = base.pin(path)
    require(pin['sha256'] == sha, 'Current artifact receipt SHA differs')
    receipt = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    require(receipt.get('schema') == RECEIPT_SCHEMA and receipt.get('completed') is True and 'error' not in receipt
        and receipt.get('artifact_published') is True and receipt.get('artifact_publication_complete') is True
        and not any(key in receipt for key in ('primary_error', 'secondary_cleanup_error', 'cleanup_error')),
        'Actually published current artifact required')
    require(all(receipt.get(key) is True for key in ('all_30_geometry_exact', 'write_preserved_candidate_exact',
        'current_sources_unchanged', 'current_scene_sources_unchanged', 'current_resources_final_before_cleanup_exact',
        'source_protection_complete')),
        'Current artifact proof incomplete')
    for label in ('source_before_write', 'source_after_write', 'source_after_cleanup'):
        row = receipt[label]
        require(row['output']['exact'] is True and row['source_properties_exact'] is True
            and row['material_source_exact'] is True, 'Current artifact Source proof differs')
    cleanup = receipt.get('cleanup', {})
    require(cleanup and cleanup.get('errors') == [] and all(value is True for key, value in cleanup.items() if key != 'errors'), 'Current artifact cleanup failed')
    require(receipt['reopen_contract']['schema'] == SCHEMA
        and receipt['reopen_contract']['accepted_full30_report'] == receipt['accepted_full30_report'], 'Current reopen contract differs')
    verify_external_pins(receipt)
    return receipt, pin
