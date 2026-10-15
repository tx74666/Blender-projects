"""Read-only006 extension: actual Base-state Full30 proof plus published005 payload.

The original contract/schema and complete geometry/Action proof stay intact.
The new entry is mandatory and explicitly names its extra visibility evidence.
"""
import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PINS = {
    'mesh_cache_artifact_contract_005.py': 'a4e68220734435de8f8ac52bbbca73c2b7259253626c1bc301dfcfc9b55efad6',
    'mesh_cache_view_layer_adapter_006.py': '67c19992951108e2b91ab0f3eac60c1e552f070aafafbd6466d7f084104d02b7',
    'mesh_cache_actor_full30_006.py': '29eb8decdbaa0f2c99ce08d2994431ecea5b4fc7b804a699c627a66385a5f0c7',
}
for name, sha in PINS.items():
    if hashlib.sha256((HERE/name).read_bytes()).hexdigest() != sha:
        raise RuntimeError('Sealed006 dependency changed: '+name)
import mesh_cache_artifact_contract_005 as previous
import mesh_cache_view_layer_adapter_006 as visibility

base, require = previous.base, previous.require
SCHEMA, RECEIPT_SCHEMA = previous.SCHEMA, previous.RECEIPT_SCHEMA
FRAMES, CACHE_SETTINGS, PORTABLE_SHA = previous.FRAMES, previous.CACHE_SETTINGS, previous.PORTABLE_SHA
logical, json_value = previous.logical, previous.json_value
scene_state, modifier_state = previous.scene_state, previous.modifier_state
dependency_closure = previous.dependency_closure
animation_state = previous.animation_state
check_serialized_dependencies = previous.check_serialized_dependencies


def validate_visibility_report(report):
    flags = ('source_to_clone_visibility_exact', 'all_replay_visibility_exact', 'visibility_hook_still_owned',
        'visibility_hook_restored', 'visibility_sources_unchanged', 'visibility_stage09_unchanged',
        'visibility_geometry_hook_still_owned', 'visibility_geometry_hook_restored', 'visibility_entry_sources_unchanged')
    require(all(report.get(key) is True for key in flags), 'Actual006 visibility/source/hook gates required')
    previous.verify_pin_group(report['visibility_adapter_sources'])
    previous.verify_pin_group(report['visibility_entry_sources'])
    require(report['visibility_adapter_sources'].get('mesh_cache_view_layer_adapter_006.py', {}).get('sha256')
        == PINS['mesh_cache_view_layer_adapter_006.py'] and report['visibility_entry_sources'].get('mesh_cache_actor_full30_006.py', {}).get('sha256')
        == PINS['mesh_cache_actor_full30_006.py'], 'Wrong006 native entry/helper')
    seal = report['visibility_override']
    previous.verify_pin(seal['manifest'])
    previous.verify_pin(seal['scene_source'])
    require(seal['manifest']['sha256'] == visibility.MANIFEST_SHA
        and seal['scene_source']['sha256'] == visibility.SCENE_SHA, 'Stage09 visibility seal differs')
    node = next(item for item in ast.parse(Path(seal['scene_source']['path']).read_text(encoding='utf-8')).body
        if isinstance(item, ast.FunctionDef) and item.name == '_copy_view_layer_state')
    require(seal['function_ast_sha256'] == hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest(), 'Visibility AST seal differs')
    require(seal['package'] == base.verify_package_manifest(Path(seal['manifest']['path']).parent/'addons/character_designer',
        json.loads(Path(seal['manifest']['path']).read_text(encoding='utf-8-sig'))), 'Stage09 package changed')
    visits = [frame for block, frames in importlib.import_module('mesh_cache_actor_full30_002').replay_visits() for frame in frames]
    require([row['frame'] for row in report['visibility_replay']] == visits
        and all(row['exact'] is True and row['subframe'] == 0. for row in report['visibility_replay']), 'All150 actual visibility visits required')


def load_full30(path, sha):
    report, pin = previous.load_full30(path, sha)
    validate_visibility_report(report)
    return report, pin


def check_visibility(scene, contract, all_layers=True):
    return visibility.check_visibility(scene, contract['visibility'], all_layers=all_layers)


def check_binding(scene, contract):
    result = previous.check_binding(scene, contract)
    check_visibility(scene, contract, all_layers=False)
    return result


def check_frame(scene, contract, frame):
    check_visibility(scene, contract, all_layers=False)
    return {**previous.check_frame(scene, contract, frame), 'visibility_exact': True}


def verify_external_pins(receipt):
    result = previous.verify_external_pins(receipt)
    load_full30(receipt['accepted_full30_report']['path'], receipt['accepted_full30_report']['sha256'])
    previous.verify_pin_group(receipt['visibility_writer_sources'])
    return {**result, 'visibility_sources_verified': True}


def load_published_receipt(path, sha):
    receipt, pin = previous.load_published_receipt(path, sha)
    require(receipt.get('visibility_writer_completed') is True
        and receipt.get('visibility_writer_hooks_still_owned') is True
        and receipt.get('visibility_writer_hooks_restored') is True
        and receipt.get('visibility_writer_sources_unchanged') is True
        and receipt.get('visibility_all_30_geometry_and_flags_exact') is True,
        'Actually completed006 visibility artifact writer required')
    require(receipt['reopen_contract'].get('visibility') == receipt['visibility_contract'], 'Serialized visibility contract differs')
    verify_external_pins(receipt)
    return receipt, pin
