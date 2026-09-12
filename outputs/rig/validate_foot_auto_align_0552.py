"""Validate the foot correction on an immutable saved-X copy, never production."""
import bpy, hashlib, json, runpy, sys, traceback
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).parent
SOURCE = OUT/'fixtures/X_auto_align_saved_20260912_foot.blend'
PREVIEW = OUT/'fixtures/X_foot_auto_align_0552_preview.blend'
REPORT = OUT/'foot_auto_align_0552_validation.json'
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import foot_controls as feet, limb_ik, limb_ik_fk, body_setup

def error(a, b):
    return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))

def update(rig):
    rig.data.update_tag()
    rig.update_tag(refresh={'OBJECT'})
    bpy.context.view_layer.update()

def main():
    report = {'ok':False}
    checksum = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    try:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
        cd.register()
        rig = bpy.data.objects['CoshaRig']
        bpy.context.view_layer.objects.active = rig
        rig.hide_set(False)
        rig.select_set(True)
        if rig.mode != 'POSE': bpy.ops.object.mode_set(mode='POSE')
        update(rig)
        digest = runpy.run_path(str(OUT/'repair_reversal_20260912.py'))['digest_meshes']
        meshes = digest()
        rests = {b.name:b.matrix_local.copy() for b in rig.data.bones}
        poses = {p.name:p.matrix.copy() for p in rig.pose.bones}
        bases = {p.name:p.matrix_basis.copy() for p in rig.pose.bones}
        old_records = {s:feet.get_record(rig,('LEG',s)) for s in 'LR'}
        assert all(old_records.values()), 'Both feet must exist in the actual fixture'
        assert bpy.ops.character_designer.upgrade_foot_auto_align('EXEC_DEFAULT') == {'FINISHED'}
        assert digest() == meshes, 'Mesh, weights, keys, transforms or original IDs changed'
        report['native_rest_error'] = max(error(rig.data.bones[n].matrix_local,m) for n,m in rests.items())
        report['pose_error'] = max(error(rig.pose.bones[n].matrix,m) for n,m in poses.items())
        report['basis_error'] = max(error(rig.pose.bones[n].matrix_basis,m) for n,m in bases.items())
        assert report['native_rest_error'] < 2e-6
        assert report['pose_error'] < 4e-4
        assert report['basis_error'] < 2e-6
        added = sorted(set(rig.data.bones.keys())-set(rests))
        report['added_helpers'] = added
        assert all(not rig.data.bones[n].use_deform for n in added)
        assert bpy.ops.character_designer.upgrade_foot_auto_align('EXEC_DEFAULT') == {'FINISHED'}
        bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW))
        report['motion'] = {}
        for side in 'LR':
            key = ('LEG',side)
            record = feet.get_record(rig,key)
            assert record['auto_follow'] == 1
            settings = limb_ik._settings(bpy.context)
            settings.selected_limb = 'LEFT_LEG' if side=='L' else 'RIGHT_LEG'
            limb_ik._set_auto_align_selected_target(bpy.context,rig,settings,True)
            target = rig.pose.bones[record['target']]
            original = target.matrix_basis.copy()
            shin,foot,toe = [rig.pose.bones[n] for n in (record['chain'][1],record['chain'][2],record['toe'])]
            relative = shin.matrix.inverted_safe() @ foot.matrix
            toe_relative = foot.matrix.inverted_safe() @ toe.matrix
            foot_before = foot.matrix.copy()
            desired = target.matrix.copy()
            desired.translation += Vector((.04,.22,.20))
            target.matrix = desired
            update(rig)
            result = {'foot_turn':limb_ik._rotation_error(foot_before,foot.matrix),
                      'shin_relative_error':limb_ik._rotation_error(relative,shin.matrix.inverted_safe()@foot.matrix),
                      'toe_relative_error':limb_ik._rotation_error(toe_relative,foot.matrix.inverted_safe()@toe.matrix)}
            assert result['foot_turn'] > .03, result
            assert result['shin_relative_error'] < 1e-3, result
            assert result['toe_relative_error'] < 1e-3, result
            wanted = {n:rig.pose.bones[n].matrix.copy() for n in (*record['chain'],record['toe'])}
            for enabled in (False,True):
                limb_ik._set_auto_align_selected_target(bpy.context,rig,settings,enabled)
                limb_ik_fk._verify(rig,wanted)
            for mode in ('FK','IK'):
                limb_ik_fk.switch_limb(bpy.context,rig,key,mode)
                limb_ik_fk._verify(rig,wanted)
            report['motion'][side]=result
            target.matrix_basis=original
            update(rig)
        bpy.ops.wm.open_mainfile(filepath=str(PREVIEW))
        rig=bpy.data.objects['CoshaRig']
        update(rig)
        limb_ik._validate_inventory(rig)
        feet.validate(rig)
        report['reopen']=True
        report['source_unchanged']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()==checksum
        report['ok']=True
    except Exception as exc:
        report.update(error=str(exc),traceback=traceback.format_exc())
        raise
    finally:
        REPORT.write_text(json.dumps(report,indent=2),encoding='utf8')
        print('X_FOOT_AUTO_ALIGN_RESULT',json.dumps(report),flush=True)

if __name__=='__main__': main()
