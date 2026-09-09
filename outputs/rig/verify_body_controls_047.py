"""Disposable real-character check for shoe-relative arrows and spine controls."""
from pathlib import Path
import hashlib
import json
import sys
import traceback
import bpy

ROOT = Path(r'D:\Blender\Projects\Character\X')
SOURCE = ROOT / 'X.blend'
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import character_setup, limb_ik, limb_ik_fk, foot_controls, torso_controls


def asset_digest():
    digest = hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type == 'MESH' and not o.get('character_designer_owner')), key=lambda o: o.name):
        data = {'name': obj.name, 'vertices': [list(v.co) for v in obj.data.vertices],
                'groups': [g.name for g in obj.vertex_groups],
                'weights': [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices],
                'faces': [list(p.vertices) for p in obj.data.polygons],
                'uv': [[list(item.uv) for item in layer.data] for layer in obj.data.uv_layers]}
        digest.update(json.dumps(data, sort_keys=True).encode())
    return digest.hexdigest()


report = {'ok': False, 'checks': []}
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
try:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    cd.register()
    rig = bpy.data.objects['CoshaRig']
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.character_designer.limb_ik_analyze()
    assert not torso_controls.get_record(rig)
    names = [b.name for b in rig.data.bones if not b.get(limb_ik.OWNER_KEY)]
    limb_ik_fk._update(bpy.context, rig)
    initial = limb_ik_fk._matrices(rig, names)
    rest, assets = limb_ik._armature_digest(rig), asset_digest()
    mapping = character_setup._mapping(character_setup.settings(bpy.context), rig, create=True)
    mapping.footwear = bpy.data.objects['Shoes']
    settings = bpy.context.window_manager.character_designer_limb_ik
    for side, selected in (('L', 'LEFT_LEG'), ('R', 'RIGHT_LEG')):
        settings.selected_limb = selected
        before = {pb.name: pb.matrix_basis.copy() for pb in rig.pose.bones}
        assert bpy.ops.character_designer.foot_controls(action='FIT_VISUAL') == {'FINISHED'}
        rec = foot_controls.get_record(rig, ('LEG', side))
        assert rig.pose.bones[rec['roll']].custom_shape_transform == rig.pose.bones[rec['chain'][2]]
        assert all(pb.matrix_basis == before[pb.name] for pb in rig.pose.bones)
        limb_ik_fk._verify(rig, initial)
    report['checks'].append('Both arrows fit Shoes in the current raised-foot pose; no pose channels changed')
    assert bpy.ops.character_designer.torso_controls(action='BUILD') == {'FINISHED'}
    record = torso_controls.get_record(rig)
    limb_ik_fk._verify(rig, initial)
    assert record['sources'] == ['spine', 'Chest', 'UpperChest']
    assert limb_ik._armature_digest(rig) == rest
    limb_ik._validate_inventory(rig)
    assert asset_digest() == assets
    preview = ROOT / 'outputs' / 'rig' / 'X_body_controls_047_preview.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(preview), copy=True)
    report['preview'] = str(preview)
    bend = rig.pose.bones[record['bend']]
    bend.rotation_euler.x = 0.15
    limb_ik_fk._update(bpy.context, rig)
    assert (rig.pose.bones['Head'].matrix.translation - initial['Head'].translation).length > 0.005
    legs = [n for key, data in limb_ik._validate_inventory(rig)['rigs'].items() if key[0] == 'LEG' for n in data['chain']]
    limb_ik_fk._verify(rig, {n: initial[n] for n in legs})
    rig.pose.bones[record['controls']['UpperChest']].rotation_euler.z = 0.1
    limb_ik_fk._update(bpy.context, rig)
    desired = limb_ik_fk._matrices(rig, names)
    assert bpy.ops.character_designer.torso_controls(action='REMOVE') == {'FINISHED'}
    limb_ik_fk._verify(rig, desired)
    assert not torso_controls.get_record(rig)
    assert limb_ik._armature_digest(rig) == rest
    limb_ik._validate_inventory(rig)
    assert asset_digest() == assets
    report['checks'].append('Three spine controls and shared bend work; removing retains the posed body and existing limbs')
    report['checks'].append('Native rest bones, geometry, UV and weights are unchanged')
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
    report.update(ok=True, production_file_unchanged=True)
except Exception as exc:
    report.update(error=str(exc), traceback=traceback.format_exc())
    raise
finally:
    (ROOT / 'outputs' / 'rig' / 'body_controls_047_verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('BODY_CONTROLS_047', json.dumps(report), flush=True)
