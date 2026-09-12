import sys,json,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import bpy
import character_designer
character_designer.register()
source=Path(r'D:\Blender\Projects\Character\X\X.blend')
sha=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
rig=bpy.data.objects['CoshaRig']
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
for obj in bpy.context.selected_objects:obj.select_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='POSE')
bpy.context.scene.tool_settings.use_keyframe_insert_auto=False
rig.data.use_mirror_x=False
areas=[(w,a,r) for w in bpy.context.window_manager.windows for a in w.screen.areas if a.type=='VIEW_3D' for r in a.regions if r.type=='WINDOW']
assert areas
window,area,region=areas[0]
def update():
    rig.data.update_tag();rig.update_tag(refresh={'OBJECT'});bpy.context.view_layer.update();bpy.context.evaluated_depsgraph_get().update()
def center(pb):
    anchor=pb.custom_shape_transform or pb
    scale=pb.custom_shape_scale_xyz*(pb.bone.length if pb.use_custom_shape_bone_size else 1.)
    matrix=rig.matrix_world@anchor.matrix@Matrix.LocRotScale(pb.custom_shape_translation,pb.custom_shape_rotation_euler.to_quaternion(),scale)
    return sum((matrix@v.co for v in pb.custom_shape.data.vertices),Vector())/len(pb.custom_shape.data.vertices)
update()
original={p.name:p.matrix_basis.copy() for p in rig.pose.bones}
results={};skipped=[]
for pb in rig.pose.bones:
    if not pb.custom_shape or not any(c.name=='Animation' and c.is_visible for c in pb.bone.collections) or pb.bone.hide:
        continue
    if pb.bone.use_connect or all(pb.lock_location):
        skipped.append({'name':pb.name,'reason':'connected_rotation_control' if pb.bone.use_connect else 'translation_locked'})
        continue
    for other in rig.pose.bones:other.select=other==pb
    rig.data.bones.active=pb.bone
    result={'local_location':pb.bone.use_local_location,'anchor':pb.custom_shape_transform.name if pb.custom_shape_transform else pb.name,'axes':[]}
    for axis in range(3):
        for sign in (1.,-1.):
            for p in rig.pose.bones:p.matrix_basis=original[p.name]
            update()
            old=rig.matrix_world@pb.head
            oldcenter=center(pb)
            delta=Vector((0.,0.,0.));delta[axis]=.01*sign
            constraint=tuple(i==axis for i in range(3))
            with bpy.context.temp_override(window=window,area=area,region=region):
                status=bpy.ops.transform.translate(value=delta,orient_type='GLOBAL',constraint_axis=constraint,use_proportional_edit=False)
            update()
            movement=rig.matrix_world@pb.head-old
            display_movement=center(pb)-oldcenter
            result['axes'].append({'axis':'XYZ'[axis],'sign':sign,'status':list(status),'head_delta':list(movement),'head_error':(movement-delta).length,'display_delta':list(display_movement),'display_error':(display_movement-delta).length})
    results[pb.name]=result
for p in rig.pose.bones:p.matrix_basis=original[p.name]
update()
report={'saved_orientation':bpy.context.scene.transform_orientation_slots[0].type,'source_unchanged':sha==hashlib.sha256(source.read_bytes()).hexdigest(),'controls_tested':len(results),'cases':sum(len(r['axes']) for r in results.values()),'max_head_error':max(x['head_error'] for r in results.values() for x in r['axes']),'head_failures':[(n,x) for n,r in results.items() for x in r['axes'] if x['head_error']>2e-6],'display_failures':[(n,x) for n,r in results.items() for x in r['axes'] if x['display_error']>2e-5],'skipped':skipped,'results':results}
Path(r'D:\Blender\Projects\Character\X\outputs\rig\animation_global_translation_readonly.json').write_text(json.dumps(report,indent=2))
print('ANIMATION_TRANSLATION_AUDIT',json.dumps({k:v for k,v in report.items() if k!='results'}),flush=True)
