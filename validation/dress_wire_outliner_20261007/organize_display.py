"""Keep live Dress dependencies intact; show helpers only under collections."""
import json
from pathlib import Path
import bpy

folder=Path(__file__).resolve().parent
artist=Path(r'D:\Blender\Projects\Character\X\X.blend')
assert Path(bpy.data.filepath).resolve()==artist.resolve()
assert bpy.context.area and bpy.context.area.type=='CONSOLE'
report_path=folder/'live_organization.json'
assert not report_path.exists()
wires=[o for o in bpy.context.scene.objects if o.name.startswith('SK_Dress_Wire_')]
assert len(wires)==11 and all(o.type=='CURVE' for o in wires)
source=wires[0].get('character_designer_skirt_source')
owner=wires[0].get('character_designer_skirt_owner')
assert source and source.name=='Dress' and owner
assert all(o.get('character_designer_skirt_source')==source and o.get('character_designer_skirt_owner')==owner for o in wires)
helpers=[c for c in bpy.data.collections if c.get('character_designer_skirt_owner')==owner
         and all(o.name in c.objects for o in wires)]
assert len(helpers)==1, 'Inspect actual collection membership before changing any links'
helper=helpers[0]
assert helper.name.startswith('Skirt Wire and Shapes | ')
outliners=[a for a in bpy.context.screen.areas if a.type=='OUTLINER']
assert outliners

def signature():
    objects={o.name:{'parent':o.parent.name if o.parent else None,'parent_type':o.parent_type,
                    'parent_bone':o.parent_bone,'world':[list(r) for r in o.matrix_world],
                    'basis':[list(r) for r in o.matrix_basis],
                    'collections':sorted(c.name for c in o.users_collection),
                    'hide_viewport':o.hide_viewport,'hide_render':o.hide_render,'hide_set':o.hide_get(),
                    'modifiers':[(m.name,m.type,getattr(getattr(m,'object',None),'name',None),getattr(m,'subtarget',None)) for m in o.modifiers]}
             for o in wires}
    parents={o.parent for o in wires if o.parent and o.parent.type=='ARMATURE'}
    curves={o.name for o in wires}
    constraints=[(rig.name,pb.name,c.name,c.type,c.target.name,c.influence,c.mute)
                 for rig in parents for pb in rig.pose.bones for c in pb.constraints
                 if getattr(c,'target',None) and c.target.name in curves]
    poses={rig.name:{p.name:[list(row) for row in p.matrix_basis] for p in rig.pose.bones} for rig in parents}
    return {'objects':objects,'constraints':constraints,'poses':poses,
            'helper_flags':{'hide_viewport':helper.hide_viewport,'hide_render':helper.hide_render}}

before=signature()
assert len(before['constraints'])>=8, 'Expected active wire references missing'
settings=[]
for area in outliners:
    space=area.spaces.active
    assert hasattr(space,'use_filter_children') and hasattr(space,'use_filter_collection')
    settings.append({'area':[area.x,area.y,area.width,area.height],
                     'children_before':space.use_filter_children,'collections_before':space.use_filter_collection})
    space.use_filter_collection=True
    space.use_filter_children=False
    area.tag_redraw()
assert signature()==before, 'Display organization changed scene dependencies'
report={'artist':str(artist),'helpers_collection':helper.name,'wire_count':len(wires),
        'wires':sorted(o.name for o in wires),'helper_members':sorted(o.name for o in helper.objects),
        'settings':settings,'scene_dependencies_unchanged':True,
        'active_wire_constraint_count':len(before['constraints']),
        'memberships_parenting_pose_modifiers_visibility_unchanged':True,'artist_saved':False}
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('DRESS_HELPERS_GROUPED_IN_OUTLINER:',helper.name,';',len(wires),'wires retained and dependencies unchanged')
