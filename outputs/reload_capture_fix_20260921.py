"""Reload and repeat the requested Capture only if the inspected selection remains."""
import hashlib
import json
from pathlib import Path
import bpy
import bmesh
import character_designer as previous
from character_designer import mesh_mirror

area=bpy.context.area
window=bpy.context.window
obj=bpy.context.object
folder=Path('D:/Blender/Projects/Character/X/outputs')
expected=json.loads((folder/'capture_repro_20260921.json').read_text())

def assets():
    bm=bmesh.from_edit_mesh(obj.data)
    live=([tuple(v.co) for v in bm.verts],[[v.index for v in f.verts] for f in bm.faces],
          [[item.index for item in seq if item.select] for seq in (bm.verts,bm.edges,bm.faces)],
          {name:[tuple(v[bm.verts.layers.shape.get(name)]) for v in bm.verts] for name in bm.verts.layers.shape.keys()})
    rigs=[(rig.name,rig.mode,[(b.name,tuple(tuple(row) for row in b.matrix_local),b.parent.name if b.parent else '')
                           for b in rig.data.bones]) for rig in bpy.data.objects if rig.type=='ARMATURE']
    return dict(mesh=mesh_mirror._fingerprint(obj),live=hashlib.sha256(repr(live).encode()).hexdigest(),
                rigs=hashlib.sha256(repr(rigs).encode()).hexdigest(),object=obj.name,mode=bpy.context.mode)

assert obj.name=='Cosha' and bpy.context.mode=='EDIT_MESH'
before=assets()
other_before={slot.name:slot.guide.record for slot in obj.character_designer_finger_bank.slots if not slot.name.startswith('MIDDLE.')}
previous._reload_addon_deferred()

def verify():
    report={}
    try:
        import character_designer as current
        from character_designer import finger_bank as bank, finger_definition as definition
        report['version']=current.bl_info['version']
        assert current.bl_info['version']==(0,61,53)
        assert assets()==before, 'Reload changed artist data/context'
        bm=definition._snapshot(obj,definition._basis_name(obj))
        try:
            spec=definition._selection(bpy.context,bm)
            same=(spec==expected['selection'] and [list(v.co) for v in bm.verts]==expected['vertices'])
        finally: bm.free()
        if same:
            with bpy.context.temp_override(window=window,area=area):
                result=bpy.ops.character_designer.finger_setup(action='CAPTURE')
            report['capture_result']=list(result)
            assert result=={'FINISHED'}
        else:
            report['capture_skipped']='The user changed the inspected geometry or selection; reload only.'
        report['assets_unchanged']=assets()==before
        assert report['assets_unchanged']
        state=obj.character_designer_finger_bank
        report['warnings']=json.loads(state.survey)['warnings']
        report['sides']={slot.name:dict(error=slot.error,record=bool(slot.guide.record),confirmed=slot.guide.confirmed)
                         for slot in state.slots if slot.name.startswith('MIDDLE.')}
        assert {slot.name:slot.guide.record for slot in state.slots if not slot.name.startswith('MIDDLE.')}==other_before
        if same:
            assert not state.slots['MIDDLE.L'].error and state.slots['MIDDLE.L'].guide.confirmed
            assert 'Left/right finger surfaces differ' in report['warnings']['MIDDLE']
    except Exception:
        import traceback
        report['error']=traceback.format_exc()
    finally:
        (folder/'capture_fix_live_20260921.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('CAPTURE_FIX_LIVE',report)
        area.type='VIEW_3D'
    return None

bpy.app.timers.register(verify,first_interval=.3)
