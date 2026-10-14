"""Source-only continuation of the exact 3636 partial cleanup, with its baseline.

No automatic entry. Never reload/save the artist or replace its before snapshot.
The final verification is the retained, pinned predecessor's unchanged function.
"""
import copy
import importlib
import json
import os
from pathlib import Path
import sys
import traceback
import types

ROUND = Path(r'D:/Blender/Projects/Character/X/validation/composition_20261011/fresh_rigging_round_20261012')
PREDECESSOR_MODULE = 'x_original_runtime_recovery_07738_02'
PREDECESSOR = ROUND / 'recover_original_registration_07738b.py'
PREDECESSOR_SHA = '3636e8b0f15bcf6e1df5a3b511adfd8684db265f58610b89a4a7666daad339bb'
FAILURE = ROUND / 'original_artist_recovery_07738_02/recovery_report.json'
FAILURE_SHA = '24e5b2e6ee8909930cd01e311f925ee099611d3c547574eb8e54e280fafb3312'
BEFORE_SHA = 'ff34b835cf347f6dd55308c9b22d682f54139d04b4d914f546ce58329ea2b599'
RAW_BEFORE_SHA = '05f3bb41c1953eb2cf56236d288096637b080fb13b9792120d164111ed9449df'
# Explicit cleanup-only late imports. Capture dependencies are admitted below
# from the failed operation's pinned report, then fresh read-only capture.
CLEANUP_IMPORTS = ('unity_export', 'animation_worklist_collection', 'animation_export',
                   'animation_worklist_target', 'body_calibration_overlay')
CLOSURE_REVIEW_COMPLETE = True
ACTIVE = None


def prefix_registration(bpy, prior, graph, original, modules):
    """Only missing registrations owned by the completed prefix are allowed."""
    allowed_classes = {id(cls) for cls in modules['character_designer.skirt_wiggle_ui'].SKIRT_WIGGLE_UI_CLASSES}
    allowed_classes.update(id(cls) for cls in modules['character_designer.control_weight_paint'].CLASSES)
    for name in ('control_pose_capture', 'control_pose_assets'):
        allowed_classes.update(id(value) for value in vars(modules['character_designer.' + name]).values()
            if isinstance(value, type) and getattr(value, '__module__', None) == 'character_designer.' + name
            and hasattr(value, 'is_registered'))
    missing = []
    for row in graph['RNA_classes']:
        cls = next(value for value in original['CLASSES'] if value.__name__ == row['name'])
        prior.require(id(cls) == row['python_id'], 'The retained original RNA class object changed.')
        actual = original['_registered_rna_class'](cls)
        if actual is None and not cls.is_registered:
            prior.require(id(cls) in allowed_classes, 'An uncompleted cleanup class is missing: ' + cls.__name__)
            missing.append(cls.__name__)
        else:
            prior.require(actual is cls and cls.is_registered, 'A foreign class replaced original RNA: ' + cls.__name__)
    pointer_types = prior.original_pointer_types(bpy, original, graph)
    allowed_handler_modules = {'character_designer.skirt_wiggle', 'character_designer.hair_wiggle_adapter',
                              'character_designer.generated_names'}
    actual_handlers = prior.owned_callbacks(bpy)
    for name in set(graph['handlers']) | set(actual_handlers):
        expected = graph['handlers'].get(name, [])
        current = actual_handlers.get(name, [])
        expected_ids = [row['python_id'] for row in expected]
        current_ids = [id(fn) for fn in current]
        prior.require(len(set(current_ids)) == len(current_ids)
            and all(value in expected_ids for value in current_ids), 'An unexpected CD callback appeared: ' + name)
        prior.require(current_ids == [value for value in expected_ids if value in current_ids],
                      'The remaining callback ordering changed: ' + name)
        for row in expected:
            prior.require(row['python_id'] in current_ids or row['module'] in allowed_handler_modules,
                          'A callback outside the completed prefix disappeared: ' + name)
        for fn in current:
            row = next(row for row in expected if row['python_id'] == id(fn))
            prior.require(id(fn.__globals__) == row['globals_id'], 'A callback globals identity changed.')
    return {'allowed_missing_RNA_classes': missing, 'fixed_types_exact_count': len(pointer_types),
            'remaining_callbacks_are_original_ordered_subset': True}


def idle(bpy, prior, state, shim, ctx):
    state['refresh'].idle(shim, ctx, bpy)
    modules = state['original_modules']
    paint, skirt = modules['character_designer.control_weight_paint'], modules['character_designer.skirt_wiggle']
    prior.require(paint.active(ctx) is None and paint.SESSION not in ctx.scene, 'An owned paint workspace is active.')
    prior.require(not skirt._REGISTERED and not skirt._SESSIONS
        and not any(skirt.STATE_KEY in obj for obj in bpy.data.objects), 'A Dress runtime or saved state appeared.')
    prior.require(not modules['character_designer.skirt']._ACTIVE_BAKES
        and not modules['character_designer.unity_export_ui']._MODAL_EXPORTS
        and not modules['character_designer.animation_worklist_ui']._DRAGS, 'An owned operation is active.')


def run(*, config_path, config_sha256, script_sha256):
    global ACTIVE
    import bpy
    prior = sys.modules.get(PREDECESSOR_MODULE)
    if prior is None:
        raise RuntimeError('The exact retained 3636 recovery module is required; never recreate its baseline.')
    prior.require(ACTIVE is None and CLOSURE_REVIEW_COMPLETE, 'This continuation is single-use and requires completed source review.')
    prior.pin(PREDECESSOR, PREDECESSOR_SHA)
    prior.require(Path(prior.__file__).resolve() == PREDECESSOR.resolve(), 'The retained predecessor has another source.')
    state = prior.STATE
    prior.require(state is not None, 'The actual pre-cleanup state is no longer retained.')
    failure_pin = prior.pin(FAILURE, FAILURE_SHA)
    failed = prior.document(failure_pin)
    prior.require(failed['phase'] == 'cleanup_failed' and failed['completed'] is False
        and failed['error'] == 'RuntimeError: An unsealed late cleanup import was refused: character_designer.body_calibration_overlay'
        and failed['temporary_root_removed'] is True
        and prior.exact_json(state['report']) == prior.exact_json(failed), 'Use the actual, unchanged 3636 partial-cleanup outcome.')
    config_pin = prior.pin(config_path, config_sha256)
    config = prior.document(config_pin)
    prior.require(config['external_authorization_confirmed'] is True and config['authorization_token']
        and config['authorization_token'] != state['config']['authorization_token'], 'Fresh continuation authorization is required.')
    prior.require(set(config) == set(state['config']) and all(prior.exact_json(value) == prior.exact_json(state['config'][key])
        for key, value in config.items() if key not in {'authorization_token', 'output_root'}),
        'Only fresh authorization/output may change; evidence/PID/FILETIME/package must remain exact.')
    prior.require(os.getpid() == failed['pid'] == config['expected_pid'] == 14500
        and config['external_process_filetime'] == failed['external_process_filetime']
        and Path(bpy.data.filepath).resolve() == prior.ARTIST.resolve() and not bpy.app.background,
        'Use the same authenticated original process and artist file.')
    prior.require(not any(prior.cd_name(name) for name in sys.modules), 'A new CD module registry appeared after the failed cleanup.')
    inputs = copy.deepcopy(failed['inputs'])
    for row in inputs.values():
        prior.pin(row['path'], row['sha256'])
    prior.require(failed['fresh_full_before']['sha256'] == BEFORE_SHA
        and failed['fresh_raw_Scene_WM_Object_Action_before']['sha256'] == RAW_BEFORE_SHA,
        'Do not substitute a new before baseline.')
    before_disk = prior.document(failed['fresh_full_before'])
    raw_disk = prior.document(failed['fresh_raw_Scene_WM_Object_Action_before'])
    prior.require(prior.exact_json(state['verifier'].public(state['before'])) == prior.exact_json(before_disk)
        and prior.exact_json(state['raw_before']) == prior.exact_json(raw_disk)
        and state['dirty_before'] == failed['dirty_before']
        and prior.exact_json(state['identities_before']) == prior.exact_json(failed['identities_before']),
        'The retained native baseline differs from the actual pre-cleanup snapshots.')
    graph = prior.document(inputs['graph'])
    original, modules, observed = state['original_globals'], state['original_modules'], state['observed']
    prior.require(id(original) == graph['root_globals_id'] and tuple(original['bl_info']['version']) == (0, 77, 36)
        and bpy.types.CHARACTERDESIGNER_PT_main.draw.__globals__ is original and len(modules) == 99,
        'The retained original namespace/graph changed.')
    for row in graph['modules']:
        prior.require(id(modules[row['name']]) == row['id'] and id(vars(modules[row['name']])) == row['globals_id'],
                      'An original retained module identity changed.')
    prefix = prefix_registration(bpy, prior, graph, original, modules)
    functions = prior.owned_functions(observed['actual_spaces'].values(), observed)
    prior.require(not any(bpy.app.timers.is_registered(fn) for fn in functions.values()), 'An old owned timer became active.')
    previous_manifest = prior.document(inputs['old_manifest'])
    for name, digest in state['candidate']['files'].items():
        prior.pin(state['installed'] / name, digest)
    output = Path(config['output_root']).resolve()
    prior.require(not output.exists() and output.is_relative_to(ROUND), 'Use a new continuation output directory.')
    output.mkdir()
    inputs.update(predecessor_source=inputs['source'], predecessor_config=inputs['config'], predecessor_failure=failure_pin,
                  source=prior.pin(__file__, script_sha256), config=config_pin)
    report = copy.deepcopy(failed)
    for name in ('error', 'traceback'):
        report.pop(name, None)
    report.update(inputs=inputs, phase='continuation_admitted_same_precleanup_baseline', completed=False,
        continuation_of_actual_partial_cleanup=True, before_baseline_replaced=False,
        prefix_registration_admission=prefix)
    # Preserve state['before'], raw_before, identities_before and all actual RNA
    # references. Only the receipt destination and fresh authorization advance.
    state.update(output=output, report=report, config=config)
    ACTIVE = prior
    prior.write_report()
    shim = types.ModuleType('character_designer')
    shim.__dict__.update(original)
    shim.__path__ = [str(prior.OLD_ROOT)]
    shim.__addon_enabled__ = False
    finder = prior.FrozenOldImports(previous_manifest)
    cleanup_started = False
    entry_sys_path = list(sys.path)
    try:
        sys.modules.update(modules)
        sys.modules['character_designer'] = shim
        sys.meta_path.insert(0, finder)
        for name in [row['module'] for row in failed['frozen36_cleanup_dependencies']] + [
                'character_designer.' + name for name in CLEANUP_IMPORTS]:
            importlib.import_module(name)
        with state['light'].original_context(bpy, 'Scene', 'CoshaRig') as (ctx, rig):
            idle(bpy, prior, state, shim, ctx)
            current = state['refresh'].capture(ctx, rig, bpy, modules['character_designer.unity_animation'], shim,
                state['light'], state['verifier'], modules['character_designer.animation_worklist_fingerprint'])
            raw_current = prior.corrected_raw_snapshot(bpy, observed)
            identities = prior.native_identities(ctx, rig, state['light'])
            report['continuation_current_full'] = prior.checkpoint('continuation_current_full', current)
            report['continuation_current_raw'] = prior.checkpoint('continuation_current_raw', raw_current)
            state['refresh'].check_capture(state['before'], current)
            prior.require(prior.exact_json(raw_current) == prior.exact_json(state['raw_before'])
                and prior.exact_json(identities) == prior.exact_json(state['identities_before'])
                and bool(bpy.data.is_dirty) == state['dirty_before'],
                'Partial cleanup changed the pre-cleanup artist/raw/identity/dirty baseline; preserve the scene and stop.')
            report['current_precleanup_baseline_exact_before_continuation'] = True
            idle(bpy, prior, state, shim, ctx)
            spaces = {id(vars(module)): vars(module) for name, module in sys.modules.items() if prior.cd_name(name)}
            spaces.update(observed['actual_spaces'])
            functions.update(prior.owned_functions(spaces.values(), observed))
            classes = {id(value): value for namespace in spaces.values() for value in namespace.values()
                if isinstance(value, type) and getattr(value, '__module__', None) == namespace.get('__name__')
                and hasattr(value, 'is_registered')}
            prior.require(not any(bpy.app.timers.is_registered(fn) for fn in functions.values()), 'A cleanup dependency started a timer.')
            report['prefix_registration_before_continuation'] = prefix_registration(bpy, prior, graph, original, modules)
            finder.sealed = True
            report.update(phase='sealed_exact_partial_cleanup_continuation',
                frozen36_continuation_dependencies=finder.admitted, cleanup_import_set_sealed=True,
                known_owned_function_count=len(functions), owned_RNA_class_count=len(classes))
            prior.write_report()
            cleanup_started = True
            original['unregister']()
            report['owned_RNA_classes_remaining_after_cleanup'] = sorted(
                cls.__module__ + '.' + cls.__name__ for cls in classes.values() if cls.is_registered)
            prior.require(not report['owned_RNA_classes_remaining_after_cleanup'], 'An original owned RNA class remains.')
            prior.require(not any(prior.owned_callbacks(bpy).values())
                and not any(bpy.app.timers.is_registered(fn) for fn in functions.values()), 'An original owned callback/timer remains.')
            prior.require(not any(prop.identifier == 'character_designer' or prop.identifier.startswith('character_designer_')
                for owner in (bpy.types.Scene, bpy.types.WindowManager, bpy.types.Object) for prop in owner.bl_rna.properties),
                'An original owned RNA property remains.')
            report['exact_original36_cleanup_completed'] = True
    except Exception as error:
        report.update(phase='continuation_cleanup_failed' if cleanup_started else 'continuation_precleanup_refused',
                      error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
        raise
    finally:
        if finder in sys.meta_path:
            sys.meta_path.remove(finder)
        prior.clear_cd_modules()
        sys.path[:] = entry_sys_path
        report['temporary_root_removed'] = sys.modules.get('character_designer') is not shim
        prior.write_report()
    try:
        installed = state['installed']
        sys.path[:] = [str(installed.parent)] + [path for path in state['entry_sys_path'] if Path(path or '.').resolve() != installed.parent]
        importlib.invalidate_caches()
        import addon_utils
        def enable_error(error):
            report['standard_enable_errors'].append({'type': type(error).__name__, 'message': str(error),
                'traceback': ''.join(traceback.format_exception(type(error), error, error.__traceback__))})
        enabled = addon_utils.enable('character_designer', default_set=False, persistent=False, handle_error=enable_error)
        prior.require(not report['standard_enable_errors'] and enabled is not None
            and enabled is sys.modules.get('character_designer') and tuple(enabled.bl_info['version']) == (0, 77, 38)
            and enabled.__addon_enabled__, 'Standard .38 enable failed; preserve its full error evidence.')
        enabled._validate_registration_integrity()
        state['refresh'].loaded_sources(enabled, installed, state['candidate'])
        native = sys.modules['character_designer.unity_animation_rigging']
        prior.require(native._REACQUIRE_TIMER is not None and bpy.app.timers.is_registered(native._REACQUIRE_TIMER),
                      'The actual standard enable did not queue registration admission.')
        state.update(candidate_module=enabled, pending_timer=native._REACQUIRE_TIMER, pending_generation=native._REACQUIRE_GENERATION)
        report.update(phase='candidate_enabled_waiting_for_natural_timer', registered_candidate_version=[0, 77, 38],
            standard_enable_returned=True, manual_reacquire_called=False,
            sys_path_policy='Retain installed package parent first; preserve all other original entry paths and ordering.',
            sys_path_after=list(sys.path))
        prior.write_report()
        return {'completed': False, 'queued': True, 'report': str(output / 'recovery_report.json'),
                'next': 'Return to Blender event loop, then call this module verify_after_event_loop().'}
    except Exception as error:
        report.update(phase='candidate_enable_failed', error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
        prior.write_report()
        raise


def verify_after_event_loop():
    if ACTIVE is None:
        raise RuntimeError('No authenticated continuation is waiting.')
    return ACTIVE.verify_after_event_loop()
