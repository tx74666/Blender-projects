"""Explicit tiny factory-only native registration proof; never load an artist file."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback

import bpy
import addon_utils
from mathutils import Matrix, Vector, Quaternion

sys.dont_write_bytecode = True
DIRECTORY = Path(__file__).resolve().parent
LEGACY = Path('C:/Users/Randy/AppData/Roaming/Blender Foundation/Blender/5.1/scripts/addons/wiggle_2.py')
LEGACY_SHA = '7333687ae3b6fd20feae8afda649faed1d99bc7b98e92622a8993c09061deac1'
OFFICIAL = DIRECTORY / 'backend' / 'wiggle_bones'
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
REPORT = DIRECTORY / ('wiggle_legacy_transition_51_' + STAMP + '.json')
HANDLERS = {
    'frame_change_pre': 'wiggle_pre', 'frame_change_post': 'wiggle_post',
    'render_pre': 'wiggle_render_pre', 'render_post': 'wiggle_render_post',
    'render_cancel': 'wiggle_render_cancel', 'load_post': 'wiggle_load',
}
LEGACY_CLASSES = ('WiggleBoneItem', 'WiggleItem', 'WiggleBone', 'WiggleObject', 'WiggleScene',
    'WiggleReset', 'WiggleCopy', 'WiggleSelect', 'WiggleBake', 'WIGGLE_PT_Settings',
    'WIGGLE_PT_Head', 'WIGGLE_PT_Tail', 'WIGGLE_PT_Utilities', 'WIGGLE_PT_Bake')
facts = {'schema': 'cdesigner.wiggle-legacy-native-transition/1', 'started_utc': STAMP,
    'ok': False, 'factory_only': True, 'blender_version': list(bpy.app.version),
    'legacy_path': str(LEGACY), 'official_source': str(OFFICIAL), 'report_path': str(REPORT),
    'forbidden_calls': [], 'errors': [], 'phases': {}}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package_hashes():
    return {str(path.relative_to(OFFICIAL)): digest(path) for path in sorted(OFFICIAL.rglob('*'))
            if path.is_file() and '__pycache__' not in path.parts}


def native(value):
    if isinstance(value, bpy.types.ID):
        return {'id_type': value.bl_rna.identifier, 'name': value.name_full,
                'pointer': value.as_pointer(), 'library': value.library.filepath if value.library else None}
    if isinstance(value, (str, bool, int, float)) or value is None:
        return value
    if isinstance(value, Matrix):
        return [[float(value[row][column]) for column in range(len(value[row]))] for row in range(len(value))]
    if isinstance(value, (Vector, Quaternion)):
        return [float(item) for item in value]
    if hasattr(value, 'items'):
        return {str(key): native(item) for key, item in sorted(value.items())}
    if hasattr(value, 'to_list'):
        return native(value.to_list())
    if isinstance(value, (tuple, list)) or hasattr(value, '__iter__'):
        return [native(item) for item in value]
    raise TypeError('Unproven snapshot value: ' + type(value).__name__)


def raw(owner):
    flat = {}
    for prop in owner.bl_rna.properties:
        if not prop.identifier.startswith('wiggle_'):
            continue
        is_set = owner.is_property_set(prop.identifier)
        # Blender5.1 nullable POINTER getters materialize an unset RNA backing
        # entry even when they return None. Never invoke those snapshot reads.
        value = None if prop.type == 'POINTER' and not is_set else native(getattr(owner, prop.identifier))
        flat[prop.identifier] = {'is_set': is_set, 'value': value}
    group_set = owner.is_property_set('wiggle')
    return {'flat': flat,
            'custom': {key: native(owner[key]) for key in sorted(owner.keys())
                       if key == 'wiggle' or key.startswith('wiggle_')},
            'group_is_set': group_set, 'group_raw': native(owner.wiggle) if group_set else None}


def schemas():
    result = {}
    for owner in (bpy.types.Scene, bpy.types.Object, bpy.types.PoseBone):
        fields = {}
        for prop in owner.bl_rna.properties:
            if prop.identifier != 'wiggle' and not prop.identifier.startswith('wiggle_'):
                continue
            entry = {'type': prop.type}
            if prop.type in {'POINTER', 'COLLECTION'}:
                try:
                    fixed = prop.fixed_type
                    entry['fixed_type'] = fixed.identifier if fixed else None
                    entry['fields'] = sorted(item.identifier for item in fixed.properties) if fixed else []
                except Exception as error:
                    entry['inspection_error'] = type(error).__name__ + ': ' + str(error)
            fields[prop.identifier] = entry
        result[owner.__name__] = fields
    return result


def handler_inventory():
    return {key: [{'module': getattr(item, '__module__', None), 'name': getattr(item, '__name__', None),
                   'identity': id(item)} for item in getattr(bpy.app.handlers, key)] for key in HANDLERS}


def snapshot(scene, armature, bone):
    return {'scene': raw(scene), 'object': raw(armature), 'bone': raw(bone),
        'frame_current': scene.frame_current, 'frame_subframe': scene.frame_subframe,
        'object_world': native(armature.matrix_world), 'bone_basis': native(bone.matrix_basis),
        'scene_pointer': scene.as_pointer(), 'object_pointer': armature.as_pointer(),
        'bone_pointer': bone.as_pointer(), 'filepath': bpy.data.filepath}


def phase(name, scene, armature, bone, legacy, minimal_scene, inactive_bone):
    record = {'snapshot': snapshot(scene, armature, bone), 'schema': schemas(), 'handlers': handler_inventory(),
        'legacy_classes_registered': {key: bool(getattr(getattr(legacy, key), 'is_registered', False)) for key in LEGACY_CLASSES},
        'live_like_minimal_scene': raw(minimal_scene), 'inactive_bone_without_raw_data': raw(inactive_bone)}
    facts['phases'][name] = record
    return record


def load_exact(name, path, package=False):
    spec = importlib.util.spec_from_file_location(name, path,
        submodule_search_locations=[str(path.parent)] if package else None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.__time__ = os.path.getmtime(path)
    require(Path(module.__file__).resolve() == path.resolve(), 'An add-on loaded from an unexpected file.')
    return module


def forbid(module, attribute):
    if not hasattr(module, attribute):
        return
    def forbidden(*_args, **_kwargs):
        facts['forbidden_calls'].append(module.__name__ + '.' + attribute)
        raise RuntimeError('List rebuilding/legacy cleanup is prohibited in this transition proof.')
    setattr(module, attribute, forbidden)


def handler_ownership(module, expected):
    return {key: sum(item is getattr(module, function) for item in getattr(bpy.app.handlers, key)) == expected
            for key, function in HANDLERS.items()}


def main():
    require(bpy.app.version[:2] == (5, 1) and bpy.app.background and bpy.data.filepath == '',
            'Run only native Blender5.1 --background --factory-startup with no .blend argument.')
    require(digest(LEGACY) == LEGACY_SHA, 'The exact existing legacy source hash changed.')
    facts['legacy_sha256_before'] = digest(LEGACY)
    facts['official_hashes_before'] = package_hashes()
    require('version = "1.1.2"' in (OFFICIAL / 'blender_manifest.toml').read_text(encoding='utf8'),
            'The reviewed official source is not1.1.2.')
    require(all(not hasattr(owner, 'wiggle') for owner in (bpy.types.Scene, bpy.types.Object, bpy.types.PoseBone)),
            'Factory startup unexpectedly loaded a Wiggle schema.')
    initial_handlers = handler_inventory()
    legacy = load_exact('wiggle_2', LEGACY)
    errors = []
    enabled = addon_utils.enable('wiggle_2', default_set=False, persistent=False, handle_error=errors.append)
    require(enabled is legacy and not errors, 'Native legacy enable failed: ' + repr(errors))
    forbid(legacy, 'build_list')
    scene = bpy.context.scene
    armature_data = bpy.data.armatures.new('Migration Proof Armature')
    armature = bpy.data.objects.new('Migration Proof Armature', armature_data)
    scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    edited = armature_data.edit_bones.new('Migration Proof Bone')
    edited.head = (0, 0, 0); edited.tail = (0, 0, 1)
    inactive = armature_data.edit_bones.new('Inactive Proof Bone')
    inactive.head = (2, 0, 0); inactive.tail = (2, 0, 1)
    bpy.ops.object.mode_set(mode='OBJECT')
    bone = armature.pose.bones['Migration Proof Bone']
    inactive_bone = armature.pose.bones['Inactive Proof Bone']
    minimal_scene = bpy.data.scenes.new('Live-like Minimal Wiggle Scene')
    minimal_scene.wiggle.is_rendering = False
    collider_mesh = bpy.data.meshes.new('Migration Proof Collider')
    collider = bpy.data.objects.new('Migration Proof Collider', collider_mesh)
    scene.collection.objects.link(collider)
    collection = bpy.data.collections.new('Migration Proof Collider Collection')
    scene.collection.children.link(collection)
    # Seed a future legacy-settings fixture without invoking its list builder.
    # This fixture-only callback suppression ends before every tested native
    # disable/register/read/rollback operation; those sources remain exact.
    original_update = legacy.update_prop
    legacy.update_prop = lambda *_args: None
    try:
        scene.wiggle_enable = True
        armature.wiggle_enable = True; armature.wiggle_mute = False; armature.wiggle_freeze = True
        for key, value in {'wiggle_enable': True, 'wiggle_head': True, 'wiggle_tail': True,
                'wiggle_mass': 1.75, 'wiggle_stiff': 333.25, 'wiggle_stretch': .125,
                'wiggle_damp': .375, 'wiggle_gravity': -2.5, 'wiggle_chain': True,
                'wiggle_collider': collider, 'wiggle_collider_collection': collection,
                'wiggle_wind_ob': collider, 'wiggle_radius': .023}.items():
            setattr(bone, key, value)
    finally:
        legacy.update_prop = original_update
    facts['fixture_seed_callback_suppression_restored_before_transition'] = True
    scene.wiggle.iterations = 7; scene.wiggle.lastframe = 39; scene.wiggle.dt = .03125
    scene.wiggle.loop = False; scene.wiggle.preroll = 13
    entry = scene.wiggle.list.add(); entry.name = armature.name
    entry.list.add().name = bone.name
    object_entry = armature.wiggle.list.add(); object_entry.name = 'Existing Object List'
    object_entry.list.add().name = bone.name
    bone.wiggle.matrix = tuple(float(index) / 4 for index in range(16))
    bone.wiggle.position = (1.25, 2.5, 3.75); bone.wiggle.position_last = (-1, -2, -3)
    bone.wiggle.velocity = (.125, .25, .5); bone.wiggle.collision_ob = collider
    bone.wiggle.collision_col = collection; bone.wiggle.collision_ob_head = collider
    bone.wiggle.collision_normal = (0, 1, 0)
    bone.wiggle['qa_unknown_nested'] = {'message': 'preserve legacy raw', 'numbers': [3, 5, 8]}
    before = phase('legacy_enabled', scene, armature, bone, legacy, minimal_scene, inactive_bone)
    require(before['live_like_minimal_scene']['group_is_set'] and
            before['live_like_minimal_scene']['group_raw'] == {'is_rendering': 0} and
            all(not value['is_set'] for value in before['live_like_minimal_scene']['flat'].values()) and
            not before['inactive_bone_without_raw_data']['group_is_set'] and
            before['inactive_bone_without_raw_data']['custom'] == {} and
            all(not value['is_set'] for value in before['inactive_bone_without_raw_data']['flat'].values()),
            'The live-like inactive fixture is not exact.')
    require(all(handler_ownership(legacy, 1).values()), 'Legacy did not own exactly six expected handlers.')
    facts['isolated_legacy_copy'] = str(DIRECTORY / ('wiggle_transition_' + STAMP + '_legacy.blend'))
    bpy.ops.wm.save_as_mainfile(filepath=facts['isolated_legacy_copy'], copy=True, check_existing=False)
    errors.clear()
    addon_utils.disable('wiggle_2', default_set=False, handle_error=errors.append)
    require(not errors and not legacy.__addon_enabled__, 'Native legacy disable failed: ' + repr(errors))
    disabled = phase('legacy_disabled', scene, armature, bone, legacy, minimal_scene, inactive_bone)
    require(disabled['snapshot'] == before['snapshot'], 'Native legacy disable changed raw metadata, pointers, pose or frame.')
    require(all(handler_ownership(legacy, 0).values()) and disabled['handlers'] == initial_handlers,
            'Native legacy disable did not remove only its six handlers.')
    require(not any(disabled['legacy_classes_registered'].values()), 'A legacy class remained registered.')
    official = load_exact('wiggle_bones', OFFICIAL / '__init__.py', package=True)
    for short in ('wiggle_core', 'properties', 'operators', 'physics_engine'):
        module = sys.modules.get('wiggle_bones.' + short)
        if module:
            forbid(module, 'build_list')
    errors.clear()
    enabled = addon_utils.enable('wiggle_bones', default_set=False, persistent=False, handle_error=errors.append)
    require(enabled is official and not errors, 'Native official enable failed: ' + repr(errors))
    after = phase('official_enabled', scene, armature, bone, legacy, minimal_scene, inactive_bone)
    require(after['snapshot'] == before['snapshot'], 'Official native registration changed existing raw metadata, pointers, pose or frame.')
    require(all(handler_ownership(legacy, 0).values()) and all(handler_ownership(official.physics_engine, 1).values()),
            'Old/new native handlers overlap or are incomplete.')
    require(after['live_like_minimal_scene'] == before['live_like_minimal_scene'] and
        after['inactive_bone_without_raw_data'] == before['inactive_bone_without_raw_data'] and
        minimal_scene.wiggle.enable is False, 'Official registration changed the exact currently observed inactive/raw-minimal legacy case.')
    facts['official_rna_reads'] = {'scene_enable': scene.wiggle.enable, 'object_enable': armature.wiggle.enable,
        'bone_enable': bone.wiggle.enable, 'bone_tail': bone.wiggle.tail, 'bone_mass': bone.wiggle.mass,
        'bone_gravity': bone.wiggle.gravity, 'iterations': scene.wiggle.iterations,
        'scene_list_count': len(scene.wiggle.list), 'object_list_count': len(armature.wiggle.list),
        'collision_object_pointer': bone.wiggle.collision_ob.as_pointer(),
        'collision_collection_pointer': bone.wiggle.collision_col.as_pointer()}
    require(snapshot(scene, armature, bone) == before['snapshot'], 'Reading new official RNA unexpectedly materialized/changed old raw values.')
    facts['isolated_official_copy'] = str(DIRECTORY / ('wiggle_transition_' + STAMP + '_official.blend'))
    bpy.ops.wm.save_as_mainfile(filepath=facts['isolated_official_copy'], copy=True, check_existing=False)
    errors.clear()
    addon_utils.disable('wiggle_bones', default_set=False, handle_error=errors.append)
    require(not errors and not official.__addon_enabled__, 'Official disable failed: ' + repr(errors))
    require(handler_inventory() == initial_handlers, 'Official disable left its handlers or removed unrelated handlers.')
    enabled = addon_utils.enable('wiggle_2', default_set=False, persistent=False, handle_error=errors.append)
    require(enabled is legacy and not errors, 'Legacy rollback native enable failed: ' + repr(errors))
    rollback = phase('legacy_reenabled', scene, armature, bone, legacy, minimal_scene, inactive_bone)
    require(rollback['snapshot'] == before['snapshot'] and rollback['schema'] == before['schema'] and
        rollback['handlers'] == before['handlers'], 'Native rollback did not exactly restore raw data/schema/handler ownership.')
    require(rollback['live_like_minimal_scene'] == before['live_like_minimal_scene'] and
        rollback['inactive_bone_without_raw_data'] == before['inactive_bone_without_raw_data'], 'Rollback changed the exact inactive live-like fixture.')
    require(bone.wiggle_collider == collider and bone.wiggle_collider_collection == collection and
        bone.wiggle.collision_ob == collider and bone.wiggle.collision_col == collection,
        'Native legacy rollback changed existing ID-pointer relationships.')
    facts['legacy_sha256_after'] = digest(LEGACY)
    facts['official_hashes_after'] = package_hashes()
    require(facts['legacy_sha256_after'] == facts['legacy_sha256_before'] and
            facts['official_hashes_after'] == facts['official_hashes_before'], 'An add-on source file was modified.')
    require(not facts['forbidden_calls'], 'A forbidden list rebuild occurred.')
    facts['data_preserved_exact'] = True
    facts['rollback_preserved_exact'] = True
    facts['legacy_handlers_removed_exact'] = True
    facts['live_like_inactive_raw_minimal_preserved_exact'] = True
    facts['official_new_settings_auto_migrated'] = False
    facts['limitations'] = [
        'Factory fixture only: the current live artist scene was never accessed or reloaded.',
        'Native addon_utils registration used the exact official package as a source package; extension ZIP installation/repository preferences are a separate live installer step.',
        'Old top-level wiggle_* fields remain separate raw/RNA values. Official nested enable/tail/mass/gravity defaults are not semantic migration of these legacy settings.',
        'No legacy cleanup, frame change, list rebuild, simulation, user-preference save or solver step occurred.',
        'The two saved .blend copies are independent tiny proof fixtures; no reload was performed.']
    facts['ok'] = True


try:
    main()
except Exception:
    facts['errors'].append(traceback.format_exc())
finally:
    facts['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    REPORT.write_text(json.dumps(facts, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print('WIGGLE_TRANSITION_REPORT', str(REPORT))
    print('WIGGLE_TRANSITION_OK', facts['ok'])
    if not facts['ok']:
        print(facts['errors'][-1])
        raise SystemExit(1)
