"""Read-only local PC2 artifact contract; no addon registration or frame seeks.

Geometry keeps the accepted complete native oracle. Only material ID display
identity is normalized by an explicit serialized mapping. This is a local
dependency bundle, not an embedded/portable texture or cache archive.
"""
import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if hashlib.sha256((HERE/'native_validation_support.py').read_bytes()).hexdigest() != '3994f58288244684679ffd48d0837ac88bcfd9768f0a3a12c3e1d7d5b6265c0a':
    raise RuntimeError('Protected geometry support changed')
import native_validation_support as base

SCHEMA = 'x.pc2-actor-artifact-contract/1'
RECEIPT_SCHEMA = 'x.pc2-actor-artifact/1'
FULL30_SHA = 'f447574e7120c8a93fd8db5d3746f5fb5c7370ef922942dd576731fe1a715c12'
PORTABLE_SHA = 'c6881b78c9de8af661b6ecbf264e4e8a4f9861ce645246d9e8dccb1fc298b680'
FRAMES = tuple(range(1, 31))
CACHE_SETTINGS = {'cache_format': 'PC2', 'deform_mode': 'OVERWRITE', 'factor': 1.0,
    'vertex_group': '', 'interpolation': 'NONE', 'play_mode': 'SCENE', 'time_mode': 'FRAME',
    'frame_start': 1.0, 'frame_scale': 1.0, 'forward_axis': 'POS_Y', 'up_axis': 'POS_Z',
    'flip_axis': [False, False, False], 'show_viewport': True, 'show_render': True}
_ACCEPTED = {}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def json_value(value):
    """The contract compares the same JSON domain before and after a reopen."""
    return json.loads(json.dumps(value, allow_nan=False))


def verify_pin(item):
    require(isinstance(item, dict) and set(item) >= {'path', 'sha256', 'bytes'}, 'Missing content pin')
    current = base.pin(item['path'])
    require(current == {key: item[key] for key in ('path', 'sha256', 'bytes')}, 'Content changed: '+str(item['path']))
    return current


def verify_pin_group(group):
    require(isinstance(group, dict) and group, 'Empty dependency pin group')
    for item in group.values():
        verify_pin(item)


def load_full30(path, sha):
    """Actual completed 004 only. This admission runs before opening any blend."""
    item = base.pin(path)
    require(item['sha256'] == sha, 'Explicit accepted Full30 receipt SHA differs')
    report = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    require(report.get('schema') == 'x.pc2-fixed-actor-full30/1' and report.get('completed') is True
        and 'error' not in report and str(report.get('blender', '')).startswith('5.2'), 'Completed real Blender5.2 Full30 required')
    require(report.get('witness_mode') == 'v9' and report.get('witness_adapter', {}).get('actual_witness') == 'v9', 'Actual V9 scope required')
    for key in ('clip_static_exact', 'all_replay_geometry_exact', 'adapter_sources_unchanged',
                'adapter_stage_manifests_unchanged', 'adapter_packages_unchanged'):
        require(report.get(key) is True, 'Full30 gate failed: '+key)
    require(report.get('static_deltas') == [], 'Full30 static payload varies')
    cleanup = report.get('cleanup', {})
    expected_cleanup = {'owned_ids_removed', 'handlers_restored_exact', 'input_disk_unchanged',
        'artist_disk_unchanged', 'source_manifest_unchanged', 'source_package_unchanged', 'scripts_unchanged',
        'cache_files_unchanged', 'source_witness_dependencies_unchanged', 'v8_factory_receipt_unchanged', 'v8_factory_sources_unchanged'}
    require(set(cleanup) == expected_cleanup | {'errors'} and cleanup['errors'] == []
        and all(cleanup[key] is True for key in expected_cleanup), 'Full30 cleanup/source proof incomplete')
    for label in ('source_after_golden', 'source_after_candidate', 'source_after_timing', 'source_after_cleanup'):
        row = report.get(label, {})
        require(row.get('output', {}).get('exact') is True and row.get('source_properties_exact') is True
            and row.get('changed_property_components') == [], 'Full30 source proof failed: '+label)
    for key in ('adapter_hooks_still_owned', 'adapter_hooks_restored'):
        require(report.get(key) == {'parent_remap': True, 'witness_chooser': True}, 'Parent/V9 hook ownership incomplete')
    for key in ('scripts', 'adapter_sources', 'v8_factory_sources', 'source_witness_dependencies'):
        verify_pin_group(report.get(key))
    require(report['adapter_sources'].get('mesh_cache_actor_full30_004.py', {}).get('sha256') == FULL30_SHA,
            'Different Full30 adapter was executed')
    for key in ('geometry_oracle', 'input_before', 'source_manifest', 'adapter_stage06', 'adapter_stage08', 'v9_factory_receipt'):
        verify_pin(report[key])
    require(report['input_before']['sha256'] == '40644b848dd2cb2c1346514fbd78f22274528a60f714597e9103541bd0fef721'
        and report['input_before']['bytes'] == 34691613, 'Only the earlier fixed40644 private snapshot is supported')
    require(report['v9_factory_receipt'] == report.get('v8_factory_receipt'), 'Disclosed factory alias differs')
    adapter = importlib.import_module('mesh_cache_actor_full30_004')
    adapter.validate_factory(json.loads(Path(report['v9_factory_receipt']['path']).read_text(encoding='utf-8-sig')))
    require(report['source_manifest']['sha256'] == adapter.STAGE06_SHA
        and report['adapter_stage08']['sha256'] == adapter.STAGE08_SHA, 'Stage seals differ')
    # Read the function seal without importing/calling the parent helper in GUI.
    seal = report['parent_override']
    scene_source = Path(report['adapter_stage08']['path']).parent/'addons/character_designer/forearm_twist_playback_scene.py'
    node = next(item for item in ast.parse(scene_source.read_text(encoding='utf-8')).body
                if isinstance(item, ast.FunctionDef) and item.name == '_remap_rna')
    require(seal['manifest'] == report['adapter_stage08'] and seal['scene_source'] == base.pin(scene_source)
        and seal['scene_source']['sha256'] == '33e84ebd52d01ea99c5cdf9bf459464a6d52ea054766bb6e2893b02304b30c7c'
        and seal['function_ast_sha256'] == hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest(),
        'Different parent function seal')
    for stage_key in ('adapter_stage06', 'adapter_stage08'):
        manifest = report[stage_key]
        observed_package = base.verify_package_manifest(Path(manifest['path']).parent/'addons/character_designer',
                                     json.loads(Path(manifest['path']).read_text(encoding='utf-8-sig')))
        require(observed_package == (report['source_package'] if stage_key == 'adapter_stage06' else seal['package']),
                'Accepted package source payload differs')
    golden = report.get('golden', [])
    require([row.get('frame') for row in golden] == list(FRAMES), 'All30 unique ordered golden frames required')
    names = set(golden[0]['meshes'])
    require(len(names) == 69 and all(set(row['meshes']) == names for row in golden), 'Complete fixed actor69 required')
    caches = report.get('cache_files', [])
    require(len(caches) == 69 and {row['source'] for row in caches} == names
        and len({row['path'] for row in caches}) == 69, 'Complete unique69 PC2 mapping required')
    for row in caches:
        verify_pin(row)
    visits = [(name, frame) for name, frames in importlib.import_module('mesh_cache_actor_full30_002').replay_visits() for frame in frames]
    require([(row.get('block'), row.get('frame')) for row in report.get('replay', [])] == visits, 'All150 replay visits required')
    indexed = {row['frame']: row['meshes'] for row in golden}
    for visit in report['replay']:
        rows = visit.get('meshes', [])
        require(len(rows) == 69 and {row['mesh'] for row in rows} == names, 'Replay actor coverage differs')
        for row in rows:
            expected = indexed[visit['frame']][row['mesh']]['sha256']
            require(row.get('exact') is True and row.get('changed_components') == []
                and row.get('source_sha256') == expected and row.get('cache_sha256') == expected, 'Replay content not bit exact')
    _ACCEPTED[(item['path'], item['sha256'])] = report
    return report, item


def accepted(contract):
    item = contract['accepted_full30_report']
    key = (item['path'], item['sha256'])
    if key not in _ACCEPTED:
        load_full30(item['path'], item['sha256'])
    return _ACCEPTED[key]


def logical(value):
    if value is None:
        return None
    value = getattr(value, 'original', value)
    return [type(value).__name__, value.name_full, value.library.filepath if value.library else None]


def scene_state(scene):
    return {'name': scene.name_full, 'frame_start': scene.frame_start, 'frame_end': scene.frame_end,
        'frame_step': scene.frame_step, 'fps': scene.render.fps, 'fps_base': float(scene.render.fps_base).hex(),
        'sync_mode': scene.sync_mode, 'use_preview_range': bool(scene.use_preview_range),
        'frame_preview_start': scene.frame_preview_start, 'frame_preview_end': scene.frame_preview_end}


def modifier_state(modifier):
    return {key: list(getattr(modifier, key)) if key == 'flip_axis' else getattr(modifier, key)
            for key in CACHE_SETTINGS}


def dependency_closure(scene):
    """Read native ID user edges; known embedded owner routes are explicit."""
    import bpy
    reverse = {}
    for dependency, users in bpy.data.user_map().items():
        for user in users:
            reverse.setdefault(user, set()).add(dependency)
    pending, found = [scene], set()
    while pending:
        owner = pending.pop()
        if owner in found:
            continue
        found.add(owner)
        pending.extend(reverse.get(owner, ()))
        if isinstance(owner, (bpy.types.Scene, bpy.types.Material, bpy.types.World)):
            for name in ('collection', 'node_tree'):
                item = getattr(owner, name, None)
                if item is not None:
                    pending.append(item)
    return found


def check_binding(scene, contract):
    import bpy
    require(contract.get('schema') == SCHEMA, 'Wrong PC2 artifact contract')
    require(contract['scene']['frames'] == list(FRAMES) and contract['scene']['saved_frame'] == 1,
            'Fixed integer clip contract differs')
    require(scene_state(scene) == {key: contract['scene'][key] for key in scene_state(scene)}, 'Scene clip/settings changed')
    rows = contract['objects']
    require(len(rows) == 69 and len({row['target_name'] for row in rows}) == 69, 'Candidate mesh mapping differs')
    require({obj.name_full for obj in scene.objects if obj.type == 'MESH'} == {row['target_name'] for row in rows}, 'Mesh membership differs')
    for row in rows:
        obj = scene.objects.get(row['target_name'])
        require(obj is not None and obj.type == 'MESH' and obj.data.name_full == row['target_data_name']
            and obj.data.shape_keys is None and len(obj.modifiers) == 1, 'Flattened mesh binding differs')
        require('character_designer_forearm_twist_v1' not in obj, 'Mesh remains enrolled in authoring runtime')
        mod = obj.modifiers[0]
        require(mod.type == 'MESH_CACHE' and mod.name == row['modifier']['name']
            and modifier_state(mod) == CACHE_SETTINGS and str(Path(mod.filepath).resolve()) == row['cache']['path'], 'PC2 modifier binding differs')
    return {'healthy': True, 'meshes': len(rows), 'scene': scene.name_full}


def check_serialized_dependencies(scene, contract):
    """Whole-file Scene enrollment and native dependency identities, outside hot FPS."""
    import bpy
    portable = importlib.import_module('native_artifact_action_witness_008')
    require(sorted(item.name_full for item in bpy.data.scenes) == sorted(contract['expected_scene_names']),
            'Artifact includes an unexpected Scene')
    require(json_value(sorted((portable.identity(item) for item in dependency_closure(scene)), key=repr))
        == contract['serialized_dependency_ids'], 'Serialized native dependency graph differs')
    return {'exact': True}


def check_frame(scene, contract, frame):
    """No seek/update/solver: caller must yield native evaluation before reading."""
    import bpy
    require(frame in FRAMES and scene.frame_current == frame and float(scene.frame_subframe) == 0.
        and bpy.context.scene is scene, 'Current evaluated integer frame/Scene differs')
    check_binding(scene, contract)
    golden = accepted(contract)['golden'][frame-1]['meshes']
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
    return {'exact': all(row['exact'] for row in rows), 'frame': frame, 'meshes': rows}


def animation_state(scene, contract):
    import bpy
    require(base.pin(HERE/'native_artifact_action_witness_008.py')['sha256'] == PORTABLE_SHA, 'Portable Action helper changed')
    portable = importlib.import_module('native_artifact_action_witness_008')
    actions = []
    for key in contract['actions']:
        matches = [item for item in bpy.data.actions if logical(item) == key]
        require(len(matches) == 1, 'Serialized Action identity missing/ambiguous')
        actions.append(matches[0])
    return json_value(portable.capture(scene, actions))


def verify_external_pins(receipt):
    verify_pin(receipt['accepted_full30_report'])
    report, _ = load_full30(receipt['accepted_full30_report']['path'], receipt['accepted_full30_report']['sha256'])
    verify_pin_group(receipt['dependency_pins'])
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
    return {'verified': True, 'pc2_files': len(report['cache_files'])}


def load_published_receipt(path, sha):
    item = base.pin(path)
    require(item['sha256'] == sha, 'Artifact receipt SHA differs')
    receipt = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    require(receipt.get('schema') == RECEIPT_SCHEMA and receipt.get('completed') is True and 'error' not in receipt
        and receipt.get('artifact_published') is True and receipt.get('artifact_publication_complete') is True,
        'Actually published completed artifact required')
    require(receipt.get('all_30_geometry_exact') is True and receipt.get('write_preserved_candidate_exact') is True
        and receipt.get('source_after_cleanup', {}).get('output', {}).get('exact') is True
        and receipt['source_after_cleanup'].get('source_properties_exact') is True, 'Artifact proof incomplete')
    cleanup = receipt.get('cleanup', {})
    require(cleanup and cleanup.get('errors') == [] and all(value is True for key, value in cleanup.items() if key != 'errors'), 'Artifact cleanup failed')
    require(receipt['reopen_contract'].get('schema') == SCHEMA
        and receipt['accepted_full30_report'] == receipt['reopen_contract']['accepted_full30_report'], 'Artifact contract differs')
    verify_external_pins(receipt)
    return receipt, item
