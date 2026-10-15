"""Root-installed one-shot SaveCopy; no prepare/refresh/seek/solver or launch.

Normal save handlers remain installed. This proves only the stated V9/Base/
context/disk scopes and supplies a NEW input for later full-clip validation.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
SUPPORT = HERE/'native_validation_support_v9.py'
SUPPORT_SHA = '55f4b4b75a2ff5991f250d845fbbb295e7ef153874fb03dbeb7f169b5c048ed5'
if hashlib.sha256(SUPPORT.read_bytes()).hexdigest() != SUPPORT_SHA:
    raise RuntimeError('Reviewed readonly V9 support changed')
sys.path.insert(0, str(HERE))
import native_validation_support_v9 as witness
if Path(witness.__file__).resolve() != SUPPORT:
    raise RuntimeError('Another V9 helper imported')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def idle(bpy):
    runtime = sys.modules.get('character_designer.forearm_twist')
    require(runtime is not None and runtime._RUNTIME_REGISTERED and runtime._SCENE_STATE_ACTIVE
        and not runtime._ERRORS and not any(getattr(runtime, name) for name in
        ('_BUSY', '_INITIALIZE_PENDING', '_SCENE_CLEANUP_PENDING'))
        and not bpy.app.timers.is_registered(runtime._complete_runtime_lifecycle), 'Normal runtime must be settled')
    require(bpy.context.mode == 'OBJECT' and not any(obj.mode != 'OBJECT' for obj in bpy.data.objects)
        and not any(window.screen and window.screen.is_animation_playing for window in bpy.context.window_manager.windows)
        and not bpy.app.is_job_running('RENDER'), 'Idle Object mode, stopped playback and no render required')
    for name, fields in (('forearm_twist', ('_SESSION',)), ('delta_symmetry', ('_RUNTIME',)),
                         ('hair_wiggle_adapter', ('_SESSION',)), ('skirt_wiggle', ('_SESSIONS', '_SAVE_RESUME'))):
        module = sys.modules.get('character_designer.'+name)
        require(module is None or all((getattr(module, field) is None if field in {'_SESSION', '_RUNTIME'}
            else not getattr(module, field)) for field in fields), 'Active save lifecycle: '+name)
    require(not any(runtime.PREVIEW_KEY in obj for obj in bpy.data.objects if obj.type == 'MESH'), 'Calibration rollback marker present')
    require(not any(image.is_dirty for image in bpy.data.images), 'Dirty images could be saved by normal SaveCopy')
    return runtime


def state(bpy):
    context = bpy.context
    layers = []
    for scene in bpy.data.scenes:
        layers.append({'scene': scene.name_full, 'frame': [scene.frame_current, float(scene.frame_subframe)],
            'layers': [{'name': layer.name, 'active': int(layer.objects.active.as_pointer()) if layer.objects.active else None,
                'objects': sorted((int(obj.as_pointer()), obj.session_uid, bool(obj.hide_get(view_layer=layer)),
                    bool(obj.select_get(view_layer=layer)), bool(obj.hide_viewport), bool(obj.hide_render),
                    bool(obj.hide_select)) for obj in layer.objects)} for layer in scene.view_layers]})
    collections = {int(item.as_pointer()): item for item in bpy.data.collections}
    collections.update((int(scene.collection.as_pointer()), scene.collection) for scene in bpy.data.scenes)
    return {'filepath': bpy.data.filepath, 'dirty': bool(bpy.data.is_dirty), 'mode': context.mode,
        'window': int(context.window.as_pointer()), 'screen': int(context.screen.as_pointer()),
        'area': int(context.area.as_pointer()), 'area_type': context.area.type,
        'scene': int(context.scene.as_pointer()), 'view_layer': int(context.view_layer.as_pointer()),
        'active': int(context.active_object.as_pointer()) if context.active_object else None,
        'layers': layers, 'collections': sorted((pointer, bool(item.hide_select), bool(item.hide_viewport),
            bool(item.hide_render)) for pointer, item in collections.items()),
        'ids': sorted(witness.native_id_pointers()), 'handlers': witness.handler_snapshot()}


def run(config):
    import bpy
    fields = {'expected_pid', 'artist', 'artist_sha256', 'copy', 'report'}
    require(isinstance(config, dict) and set(config) == fields and type(config['expected_pid']) is int
        and config['expected_pid'] == os.getpid(), 'Fresh Root PID and exact SaveCopy CONFIG required')
    require(not bpy.app.background and bpy.app.version[:2] == (5, 2)
        and bpy.context.window and bpy.context.screen and bpy.context.area, 'Observed Blender5.2 GUI context required')
    artist, output, report_path = (Path(config[key]).resolve() for key in ('artist', 'copy', 'report'))
    require(artist == (HERE.parents[2]/'X.blend').resolve() and Path(bpy.data.filepath).resolve() == artist,
        'Fresh observed canonical artist must still be open')
    artist_pin = witness.pin(artist)
    require(artist_pin['sha256'] == config['artist_sha256'], 'Fresh artist disk pin differs')
    require(output.suffix.lower() == '.blend' and output.parent.parent == HERE and not output.parent.exists()
        and report_path.parent == HERE and report_path.suffix == '.json' and not report_path.exists(),
        'Unused unique child directory for copy and unused direct JSON report required')
    report = {'schema': 'x.current-model-save-copy/1', 'completed': False, 'pid': os.getpid(),
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'artist_before': artist_pin, 'script': witness.pin(__file__), 'no_prepare_refresh_seek_solver': True,
        'normal_save_handlers_preserved': False,
        'limits': 'V9 declared source properties/Rest/pose/foreign payload plus Base/context/disk proof only; not full source geometry, all RAM, current-cache equivalence or full-clip acceptance.'}
    with report_path.open('x', encoding='utf8') as stream:
        try:
            runtime = idle(bpy)
            report['loaded_metadata'] = {'blender': bpy.app.version_string,
                'character_designer_version': getattr(sys.modules.get('character_designer'), 'bl_info', {}).get('version'),
                'runtime_file': runtime.__file__, 'scope': 'Loaded metadata and package disk pins only; no live-code attestation.'}
            require(config['expected_pid'] == os.getpid(), 'Artist PID changed')
            report['dependencies'] = witness.witness_dependency_pins()
            package = Path(runtime.__file__).resolve().parent
            report['package_disk_files'] = witness.package_pins(package)
            before = state(bpy)
            report['source_identity'] = {'scene': bpy.context.scene.name_full,
                'frame': [bpy.context.scene.frame_current, float(bpy.context.scene.frame_subframe)],
                'view_layer': bpy.context.view_layer.name, 'dirty': before['dirty'], 'filepath': before['filepath']}
            props = witness.source_property_witness(bpy.context.scene)
            require(state(bpy) == before, 'Readonly pre-save witness changed protected context/Base state')
            report['before_state_sha256'], report['before_properties_sha256'] = witness.object_hash(before), props['sha256']
            output.parent.mkdir()  # exclusive directory owns the new .blend namespace
            report['copy_attempted'] = True
            try:
                result = bpy.ops.wm.save_as_mainfile(filepath=str(output), copy=True, relative_remap=True,
                    check_existing=True, show_save_modified_images_dialog=False)
                report['operator_result'] = sorted(result)
            finally:
                try:
                    report['copy'] = witness.pin(output) if output.is_file() else None
                    idle(bpy)
                    report['protected_context_base_exact'] = state(bpy) == before
                    report['source_properties_exact'] = witness.source_property_witness(bpy.context.scene)['sha256'] == props['sha256']
                    report['protected_context_base_after_witness_exact'] = state(bpy) == before
                    report['artist_disk_exact'] = witness.pin(artist) == artist_pin
                    report['package_disk_exact'] = witness.package_pins(package) == report['package_disk_files']
                    report['dependencies_exact'] = witness.witness_dependency_pins() == report['dependencies']
                    report['script_exact'] = witness.pin(__file__) == report['script']
                    report['normal_save_handlers_preserved'] = witness.handler_snapshot() == before['handlers']
                except BaseException:
                    report['after_proof_error'] = traceback.format_exc()
            require('after_proof_error' not in report and result == {'FINISHED'} and report['copy'] is not None
                and report['copy']['bytes'] > 0, 'Native SaveCopy or post-save proof failed')
            require(all(report[key] is True for key in ('protected_context_base_exact', 'source_properties_exact',
                'protected_context_base_after_witness_exact', 'artist_disk_exact', 'package_disk_exact',
                'dependencies_exact', 'script_exact', 'normal_save_handlers_preserved')), 'SaveCopy protection proof failed')
            report['completed'] = True
        except BaseException:
            report['error'] = traceback.format_exc()
            raise
        finally:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    return report
