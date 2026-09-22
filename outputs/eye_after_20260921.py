import json, time, statistics, traceback
from pathlib import Path
from unittest.mock import patch
import bpy
import character_designer as addon
from character_designer import finger_layout as old_layout
C=bpy.context
obj=C.scene.character_designer_finger_setup
before=old_layout.fingerprint(obj)
rig=C.scene.character_designer_setup.rig
bones=tuple((b.name,tuple(v for row in b.matrix_local for v in row)) for b in rig.data.bones)
addon._reload_addon_deferred()
import character_designer as addon
from character_designer import finger_bank as bank, finger_workflow_ui as ui, finger_definition_ui as guides
from character_designer import finger_preview_proof as proof, finger_workflow as work, finger_layout as layout
obj=bank.active_object(C)
b=obj.character_designer_finger_bank
original=b.active
C.view_layer.update()
guides.show(invalidate=False)
ui.show(C)
guides._display_request=C.scene,obj; guides._refresh_display()
initial=ui._preview
report=dict(version=addon.bl_info['version'], active=original, initial_stale=initial.get('stale'), groups=len(initial['groups']))
def run_check():
    try:
        timings={}
        def cycle_master():
            bpy.ops.character_designer.finger_definition(action='OVERLAYS')
            bpy.ops.character_designer.finger_definition(action='OVERLAYS')
        def cycle_child():
            bpy.ops.character_designer.finger_workflow(action='PREVIEW')
            bpy.ops.character_designer.finger_workflow(action='PREVIEW')
        with patch.object(proof,'verify',wraps=proof.verify) as verify, patch.object(work,'plans',wraps=work.plans) as plans:
            for name, fn in (('master',cycle_master),('child',cycle_child)):
                values=[]
                for i in range(20):
                    start=time.perf_counter(); fn(); C.view_layer.update(); ui._refresh(); guides._refresh_display()
                    values.append((time.perf_counter()-start)*1000)
                    assert ui.joint_preview_visible(C), (name,i,'missing rings')
                    assert ui._preview is initial, (name,i,'rebuilt lines')
                timings[name]=dict(median_ms=statistics.median(values),max_ms=max(values))
            report['warm_verify_calls']=verify.call_count
            report['warm_plan_calls']=plans.call_count
        bpy.ops.character_designer.finger_setup(action='SIDE');ui._refresh()
        bpy.ops.character_designer.finger_setup(action='SIDE');ui._refresh()
        with patch.object(proof,'verify',wraps=proof.verify) as verify, patch.object(work,'plans',wraps=work.plans) as plans:
            values=[]
            for i in range(20):
                start=time.perf_counter()
                bpy.ops.character_designer.finger_setup(action='SIDE');C.view_layer.update();ui._refresh()
                values.append((time.perf_counter()-start)*1000)
                assert ui.joint_preview_visible(C)
            timings['side']=dict(median_ms=statistics.median(values),max_ms=max(values))
            report['side_verify_calls']=verify.call_count;report['side_plan_calls']=plans.call_count
        report['timings']=timings
        report['same_mesh']=layout.fingerprint(obj)==before
        report['same_bones']=bones==tuple((b.name,tuple(v for row in b.matrix_local for v in row)) for b in rig.data.bones)
        report['active_restored']=b.active==original
    except Exception as exc:
        report['error']=repr(exc);report['traceback']=traceback.format_exc()
    finally:
        if b.active!=original:
            b.active=original;ui.refresh_selection(C);ui._refresh()
        Path(r'D:\Blender\Projects\Character\X\outputs\eye_after_20260921.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return None
bpy.app.timers.register(run_check,first_interval=.5)
C.area.type='VIEW_3D'
