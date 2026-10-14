import bpy
import json
from mathutils import Vector
from pathlib import Path

BASE = Path(r'D:\Blender\Projects\Character\X\validation\arm_pole_20261009')
assert bpy.app.background, 'This validation only runs in an isolated background Blender'
with bpy.data.libraries.load(str(BASE / 'X_before_arm_pole_seed_repair.blend'), link=False) as (src, dst):
    dst.objects = ['CoshaRig']
rig = bpy.data.objects['CoshaRig']
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.context.view_layer.update()
namespace = {}
exec(compile((BASE / 'repair_seed.py').read_text(encoding='utf-8'), 'repair_seed', 'exec'), namespace)
report = namespace['repair'](rig)
basis = {p.name: p.matrix_basis.copy() for p in rig.pose.bones}
angles = {p.name: [(c.name, c.pole_angle) for c in p.constraints if c.type == 'IK'] for p in rig.pose.bones}
cases = []
for side in ('L', 'R'):
    for fraction in (0.02, 0.15, 0.30):
        for name, m in basis.items():
            rig.pose.bones[name].matrix_basis = m
        rig.update_tag(refresh={'OBJECT', 'DATA', 'TIME'})
        bpy.context.view_layer.update()
        start = rig.pose.bones['upper_arm.' + side].matrix.translation.copy()
        target = rig.pose.bones['CTRL_hand_IK.' + side]
        m = target.matrix.copy()
        m.translation += (start - m.translation) * fraction
        target.matrix = m
        rig.update_tag(refresh={'OBJECT', 'DATA', 'TIME'})
        bpy.context.view_layer.update()
        joint = rig.pose.bones['forearm.' + side].matrix.translation.copy()
        end = rig.pose.bones['hand.' + side].matrix.translation.copy()
        axis = (end - start).normalized()
        radial = joint - start - axis * (joint - start).dot(axis)
        back = Vector((0, 1, 0)); back -= axis * back.dot(axis)
        dot = radial.normalized().dot(back.normalized())
        assert dot > 0.97, ('Elbow is not bending backwards', side, fraction, dot)
        assert angles == {p.name: [(c.name, c.pole_angle) for c in p.constraints if c.type == 'IK'] for p in rig.pose.bones}
        cases.append({'side': side, 'retract': fraction, 'back_dot': dot, 'radial': list(radial.normalized())})
        print('ARM_POLE_DRAG_PASS', side, fraction, dot)
report['drag_cases'] = cases
report['passed'] = True
(BASE / 'isolated_repair_verified.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('ARM_POLE_REPAIR_NATIVE_PASS', len(cases))
