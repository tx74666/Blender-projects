"""Prove a CD .23 -> .24 in-process refresh on a disposable full-artist backup.

Do not run against X.blend. Captures native RNA before unregister, verifies
natural retained Scene data, then restores only missing transient WM values.
No blanket PropertyGroup rewrite, Scene switch, frame evaluation or file reload
is permitted during the actual unregister/import/register operation.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import traceback

import addon_utils
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validation_preservation import asset_snapshot, changes, digest

EVIDENCE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(EVIDENCE) or path.name.lower() == 'x.blend':
        raise ValueError('Refresh test input/output must be disposable files within ' + str(EVIDENCE))
    return path


def id_description(value):
    return {'kind': 'ID', 'type': value.bl_rna.identifier, 'name': value.name,
            'library': value.library.filepath if value.library else None}


def public(value):
    if isinstance(value, bpy.types.ID):
        return id_description(value)
    if isinstance(value, dict):
        return {key: public(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [public(item) for item in value]
    if isinstance(value, set):
        return sorted(value)
    return value


def pg_capture(pg):
    result = {}
    for prop in pg.bl_rna.properties:
        name = prop.identifier
        if name == 'rna_type' or (prop.is_readonly and prop.type not in {'COLLECTION', 'POINTER'}):
            continue
        value = getattr(pg, name)
        if prop.type == 'COLLECTION':
            result[name] = {'kind': 'COLLECTION', 'items': [pg_capture(item) for item in value]}
        elif prop.type == 'POINTER' and isinstance(value, bpy.types.PropertyGroup):
            result[name] = {'kind': 'GROUP', 'fields': pg_capture(value)}
        elif prop.type == 'POINTER':
            result[name] = value
        elif getattr(prop, 'is_array', False):
            result[name] = list(value)
        elif isinstance(value, set):
            result[name] = set(value)
        else:
            result[name] = value
    return result


def restore_only_changed_wm(pg, saved, prefix, restored):
    """Restore one changed scalar/ID pointer at a time; never rewrite collections."""
    current = pg_capture(pg)
    for name, expected in saved.items():
        if name not in current:
            raise AssertionError('The refreshed WM schema removed ' + prefix + '.' + name)
        if public(current[name]) == public(expected):
            continue
        prop = pg.bl_rna.properties[name]
        if prop.type == 'COLLECTION':
            raise AssertionError('Transient WM collection was lost; no blind callback rewrite: ' + prefix + '.' + name)
        if isinstance(expected, dict) and expected.get('kind') == 'GROUP':
            restore_only_changed_wm(getattr(pg, name), expected['fields'], prefix + '.' + name, restored)
        else:
            setattr(pg, name, expected)
            restored.append(prefix + '.' + name)


def scene_capture():
    return {scene.name: {'setup': pg_capture(scene.character_designer_setup),
                         'worklist': pg_capture(scene.character_designer_animation_worklist)}
            for scene in bpy.data.scenes}


def wm_capture(cd):
    return {name: pg_capture(getattr(bpy.context.window_manager, name))
            for name, _cls in cd._WINDOW_MANAGER_POINTER_TYPES}


def native_context():
    window = bpy.context.window
    active = bpy.context.view_layer.objects.active
    active_action = active.animation_data.action if active and active.animation_data else None
    slot = active.animation_data.action_slot if active and active.animation_data else None
    return {'scene': bpy.context.scene.name, 'view_layer': bpy.context.view_layer.name,
            'workspace': window.workspace.name, 'frame': bpy.context.scene.frame_current_final,
            'active': active.name if active else None, 'mode': bpy.context.mode,
            'selected': sorted(obj.name for obj in bpy.context.selected_objects),
            'action': public(active_action), 'action_slot': slot.handle if slot else None,
            'selected_pose_bones': sorted(pb.name for pb in (bpy.context.selected_pose_bones or [])),
            'active_bone': active.data.bones.active.name if active and active.type == 'ARMATURE' and active.data.bones.active else None,
            'auto_key': bpy.context.scene.tool_settings.use_keyframe_insert_auto}


def native_pose_channels():
    return {rig.name: {pb.name: {'mode': pb.rotation_mode,
             **{field: list(getattr(pb, field)) for field in
                ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')}}
            for pb in rig.pose.bones}
            for rig in bpy.data.objects if rig.type == 'ARMATURE' and rig.name in {'CoshaRig', 'CoshaRig.001'}}


def assets(ua):
    result = {}
    for name in ('CoshaRig', 'CoshaRig.001'):
        rig = bpy.data.objects.get(name)
        if rig:
            scene = next((scene for scene in bpy.data.scenes if scene.objects.get(name) is rig), None)
            if scene:
                result[name] = asset_snapshot(scene, rig, ua)
    return result


def mount(root):
    root = Path(root).resolve()
    # Add-on modules from the last tree must never shadow the pinned target.
    sys.path[:] = [str(root)] + [path for path in sys.path if Path(path or '.').resolve() != root]
    importlib.invalidate_caches()
    module = importlib.import_module('character_designer')
    if not Path(module.__file__).resolve().is_relative_to(root):
        raise RuntimeError('Unexpected Character Designer tree: ' + module.__file__)
    enabled = addon_utils.enable('character_designer', default_set=False, persistent=False)
    if enabled is None or not getattr(module, '__addon_enabled__', False):
        raise RuntimeError('addon_utils.enable did not activate the pinned runtime.')
    return enabled


def differences(before, after, prefix=''):
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in before.keys() | after.keys():
            if key not in before or key not in after:
                result.append(prefix + '.' + key)
            else:
                result.extend(differences(before[key], after[key], prefix + '.' + key))
        return result
    return [] if public(before) == public(after) else [prefix]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--old-addon-root', required=True)
    parser.add_argument('--new-addon-root', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    input_path, report_path = safe_path(args.input), safe_path(args.report)
    input_hash = sha(input_path)
    report = {'schema': 'x.validation.addon-refresh-isolated/1', 'completed': False,
              'input': str(input_path), 'input_sha256': input_hash,
              'scope': 'Disposable process and backup only; no artist reload or mutation.'}
    try:
        old = mount(args.old_addon_root)
        if tuple(old.bl_info['version']) != (0, 77, 23):
            raise RuntimeError('Expected frozen CD .23 old runtime.')
        bpy.ops.wm.open_mainfile(filepath=str(input_path), use_scripts=False, load_ui=True)
        old_ua = importlib.import_module('character_designer.unity_animation')
        # Saved files omit SKIP_SAVE WM fields. Seed meaningful representative
        # current selections on the disposable backup only, then capture them.
        # Existing persisted Scene setup/worklists are never rewritten.
        wm_animation = bpy.context.window_manager.character_designer_animation
        wm_animation.target = bpy.data.objects.get('CoshaRig.001') or bpy.data.objects.get('CoshaRig')
        wm_animation.source = bpy.data.objects.get('CoshaRig')
        wm_animation.prompt = 'Refresh smoke: retain the current motion description.'
        wm_animation.seed = 173
        wm_animation.duration = 3.5
        wm_animation.start_frame = 19
        wm_animation.show_setup = True
        wm_animation.show_unity_files = True
        before_scene, before_wm = scene_capture(), wm_capture(old)
        before_context, before_pose = native_context(), native_pose_channels()
        before_assets = assets(old_ua)
        report['old_runtime'] = {'version': list(old.bl_info['version']), 'path': old.__file__, 'init_sha256': sha(old.__file__)}
        report['before_context'] = before_context
        report['before_scenes'] = public(before_scene)
        report['before_wm'] = public(before_wm)
        report['before_assets'] = before_assets
        scene_raw_before = {scene.name: sorted(key for key in scene.keys() if key.startswith('character_designer'))
                            for scene in bpy.data.scenes}
        # This is the candidate real-session refresh sequence. Native artist IDs
        # remain in the same process; no open_mainfile call occurs after capture.
        addon_utils.disable('character_designer', default_set=False)
        if getattr(old, '__addon_enabled__', False):
            raise RuntimeError('addon_utils.disable did not disable the old runtime.')
        report['scene_property_storage_after_unregister'] = {
            scene.name: sorted(key for key in scene.keys() if key.startswith('character_designer'))
            for scene in bpy.data.scenes}
        report['scene_idproperty_storage_retained'] = scene_raw_before == report['scene_property_storage_after_unregister']
        removed = sorted(name for name in tuple(sys.modules)
                         if name == 'character_designer' or name.startswith('character_designer.'))
        for name in removed:
            del sys.modules[name]
        new = mount(args.new_addon_root)
        if tuple(new.bl_info['version']) != (0, 77, 24):
            raise RuntimeError('Expected frozen CD .24 target runtime.')
        new._validate_registration_integrity()
        report['new_runtime'] = {'version': list(new.bl_info['version']), 'path': new.__file__, 'init_sha256': sha(new.__file__)}
        report['removed_old_module_count'] = len(removed)
        after_scene = scene_capture()
        # Additional .24 schema defaults are valid; every old persistent field
        # must still exist with exactly the same ID pointer or value.
        retained_differences = []
        for scene_name, old_fields in before_scene.items():
            current = after_scene.get(scene_name)
            if current is None:
                retained_differences.append(scene_name)
                continue
            for kind, values in old_fields.items():
                projected = {key: current[kind].get(key) for key in values}
                retained_differences.extend(differences(public(values), public(projected), scene_name + '.' + kind))
        report['persistent_scene_field_differences'] = retained_differences
        if retained_differences:
            raise AssertionError('Persistent Scene state changed during refresh: ' + ', '.join(retained_differences[:20]))
        naturally_retained = wm_capture(new)
        report['natural_wm_differences'] = differences(public(before_wm), public(naturally_retained), 'WM')
        # Preserve only values whose RNA disappeared with the old runtime. Do
        # not invoke callbacks for values that Blender already retained.
        restored = []
        for group, fields in before_wm.items():
            restore_only_changed_wm(getattr(bpy.context.window_manager, group), fields, group, restored)
        report['explicitly_restored_transient_wm_fields'] = restored
        after_wm = wm_capture(new)
        for group, fields in before_wm.items():
            projected = {key: after_wm[group].get(key) for key in fields}
            if public(projected) != public(fields):
                raise AssertionError('WM values could not be preserved: ' + group)
        report['after_context'] = native_context()
        if report['after_context'] != before_context:
            raise AssertionError('Refresh changed active Scene, frame, mode, selection, Action or editor workspace.')
        if native_pose_channels() != before_pose:
            raise AssertionError('Refresh or changed-WM restoration changed artist pose channels.')
        new_ua = importlib.import_module('character_designer.unity_animation')
        after_assets = assets(new_ua)
        for name, prior in before_assets.items():
            if name not in after_assets or changes(prior, after_assets[name]):
                raise AssertionError('Refresh changed original character assets: ' + name)
        report['persistent_scene_setup_worklist_items_catalog_retained'] = True
        report['relevant_wm_values_retained'] = True
        report['active_context_action_pose_preserved'] = True
        report['assets_preserved'] = True
        report['after_scenes'] = public(after_scene)
        report['after_wm'] = public(after_wm)
        report['completed'] = True
    except Exception as exc:
        report['error_type'], report['error'], report['traceback'] = type(exc).__name__, str(exc), traceback.format_exc()
    finally:
        report['input_file_unchanged'] = sha(input_path) == input_hash
        report['completed'] = bool(report['completed'] and report['input_file_unchanged'])
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        print('ADDON_REFRESH_ISOLATED ' + json.dumps({key: report.get(key) for key in
            ('completed', 'error_type', 'error', 'input_file_unchanged',
             'persistent_scene_setup_worklist_items_catalog_retained', 'relevant_wm_values_retained',
             'active_context_action_pose_preserved')}, ensure_ascii=False))
    if not report['completed']:
        raise RuntimeError(report.get('error', 'Refresh smoke did not complete.'))


if __name__ == '__main__':
    main()
