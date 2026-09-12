"""Read-only code audit supplemented by disposable actual-X removal probes."""
import bpy,sys,json,runpy,traceback
from pathlib import Path
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons',r'D:\MyRepository\Blender-addons-by-Randy\tests']
import character_designer as cd
from character_designer import forearm_twist as rt
import test_forearm_twist_blender as fixtures
OUT=Path(__file__).parent
PATH=OUT/'fixtures/X_forearm_ranges_0555_preview.blend'
report={}
def open_copy():
    bpy.ops.wm.open_mainfile(filepath=str(PATH),load_ui=False,use_scripts=False)
    if not hasattr(bpy.types.WindowManager,'character_designer_limb_ik'):cd.register()
    obj=bpy.data.objects['Cosha'];arm=bpy.data.objects['CoshaRig']
    fixtures.activate_mesh(obj);rt.update_runtime(bpy.context.scene)
    return obj,arm
obj,arm=open_copy()
before_pose=fixtures.pose_snapshot(arm);before_structure=fixtures.structure_snapshot(arm,obj)
owned={r['key'] for r in rt._records(obj).values()}
originals=fixtures.key_snapshot(obj,tuple(k.name for k in obj.data.shape_keys.key_blocks if k.name not in owned))
rt.remove_paired_calibration(bpy.context,obj)
assert rt.RECORD_KEY not in obj
assert not any(k in obj.data.shape_keys.key_blocks for k in owned)
assert fixtures.structure_snapshot(arm,obj)==before_structure
assert fixtures.key_snapshot(obj,tuple(originals))==originals
fixtures.assert_pose_snapshot(arm,before_pose,'Actual paired calibration removal')
report['normal_actual_x_remove']={'ok':True,'native_rest_pose_weights_preserved':True,'artist_keys_preserved':True}
# Common real-world preflight refusal: an artist key derives from R's output.
# The ownership resolver also auto-repairs a renamed L key, which is a write.
obj,arm=open_copy()
records=rt._records(obj)
left=rt._managed_key(obj,'L',records['L']);right=rt._managed_key(obj,'R',records['R'])
busy=rt._BUSY;rt._BUSY=True
try:
    left.name='Artist Friendly Forearm L'
    dependent=obj.shape_key_add(name='Artist derivative of right correction')
    dependent.relative_key=right
    before_names=list(obj.data.shape_keys.key_blocks.keys());before_json=obj[rt.RECORD_KEY]
    try:rt.remove_paired_calibration(bpy.context,obj)
    except ValueError as exc:refusal=str(exc)
    else:raise AssertionError('Expected dependent right-key refusal')
    after_names=list(obj.data.shape_keys.key_blocks.keys())
    assert obj[rt.RECORD_KEY]==before_json and len(before_names)==len(after_names)
    report['rename_then_other_side_dependency_refusal']={'error':refusal,'keys_before':before_names,'keys_after':after_names,'any_deleted':False,'left_name_changed_on_refusal':before_names!=after_names}
finally:rt._BUSY=busy
(OUT/'forearm_remove_atomicity_0555.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('PAIRED_REMOVE_AUDIT',json.dumps(report),flush=True)
