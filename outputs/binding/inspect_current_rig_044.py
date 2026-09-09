import bpy, sys, json
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer
from character_designer import character_setup, skirt_rig
character_designer.register()
state=bpy.context.scene.character_designer_setup
result={'file':bpy.data.filepath, 'main_rig':state.rig.name if state.rig else None,
        'body':state.body.name if state.body else None, 'hips':character_setup.bone_mapping_status(bpy.context,'HIPS')['name'],
        'head':character_setup.bone_mapping_status(bpy.context,'HEAD')['name'], 'meshes':[], 'skirt_rigs':[]}
for obj in bpy.data.objects:
    if obj.name == 'Dress' or skirt_rig.RECORD_KEY in obj:
        result['meshes'].append({'name':obj.name,'vertices':len(obj.data.vertices) if obj.type=='MESH' else None,
            'groups':len(obj.vertex_groups),'parent':obj.parent.name if obj.parent else None,
            'modifiers':[(m.name,m.type,getattr(getattr(m,'object',None),'name',None)) for m in obj.modifiers],
            'record':skirt_rig.RECORD_KEY in obj})
    if obj.type=='ARMATURE' and obj.get(skirt_rig.OWNER_KEY):
        result['skirt_rigs'].append({'name':obj.name,'parent':obj.parent.name if obj.parent else None,'parent_bone':obj.parent_bone})
print('CURRENT_RIG_AUDIT',json.dumps(result))
