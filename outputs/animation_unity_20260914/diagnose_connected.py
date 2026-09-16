import bpy, sys, json
from mathutils import Vector
from pathlib import Path
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import unity_animation as ua
bpy.ops.wm.open_mainfile(filepath=r'D:\Blender\Projects\Character\X\outputs\animation_unity_20260914\source_182347.blend',use_scripts=False,load_ui=False)
rig=bpy.data.objects['CoshaRig']; scene=bpy.context.scene
path=r'D:\Blender\Projects\Character\Animation\UnityExports\Cosha_Walk.cdanim.json'
data=ua.load_package(path); mapping=ua._mapping(rig,data,scene.unit_settings.scale_length)
result=ua.import_test_action(bpy.context,rig,path)
frame_index=min(range(len(data['frames'])),key=lambda i:abs(data['frames'][i]['time']-.71666664))
ua._set_frame(scene,1+data['frames'][frame_index]['time']*scene.render.fps/scene.render.fps_base)
bpy.context.view_layer.update()
expected=ua.expected_world_matrices(rig,data,frame_index,mapping=mapping)
ev=rig.evaluated_get(bpy.context.evaluated_depsgraph_get()); rows=[]
for name,wanted in expected.items():
    pb=rig.pose.bones[name]; actual=rig.matrix_world@ev.pose.bones[name].matrix
    kwargs={'parent_matrix':rig.matrix_world.inverted()@expected[pb.parent.name], 'parent_matrix_local':pb.parent.bone.matrix_local} if pb.parent else {}
    basis=pb.bone.convert_local_to_pose(rig.matrix_world.inverted()@wanted,pb.bone.matrix_local,invert=True,**kwargs)
    error=(actual.translation-wanted.translation).length
    if error>1e-5 or basis.translation.length>1e-5:
        parent_delta=(wanted.translation-expected[pb.parent.name].translation) if pb.parent else None
        rows.append(dict(name=name,connected=pb.bone.use_connect,error=error,location=list(pb.location),wanted_basis=list(basis.translation),parent=pb.parent.name if pb.parent else None,parent_delta=list(parent_delta) if parent_delta else None,parent_axis=list(expected[pb.parent.name].to_3x3().col[1]) if pb.parent else None,parent_length=pb.parent.length if pb.parent else None))
# print('DIAG='+json.dumps(rows,indent=2))
for row in rows:
    name=row['name']; pb=rig.pose.bones[name]
    if not pb.bone.use_connect or Vector(row['wanted_basis']).length<1e-5: continue
    con=pb.constraints.new('LIMIT_LOCATION');con.owner_space='WORLD'
    for axis,coord in zip('xyz',expected[name].translation):
        setattr(con,'use_min_'+axis,True);setattr(con,'use_max_'+axis,True)
        setattr(con,'min_'+axis,coord);setattr(con,'max_'+axis,coord)
bpy.context.view_layer.update(); ev=rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
print('LIMIT_MAX='+str(max((rig.matrix_world@ev.pose.bones[name].matrix.translation-expected[name].translation).length for name in expected)))
for pb in rig.pose.bones:
    for con in list(pb.constraints):pb.constraints.remove(con)
for typename in ['COPY_TRANSFORMS','CHILD_OF']:
    obj=bpy.data.objects.new('Test target',None);bpy.context.scene.collection.objects.link(obj)
    name='shin.R';pb=rig.pose.bones[name]
    obj.matrix_world=expected[name]
    con=pb.constraints.new(typename);con.target=obj
    if typename=='CHILD_OF':con.inverse_matrix=(rig.matrix_world@pb.matrix).inverted()
    bpy.context.view_layer.update();ev=rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    print(typename+' ERROR '+str((rig.matrix_world@ev.pose.bones[name].matrix.translation-expected[name].translation).length))
    pb.constraints.remove(con);bpy.data.objects.remove(obj,do_unlink=True)
