import bpy
import json
from mathutils import Matrix, Vector
from pathlib import Path

BASE = Path(r'D:\Blender\Projects\Character\X\validation\arm_pole_20261009')
OLD = json.loads((BASE.parent / 'arm_flat_mirror_20261008' / 'live_before.json').read_text(encoding='utf-8'))
with bpy.data.libraries.load(r'D:\Blender\Projects\Character\X\X.blend', link=False) as (src, dst):
    dst.objects = ['CoshaRig']
rig = bpy.data.objects['CoshaRig']
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.context.view_layer.update()
basis = {p.name: p.matrix_basis.copy() for p in rig.pose.bones}

def update():
    rig.update_tag(refresh={'OBJECT', 'DATA', 'TIME'})
    bpy.context.view_layer.update()

def restore():
    for name, m in basis.items():
        rig.pose.bones[name].matrix_basis = m
    update()

def read(side):
    a, b, c = [rig.pose.bones[n + '.' + side].matrix.translation.copy() for n in ('upper_arm', 'forearm', 'hand')]
    axis = (c - a).normalized()
    radial = b - a - axis * (b - a).dot(axis)
    back = Vector((0, 1, 0)); back -= axis * back.dot(axis)
    pole = rig.pose.bones['CTRL_elbow_pole.' + side].matrix.translation.copy()
    return {'a': list(a), 'b': list(b), 'c': list(c), 'pole': list(pole),
            'radial': list(radial), 'radial_length': radial.length,
            'radial_direction': list(radial.normalized()),
            'back_dot': radial.normalized().dot(back.normalized()),
            'pole_angle': next(cn.pole_angle for cn in rig.pose.bones['forearm.' + side].constraints if cn.type == 'IK')}

records = []
for variant in ('saved', 'source_identity', 'historic_source'):
    for side in ('L', 'R'):
        for fraction in (0.02, 0.15, 0.30):
            restore()
            if variant == 'source_identity':
                for name in ('upper_arm', 'forearm', 'hand'):
                    rig.pose.bones[name + '.' + side].matrix_basis = Matrix.Identity(4)
            elif variant == 'historic_source':
                for name in ('upper_arm', 'forearm', 'hand'):
                    rig.pose.bones[name + '.' + side].matrix_basis = Matrix(OLD['bones'][name + '.' + side]['basis'])
            update()
            before = read(side)
            target = rig.pose.bones['CTRL_hand_IK.' + side]
            m = target.matrix.copy()
            start, end = Vector(before['a']), Vector(before['c'])
            m.translation = end + (start - end) * fraction
            target.matrix = m
            update()
            result = {'variant': variant, 'side': side, 'retract': fraction, 'before': before, 'after': read(side)}
            records.append(result)
            print(variant, side, fraction, 'back_dot', result['after']['back_dot'], 'direction', result['after']['radial_direction'])
(BASE / 'saved_drag_probe.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
restore()
