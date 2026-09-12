"""Disposable actual-X forearm range acceptance; production X is never saved."""
import bpy,copy,hashlib,json,math,runpy,sys,traceback
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from mathutils import Vector

CANON=Path(r'D:\MyRepository\Blender-addons-by-Randy')
sys.path[:0]=[str(CANON/'addons'),str(CANON/'tests')]
import character_designer as cd
from character_designer import forearm_twist as rt,forearm_twist_edit as editing,limb_ik
from character_designer.forearm_twist_symmetry import mirror_ring_pairs
import test_forearm_twist_blender as fixtures

OUT=Path(__file__).parent
SOURCE=OUT/'fixtures/X_forearm_ranges_0555_source.blend'
PREVIEW=OUT/'fixtures/X_forearm_ranges_0555_preview.blend'
REPORT=OUT/'forearm_ranges_actual_0555.json'
ANIMATION=runpy.run_path(str(OUT/'verify_root_height_0523_saved.py'))['animation_state']
report={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'production_saved':False,'checks':[]}

def emit(label,**values):
    report['checks'].append(dict(check=label,**values));print('ACTUAL_RANGE',label,json.dumps(values),flush=True)
def same_pose(arm,before,label):fixtures.assert_pose_snapshot(arm,before,label)
def key_snapshot(obj):return fixtures.key_snapshot(obj,tuple(obj.data.shape_keys.key_blocks.keys()))
def source_snapshot(obj):
    owned={r['key'] for r in rt._records(obj).values()}
    return fixtures.structure_snapshot(bpy.data.objects['CoshaRig'],obj),fixtures.key_snapshot(obj,tuple(n for n in obj.data.shape_keys.key_blocks.keys() if n not in owned))
def activate(obj):
    if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    for other in bpy.context.selected_objects:other.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
def cage(obj,*,uncorrected=False):
    """Evaluate actual Blender armature deformation before downstream smoothing."""
    modifiers=[(m,m.show_viewport) for m in list(obj.modifiers)[1:]]
    owned=[obj.data.shape_keys.key_blocks[r['key']] for r in rt._records(obj).values()]
    mutes=[k.mute for k in owned];busy=rt._BUSY;rt._BUSY=True
    try:
        for m,_ in modifiers:m.show_viewport=False
        if uncorrected:
            for k in owned:k.mute=True
        bpy.context.view_layer.update()
        eval_obj=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=eval_obj.to_mesh()
        try:result=[v.co.copy() for v in mesh.vertices]
        finally:eval_obj.to_mesh_clear()
    finally:
        for k,mute in zip(owned,mutes):k.mute=mute
        for m,visible in modifiers:m.show_viewport=visible
        bpy.context.view_layer.update();rt._BUSY=busy
    assert len(result)==len(obj.data.vertices)
    return result
def check_geometry(obj,side,degrees):
    actual,baseline=cage(obj),cage(obj,uncorrected=True)
    records=rt._records(obj);interiors=set()
    for r in records.values():
        first,last=r['rings'][r['range_start']]['position'],r['rings'][r['range_end']]['position']
        interiors.update(i for i,t in zip(r['vertices'],r['positions']) if first<t<last)
    outside=set(range(len(actual)))-interiors
    error=max(((actual[i]-baseline[i]).length for i in outside),default=0.)
    assert error<1.5e-5,('Outside extra deformation',side,degrees,error)
    r=records[side]
    boundary=set(r['rings'][r['range_start']]['vertices']+r['rings'][r['range_end']]['vertices'])
    boundary_error=max((actual[i]-baseline[i]).length for i in boundary)
    assert boundary_error<1.5e-5,('Boundary extra deformation',side,degrees,boundary_error)
    interior_error=max((actual[i]-baseline[i]).length for i in r['rings'][3]['vertices'])
    assert interior_error>1e-5,('No actual correction effect',side,degrees,interior_error)
    overlays=rt.overlay_geometry(bpy.context,all_rings=True)
    overlay_error=0.
    for layer in overlays:
        ids=r['rings'][layer['index']]['vertices']
        expected=[obj.matrix_world@actual[i] for i in ids+ids[:1]]
        overlay_error=max(overlay_error,max((Vector(a)-b).length for a,b in zip(layer['points'],expected)))
    assert overlay_error<1.5e-5,('World overlay mismatch',side,degrees,overlay_error)
    before=key_snapshot(obj)
    for _ in range(3):rt.update_runtime(bpy.context.scene,bpy.context.evaluated_depsgraph_get())
    assert key_snapshot(obj)==before,'Runtime drift'
    emit('Actual cage deformation',side=side,degrees=degrees,outside_vertex_count=len(outside),outside_error=error,boundary_error=boundary_error,interior_effect=interior_error,overlay_error=overlay_error)

def main():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
    cd.register()
    obj,arm=bpy.data.objects['Cosha'],bpy.data.objects['CoshaRig'];activate(obj)
    report['wrist_sync']=limb_ik.sync_wrist_local_axes(arm)
    rt.update_runtime(bpy.context.scene)
    original_json=obj.get(rt.RECORD_KEY);original_keys=key_snapshot(obj)
    original_pose=fixtures.pose_snapshot(arm);original_source=source_snapshot(obj);original_animation=ANIMATION()
    report['original_stale_records']={side:record['topology']!=rt._topology(obj.data) for side,record in rt._records(obj).items()}
    for side in ('L','R'):
        runtime_record=rt.start_test(bpy.context,obj,side,symmetry=True,recapture=True)
        assert len(runtime_record['rings'])>=6
        rt.set_range(bpy.context,1,5);rt.set_ratio(bpy.context,3,.62)
        editing.set_current(bpy.context,1)
        for degrees in (90,-90):
            rt._test_pose(bpy.context,math.radians(degrees))
            check_geometry(obj,side,degrees)
        rt.finish_test(bpy.context,confirm=False)
        assert obj[rt.RECORD_KEY]==original_json,'Cancel lost stale backup record'
        assert key_snapshot(obj)==original_keys,'Cancel lost old corrective buffers'
        same_pose(arm,original_pose,'Actual-X Cancel')
        assert source_snapshot(obj)==original_source
        assert ANIMATION()==original_animation
        emit('Recapture Cancel exact',side=side,records=True,keys=True,poses=True,original_sources=True,animation=True)
    # A failed explicit recapture must not replace stale recovery information.
    with patch.object(rt,'_test_pose',side_effect=RuntimeError('injected actual-X preview pose failure')):
        try:rt.start_test(bpy.context,obj,'L',symmetry=True,recapture=True)
        except RuntimeError as exc:assert 'injected' in str(exc)
        else:raise AssertionError('Expected failed explicit recapture')
    assert rt._SESSION is None and rt.PREVIEW_KEY not in obj
    assert obj[rt.RECORD_KEY]==original_json and key_snapshot(obj)==original_keys
    same_pose(arm,original_pose,'Failed actual-X recapture')
    emit('Failed explicit recapture is atomic',records=True,keys=True,poses=True)
    rt.start_test(bpy.context,obj,'L',symmetry=True,recapture=True)
    rt.set_range(bpy.context,1,5);rt.set_ratio(bpy.context,3,.62);editing.set_current(bpy.context,3)
    rt.finish_test(bpy.context,confirm=True)
    confirmed=copy.deepcopy(rt._records(obj));confirmed_keys=key_snapshot(obj)
    pairs=dict(mirror_ring_pairs(obj,arm,confirmed['L'],confirmed['R']))
    assert all(confirmed['R'][key]==pairs[confirmed['L'][key]] for key in ('range_start','range_end','current_ring'))
    assert source_snapshot(obj)==original_source and ANIMATION()==original_animation
    same_pose(arm,original_pose,'Confirm restores original actual-X pose')
    bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW),copy=True)
    bpy.ops.wm.open_mainfile(filepath=str(PREVIEW),load_ui=False,use_scripts=False)
    obj,arm=bpy.data.objects['Cosha'],bpy.data.objects['CoshaRig'];activate(obj)
    rt.update_runtime(bpy.context.scene)
    assert rt._records(obj)==confirmed
    assert key_snapshot(obj)==confirmed_keys
    same_pose(arm,original_pose,'Actual-X preview save/reopen')
    assert source_snapshot(obj)==original_source and ANIMATION()==original_animation
    emit('Confirm and save/reopen',range=[confirmed['L']['range_start'],confirmed['L']['range_end']],current=confirmed['L']['current_ring'],loop_counts={s:len(r['rings']) for s,r in confirmed.items()},pair_count=len(pairs),original_sources=True,animation=True,output=str(PREVIEW))
    # Explicit recapture keeps manual shares and range/current identities when
    # those loops still exist in the refreshed topology capture.
    before_recapture_json=obj[rt.RECORD_KEY]
    recaptured=rt.start_test(bpy.context,obj,'L',symmetry=True,recapture=True)
    previous_by_ids={frozenset(r['vertices']):r for r in confirmed['L']['rings']}
    assert all(r['ratio']==previous_by_ids[frozenset(r['vertices'])]['ratio'] for r in recaptured['rings'])
    for field in ('range_start','range_end','current_ring'):
        assert frozenset(recaptured['rings'][recaptured[field]]['vertices'])==frozenset(confirmed['L']['rings'][confirmed['L'][field]]['vertices'])
    rt.finish_test(bpy.context,confirm=False)
    assert obj[rt.RECORD_KEY]==before_recapture_json and key_snapshot(obj)==confirmed_keys
    same_pose(arm,original_pose,'Matching actual-X explicit recapture Cancel')
    emit('Matching-loop explicit recapture preserves edits',shares=True,range_anchors=True,current_identity=True,cancel_exact=True)
    # Test editing an already-keyed hand without replacing its pose/animation.
    inventory=limb_ik._validate_inventory(arm)
    target=arm.pose.bones[inventory['rigs'][('ARM','L')]['target'].name]
    target.keyframe_insert('rotation_euler',frame=bpy.context.scene.frame_current)
    keyed_animation=ANIMATION();keyed_pose=fixtures.pose_snapshot(arm)
    current_json=obj[rt.RECORD_KEY]
    rt.start_test(bpy.context,obj,'L',symmetry=True)
    assert rt._SESSION['pose_locked']
    same_pose(arm,keyed_pose,'Keyed target range-edit entry')
    rt.set_ratio(bpy.context,3,.42)
    same_pose(arm,keyed_pose,'Keyed target profile edit')
    rt.finish_test(bpy.context,confirm=False)
    same_pose(arm,keyed_pose,'Keyed target range-edit Cancel')
    assert ANIMATION()==keyed_animation and obj[rt.RECORD_KEY]==current_json
    emit('Animated target profile editing',pose_locked=True,poses=True,animation=True,record_cancel=True)
    report['ok']=True

try:main()
except Exception as exc:
    report['ok']=False;report['error']=str(exc);report['traceback']=traceback.format_exc();print(report['traceback'],flush=True)
finally:
    report['source_unchanged']=report['source_sha256']==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    REPORT.write_text(json.dumps(report,indent=2),encoding='utf8')
    print('ACTUAL_FOREARM_ACCEPTANCE',json.dumps({'ok':report.get('ok'), 'error':report.get('error'),'report':str(REPORT),'source_unchanged':report['source_unchanged']}),flush=True)
if not report.get('ok'):raise RuntimeError(report.get('error','Actual-X acceptance failed'))
