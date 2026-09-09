import bpy,json,hashlib,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import limb_ik,bone_collections,torso_controls,foot_controls,eye_controls
REPORT=Path(r'D:\Blender\Projects\Character\X\outputs\rig\audit_x_root_rain_shapes_readonly.json')
paths=[Path(r'D:\Blender\Projects\Character\X\X.blend'),Path(r'D:\Blender Samples\Characters\Rain v3.3\rain_v3.2.blend')]
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
character_designer.register()
report={}
def cons(pb):
    return [{'name':c.name,'type':c.type,'target':getattr(getattr(c,'target',None),'name',None),'subtarget':getattr(c,'subtarget',''),'influence':c.influence,'mute':c.mute,'mix_mode':getattr(c,'mix_mode',None),'owner_space':getattr(c,'owner_space',None),'target_space':getattr(c,'target_space',None)} for c in pb.constraints]
def bone(pb,geo=False):
    s=pb.custom_shape
    result={'name':pb.name,'parent':pb.parent.name if pb.parent else None,'length':pb.length,'deform':pb.bone.use_deform,'hide':pb.bone.hide,'hide_select':pb.bone.hide_select,'collections':[{'name':c.name,'visible':c.is_visible,'visible_effective':c.is_visible_effectively} for c in pb.bone.collections],'head':list(pb.head),'tail':list(pb.tail),'basis':[list(r) for r in pb.matrix_basis],'shape':s.name if s else None,'shape_transform':pb.custom_shape_transform.name if pb.custom_shape_transform else None,'shape_translation':list(pb.custom_shape_translation),'shape_rotation':list(pb.custom_shape_rotation_euler),'shape_scale':list(pb.custom_shape_scale_xyz),'shape_bone_size':pb.use_custom_shape_bone_size,'constraints':cons(pb),'props':{k:str(pb[k]) for k in pb.keys() if 'component' not in k}}
    if geo and s and s.type=='MESH':
        points=[v.co for v in s.data.vertices]
        result['geometry']={'verts':[list(p) for p in points],'edges':[list(e.vertices) for e in s.data.edges],'faces':len(s.data.polygons),'bbox_min':[min(p[i] for p in points) for i in range(3)],'bbox_max':[max(p[i] for p in points) for i in range(3)]}
    return result
bpy.ops.wm.open_mainfile(filepath=str(paths[0]))
x=bpy.data.objects['CoshaRig']
limb_ik._mode_set(bpy.context,x,'POSE')
inv=limb_ik._validate_inventory(x)
report['x']={'total_bones':len(x.data.bones),'schema':inv['schema'],'master_constant':limb_ik.MASTER_NAME,'master_exists':limb_ik.MASTER_NAME in x.data.bones,'armature_location':list(x.location),'armature_scale':list(x.scale),'armature_rotation':list(x.rotation_euler),'root_bones':[bone(pb,True) for pb in x.pose.bones if pb.parent is None],'collections':[{'name':c.name,'visible':c.is_visible,'visible_effective':c.is_visible_effectively} for c in x.data.collections_all],'master_follow':[{'bone':pb.name,'constraints':cons(pb)} for pb in x.pose.bones if any('MASTER' in c.name.upper() for c in pb.constraints)],'controls':[bone(pb,True) for pb in x.pose.bones if pb.name.startswith('CTRL_') and any(s in pb.name for s in ('hand','foot_ik','elbow','knee','spine','eye'))]}
report['x']['limbs']=[{'key':key,'target':data['target'].name,'pole':data['pole'].name,'chain':data['chain'],'ik_fk':x.pose.bones[data['target'].name].get('ik_fk',1)} for key,data in inv['rigs'].items()]
bpy.ops.wm.open_mainfile(filepath=str(paths[1]))
r=bpy.data.objects['RIG-rain']
names=[pb.name for pb in r.pose.bones if pb.custom_shape and (pb.name in ('ROOT','ROOT_Child','MSTR-Pelvis','MSTR-Pelvis_Parent') or any(s in pb.name.lower() for s in ('upperarm','forearm','hand','thigh','shin','foot','knee','elbow','arm_','leg_','pole')))]
report['rain']={'total_bones':len(r.data.bones),'controls':[bone(r.pose.bones[n],True) for n in names], 'ikfk_props':{k:r.pose.bones['Properties_IKFK'][k] for k in r.pose.bones['Properties_IKFK'].keys() if isinstance(r.pose.bones['Properties_IKFK'][k],(int,float,str))}}
report['files_unchanged']={str(p):hashlib.sha256(p.read_bytes()).hexdigest()==hashes[str(p)] for p in paths}
report['saved']=False
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('ROOT_SHAPES_AUDIT',json.dumps({'x_bones':report['x']['total_bones'],'x_master_exists':report['x']['master_exists'],'x_roots':[b['name'] for b in report['x']['root_bones']],'rain_shape_controls':len(report['rain']['controls']),'unchanged':report['files_unchanged']}),flush=True)
