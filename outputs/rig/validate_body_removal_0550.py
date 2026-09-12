"""Complete teardown/rollback in a named immutable old-good fixture only."""
import importlib.util
import json
import sys
import traceback
from pathlib import Path

import bpy
from bpy.props import PointerProperty

OUT = Path(__file__).parent
FIXTURE = OUT / 'fixtures/X_body_setup_20260911_053445_231.blend'
REPORT = OUT / 'body_removal_0550_validation.json'
if '--repaired' in sys.argv:
    FIXTURE = OUT / 'fixtures/X_repaired_roll_20260912.blend'
    REPORT = OUT / 'body_removal_repaired_0550_validation.json'
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import (body_setup, body_setup_removal, body_setup_transaction,
                               limb_ik, forearm_twist)
spec = importlib.util.spec_from_file_location('scene_checks', OUT / 'validate_body_setup_0550.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
h = checks.h


def key_data():
    return h.digest([[key.name, h.properties(key),
                     [[block.name, h.rna_values(block), [list(v.co) for v in block.data]]
                      for block in key.key_blocks]] for key in bpy.data.shape_keys])


def rest(rig):
    return {bone.name: [list(row) for row in bone.matrix_local] for bone in rig.data.bones
            if bone.get(limb_ik.OWNER_KEY) not in limb_ik.GENERATED_CONTROL_OWNERS}


def native_mesh_data():
    return h.digest([[obj.name, obj.as_pointer(), obj.data.as_pointer(),
                      [[list(v.co), [(g.group, g.weight) for g in v.groups]] for v in obj.data.vertices],
                      [[m.name, h.rna_values(m)] for m in obj.modifiers],
                      h.properties(obj)] for obj in bpy.data.objects if obj.type == 'MESH'
                     and obj.get(limb_ik.OWNER_KEY) not in body_setup_transaction._owners()])


def main():
    report = {'ok': False, 'fixture': str(FIXTURE), 'production_written': False}
    digest = h.sha_file(FIXTURE)
    snapshot = None
    try:
        bpy.utils.register_class(limb_ik.CharacterDesignerLimbIKState)
        bpy.types.WindowManager.character_designer_limb_ik = PointerProperty(type=limb_ik.CharacterDesignerLimbIKState)
        bpy.ops.wm.open_mainfile(filepath=str(FIXTURE), use_scripts=False)
        rig = bpy.data.objects['CoshaRig']
        checks.checks.activate(rig)
        forearm_twist._BUSY = True
        report['generate'] = body_setup.generate(bpy.context, rig)
        native_before, mesh_before, keys_before = rest(rig), native_mesh_data(), key_data()
        pose_before = {pb.name: pb.matrix.copy() for pb in rig.pose.bones}
        collections_before = set(bpy.data.collections.keys())
        objects_before = set(bpy.data.objects.keys())
        original_records = {obj.name: obj[forearm_twist.RECORD_KEY] for obj in bpy.data.objects
                            if forearm_twist.RECORD_KEY in obj}
        plan = body_setup_removal.preflight(bpy.context, rig, keep_native_rest=True)
        snapshot = body_setup_transaction.capture(bpy.context, rig)
        report['remove'] = body_setup_removal.execute(bpy.context, rig, plan)
        assert not body_setup.has_generated(rig)
        assert rest(rig) == native_before, 'native Rest changed during kept-Rest removal'
        assert native_mesh_data() == mesh_before, 'native mesh or modifier changed'
        assert key_data() == keys_before, 'corrective keys changed'
        assert original_records == {name: bpy.data.objects[name][forearm_twist.RECORD_KEY]
                                    for name in original_records}, 'corrective records changed'
        body_setup_transaction.restore(bpy.context, rig, snapshot)
        body_setup_transaction.assert_original_ids(snapshot)
        assert rest(rig) == native_before, 'native Rest changed during rollback'
        assert native_mesh_data() == mesh_before and key_data() == keys_before
        assert set(bpy.data.collections.keys()) == collections_before
        assert set(bpy.data.objects.keys()) == objects_before
        report['rollback_pose_error'] = max(abs(pb.matrix[i][j] - pose_before[pb.name][i][j])
                                             for pb in rig.pose.bones for i in range(4) for j in range(4))
        assert report['rollback_pose_error'] < 2e-5
        assert not body_setup.plan(bpy.context, rig)['blocked']
        body_setup_transaction.discard(snapshot)
        snapshot = None
        report['public_remove'] = body_setup.remove(bpy.context, rig, keep_native_rest=True)
        removed_skin = body_setup._native_skin(rig)
        removed_surfaces = body_setup_removal._bound_surfaces(bpy.context, rig)
        report['regenerate_plan'] = body_setup.plan(bpy.context, rig)
        report['regenerate'] = body_setup.generate(bpy.context, rig)
        assert not body_setup.plan(bpy.context, rig)['blocked']
        rebuilt_skin = body_setup._native_skin(rig)
        report['regenerate_skin_error'] = max(abs(value[i][j] - rebuilt_skin[name][i][j])
                                               for name, value in removed_skin.items()
                                               for i in range(4) for j in range(4))
        report['regenerate_surface_error'] = body_setup_removal._check_surfaces(bpy.context, rig, removed_surfaces)
        assert report['regenerate_skin_error'] < 1e-4
        assert rest(rig) == native_before
        assert native_mesh_data() == mesh_before and key_data() == keys_before
        report['stable_full_remove'] = body_setup.remove(bpy.context, rig, keep_native_rest=True)
        assert not body_setup.has_generated(rig)
        assert rest(rig) == native_before
        assert native_mesh_data() == mesh_before and key_data() == keys_before
        if '--repaired' in sys.argv:
            forearm_twist._BUSY = False
            forearm_twist.update_runtime(bpy.context.scene)
            assert native_mesh_data() == mesh_before and key_data() == keys_before
            assert original_records == {name: bpy.data.objects[name][forearm_twist.RECORD_KEY]
                                        for name in original_records}
            report['runtime_preserved_stale_keys'] = True
            report['existing_calibration_errors'] = dict(forearm_twist._ERRORS)
        report['ok'] = True
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    finally:
        if snapshot is not None:
            body_setup_transaction.discard(snapshot)
        report['source_unchanged'] = h.sha_file(FIXTURE) == digest
        REPORT.write_text(json.dumps(report, indent=2), encoding='utf8')
        print('BODY_REMOVAL_0550', json.dumps(report), flush=True)
    assert report['ok'], report.get('error')


if __name__ == '__main__':
    main()
