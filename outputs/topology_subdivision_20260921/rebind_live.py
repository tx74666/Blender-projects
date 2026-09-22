"""Repair workflow metadata in the existing X session; never apply or save."""
import bpy, json, hashlib, traceback, time
from pathlib import Path
import character_designer as addon
from character_designer import finger_bank as bank, finger_workflow as work
from character_designer import finger_workflow_ui as ui, finger_definition_ui as guides
from character_designer import finger_layout as layout, finger_chain, finger_subdivision

C = bpy.context
report = dict(version=addon.bl_info['version'], fingers={}, started=time.time())
obj = bpy.data.objects['Cosha']

def rigs():
    return {rig.name: dict(bones={bone.name:(list(bone.head_local),list(bone.tail_local),[list(r) for r in bone.matrix_local]) for bone in rig.data.bones},
                          pose={bone.name:[list(r) for r in bone.matrix_basis] for bone in rig.pose.bones})
            for rig in bpy.data.objects if rig.type=='ARMATURE'}

try:
    assert tuple(addon.bl_info['version']) >= (0,61,46)
    if C.object and C.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    for selected in C.selected_objects: selected.select_set(False)
    obj.select_set(True)
    C.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT')
    ui.hide(keep_enabled=True)
    guides.hide(invalidate=True)
    before=layout.fingerprint(obj)
    old_mesh=obj.data.as_pointer()
    old_rigs=rigs()
    old_values={key.name:key.value for key in obj.data.shape_keys.key_blocks}
    state=obj.character_designer_finger_workflow
    report['adapted']=work.refresh_topology(C)
    bank.recheck(C)
    try:
        work.check_source(obj,state)
        report['released_stale_source']=False
    except ValueError as exc:
        report['old_source_error']=str(exc)
        work.release(C)
        report['released_stale_source']=True
    for digit in bank.detect.DIGITS:
        item={}
        report['fingers'][digit]=item
        try:
            bank.select(C,digit,'L')
            pair=work.prepare(C)
            item.update(prepared=True,positions=[j.position for j in pair.joints],widths=[j.width for j in pair.joints],
                        phase=work.committed_phase(pair,state))
            entries=work.plans(C,preview=True)
            item['preview']={key:dict(rings=len(plan['rings']),subdivision=bool(plan.get('subdivision')),
                                     warning=plan.get('warning','')) for _,key,recipe,plan in entries}
            try:
                finger_chain.plans(C,entries)
                item['bone_preflight']=True
            except ValueError as exc: item['bone_error']=str(exc)
        except Exception as exc:
            item['error']=str(exc)
        assert layout.fingerprint(obj)==before, digit+': mesh data changed during metadata repair'
        assert rigs()==old_rigs, digit+': rig data changed during metadata repair'
    bank.select(C,'INDEX','L')
    report['slots']={slot.name:slot.error for slot in obj.character_designer_finger_bank.slots}
    report['configuration']=finger_subdivision.configuration(obj)
    report.update(mesh_unchanged=layout.fingerprint(obj)==before,mesh_identity_unchanged=obj.data.as_pointer()==old_mesh,
                  rig_unchanged=rigs()==old_rigs,key_values_unchanged={key.name:key.value for key in obj.data.shape_keys.key_blocks}==old_values,
                  vertices=len(obj.data.vertices),shape_keys=len(obj.data.shape_keys.key_blocks))
    guides.show()
    try: ui.show(C)
    except Exception as exc: report['preview_error']=str(exc)
except Exception:
    report['error']=traceback.format_exc()
finally:
    report['seconds']=time.time()-report['started']
    Path(r'D:\Blender\Projects\Character\X\outputs\topology_subdivision_20260921\live_after.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    C.area.type='VIEW_3D'
