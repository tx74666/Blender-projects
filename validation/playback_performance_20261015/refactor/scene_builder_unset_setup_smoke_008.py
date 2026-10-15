"""Factory-only regression for copying a Scene whose Setup was never stored."""
import argparse
import importlib
import json
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_validation_support_v7 as witness


def require(value, message):
    if not value:
        raise RuntimeError(message)


def main(args, report):
    import bpy
    native = sys.argv[:sys.argv.index('--')]
    require(bpy.app.background and '--factory-startup' in native and not bpy.data.filepath,
            'A new empty factory-startup background worker is required')
    require(any(value in ('-t', '--threads') and native[index+1] == '1'
                for index, value in enumerate(native[:-1])), 'Explicit native -t 1 required')
    package = Path(args.addons).resolve() / 'character_designer'
    manifest = json.loads(Path(args.source_manifest).read_text(encoding='utf-8-sig'))
    sources = witness.verify_package_manifest(package, manifest)
    require(sources['forearm_twist_playback_scene.py']['sha256'] ==
            'e4f4f58378540d23ea8c3acf6f4bbc7a3b056494b7af480e2f3b9aa092ecef3d',
            'This regression requires the reviewed Scene stored-Setup fix')
    artist_before = witness.pin(args.artist)
    dependencies = witness.witness_dependency_pins()
    handlers = witness.handler_snapshot()
    sys.path.insert(0, str(package.parent))
    addon = importlib.import_module('character_designer')
    builder = importlib.import_module('character_designer.forearm_twist_playback_scene')
    require(Path(addon.__file__).resolve().parent == package, 'Imported another addon package')
    source, session, protected, private_ids = bpy.context.scene, None, None, set()
    registered, errors = False, []
    report.update(script=witness.pin(__file__), source_manifest=witness.pin(args.source_manifest),
                  artist_before=artist_before, witness_dependencies=dependencies,
                  blender=bpy.app.version_string, version=list(addon.bl_info['version']))
    try:
        addon.register()
        registered = True
        name = 'character_designer_setup'
        require(source.bl_rna.properties.get(name) is not None, 'Setup RNA declaration is missing')
        require(not source.is_property_set(name), 'Regression requires genuinely unset source Setup')
        protected = witness.source_property_witness(source)
        require(not source.is_property_set(name), 'Source witness materialized unset Setup')
        before_ids = witness.native_id_pointers()
        try:
            session = builder.build_isolated_scene(source)
        finally:
            private_ids = witness.native_id_pointers() - before_ids
        after = witness.source_property_witness(source)
        report['after_build'] = {'properties_exact': protected == after,
            'source_setup_remains_unset': not source.is_property_set(name),
            'changed_components': sorted(key for key in set(protected['components']) | set(after['components'])
                if protected['components'].get(key) != after['components'].get(key))}
        require(report['after_build']['properties_exact'] and report['after_build']['source_setup_remains_unset'],
                'Scene copy materialized or changed its unset source Setup')
    finally:
        if session is not None:
            try:
                session.close()
            except BaseException:
                errors.append(traceback.format_exc())
        if protected is not None:
            try:
                after_close = witness.source_property_witness(source)
                report['after_close'] = {'properties_exact': protected == after_close,
                    'source_setup_remains_unset': not source.is_property_set('character_designer_setup')}
            except BaseException:
                errors.append(traceback.format_exc())
        if registered:
            try:
                addon.unregister()
            except BaseException:
                errors.append(traceback.format_exc())
        report['cleanup'] = {'errors': errors,
            'all_owned_ids_removed': not bool(private_ids & witness.native_id_pointers()),
            'handlers_restored_exact': handlers == witness.handler_snapshot()}
        report['artist_disk_unchanged'] = artist_before == witness.pin(args.artist)
        report['staged_sources_unchanged'] = sources == witness.verify_package_manifest(package, manifest)
        report['witness_dependencies_unchanged'] = dependencies == witness.witness_dependency_pins()
        require(not errors and all(value for key, value in report['cleanup'].items() if key != 'errors'),
                'Factory copy cleanup failed')
        require(protected is not None and all(report.get('after_close', {}).values()),
                'Source Setup changed during owned cleanup')
        require(report['artist_disk_unchanged'] and report['staged_sources_unchanged']
                and report['witness_dependencies_unchanged'] and not bpy.data.filepath,
                'Protected disks/sources changed or a file was opened')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('artist', 'addons', 'source-manifest', 'report'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report = {'schema': 'x.unset-setup-scene-copy-smoke/1', 'completed': False,
        'no_blend_open_or_save': True, 'no_gui': True, 'performance_acceptance': False,
        'scope': 'Raw source properties before/after private Scene copy and owned cleanup; no Setup getter is called by this probe. No geometry or FPS acceptance.'}
    with Path(args.report).resolve().open('x', encoding='utf-8') as stream:
        try:
            main(args, report)
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
