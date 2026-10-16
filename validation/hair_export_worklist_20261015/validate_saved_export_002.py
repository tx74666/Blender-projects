"""Prepare/run one pinned saved-X model export in a disposable Blender process.

Root alone may run this after obtaining the serial native window. No subprocess,
artist save, add-on-wide registration, coordinator publication, or Unity access.
The real model worker runs after reopening a new local libraries.write snapshot;
its FBX is then imported into an empty scene in this same disposable process.
"""
from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback
import types
import uuid

HERE = Path(__file__).resolve().parent
ARTIST = HERE.parents[1] / 'X.blend'
ARTIST_SHA = 'db10be327442c98dd5148d504440ae5ab713320a9a618de889d4faff03c4719d'
ARTIST_BYTES = 34837592
PROJECTION = HERE / 'release_projection_07743.json'
PROJECTION_SHA = '9baac8f7575b121c5aa95502ad02b0a6762229fd7e86e395a1fb803eeade2b4c'
PACKAGE = HERE / 'release_07743' / 'character_designer'
SUPPORT = HERE / 'inspect_live_hair.py'
SUPPORT_SHA = '8721c2748f7f5440b3bfa93cfbd4ed832db95c575314d7164ab3c5b04fb0cb86'
EXPECTED_OBJECTS = ('CoshaRig', 'Clothes', 'Cosha', 'Dress', 'Hair', 'Shoes', 'Stocking')
EXPECTED_MESHES = frozenset(EXPECTED_OBJECTS) - {'CoshaRig'}
EXPORT_PROPERTY = 'character_designer_unity_export'
PACKAGE_NAME = '_x_saved_model_export_07743_002'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path):
    path = Path(path).resolve(strict=True)
    digest, count = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
            count += len(block)
    return {'path': str(path), 'sha256': digest.hexdigest(), 'bytes': count}


def write_new_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def package_proof():
    manifest_pin = pin(PROJECTION)
    require(manifest_pin['sha256'] == PROJECTION_SHA, 'Frozen .43 projection changed')
    manifest = json.loads(PROJECTION.read_text(encoding='utf-8-sig'))
    require(manifest['module'] == 'character_designer' and manifest['version'] == '0.77.43'
            and Path(manifest['source_root']).resolve() == PACKAGE.resolve()
            and len(manifest['files']) == 190, 'Unexpected .43 projection identity')
    actual = {p.relative_to(PACKAGE).as_posix(): p for p in PACKAGE.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    require(set(actual) == set(manifest['files']), 'Frozen .43 package file inventory changed')
    for name, path in actual.items():
        require(pin(path)['sha256'] == manifest['files'][name], 'Frozen .43 file changed: ' + name)
    return {'manifest': manifest_pin, 'files': len(actual), 'version': manifest['version']}


def input_proof():
    value = pin(ARTIST)
    require(value['sha256'] == ARTIST_SHA and value['bytes'] == ARTIST_BYTES,
            'Saved X changed; capture a new explicit input pin instead of changing this validator')
    return value


def private_package():
    require(PACKAGE_NAME not in sys.modules, 'This validation package is already loaded')
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__, package.__package__ = [str(PACKAGE)], PACKAGE_NAME
    package.__file__ = str(PACKAGE / '__init__.py')
    tree = ast.parse((PACKAGE / '__init__.py').read_bytes())
    package.bl_info = next(ast.literal_eval(node.value) for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == 'bl_info' for target in node.targets))
    require(tuple(package.bl_info['version']) == (0, 77, 43), 'Frozen package version differs')
    sys.modules[PACKAGE_NAME] = package
    return package


def support_module():
    require(pin(SUPPORT)['sha256'] == SUPPORT_SHA, 'Saved-state observer source changed')
    spec = importlib.util.spec_from_file_location('_x_saved_export_observer002', SUPPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_saved_export_config(bpy, rig, report):
    """Use the real four config RNA classes; never emulate collection storage."""
    require(EXPORT_PROPERTY in rig, 'Pinned saved rig has no saved export profile')
    require(bpy.types.Object.bl_rna.properties.get(EXPORT_PROPERTY) is None,
            'Unexpected existing export property registration in factory process')
    ui = importlib.import_module(PACKAGE_NAME + '.unity_export_ui')
    classes = (ui.CharacterDesignerUnityExtra, ui.CharacterDesignerUnitySimpleMaterial,
               ui.CharacterDesignerUnityMaterialMatch, ui.CharacterDesignerUnityExport)
    registered, property_added = [], False
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
            registered.append(cls)
        setattr(bpy.types.Object, EXPORT_PROPERTY,
                bpy.props.PointerProperty(type=ui.CharacterDesignerUnityExport))
        property_added = True
        saved = getattr(rig, EXPORT_PROPERTY)
        stored = rig[EXPORT_PROPERTY]
        # Preserve actual saved include/simple choices. Destination/profile
        # defaults are copied, never assigned back into the saved native group.
        result = types.SimpleNamespace(
            directory='', filename=saved.filename if 'filename' in stored else '',
            asset_id=saved.asset_id if 'asset_id' in stored else '',
            extras=[types.SimpleNamespace(object=row.object, enabled=row.enabled) for row in saved.extras]
                if 'extras' in stored else [],
            simple_materials=[types.SimpleNamespace(material=row.material) for row in saved.simple_materials]
                if 'simple_materials' in stored else [])
        report['saved_export_choices'] = {
            'filename': result.filename, 'asset_id': result.asset_id,
            'extras': [{'object': row.object.name if row.object else None, 'enabled': row.enabled}
                       for row in result.extras],
            'simple_materials': [row.material.name if row.material else None for row in result.simple_materials],
            'material_match_count': len(saved.unity_material_matches) if 'unity_material_matches' in stored else 0,
            'destination_files_not_read_or_used': True,
        }
        return result
    finally:
        if property_added:
            delattr(bpy.types.Object, EXPORT_PROPERTY)
        for cls in reversed(registered):
            bpy.utils.unregister_class(cls)
        report['narrow_config_registration_removed'] = (
            bpy.types.Object.bl_rna.properties.get(EXPORT_PROPERTY) is None
            and all(getattr(bpy.types, cls.__name__, None) is None for cls in classes))
        require(report['narrow_config_registration_removed'], 'Narrow config registration cleanup failed')


def verify_output_files(exporter, stage, result, filename):
    require(result.get('ok') is True, 'Native worker did not report success')
    files = result.get('files')
    require(type(files) is list and files and len(files) == len(set(files)) and filename in files,
            'Native output file inventory is incomplete or duplicated')
    output = {}
    for relative in files:
        path = exporter._safe_file(stage, relative)
        require(path.resolve().is_relative_to(stage.resolve()), 'Export output escaped local stage')
        output[relative] = pin(path)
    fbx = stage / filename
    with fbx.open('rb') as stream:
        require(stream.read(23) == b'Kaydara FBX Binary  \x00\x1a\x00', 'Native output is not binary FBX')
    require(output[filename]['bytes'] > 32, 'Native FBX is incomplete')
    return output


def verify_sidecars(package_name, stage, specification, result, fbx_pin):
    exporter = importlib.import_module(package_name + '.unity_export')
    exporter._dress_publication({'dress_surfaces': specification['dress_surfaces']}, result)
    hair = result.get('hair_motion', {})
    expected_hair_file = Path(specification['filename']).stem + '.hair-motion.json'
    require(hair.get('active') is True and hair.get('file') == expected_hair_file
            and hair.get('simulation_baked') is False and expected_hair_file in result['files'],
            'Actual configured Hair sidecar was not exported')
    service = importlib.import_module(package_name + '.hair_motion_export')
    payload = service.verify_read(stage / expected_hair_file, fbx_path=stage / specification['filename'])
    capture = specification['hair_motion']
    require(payload['asset_id'] == specification['asset_id']
            and payload['source_uid'] == capture['registry']['source_uid']
            and len(payload['strands']) == len(capture['registry']['strands']) == 32,
            'Hair sidecar changed saved source/profile identity or strand inventory')
    correction = result.get('forearm_correction')
    correction_summary = None
    if specification['forearm']:
        require(type(correction) is dict and correction.get('file') in result['files'],
                'Captured Forearm correction sidecar was omitted')
        forearm_path = stage / correction['file']
        data = json.loads(forearm_path.read_text(encoding='utf-8'))
        require(data.get('schema') == 'cdesigner.forearm/1'
                and data.get('fbx') == specification['filename']
                and data.get('fbxSha256') == fbx_pin['sha256'], 'Forearm sidecar FBX binding differs')
        rows = data.get('meshes', [])
        require({row.get('objectName') for row in rows} == set(specification['forearm'])
                and len(rows) == len(specification['forearm']), 'Forearm sidecar mesh inventory differs')
        for row in rows:
            require(row['vertexCount'] == result['meshes'][row['objectName']]['vertices']
                    and len(row['positions']) == row['vertexCount']
                    and type(row['idUvChannel']) is int and 0 <= row['idUvChannel'] < 8
                    and 0 <= row['stencilCheckMaxError'] <= 3e-6,
                    'Forearm output correspondence proof differs')
        correction_summary = {'file': pin(forearm_path), 'meshes': [
            {key: row[key] for key in ('objectName', 'vertexCount', 'idUvChannel', 'stencilCheckMaxError')}
            for row in rows]}
    else:
        require(correction is None, 'Unexpected correction on fresh output with no captured Forearm')
    return {'hair': {'file': pin(stage / expected_hair_file), 'strands': len(payload['strands']),
                     'source_uid': payload['source_uid'], 'verified_against_actual_fbx': True},
            'forearm': correction_summary, 'dress': result.get('dress_surfaces', [])}


def verify_fbx_import(bpy, fbx, result):
    """Real Blender FBX reader, after discarding only this process's worker data."""
    require('FINISHED' in bpy.ops.wm.read_factory_settings(use_empty=True), 'Private import reset failed')
    require(not bpy.data.objects, 'Private import scene is not empty')
    require('FINISHED' in bpy.ops.preferences.addon_enable(module='io_scene_fbx'), 'FBX reader unavailable')
    require('FINISHED' in bpy.ops.import_scene.fbx(filepath=str(fbx), use_anim=False), 'FBX reader failed')
    meshes = {obj.name: obj for obj in bpy.context.scene.objects if obj.type == 'MESH'}
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
    require(set(meshes) == EXPECTED_MESHES and len(rigs) == 1,
            'Actual imported FBX mesh/armature inventory differs')
    rig = rigs[0]
    require(set(result['rigs']) == {'CoshaRig'}
            and set(rig.data.bones.keys()) == set(result['rigs']['CoshaRig']),
            'Actual imported FBX skeleton differs from native worker output')
    rows = {}
    for name, obj in meshes.items():
        expected = result['meshes'][name]
        require(len(obj.data.vertices) == expected['vertices'], 'FBX vertex count differs: ' + name)
        keys = obj.data.shape_keys
        names = [] if keys is None else [key.name for key in keys.key_blocks if key != keys.reference_key]
        require(set(names) == set(result['shape_keys'][name]), 'FBX artist Shape Keys differ: ' + name)
        armatures = [modifier.object for modifier in obj.modifiers if modifier.type == 'ARMATURE']
        require(armatures == [rig], 'FBX skin does not bind to its one imported rig: ' + name)
        rows[name] = {'vertices': len(obj.data.vertices), 'polygons': len(obj.data.polygons),
                      'shape_keys': names, 'uv_layers': list(obj.data.uv_layers.keys()),
                      'materials': [material.name if material else None for material in obj.data.materials],
                      'armature': rig.name}
    require(not bpy.data.actions, 'Model-only FBX unexpectedly imported animation')
    return {'completed': True, 'rig': rig.name, 'bones': len(rig.data.bones), 'meshes': rows,
            'limits': 'Blender FBX structural roundtrip; no Unity import, world/rest numerical equivalence or appearance acceptance.'}


def run(args, report):
    import bpy
    require(bpy.app.background and '--factory-startup' in sys.argv and '--disable-autoexec' in sys.argv
            and bpy.app.version[:2] == (5, 2) and not bpy.data.filepath,
            'Use a new --background --factory-startup --disable-autoexec Blender5.2 process')
    native = sys.argv[:sys.argv.index('--')]
    require(any(value in ('-t', '--threads') and native[index + 1] == '1'
                for index, value in enumerate(native[:-1])), 'Run this native validation with -t 1')
    report.update(pid=os.getpid(), blender=bpy.app.version_string, input=input_proof(),
                  frozen_package=package_proof(), observer=pin(SUPPORT), script=pin(__file__))
    require(pin(SUPPORT)['sha256'] == SUPPORT_SHA, 'Observer pin differs')
    run_dir = Path(args.run_dir).resolve()
    require(run_dir.parent == HERE and not run_dir.exists(), 'Use an unused direct validation child directory')
    run_dir.mkdir()
    stage = run_dir / 'out'
    stage.mkdir()
    report['run_directory'] = str(run_dir)
    sys.dont_write_bytecode = True
    private_package()
    exporter = importlib.import_module(PACKAGE_NAME + '.unity_export')
    worker = importlib.import_module(PACKAGE_NAME + '.unity_export_worker')
    forearm_service = importlib.import_module(PACKAGE_NAME + '.unity_forearm')
    observer = support_module()
    require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(ARTIST), load_ui=False), 'Pinned saved input open failed')
    require(Path(bpy.data.filepath).resolve() == ARTIST and input_proof() == report['input'], 'Another input loaded')
    require(bpy.context.mode in {'OBJECT', 'POSE'}, 'Saved input is not in an exportable mode')
    source, rig = bpy.data.objects.get('Hair'), bpy.data.objects.get('CoshaRig')
    require(source is not None and source.type == 'MESH' and rig is not None and rig.type == 'ARMATURE',
            'Pinned saved source/rig identity missing')
    require(all(name in bpy.context.scene.objects for name in EXPECTED_OBJECTS), 'Expected source objects not in active saved scene')
    before = observer._snapshot(bpy, source)
    config = read_saved_export_config(bpy, rig, report)
    # Default character_setup.settings() returns None when its Scene RNA is
    # unregistered. No fake setup or include-filter override is installed.
    require(exporter.character_setup.settings(bpy.context) is None, 'Unexpected registered Character Setup')
    collected = exporter.collect_character(bpy.context, rig, config)
    objects = collected['objects']
    require(tuple(obj.name for obj in objects) == EXPECTED_OBJECTS,
            'Actual saved include/binding choices do not collect exactly the authorized seven objects')
    importlib.import_module(PACKAGE_NAME + '.dress_export_guard').reject_model_sources(objects)
    dress = exporter._capture_dress_surfaces(objects)
    hair = exporter._capture_hair_motion(objects)
    require(hair is not None and hair['source'] == 'Hair' and hair['rig'] == 'CoshaRig'
            and len(hair['registry']['strands']) == 32, 'Saved-model Hair capture differs')
    owned_keys = exporter._owned_keys(objects)
    forearm = {obj.name: forearm_service.capture(obj) for obj in objects
               if obj.type == 'MESH' and obj.name in owned_keys}
    after_capture = observer._snapshot(bpy, source)
    report['capture_protection'] = {'before': before, 'after': after_capture,
                                    'exact': before == after_capture}
    require(before == after_capture, 'Config/capture changed saved source private data')
    # This is a new validation destination. There is intentionally no prior
    # manifest; this is begin_export's fresh-output had_forearm=False branch.
    filename = exporter._filename(config.filename, rig)
    specification = {
        'objects': [obj.name for obj in objects], 'rig': rig.name,
        'rigs': [obj.name for obj in objects if obj.type == 'ARMATURE'],
        'filename': filename, 'stage': str(stage), 'asset_id': config.asset_id or uuid.uuid4().hex,
        'unit_scale': bpy.context.scene.unit_settings.scale_length,
        'owned_keys': owned_keys, 'warnings': collected['warnings'], 'forearm': forearm,
        'hair_motion': hair, 'dress_surfaces': dress, 'had_forearm': False,
        'simple_materials': sorted({row.material.name for row in config.simple_materials
            if row.material is not None and any(slot.material == row.material
                for obj in objects if obj.type == 'MESH' for slot in obj.material_slots)}),
        'image_buffers': exporter._image_buffers(objects, run_dir),
    }
    job_path, snapshot_path = run_dir / 'job.json', run_dir / 'character_snapshot.blend'
    write_new_json(job_path, specification)
    bpy.data.libraries.write(str(snapshot_path), exporter._model_snapshot_datablocks(objects, dress),
                             path_remap='ABSOLUTE', fake_user=False, compress=True)
    after_snapshot = observer._snapshot(bpy, source)
    report['snapshot_protection'] = {'after': after_snapshot, 'exact': after_snapshot == before}
    require(after_snapshot == before, 'Image capture/snapshot write changed private saved source data')
    report.update(job=pin(job_path), snapshot=pin(snapshot_path), capture_counts={
        'objects': specification['objects'], 'hair_strands': len(hair['registry']['strands']),
        'hair_bones': sum(len(row['bones']) for row in hair['registry']['strands']),
        'dress_surfaces': len(dress), 'forearm_meshes': sorted(forearm), 'owned_keys': owned_keys,
        'simple_materials': specification['simple_materials'], 'image_buffers': len(specification['image_buffers'])})
    require(input_proof() == report['input'], 'Artist disk changed before disposable worker')
    require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(snapshot_path), load_ui=False), 'Local model snapshot reopen failed')
    require(Path(bpy.data.filepath).resolve() == snapshot_path, 'Worker did not reopen local snapshot')
    require(pin(job_path) == report['job'], 'Serialized worker job changed before execution')
    specification = json.loads(job_path.read_text(encoding='utf-8'))
    report['worker_called_directly_no_nested_process'] = True
    result = worker.export_job(specification)
    write_new_json(stage / 'result.json', result)
    report['worker_result'] = pin(stage / 'result.json')
    require(set(result.get('objects', [])) == set(EXPECTED_OBJECTS), 'Worker output object inventory differs')
    output_pins = verify_output_files(exporter, stage, result, filename)
    report['sidecars'] = verify_sidecars(PACKAGE_NAME, stage, specification, result, output_pins[filename])
    report['files'] = output_pins
    report['warnings'], report['notices'] = exporter.report_messages(result)
    # Inspect actual FBX bytes through the real importer, not a generated or
    # hand-constructed stand-in. All worker source data remain disposable.
    report['fbx_roundtrip'] = verify_fbx_import(bpy, stage / filename, result)
    require(input_proof() == report['input'] and package_proof() == report['frozen_package'],
            'Protected artist/package disk changed')
    require(pin(job_path) == report['job'] and pin(snapshot_path) == report['snapshot'],
            'Actual worker inputs changed during validation')
    require(pin(SUPPORT) == report['observer'] and pin(__file__) == report['script'],
            'Validator/observer source changed during validation')
    require(verify_output_files(exporter, stage, result, filename) == output_pins, 'Export bytes changed during FBX verification')
    report['artist_disk_unchanged'] = report['frozen_package_unchanged'] = True
    report['completed'] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    report_path = Path(args.report).resolve()
    require(report_path.parent == HERE and report_path.suffix.lower() == '.json'
            and not report_path.exists(), 'Use an unused direct validation JSON report')
    report = {'schema': 'x.actual-saved-model-export/2', 'completed': False,
              'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'artist_saved': False, 'unity_accessed': False, 'gui_used': False,
              'addon_wide_registration_used': False, 'coordinator_publication_used': False,
              'scope': 'Pinned saved X only; current unsaved window contents and live runtime were not observed.',
              'limits': ['Fresh validation destination; no production prior manifest, material match publication or stale-file handling.',
                         'Native worker static Rest FBX plus Hair/Forearm sidecars; no animation or physics simulation bake.',
                         'Blender structural FBX roundtrip does not prove Unity import/Avatar/runtime deformation/material appearance.',
                         'Private process source data are intentionally changed by the real worker and then discarded for FBX import.']}
    with report_path.open('x', encoding='utf-8') as stream:
        try:
            run(args, report)
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            for label, callback in (('artist_disk_final', input_proof), ('frozen_package_final', package_proof)):
                try:
                    report[label] = callback()
                except BaseException:
                    report[label + '_error'] = traceback.format_exc()
                    report['completed'] = False
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    require(report['completed'] is True, 'Final protected disk verification failed; inspect the preserved report')
    print('X_ACTUAL_SAVED_MODEL_EXPORT_VALIDATED', str(report_path), flush=True)


if __name__ == '__main__':
    main()
