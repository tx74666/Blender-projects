import bpy
import json
import sys
from pathlib import Path

root = Path(r'D:\Blender\Projects\Character\X')
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import character_setup, quick_bind

bpy.ops.wm.open_mainfile(filepath=str(root / 'X.blend'), load_ui=False)
character_designer.register()
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
state = bpy.context.scene.character_designer_setup
state.rig = bpy.data.objects['CoshaRig']
state.body = bpy.data.objects['Cosha']
for name, role in [('Clothes', 'CLOTHING'), ('Stocking', 'STOCKINGS'), ('Shoes', 'SHOES'),
                   ('Hair1', 'HAIR'), ('Hair2', 'HAIR'), ('Hair3', 'HAIR'), ('Dress', 'SKIRT')]:
    if name in bpy.data.objects:
        character_setup.remember_asset(bpy.context, bpy.data.objects[name], role)

def geometry(obj):
    return (obj.data.as_pointer(), tuple(tuple(v.co) for v in obj.data.vertices),
            tuple(tuple(p.vertices) for p in obj.data.polygons),
            tuple(tuple(e.vertices) for e in obj.data.edges),
            tuple(tuple(row) for row in obj.matrix_world),
            tuple((uv.name, tuple(tuple(x.uv) for x in uv.data)) for uv in obj.data.uv_layers))

def weights(obj):
    return {g.name: {v.index: next(a.weight for a in v.groups if a.group == g.index)
                     for v in obj.data.vertices if any(a.group == g.index for a in v.groups)}
            for g in obj.vertex_groups}

report = {'source': state.body.name, 'rig': state.rig.name, 'targets': {}}
restore_baselines = {}
source_before = geometry(state.body), weights(state.body)
names = {b.name for b in state.rig.data.bones if b.use_deform}
for name, mode in [('Clothes', 'TRANSFER'), ('Stocking', 'TRANSFER'), ('Shoes', 'TRANSFER')]:
    obj = bpy.data.objects[name]
    before_geometry, before_weights = geometry(obj), weights(obj)
    restore_baselines[name] = (before_geometry[1:], before_weights, [(m.name, m.type) for m in obj.modifiers])
    result = {}
    try:
        result['binding'] = quick_bind.bind_weights(bpy.context, obj, state.rig, body=state.body, mode=mode)
    except quick_bind.QuickBindError as exc:
        result['auto_error'] = str(exc)
        assert geometry(obj) == before_geometry and weights(obj) == before_weights
        if mode != 'AUTO':
            raise
        result['binding'] = quick_bind.bind_weights(bpy.context, obj, state.rig, body=state.body, mode='TRANSFER')
    assert geometry(obj) == before_geometry
    after_weights = weights(obj)
    assert all(after_weights[group] == values for group, values in before_weights.items() if group not in names)
    by_index = {g.index: g.name for g in obj.vertex_groups}
    sums = [sum(a.weight for a in v.groups if by_index[a.group] in names) for v in obj.data.vertices]
    assert all(abs(total - 1.0) < 1e-5 for total in sums)
    assert len([m for m in obj.modifiers if m.type == 'ARMATURE' and m.object == state.rig]) == 1
    result.update(vertices=len(obj.data.vertices), min_sum=min(sums), max_sum=max(sums),
                  geometry_uv_transforms_unchanged=True, old_auxiliary_weights_preserved=True,
                  modifiers=[(m.name, m.type) for m in obj.modifiers])
    report['targets'][name] = result
    print('REAL_MODEL_TARGET_VERIFIED', name, result, flush=True)
assert (geometry(state.body), weights(state.body)) == source_before
report['body_source_unchanged'] = True
preview = root / 'Previews' / 'X_Quick_Bind_0.43.1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(preview), copy=True)
report['preview'] = str(preview)
bpy.ops.wm.open_mainfile(filepath=str(preview), load_ui=False)
for name, (expected_geometry, expected_weights, expected_modifiers) in restore_baselines.items():
    obj = bpy.data.objects[name]
    assert quick_bind.has_binding_backup(obj)
    quick_bind.restore_binding(bpy.context, obj)
    assert geometry(obj)[1:] == expected_geometry
    assert weights(obj) == expected_weights
    assert [(m.name, m.type) for m in obj.modifiers] == expected_modifiers
    assert not quick_bind.has_binding_backup(obj)
report['save_reopen_restore_verified'] = True
(root / 'outputs/binding/quick_bind_real_model_verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('REAL_MODEL_QUICK_BIND_VERIFIED', json.dumps(report), flush=True)
