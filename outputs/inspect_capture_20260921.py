"""Read live edit data and export an isolated repro; no capture, reload or save."""
import json
import traceback
from pathlib import Path
import bpy
import character_designer
from character_designer import finger_bank as bank, finger_definition as definition

area = bpy.context.area
obj = bpy.context.object
output = Path('D:/Blender/Projects/Character/X/outputs')
bm = None
report = {}
try:
    state = obj.character_designer_finger_bank
    bm = definition._snapshot(obj, definition._basis_name(obj))
    spec = definition._selection(bpy.context, bm)
    saved = json.loads(state.survey)
    fresh = bank.survey(bpy.context, obj, bm, force=True)
    key = bank._resolve(fresh, spec, bm)
    mate = key[:-1]+('R' if key[-1] == 'L' else 'L')
    report = dict(version=character_designer.bl_info['version'], object=obj.name,
                  active=state.active, selected=key, counts=(len(bm.verts),len(bm.edges),len(bm.faces)),
                  selected_input=spec, status=state.status, saved_warnings=saved['warnings'],
                  fresh_warnings=fresh['warnings'], sides={})
    for name in (key,mate):
        slot=state.slots.get(name)
        entry=report['sides'][name]=dict(error=slot.error, record=bool(slot.guide.record), revision=slot.guide.revision)
        try:
            data=definition.frame(bank.scoped(bpy.context,slot.guide))
            entry['frame_valid']=True
            entry['length']=data['length']
        except Exception as exc: entry['frame_error']=str(exc)
    for name,call in (
        ('current_vertex_map',lambda: bank.detect.vertex_map(bm,fresh['candidates'][key],fresh['candidates'][mate],bank.plane(obj))),
        ('current_ring_surface',lambda: bank._mirrored_ring_surface(bm,fresh['candidates'][key],fresh['candidates'][mate],bank.plane(obj))),
    ):
        try: call(); report[name]='valid'
        except Exception as exc: report[name]=str(exc)
    try:
        record=bank._internal_record(obj,bm,spec,fresh['candidates'][key],key)
        report['fresh_source']='valid'
        try:
            bank.remap_record(record,bm,reflection=bank.plane(obj),target=fresh['candidates'][mate],allow_ring_edits=True)
            report['fresh_mirror']='valid'
        except Exception as exc:
            report['fresh_mirror']=str(exc)
            report['fresh_mirror_trace']=traceback.format_exc()
    except Exception as exc: report['fresh_source']=str(exc)
    slots={slot.name:{field:(getattr(slot.guide,field).name if getattr(slot.guide,field) else None)
                                if field in {'source','bend_source','pending_source'} else getattr(slot.guide,field)
                      for field in bank.FIELDS} | {'error':slot.error,'bones':slot.bones}
           for slot in state.slots}
    fixture=dict(vertices=[list(v.co) for v in bm.verts],edges=[[v.index for v in e.verts] for e in bm.edges],
                 faces=[[v.index for v in f.verts] for f in bm.faces],selection=spec,
                 survey=state.survey,active=state.active,slots=slots,
                 matrix=[list(r) for r in obj.matrix_world],plane=[list(r) for r in bank.plane(obj)])
    (output/'capture_repro_20260921.json').write_text(json.dumps(fixture),encoding='utf-8')
except Exception:
    report['error']=traceback.format_exc()
finally:
    if bm: bm.free()
    (output/'capture_inspection_20260921.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('CAPTURE_READ_ONLY_INSPECTION',report)
    area.type='VIEW_3D'
