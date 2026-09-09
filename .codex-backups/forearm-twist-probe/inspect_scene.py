"""Read-only saved-scene compatibility probe; never saves blend data."""
import bpy
import bmesh
import json
from collections import Counter
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parent

def plain(value):
    try:
        return value.to_dict()
    except AttributeError:
        try:
            return list(value)
        except TypeError:
            return value

def ids(obj):
    return {k: plain(obj[k]) for k in obj.keys() if k != '_RNA_UI'}

report = {'blender_version': bpy.app.version_string, 'filepath': bpy.data.filepath, 'objects': [], 'armatures': [], 'forearms': []}
for ob in bpy.data.objects:
    if ob.type not in {'MESH', 'ARMATURE'}:
        continue
    base = {'name': ob.name, 'type': ob.type, 'hide_viewport': ob.hide_viewport, 'visible': ob.visible_get(), 'scale': list(ob.scale), 'data_users': ob.data.users, 'id_properties': ids(ob)}
    if ob.type == 'MESH':
        base.update(vertices=len(ob.data.vertices), polygons=len(ob.data.polygons), groups=[g.name for g in ob.vertex_groups], shape_keys=[] if ob.data.shape_keys is None else [{'name': k.name, 'value': k.value, 'mute': k.mute, 'relative': k.relative_key.name, 'vertex_group': k.vertex_group} for k in ob.data.shape_keys.key_blocks], modifiers=[])
        for mod in ob.modifiers:
            props = {'name': mod.name, 'type': mod.type, 'show_viewport': mod.show_viewport, 'show_render': mod.show_render}
            for key in ('use_deform_preserve_volume', 'use_vertex_groups', 'use_bone_envelopes', 'use_multi_modifier', 'vertex_group', 'invert_vertex_group', 'levels', 'render_levels', 'use_clip', 'use_mirror_vertex_groups', 'use_axis'):
                if hasattr(mod, key):
                    props[key] = plain(getattr(mod, key))
            if hasattr(mod, 'object'):
                props['object'] = getattr(mod, 'object').name if getattr(mod, 'object') else None
            base['modifiers'].append(props)
    else:
        base.update(data_id_properties=ids(ob.data), bones=[])
        for pb in ob.pose.bones:
            if not any(word in pb.name.lower() for word in ('forearm', 'hand', 'upper_arm')):
                continue
            bd = {'name': pb.name, 'deform': pb.bone.use_deform, 'parent': pb.parent.name if pb.parent else None, 'rest_head': list(pb.bone.head_local), 'rest_tail': list(pb.bone.tail_local), 'head': list(pb.head), 'tail': list(pb.tail), 'rotation_mode': pb.rotation_mode, 'rotation_euler': list(pb.rotation_euler), 'bone_id_properties': ids(pb.bone), 'id_properties': ids(pb), 'constraints': []}
            for c in pb.constraints:
                cd = {'name': c.name, 'type': c.type, 'influence': c.influence, 'mute': c.mute}
                for key in ('subtarget', 'pole_subtarget', 'chain_count', 'use_rotation', 'owner_space', 'target_space'):
                    if hasattr(c, key): cd[key] = getattr(c, key)
                bd['constraints'].append(cd)
            base['bones'].append(bd)
        report['armatures'].append(base)
    report['objects'].append(base)

for ob in bpy.data.objects:
    if ob.type != 'MESH': continue
    arm_mods = [m for m in ob.modifiers if m.type == 'ARMATURE' and m.object]
    for mod in arm_mods:
        arm = mod.object
        for side in ('L', 'R'):
            bone = arm.data.bones.get('forearm.' + side)
            if bone is None: continue
            groups = {g.index: g.name for g in ob.vertex_groups}
            arm_names = {'upper_arm.'+side, 'forearm.'+side, 'hand.'+side}
            matrix = arm.matrix_world.inverted() @ ob.matrix_world
            axis = bone.tail_local - bone.head_local
            length = axis.length
            axis.normalize()
            vertices = []
            bins = {}
            weighted = Counter()
            for v in ob.data.vertices:
                weights = {groups[g.group]: g.weight for g in v.groups if g.group in groups and g.weight > 1e-7}
                related = sum(weights.get(n, 0) for n in arm_names)
                if related <= 0.01: continue
                co = matrix @ v.co
                t = (co-bone.head_local).dot(axis)/length
                radial = ((co-bone.head_local) - axis*((co-bone.head_local).dot(axis))).length
                vertices.append({'i':v.index, 't':t, 'radial':radial, 'co':list(v.co), 'weights':weights})
                weighted.update(weights.keys())
                if 0 <= t <= 1:
                    bins.setdefault(min(9,int(t*10)), []).append(vertices[-1])
            if not vertices: continue
            summary = {'object': ob.name, 'armature': arm.name, 'side': side, 'bone_length':length, 'related_vertices':len(vertices), 'forearm_range_vertices':sum(len(v) for v in bins.values()), 'influences':dict(weighted), 'bins':{}, 'candidate_loops':[]}
            for b, verts in sorted(bins.items()):
                summary['bins'][str(b)] = {'n': len(verts), 'radial_min':min(v['radial'] for v in verts),'radial_max':max(v['radial'] for v in verts),'weights':{n:[min(v['weights'].get(n,0) for v in verts), max(v['weights'].get(n,0) for v in verts)] for n in arm_names},'other_influences':list({n for v in verts for n in v['weights'] if n not in arm_names})}
            # Partition candidate circumferential edges (axial excursion much smaller than radial motion).
            bm=bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
            vdict={v['i']:v for v in vertices if -0.05 <= v['t'] <= 1.05}
            selected=set()
            for e in bm.edges:
                if all(v.index in vdict for v in e.verts):
                    v1,v2=e.verts; delta=matrix.to_3x3()@(v2.co-v1.co)
                    if abs(delta.dot(axis)) < delta.length*0.45: selected.add(e.index)
            seen=set()
            for ei in sorted(selected):
                if ei in seen: continue
                pending=[ei]; component_edges=set(); component_verts=set()
                while pending:
                    eidx=pending.pop()
                    if eidx in seen: continue
                    seen.add(eidx); component_edges.add(eidx)
                    for v in bm.edges[eidx].verts:
                        component_verts.add(v.index)
                        pending.extend(e.index for e in v.link_edges if e.index in selected and e.index not in seen)
                degree=Counter(vi for eidx in component_edges for vi in [v.index for v in bm.edges[eidx].verts])
                closed=bool(degree) and all(v==2 for v in degree.values())
                ts=[vdict[i]['t'] for i in component_verts]
                if len(component_verts)>=6:
                    summary['candidate_loops'].append({'closed':closed,'vertices':sorted(component_verts),'n':len(component_verts),'t_mean':sum(ts)/len(ts),'t_range':[min(ts),max(ts)]})
            bm.free()
            report['forearms'].append(summary)
            (OUT / f'vertices-{ob.name}-{side}.json').write_text(json.dumps(vertices,indent=2),encoding='utf8')

(OUT / 'scene-report.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf8')
print('FOREARM_PROBE_REPORT=' + str(OUT / 'scene-report.json'))
for ob in report['objects']:
    if ob['type']=='MESH' and ob['vertices']>100:
        print('MESH',ob['name'],ob['vertices'],ob['modifiers'],'shape_keys',len(ob['shape_keys']))
for r in report['forearms']:
    print('FOREARM',r['object'],r['side'],'weighted',r['related_vertices'],'in range',r['forearm_range_vertices'],'loops',[(a['n'],round(a['t_mean'],3),a['closed']) for a in r['candidate_loops']])
