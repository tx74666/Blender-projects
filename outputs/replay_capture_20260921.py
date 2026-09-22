"""Replay an exported live selection in an isolated factory-startup process."""
import hashlib
import json
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Matrix
sys.path.insert(0,'D:/MyRepository/Blender-addons-by-Randy/addons')
import character_designer
from character_designer import finger_bank as bank, finger_definition as definition, finger_definition_ui as ui

folder=Path('D:/Blender/Projects/Character/X/outputs')
data=json.loads((folder/'capture_repro_20260921.json').read_text())
character_designer.register()
mesh=bpy.data.meshes.new('CaptureRepro')
mesh.from_pydata(data['vertices'],data['edges'],data['faces'])
obj=bpy.data.objects.new('CaptureRepro',mesh)
bpy.context.collection.objects.link(obj)
for other in bpy.context.selected_objects: other.select_set(False)
obj.select_set(True)
bpy.context.view_layer.objects.active=obj
obj.matrix_world=Matrix(data['matrix'])
assert Matrix(data['plane'])==Matrix.Identity(4)
obj.shape_key_add(name='Basis')
state=obj.character_designer_finger_bank
state.survey=data['survey']
bpy.context.scene.character_designer_finger_setup=obj
with ui.reference_write():
    for name,values in data['slots'].items():
        slot=bank._slot(state,name)
        for field in bank.FIELDS:
            value=values[field]
            if field in {'source','bend_source','pending_source'}: value=obj if value else None
            setattr(slot.guide,field,value)
        slot.error,slot.bones=values['error'],values['bones']
state.active=data['active']
bpy.ops.object.mode_set(mode='EDIT')
bm=bmesh.from_edit_mesh(mesh)
definition._index(bm)
for seq in (bm.verts,bm.edges,bm.faces):
    for item in seq: item.select_set(False)
for index in data['selection']['ids']: bm.faces[index].select_set(True)
bpy.context.tool_settings.mesh_select_mode=(False,False,True)
bmesh.update_edit_mesh(mesh)

def shape():
    live=bmesh.from_edit_mesh(mesh)
    return hashlib.sha256(repr(([tuple(v.co) for v in live.verts],
          [[v.index for v in f.verts] for f in live.faces],
          [f.index for f in live.faces if f.select])).encode()).hexdigest()

before=shape()
assert bpy.ops.character_designer.finger_setup(action='CAPTURE')=={'FINISHED'}
summary=dict(version=character_designer.bl_info['version'],geometry_and_selection_unchanged=shape()==before,
             warnings=json.loads(state.survey)['warnings'],sides={})
for name in ('MIDDLE.L','MIDDLE.R'):
    slot=state.slots[name]
    summary['sides'][name]=dict(record=bool(slot.guide.record),error=slot.error,confirmed=slot.guide.confirmed)
assert summary['geometry_and_selection_unchanged']
assert not state.slots['MIDDLE.L'].error
assert definition.frame(bank.scoped(bpy.context,state.slots['MIDDLE.L'].guide),require_confirmed=True)['internal']
assert 'Left/right finger surfaces differ' in summary['warnings']['MIDDLE']
assert 'rebind' not in summary['warnings']['MIDDLE'].lower()
(folder/'capture_replay_20260921.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print('REAL_CAPTURE_REPLAY_PASS',summary)
