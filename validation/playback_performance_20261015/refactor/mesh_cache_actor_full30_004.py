"""Run unchanged Full30_002 with explicit V9 proof and sealed parent remap.

Root alone launches Native. The legacy v8_* receipt names below are disclosed
aliases for actual V9 provenance, so every original final cleanup gate executes.
No solver, geometry, seek, timing or acceptance policy is replaced here.
"""
import argparse
import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PINS = {
    'mesh_cache_actor_full30_002.py': '261b5508bab90426f1edb4e632fcecca6de4b893ab3e840ba101828cdbce4377',
    'mesh_cache_actor_parent_diagnostic_003.py': 'e2015c64d1e83e2ac4dba1339dd488cce8f36d09f4adc9f900144bc661b5e73b',
    'native_parent_remap_fixture_003.py': 'cecb4fe297942de7282c97ae1a6cba4c9c7c5d91128b6529f6b255b8948c8eea',
    'native_validation_support_v9.py': '55f4b4b75a2ff5991f250d845fbbb295e7ef153874fb03dbeb7f169b5c048ed5',
    'native_source_reference_witness_v9.py': 'fb87e81b29482e2668b6d29449713e4ddf4885797e6860100f118dd4bfa6b192',
    'native_keyframe_bulk_factory_008.py': '986b1ad696222cf4fb7d1ff1381dcc149691f56af543a786a68c8d706a69a606',
    'native_keyframe_bulk_factory_009.py': 'e6e37eeec0c1132c6132bd0b96c990de9bc7e58a13d2fe3df21e27503101c58c',
    'native_source_reference_witness_v7.py': '1e0d888f6a1db20d8261cb1f56fdcb065af59a0c70a8264a0d3dff67d70de542',
}
for _name, _sha in PINS.items():
    if hashlib.sha256((HERE/_name).read_bytes()).hexdigest() != _sha:
        raise RuntimeError('Protected adapter dependency changed: '+_name)
import mesh_cache_actor_full30_002 as runner
import mesh_cache_actor_parent_diagnostic_003 as parent
import native_validation_support_v9 as witness

base, require = runner.base, runner.require
STAGE06 = HERE/'staged_20261015_06'
STAGE08 = HERE/'staged_20261015_08'
STAGE06_SHA = '5c7965ef74e99ed8036bc57ad639cb4db37e6501bb580483a676d4b2fd6cc3c0'
STAGE08_SHA = 'a8bf6d459b5c058efb32c7935199b64c010d327ef6d5d9e90831d95a99c51bf8'
FLAGS = ('bulk_read_did_not_write_old_point_state', 'all15_field_coverage_exact', 'reader_dispatch_bulk',
         'all_fixture_ids_removed', 'handlers_unchanged', 'artist_disk_unchanged', 'stage_unchanged',
         'witness_sources_unchanged', 'scripts_unchanged', 'factory_overrides_still_owned',
         'factory_overrides_restored', 'wrapper_factory_sources_unchanged')


def validate_factory(receipt):
    require(receipt.get('schema') == 'x.native-keyframe-bulk-factory/1'
            and receipt.get('completed') is True and 'error' not in receipt
            and str(receipt.get('blender', '')).startswith('5.2'), 'Actual passed 5.2 Factory009 required')
    require(all(receipt.get(key) is True for key in FLAGS) and not receipt.get('cleanup_errors'),
            'Factory009 proof/cleanup gates failed')
    fields = witness._extension.KEYFRAME_FIELDS
    for key, names in (
        ('field_checks', set(fields)),
        ('enum_api_checks', {name for name, (kind, width) in fields.items() if kind == 'ENUM'}),
        ('mutation_traps', {'co_and_handle', 'enum', 'add_key', 'remove_key', 'native_custom_storage_unsupported'}),
    ):
        values = receipt.get(key)
        require(isinstance(values, dict) and set(values) == names
                and all(value is True for value in values.values()), 'Factory009 coverage differs: '+key)
    states = receipt.get('old_point_state_sha256_before_after')
    require(isinstance(states, list) and len(states) == 2 and states[0] == states[1]
            and isinstance(states[0], str) and len(states[0]) == 64
            and all(char in '0123456789abcdef' for char in states[0]), 'Factory009 no-write proof differs')
    deps = witness.witness_dependency_pins()
    require(receipt.get('witness_sources') == deps, 'Factory009 used different V9 witness sources')
    scripts = {name: base.pin(HERE/name) for name in (
        'native_keyframe_bulk_factory_008.py', 'native_validation_support_v9.py',
        'native_source_reference_witness_v9.py', 'native_source_reference_witness_v7.py')}
    require(receipt.get('scripts') == scripts, 'Factory009 original source set changed')
    expected_override = {key: base.pin(HERE/name) for key, name in (
        ('wrapper', 'native_keyframe_bulk_factory_009.py'), ('unchanged_factory', 'native_keyframe_bulk_factory_008.py'),
        ('bulk', 'native_source_reference_witness_v9.py'), ('support', 'native_validation_support_v9.py'))}
    require(receipt.get('factory_override') == expected_override, 'Factory009 wrapper/source provenance differs')
    return deps, {**scripts, 'native_keyframe_bulk_factory_009.py': expected_override['wrapper']}


def choose_v9(args, report):
    require(args.witness == 'v9' and args.v9_factory_report and args.v9_factory_sha256,
            'Explicit V9 and actual Factory009 receipt path/SHA required')
    receipt_pin = base.pin(args.v9_factory_report)
    require(receipt_pin['sha256'] == args.v9_factory_sha256, 'Factory009 receipt SHA differs')
    receipt = json.loads(Path(args.v9_factory_report).read_text(encoding='utf-8-sig'))
    deps, sources = validate_factory(receipt)
    # Unchanged 002 finally uses these names; aliases contain real V9 provenance.
    args.v8_factory_report = args.v9_factory_report
    report.update(v8_factory_receipt=receipt_pin, v8_factory_sources=sources,
        v9_factory_receipt=receipt_pin, source_witness_dependencies=deps,
        source_property_scope='V9 stored/raw/registered/foreign payload plus exact 15-field native Keyframe bulk; unset/computed outputs and other ID content remain unclaimed.',
        witness_adapter={'schema': 'x.full30-v9-parent-adapter/1', 'actual_witness': 'v9',
            'legacy_receipt_aliases': 'v8_factory_* fields refer to this actual V9 Factory009, solely for unchanged 002 final checks.'})
    return witness, deps


def run_owned(args, report, scene_module):
    original_choose, original_remap = runner.choose_witness, scene_module._remap_rna
    patched, owned_globals, seal = parent.sealed_remap(scene_module.__dict__)
    owned_globals['_remap_rna'] = patched
    require(patched.__globals__ is owned_globals, 'Parent remap recursion globals differ')
    report['parent_override'] = seal
    runner.choose_witness, scene_module._remap_rna = choose_v9, patched
    try:
        runner.main(args, report)
    finally:
        bindings = (('parent_remap', scene_module, '_remap_rna', patched, original_remap),
                    ('witness_chooser', runner, 'choose_witness', choose_v9, original_choose))
        report['adapter_hooks_still_owned'] = {name: getattr(owner, attr) is installed
            for name, owner, attr, installed, original in bindings}
        report['adapter_hooks_restored'] = parent.restore_owned_hooks(bindings)


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath
            and bpy.app.version[:2] == (5, 2), 'Fresh private 5.2 factory background required')
    require(any(value in ('-t', '--threads') and native[index+1] == '1'
                for index, value in enumerate(native[:-1])), '-t 1 required')
    require(Path(args.addons).resolve() == STAGE06/'addons'
            and Path(args.source_manifest).resolve() == STAGE06/'source_manifest.json', 'Fixed Stage06 paths required')
    require(Path(args.cache_dir).resolve() == HERE/'cache' and not (HERE/'cache').exists(),
            'Unused ignored direct-child refactor/cache required')
    sources = {name: base.pin(HERE/name) for name in (*PINS, Path(__file__).name)}
    for name, expected in PINS.items():
        require(sources[name]['sha256'] == expected, 'Adapter dependency changed: '+name)
    manifest06, manifest08 = base.pin(STAGE06/'source_manifest.json'), base.pin(STAGE08/'source_manifest.json')
    require(manifest06['sha256'] == STAGE06_SHA and manifest08['sha256'] == STAGE08_SHA, 'Stage06/08 seal changed')
    sealed06 = base.verify_package_manifest(STAGE06/'addons/character_designer',
        json.loads((STAGE06/'source_manifest.json').read_text(encoding='utf-8-sig')))
    sealed08 = base.verify_package_manifest(STAGE08/'addons/character_designer',
        json.loads((STAGE08/'source_manifest.json').read_text(encoding='utf-8-sig')))
    report.update(adapter_sources=sources, adapter_stage06=manifest06, adapter_stage08=manifest08)
    sys.path.insert(0, str(STAGE06/'addons'))
    scene_module = importlib.import_module('character_designer.forearm_twist_playback_scene')
    require(Path(scene_module.__file__).resolve() == STAGE06/'addons/character_designer/forearm_twist_playback_scene.py',
            'Wrong Stage06 Scene module')
    try:
        run_owned(args, report, scene_module)
    finally:
        report['adapter_sources_unchanged'] = all(item == base.pin(item['path']) for item in sources.values())
        report['adapter_stage_manifests_unchanged'] = (manifest06 == base.pin(manifest06['path'])
            and manifest08 == base.pin(manifest08['path']))
        report['adapter_packages_unchanged'] = (sealed06 == base.verify_package_manifest(
            STAGE06/'addons/character_designer', json.loads((STAGE06/'source_manifest.json').read_text(encoding='utf-8-sig')))
            and sealed08 == base.verify_package_manifest(STAGE08/'addons/character_designer',
            json.loads((STAGE08/'source_manifest.json').read_text(encoding='utf-8-sig'))))
    require(all(report['adapter_hooks_still_owned'].values()) and all(report['adapter_hooks_restored'].values())
            and all(report[key] for key in ('adapter_sources_unchanged', 'adapter_stage_manifests_unchanged',
                                           'adapter_packages_unchanged')), 'Adapter ownership/pin cleanup failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('input', 'artist', 'addons', 'source-manifest', 'cache-dir', 'report',
                 'v9-factory-report', 'v9-factory-sha256'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--witness', choices=('v9',), required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema': 'x.pc2-fixed-actor-full30/1', 'completed': False, 'diagnostic_only': True,
        'pid': os.getpid(), 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'no_artifact_save': True, 'no_adoption_or_deploy': True, 'gui_fps_verified': False,
        'limits': ['Unchanged Full30_002 exact geometry/static/world/normal and source cleanup gates apply.',
                   'Frames 1-30 only; background pipeline timings are not GUI playback FPS.',
                   'No shader visual/subframe/motion-blur proof, blend save or production adoption.',
                   'Stage06/.41 plus disclosed sealed Stage08 _remap_rna only; no diagnostic frame/update hooks.']}
    with Path(args.report).resolve().open('x', encoding='utf-8') as stream:
        try:
            main(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
