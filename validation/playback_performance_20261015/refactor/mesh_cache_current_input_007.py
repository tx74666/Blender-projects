"""Bounded current SaveCopy admission and explicit isolated Stage09 loader.

No addon/scene operations occur on import. The actual Foundation006 and current
SaveCopy receipts are required before opening any file. No hash substitution,
legacy module mutation or Stage09 package __init__ execution is used.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_validation_support as base
import mesh_cache_artifact_contract_006 as foundation

SAVE_COPY_SHA = '0de04db4929e725446ee9ec0e9414b26894274776edda6ad28852d9b1b29c9d4'
SAVE_FLAGS = ('protected_context_base_exact', 'source_properties_exact',
    'protected_context_base_after_witness_exact', 'artist_disk_exact', 'package_disk_exact',
    'dependencies_exact', 'script_exact', 'normal_save_handlers_preserved')
STAGE06 = HERE/'staged_20261015_06'
STAGE08 = HERE/'staged_20261015_08'
STAGE09 = HERE/'staged_20261015_09'
require = foundation.require


def load_snapshot(path, receipt_sha, input_sha, input_bytes):
    pin = base.pin(path)
    require(pin['sha256'] == receipt_sha, 'Actual current SaveCopy receipt SHA differs')
    report = json.loads(Path(pin['path']).read_text(encoding='utf-8-sig'))
    require(report.get('schema') == 'x.current-model-save-copy/1' and report.get('completed') is True
        and 'error' not in report and 'after_proof_error' not in report
        and report.get('copy_attempted') is True and report.get('operator_result') == ['FINISHED']
        and all(report.get(key) is True for key in SAVE_FLAGS), 'Actual guarded SaveCopy PASS required')
    foundation.previous.verify_pin(report['script'])
    require(report['script']['sha256'] == SAVE_COPY_SHA, 'Different SaveCopy producer')
    foundation.previous.verify_pin_group(report['dependencies'])
    source = report['copy']
    foundation.previous.verify_pin(source)
    require(type(input_bytes) is int and input_bytes > 0 and source['bytes'] == input_bytes
        and source['sha256'] == input_sha, 'Explicit current input SHA/length differs')
    artist = report['artist_before']
    require(Path(artist['path']).resolve() == HERE.parents[2]/'X.blend'
        and Path(source['path']).resolve() != Path(artist['path']).resolve(), 'Current canonical artist/copy paths differ')
    identity = report['source_identity']
    require(Path(identity['filepath']).resolve() == Path(artist['path']).resolve() and identity['scene'] and identity['view_layer']
        and len(identity['frame']) == 2 and type(identity['frame'][0]) is int
        and 1 <= identity['frame'][0] <= 30 and float(identity['frame'][1]) == 0., 'Current saved integer1-30 context required')
    require(str(report.get('loaded_metadata', {}).get('blender', '')).startswith('5.2'), 'Observed Blender5.2 current capture required')
    return report, pin


def scene_source_proof():
    paths = [stage/'source_manifest.json' for stage in (STAGE06, STAGE08, STAGE09)]
    pins = [base.pin(path) for path in paths]
    require([item['sha256'] for item in pins] == [
        '5c7965ef74e99ed8036bc57ad639cb4db37e6501bb580483a676d4b2fd6cc3c0',
        'a8bf6d459b5c058efb32c7935199b64c010d327ef6d5d9e90831d95a99c51bf8',
        'b8faecfb0ce428bbdc3d845494fae7cb2aa5db4b4c9ad875e399194f98529ee6'], 'Reviewed06/08/09 source seals differ')
    packages = [base.verify_package_manifest(path.parent/'addons/character_designer',
        json.loads(path.read_text(encoding='utf-8-sig'))) for path in paths]
    def functions(stage):
        path = stage/'addons/character_designer/forearm_twist_playback_scene.py'
        return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(path.read_text(encoding='utf-8')).body
                if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    old, parent, current = (functions(stage) for stage in (STAGE06, STAGE08, STAGE09))
    require(current['_remap_rna'] == parent['_remap_rna'], 'Stage09 parent function is not sealed08')
    allowed = {'_remap_rna', '_copy_view_layer_state', 'PlaybackSceneSession', 'build_isolated_scene'}
    require(all(current[name] == value for name, value in old.items() if name not in allowed), 'Unrelated Scene implementation changed')
    return {'manifests': pins, 'packages': packages,
        'parent_ast_sha256': hashlib.sha256(current['_remap_rna'].encode()).hexdigest(),
        'base_ast_sha256': hashlib.sha256(current['_copy_view_layer_state'].encode()).hexdigest(),
        'scope': 'Stage06 authoring/registration; separate sealedStage09 Scene module contains Parent08/Base09. Stage09 addon __init__ is never loaded.'}


def load_scene_module(package, report):
    require(Path(package).resolve() == STAGE06/'addons/character_designer', 'Stage06 authoring package required')
    proof = scene_source_proof()
    name = 'character_designer._current_cache_scene_stage09_007'
    path = STAGE09/'addons/character_designer/forearm_twist_playback_scene.py'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        require(spec is not None and spec.loader is not None, 'Private Stage09 module spec missing')
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
