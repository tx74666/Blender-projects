import bpy, json, traceback
from pathlib import Path
import character_designer
character_designer._reload_addon_deferred()
exec(compile(Path(r'D:\Blender\Projects\Character\X\outputs\topology_subdivision_20260921\rebind_live.py').read_text(encoding='utf8'),'rebind_live.py','exec'))
from character_designer import finger_workflow as work, finger_layout as layout
from character_designer import finger_targets as targets, finger_subdivision as sub

C=bpy.context
obj=bpy.data.objects['Cosha']
state=obj.character_designer_finger_workflow
source=state.source
before=layout.fingerprint(obj)
report=dict(vertices=[list(v.co) for v in source.vertices],
            faces=[list(p.vertices) for p in source.polygons],
            matrix=[list(row) for row in obj.matrix_world],
            configuration=sub.configuration(obj),pairs={},bones={})
for pair in state.pairs:
    report['pairs'][pair.name]=dict(recipe=json.loads(pair.recipe),
        joints=[{k:getattr(j,k) for k in ('position','width','inner_spacing','outer_spacing')} for j in pair.joints],
        fill_between=pair.fill_between,phase=work.committed_phase(pair,state))
try:
    entries=work.plans(C,supports_only=True)
    report['index_supports']={key:dict(rings=len(plan['rings']),subdivision=bool(plan.get('subdivision'))) for pair,key,recipe,plan in entries}
except Exception as exc: report['index_supports_error']=str(exc)
_,rig=targets.owner(C)
chains=targets.index(rig)
for key in ('PINKY.L','PINKY.R'):
    slot=obj.character_designer_finger_bank.slots[key]
    report['bones'][key]=dict(saved=json.loads(slot.bones) if slot.bones else None,current=targets.signature(chains[key]))
report['unchanged']=before==layout.fingerprint(obj)
Path(r'D:\Blender\Projects\Character\X\outputs\topology_subdivision_20260921\live_planning.json').write_text(json.dumps(report),encoding='utf8')
other=next(a for a in C.screen.areas if a.type=='VIEW_3D')
view=other.spaces.active.region_3d
values={k:getattr(view,k).copy() if hasattr(getattr(view,k),'copy') else getattr(view,k) for k in ('view_distance','view_location','view_rotation','view_perspective')}
C.area.type='VIEW_3D'
for k,value in values.items(): setattr(C.space_data.region_3d,k,value)
