"""Artist operation: protect, refresh validated add-on, apply repaired preset, save."""
import bpy
import hashlib
import importlib.util
import json
import sys
import traceback
from pathlib import Path

BASE = Path(__file__).resolve().parent
ARTIST = BASE.parent.parent / 'X.blend'
assert Path(bpy.data.filepath).resolve() == ARTIST.resolve()
rig = bpy.data.objects['CoshaRig']
assert bpy.context.object == rig and bpy.context.mode == 'POSE'
from character_designer import body_original_mode as original
assert not original.active(rig)
assert rig.animation_data is None or (rig.animation_data.action is None and not rig.animation_data.nla_tracks)
assert not (BASE/'live_fix_receipt.json').exists(), 'Already applied: inspect receipt, do not repeat.'

if not (BASE/'X_before_arm_flat_fix.blend').exists():
    backup_code = (BASE.parent/'arm_pole_20261009'/'protect_arm_flat_fix.py').read_text(encoding='utf-8')
    exec(compile(backup_code,'protect_arm_flat_fix','exec'),{'__file__':str(BASE.parent/'arm_pole_20261009'/'protect_arm_flat_fix.py')})
receipt = json.loads((BASE/'backup_receipt.json').read_text(encoding='utf-8'))
assert hashlib.sha256(Path(receipt['backup']).read_bytes()).hexdigest() == receipt['backup_sha256']

# Refresh is part of the protected operation, not a new validation baseline.
from character_designer import control_pose_assets as old_poses, limb_ik as old_limb, limb_ik_fk as old_match
pre_spec=importlib.util.spec_from_file_location('pre_refresh_flat_protection',str(BASE.parent/'arm_flat_mirror_20261008'/'isolated_character_validation.py'))
pre_proof=importlib.util.module_from_spec(pre_spec);pre_spec.loader.exec_module(pre_proof)
pre_proof.poses=old_poses;pre_proof.match=old_match;pre_proof.limb_ik=old_limb;pre_proof.rig=rig
pre_protected=pre_proof.protected_state(rig)
pre_raw=pre_proof.raw_state(rig)
pre_poles=pre_proof.poles(rig)
key_values=lambda:{mesh.name:{key.name:(key.value,key.mute,key.slider_min,key.slider_max)
    for key in mesh.shape_keys.key_blocks} for mesh in bpy.data.meshes if mesh.shape_keys}
pre_key_values=key_values()

def apply_after_refresh():
    try:
        import character_designer
        from character_designer import control_pose_assets as poses, control_pose_mirror as mirror
        from character_designer import limb_ik, limb_ik_fk as match
        assert tuple(character_designer.bl_info['version']) == (0,77,11)
        expected = json.loads((BASE/'release_projection.json').read_text(encoding='utf-8'))['files']
        module_path = Path(poses.__file__)
        assert hashlib.sha256(module_path.read_bytes()).hexdigest() == expected['control_pose_assets.py']
        assert hasattr(poses,'_match_stable_ik_bend')
        spec = importlib.util.spec_from_file_location('live_flat_protection', str(BASE.parent/'arm_flat_mirror_20261008'/'isolated_character_validation.py'))
        proof=importlib.util.module_from_spec(spec);spec.loader.exec_module(proof)
        proof.poses=poses;proof.match=match;proof.limb_ik=limb_ik;proof.rig=rig
        asset=bpy.data.actions['Arm Flat']
        asset_before=proof.assets_state()
        protection=proof.protected_state(rig)
        raw_before=proof.raw_state(rig)
        assert protection==pre_protected, 'Refresh changed protected Rest/meshes/assets'
        assert proof.poles(rig)==pre_poles and key_values()==pre_key_values
        assert all(proof.raw_error(pre_raw[n],raw_before[n])<2e-5 for n in pre_raw)
        before_refresh=json.loads((BASE/'live_before.json').read_text(encoding='utf-8'))
        for n,raw in raw_before.items():
            assert all(proof.raw_error(raw[prop],before_refresh['bones'][n][prop])<2e-5
                       for prop in ('location','rotation_mode','rotation_euler','rotation_quaternion','rotation_axis_angle','scale'))
        poles=proof.poles(rig)
        metadata=poses.asset_metadata(asset)
        old_metadata=dict(metadata)
        metadata.update(stable_ik_bend=True,stable_ik_seed=json.loads((BASE/'stable_ik_seed.json').read_text(encoding='utf-8')))
        auto_key=bpy.context.scene.tool_settings.use_keyframe_insert_auto
        basis_before={p.name:p.matrix_basis.copy() for p in rig.pose.bones}
        inventory=limb_ik._validate_inventory(rig)
        assert all(match.mode_for_rig(rig,inventory['rigs'][('ARM',s)])=='IK' for s in ('L','R'))
        try:
            bpy.context.scene.tool_settings.use_keyframe_insert_auto=False
            asset[poses.ASSET_METADATA]=json.dumps(metadata,separators=(',',':'))
            values=poses.channels(asset,rig)
            both=dict(values)
            both.update(mirror.mirrored_channels(rig,values,metadata=metadata))
            applied=poses.apply_channels(bpy.context,rig,both,metadata=metadata)
            match._update(bpy.context,rig)
            final_protection=proof.protected_state(rig)
            assert all(protection[k]==final_protection[k] for k in ('native_rest','all_rest','meshes_vertices_weights_shape_keys'))
            asset_after=proof.assets_state()
            asset_after[asset.name]['properties'][poses.ASSET_METADATA]=asset_before[asset.name]['properties'][poses.ASSET_METADATA]
            assert asset_after==asset_before
            raw_after=proof.raw_state(rig)
            allowed=set()
            for s in ('L','R'):
                allowed.update(proof.entry_bones(inventory['rigs'][('ARM',s)]))
                allowed.add('shoulder.'+s)
            unexpected={n:proof.raw_error(raw_before[n],raw_after[n]) for n in raw_before
                        if n not in allowed and proof.raw_error(raw_before[n],raw_after[n])>=2e-5}
            if unexpected:
                (BASE/'unrelated_channel_diagnostic.json').write_text(json.dumps(
                    {'unexpected':unexpected,'before':{n:raw_before[n] for n in unexpected},
                     'after':{n:raw_after[n] for n in unexpected}},indent=2),encoding='utf-8')
            assert not unexpected, 'Unexpected pose channels: '+str(unexpected)
            assert proof.poles(rig)==poles
            assert key_values()==pre_key_values
            assert Path(bpy.data.filepath).resolve()==ARTIST.resolve()
        except Exception:
            asset[poses.ASSET_METADATA]=asset_before[asset.name]['properties'][poses.ASSET_METADATA]
            for name,raw in raw_before.items():
                pb=rig.pose.bones[name]
                for prop,value in raw.items():
                    if prop!='ik_fk':setattr(pb,prop,value)
                if raw['ik_fk'] is not None:pb['ik_fk']=raw['ik_fk']
            match._update(bpy.context,rig)
            raise
        finally:
            bpy.context.scene.tool_settings.use_keyframe_insert_auto=auto_key
        saved=bpy.ops.wm.save_mainfile()
        assert saved=={'FINISHED'}
        result={'runtime':character_designer.bl_info['version'],'module':str(module_path),
            'source_sha256':expected['control_pose_assets.py'],'applied_both_arms':applied,
            'artist':str(ARTIST),'saved':sorted(saved),'artist_sha256':hashlib.sha256(ARTIST.read_bytes()).hexdigest(),
            'rest_mesh_weights_shape_key_geometry_and_asset_curves_preserved':True,
            'all_unrelated_raw_pose_channels_preserved_within_2e_5':True,'pole_angles_preserved':True,
            'asset_metadata_only_added':['stable_ik_bend','stable_ik_seed'],'allowed_pose_bones':sorted(allowed)}
        (BASE/'live_fix_receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print('ARM_FLAT_LIVE_FIX_SAVED_OK',tuple(character_designer.bl_info['version']))
    except Exception:
        (BASE/'live_fix_error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        traceback.print_exc()
    return None

import character_designer
if tuple(character_designer.bl_info['version']) != (0,77,11):
    character_designer._reload_addon_deferred()
bpy.app.timers.register(apply_after_refresh,first_interval=.25)
print('ARM_FLAT_FIX_PROTECTED_AND_SCHEDULED')
