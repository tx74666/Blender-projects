"""Read X, export only active Armature-bound meshes to a temporary folder, reimport.

The loaded source is never saved. No Unity project is opened or written.
"""
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import bpy

sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import character_setup, forearm_twist, unity_export

OUT = Path(__file__).resolve().parent
SOURCE = Path(r'D:\Blender\Projects\Character\X\X.blend')


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_digest():
    h = hashlib.sha256()
    def add(value):
        h.update(repr(value).encode('utf8'))
    def coordinates(items):
        buffer = array('f', [0]) * (3 * len(items))
        items.foreach_get('co', buffer)
        h.update(buffer.tobytes())
    add((bpy.context.mode, bpy.context.scene.frame_current, bpy.data.filepath,
         bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None))
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        add((obj.name, obj.type, list(map(tuple, obj.matrix_world)), obj.select_get(),
             obj.hide_get() if obj.name in bpy.context.view_layer.objects else None,
             obj.hide_viewport, obj.hide_render, obj.parent.name if obj.parent else None,
             obj.parent_type, obj.parent_bone, obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None))
        for modifier in obj.modifiers:
            add((modifier.name, modifier.type, modifier.show_viewport, modifier.show_render))
            if modifier.type == 'ARMATURE':
                add((modifier.object.name if modifier.object else None, modifier.use_vertex_groups,
                     modifier.use_bone_envelopes, modifier.use_deform_preserve_volume))
        if obj.type == 'ARMATURE':
            add(obj.data.pose_position)
            for bone in obj.pose.bones:
                add((bone.name, list(map(tuple, bone.matrix_basis)), list(map(tuple, bone.bone.matrix_local)),
                     bone.bone.parent.name if bone.bone.parent else None, bone.bone.use_deform,
                     bone.custom_shape.name if bone.custom_shape else None,
                     [(c.name, c.type, c.influence, c.mute) for c in bone.constraints]))
        if obj.type == 'MESH':
            coordinates(obj.data.vertices)
            add([tuple(face.vertices) for face in obj.data.polygons])
            add([(group.name, group.index) for group in obj.vertex_groups])
            add([[(group.group, group.weight) for group in vertex.groups] for vertex in obj.data.vertices])
            if obj.data.shape_keys:
                keys = obj.data.shape_keys
                add((keys.use_relative, keys.animation_data.action.name if keys.animation_data and keys.animation_data.action else None))
                for key in keys.key_blocks:
                    add((key.name, key.value, key.mute, key.relative_key.name, key.vertex_group))
                    coordinates(key.data)
            add([material.name if material else None for material in obj.data.materials])
    for image in bpy.data.images:
        add((image.name, image.filepath, image.file_format, image.source, tuple(image.size)))
    return h.hexdigest()


def parented_to(obj, rig):
    parent = obj.parent
    seen = set()
    while parent and parent not in seen:
        if parent == rig:
            return True
        seen.add(parent)
        parent = parent.parent
    return False


def weight_dicts(obj, mesh, bone_names):
    groups = {g.index: g.name for g in obj.vertex_groups if g.name in bone_names}
    return [{groups[g.group]: float(g.weight) for g in vertex.groups
             if g.group in groups and g.weight > 0} for vertex in mesh.vertices]


def expected_scope(rig):
    rigs = {rig} | {o for o in bpy.context.scene.objects if o.type == 'ARMATURE' and parented_to(o, rig)}
    shapes = {pb.custom_shape for arm in rigs for pb in arm.pose.bones if pb.custom_shape}
    expected, inventory = [], []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or obj in shapes:
            continue
        active = [m for m in obj.modifiers if m.type == 'ARMATURE' and m.object is not None
                  and m.show_viewport and (m.use_vertex_groups or m.use_bone_envelopes)]
        belongs = any(m.object in rigs for m in active)
        if belongs:
            assert all(m.object in rigs for m in active), obj.name + ' uses multiple character rigs'
            expected.append(obj.name)
        inventory.append({'name': obj.name, 'included': belongs, 'parent': obj.parent.name if obj.parent else None,
                          'hidden': obj.hide_get(), 'armatures': [{'name': m.name, 'target': m.object.name if m.object else None,
                            'enabled': m.show_viewport, 'vertex_groups': m.use_vertex_groups, 'envelopes': m.use_bone_envelopes}
                           for m in obj.modifiers if m.type == 'ARMATURE']})
    return sorted(expected), inventory


def main():
    assert Path(bpy.data.filepath).resolve() == SOURCE.resolve()
    source_hash = hash_file(SOURCE)
    character_designer.register()
    rig = bpy.data.objects['CoshaRig']
    body = bpy.data.objects['Cosha']
    expected, inventory = expected_scope(rig)
    assert expected and 'Cosha' in expected
    key_blocks = body.data.shape_keys.key_blocks if body.data.shape_keys else []
    owned = set()
    for side, record in forearm_twist._records(body).items():
        key = forearm_twist._managed_key(body, side, record, repair_name=False)
        if key:
            owned.add(key.name)
    artist_keys = [k.name for k in key_blocks[1:] if k.name not in owned]
    bone_names = {bone.name for bone in rig.data.bones if bone.use_deform}
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=bpy.context.evaluated_depsgraph_get())
    try:
        original_weights = weight_dicts(body, mesh, bone_names)
    finally:
        evaluated.to_mesh_clear()
    report = {'ok': False, 'source': str(SOURCE), 'source_file_hash': source_hash,
              'expected_bound_meshes': expected, 'source_inventory': inventory,
              'source_artist_keys': artist_keys, 'source_runtime_keys_omitted': sorted(owned)}
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cdesigner-X-bound-0572-') as temporary:
        temp = Path(temporary)
        extras = [SimpleNamespace(object=bpy.data.objects[name], enabled=True)
                  for name in ('Hair', 'Dress', 'Jacket') if bpy.data.objects.get(name)]
        config = SimpleNamespace(directory=str(temp / 'Assets' / 'Cosha'), filename='CoshaBound',
                                 asset_id='x-bound-0572-validation', extras=extras)
        original_resource = bpy.utils.user_resource
        backups = temp / 'backups'
        backups.mkdir()
        def local_resource(kind, *, path='', create=False):
            if kind == 'DATAFILES' and path == 'character_designer/export_backups':
                return str(backups)
            return original_resource(kind, path=path, create=create)
        before = source_digest()
        with patch.object(bpy.utils, 'user_resource', local_resource):
            result = unity_export.export_character(bpy.context, rig, config)
        after = source_digest()
        assert before == after, 'Source data changed during export'
        report.update(source_unchanged=True, source_data_digest=before,
                      warnings=result['warnings'], legacy_extra_names=[e.object.name for e in extras])
        manifest = json.loads(Path(result['report_path']).read_text(encoding='utf8'))
        report['export_manifest'] = manifest
        assert sorted(manifest['meshes']) == expected, (manifest['meshes'].keys(), expected)
        assert all(info['skinned'] for info in manifest['meshes'].values())
        for extra in extras:
            if extra.object.name not in expected:
                assert any(extra.object.name in warning and 'skip' in warning.lower() for warning in result['warnings'])
        assert manifest['shape_keys']['Cosha'] == artist_keys
        assert all(not name.startswith(('CTRL_', 'MCH_', 'ORG_', 'ORI_')) for name in manifest['rigs']['CoshaRig'])
        # Everything below operates only on the imported disposable FBX copy.
        character_designer.unregister()
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.preferences.addon_enable(module='io_scene_fbx')
        assert 'FINISHED' in bpy.ops.import_scene.fbx(filepath=result['filepath'])
        meshes = {o.name: o for o in bpy.context.scene.objects if o.type == 'MESH'}
        armatures = {o.name: o for o in bpy.context.scene.objects if o.type == 'ARMATURE'}
        assert sorted(meshes) == expected
        assert all(any(m.type == 'ARMATURE' and m.object in armatures.values() for m in obj.modifiers) for obj in meshes.values())
        for name, imported_rig in armatures.items():
            assert set(imported_rig.data.bones.keys()) == set(manifest['rigs'][name])
        imported_body = meshes['Cosha']
        imported_keys = list(imported_body.data.shape_keys.key_blocks.keys())[1:] if imported_body.data.shape_keys else []
        assert imported_keys == artist_keys
        imported_weights = weight_dicts(imported_body, imported_body.data, bone_names)
        assert len(imported_weights) == len(original_weights), (len(imported_weights), len(original_weights))
        raw_error, normalized_error = 0., 0.
        changed_vertices = 0
        for original, imported in zip(original_weights, imported_weights):
            total = sum(original.values())
            names = original.keys() | imported.keys()
            local_error = max((abs(original.get(n, 0) - imported.get(n, 0)) for n in names), default=0)
            raw_error = max(raw_error, local_error)
            changed_vertices += local_error > 2e-6
            normalized_error = max(normalized_error, max((abs((original.get(n, 0) / total if total else 0) - imported.get(n, 0)) for n in names), default=0))
        assert min(raw_error, normalized_error) < 2e-6, (raw_error, normalized_error)
        for name, obj in meshes.items():
            info = manifest['meshes'][name]
            assert len(obj.data.vertices) == info['vertices']
            assert len(obj.data.polygons) == info['polygons']
        report['reimport'] = {'meshes': sorted(meshes), 'armatures': {n: len(a.data.bones) for n, a in armatures.items()},
                              'all_meshes_have_armature': True, 'body_vertices': len(imported_body.data.vertices),
                              'body_artist_keys': imported_keys, 'body_weight_max_raw_error': raw_error,
                              'body_weight_max_normalized_error': normalized_error, 'body_raw_changed_vertices': changed_vertices,
                              'body_unweighted_vertices': sum(not w for w in imported_weights)}
    assert hash_file(SOURCE) == source_hash, 'Production file was modified'
    report.update(ok=True, source_file_unchanged=True, temporary_asset_removed=True,
                  unverified=['Unity importer/avatar/rendering/physics'])
    (OUT / 'bound_x_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print('BOUND_X_0572_PASS', json.dumps({'expected': expected, 'weights': report['reimport'], 'source_unchanged': True}), flush=True)


if __name__ == '__main__':
    main()
