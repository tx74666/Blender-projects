"""One actual008 Source-capture checkpoint, plus the narrow Stage10 remapper.

The checkpoint remains a failed playback run. Only its completed Source golden
and immutable PC2 bytes are reused; a fresh Source proof and all150 target visits
are mandatory. No bpy import, scene open, cache write or false PASS occurs here.
"""
import ast
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_cache_current_input_007 as previous
import mesh_cache_current_contract_008 as prior_contract
from mesh_cache_pc2_factory_001 import HEADER

base, require = previous.base, previous.require
load_snapshot = previous.load_snapshot
STAGE06, STAGE08, STAGE09 = previous.STAGE06, previous.STAGE08, previous.STAGE09
STAGE10 = HERE/'staged_20261015_10'
STAGE10_SHA = 'e1859b8b56ca5b63a5c91dcec0e4fed9d9da48d1bffa30263b191692ebed91c4'
STAGE10_SCENE_SHA = 'be291c9e70e7de4160027300ba7c4d7d4ac56ea86738e6ba9aecbd1af0360cb2'
CHECKPOINT = HERE/'mesh_cache_current_full30_report_008.json'
CHECKPOINT_SHA = '8b762b053b6e849b1b0251178a213964acacb6a4bc6403b9cf4c23c4334c85d1'
CHECKPOINT_BYTES = 11810900
CHECKPOINT_SEAL_SHA = '8fbffc3763e21efc694ea5775aa96c3ca43ad20d74a63e2e680d8c84789e8665'
SOURCE_SHA = '1c80b2580a1d7ba815a8822ccca8594845080c49f6d63c143831d2e1490a35ba'
FRAMES = tuple(range(1, 31))


def validate_checkpoint_payload(report):
    """Validate capture-only claims; never call the old Full30 PASS loader."""
    require(report.get('schema') == 'x.current-pc2-full30/1'
        and report.get('completed') is False and report.get('replay') == []
        and str(report.get('blender', '')).startswith('5.2')
        and 'Unsupported stored/registered shader field: ["World","World",null].cycles' in report.get('primary_error', '')
        and 'secondary_cleanup_error' not in report and 'cleanup_error' not in report,
        'Only the fixed actual008 clone-World failure checkpoint is supported')
    require(report.get('clip_static_exact') is True and report.get('static_deltas') == []
        and report.get('source_protection_complete') is True
        and report.get('source_shader_protection_state') == 'verified', 'Checkpoint Source capture was incomplete')
    require(report.get('saved_frame') == 13 and report.get('current_frame_domain') == {
        'frames': list(FRAMES), 'fps': 30, 'fps_base': 1.0}, 'Checkpoint frame domain differs')
    for label in ('source_after_golden', 'source_after_cleanup'):
        row = report.get(label, {})
        require(row.get('output') == {'exact': True, 'changed_components': [],
            'source_sha256': SOURCE_SHA, 'playback_sha256': SOURCE_SHA}
            and row.get('source_properties_exact') is True and row.get('changed_property_components') == []
            and row.get('material_source_exact') is True, 'Checkpoint Source proof failed: '+label)
    cleanup = report.get('cleanup', {})
    expected = {'owned_ids_removed', 'handlers_restored_exact', 'input_disk_unchanged',
        'artist_disk_unchanged', 'source_manifest_unchanged', 'source_package_unchanged', 'scripts_unchanged',
        'cache_files_unchanged', 'source_witness_dependencies_unchanged', 'v8_factory_receipt_unchanged', 'v8_factory_sources_unchanged'}
    require(set(cleanup) == expected | {'errors'} and cleanup['errors'] == []
        and all(cleanup[name] is True for name in expected), 'Checkpoint cleanup or protection failed')
    golden = report.get('golden', [])
    require([row.get('frame') for row in golden] == list(FRAMES), 'Checkpoint must contain all30 Source frames')
    names = set(golden[0]['meshes'])
    require(len(names) == 69 and all(set(row['meshes']) == names for row in golden), 'Checkpoint all69 mesh mapping differs')
    for frame in golden:
        for row in frame['meshes'].values():
            require(row.get('sha256') == base.object_hash(row['components']), 'Checkpoint geometry payload hash differs')
        shader = frame['shader']
        require(shader.get('sha256') == base.object_hash({'components': shader['components']}), 'Checkpoint shader payload hash differs')
    caches = report.get('cache_files', [])
    require(len(caches) == 69 and {row['source'] for row in caches} == names
        and len({row['path'] for row in caches}) == 69, 'Checkpoint unique69 PC2 mapping differs')
    return names


def checkpoint_cache_domains(report):
    """Read only32-byte headers, lengths and streaming pins; no sample rewrite."""
    root = HERE/'blendcache_current_008'
    result = {}
    for row in report['cache_files']:
        path = Path(row['path']).resolve()
        require(path.parent == root and path.suffix.lower() == '.pc2', 'Foreign checkpoint cache route')
        prior_contract.verify_pin(row)
        with path.open('rb') as stream:
            header = stream.read(HEADER.size)
        require(len(header) == HEADER.size, 'Checkpoint PC2 header missing')
        magic, version, vertices, start, sampling, count = HEADER.unpack(header)
        require(magic == b'POINTCACHE2\0' and version == 1 and vertices > 0
            and start == 0.0 and sampling == 1.0 and count == 30,
            'Checkpoint PC2 header/domain differs')
        require(row['bytes'] == HEADER.size + vertices*30*12, 'Checkpoint PC2 payload length differs')
        result[row['source']] = vertices
    return result


def load_capture_checkpoint(path, sha):
    pin = base.pin(path)
    require(Path(pin['path']).resolve() == CHECKPOINT and pin['sha256'] == sha == CHECKPOINT_SHA
        and pin['bytes'] == CHECKPOINT_BYTES, 'Fixed actual008 Source checkpoint pin required')
    report = json.loads(Path(pin['path']).read_text(encoding='utf-8-sig'))
    validate_checkpoint_payload(report)
    require(report['current_source_seal']['sha256'] == CHECKPOINT_SEAL_SHA
        and Path(report['current_source_seal']['path']).resolve() == HERE/'current_cache_sources_008.json',
        'Checkpoint producer23 source seal differs')
    require(report['current_sources'] == prior_contract.verify_sources(report['current_source_seal']),
        'Checkpoint producer23 source pins changed')
    require(report['current_scene_source_proof'] == previous.scene_source_proof(), 'Checkpoint old Stage09 proof changed')
    snapshot, snapshot_pin = load_snapshot(report['current_snapshot_receipt']['path'],
        report['current_snapshot_receipt']['sha256'], report['input_before']['sha256'], report['input_before']['bytes'])
    require(snapshot['copy'] == report['input_before'] and snapshot_pin == report['current_snapshot_receipt']
        and snapshot['source_identity'] == report['current_snapshot_identity'], 'Checkpoint current SaveCopy identity differs')
    prior_contract.validate_tiny(report['tiny_fixture_receipt']['path'], report['tiny_fixture_receipt']['sha256'])
    for key in ('scripts', 'adapter_sources', 'v8_factory_sources', 'source_witness_dependencies'):
        prior_contract.verify_pin_group(report[key])
    for key in ('geometry_oracle', 'input_before', 'artist_before', 'source_manifest', 'v9_factory_receipt'):
        prior_contract.verify_pin(report[key])
    require(report.get('witness_mode') == 'v9' and report.get('witness_adapter', {}).get('actual_witness') == 'v9'
        and report['v9_factory_receipt'] == report.get('v8_factory_receipt'), 'Checkpoint actual V9 witness differs')
    chooser = importlib.import_module('mesh_cache_actor_full30_004')
    chooser.validate_factory(json.loads(Path(report['v9_factory_receipt']['path']).read_text(encoding='utf-8-sig')))
    witness = importlib.import_module('native_validation_support_v9')
    require(report['source_witness_dependencies'] == witness.witness_dependency_pins(), 'Checkpoint V9 reader changed')
    require(report['source_manifest']['sha256'] == chooser.STAGE06_SHA
        and report['source_package'] == base.verify_package_manifest(
            Path(report['source_manifest']['path']).parent/'addons/character_designer',
            json.loads(Path(report['source_manifest']['path']).read_text(encoding='utf-8-sig'))), 'Checkpoint Stage06 authoring changed')
    for item in prior_contract._resources(report):
        prior_contract.verify_pin(item)
    report['_checkpoint_vertex_counts'] = checkpoint_cache_domains(report)
    return report, pin


def scene_source_proof():
    old = previous.scene_source_proof()
    manifest_path = STAGE10/'source_manifest.json'
    manifest = base.pin(manifest_path)
    scene_path = STAGE10/'addons/character_designer/forearm_twist_playback_scene.py'
    require(manifest['sha256'] == STAGE10_SHA and base.pin(scene_path)['sha256'] == STAGE10_SCENE_SHA,
        'Reviewed Stage10 unset-PG guard required')
    package = base.verify_package_manifest(scene_path.parent, json.loads(manifest_path.read_text(encoding='utf-8-sig')))
    def body(path):
        return [ast.dump(node, include_attributes=False) for node in ast.parse(path.read_text(encoding='utf-8')).body
            if not isinstance(node, ast.FunctionDef) or node.name != '_remap_rna']
    prior_path = STAGE09/'addons/character_designer/forearm_twist_playback_scene.py'
    require(body(scene_path) == body(prior_path), 'Stage10 changed beyond the one remapper guard')
    tree = ast.parse(scene_path.read_text(encoding='utf-8'))
    remap = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_remap_rna')
    remap_ast = ast.dump(remap, include_attributes=False)
    # The sole accepted AST delta is this reviewed, get-before-storage guard.
    expected_guard = ast.parse("""
if prop.type == 'POINTER' and getattr(prop, 'is_runtime', False):
    fixed = prop.fixed_type
    while fixed is not None and fixed.identifier != 'PropertyGroup':
        fixed = fixed.base
    if fixed is not None and not struct.is_property_set(name):
        continue
""").body[0]
    loops = [node for node in remap.body if isinstance(node, ast.For)
        and ast.unparse(node.iter) == 'struct.bl_rna.properties']
    require(len(loops) == 1, 'Stage10 property loop differs')
    matches = [node for node in loops[0].body if ast.dump(node) == ast.dump(expected_guard)]
    require(len(matches) == 1, 'Stage10 exact unset-PG guard missing')
    loops[0].body.remove(matches[0])
    old_tree = ast.parse(prior_path.read_text(encoding='utf-8'))
    old_remap = next(node for node in old_tree.body if isinstance(node, ast.FunctionDef) and node.name == '_remap_rna')
    require(ast.dump(remap) == ast.dump(old_remap), 'Stage10 remapper changed beyond the sole unset-PG guard')
    return {'previous_stage09': old, 'stage10_manifest': manifest, 'stage10_package': package,
        'remap_ast_sha256': hashlib.sha256(remap_ast.encode()).hexdigest(),
        'scope': 'Stage06 authoring and Parent08/Base09 retained; Stage10 only avoids unset registered PG getter. Separate Scene module, no Stage10 addon registration.'}


def load_scene_module(package, report):
    require(Path(package).resolve() == STAGE06/'addons/character_designer', 'Stage06 authoring package required')
    proof = scene_source_proof()
    name = 'character_designer._current_cache_scene_stage10_009'
    path = STAGE10/'addons/character_designer/forearm_twist_playback_scene.py'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        require(spec is not None and spec.loader is not None, 'Private Stage10 module spec missing')
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            if sys.modules.get(name) is module:
                del sys.modules[name]
            raise
    module = sys.modules[name]
    require(Path(module.__file__).resolve() == path, 'Unexpected private Scene module')
    report['current_scene_source_proof'] = proof
    return module
