"""Read-only Blender snapshot for an independent before/after scene integrity audit.
Run --factory-startup -b FILE --python this.py -- --output snapshot.json.
No add-on is registered; no source file is saved or changed.
"""
import argparse, hashlib, json, sys
from array import array
from pathlib import Path
import bpy

RECORD_KEY='character_designer_forearm_twist_v1'

def matrix(m):return [list(row) for row in m]
def ref(value):return getattr(value,'name_full',getattr(value,'name',None)) if value else None

def scalar_props(value):
    result={}
    for prop in value.bl_rna.properties:
        name=prop.identifier
        if name in {'rna_type','name'} or prop.is_readonly:continue
        try:
            item=getattr(value,name)
            if prop.type in {'STRING','BOOLEAN','INT','FLOAT','ENUM'}:
                if prop.is_array:item=list(item)
                elif isinstance(item,set):item=sorted(item)
                result[name]=item
            elif prop.type=='POINTER':result[name]=ref(item) if hasattr(item,'name_full') else getattr(item,'name',None)
        except (AttributeError,TypeError,ValueError):pass
    return result

def hash_json(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def coords(data):
    values=array('f',[0.0])*(3*len(data)); data.foreach_get('co',values)
    return values

def curves(action):
    if hasattr(action,'fcurves'):return list(action.fcurves)
    return [fc for layer in getattr(action,'layers',()) for strip in layer.strips for bag in getattr(strip,'channelbags',()) for fc in bag.fcurves]

def curve_snapshot(fc):
    result=dict(path=fc.data_path,index=fc.array_index,extrapolation=fc.extrapolation,
        mute=fc.mute,keys=[dict(co=list(k.co),left=list(k.handle_left),right=list(k.handle_right),
         interpolation=k.interpolation,left_type=k.handle_left_type,right_type=k.handle_right_type,
         easing=k.easing,type=k.type) for k in fc.keyframe_points],
        samples=[list(p.co) for p in fc.sampled_points],
        modifiers=[dict(type=m.type,props=scalar_props(m)) for m in fc.modifiers])
    if fc.driver:
        result['driver']=dict(type=fc.driver.type,expression=fc.driver.expression,use_self=fc.driver.use_self,
            variables=[dict(name=v.name,type=v.type,targets=[scalar_props(t) for t in v.targets]) for v in fc.driver.variables])
    return result

def animation(data):
    ad=data.animation_data
    if not ad:return None
    return dict(action=ref(ad.action),slot=getattr(ad.action_slot,'identifier',None),
        action_blend_type=ad.action_blend_type,action_influence=ad.action_influence,
        drivers=[curve_snapshot(c) for c in ad.drivers],
        nla=[dict(name=t.name,mute=t.mute,is_solo=t.is_solo,
             strips=[dict(name=s.name,props=scalar_props(s),curves=[curve_snapshot(c) for c in s.fcurves]) for s in t.strips]) for t in ad.nla_tracks])

def snapshot():
    source=Path(bpy.data.filepath)
    before_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.context.view_layer.update()
    result=dict(source=str(source),source_sha256=before_hash,blender_version=list(bpy.app.version),
        frames={s.name:dict(frame=s.frame_current,subframe=s.frame_subframe) for s in bpy.data.scenes},
        armatures={},meshes={},objects={},actions={},calibrations={})
    owned={}
    for obj in bpy.data.objects:
        if RECORD_KEY not in obj:continue
        record=json.loads(obj[RECORD_KEY])
        effective={}
        for side,item in record.items():
            owned.setdefault(ref(obj.data),set()).add(item['key'])
            effective[side]=dict(armature=item['armature'],chain=item['chain'],target=item['target'],
                enabled=item.get('enabled',True),paired=item.get('paired',False),
                vertices=item['vertices'],positions=item['positions'],rings=item['rings'],
                range_start=item.get('range_start',0),range_end=item.get('range_end',len(item['rings'])-1),
                transition=item.get('range_transition',None))
        result['calibrations'][obj.name]=dict(raw=record,effective=effective)
    for arm in bpy.data.armatures:
        result['armatures'][arm.name]=dict(bones={b.name:dict(parent=ref(b.parent),connect=b.use_connect,
            deform=b.use_deform,segments=b.bbone_segments,rest=matrix(b.matrix_local),
            inherit_scale=b.inherit_scale,use_inherit_rotation=b.use_inherit_rotation,
            use_local_location=b.use_local_location) for b in arm.bones},animation=animation(arm))
    for obj in bpy.data.objects:
        data=dict(type=obj.type,data=ref(obj.data),parent=ref(obj.parent),parent_type=obj.parent_type,parent_bone=obj.parent_bone,
                  matrix_basis=matrix(obj.matrix_basis),matrix_world=matrix(obj.matrix_world),
                  parent_inverse=matrix(obj.matrix_parent_inverse),animation=animation(obj),
                  modifiers=[dict(name=m.name,type=m.type,props=scalar_props(m)) for m in obj.modifiers],
                  vertex_groups=[(g.index,g.name,g.lock_weight) for g in obj.vertex_groups])
        if obj.type=='ARMATURE':
            data['pose']={p.name:dict(matrix=matrix(p.matrix),basis=matrix(p.matrix_basis),
                shape=ref(p.custom_shape),shape_transform=ref(p.custom_shape_transform),
                at_shape=p.use_transform_at_custom_shape,around_shape=p.use_transform_around_custom_shape,
                constraints=[dict(name=c.name,type=c.type,props=scalar_props(c)) for c in p.constraints]) for p in obj.pose.bones}
        result['objects'][obj.name]=data
    for mesh in bpy.data.meshes:
        basis=coords(mesh.vertices)
        record=dict(counts=(len(mesh.vertices),len(mesh.edges),len(mesh.polygons)),
           basis_hash=hashlib.sha256(basis.tobytes()).hexdigest(),
           topology_hash=hash_json(([list(e.vertices) for e in mesh.edges],[list(p.vertices) for p in mesh.polygons])),
           weights_hash=hash_json([[(g.group,g.weight) for g in v.groups] for v in mesh.vertices]),keys={})
        if mesh.shape_keys:
            record['key_animation']=animation(mesh.shape_keys)
            for key in mesh.shape_keys.key_blocks:
                values=coords(key.data)
                entry=dict(relative=key.relative_key.name,value=key.value,mute=key.mute,vertex_group=key.vertex_group,
                           slider_min=key.slider_min,slider_max=key.slider_max,
                           hash=hashlib.sha256(values.tobytes()).hexdigest(),owned=key.name in owned.get(mesh.name,set()))
                if entry['owned']:entry['coords']=list(values)
                record['keys'][key.name]=entry
        result['meshes'][mesh.name]=record
    for action in bpy.data.actions:
        result['actions'][action.name]=dict(slots=[(s.identifier,s.target_id_type) for s in getattr(action,'slots',())],
            curves=[curve_snapshot(c) for c in curves(action)])
    result['source_unchanged']=before_hash==hashlib.sha256(source.read_bytes()).hexdigest()
    assert result['source_unchanged']
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    data=snapshot();args.output.write_text(json.dumps(data,indent=2,default=lambda value:list(value)),encoding='utf8')
    print('INTEGRITY_SNAPSHOT',str(args.output),'source_unchanged',data['source_unchanged'],flush=True)


