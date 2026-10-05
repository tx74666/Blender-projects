"""Reviewed live-X entry point; preparation alone performs no Blender action.

The caller must obtain fresh coordination and official-install approval, then
execute this file into a namespace and call run with the OBSERVED prior editor:

  scope = {'__file__': SCRIPT_PATH, '__name__': 'cd_live_hair_install'}
  exec(compile(Path(SCRIPT_PATH).read_text(encoding='utf8'), SCRIPT_PATH, 'exec'), scope)
  scope['run'](previous_editor={'type': OBSERVED_TYPE, 'ui_type': OBSERVED_UI_TYPE},
               approved_official_install=True)

No main call occurs on import/exec. No artist file is opened, pose preview is
started, frame is changed, bone display is changed, or bake function is called.
An independent native recovery copy precedes refresh/install/configuration.
Installation uses Blender's official local-extension operator only. Failure
before the artist save rolls back owned source metadata. After a finished artist
save, a validation failure preserves the saved configuration and reports that
review is required. It never uninstalls shared packages or reloads the artist
from a background result. Every attempt retains its own recovery and report.
"""
import datetime
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import time
import tomllib
import traceback

import bpy

DIRECTORY = Path(__file__).resolve().parent
ARTIST = Path('D:/Blender/Projects/Character/X/X.blend').resolve()
ARCHIVE = DIRECTORY.parent / 'wiggle_research_20261004' / 'wiggle_bones-1.1.2.zip'
ARCHIVE_SHA256 = '9f58389c7702d8a4d768fb0d8b53aebc441032363b9269c97bf5736d0561f8a0'
EXPECTED_UID = '331afdb7e5154ae1aaa39603a4f61768'
VERSION = (0, 76, 1)
LEGACY_SHA256 = '7333687ae3b6fd20feae8afda649faed1d99bc7b98e92622a8993c09061deac1'
REPORT_PREFIX = 'live_install_refresh_config_save'
READERS_SHA256 = '36495cde240e0cb49a8f49a8c1e0d3043391ae9a127c1d04214f22721dbbcc9c'
POSE_TOLERANCE = 1e-6


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_report(facts):
    """Preserve every attempt, including same-time retries, without replacement."""
    stamp = facts['started_utc'].replace('-', '').replace(':', '').replace('+', '_')
    for index in range(1000):
        suffix = '' if index == 0 else '_' + str(index)
        path = DIRECTORY / (REPORT_PREFIX + '_' + stamp + suffix + '.json')
        result = dict(facts, report_path=str(path))
        serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        try:
            with path.open('x', encoding='utf8') as stream:
                stream.write(serialized)
        except FileExistsError:
            continue
        facts['report_path'] = str(path)
        return
    raise RuntimeError('No independent report filename is available; no prior report was replaced.')


def runtime():
    addon = sys.modules.get('character_designer')
    require(addon is not None, 'The native installed Character Designer runtime is not loaded.')
    expected = (Path(bpy.utils.user_resource('SCRIPTS')) / 'addons' / 'character_designer' / '__init__.py').resolve()
    require(Path(addon.__file__).resolve() == expected,
            'Loaded Character Designer is not the active Blender user installation: ' + str(addon.__file__))
    require(expected.is_file(), 'The installed Character Designer source is missing.')
    result = {'addon': addon, 'installed_source': expected}
    for short in ('hair_bones_rig', 'hair_strand_registry', 'hair_motion_profiles',
                  'hair_motion_lifecycle', 'hair_wiggle_adapter', 'bone_display', 'forearm_twist'):
        result[short] = importlib.import_module('character_designer.' + short)
        require(Path(result[short].__file__).resolve().parent == expected.parent,
                'A Character Designer dependency is loaded from another package: ' + short)
    return result


def read_helpers(modules):
    """Import reviewed readers without calling the validation script's main."""
    path = DIRECTORY / 'validate_real_hair_preview.py'
    require(path.is_file(), 'The reviewed artist-data reader source is missing.')
    reviewed_source = path.read_bytes()
    require(hashlib.sha256(reviewed_source).hexdigest() == READERS_SHA256,
            'The reviewed artist-data reader source hash differs; review the changed helper before use.')
    name = '_cd_live_hair_validation_readers'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    try:
        # Execute the exact reviewed bytes, rather than letting an import
        # loader reread a changed file or accept an unrelated bytecode cache.
        exec(compile(reviewed_source, str(path), 'exec'), module.__dict__)
    finally:
        sys.path[:] = old_path
    module.ALLOWED_METADATA = {modules['hair_strand_registry'].REGISTRY_KEY,
        modules['hair_motion_profiles'].PROFILE_KEY,
        modules['hair_motion_lifecycle'].OWNER_KEY,
        modules['hair_motion_lifecycle'].IDENTITY_KEY}
    module.adapter = modules['hair_wiggle_adapter']
    return module


def find_source(hair):
    found = []
    for source in bpy.data.objects:
        if source.type != 'MESH' or hair.RECORD_KEY not in source:
            continue
        try:
            record = json.loads(source[hair.RECORD_KEY])
        except (ValueError, TypeError):
            continue
        if isinstance(record, dict) and record.get('source_id') == EXPECTED_UID:
            found.append(source)
    require(len(found) == 1, 'The proven Cosha Hair source UID must identify exactly one live mesh.')
    return found[0]


def selection_snapshot():
    layer = bpy.context.view_layer
    return {'mode': bpy.context.mode, 'scene': bpy.context.scene.name,
        'view_layer': layer.name,
        'active_object': layer.objects.active.name if layer.objects.active else None,
        'selected_objects': sorted(obj.name for obj in bpy.context.selected_objects),
        'rigs': {obj.name: {'active': obj.data.bones.active.name if obj.data.bones.active else None,
            # Blender 5.1 Object/Pose selection belongs to PoseBone; EditBone
            # head/tail flags are neither available nor relevant in this run.
            'selected': sorted(bone.name for bone in obj.pose.bones if bone.select)}
            for obj in bpy.data.objects if obj.type == 'ARMATURE'}}


def full_pose(modules, helpers):
    adapter = modules['hair_wiggle_adapter']
    result = {'frame': (bpy.context.scene.frame_current, bpy.context.scene.frame_subframe),
        'autokey': bpy.context.scene.tool_settings.use_keyframe_insert_auto,
        'channels': [], 'custom': [], 'wiggle': [], 'evaluated': [], 'shapes': []}
    owners = list(bpy.data.scenes)
    for obj in bpy.data.objects:
        owner, mode, channels = adapter._channels(obj, True)
        result['channels'].append((owner, mode, channels, tuple(tuple(row) for row in obj.matrix_basis)))
        result['evaluated'].append((obj, 'matrix_world', tuple(tuple(row) for row in obj.matrix_world)))
        owners.append(obj)
        if obj.type == 'ARMATURE':
            for bone in obj.pose.bones:
                owner, mode, channels = adapter._channels(bone)
                result['channels'].append((owner, mode, channels, tuple(tuple(row) for row in bone.matrix_basis)))
                result['evaluated'].append((bone, 'matrix', tuple(tuple(row) for row in bone.matrix)))
                owners.append(bone)
        if obj.type == 'MESH' and obj.data.shape_keys:
            keys = obj.data.shape_keys
            result['shapes'].append((keys, keys.eval_time,
                tuple((key.name, key.value, key.mute) for key in keys.key_blocks)))
    for owner in owners:
        result['custom'].append(adapter._pose_custom(owner))
        if owner.bl_rna.properties.get('wiggle') is not None:
            result['wiggle'].append(adapter._raw_snapshot(owner))
        else:
            result['wiggle'].append((owner, False, None))
    return result


def check_pose(saved, modules):
    adapter = modules['hair_wiggle_adapter']
    require((bpy.context.scene.frame_current, bpy.context.scene.frame_subframe) == saved['frame'],
            'Artist frame/subframe changed.')
    require(bpy.context.scene.tool_settings.use_keyframe_insert_auto == saved['autokey'], 'AutoKey changed.')
    for owner, mode, channels, basis in saved['channels']:
        require(owner.rotation_mode == mode
            and all(tuple(getattr(owner, key)) == value for key, value in channels.items())
            and tuple(tuple(row) for row in owner.matrix_basis) == basis,
            'Exact artist pose input changed: ' + owner.name)
    for owner, values in saved['custom']:
        require(adapter._pose_custom(owner)[1] == values, 'Artist numeric pose properties changed: ' + owner.name)
    for owner, existed, values in saved['wiggle']:
        current = adapter._raw_snapshot(owner) if owner.bl_rna.properties.get('wiggle') is not None else (owner, False, None)
        require(current[1:] == (existed, values), 'Artist native Wiggle data changed: ' + owner.name)
    for keys, evaluation, values in saved['shapes']:
        require(keys.eval_time == evaluation
            and tuple((key.name, key.value, key.mute) for key in keys.key_blocks) == values,
            'Artist Shape Key state changed: ' + keys.name)
    maximum = 0.
    for owner, field, before in saved['evaluated']:
        after = getattr(owner, field)
        differences = [abs(float(old) - float(new)) for left, right in zip(before, after)
                       for old, new in zip(left, right)]
        require(all(math.isfinite(value) for value in differences), 'Nonfinite evaluated artist pose: ' + owner.name)
        maximum = max(maximum, max(differences, default=0.))
    require(maximum <= POSE_TOLERANCE, 'Evaluated artist pose changed beyond native float tolerance.')
    return {'inputs_exact': True, 'maximum_evaluated_matrix_error': maximum, 'tolerance': POSE_TOLERANCE}


def display_snapshot(modules):
    adapter = modules['hair_wiggle_adapter']
    return {obj.name: {'display': modules['bone_display']._snapshot(obj),
        'data_properties': {key: adapter._clone(obj.data[key]) for key in obj.data.keys()},
        'pose': {bone.name: {'locks': (tuple(bone.lock_location), tuple(bone.lock_rotation),
                         tuple(bone.lock_scale), bone.lock_rotation_w, bone.lock_rotations_4d),
            'constraints': tuple(adapter._rna_snapshot(item) for item in bone.constraints),
            'shape': bone.custom_shape, 'shape_transform': bone.custom_shape_transform,
            'shape_scale': tuple(bone.custom_shape_scale_xyz),
            'shape_translation': tuple(bone.custom_shape_translation),
            'shape_rotation': tuple(bone.custom_shape_rotation_euler)} for bone in obj.pose.bones}}
        for obj in bpy.data.objects if obj.type == 'ARMATURE'}


def automatic_refresh_plan():
    """Prove queued migration/name callbacks have no artist writes to perform.

    Use their own read-only target readers and eligibility tests, not execution
    of either cleanup service. A planned migration/rename blocks this limited
    Hair integration before refresh; it needs a separate reviewed operation.
    """
    from character_designer import (bone_collections as groups, body_setup,
        generated_names as names, skirt_rig as skirt)
    result = {'migration_candidates': [], 'rename_candidates': [], 'name_reader_skips': []}
    for rig in tuple(bpy.context.scene.objects):
        if (rig.type != 'ARMATURE' or rig.mode == 'EDIT' or rig.library or rig.data.library
                or not rig.is_editable or rig.data.users != 1 or rig.data.get(groups.NATIVE_ONLY_KEY)
                or groups.VIEW_KEY in rig.data):
            continue
        original = rig.data.collections_all.get('Original')
        if (groups.body_collection(rig) is not None and original is not None
                and original.get(groups.GROUP_KEY) == 'Original' and not body_setup.has_generated(rig)):
            result['migration_candidates'].append(rig.name)
    # clean_generated_names catches these exact errors and skips the affected
    # resource before any transaction. Retain that same read-only refusal.
    errors = (ValueError, RuntimeError, KeyError, TypeError, AttributeError)
    for rig in tuple(bpy.data.objects):
        if (rig.type != 'ARMATURE' or rig.library or rig.data.library or not rig.is_editable
                or rig.data.users != 1 or rig.mode == 'EDIT'
                or not any(key.startswith('character_designer') for key in rig.data.keys())):
            continue
        try:
            result['rename_candidates'].extend((item.name, target, domain)
                for item, target, domain in names._widget_targets(rig))
        except errors as exc:
            result['name_reader_skips'].append({'name': rig.name, 'reason': str(exc)})
    for source in tuple(bpy.data.objects):
        if skirt.RECORD_KEY not in source or source.library or not source.is_editable or source.mode == 'EDIT':
            continue
        try:
            result['rename_candidates'].extend((item.name, target, domain)
                for item, target, domain in names._skirt_targets(source))
            record = skirt.read_record(source)
            if record:
                # These are the exact authoritative names used by clean(),
                # with the same legacy pattern; no guessed bone correspondence.
                legacy = re.compile(r'^SK_.+_' + re.escape(record['owner'][:6]) + r'(_.+)$')
                prefix = 'SK_' + names.label(source.name, 37)
                expected = set.union(*skirt._bone_collection_layout(record))
                result['rename_candidates'].extend((name, prefix + match.group(1), 'bone')
                    for name in expected if (match := legacy.fullmatch(name)))
        except errors as exc:
            result['name_reader_skips'].append({'name': source.name, 'reason': str(exc)})
    require(not result['migration_candidates'] and not result['rename_candidates'],
            'Refresh has a pending native layout/name migration; this Hair-only operation cannot apply it: '
            + json.dumps(result, ensure_ascii=False))
    return result


def text_snapshot(adapter):
    return {text: {'name': text.name, 'body': text.as_string(), 'module': text.use_module,
        'fake_user': text.use_fake_user,
        'properties': {key: adapter._clone(text[key]) for key in text.keys()}} for text in bpy.data.texts}


def check_texts(saved, source, modules):
    adapter, lifecycle = modules['hair_wiggle_adapter'], modules['hair_motion_lifecycle']
    now = text_snapshot(adapter)
    for text, proof in saved.items():
        require(text in now and now[text] == proof, 'An existing artist Text changed or disappeared.')
    created = set(now) - set(saved)
    require(len(created) <= 1, 'More than one private Hair identity Text was created.')
    for text in created:
        require(lifecycle._owned_holder(text, source) and source.get(lifecycle.OWNER_KEY) == text
                and text.as_string() == lifecycle._HOLDER_BODY
                and not text.use_module and not text.use_fake_user,
                'An unowned or unexpected Text datablock was created.')
    return len(created)


def no_live_preview(modules):
    require(not bpy.context.screen.is_animation_playing, 'Pause artist timeline playback first.')
    addon, adapter = modules['addon'], modules['hair_wiggle_adapter']
    require(not adapter.status()['active'], 'Finish the active Hair preview before refresh/install/save.')
    require(modules['forearm_twist']._SESSION is None, 'Finish the active Forearm preview first.')
    require(not any(modules['forearm_twist'].PREVIEW_KEY in obj for obj in bpy.data.objects),
            'An existing Forearm preview marker must be resolved before saving.')
    require(getattr(addon, '_LIVE_PREVIEW_SOURCE_KEY', None) is None, 'Finish Hair Centerline Live Preview first.')
    delta = sys.modules.get('character_designer.delta_symmetry')
    require(delta is None or getattr(delta, '_RUNTIME', None) is None, 'Finish Delta Symmetry Live Preview first.')
    skirt = sys.modules.get('character_designer.skirt')
    require(skirt is None or not getattr(skirt, '_ACTIVE_BAKES', {}),
            'Finish the active Dress bake before refreshing Character Designer.')
    legacy = sys.modules.get('wiggle_2')
    legacy_registered = legacy is not None and getattr(legacy.WiggleScene, 'is_registered', False)
    for owner in (*tuple(bpy.data.scenes), *tuple(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')):
        if legacy_registered:
            require(owner.bl_rna.properties.get('wiggle_enable') is not None and not owner.wiggle_enable,
                    'A pre-existing legacy Wiggle simulation must remain untouched: ' + owner.name)
        elif owner.bl_rna.properties.get('wiggle') is not None and owner.is_property_set('wiggle'):
            require(owner.wiggle.bl_rna.properties.get('enable') is not None,
                    'Unsupported native Wiggle RNA schema: ' + owner.name)
            require(not owner.wiggle.enable, 'A pre-existing native Wiggle simulation must remain untouched: ' + owner.name)
        if isinstance(owner, bpy.types.Scene) and owner.bl_rna.properties.get('wiggle') is not None and owner.is_property_set('wiggle'):
            require(not any(getattr(owner.wiggle, key) for key in ('is_rendering', 'reset', 'is_preroll')),
                    'A native Wiggle render/reset/preroll is active: ' + owner.name)


def legacy_snapshot(modules):
    """Only the reviewed inactive v2.2.4 may be natively disabled, without conversion."""
    legacy = sys.modules.get('wiggle_2')
    if legacy is None or not getattr(legacy.WiggleScene, 'is_registered', False):
        return None
    require(tuple(legacy.bl_info['version']) == (2, 2, 4)
            and sha256(legacy.__file__) == LEGACY_SHA256, 'The legacy Wiggle source differs from the reviewed v2.2.4.')
    require('wiggle_2' in bpy.context.preferences.addons, 'Legacy Wiggle registration has no enabled preference owner.')
    for typename, owner in (('WiggleScene', bpy.types.Scene), ('WiggleObject', bpy.types.Object), ('WiggleBone', bpy.types.PoseBone)):
        prop = owner.bl_rna.properties.get('wiggle')
        require(prop is not None and prop.fixed_type == getattr(legacy, typename).bl_rna,
                'Legacy Wiggle RNA owner differs: ' + typename)
    handlers = [(getattr(bpy.app.handlers, collection), getattr(legacy, function))
        for collection, function in (('frame_change_pre', 'wiggle_pre'), ('frame_change_post', 'wiggle_post'),
            ('render_pre', 'wiggle_render_pre'), ('render_post', 'wiggle_render_post'),
            ('render_cancel', 'wiggle_render_cancel'), ('load_post', 'wiggle_load'))]
    require(all(collection.count(function) == 1 for collection, function in handlers),
            'Legacy Wiggle callbacks are not each registered exactly once.')
    rows = []
    for owner in [*bpy.data.scenes, *bpy.data.objects,
            *(bone for obj in bpy.data.objects if obj.type == 'ARMATURE' for bone in obj.pose.bones)]:
        top = {}
        for prop in owner.bl_rna.properties:
            if not prop.identifier.startswith('wiggle_'):
                continue
            was_set = owner.is_property_set(prop.identifier)
            value = None if prop.type == 'POINTER' and not was_set else modules['hair_wiggle_adapter']._clone(getattr(owner, prop.identifier))
            top[prop.identifier] = (was_set, value)
        require(not any(top.get(key, (False, False))[1] for key in ('wiggle_enable', 'wiggle_head', 'wiggle_tail')),
                'Legacy per-bone physics settings need a separate reviewed migration: ' + owner.name)
        group_set = owner.bl_rna.properties.get('wiggle') is not None and owner.is_property_set('wiggle')
        raw = modules['hair_wiggle_adapter']._clone(owner.wiggle) if group_set else None
        rows.append((owner, top, group_set, raw))
    return {'module': legacy, 'handlers': handlers, 'rows': rows}


def legacy_serialized(snapshot):
    def encode(value):
        if isinstance(value, bpy.types.ID):
            return {'id_type': value.bl_rna.identifier, 'name': value.name_full,
                    'library': value.library.filepath if value.library else None}
        if isinstance(value, dict):
            return {key: encode(item) for key, item in value.items()}
        if hasattr(value, 'typecode'):
            return {'array_typecode': value.typecode, 'values': list(value)}
        if isinstance(value, (tuple, list)):
            return [encode(item) for item in value]
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        raise TypeError('Unsupported legacy snapshot value: ' + type(value).__name__)
    return {'module': 'wiggle_2', 'version': [2, 2, 4], 'source_sha256': LEGACY_SHA256,
        'simulation_active': False, 'automatic_conversion': False,
        'rows': [{'type': owner.bl_rna.identifier, 'name': owner.name,
                  'armature': owner.id_data.name if isinstance(owner, bpy.types.PoseBone) else None,
                  'top': encode(top), 'group_set': group_set, 'raw': encode(raw)}
                 for owner, top, group_set, raw in snapshot['rows']]}


def check_legacy_preserved(snapshot, modules):
    if snapshot is None:
        return
    require(sha256(snapshot['module'].__file__) == LEGACY_SHA256, 'The legacy Wiggle source file changed.')
    for owner, top, group_set, raw in snapshot['rows']:
        for key, (was_set, value) in top.items():
            prop = owner.bl_rna.properties.get(key)
            require(prop is not None and owner.is_property_set(key) == was_set,
                    'Legacy top-level setting presence changed: ' + owner.name + '.' + key)
            current = None if prop.type == 'POINTER' and not was_set else modules['hair_wiggle_adapter']._clone(getattr(owner, key))
            require(current == value,
                'Legacy top-level settings changed: ' + owner.name + '.' + key)
        require(owner.is_property_set('wiggle') == group_set, 'Legacy backing presence changed: ' + owner.name)
        if group_set:
            require(modules['hair_wiggle_adapter']._clone(owner.wiggle) == raw,
                    'Legacy inactive raw backing changed: ' + owner.name)


def official_files(path, adapter):
    require(path.is_dir(), 'The native Wiggle extension directory is missing.')
    manifest = tomllib.loads((path / 'blender_manifest.toml').read_text(encoding='utf8'))
    require(manifest.get('id') == 'wiggle_bones' and manifest.get('version') == '1.1.2',
            'An existing Wiggle package has another identity/version; do not overwrite it.')
    for filename, expected in adapter._HASHES.items():
        require(hashlib.sha256((path / filename).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == expected,
                'The existing official Wiggle source hash differs: ' + filename)


def extension_plan(modules):
    adapter = modules['hair_wiggle_adapter']
    ops = importlib.import_module('bl_pkg.bl_extension_ops')
    repositories = list(ops.repo_iter_valid_only(bpy.context, exclude_remote=False, exclude_system=False))
    try:
        backend = adapter._backend()
    except adapter.HairWiggleError:
        backend = None
    if backend is not None:
        matches = [repo for repo in repositories
            if backend['name'] == 'bl_ext.' + repo.module + '.wiggle_bones'
            and Path(backend['module'].__file__).resolve().parent == (Path(repo.directory) / 'wiggle_bones').resolve()]
        require(len(matches) == 1, 'The loaded Wiggle module is not a canonical native extension repository installation.')
        return {'operation': 'already_loaded', 'repo': matches[0], 'module': backend['name']}
    # A loaded incompatible package must not be replaced under this limited
    # installation approval. Only a clean native module load is supported.
    require(not any(name.endswith('.wiggle_bones') or name == 'wiggle_bones' for name in sys.modules),
            'A partially loaded or incompatible Wiggle package already exists; no automatic replacement.')
    enum_ids = {item[0] for item in ops.rna_prop_repo_enum_valid_only_itemf(None, bpy.context) if item is not None}
    local = list(ops.repo_iter_valid_only(bpy.context, exclude_remote=True, exclude_system=True))
    local = [repo for repo in local if repo.module in enum_ids]
    require(local, 'No enabled native local user extension repository exists; repositories will not be changed.')
    installed = []
    for repo in local:
        package = Path(repo.directory) / 'wiggle_bones'
        if package.exists():
            official_files(package, adapter)
            installed.append(repo)
    require(len(installed) <= 1, 'The official Wiggle package exists in multiple local repositories.')
    if installed:
        repo = installed[0]
        return {'operation': 'enable_existing', 'repo': repo, 'module': 'bl_ext.' + repo.module + '.wiggle_bones'}
    preferences = bpy.context.preferences.extensions
    index = preferences.active_repo
    active = preferences.repos[index] if 0 <= index < len(preferences.repos) else None
    selected = next((repo for repo in local if active == repo), None)
    selection_reason = 'active_local_repository'
    if selected is None:
        # The active preference may be a remote catalogue. Use only Blender's
        # uniquely proven standard user repository, not a development directory
        # or a local repository selected by its display name/order.
        user_root = bpy.utils.user_resource('EXTENSIONS')
        default_path = (Path(user_root) / 'user_default').resolve() if user_root else None
        defaults = [repo for repo in local
                    if repo.module == 'user_default' and repo.source == 'USER'
                    and repo.enabled and not repo.use_remote_url
                    and not repo.use_custom_directory and default_path is not None
                    and Path(repo.directory).resolve() == default_path]
        if len(defaults) == 1:
            aliases = [repo for repo in repositories if Path(repo.directory).resolve() == default_path]
            require(len(aliases) == 1, 'The standard user repository has ambiguous directory aliases.')
            selected = defaults[0]
            selection_reason = 'verified_standard_user_default'
        else:
            require(len(local) == 1, 'Select the intended existing local repository before installation; selection is ambiguous.')
            selected = local[0]
            selection_reason = 'only_valid_local_repository'
    return {'operation': 'install_official', 'repo': selected, 'module': 'bl_ext.' + selected.module + '.wiggle_bones',
            'selection_reason': selection_reason,
            'active_repo_index': index, 'active_repo_module': active.module if active is not None else None,
            'local_repositories': [{key: getattr(repo, key) for key in
                ('module', 'source', 'enabled', 'use_remote_url', 'use_custom_directory', 'directory')}
                for repo in local]}


def restore_editor(area, previous_editor):
    area.type = previous_editor['type']
    if previous_editor['ui_type']:
        area.ui_type = previous_editor['ui_type']
    require(area.type == previous_editor['type'] and area.ui_type == previous_editor['ui_type'],
            'The explicitly observed previous editor could not be restored exactly.')


def run(*, previous_editor, approved_official_install=False):
    facts = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'phase': 'preflight', 'status': 'starting', 'saved': False, 'simulation_baked': False,
        'preview_started': False, 'artist_opened': False, 'installer_rollback': 'not attempted'}
    area = None
    source = None
    modules = None
    metadata_before = None
    identity_before = None
    protection = None
    legacy = None
    began = time.perf_counter()
    try:
        require(approved_official_install is True, 'Fresh official Wiggle 1.1.2 install approval must be supplied explicitly.')
        require(not bpy.app.background and bpy.context.window is not None
                and bpy.context.area is not None and bpy.context.area.type == 'CONSOLE',
                'Run only in the coordinated artist X native Python Console.')
        require(tuple(bpy.app.version[:2]) == (5, 1), 'This live plan is for the observed Blender 5.1 artist runtime.')
        require(Path(bpy.data.filepath).resolve() == ARTIST, 'The current artist filepath must be exactly X.blend.')
        require(bpy.context.mode in {'OBJECT', 'POSE'}, 'Finish the current Edit/Paint operation before live integration.')
        require(isinstance(previous_editor, dict) and set(previous_editor) == {'type', 'ui_type'}
            and all(isinstance(value, str) and value for value in previous_editor.values())
            and previous_editor['type'] != 'CONSOLE', 'Supply the actually observed previous editor type and ui_type.')
        area = bpy.context.area
        modules = runtime()
        addon = modules['addon']
        require(not addon.ADDON_REFRESH_PENDING and not bpy.app.timers.is_registered(addon._reload_addon_deferred),
                'An add-on refresh is already pending.')
        no_live_preview(modules)
        legacy = legacy_snapshot(modules)
        facts['automatic_refresh_plan_before'] = automatic_refresh_plan()
        require(ARCHIVE.is_file() and sha256(ARCHIVE) == ARCHIVE_SHA256, 'The approved official Wiggle archive hash differs.')
        plan = extension_plan(modules)
        source = find_source(modules['hair_bones_rig'])
        hair = modules['hair_bones_rig']
        record = hair._read_records(source)
        armature = source.get(hair.RIG_KEY)
        require(isinstance(armature, bpy.types.Object) and armature.type == 'ARMATURE',
                'The authoritative native Hair armature is missing.')
        hair._validate_owned(source, armature, record, hair._mesh_snapshot(source))
        helpers = read_helpers(modules)
        registry, profiles, lifecycle = (modules[key] for key in
            ('hair_strand_registry', 'hair_motion_profiles', 'hair_motion_lifecycle'))
        metadata_before = {key: (key in source, source.get(key))
            for key in (registry.REGISTRY_KEY, profiles.PROFILE_KEY)}
        identity_before = lifecycle.snapshot(source)
        selection = selection_snapshot()
        pose = full_pose(modules, helpers)
        asset = helpers.asset_fingerprint(source)
        display = display_snapshot(modules)
        texts = text_snapshot(modules['hair_wiggle_adapter'])
        protection = (helpers, asset, pose, selection, display, texts)
        facts.update(runtime=bpy.app.version_string, installed_source=str(modules['installed_source']),
            installed_init_sha256=sha256(modules['installed_source']),
            addon_before=list(addon.bl_info['version']), artist=str(ARTIST), source=source.name,
            source_uid=EXPECTED_UID, artist_disk_before=sha256(ARTIST),
            archive=str(ARCHIVE), archive_sha256=ARCHIVE_SHA256,
            reader_source=str(DIRECTORY / 'validate_real_hair_preview.py'), reader_sha256=READERS_SHA256,
            extension_plan={'operation': plan['operation'], 'repo_module': plan['repo'].module,
                            'directory': plan['repo'].directory, 'module': plan['module'],
                            **{key: plan[key] for key in ('selection_reason', 'active_repo_index',
                                'active_repo_module', 'local_repositories') if key in plan}},
            observed_previous_editor=previous_editor, initial_asset=asset, selection_before=selection,
            frame_before=list(pose['frame']), checks={})

        def check(label):
            helpers.adapter = modules['hair_wiggle_adapter']
            check_legacy_preserved(legacy, modules)
            current = helpers.asset_fingerprint(source)
            require(current['sha256'] == asset['sha256'] and current['portable_sha256'] == asset['portable_sha256'],
                    'Raw artist geometry/Rest/weights/UV/keys/actions/material relationships changed: ' + label)
            require(selection_snapshot() == selection, 'Artist selection/context changed: ' + label)
            require(display_snapshot(modules) == display, 'Artist bone display/constraints/locks/shapes changed: ' + label)
            new_texts = check_texts(texts, source, modules)
            facts['checks'][label] = {'asset_sha256': current['sha256'],
                'portable_sha256': current['portable_sha256'], 'raw_exact': True,
                'selection_exact': True, 'display_exact': True, 'new_owned_texts': new_texts,
                'legacy_settings_exact': legacy is not None,
                'pose': check_pose(pose, modules)}
            no_live_preview(modules)
            require(Path(bpy.data.filepath).resolve() == ARTIST, 'The live artist filepath changed.')

        stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        recovery = DIRECTORY / ('X_before_hair_motion_' + stamp + '.blend')
        require(not recovery.exists() and recovery.resolve() != ARTIST, 'The recovery copy path must be independent and new.')
        facts['phase'] = 'save_independent_recovery'
        result = bpy.ops.wm.save_as_mainfile(filepath=str(recovery), copy=True, check_existing=False)
        require(result == {'FINISHED'} and recovery.is_file(), 'Independent native recovery save did not finish.')
        require(sha256(ARTIST) == facts['artist_disk_before'], 'Saving the recovery copy changed the artist disk file.')
        facts['recovery'] = {'path': str(recovery), 'sha256': sha256(recovery), 'native_result': sorted(result)}
        check('after_recovery')

        facts['phase'] = 'refresh_character_designer'
        addon._reload_addon_deferred()
        modules = runtime()
        addon = modules['addon']
        require(tuple(addon.bl_info['version']) == VERSION and not addon.ADDON_REFRESH_LAST_ERROR,
                'Refresh did not load the deployed Character Designer 0.76.1: ' + addon.ADDON_REFRESH_LAST_ERROR)
        addon._validate_registration_integrity()
        facts['automatic_refresh_plan_after'] = automatic_refresh_plan()
        check('after_refresh')

        facts['phase'] = 'install_or_enable_official_wiggle'
        import addon_utils
        if legacy is not None:
            backup = DIRECTORY / ('Wiggle2_inactive_settings_' + stamp + '.json')
            with backup.open('x', encoding='utf8') as stream:
                json.dump(legacy_serialized(legacy), stream, ensure_ascii=False, indent=2, allow_nan=False)
            facts['legacy_upgrade'] = {'module': 'wiggle_2', 'version': [2, 2, 4],
                'source_sha256': LEGACY_SHA256, 'settings_backup': str(backup),
                'settings_backup_sha256': sha256(backup), 'automatic_conversion': False,
                'old_file_retained': True, 'inactive': True}
            errors = []
            addon_utils.disable('wiggle_2', default_set=True, handle_error=errors.append)
            require(not errors and 'wiggle_2' not in bpy.context.preferences.addons,
                    'Native legacy Wiggle disable did not finish: ' + '; '.join(map(str, errors)))
            require(all(function not in collection for collection, function in legacy['handlers']),
                    'Legacy Wiggle callbacks remain registered after native disable.')
            require(not any(getattr(value, 'is_registered', False)
                for value in vars(legacy['module']).values()
                if isinstance(value, type) and value.__module__ == 'wiggle_2'),
                'Legacy Wiggle classes remain registered after native disable.')
            facts['legacy_upgrade']['native_disable_verified'] = True
        plan = extension_plan(modules)
        if plan['operation'] == 'install_official':
            result = bpy.ops.extensions.package_install_files('EXEC_DEFAULT',
                filepath=str(ARCHIVE), repo=plan['repo'].module, enable_on_install=True)
            facts['native_extension_install_result'] = sorted(result)
            require(result == {'FINISHED'}, 'Blender did not finish the official native local extension installation.')
        else:
            facts['native_extension_install_result'] = 'skipped_' + plan['operation']
        errors = []
        enabled = sys.modules.get(plan['module'])
        if enabled is not None and getattr(enabled, '__addon_enabled__', False):
            require(plan['module'] in bpy.context.preferences.addons,
                    'The already enabled official extension has no persistent preference entry.')
            facts['native_extension_enable_result'] = 'already_enabled_preserved'
        else:
            enabled = addon_utils.enable(plan['module'], default_set=True, persistent=True, handle_error=errors.append)
            facts['native_extension_enable_result'] = 'native_enable'
        require(enabled is not None and not errors, 'Native Wiggle enable failed: ' + '; '.join(map(str, errors)))
        official_files(Path(enabled.__file__).resolve().parent, modules['hair_wiggle_adapter'])
        backend = modules['hair_wiggle_adapter']._backend()
        require(backend['name'] == plan['module'], 'The native installed backend module differs from its repository identity.')
        facts['backend'] = {'module': backend['name'], 'version': '1.1.2', 'official_hashes_exact': True}
        check_legacy_preserved(legacy, modules)
        if legacy is not None:
            facts['legacy_upgrade']['inactive_raw_backing_exact_after_register'] = True
            facts['legacy_upgrade']['top_level_values_and_presence_exact'] = True
        check('after_official_install_enable')
        result = bpy.ops.wm.save_userpref()
        require(result == {'FINISHED'}, 'Native extension preferences were not saved.')
        facts['preferences_save_result'] = sorted(result)
        check('after_preferences_save')

        facts['phase'] = 'initialize_or_reconcile_hair_configuration'
        registry, profiles, lifecycle = (modules[key] for key in
            ('hair_strand_registry', 'hair_motion_profiles', 'hair_motion_lifecycle'))
        data = registry.reconcile(source) if metadata_before[registry.REGISTRY_KEY][0] else registry.initialize(source)
        if metadata_before[profiles.PROFILE_KEY][0]:
            record = profiles.reconcile(source, registry=data)
        else:
            profiles.initialize(source, registry=data)
            record = profiles.assign_suggested_groups(source, registry=data)
        lifecycle.claim_bound(source, strict_registry=True)
        require(data['source_uid'] == EXPECTED_UID, 'Hair source identity changed during configuration.')
        require(registry.read(source, validate=True) == data, 'Final native Hair strand proof differs.')
        require(profiles.read(source, registry=data) == record, 'Final Hair motion configuration differs.')
        facts['configuration'] = {'strands': len(data['strands']),
            'paired_strands': sum(bool(item['mirror_id']) for item in data['strands']),
            'center_strands': sum(item['side'] == 'C' for item in data['strands']),
            'groups': {group: sum(item['group'] == group for item in record['strands'].values()) for group in profiles.GROUPS},
            'source_metadata_keys': sorted(helpers.ALLOWED_METADATA), 'automatic_ui_highlight': False}
        check('after_configuration')

        facts['phase'] = 'restore_observed_editor'
        restore_editor(area, previous_editor)
        check('after_editor_restore')
        facts['phase'] = 'save_artist'
        result = bpy.ops.wm.save_mainfile()
        facts['artist_save_result'] = sorted(result)
        require(result == {'FINISHED'}, 'Native artist save did not finish.')
        facts['saved'] = True
        facts['artist_disk_after'] = sha256(ARTIST)
        facts['phase'] = 'validate_artist_save'
        check('after_artist_save')
        facts.update(status='passed', phase='complete', addon_after=list(addon.bl_info['version']),
            artist_disk_after=sha256(ARTIST), selection_after=selection_snapshot(),
            frame_after=[bpy.context.scene.frame_current, bpy.context.scene.frame_subframe])
    except Exception as exc:
        facts.update(status='failed_after_save' if facts['saved'] else 'failed',
            failure_phase=facts['phase'], error=str(exc), traceback=traceback.format_exc())
        if facts['saved']:
            # FINISHED means the owned metadata is already on disk. Rolling it
            # back only in memory would produce two different configurations.
            # Retain that result and recovery; never implicitly resave/reopen.
            facts['metadata_rollback'] = 'not attempted after finished artist save'
            facts['saved_configuration_retained'] = True
            facts['followup_required'] = 'Review post-save validation failure and recovery before any correction; no complete rollback is claimed.'
            try:
                facts['artist_disk_after'] = sha256(ARTIST)
            except Exception as disk_error:
                facts['artist_disk_hash_error'] = str(disk_error)
        elif source is not None and metadata_before is not None and identity_before is not None:
            try:
                for key, (present, value) in metadata_before.items():
                    if present:
                        source[key] = value
                    elif key in source:
                        del source[key]
                modules['hair_motion_lifecycle'].restore(source, identity_before)
                facts['metadata_rollback'] = 'complete'
                if protection is not None and 'check' in locals():
                    check('after_metadata_rollback')
            except Exception as rollback:
                facts['metadata_rollback_error'] = str(rollback)
        facts['installer_rollback'] = 'not attempted; native installation/preferences remain for review'
        if area is not None:
            try:
                restore_editor(area, previous_editor)
                facts['editor_restored_after_failure'] = True
            except Exception as editor_error:
                facts['editor_restore_error'] = str(editor_error)
    finally:
        facts['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        facts['elapsed_seconds'] = time.perf_counter() - began
        try:
            write_report(facts)
        except Exception as report_error:
            facts['report_write_error'] = str(report_error)
        print('LIVE_HAIR_INSTALL_REFRESH_CONFIG_SAVE', json.dumps({key: facts.get(key)
            for key in ('status', 'phase', 'saved', 'error', 'report_path', 'report_write_error',
                        'elapsed_seconds')}, ensure_ascii=False), flush=True)
    return facts
