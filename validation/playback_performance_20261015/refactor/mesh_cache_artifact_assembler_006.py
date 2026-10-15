"""Thin006 writer: unchanged005 main, deferred publication and Base-state binding.

All three runtime hooks have explicit ownership and are restored before publish.
The old005 source/receipt never changes and no old report is promoted to proof.
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
if hashlib.sha256((HERE/'mesh_cache_artifact_assembler_005.py').read_bytes()).hexdigest() != '8c9a8eb7552a756e772bb47954b5de092dc2bf8014b18280bfbb94a457246f72':
    raise RuntimeError('Sealed005 writer changed')
import mesh_cache_artifact_assembler_005 as previous
import mesh_cache_artifact_contract_006 as contract
import mesh_cache_view_layer_adapter_006 as visibility

base, require = contract.base, contract.require


def main(args, report):
    # New completed006 admission precedes opening the fixed input or writing.
    accepted, _ = contract.load_full30(args.full30_report, args.full30_sha256)
    sys.path.insert(0, str(Path(accepted['source_manifest']['path']).parent/'addons'))
    scene_module = importlib.import_module('character_designer.forearm_twist_playback_scene')
    sources = {name: base.pin(HERE/name) for name in (Path(__file__).name,
        'mesh_cache_artifact_contract_006.py', 'mesh_cache_view_layer_adapter_006.py',
        'mesh_cache_actor_full30_006.py', 'mesh_cache_artifact_assembler_005.py')}
    report['visibility_writer_sources'] = sources
    adapter = visibility.VisibilityAdapter(scene_module, report)
    original_contract, original_publish = previous.contract, previous.publish
    pending = []

    class AssemblyContract:
        def __getattr__(self, name):
            return getattr(contract, name)
        def check_frame(self, scene, reopen_contract, frame):
            if 'visibility' not in reopen_contract:
                require(adapter.session is not None and adapter.session.scene is scene,
                        'Visibility contract is not attached to the owned assembled Scene')
                state = report['visibility_contract']
                require(state == accepted['visibility_contract'], 'New fixed-input visibility differs from real Full30_006')
                reopen_contract['visibility'] = state
                reopen_contract['visibility_scope'] = 'Actual006 Source-to-clone per-ViewLayer Base state, Collection selectability and explicit Source context layer.'
            return contract.check_frame(scene, reopen_contract, frame)
        def animation_state(self, scene, reopen_contract):
            contract.check_visibility(scene, reopen_contract, all_layers=True)
            return contract.animation_state(scene, reopen_contract)

    proxy = AssemblyContract()
    def hold_publish(staged, output, observed):
        require(observed is report and not pending, 'Publication ownership/count differs')
        pending.append((staged, output))
        report['visibility_publication_deferred_until_hook_cleanup'] = True

    adapter.install()
    previous.contract, previous.publish = proxy, hold_publish
    try:
        previous.main(args, report)
    finally:
        bindings = (('contract', previous, 'contract', proxy, original_contract),
                    ('publication', previous, 'publish', hold_publish, original_publish))
        report['visibility_writer_hooks_still_owned'] = all(getattr(owner, attr) is installed
            for label, owner, attr, installed, original in bindings)
        restored = previous.importlib.import_module('mesh_cache_actor_parent_diagnostic_003').restore_owned_hooks(bindings)
        report['visibility_writer_hooks_restored'] = all(restored.values())
        adapter.close()
        report['visibility_writer_sources_unchanged'] = all(item == base.pin(item['path']) for item in sources.values())
    require(all(report.get(key) is True for key in ('visibility_writer_hooks_still_owned', 'visibility_writer_hooks_restored',
        'visibility_writer_sources_unchanged', 'source_to_clone_visibility_exact', 'visibility_hook_still_owned',
        'visibility_hook_restored', 'visibility_sources_unchanged', 'visibility_stage09_unchanged')),
        '006 writer ownership/source/visibility cleanup failed')
    report['visibility_all_30_geometry_and_flags_exact'] = (len(report['replay']) == 30
        and [row['frame'] for row in report['replay']] == list(contract.FRAMES)
        and all(row.get('exact') is True and row.get('visibility_exact') is True for row in report['replay']))
    require(report['visibility_all_30_geometry_and_flags_exact'] and len(pending) == 1,
            'No complete006 geometry/visibility staging candidate')
    contract.verify_external_pins(report)
    staged, output = pending[0]
    require(base.pin(staged) == report['artifact_staged'], 'Owned staging content changed before006 publication')
    original_publish(staged, output, report)
    report['visibility_writer_completed'] = True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('full30-report', 'full30-sha256', 'artist', 'output', 'report'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema': contract.RECEIPT_SCHEMA, 'completed': False, 'artifact_published': False,
        'artifact_publication_complete': False, 'gui_fps_verified': False, 'normal_reopen_verified': False,
        'visibility_writer_completed': False, 'pid': os.getpid(),
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'limits': ['Earlier fixed40644 private snapshot, not current live-model equivalence.',
            'Local persistent external PC2/image dependencies, not a fully packed portable bundle.',
            'Actual006 Base visibility and full geometry proof required; independent normal GUI reopen/FPS and shader appearance still pending.']}
    with Path(args.report).resolve().open('x', encoding='utf-8') as stream:
        try:
            main(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
