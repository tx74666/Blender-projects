import sys,json,hashlib
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'addons'))
from character_designer import hair_bones_topology as topology
path=Path(bpy.data.filepath); digest=hashlib.sha256(path.read_bytes()).hexdigest()
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
for name in ('Hair1','Hair2','Hair3'):
    obj=bpy.data.objects.get(name)
    for item in bpy.context.selected_objects: item.select_set(False)
    obj.hide_set(False); obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT')
    _,plans=topology.select_strands(bpy.context)
    bpy.ops.object.mode_set(mode='OBJECT')
    mods=[]
    for mod in obj.modifiers:
        item=dict(name=mod.name,type=mod.type,viewport=mod.show_viewport,render=mod.show_render)
        if mod.type=='MIRROR': item.update(axes=list(mod.use_axis),bisect=list(mod.use_bisect_axis),threshold=mod.merge_threshold,merge=mod.use_mirror_merge,vg=mod.use_mirror_vertex_groups,object=mod.mirror_object.name if mod.mirror_object else None)
        mods.append(item)
    report=dict(name=name,modifiers=mods,shape_keys=bool(obj.data.shape_keys),vertices=len(obj.data.vertices),plans=[])
    for plan in plans:
        seam=[]; span=[]
        for layer in plan['layers']:
            xs=[obj.data.vertices[i].co.x for i in layer]
            seam.append(sum(abs(x)<=.001 for x in xs)); span.append([min(xs),max(xs)])
        report['plans'].append(dict(sig=plan['signature'],counts=[len(l) for l in plan['layers']],centers=plan['centers'],seam=seam,xspan=span))
    print('MIRROR_PROBE='+json.dumps(report),flush=True)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
