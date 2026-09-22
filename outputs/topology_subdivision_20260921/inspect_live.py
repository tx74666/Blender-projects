import bpy, json, traceback
from pathlib import Path
import character_designer as addon
C = bpy.context
report = dict(version=addon.bl_info['version'], module=addon.__file__, mode=C.mode,
              active=C.object.name if C.object else None, objects=[])
try:
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not hasattr(obj, 'character_designer_finger_bank'): continue
        bank = obj.character_designer_finger_bank
        if not len(bank.slots): continue
        state = obj.character_designer_finger_workflow
        report['objects'].append(dict(name=obj.name, mesh=obj.data.name, vertices=len(obj.data.vertices),
            modifiers=[dict(name=m.name,type=m.type,visible=m.show_viewport,edit=m.show_in_editmode,
                            level=getattr(m,'levels',None),rig=getattr(m,'object',None).name if getattr(m,'object',None) else None)
                       for m in obj.modifiers],
            nonzero_keys=[(k.name,k.value) for k in list(obj.data.shape_keys.key_blocks)[1:] if abs(k.value)>1e-7] if obj.data.shape_keys else [],
            active=bank.active,status=bank.status,dirty=bank.needs_recheck,
            slots=[dict(name=s.name,error=s.error,confirmed=s.guide.confirmed,revision=s.guide.revision) for s in bank.slots],
            workflow=dict(source=state.source.name if state.source else None,status=state.status,
                          pairs=[dict(name=p.name,applied=p.applied,recipe=bool(p.recipe)) for p in state.pairs])))
except Exception:
    report['error']=traceback.format_exc()
finally:
    Path(r'D:\Blender\Projects\Character\X\outputs\topology_subdivision_20260921\live_before.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    C.area.type='VIEW_3D'
