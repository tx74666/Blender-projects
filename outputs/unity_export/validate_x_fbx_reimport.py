"""Read-only validation of the exported X character in an empty Blender process.

Only this JSON report is written. Neither the FBX, its textures nor X.blend is saved.
"""
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

OUT = Path(__file__).resolve().parent
ASSET = OUT / 'Cosha'
MANIFEST = json.loads((ASSET / 'Cosha.cdesigner.json').read_text(encoding='utf8'))
SOURCE = Path(r'D:\Blender\Projects\Character\X\X.blend')
REPORT = OUT / 'x_fbx_reimport.json'


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluated_points(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def movement(before, after):
    assert len(before) == len(after)
    values = [(a - b).length for a, b in zip(before, after)]
    return {'maximum': max(values, default=0), 'moved_vertices': sum(v > 1e-6 for v in values)}


def main():
    source_hash = file_hash(SOURCE)
    manifest_hash = file_hash(ASSET / 'Cosha.cdesigner.json')
    asset_hashes = {name: file_hash(ASSET / name) for name in MANIFEST['files']}
    assert asset_hashes == MANIFEST['files'], 'Published export files differ from the manifest'
    for obj in tuple(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.preferences.addon_enable(module='io_scene_fbx')
    result = bpy.ops.import_scene.fbx(filepath=str(ASSET / 'Cosha.fbx'))
    assert 'FINISHED' in result
    objects = {obj.name: obj for obj in bpy.context.scene.objects}
    assert set(objects) == set(MANIFEST['objects']), sorted(objects)
    rigs = {name: obj for name, obj in objects.items() if obj.type == 'ARMATURE'}
    meshes = {name: obj for name, obj in objects.items() if obj.type == 'MESH'}
    assert len(rigs) == 1 and len(meshes) == 7
    rig = rigs['CoshaRig']
    assert set(rig.data.bones.keys()) == set(MANIFEST['rigs']['CoshaRig'])
    assert len(rig.data.bones) == 56
    assert not any(name.startswith(('CTRL_', 'MCH_', 'ORG_', 'ORI_')) for name in rig.data.bones.keys())
    report = {'ok': False, 'file': str(ASSET / 'Cosha.fbx'), 'objects': sorted(objects),
              'bone_count': len(rig.data.bones), 'bones': sorted(rig.data.bones.keys()),
              'meshes': {}, 'deformation': {}, 'warnings': []}
    all_points = []
    used_materials = set()
    for name, obj in meshes.items():
        expected = MANIFEST['meshes'][name]
        assert len(obj.data.vertices) == expected['vertices'], (name, len(obj.data.vertices), expected['vertices'])
        assert len(obj.data.polygons) == expected['polygons'], (name, len(obj.data.polygons), expected['polygons'])
        shape_names = list(obj.data.shape_keys.key_blocks.keys())[1:] if obj.data.shape_keys else []
        assert shape_names == expected['shape_keys'], (name, shape_names)
        assert not any(name.startswith('CD Forearm Twist') for name in shape_names)
        skins = [m for m in obj.modifiers if m.type == 'ARMATURE']
        assert bool(skins) == expected['skinned'], (name, [(m.type, m.name) for m in obj.modifiers])
        assert all(m.object == rig for m in skins)
        bone_groups = {g.index: g.name for g in obj.vertex_groups if g.name in rig.data.bones}
        weights = [sum(g.weight for g in v.groups if g.group in bone_groups) for v in obj.data.vertices]
        assert all(math.isfinite(w) and w >= 0 for w in weights)
        weighted = sum(w > 1e-7 for w in weights)
        if skins:
            assert weighted > 0, name + ' lost all skin weights'
            if weighted < len(weights):
                report['warnings'].append(f'{name}: {len(weights) - weighted} vertices have no imported skin weight.')
        coords = evaluated_points(obj)
        assert all(all(math.isfinite(c) for c in p) for p in coords)
        all_points.extend(coords)
        material_names = [m.name for m in obj.data.materials if m]
        used_materials.update(material_names)
        report['meshes'][name] = {'vertices': len(obj.data.vertices), 'polygons': len(obj.data.polygons),
                                  'shape_keys': shape_names, 'skinned': bool(skins),
                                  'weighted_vertices': weighted, 'bone_groups': sorted(bone_groups.values()),
                                  'weight_sum_min': min(weights, default=0), 'weight_sum_max': max(weights, default=0),
                                  'materials': material_names}
    assert used_materials == set(MANIFEST['materials']), (used_materials, MANIFEST['materials'])
    minimum = Vector(tuple(min(point[axis] for point in all_points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in all_points) for axis in range(3)))
    dimensions = maximum - minimum
    assert .5 < dimensions.z < 3.5 and max(dimensions.x, dimensions.y) < 3.5, tuple(dimensions)
    assert max(abs(value) for value in (*minimum, *maximum)) < 4
    report['bounds'] = {'minimum': list(minimum), 'maximum': list(maximum), 'dimensions': list(dimensions)}
    report['materials'] = sorted(used_materials)
    # Actual imported bone motion must reach the skin, then restore exactly.
    skinned = {name: obj for name, obj in meshes.items() if MANIFEST['meshes'][name]['skinned']}
    baseline = {name: evaluated_points(obj) for name, obj in skinned.items()}
    for bone_name, delta in [('Hips', Matrix.Translation((0, .04, 0))),
                             ('hand.L', Matrix.Rotation(.25, 4, 'Y')),
                             ('hand.R', Matrix.Rotation(-.25, 4, 'Y'))]:
        bone = rig.pose.bones[bone_name]
        original = bone.matrix_basis.copy()
        bone.matrix_basis = original @ delta
        rig.update_tag(refresh={'OBJECT'})
        bpy.context.view_layer.update()
        changed = {name: movement(baseline[name], evaluated_points(obj)) for name, obj in skinned.items()}
        assert changed['Cosha']['maximum'] > 1e-4, (bone_name, changed)
        if bone_name == 'Hips':
            assert all(info['maximum'] > .001 for info in changed.values()), changed
        bone.matrix_basis = original
        rig.update_tag(refresh={'OBJECT'})
        bpy.context.view_layer.update()
        restored = {name: movement(baseline[name], evaluated_points(obj)) for name, obj in skinned.items()}
        assert all(info['maximum'] < 2e-6 for info in restored.values()), (bone_name, restored)
        report['deformation'][bone_name] = {'motion': changed, 'restored': restored}
    keys = meshes['Cosha'].data.shape_keys
    key = keys.key_blocks['Eye_Close_L']
    original = key.value
    body_before = evaluated_points(meshes['Cosha'])
    key.value = .9 if original < .5 else .1
    bpy.context.view_layer.update()
    key_movement = movement(body_before, evaluated_points(meshes['Cosha']))
    assert key_movement['maximum'] > 1e-5, key_movement
    key.value = original
    bpy.context.view_layer.update()
    assert movement(body_before, evaluated_points(meshes['Cosha']))['maximum'] < 2e-6
    report['artist_shape_key_deformation'] = {'key': key.name, **key_movement, 'restored': True}
    assert not any(obj.animation_data and obj.animation_data.action for obj in objects.values())
    texture_paths = sorted({bpy.path.abspath(node.image.filepath)
                            for obj in meshes.values() for material in obj.data.materials if material and material.use_nodes
                            for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image})
    assert all(Path(path).is_file() for path in texture_paths), texture_paths
    report['imported_texture_references'] = texture_paths
    report['published_texture_count'] = len(asset_hashes) - 1
    report['checks'] = ['7 meshes and 1 armature', '56 native bones, no generated helpers',
                        'vertex and polygon counts match exported evaluated geometry',
                        '7 artist Shape Keys preserved, runtime forearm keys omitted',
                        'skin weights and 19 material slots retained', 'plausible rest model bounds',
                        'Hips and both hands deform imported skin and restore',
                        'artist eye Shape Key deforms and restores', 'texture references resolve',
                        'FBX, manifest, textures and production X remain unchanged']
    report['unverified'] = ['Unity import, Humanoid Avatar, renderer appearance and runtime physics']
    assert file_hash(SOURCE) == source_hash
    assert file_hash(ASSET / 'Cosha.cdesigner.json') == manifest_hash
    assert {name: file_hash(ASSET / name) for name in asset_hashes} == asset_hashes
    report.update(ok=True, source_unchanged=True, asset_files_unchanged=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print('X_FBX_REIMPORT_PASS', json.dumps({'bones': report['bone_count'], 'meshes': len(meshes),
                                           'dimensions': list(dimensions), 'warnings': report['warnings']}), flush=True)


if __name__ == '__main__':
    main()
