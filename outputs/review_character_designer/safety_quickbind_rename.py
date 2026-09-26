import sys,json
from pathlib import Path
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import bpy
from character_designer import quick_bind as q
for item in tuple(bpy.data.objects):
    bpy.data.objects.remove(item,do_unlink=True)
rig=bpy.data.objects.new('Rig',bpy.data.armatures.new('RigData'))
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,x in [('A',0),('B',2)]:
    bone=rig.data.edit_bones.new(name)
    bone.head=(x,0,0); bone.tail=(x,0,1)
bpy.ops.object.mode_set(mode='OBJECT')
def mesh(name):
    data=bpy.data.meshes.new(name+'Data')
    data.from_pydata([(0,0,0),(1,0,0),(0,1,0)],[],[(0,1,2)])
    obj=bpy.data.objects.new(name,data)
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new('Existing binding','ARMATURE').object=rig
    return obj
body=mesh('Body'); obj=mesh('Clothes')
for target,a in [(body,.8),(obj,.5)]:
    target.vertex_groups.new(name='A').add([0,1,2],a,'REPLACE')
    target.vertex_groups.new(name='B').add([0,1,2],1-a,'REPLACE')
rig.pose.bones['A'].location.x=1.0
def positions():
    rig.update_tag(refresh={'OBJECT'})
    obj.update_tag(refresh={'OBJECT','DATA'})
    bpy.context.view_layer.update()
    return [list(v.co) for v in obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
before=positions()
q.bind_weights(bpy.context,obj,rig,body=body)
# This is the normal RNA edit made when a user renames a bone in Blender.
# Blender itself renames its bound vertex groups automatically.
rig.data.bones['A'].name='Renamed_A'
groups_after_rename=list(obj.vertex_groups.keys())
result=q.restore_binding(bpy.context,obj)
after=positions()
report={'before_original_binding':before,'after_restore':after,
        'max_coordinate_delta':max(abs(a-b) for pa,pb in zip(before,after) for a,b in zip(pa,pb)),
        'groups_after_bone_rename':groups_after_rename,
        'groups_after_restore':list(obj.vertex_groups.keys()),
        'weights_after_restore':{g.name:g.weight(0) for g in obj.vertex_groups},
        'bones':list(rig.data.bones.keys()),'result':result,'has_backup':q.has_binding_backup(obj)}
print('QUICK_BIND_RENAME_REPRO',json.dumps(report))
Path(r'D:\Blender\Projects\Character\X\outputs\review_character_designer\safety_quickbind_rename.json').write_text(json.dumps(report,indent=2))
