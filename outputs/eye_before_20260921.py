import json, time
from pathlib import Path
import bpy
from character_designer import finger_bank as bank, finger_workflow_ui as ui, finger_definition_ui as guides
C=bpy.context
obj=bank.active_object(C)
s=obj.character_designer_finger_workflow
b=obj.character_designer_finger_bank
def preview(p):
    return None if not p else {k:p.get(k) for k in ('kind','active','side','all','stale','allocations')} | {'groups':len(p.get('groups',[])),'labels':len(p.get('labels',[])), 'batches':p.get('batches') is not None, 'modifier_matches':p.get('modifier_stamp')==ui._modifier_stamp(obj)}
def snap():
    return dict(active=b.active, master=guides.overlays_enabled(C), child=s.preview_enabled, guides=guides._visible,status=s.status, preview=preview(ui._preview), pending=preview(ui._refresh_request), valid=bool(ui._valid(C)))
out={'before':snap()}
try:
    for enabled in (False,True):
        start=time.perf_counter()
        C.scene.character_designer_finger_definition.overlays_enabled=enabled
        ui._refresh(); guides._refresh_display(); C.view_layer.update()
        out[str(enabled)]={'ms':(time.perf_counter()-start)*1000, **snap()}
except Exception as exc: out['error']=repr(exc)
Path(r'D:\Blender\Projects\Character\X\outputs\eye_before_20260921.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
C.area.type='VIEW_3D'
