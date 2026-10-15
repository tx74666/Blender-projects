"""Unchanged Full30 004.run_owned/002.main plus sealed Stage09 Base copying.

The new entry has its own unused cache directory and explicit provenance. It
does not claim old geometry receipts already prove per-layer visibility.
"""
import argparse
import datetime
import importlib
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mesh_cache_actor_full30_004 as previous
import mesh_cache_view_layer_adapter_006 as visibility

base, require = previous.base, previous.require


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath
        and bpy.app.version[:2] == (5, 2), 'Fresh private factory-startup Blender5.2 required')
    require(any(value in ('-t', '--threads') and native[index+1] == '1'
        for index, value in enumerate(native[:-1])), '-t 1 required')
    require(Path(args.addons).resolve() == previous.STAGE06/'addons'
        and Path(args.source_manifest).resolve() == previous.STAGE06/'source_manifest.json', 'Fixed Stage06 paths required')
    require(Path(args.cache_dir).resolve() == HERE/'blendcache_full30_006' and not Path(args.cache_dir).exists(),
            'Unused ignored blendcache_full30_006 required')
    sources = {name: base.pin(HERE/name) for name in (*previous.PINS, 'mesh_cache_actor_full30_004.py')}
    require(sources['mesh_cache_actor_full30_004.py']['sha256'] == 'f447574e7120c8a93fd8db5d3746f5fb5c7370ef922942dd576731fe1a715c12', 'Sealed004 changed')
    for name, sha in previous.PINS.items():
        require(sources[name]['sha256'] == sha, 'Prior dependency changed: '+name)
    stages = [base.pin(stage/'source_manifest.json') for stage in (previous.STAGE06, previous.STAGE08)]
    require([item['sha256'] for item in stages] == [previous.STAGE06_SHA, previous.STAGE08_SHA], 'Parent/source stage seals differ')
    packages = [base.verify_package_manifest(Path(item['path']).parent/'addons/character_designer',
        json.loads(Path(item['path']).read_text(encoding='utf-8-sig'))) for item in stages]
    report.update(adapter_sources=sources, adapter_stage06=stages[0], adapter_stage08=stages[1],
        visibility_entry_sources={Path(__file__).name: base.pin(__file__)},
        visibility_entry_scope='Entry006 preflight then unchanged004.run_owned/002.main; Stage08 parent plus Stage09 Base helper. Prior004 main is not called because006 requires its own unused cache path.')
    sys.path.insert(0, str(previous.STAGE06/'addons'))
    scene_module = importlib.import_module('character_designer.forearm_twist_playback_scene')
    require(Path(scene_module.__file__).resolve() == previous.STAGE06/'addons/character_designer/forearm_twist_playback_scene.py', 'Wrong Scene module')
    adapter = visibility.VisibilityAdapter(scene_module, report).install()
    original_geometry = base.geometry_witness
    first_pointer = None
    report['visibility_replay'] = []

    def geometry(obj, reverse):
        nonlocal first_pointer
        session = adapter.session
        if session is not None and not session.closed and bpy.context.scene is session.scene:
            if first_pointer is None:
                first = min(((source, target) for source, target in session.object_map.items() if source.type == 'MESH'),
                            key=lambda pair: pair[0].name)[1]
                first_pointer = int(first.as_pointer())
            if int(obj.as_pointer()) == first_pointer:
                token = (session.scene.frame_current, float(session.scene.frame_subframe))
                result = visibility.check_visibility(session.scene, report['visibility_contract'], all_layers=False)
                report['visibility_replay'].append({'frame': token[0], 'subframe': token[1], **result})
        return original_geometry(obj, reverse)

    base.geometry_witness = geometry
    try:
        previous.run_owned(args, report, scene_module)
    finally:
        report['visibility_geometry_hook_still_owned'] = base.geometry_witness is geometry
        report['visibility_geometry_hook_restored'] = previous.parent.restore_owned_hooks((
            ('geometry', base, 'geometry_witness', geometry, original_geometry),))['geometry']
        adapter.close()
        report['adapter_sources_unchanged'] = all(item == base.pin(item['path']) for item in sources.values())
        report['adapter_stage_manifests_unchanged'] = all(item == base.pin(item['path']) for item in stages)
        report['adapter_packages_unchanged'] = all(expected == base.verify_package_manifest(
            Path(item['path']).parent/'addons/character_designer', json.loads(Path(item['path']).read_text(encoding='utf-8-sig')))
            for item, expected in zip(stages, packages))
        report['visibility_entry_sources_unchanged'] = all(item == base.pin(item['path']) for item in report['visibility_entry_sources'].values())
    visits = [frame for block, frames in previous.runner.replay_visits() for frame in frames]
    report['all_replay_visibility_exact'] = ([row['frame'] for row in report['visibility_replay']] == visits
        and all(row['exact'] is True and row['subframe'] == 0. for row in report['visibility_replay']))
    require(all(report.get(key) is True for key in ('source_to_clone_visibility_exact', 'all_replay_visibility_exact',
        'visibility_geometry_hook_still_owned', 'visibility_geometry_hook_restored', 'visibility_entry_sources_unchanged',
        'adapter_sources_unchanged', 'adapter_stage_manifests_unchanged', 'adapter_packages_unchanged'))
        and all(report['adapter_hooks_still_owned'].values()) and all(report['adapter_hooks_restored'].values()), '006 visibility/source/hook proof failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('input', 'artist', 'addons', 'source-manifest', 'cache-dir', 'report', 'v9-factory-report', 'v9-factory-sha256'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--witness', choices=('v9',), required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema': 'x.pc2-fixed-actor-full30/1', 'completed': False, 'diagnostic_only': True,
        'pid': os.getpid(), 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'no_artifact_save': True, 'gui_fps_verified': False,
        'limits': ['Earlier fixed40644 private snapshot, not current live-model equivalence.',
            'New actual150-visit geometry AND per-layer Base proof required; prior004/003 PASS is not visibility acceptance.',
            'Background frame pipeline is not GUI FPS; no shader/subframe/motion-blur or artist adoption proof.']}
    with Path(args.report).resolve().open('x', encoding='utf-8') as stream:
        try:
            main(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
