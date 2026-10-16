"""Prepared GUI-only Hair leaf refresh. Importing this file never runs it.

run(config) requires exactly expected_pid, artist, artist_sha256, report_prefix.
Only fresh reports and an in-place registry-module reload are authorized here.
No timer, registration, scene repair/restoration, evaluation, save or export.
"""
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import types


BASE = Path(__file__).resolve().parent
ARTIST_SHA256 = 'db10be327442c98dd5148d504440ae5ab713320a9a618de889d4faff03c4719d'
PROJECTION_SHA256 = '9baac8f7575b121c5aa95502ad02b0a6762229fd7e86e395a1fb803eeade2b4c'
DIAGNOSTIC_SHA256 = '8721c2748f7f5440b3bfa93cfbd4ed832db95c575314d7164ab3c5b04fb0cb86'
CONNECTION_ERROR = 'Hair connection or ordered parent relationships changed.'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _diagnostic_module():
    path = BASE / 'inspect_live_hair.py'
    _require(_sha(path) == DIAGNOSTIC_SHA256, 'The sealed diagnostic helper changed.')
    module = types.ModuleType('_x_guarded_hair_diagnostic')
    module.__file__ = str(path)
    # No sys.modules/sys.path entry and no bytecode file is created for this helper.
    exec(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True,
                 optimize=sys.flags.optimize), module.__dict__)
    return module


def _idle(config, bpy, diagnostic):
    _require(type(config['expected_pid']) is int and os.getpid() == config['expected_pid'], 'Wrong GUI PID.')
    _require(not bpy.app.background, 'Background Blender is refused.')
    _require(not any(screen.is_animation_playing for screen in bpy.data.screens), 'Playback is active.')
    _require(not bpy.context.mode.startswith('EDIT')
             and not any(obj.mode == 'EDIT' for obj in bpy.data.objects), 'Edit Mode is active.')
    _require(not bpy.app.is_job_running('RENDER'), 'Rendering is active.')
    artist = Path(config['artist'])
    _require(artist.is_absolute() and artist.is_file() and bpy.data.filepath
             and Path(bpy.data.filepath).resolve() == artist.resolve(), 'Wrong artist filepath.')
    _require(config['artist_sha256'] == ARTIST_SHA256 and _sha(artist) == ARTIST_SHA256,
             'The current artist disk pin is not the admitted new db10 input.')
    leaf = diagnostic._live_registry()
    package = sys.modules.get(leaf.__package__)
    _require(package is not None and getattr(package, 'ADDON_REFRESH_PENDING', None) is False,
             'Full Refresh is pending or its state is unavailable.')
    _require(tuple(package.bl_info['version']) in {(0, 77, 41), (0, 77, 43)},
             'Loaded main version is outside the admitted .41/.43 runtime.')
    refresh = getattr(package, '_reload_addon_deferred', None)
    _require(callable(refresh) and not bpy.app.timers.is_registered(refresh), 'Full Refresh is queued.')
    adapter = sys.modules.get(leaf.__package__ + '.hair_wiggle_adapter')
    _require(adapter is not None and hasattr(adapter, '_SESSION') and adapter._SESSION is None
             and not getattr(adapter, '_STOPPING', False), 'Hair preview is active or unobservable.')
    for name in ('unity_export', 'animation_export'):
        module = sys.modules.get(leaf.__package__ + '.' + name)
        _require(module is None or (hasattr(module, '_ACTIVE_JOB') and module._ACTIVE_JOB is None),
                 name + ' has an active/unobservable export.')
    return leaf, package


def _tree(root, expected):
    paths = {path.relative_to(root).as_posix(): path for path in root.rglob('*')
             if path.is_file() and not any(part.startswith('.') or part == '__pycache__'
                 for part in path.relative_to(root).parts) and path.suffix not in {'.pyc', '.pyo'}}
    _require(set(paths) == set(expected), 'The deployed/frozen file set is not the exact approved projection.')
    for name, path in paths.items():
        _require(path.resolve().is_relative_to(root.resolve()) and _sha(path) == expected[name],
                 'Projection file hash/path differs: ' + str(path))
    return {'root': str(root), 'files': len(paths), 'all_exact': True}


def _deployment(leaf, package):
    manifest = BASE / 'release_projection_07743.json'
    _require(_sha(manifest) == PROJECTION_SHA256, 'The sealed release projection changed.')
    projection = json.loads(manifest.read_text(encoding='utf-8'))
    expected, provenance = projection['files'], projection['source_provenance']
    baseline = provenance['base_files_sha256']
    changed = {name for name in expected if expected[name] != baseline.get(name)}
    _require(projection['version'] == '0.77.43' and len(expected) == 190
             and set(expected) == set(baseline) and provenance['base_version'] == '0.77.41'
             and changed == {'__init__.py', 'hair_strand_registry.py'}
             and set(provenance['approved_changed_files']) == changed,
             'The projection is not the approved two-file .41-to-.43 change.')
    for name in changed:
        change = provenance['approved_changed_files'][name]
        _require(change['before_sha256'] == baseline[name] and change['after_sha256'] == expected[name],
                 'Approved change pins differ: ' + name)
    frozen = BASE / 'release_07743' / 'character_designer'
    installed = Path(leaf.__file__).resolve().parent
    _require(Path(projection['source_root']).resolve() == frozen.resolve()
             and Path(package.__file__).resolve() == installed / '__init__.py'
             and Path(leaf.__file__).resolve() == installed / 'hair_strand_registry.py',
             'Live package/leaf and frozen source identities disagree.')
    return {'projection_sha256': PROJECTION_SHA256, 'changed_files': sorted(changed),
            'frozen': _tree(frozen, expected), 'installed': _tree(installed, expected),
            'leaf_sha256': expected['hair_strand_registry.py']}


def _diagnose(diagnostic, config, path):
    diagnostic.run({'expected_pid': config['expected_pid'], 'artist': config['artist'],
                    'candidate_root': str(BASE / 'release_07743' / 'character_designer'), 'report': str(path)})
    result = json.loads(path.read_text(encoding='utf-8'))
    clean = result.get('cleanup', {})
    _require(result.get('status') == 'diagnosed' and result.get('protected_state_unchanged') is True
             and not clean.get('owned_remaining') and clean.get('sys_path_restored') is True
             and clean.get('meta_path_unchanged') is True and clean.get('bytecode_flag_restored') is True
             and clean.get('existing_module_identities_unchanged') is True,
             'Fresh diagnosis failed protection/cleanup; no refresh is authorized.')
    return result


def _loaded_leaf_matches_disk(leaf):
    # Match the loader's own filename spelling and current optimization mode.
    filename = leaf.read.__code__.co_filename
    code = compile(Path(leaf.__file__).read_bytes(), filename, 'exec', dont_inherit=True,
                   optimize=sys.flags.optimize)
    definitions = {value.co_name: value for value in code.co_consts if isinstance(value, types.CodeType)}
    names = ('read', '_live', '_rest', '_anchor', '_source_rest_view', '_source_bone')
    return all(getattr(getattr(leaf, name, None), '__code__', None) == definitions.get(name) for name in names)


def run(config):
    """Perform a guarded leaf-only reload, or record why it was skipped/refused."""
    _require(set(config) == {'expected_pid', 'artist', 'artist_sha256', 'report_prefix'}, 'Unexpected/missing config keys.')
    prefix = Path(config['report_prefix'])
    _require(prefix.is_absolute() and prefix.parent.resolve() == BASE and not prefix.suffix
             and not any(BASE.glob(prefix.name + '*')), 'report_prefix must be new and unused in this directory.')
    summary, before_report, after_report = (Path(str(prefix) + suffix)
                                           for suffix in ('.json', '.before.json', '.after.json'))
    result = {'schema': 'x.validation.guarded-hair-leaf-refresh/1', 'status': 'refused',
        'reload_attempted': False, 'scene_operations': False,
        'limits': ['GUI proof only; no model export, Unity acceptance, playback proof or artist save.',
                   'Only captured native state is compared; non-enumerable timer/GPU/cache side effects remain unproved.',
                   'Main bl_info is never altered; a .41 main with the .43 Hair leaf is recorded as mixed runtime.',
                   'Failures stop without scene repair/restoration or a full Refresh fallback.']}
    diagnostic, first = None, None
    with summary.open('x', encoding='utf-8', newline='\n') as stream:
        try:
            import bpy
            diagnostic = _diagnostic_module()
            leaf, package = _idle(config, bpy, diagnostic)
            result['artist'] = {'path': bpy.data.filepath, 'disk_sha256': ARTIST_SHA256,
                                'pid': os.getpid(), 'dirty': bool(bpy.data.is_dirty)}
            first = _diagnose(diagnostic, config, before_report)
            result['before_report'] = str(before_report)
            result['runtime_main_version'] = list(package.bl_info['version'])
            result['leaf_module_before'] = diagnostic._module_info(leaf)
            if first['live_registry']['ok']:
                result['status'] = 'skipped_live_registry_already_passes'
            else:
                failure, proof, flags = first['live_registry'], first.get('adoption_proof', {}), first.get('chain_flags', {})
                _require(failure.get('error_type') == 'HairStrandRegistryError'
                         and failure.get('error') == CONNECTION_ERROR
                         and first.get('candidate_registry', {}).get('ok') is True
                         and proof.get('ok') is True and proof.get('view_available') is True
                         and flags.get('live_binding_mismatches', 0) > 0
                         and flags.get('authored_binding_mismatches') == 0,
                         'The fresh failure/proof is not the admitted managed-connection case.')
                result['deployment'] = _deployment(leaf, package)
                live_again, package_again = _idle(config, bpy, diagnostic)
                _require(live_again is leaf and package_again is package, 'Runtime ownership changed before reload.')
                for module_name, alias in (('hair_motion_ui', 'registry'), ('hair_wiggle_adapter', 'strands')):
                    caller = sys.modules.get(leaf.__package__ + '.' + module_name)
                    _require(caller is None or getattr(caller, alias, None) is leaf, 'A Hair caller holds another module identity.')
                previous_bytecode = sys.dont_write_bytecode
                result['reload_attempted'] = True
                try:
                    sys.dont_write_bytecode = True
                    reloaded = importlib.reload(leaf)
                finally:
                    sys.dont_write_bytecode = previous_bytecode
                _require(reloaded is leaf and sys.modules.get(leaf.__name__) is leaf,
                         'Reload changed the existing leaf module identity.')
                _require(_loaded_leaf_matches_disk(leaf), 'Loaded leaf functions do not match the exact deployed source.')
                result['leaf_module_after'] = diagnostic._module_info(leaf)
                result['mixed_runtime'] = tuple(package.bl_info['version']) != (0, 77, 43)
                result['status'] = 'leaf_reloaded_pending_post_diagnosis'
        except Exception as exc:
            result['failure'] = {'type': type(exc).__name__, 'error': str(exc)}
            result['status'] = 'reload_failed_no_repair' if result['reload_attempted'] else 'refused_no_reload'
        finally:
            if diagnostic is not None and first is not None:
                try:
                    if result['reload_attempted']:
                        after = _diagnose(diagnostic, config, after_report)
                        result['after_report'] = str(after_report)
                        result['targeted_state_unchanged'] = first['after'] == after['after']
                        result['registry_passes_after'] = after['live_registry']['ok']
                        result['registry_equals_candidate'] = after['live_registry'].get('sha256') == after['candidate_registry'].get('sha256')
                        _require(result['targeted_state_unchanged'] and result['registry_passes_after']
                                 and result['registry_equals_candidate'], 'Post-refresh state/proof differs; no repair attempted.')
                        if 'failure' not in result:
                            result['status'] = 'leaf_refresh_verified_gui_only'
                    else:
                        result['targeted_state_unchanged'] = first['protected_state_unchanged']
                    result['artist_disk_unchanged'] = _sha(config['artist']) == ARTIST_SHA256
                    _require(result['artist_disk_unchanged'], 'Artist disk pin changed during the operation.')
                except Exception as exc:
                    result['post_failure'] = {'type': type(exc).__name__, 'error': str(exc)}
                    result['status'] = 'post_proof_failed_no_repair'
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    return {'status': result['status'], 'report': str(summary), 'reload_attempted': result['reload_attempted'],
            'failure': result.get('failure'), 'post_failure': result.get('post_failure')}
