"""Back up X, fit the shoe-relative arrows, and add removable spine controls."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import bpy
import character_designer as cd
from character_designer import character_setup, bone_collections, foot_controls, torso_controls, limb_ik, limb_ik_fk

ROOT = Path(r'D:\Blender\Projects\Character\X')
assert Path(bpy.data.filepath).resolve() == (ROOT / 'X.blend').resolve()
assert cd.bl_info['version'] == (0, 47, 0)


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


class CD_OT_apply_body_047(bpy.types.Operator):
    bl_idname = 'character_designer.apply_body_047'
    bl_label = 'Fit Foot Arrows and Add Spine Controls'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rig = bpy.data.objects['CoshaRig']
        assert context.scene.character_designer_setup.rig == rig
        assert rig.mode in {'OBJECT', 'POSE'}
        assert not torso_controls.get_record(rig), 'Spine controls already installed; no duplicate created.'
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for obj in context.selected_objects:
            obj.select_set(False)
        rig.select_set(True)
        context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='POSE')
        limb_ik_fk._update(context, rig)
        before = {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.data.bones if not b.get(limb_ik.OWNER_KEY)}
        rest, assets = limb_ik._armature_digest(rig), asset_digest()
        layout = bone_collections.capture_managed_layout(rig)
        foot_raw = rig.data[foot_controls.RECORD_KEY]
        visuals = {s: foot_controls._roll_visual_state(rig.pose.bones[r['roll']]) for s, r in foot_controls.records(rig).items()}
        mapping = character_setup._mapping(character_setup.settings(context), rig, create=True)
        old_shoe = mapping.footwear
        backup = ROOT / 'outputs' / 'rig' / 'backups' / ('X_before_body_controls_047_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
        backup.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True)
        try:
            mapping.footwear = bpy.data.objects['Shoes']
            for side in ('L', 'R'):
                foot_controls.fit_roll_visual(context, rig, ('LEG', side), shoe=mapping.footwear)
            torso_controls.build(context, rig, hips_name=character_setup.resolve_bone(context, 'HIPS', rig))
            limb_ik_fk._verify(rig, before)
            assert limb_ik._armature_digest(rig) == rest
            assert asset_digest() == assets
            limb_ik._validate_inventory(rig)
        except Exception:
            if torso_controls.get_record(rig):
                torso_controls.remove(context, rig)
            for side, state in visuals.items():
                record = foot_controls.get_record(rig, ('LEG', side))
                foot_controls._set_roll_visual(rig, rig.pose.bones[record['roll']], state)
            rig.data[foot_controls.RECORD_KEY] = foot_raw
            mapping.footwear = old_shoe
            bone_collections.finish_rig_edit(rig, layout)
            raise
        state = context.window_manager.character_designer
        state.ui_page, state.rig_section = 'RIG', 'BODY'
        bpy.ops.character_designer.limb_ik_analyze()
        context.window_manager.character_designer_limb_ik.selected_limb = 'LEFT_LEG'
        context.window_manager.character_designer_limb_ik.show_foot_visual_options = True
        torso = torso_controls.get_record(rig)
        bpy.ops.character_designer.torso_controls(action='SELECT', bone=torso['bend'])
        report = {'ok': True, 'version': list(cd.bl_info['version']), 'backup': str(backup),
                  'source': bpy.data.filepath, 'native_pose_errors': list(limb_ik_fk._pose_errors(rig, before)),
                  'native_rest_unchanged': True, 'weights_geometry_uv_unchanged': True,
                  'footwear': mapping.footwear.name, 'spine_sources': torso['sources'], 'spine_controls': torso['controls'],
                  'bend': torso['bend'], 'foot_arrows': {s: r['roll_visual_fit'] for s, r in foot_controls.records(rig).items()},
                  'main_file_saved': False}
        (ROOT / 'outputs' / 'rig' / 'body_controls_047_live_result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('BODY_CONTROLS_047_LIVE', json.dumps(report))
        self.report({'INFO'}, 'Foot arrows fitted to Shoes and spine controls added; original pose and weights preserved. Backup saved.')
        return {'FINISHED'}


if hasattr(bpy.types, 'CD_OT_apply_body_047'):
    bpy.utils.unregister_class(bpy.types.CD_OT_apply_body_047)
bpy.utils.register_class(CD_OT_apply_body_047)
bpy.ops.character_designer.apply_body_047()
