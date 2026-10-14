"""Prepared recovery only; no automatic entry, SDK, deploy, save or file reload.

An exact old-root import shim exists only while the retained .36 functions
perform cleanup. It is never reported as an enabled runtime. The final gate
must be called after Blender naturally services .38's registration timer.
"""
import hashlib
import importlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback
import types

ROUND = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012')
HISTORY = ROUND.parent.parent / 'direct_original_rig_return_20261011'
ARTIST = Path(r'D:/Blender/Projects/Character/X/X.blend')
OLD_ROOT = ROUND / 'package_c1e59f7f/source/character_designer'
OLD_MANIFEST = ROUND / 'package_c1e59f7f/python_projection.json'
OLD_MANIFEST_SHA = 'e413d8e6d66bb5a0dd676fc24b0152d1599436464981979fd12d38085daca7e4'
CANDIDATE_MANIFEST = ROUND / 'package_e51290d9/python_projection.json'
CANDIDATE_MANIFEST_SHA = '0d0678388250fca04ce53164628c9460d6d237a5664d6e14c5f79ea8b337e209'
GRAPH = ROUND / 'original_runtime_registration_graph_01/report.json'
GRAPH_SHA = '49cccb13f74253f3e68642bd7b78268a2c866a10d3027c53b19ef94682c3a9bb'
REFRESH_SHA = 'f9c28504ce0453bfe4232dc0231fc484f18db8793dfd34302f5ec3a6edf38cc7'
LIGHT_SHA = '6df88f6e605a2a4e96eb1d3f261ed456dbe150c3e54a0d1e68f0f5aa962ff971'
VERIFIER_SHA = 'f220d2f398e16a190715fd28a9c161207bcbeaf05946ff9d516038408ba2bf32'
ORACLE_SHA = '260b2bc581df220ea861d18f6b369d104561d5a3d119e21e5e52e9e230219a5d'
EXPECTED38 = {'__init__.py': '0132dca91c92b16763c678ec326afef8c453b1e159f1e3edcdf0ad0a9de79a52',
    'unity_animation_rigging.py': '0ca35e2e44bea9ed1007bf9024cfadb50b0e6a8ada2a702a84de43f30c484cd9',
    'skirt_wiggle.py': '81b0f0c42cfb8c4d3854c81e7da4a351d47e42b18929467d3e4864982bb13c25',
    'control_weight_paint.py': 'efbaf8227830b48c5744f1c024d0240c147cdc612612a72810eb60b2c01748bc'}
STATE = None

def require(value, message):
    if not value:
        raise RuntimeError(message)

def exact_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def pin(path, expected):
    path = Path(path).resolve()
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    require(digest == expected, 'Source/evidence changed: ' + str(path))
    return {'path': str(path), 'sha256': digest, 'bytes': len(data)}

def document(row):
    pin(row['path'], row['sha256'])
    return json.loads(Path(row['path']).read_text(encoding='utf-8'))

def cd_name(name):
    return isinstance(name, str) and (name == 'character_designer' or name.startswith('character_designer.'))

def load(path, expected, name):
    checked = pin(path, expected)
    spec = importlib.util.spec_from_file_location(name, checked['path'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def write_report():
    state = STATE
    path = state['output'] / 'recovery_report.json'
    path.write_text(json.dumps(state['report'], ensure_ascii=False, indent=2), encoding='utf-8')

def checkpoint(name, value):
    path = STATE['output'] / (name + '.json')
    require(not path.exists(), 'Do not replace a preservation snapshot.')
    raw = json.dumps(STATE['verifier'].public(value), ensure_ascii=False, indent=2).encode('utf-8')
    path.write_bytes(raw)
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

class FrozenOldImports(importlib.abc.MetaPathFinder):
    """Missing cleanup dependencies may only come from the sealed .36 tree."""
    def __init__(self, manifest):
        self.files = manifest['files']
        self.admitted = []
        self.sealed = False
    def find_spec(self, fullname, path=None, target=None):
        if not cd_name(fullname):
            return None
        require(not self.sealed, 'An unsealed late cleanup import was refused: ' + fullname)
        require(fullname != 'character_designer', 'The temporary root must already be bound.')
        relative = fullname[len('character_designer.'):].replace('.', '/') + '.py'
        require(relative in self.files, 'Unknown cleanup import refused: ' + fullname)
        checked = pin(OLD_ROOT / relative, self.files[relative])
        self.admitted.append({'module': fullname, **checked})
        return importlib.util.spec_from_file_location(fullname, checked['path'])

def clear_cd_modules():
    for name in tuple(sys.modules):
        if cd_name(name):
            del sys.modules[name]

def corrected_raw_snapshot(bpy, observed):
    # The earlier diagnostic incorrectly passed an Object ID pointer to rna_group.
    def value(owner, name):
        actual = getattr(owner, name)
        return observed['rna_group'](actual) if isinstance(actual, bpy.types.PropertyGroup) else observed['plain'](actual)
    return {'scenes': {scene.name: {p.identifier: value(scene, p.identifier)
                for p in bpy.types.Scene.bl_rna.properties if p.identifier.startswith('character_designer')}
                for scene in bpy.data.scenes},
            'window_managers': {str(wm.as_pointer()): {p.identifier: value(wm, p.identifier)
                for p in bpy.types.WindowManager.bl_rna.properties if p.identifier.startswith('character_designer')}
                for wm in bpy.data.window_managers},
            'Scene_custom_properties': {str(scene.as_pointer()): observed['plain'](dict(scene.items())) for scene in bpy.data.scenes},
            'WM_custom_properties': {str(wm.as_pointer()): observed['plain'](dict(wm.items())) for wm in bpy.data.window_managers},
            'object_custom_properties': {str(obj.as_pointer()): observed['plain'](dict(obj.items())) for obj in bpy.data.objects},
            'Action_custom_properties': {str(action.as_pointer()): observed['plain'](dict(action.items())) for action in bpy.data.actions}}

def owned_callbacks(bpy):
    return {name: [callback for callback in getattr(bpy.app.handlers, name)
                   if cd_name(getattr(callback, '__module__', None))]
            for name in dir(bpy.app.handlers) if isinstance(getattr(bpy.app.handlers, name), list)}

def owned_functions(namespaces, observed):
    result = {}
    for namespace in namespaces:
        for value in tuple(namespace.values()):
            values = tuple(vars(value).values()) if isinstance(value, type) else (value,)
            for item in values:
                fn = observed['function'](item)
                if fn is not None and cd_name(fn.__globals__.get('__name__')):
                    result[id(fn)] = fn
    return result

def native_identities(ctx, rig, light):
    return {'scene': light.reference(ctx.scene), 'rig': light.reference(rig),
        'rig_data': light.reference(rig.data), 'window_manager': light.reference(ctx.window_manager),
        'window': {'native_pointer': int(ctx.window.as_pointer())},
        'view_layer': {'name': ctx.view_layer.name, 'native_pointer': int(ctx.view_layer.as_pointer())}}

def original_pointer_types(bpy, original, graph):
    rows = []
    expected = [(bpy.types.WindowManager, name, cls) for name, cls in original['_WINDOW_MANAGER_POINTER_TYPES']] + [
        (bpy.types.Scene, 'character_designer_setup', original['CharacterDesignerSetup']),
        (bpy.types.Scene, 'character_designer_animation_worklist', original['CharacterDesignerAnimationWorklistState']),
        (bpy.types.Object, 'character_designer_unity_export', original['CharacterDesignerUnityExport'])]
    for owner, name, cls in expected:
        prior = next(row for row in graph['pointer_types'] if row['owner'] == owner.__name__ and row['name'] == name)
        prop = owner.bl_rna.properties.get(name)
        require(id(cls) == prior['expected_class_id'] and prop is not None and prop.type == 'POINTER'
            and prop.fixed_type == cls.bl_rna, 'Original registered PointerProperty type changed: ' + name)
        rows.append({'owner': owner.__name__, 'name': name, 'expected_class_id': id(cls), 'exact_fixed_type': True})
    require(len(rows) == len(graph['pointer_types']) == 14, 'Unexpected original fixed-type domain.')
    return rows

def run(*, config_path, config_sha256, script_sha256):
    """Root supplies a sealed concrete config only after .38 standard-enable PASS."""
    global STATE
    require(STATE is None, 'This recovery helper is single-use.')
    require('PENDING' not in CANDIDATE_MANIFEST_SHA and all('PENDING' not in value for value in EXPECTED38.values()),
            'This source draft has not been bound to a frozen .38 candidate.')
    import bpy
    config = document(pin(config_path, config_sha256))
    require('PENDING' not in json.dumps(config), 'Bind concrete recovery evidence first.')
    require(config['external_authorization_confirmed'] is True and config['authorization_token'], 'Fresh root authorization required.')
    require(os.getpid() == config['expected_pid'] == 14500 and not bpy.app.background,
            'Use only the authenticated still-open original process.')
    require(Path(bpy.data.filepath).resolve() == ARTIST.resolve(), 'The original artist file changed.')
    inputs = {'source': pin(__file__, script_sha256), 'config': pin(config_path, config_sha256),
        'graph': pin(GRAPH, GRAPH_SHA), 'old_manifest': pin(OLD_MANIFEST, OLD_MANIFEST_SHA)}
    for key in ('package_manifest', 'standard_probe', 'standard_probe_release', 'backup', 'backup_receipt', 'failed_refresh_receipt'):
        inputs[key] = pin(config[key]['path'], config[key]['sha256'])
    require(inputs['package_manifest'] == pin(CANDIDATE_MANIFEST, CANDIDATE_MANIFEST_SHA), 'Use the actual R20 frozen manifest.')
    inputs['protected_artist'] = pin(ARTIST, config['protected_artist_sha256'])
    candidate, previous = document(inputs['package_manifest']), document(inputs['old_manifest'])
    require(candidate['version'] == '0.77.38' and len(candidate['files']) == 190
        and set(candidate['files']) == set(previous['files']), 'Unexpected candidate package.')
    changed = {name for name in candidate['files'] if candidate['files'][name] != previous['files'][name]}
    require(changed == set(EXPECTED38) and all(candidate['files'][name] == digest for name, digest in EXPECTED38.items()), 'The .38 source delta exceeds registration-only scope.')
    installed = Path(config['installed_root']).resolve()
    for name, digest in candidate['files'].items():
        pin(installed / name, digest)
    probe, release = document(inputs['standard_probe']), document(inputs['standard_probe_release'])
    required = ('completed', 'passed', 'standard_enable_returned_module_before_deferred_admission',
        'actual_deferred_registration_admission_once', 'standard_disable_cleanup_verified',
        'immediate_disable_cancels_without_late_admission', 'controlled_failure_preserves_original_error_and_cleans_RNA',
        'controlled_failure_leaves_no_late_callback', 'input_files_unchanged')
    require(probe['schema'] == 'x.validation.standard-registration-lifecycle/1' and all(probe.get(key) is True for key in required), 'No actual standard-registration PASS.')
    require(probe['source_inputs']['package_manifest']['sha256'] == inputs['package_manifest']['sha256'], 'Standard probe used another package.')
    # Root binds the concrete retained-handle receipt shape, not a guessed exit flag.
    require(all(release.get(key) == value for key, value in config['release_required_fields'].items())
        and config['release_required_fields'], 'Standard probe END is not admitted.')
    graph = document(inputs['graph'])
    holder = sys.modules.get('x_original_registration_recovery_07736')
    require(holder is not None and isinstance(holder.observed_namespace, dict), 'Retained original graph is missing.')
    observed = holder.observed_namespace
    original = observed['root_globals']
    require(id(original) == graph['root_globals_id'] and tuple(original['bl_info']['version']) == (0, 77, 36)
        and bpy.types.CHARACTERDESIGNER_PT_main.draw.__globals__ is original, 'Registered original root identity changed.')
    objects = {}
    for namespace in observed['actual_spaces'].values():
        for value in tuple(namespace.values()):
            if isinstance(value, types.ModuleType) and cd_name(value.__name__):
                require(value.__name__ not in objects or objects[value.__name__] is value, 'Conflicting original module objects.')
                objects[value.__name__] = value
    require('character_designer' not in objects and len(objects) == 99, 'Do not synthesize or confuse the original root.')
    for row in graph['modules']:
        require(row['name'] in objects and id(objects[row['name']]) == row['id']
            and id(vars(objects[row['name']])) == row['globals_id'], 'Original module identity drift.')
    for row in graph['RNA_classes']:
        cls = next(c for c in original['CLASSES'] if c.__name__ == row['name'])
        require(id(cls) == row['python_id'] and original['_registered_rna_class'](cls) is cls, 'Registered original class changed.')
    original['_validate_registration_integrity']()
    pointer_types = original_pointer_types(bpy, original, graph)
    require(all(not rows or all(id(callback.__globals__) in observed['actual_spaces'] for callback in rows)
                for rows in owned_callbacks(bpy).values()), 'A foreign CD callback appeared.')
    graph_functions = owned_functions(observed['actual_spaces'].values(), observed)
    require(not any(bpy.app.timers.is_registered(fn) for fn in graph_functions.values()),
            'A known old runtime timer became active after the graph diagnostic.')
    output = Path(config['output_root']).resolve()
    require(not output.exists() and output.is_relative_to(ROUND), 'Use a new owned recovery output directory.')
    output.mkdir()
    report = {'schema': 'x.recovery.original-registration/1', 'completed': False, 'phase': 'admitted_no_cleanup',
        'inputs': inputs, 'pid': os.getpid(), 'external_process_filetime': config['external_process_filetime'],
        'scope': 'Preserve freshly measured post-failure live state; no claim of unknown pre-F9C2 WM/Undo preservation.',
        'original_root_module_absent': True, 'temporary_root_is_cleanup_only': True,
        'file_reload_or_save_performed': False, 'registered_candidate_version': None,
        'old_registered_pointer_types': pointer_types, 'old_registered_pointer_types_exact_count': len(pointer_types),
        'unknown_pre_failure_WM_or_Undo_preservation_claimed': False,
        'standard_enable_errors': []}
    STATE = {'output': output, 'report': report, 'original_globals': original, 'original_modules': objects,
        'observed': observed, 'candidate': candidate, 'installed': installed, 'config': config,
        'entry_sys_path': list(sys.path), 'entry_cd_modules': {name: module for name, module in sys.modules.items() if cd_name(name)}}
    refresh = load(ROUND / 'refresh_original_artist_runtime_07736.py', REFRESH_SHA, 'original_recovery_refresh_contract')
    light = load(ROUND / 'snapshot_latest_original_artist.py', LIGHT_SHA, 'original_recovery_light')
    oracle = load(HISTORY / 'validation_preservation.py', ORACLE_SHA, 'original_recovery_oracle')
    saved_oracle = sys.modules.get('validation_preservation')
    sys.modules['validation_preservation'] = oracle
    try:
        verifier = load(HISTORY / 'verify_addon_refresh_isolated.py', VERIFIER_SHA, 'original_recovery_verifier')
    finally:
        if saved_oracle is None:
            sys.modules.pop('validation_preservation', None)
        else:
            sys.modules['validation_preservation'] = saved_oracle
    STATE.update(refresh=refresh, light=light, verifier=verifier)
    shim = types.ModuleType('character_designer')
    shim.__dict__.update(original)
    shim.__path__ = [str(OLD_ROOT)]
    shim.__addon_enabled__ = False
    finder = FrozenOldImports(previous)
    cleanup_started = False
    try:
        clear_cd_modules()
        sys.modules.update(objects)
        sys.modules['character_designer'] = shim
        sys.meta_path.insert(0, finder)
        # Complete the known late-import dependencies before the protection seal.
        for name in ('unity_export', 'animation_worklist_collection'):
            importlib.import_module('character_designer.' + name)
        admitted_modules = {name: module for name, module in sys.modules.items() if cd_name(name)}
        admitted_spaces = {id(vars(module)): vars(module) for module in admitted_modules.values()}
        admitted_spaces.update(observed['actual_spaces'])
        owned_classes = {id(value): value for namespace in admitted_spaces.values()
            for value in namespace.values() if isinstance(value, type)
            and getattr(value, '__module__', None) == namespace.get('__name__')
            and hasattr(value, 'is_registered')}
        graph_functions.update(owned_functions(admitted_spaces.values(), observed))
        require(not any(bpy.app.timers.is_registered(fn) for fn in graph_functions.values()),
                'A known owned timer is active after cleanup dependency imports.')
        require(all(not rows or all(id(callback.__globals__) in admitted_spaces for callback in rows)
                    for rows in owned_callbacks(bpy).values()), 'A foreign callback appeared during cleanup admission.')
        finder.sealed = True
        with light.original_context(bpy, 'Scene', 'CoshaRig') as (ctx, rig):
            refresh.idle(shim, ctx, bpy)
            paint = objects['character_designer.control_weight_paint']
            require(paint.active(ctx) is None and paint.SESSION not in ctx.scene,
                    'Finish the active weight-paint workspace before original runtime cleanup.')
            skirt = objects['character_designer.skirt_wiggle']
            require(not skirt._REGISTERED and not skirt._SESSIONS, 'Unexpected started Dress adapter.')
            require(not any(skirt.STATE_KEY in obj for obj in bpy.data.objects), 'Saved Dress Automatic/Manual metadata requires a separate nonmutating cleanup review.')
            require(not objects['character_designer.skirt']._ACTIVE_BAKES, 'An actual Dress bake is active.')
            require(not objects['character_designer.unity_export_ui']._MODAL_EXPORTS
                and not objects['character_designer.animation_worklist_ui']._DRAGS, 'A modal export/worklist operation is active.')
            before = refresh.capture(ctx, rig, bpy, objects['character_designer.unity_animation'], shim,
                light, verifier, objects['character_designer.animation_worklist_fingerprint'])
            raw_before = corrected_raw_snapshot(bpy, observed)
            identities = native_identities(ctx, rig, light)
            STATE.update(before=before, raw_before=raw_before, dirty_before=bool(bpy.data.is_dirty), identities_before=identities)
            report['fresh_full_before'] = checkpoint('fresh_full_before', before)
            report['fresh_raw_Scene_WM_Object_Action_before'] = checkpoint('fresh_raw_before', raw_before)
            report['frozen36_cleanup_dependencies'] = finder.admitted
            report.update(dirty_before=STATE['dirty_before'], identities_before=identities,
                before_light_signature=light.digest(before['light']),
                known_owned_timers_idle_before_cleanup=True, known_owned_function_count=len(graph_functions),
                owned_RNA_class_count=len(owned_classes),
                registered_owned_RNA_class_count=sum(bool(cls.is_registered) for cls in owned_classes.values()),
                weight_paint_inactive_before_cleanup=True,
                cleanup_import_set_sealed=True, sys_path_before=STATE['entry_sys_path'])
            report['phase'] = 'sealed_before_owned_cleanup'
            write_report()
            cleanup_started = True
            original['unregister']()
            require(not any(getattr(cls, 'is_registered', False) for cls in original['CLASSES']), 'Original RNA classes remain registered.')
            report['owned_RNA_classes_remaining_after_cleanup'] = sorted(
                cls.__module__ + '.' + cls.__name__ for cls in owned_classes.values() if cls.is_registered)
            require(not report['owned_RNA_classes_remaining_after_cleanup'], 'Owned submodule RNA classes remain registered.')
            require(not any(owned_callbacks(bpy).values()), 'Owned CD callbacks remain after cleanup.')
            require(not any(bpy.app.timers.is_registered(fn) for fn in graph_functions.values()), 'An original runtime timer remains after cleanup.')
            require(not any(prop.identifier == 'character_designer' or prop.identifier.startswith('character_designer_')
                for owner in (bpy.types.Scene, bpy.types.WindowManager, bpy.types.Object)
                for prop in owner.bl_rna.properties), 'Owned RNA properties remain after cleanup.')
            report['exact_original36_cleanup_completed'] = True
    except Exception as error:
        report.update(error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc(),
            phase='cleanup_failed' if cleanup_started else 'precleanup_refused')
        raise
    finally:
        if finder in sys.meta_path:
            sys.meta_path.remove(finder)
        clear_cd_modules()
        # Before cleanup no registration changed: restore the observed registry exactly.
        if not cleanup_started:
            sys.modules.update(STATE['entry_cd_modules'])
            sys.path[:] = STATE['entry_sys_path']
        report['temporary_root_removed'] = sys.modules.get('character_designer') is not shim
        write_report()
    try:
        # Use Blender's real standard enable; never call .38 register/reacquire ourselves.
        sys.path[:] = [str(installed.parent)] + [p for p in STATE['entry_sys_path'] if Path(p or '.').resolve() != installed.parent]
        importlib.invalidate_caches()
        import addon_utils
        def enable_error(error):
            report['standard_enable_errors'].append({'type': type(error).__name__, 'message': str(error),
                'traceback': ''.join(traceback.format_exception(type(error), error, error.__traceback__))})
        enabled = addon_utils.enable('character_designer', default_set=False, persistent=False, handle_error=enable_error)
        require(not report['standard_enable_errors'], 'Standard .38 enable reported an exception; see its retained traceback.')
        require(enabled is not None and enabled is sys.modules.get('character_designer')
            and tuple(enabled.bl_info['version']) == (0, 77, 38) and enabled.__addon_enabled__, 'Standard .38 enable failed.')
        enabled._validate_registration_integrity()
        refresh.loaded_sources(enabled, installed, candidate)
        native = sys.modules['character_designer.unity_animation_rigging']
        require(native._REACQUIRE_TIMER is not None and bpy.app.timers.is_registered(native._REACQUIRE_TIMER), 'Standard enable did not queue its genuine restricted registration admission.')
        STATE.update(candidate_module=enabled, pending_timer=native._REACQUIRE_TIMER,
            pending_generation=native._REACQUIRE_GENERATION)
        report.update(phase='candidate_enabled_waiting_for_natural_timer', registered_candidate_version=[0, 77, 38],
            standard_enable_returned=True, manual_reacquire_called=False,
            sys_path_policy='Retain installed package parent first; preserve all other entry paths and ordering.',
            sys_path_after=list(sys.path))
        write_report()
        return {'completed': False, 'queued': True, 'report': str(output / 'recovery_report.json'),
                'next': 'Return to the event loop, then call verify_after_event_loop() in this same helper module.'}
    except Exception as error:
        report.update(error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc(), phase='candidate_enable_failed')
        write_report()
        raise

def verify_after_event_loop():
    """A separate root call; does not manually run or retry the product callback."""
    import bpy
    state = STATE
    require(state is not None and state['report']['phase'] == 'candidate_enabled_waiting_for_natural_timer', 'No pending authenticated recovery.')
    report = state['report']
    native = sys.modules['character_designer.unity_animation_rigging']
    try:
        if native._REACQUIRE_TIMER is not None or native._REACQUIRE_PENDING:
            require(native._REACQUIRE_TIMER is state['pending_timer']
                and native._REACQUIRE_GENERATION == state['pending_generation']
                and bpy.app.timers.is_registered(state['pending_timer'])
                and not native._REACQUIRE_PENDING and not native._HANDLER_ERRORS,
                'The queued registration lifecycle changed before its natural admission.')
            return {'completed': False, 'queued': True, 'pending_registered': True}
        require(native._REACQUIRE_GENERATION == state['pending_generation'] + 1
            and not bpy.app.timers.is_registered(state['pending_timer']) and not native._HANDLER_ERRORS,
            'The real registration timer did not complete exactly once without errors.')
        refresh, light, verifier = state['refresh'], state['light'], state['verifier']
        package = state['candidate_module']
        require(sys.modules.get('character_designer') is package, 'The candidate root changed.')
        with light.original_context(bpy, 'Scene', 'CoshaRig') as (ctx, rig):
            refresh.project_old(state['before']['scenes'], verifier.scene_capture(), 'Scenes', [], scene=True)
            restored = []
            for group, fields in state['before']['wm'].items():
                verifier.restore_only_changed_wm(getattr(ctx.window_manager, group), fields, group, restored)
            after = refresh.capture(ctx, rig, bpy, sys.modules['character_designer.unity_animation'], package,
                light, verifier, sys.modules['character_designer.animation_worklist_fingerprint'])
            raw_after = corrected_raw_snapshot(bpy, state['observed'])
            identities = native_identities(ctx, rig, light)
            report['fresh_full_after'] = checkpoint('fresh_full_after', after)
            report['fresh_raw_Scene_WM_Object_Action_after'] = checkpoint('fresh_raw_after', raw_after)
            refresh.check_capture(state['before'], after)
            report.update(dirty_after=bool(bpy.data.is_dirty), identities_after=identities,
                after_light_signature=light.digest(after['light']))
            require(exact_json(raw_after) == exact_json(state['raw_before']), 'The fresh raw Scene/WM/Object/Action values changed.')
            require(bool(bpy.data.is_dirty) == state['dirty_before'], 'The live dirty state changed.')
            require(exact_json(identities) == exact_json(state['identities_before']), 'A protected live native identity changed.')
            package._validate_registration_integrity()
            refresh.loaded_sources(package, state['installed'], state['candidate'])
            for row in report['inputs'].values():
                pin(row['path'], row['sha256'])
            report.update(completed=True, phase='completed_postfailure_live_state_preserved',
                natural_registration_timer_completed_once=True, restored_only_changed_WM_fields=restored,
                fresh_full_postfailure_preservation_verified=True, fresh_raw_values_exact=True,
                original_disk_unchanged=True, native_identities_exact=True,
                raw_comparison='Canonical JSON with exact types and float_hex signed-zero preservation.',
                unknown_pre_failure_WM_or_Undo_preservation_claimed=False)
    except Exception as error:
        report.update(completed=False, phase='candidate_verification_failed', error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
    write_report()
    return {'completed': report['completed'], 'error': report.get('error'), 'report': str(state['output'] / 'recovery_report.json')}
