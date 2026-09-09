"""Back up the current X scene and add the tested optional foot controls."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import bpy
import character_designer
from character_designer import bone_collections, foot_controls, limb_ik, limb_ik_fk

ROOT = Path(r'D:\Blender\Projects\Character\X')
assert Path(bpy.data.filepath).resolve() == (ROOT / 'X.blend').resolve()
assert character_designer.bl_info['version'] == (0, 46, 0)


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


class CD_OT_apply_feet_046(bpy.types.Operator):
    bl_idname = 'character_designer.apply_feet_046'
    bl_label = 'Add Foot Roll and Toe Bend to X'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig = bpy.data.objects['CoshaRig']
        assert context.scene.character_designer_setup.rig == rig
        assert rig.mode in {'OBJECT', 'POSE'}
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in context.selected_objects:
            obj.select_set(False)
        rig.select_set(True)
        context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE')
        assert not foot_controls.records(rig), 'Foot Controls already applied; no duplicate created.'
        inventory = limb_ik._validate_inventory(rig)
        for side in ('L', 'R'):
            assert ('LEG', side) in inventory['rigs']
        limb_ik_fk._update(context, rig)
        before = {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.data.bones
                  if b.get(limb_ik.OWNER_KEY) != limb_ik.OWNER_VALUE}
        rest = limb_ik._armature_digest(rig)
        assets = asset_digest()
        layout = bone_collections.capture_managed_layout(rig)
        backup = ROOT / 'outputs' / 'rig' / 'backups' / ('X_before_foot_controls_046_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
        backup.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True)
        added = []
        try:
            for side in ('L', 'R'):
                current_layout = bone_collections.capture_managed_layout(rig)
                foot_controls.build(context, rig, ('LEG', side))
                added.append(side)
                bone_collections.finish_rig_edit(rig, current_layout)
                limb_ik_fk._verify(rig, before)
            assert limb_ik._armature_digest(rig) == rest, 'Native rest bones changed'
            assert asset_digest() == assets, 'Mesh or weight changes detected'
            limb_ik._validate_inventory(rig)
        except Exception:
            for side in reversed(added):
                foot_controls.remove(context, rig, ('LEG', side))
            bone_collections.finish_rig_edit(rig, layout)
            raise
        state = context.window_manager.character_designer
        state.ui_page, state.rig_section = 'RIG', 'BODY'
        bpy.ops.character_designer.limb_ik_analyze()
        context.window_manager.character_designer_limb_ik.selected_limb = 'LEFT_LEG'
        bpy.ops.character_designer.foot_controls(action='SELECT_ROLL')
        report = {'ok': True, 'backup': str(backup), 'version': list(character_designer.bl_info['version']),
                  'source': bpy.data.filepath, 'native_pose_errors': list(limb_ik_fk._pose_errors(rig, before)),
                  'native_rest_unchanged': True, 'weights_geometry_uv_unchanged': True,
                  'controls': {s: {k: v for k, v in r.items() if k in ('roll', 'toe_control', 'toe')} for s, r in foot_controls.records(rig).items()},
                  'collections': [{'name': c.name, 'visible': c.is_visible, 'count': len(c.bones)} for c in rig.data.collections],
                  'main_file_saved': False}
        (ROOT / 'outputs' / 'rig' / 'foot_controls_046_live_result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('FOOT_CONTROLS_046_LIVE', json.dumps(report))
        self.report({'INFO'}, 'Both foot controls added; original pose, rest bones and weights preserved. Backup saved.')
        return {'FINISHED'}


if hasattr(bpy.types, 'CD_OT_apply_feet_046'):
    bpy.utils.unregister_class(bpy.types.CD_OT_apply_feet_046)
bpy.utils.register_class(CD_OT_apply_feet_046)
bpy.ops.character_designer.apply_feet_046()
