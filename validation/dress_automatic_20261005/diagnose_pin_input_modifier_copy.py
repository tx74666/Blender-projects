"""Factory-only native copy diagnosis; never opens or saves an artist file."""
import hashlib
import json
from pathlib import Path
import sys

import bpy


def rna(owner):
    result = {}
    for prop in owner.bl_rna.properties:
        name = prop.identifier
        if name == 'rna_type' or prop.is_readonly or prop.type == 'COLLECTION':
            continue
        value = getattr(owner, name)
        if prop.type == 'POINTER':
            result[name] = getattr(value, 'name', None) if value else None
        elif getattr(prop, 'is_array', False):
            result[name] = list(value)
        elif isinstance(value, (str, bool, int, float)) or value is None:
            result[name] = value
        elif isinstance(value, set):
            result[name] = sorted(value)
        else:
            raise RuntimeError('Unknown RNA: ' + name)
    return result


def matrix(value):
    return [list(row) for row in value]


def main():
    if not bpy.app.background or bpy.data.filepath:
        raise RuntimeError('Factory background with no artist filepath required')
    output = Path(sys.argv[sys.argv.index('--output') + 1])
    output.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    armature = bpy.data.armatures.new('QA Copy Diagnosis Armature')
    rig = bpy.data.objects.new('QA Copy Diagnosis Rig', armature)
    scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bone = armature.edit_bones.new('QA Waist')
    bone.head, bone.tail = (0, 0, 0), (0, 1, 0)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.mesh.primitive_cube_add(size=2)
    target = bpy.context.object
    target.name = 'QA Native Body Target'
    target.scale = (2, 2, 2)
    mesh = bpy.data.meshes.new('QA Copy Diagnosis Mesh')
    mesh.from_pydata([(-.2, -.2, 2.1), (.2, -.2, 2.1), (.2, .2, 2.1), (-.2, .2, 2.1)], [], [(0, 1, 2, 3)])
    source = bpy.data.objects.new('QA Copy Diagnosis Source', mesh)
    scene.collection.objects.link(source)
    source.location, source.scale = (.04, -.08, .03), (.782, .782, .782)
    source.rotation_euler = (.02, -.03, .01)
    source.vertex_groups.new(name='QA Waist').add(list(range(4)), 1., 'REPLACE')
    source.vertex_groups.new(name='QA Mass').add([0, 1], 1., 'REPLACE')
    source.vertex_groups.new(name='QA Mask').add([0, 1], 1., 'REPLACE')
    skin = source.modifiers.new('QA Waist Armature', 'ARMATURE')
    skin.object = rig
    surface = source.modifiers.new('QA Sparse Surface Attachment', 'SURFACE_DEFORM')
    surface.target, surface.vertex_group = target, 'QA Mask'
    surface.strength, surface.use_sparse_bind = 1., True
    cloth = source.modifiers.new('QA Original Cloth', 'CLOTH')
    cloth.show_viewport = cloth.show_render = False
    cloth.settings.vertex_group_mass = 'QA Mass'
    skin.is_active = surface.is_active = False
    cloth.is_active = True
    bpy.context.view_layer.objects.active = source
    source.select_set(True)
    bpy.context.view_layer.update()
    result = bpy.ops.object.surfacedeform_bind(modifier=surface.name)
    bpy.context.view_layer.update()
    if result != {'FINISHED'} or not surface.is_bound:
        raise RuntimeError('Native test fixture bind did not succeed')
    expected = [rna(m) for m in source.modifiers[:2]]
    probe = source.copy()
    probe.name = 'QA Temporary Copy Probe'
    scene.collection.objects.link(probe)
    probe.modifiers.remove(probe.modifiers[-1])
    for copied, original in zip(probe.modifiers, source.modifiers[:2]):
        copied.is_active = original.is_active

    def evidence():
        actual = [rna(m) for m in probe.modifiers]
        return {'bound': probe.modifiers[1].is_bound, 'target_exact': probe.modifiers[1].target == target,
                'modifiers_exact': actual == expected,
                'modifier_differences': [{k: [a.get(k), b.get(k)] for k in set(a) | set(b) if a.get(k) != b.get(k)} for a, b in zip(expected, actual)],
                'basis_exact': matrix(probe.matrix_basis) == matrix(source.matrix_basis),
                'world_exact': matrix(probe.matrix_world) == matrix(source.matrix_world),
                'source_world': matrix(source.matrix_world), 'probe_world': matrix(probe.matrix_world),
                'shared_mesh_exact': probe.data == source.data}
    report = {'runtime': bpy.app.version_string, 'artist_opened_or_saved': False,
              'operator': sorted(result), 'before_update': evidence()}
    bpy.context.view_layer.update()
    report['after_update'] = evidence()
    report['source_modifiers_after_exact'] = [rna(m) for m in source.modifiers[:2]] == expected
    report['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (output / 'pin_input_modifier_copy.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf8')
    print('PIN_INPUT_MODIFIER_COPY=' + json.dumps(report, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
