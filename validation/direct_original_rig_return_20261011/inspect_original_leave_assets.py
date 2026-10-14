"""Root-launched isolated asset transition diagnosis; no artist save or reload.

Default stops after official Original leave. --through adopt/bake is explicit.
Full raw mesh rows are saved to disk, while stdout reports only changed fields.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import traceback

import bpy

EVIDENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(EVIDENCE))
from validation_preservation import asset_snapshot, changes, digest, identity, mesh_content


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def isolated_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(EVIDENCE) or path.name.lower() == 'x.blend':
        raise ValueError('Input/report must be task validation paths, never artist X.blend.')
    return path


def field_differences(before, after, path=''):
    """Every changed compact component field, including key/list membership."""
    if isinstance(before, dict) and isinstance(after, dict):
        rows = []
        for key in sorted(before.keys() | after.keys()):
            child = path + '/' + str(key).replace('~', '~0').replace('/', '~1')
            if key not in before or key not in after:
                rows.append({'path': child, 'before': before.get(key), 'after': after.get(key),
                             'before_present': key in before, 'after_present': key in after})
            else:
                rows.extend(field_differences(before[key], after[key], child))
        return rows
    if isinstance(before, list) and isinstance(after, list):
        rows = []
        for index in range(max(len(before), len(after))):
            child = path + '/' + str(index)
            if index >= len(before) or index >= len(after):
                rows.append({'path': child,
                             'before': before[index] if index < len(before) else None,
                             'after': after[index] if index < len(after) else None,
                             'before_present': index < len(before), 'after_present': index < len(after)})
            else:
                rows.extend(field_differences(before[index], after[index], child))
        return rows
    return [] if before == after else [{'path': path, 'before': before, 'after': after}]


def skin_objects(scene, rig):
    return sorted((obj for obj in scene.objects if obj.type == 'MESH' and
                   (obj.parent is rig or any(m.type == 'ARMATURE' and m.object is rig
                                            for m in obj.modifiers))), key=lambda o: o.name)


def raw_mesh(obj):
    mesh = obj.data
    groups = {g.index: g.name for g in obj.vertex_groups}
    return {
        'object_id': identity(obj), 'object_pointer': obj.as_pointer(),
        'data_id': identity(mesh), 'data_pointer': mesh.as_pointer(),
        'parent': identity(obj.parent), 'parent_type': obj.parent_type,
        'parent_bone': obj.parent_bone,
        'armature_modifiers': [{'name': m.name, 'object': identity(m.object),
                               'show_viewport': m.show_viewport, 'show_render': m.show_render}
                              for m in obj.modifiers if m.type == 'ARMATURE'],
        'vertex_groups': [{'index': g.index, 'name': g.name, 'lock_weight': g.lock_weight}
                          for g in obj.vertex_groups],
        'vertices': [list(v.co) for v in mesh.vertices],
        'edges': [list(e.vertices) for e in mesh.edges],
        'loops': [loop.vertex_index for loop in mesh.loops],
        'polygons': [[p.loop_start, p.loop_total, p.material_index, bool(p.use_smooth)]
                     for p in mesh.polygons],
        'weights_ordered': [[[g.group, groups.get(g.group), float(g.weight)] for g in v.groups]
                            for v in mesh.vertices],
        'materials': [identity(m) for m in mesh.materials],
        'material_slots': [[slot.link, identity(slot.material)] for slot in obj.material_slots],
        'forearm_twist_exact_record': obj.get('character_designer_forearm_twist_v1'),
        'shape_keys': [{'name': key.name, 'relative': key.relative_key.name,
                        'vertex_group': key.vertex_group,
                        'slider_min': key.slider_min, 'slider_max': key.slider_max,
                        'geometry': [list(v.co) for v in key.data]}
                       for key in mesh.shape_keys.key_blocks] if mesh.shape_keys else [],
    }


def capture(scene, rig, ua):
    skins = skin_objects(scene, rig)
    return {'frame': scene.frame_current + scene.frame_subframe,
            'original_mode_active': bool(importlib.import_module(
                'character_designer.body_original_mode').active(rig)),
            'rig_data_id': identity(rig.data), 'rig_data_pointer': rig.data.as_pointer(),
            'rest_full': ua._rest_state(rig.data),
            'asset_snapshot': asset_snapshot(scene, rig, ua),
            'mesh_content_full': {obj.name: mesh_content(obj) for obj in skins},
            'mesh_raw_full': {obj.name: raw_mesh(obj) for obj in skins}}


def compare(before, after):
    old, new = before['mesh_raw_full'], after['mesh_raw_full']
    result = {'asset_component_changes': sorted(changes(before['asset_snapshot'], after['asset_snapshot'])),
              'skin_membership_before': sorted(old), 'skin_membership_after': sorted(new),
              'mesh_content_field_differences': field_differences(
                  before['mesh_content_full'], after['mesh_content_full'], '/mesh_content_full'),
              'rest_field_differences': field_differences(before['rest_full'], after['rest_full'], '/rest_full'),
              'mesh_raw_components': {}}
    for name in sorted(old.keys() & new.keys()):
        first, second = old[name], new[name]
        changed_fields = sorted(key for key in first.keys() | second.keys()
                                if first.get(key) != second.get(key))
        detail = {'changed_fields': changed_fields,
                  'component_before_sha256': {key: digest(value) for key, value in first.items()},
                  'component_after_sha256': {key: digest(value) for key, value in second.items()},
                  'immutable_coordinates_exact': first['vertices'] == second['vertices'],
                  'shape_key_geometry_and_metadata_exact': first['shape_keys'] == second['shape_keys'],
                  'topology_exact': all(first[k] == second[k] for k in ('edges', 'loops', 'polygons')),
                  'material_assignments_exact': all(first[k] == second[k] for k in ('materials', 'material_slots')),
                  'weight_order_changed_vertices': [], 'weight_values_changed_vertices': []}
        a, b = first['weights_ordered'], second['weights_ordered']
        for index in range(max(len(a), len(b))):
            left, right = a[index] if index < len(a) else None, b[index] if index < len(b) else None
            if left != right:
                detail['weight_order_changed_vertices'].append(index)
            if left is None or right is None or sorted(left) != sorted(right):
                detail['weight_values_changed_vertices'].append(index)
        detail['weights_equal_by_group_identity_and_exact_value'] = not detail['weight_values_changed_vertices']
        # Full source rows are retained in phases; every changed component has
        # a JSON Pointer here. Order-only claims require exact per-group proof.
        detail['changed_component_paths'] = [f'/mesh_raw_full/{name}/{key}' for key in changed_fields]
        result['mesh_raw_components'][name] = detail
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--addon-root', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--through', choices=('leave', 'adopt', 'bake'), default='leave')
    parser.add_argument('--workspace')
    parser.add_argument('--packet')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source, output = isolated_path(args.input), isolated_path(args.report)
    if source == output:
        raise ValueError('Report must differ from backup input.')
    input_hash = file_hash(source)
    report = {'schema': 'x.validation.original-leave-asset-transition/1', 'completed': False,
              'input': str(source), 'input_sha256': input_hash, 'through': args.through,
              'scope': 'Disposable Blender process and full backup only. No artist or Unity mutation; no saves.',
              'phases': {}, 'transitions': {}}
    try:
        addon_root = Path(args.addon_root).resolve()
        sys.path.insert(0, str(addon_root))
        cd = importlib.import_module('character_designer')
        if not Path(cd.__file__).resolve().is_relative_to(addon_root):
            raise RuntimeError('Unexpected runtime root.')
        cd.register()
        ua = importlib.import_module('character_designer.unity_animation')
        original = importlib.import_module('character_designer.body_original_mode')
        report['runtime'] = {'blender': bpy.app.version_string,
                             'addon': list(cd.bl_info['version']), 'path': cd.__file__,
                             'source_sha256': {m.__name__: file_hash(m.__file__) for m in (cd, ua, original)}}
        bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False, load_ui=False)
        scene, rig = bpy.data.scenes.get('Scene'), bpy.data.objects.get('CoshaRig')
        if not scene or not rig or rig.name not in scene.objects:
            raise RuntimeError('Backup lacks original Scene/CoshaRig.')
        bpy.context.window.scene = scene
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        rig.hide_set(False)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.context.view_layer.update()
        report['phases']['before'] = capture(scene, rig, ua)
        if not original.active(rig):
            raise RuntimeError('Baseline must have original Rig in Original mode.')
        original._validate_session_rest(rig)
        report['original_rest_validation_passed'] = True
        report['phases']['after_validate'] = capture(scene, rig, ua)
        report['transitions']['validate'] = compare(report['phases']['before'], report['phases']['after_validate'])
        if not original.leave(bpy.context, rig):
            raise RuntimeError('Official Original leave did not complete.')
        bpy.context.view_layer.update()
        report['phases']['after_leave'] = capture(scene, rig, ua)
        report['transitions']['leave'] = compare(report['phases']['before'], report['phases']['after_leave'])
        if args.through != 'leave':
            if not args.workspace:
                raise ValueError('--workspace is required for adopt/bake.')
            worklist = importlib.import_module('character_designer.animation_worklist')
            target = importlib.import_module('character_designer.animation_worklist_target')
            saved = worklist.connect(bpy.context, args.workspace)
            target.adopt_main_rig(bpy.context)
            bpy.context.view_layer.update()
            report['phases']['after_adopt'] = capture(scene, rig, ua)
            report['transitions']['adopt'] = compare(report['phases']['after_leave'], report['phases']['after_adopt'])
            if args.through == 'bake':
                if not args.packet:
                    raise ValueError('--packet is required for bake.')
                datafiles = Path(bpy.utils.user_resource('DATAFILES', create=True)).resolve()
                if not datafiles.is_relative_to(EVIDENCE) and datafiles != EVIDENCE.parent / 'dr24cache':
                    raise RuntimeError('Baking requires the isolated task-owned source cache.')
                report['packet_sha256'] = file_hash(args.packet)
                ready = [row for row in saved.catalog if row.ready]
                if len(ready) != 1:
                    raise RuntimeError('Expected exactly one ready clip.')
                item = worklist.add(bpy.context, ready[0].clip_key)
                worklist.activate(bpy.context, item.item_id, 'CUSTOM')
                bpy.context.view_layer.update()
                report['phases']['after_bake'] = capture(scene, rig, ua)
                report['transitions']['bake'] = compare(report['phases']['after_adopt'], report['phases']['after_bake'])
        report['completed'] = True
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
    finally:
        report['input_file_unchanged'] = file_hash(source) == input_hash
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        print(json.dumps({'completed': report['completed'], 'report': str(output),
                          'error': report.get('error'), 'transitions': {
                              name: {'asset_changes': row['asset_component_changes'],
                                     'mesh_field_differences': row['mesh_content_field_differences'],
                                     'raw_changed_fields': {mesh: info['changed_fields'] for mesh, info in
                                                           row['mesh_raw_components'].items()}}
                              for name, row in report['transitions'].items()}}))
    if not report['completed'] or not report['input_file_unchanged']:
        raise SystemExit(1)


main()
