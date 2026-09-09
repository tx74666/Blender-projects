import bpy,hashlib,json,sys
from pathlib import Path
from collections import Counter,defaultdict
from mathutils import Vector
sys.path[:0]=[r'D:\MyRepository\Blender-addons-by-Randy\addons']
import character_designer
from character_designer import character_setup as setup,eye_controls,limb_ik
SOURCE=Path(r'D:\Blender\Projects\Character\X\X.blend')
OUT=Path(r'D:\Blender\Projects\Character\X\outputs\rig\audit_x_head_neck_geometry_readonly.json')
sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
character_designer.register()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
state=setup.settings(bpy.context)
rig=setup.preferred_rig(bpy.context)
head_name=setup.resolve_bone(bpy.context,'HEAD',armature=rig)
head=rig.data.bones[head_name]
neck=head.parent
body=state.body
def mat(value):return [list(row) for row in value]
def bone(value):
    return {'name':value.name,'parent':value.parent.name if value.parent else None,'head_armature':list(value.head_local),'tail_armature':list(value.tail_local),
            'length':value.length,'rest_matrix':mat(value.matrix_local),'axis_columns_armature':[list(value.matrix_local.to_3x3().col[i]) for i in range(3)],
            'pose_matrix':mat(rig.pose.bones[value.name].matrix),'custom_shape':rig.pose.bones[value.name].custom_shape.name if rig.pose.bones[value.name].custom_shape else None}
def quantile(values,q):
    values=sorted(values)
    pos=(len(values)-1)*q
    low=int(pos);high=min(low+1,len(values)-1)
    return values[low]*(1-(pos-low))+values[high]*(pos-low)
def bounds(points):
    if not points:return None
    return {'count':len(points),'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)],
            'quantiles':{str(q):[quantile([p[i] for p in points],q) for i in range(3)] for q in (.01,.02,.05,.1,.25,.5,.75,.9,.95,.98,.99)}}
def report_mesh(obj):
    transform=head.matrix_local.inverted()@rig.matrix_world.inverted()@obj.matrix_world
    headgroup=obj.vertex_groups.get(head_name)
    if not headgroup:return {'name':obj.name,'head_weight_group':False}
    weighted={v.index:next((g.weight for g in v.groups if g.group==headgroup.index),0.0) for v in obj.data.vertices}
    selected={idx:transform@obj.data.vertices[idx].co for idx,w in weighted.items() if w>.05}
    material_points=defaultdict(dict)
    for polygon in obj.data.polygons:
        material=obj.material_slots[polygon.material_index].name if polygon.material_index<len(obj.material_slots) else '<none>'
        for idx in polygon.vertices:
            if idx in selected:material_points[material][idx]=selected[idx]
    parent=list(range(len(obj.data.vertices)))
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    for edge in obj.data.edges:
        a,b=(find(i) for i in edge.vertices)
        if a!=b:parent[b]=a
    components=defaultdict(list)
    for idx in selected:components[find(idx)].append(idx)
    totals=Counter(find(idx) for idx in range(len(parent)))
    component_reports=[]
    for root,indices in sorted(components.items(),key=lambda item:len(item[1]),reverse=True):
        materials={material:len(set(indices)&set(points)) for material,points in material_points.items() if set(indices)&set(points)}
        component_reports.append({'mesh_component_vertex_count':totals[root],'head_weighted':bounds([selected[idx] for idx in indices]),'material_vertex_counts':materials})
    largest=max(components.values(),key=len) if components else []
    main_points=[selected[idx] for idx in largest]
    return {'name':obj.name,'vertex_count':len(obj.data.vertices),'matrix_world':mat(obj.matrix_world),'mesh_to_head_rest':mat(transform),
            'materials':[slot.name for slot in obj.material_slots],
            'head_weight_bounds':{str(threshold):bounds([transform@obj.data.vertices[idx].co for idx,w in weighted.items() if w>threshold]) for threshold in (.01,.05,.5,.9)},
            'materials_head_weight_gt_005':{name:bounds(list(points.values())) for name,points in material_points.items()},
            'components_head_weight_gt_005':component_reports[:20],
            'largest_component_height_profiles_head_local':[{'y_range':[low,high],'bounds':bounds([p for p in main_points if low<=p.y<high])}
                for low,high in ((-.03,0),(0,.03),(.03,.06),(.06,.1),(.1,.15),(.15,.2),(.2,.24))]}

eye_sources=eye_controls.resolve_eyes(bpy.context,rig)
eye_forward=sum(((rig.data.bones[name].tail_local-rig.data.bones[name].head_local).normalized() for name in eye_sources[1:]),Vector()).normalized()
report={'source':str(SOURCE),'size':SOURCE.stat().st_size,'sha256_before':sha,'rig':rig.name,'bone_count':len(rig.data.bones),
        'character_setup':{'body':body.name if body else None,'head_mapping':setup.bone_mapping_status(bpy.context,'HEAD',armature=rig)['status'],
                           'assets':[{'name':item.object.name if item.object else None,'role':item.role} for item in state.assets]},
        'rig_matrix_world':mat(rig.matrix_world),'head':bone(head),'neck':bone(neck),
        'eye_forward_armature':list(eye_forward),'eye_forward_head_local':list(head.matrix_local.inverted().to_3x3()@eye_forward),
        'meshes':[report_mesh(obj) for obj in bpy.data.objects if obj.type=='MESH' and (obj==body or any(m.type=='ARMATURE' and m.object==rig for m in obj.modifiers))]}
neck_transform=neck.matrix_local.inverted()@rig.matrix_world.inverted()@body.matrix_world
neck_group=body.vertex_groups.get(neck.name)
neck_points=[neck_transform@v.co for v in body.data.vertices if neck_group and any(g.group==neck_group.index and g.weight>.05 for g in v.groups)]
body_neck_points=[neck_transform@v.co for v in body.data.vertices]
report['neck_weight_gt_005_bounds_neck_local']=bounds(neck_points)
report['neck_height_profiles_neck_local']=[{'y_range':[low,high],'bounds':bounds([p for p in body_neck_points if low<=p.y<high and abs(p.x)<.15 and abs(p.z)<.15])}
    for low,high in ((0,.012),(.012,.03),(.03,.05),(.05,.065))]
report['hair_assets']=[{'name':item.object.name,'parent':item.object.parent.name if item.object.parent else None,
    'armature_modifiers':[m.object.name if m.object else None for m in item.object.modifiers if m.type=='ARMATURE'],
    'materials':[slot.name for slot in item.object.material_slots]}
    for item in state.assets if item.role=='HAIR' and item.object]
report['sha256_after']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
report['source_unchanged']=report['sha256_after']==sha
OUT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HEAD_NECK_GEOMETRY_SUMMARY',json.dumps({'rig':rig.name,'bone_count':len(rig.data.bones),'body':body.name if body else None,'head':report['head'],'neck':report['neck'],
      'eye_forward_armature':list(eye_forward),'eye_forward_head_local':report['eye_forward_head_local'],
      'mesh_summaries':[{'name':item['name'],'head_weight_bounds':item.get('head_weight_bounds'),'materials':item.get('materials'),'components':[(entry['head_weighted']['count'],entry['material_vertex_counts']) for entry in item.get('components_head_weight_gt_005',[])]} for item in report['meshes']],
      'source_unchanged':report['source_unchanged'],'report':str(OUT)}),flush=True)
