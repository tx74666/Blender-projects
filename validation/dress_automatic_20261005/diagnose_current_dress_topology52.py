"""Read-only raw Dress seams/components and one saved-pose native baseline.

No install, pose/mode switch, frame seek, simulation, weld or .blend save.
Raw disconnected panels are observations, not faults or proved Cloth tearing.
Root alone executes factory BG5.2; native renders use disposable snapshot IDs.
"""
import argparse
import ast
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import time
import traceback
from types import SimpleNamespace

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PINS={
 'compare_current_artist_fixture52.py':'b0b4730dac104dc6ad750eaba2ee7cb89acf6ed57a274d15f8c7bc57f296ec6f',
 'compare_current_artist_fixture52_v2.py':'55c0265c576473e736ec9c44e283026fc62f6503c491c34816ff5681c2d4093d',
 'verify_direct_cold_install52_v4.py':'4bb8e79fbad87950c75c1999e27d97657733ea42695df8e0f2b3a2ae4f58c536',
 'validate_real_dress.py':'613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046',
 'diagnose_skin_transfer.py':'9ad85213c41c62393b34cd5f5a45f0508bbef2ccfdf3a520f92dcf0e836f6a28',
 'verify_live_direct_cloth52_progressive_manual.py':'0c6c2747123460a31bb67ca7fb3038eed27189dfc296dd0648cfbf569ebc8bd6',
 'artist_disk_protection52.py':'11d925f0356a45d831ff84339e31bf691df21c257e195497fd36922907167b37',
 'source_compatibility52_node_ui.py':'08d36c4e561c808ed40a49e6b094085ef687a8a2e02bf5413c56ea203332507b'}
ARTIST_SHA='e0b30f73fc2f8ecc91ae418602fd3bec279b19071be3529b3d109ed55ec40dd7'
RECEIPT=HERE/'artist_disk_protection_20261007_e0b30f73fc2f.json'
RECEIPT_SHA='4d092929664f9718241afabc1ba3a3c667b600eeeb3d8a98fac0aea322ff536f'


def need(value,message):
    if not value: raise RuntimeError('DressTopology52: '+message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name):
    path=HERE/name; need(sha(path)==PINS[name],'Frozen observer differs: '+name)
    spec=importlib.util.spec_from_file_location('topology_'+path.stem,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def topology_summary(points,faces,edges):
    """Connectivity uses native indices; coincidence uses exact float tuples only."""
    need(points and faces and all(len(p)==3 and all(math.isfinite(v) for v in p) for p in points),'Missing/nonfinite geometry')
    count=len(points); incidence=defaultdict(list); by_vertex=defaultdict(list)
    need(all(len(f)>=3 and len(set(f))==len(f) and all(type(i) is int and 0<=i<count for i in f) for f in faces),'Invalid face indices')
    need(all(len(e)==2 and e[0]!=e[1] and all(type(i) is int and 0<=i<count for i in e) for e in edges),'Invalid edge indices')
    for fi,face in enumerate(faces):
        for i in face: by_vertex[i].append(fi)
        for a,b in zip(face,face[1:]+face[:1]): incidence[tuple(sorted((a,b)))].append(fi)
    native_edges={tuple(sorted(e)) for e in edges}
    need(len(native_edges)==len(edges) and set(incidence)<=native_edges,'Native edge/face connectivity disagreement')
    def components(neighbours):
        parent=list(range(len(faces)))
        def root(i):
            while i!=parent[i]: parent[i]=parent[parent[i]]; i=parent[i]
            return i
        for items in neighbours:
            for i in items[1:]: parent[root(i)]=root(items[0])
        groups=defaultdict(list)
        for i in range(len(faces)): groups[root(i)].append(i)
        ordered=sorted(groups.values(),key=lambda group:group[0]); ids={fi:ci for ci,group in enumerate(ordered) for fi in group}
        return ordered,ids
    edge_components,face_component=components(incidence.values()); vertex_components,_=components(by_vertex.values())
    boundary=sorted(edge for edge,items in incidence.items() if len(items)==1)
    graph=defaultdict(set)
    for a,b in boundary: graph[a].add(b); graph[b].add(a)
    unvisited=set(graph); paths=[]
    while unvisited:
        stack=[min(unvisited)]; nodes=set()
        while stack:
            current=stack.pop()
            if current in nodes: continue
            nodes.add(current); stack.extend(graph[current]-nodes)
        unvisited-=nodes; group_edges=[list(edge) for edge in boundary if edge[0] in nodes]
        closed=all(len(graph[i])==2 for i in nodes)
        ordered=None
        if closed:
            first=min(nodes); ordered=[first]; previous=None; current=first
            for _ in range(len(nodes)):
                candidates=graph[current]-({previous} if previous is not None else set())
                following=min(candidates); previous,current=current,following; ordered.append(current)
                if current==first: break
            need(ordered[-1]==first and len(ordered)==len(nodes)+1,'Boundary traversal unresolved')
        paths.append({'vertices':sorted(nodes),'edges':group_edges,'closed_index_cycle':closed,'ordered_cycle':ordered,
                      'branch_or_endpoint_vertices':[i for i in sorted(nodes) if len(graph[i])!=2]})
    positions=defaultdict(list)
    for index,point in enumerate(points): positions[tuple(point)].append(index)
    coincidence=[]
    for point,indices in positions.items():
        if len(indices)>1:
            coincidence.append({'position':list(point),'distinct_vertex_indices':indices,
                'incident_face_components':sorted({face_component[fi] for i in indices for fi in by_vertex.get(i,())}),
                'all_boundary_vertices':all(i in graph for i in indices)})
    return {'vertices':count,'faces':len(faces),'edges':len(edges),
        'face_components_shared_edge':edge_components,'face_components_shared_vertex':vertex_components,
        'boundary_edges':[list(edge) for edge in boundary],'boundary_components':paths,
        'closed_boundary_loop_count':sum(row['closed_index_cycle'] for row in paths),
        'nonmanifold_edges':[{'edge':list(edge),'faces':items} for edge,items in incidence.items() if len(items)>2],
        'loose_edges':[list(edge) for edge in sorted(native_edges-set(incidence))],
        'unused_face_vertices':sorted(set(range(count))-set(by_vertex)),
        'exact_coincident_different_indices':coincidence,
        'zero_length_index_edges':[list(edge) for edge in sorted(native_edges) if points[edge[0]]==points[edge[1]]],
        'coincidence_definition':'Exact native numerical coordinates; no nearest pairing, threshold, welding or topology edit',
        'panel_fault_or_Cloth_tearing_proved':False,'self_intersection_or_overlap_proved':False}


def observers(bpy,q):
    from mathutils import Matrix
    text=(HERE/'diagnose_skin_transfer.py').read_text(encoding='utf-8'); tree=ast.parse(text)
    names={'matrix','vector','mesh_snapshot','native_render'}
    scope={'bpy':bpy,'qa':q,'Matrix':Matrix,'struct':struct,'traceback':traceback,'require':need}
    # Preserve original line locations so the renderer's inspect.getsource is exact.
    selected=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(HERE/'diagnose_skin_transfer.py'),'exec'),scope)
    need(names<=scope.keys(),'Native observer ABI missing')
    progressive=load('verify_live_direct_cloth52_progressive_manual.py')
    return SimpleNamespace(**scope),progressive.two_view_renderer(SimpleNamespace(**scope))


def native_settings(bpy):
    path=Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/skirt_surface.py')
    tree=ast.parse(path.read_text(encoding='utf-8-sig')); names={'_matrix','_id','_rna'}
    selected=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    need({node.name for node in selected}==names,'Actual scalar native settings ABI missing')
    scope={'bpy':bpy,'SkirtSurfaceError':ValueError}
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(path),'exec'),scope)
    return SimpleNamespace(**scope)


def stable_receipt(bpy,p,q,cold,settings,rig,body,dress):
    owners=[rig,rig.data,body,body.data,dress,dress.data]
    if body.data.shape_keys is not None: owners.append(body.data.shape_keys)
    if dress.data.shape_keys is not None: owners.append(dress.data.shape_keys)
    context=bpy.context
    return p.primitive({'inventory':cold.inventory(bpy),'pose':q.pose_channels(rig),
        'bindings':[p.animation(owner,q) for owner in owners],
        'Body_Key_channels':None if body.data.shape_keys is None else [q.simple_rna(body.data.shape_keys),[q.simple_rna(block) for block in body.data.shape_keys.key_blocks]],
        'frame':[context.scene.frame_current,context.scene.frame_subframe],'mode':context.mode,
        'active':q.id_name(context.view_layer.objects.active),'selected':sorted(o.name for o in context.selected_objects),
        'bone_selection':cold.bone_selection(rig),'object_RNA':[settings._rna(obj) for obj in (rig,body,dress)],
        'object_custom':{obj.name:{key:q.custom_content(value) for key,value in obj.items()} for obj in (rig,body,dress)},
        'modifiers':[(obj.name,[settings._rna(m) for m in obj.modifiers]) for obj in (rig,body,dress)]})


def bounds_for_saved_dress(rig,record,graph,points):
    evaluated=rig.evaluated_get(graph); linear=evaluated.matrix_world.to_3x3()
    up=linear.col[2].normalized(); right=linear.col[0]; right=(right-up*right.dot(up)).normalized()
    waist=evaluated.matrix_world @ evaluated.pose.bones[record['controls']['waist']].head
    projected=[(point-waist).dot(up) for point in points]; low,high=min(projected),max(projected)
    need(high>low and right.length>0.,'Saved-pose geometry framing unresolved')
    pad=(high-low)*.03
    return {'waist':waist,'up':up,'right':right,'forward':up.cross(right).normalized(),
            'lower':low-pad,'upper':high+pad,'scope':'Native garment height, saved author pose; no leg input or frame change'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True); parser.add_argument('--render',action='store_true')
    parser.add_argument('--body-object',required=True); parser.add_argument('--dress-object',required=True)
    parser.add_argument('--artist-protection',type=Path,required=True); parser.add_argument('--artist-protection-sha',required=True)
    parser.add_argument('--soft-seconds',type=float,default=90.)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    need(args.output.is_absolute() and args.output.resolve().is_relative_to(HERE) and not args.output.exists(),'Fresh private output directory required')
    need(0.<args.soft_seconds<=90. and args.artist_protection.resolve()==RECEIPT.resolve() and args.artist_protection_sha==RECEIPT_SHA,'Current e0b typed protection and bounded90 required')
    import bpy
    need(bpy.app.background and bpy.app.version[:2]==(5,2) and '--factory-startup' in sys.argv and not bpy.data.filepath,'Empty factory BG5.2 only')
    p=load('compare_current_artist_fixture52.py'); locator=load('compare_current_artist_fixture52_v2.py')
    cold=load('verify_direct_cold_install52_v4.py'); disk=load('artist_disk_protection52.py'); source=load('source_compatibility52_node_ui.py')
    pins={HERE/name:value for name,value in PINS.items()}; pins.update({RECEIPT:RECEIPT_SHA,Path(__file__):sha(__file__)})
    before_source=source.current_manifest(); started=time.perf_counter(); args.output.mkdir()
    report={'collection_success':False,'accepted':False,'naturalness_accepted':False,'collision_accepted':False,
        'saved_any_blend':False,'model_modified':False,'Cloth_simulation_or_Bake_called':False,'errors':[],
        'source_before':before_source,'scope':'Raw topology and one saved author-pose prephysics baseline; not matched C30 causal comparison'}
    def write(): (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf-8')
    def budget(): need(time.perf_counter()-started<=args.soft_seconds,'Read-only topology diagnostic budget exhausted')
    protection=None; original=None; render_images=[]; render_images_removed=None
    try:
        report['artist_before']=disk.proof(args.artist_protection,args.artist_protection_sha)
        artist=Path(report['artist_before']['receipt']['artist_path']); need(sha(artist)==ARTIST_SHA,'Current protected artist differs')
        bpy.ops.wm.open_mainfile(filepath=str(artist),load_ui=False)
        selections=[]; scene,rig,body,dress,record=locator.locate_explicit(bpy,p,args.body_object,args.dress_object,selections)
        report['explicit_selection']=selections; q=p.readers(bpy); settings=native_settings(bpy)
        protection=q.Protection(); original=stable_receipt(bpy,p,q,cold,settings,rig,body,dress)
        need(body.data.shape_keys is not None and len(body.data.shape_keys.key_blocks)==12,'Current Body12 raw Key identity required')
        report['author_protection_before']=protection.summary(); report['author_saved_pose']=original['pose']
        report['saved_frame_context']={key:original[key] for key in ('frame','mode','active','selected')}
        report['saved_Dress_backend']=record.get('physics',{}).get('backend','LEGACY_CAGE')
        report['saved_Direct_state_raw']=dress.get('character_designer_dress_direct_state_v1')
        report['actual_modifier_stack']={obj.name:[settings._rna(mod) for mod in obj.modifiers] for obj in (dress,body)}
        need(all(vertex.index==i for i,vertex in enumerate(dress.data.vertices))
             and all(face.index==i for i,face in enumerate(dress.data.polygons))
             and all(edge.index==i for i,edge in enumerate(dress.data.edges)),'Raw native index sequence incomplete')
        raw_points=[list(vertex.co) for vertex in dress.data.vertices]
        raw_faces=[list(face.vertices) for face in dress.data.polygons]; raw_edges=[list(edge.vertices) for edge in dress.data.edges]
        report['raw_Dress_basis_index_topology']=topology_summary(raw_points,raw_faces,raw_edges)
        report['raw_Dress_basis_index_topology']['coordinate_scope']='Original Mesh Basis/local coordinates and original vertex/face/edge indices'
        report['raw_basis_geometry_sha256']=q.digest({'points':raw_points,'faces':raw_faces,'edges':raw_edges}); write(); budget()
        active_cloth=[{'object':obj.name,'modifier':mod.name,'viewport':mod.show_viewport,'render':mod.show_render}
            for obj in bpy.data.objects for mod in obj.modifiers if mod.type=='CLOTH' and (mod.show_viewport or mod.show_render)]
        report['active_native_Cloth']=active_cloth
        need(not active_cloth,'Active Cloth requires a separately scoped diagnostic; do not evaluate or pause it here')
        # Extend only a frozen read helper needed by the existing native renderer.
        text=p.QA.read_text(encoding='utf-8'); node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='file_state')
        values={'hashlib':hashlib,'Path':Path}; exec(compile(ast.get_source_segment(text,node),str(p.QA),'exec'),values); q.file_state=values['file_state']
        diag,render=observers(bpy,q); graph=bpy.context.evaluated_depsgraph_get()
        native=diag.mesh_snapshot(dress,graph); native_body=diag.mesh_snapshot(body,graph)
        report['saved_pose_native_evaluated_Dress']=topology_summary([list(v) for v in native['points']],
            [list(v) for v in native['faces']],[list(v) for v in native['edges']])
        report['evaluation_scope']={'frame':scene.frame_current,'subframe':scene.frame_subframe,
            'body_vertices':len(native_body['points']),'Dress_vertices':len(native['points']),'Dress_triangles':len(native['triangles']),
            'scene_scale_length_m_per_world_unit':scene.unit_settings.scale_length,
            'native_Dress_world_sha256':q.digest({'points':[list(v) for v in native['points']],'faces':native['faces']}),
            'mode':'Saved current author input; no active Cloth','neutral_Rest_pose_created':False,'private_cold_install_called':False,
            'coordinate_scope':'Same-depsgraph evaluated world coordinates and output Mesh indices',
            'raw_to_Subdiv_vertex_index_correspondence_proved':False,
            'different_time_or_C30_equivalence_claimed':False}; write(); budget()
        if args.render:
            images_before={item.as_pointer() for item in bpy.data.images}
            try:
                report['native_baseline_views']=render(SimpleNamespace(output=args.output,frame=scene.frame_current),native,native_body,
                                                      bounds_for_saved_dress(rig,record,graph,native['points']))
                report['native_baseline_views']['provenance']='Saved e0b native evaluated Dress/Body before any QA physical install or pose change'
            finally:
                render_images=[(item.name,item.as_pointer()) for item in bpy.data.images if item.as_pointer() not in images_before]
                for name,pointer in render_images:
                    item=bpy.data.images.get(name)
                    need(item is not None and item.as_pointer()==pointer and item.type=='RENDER_RESULT' and item.users==0,
                         'Unexpected new render Image ownership; no broad cleanup')
                    bpy.data.images.remove(item)
                render_images_removed=True
            write(); need(report['native_baseline_views']['success'] is True and set(report['native_baseline_views']['views'])=={'front','side'},'Two baseline views incomplete')
        report['collection_success']=True
    except Exception as error: report['errors'].append({'exception':repr(error),'traceback':traceback.format_exc()})
    finally:
        if protection is not None:
            try:
                report['author_protection_after']=q.Protection.verify(protection)
                report['author_body12_pose_bindings_context_IDs_exact']=stable_receipt(bpy,p,q,cold,settings,rig,body,dress)==original
                need(report['author_protection_after']['success'] and report['author_body12_pose_bindings_context_IDs_exact'],'Read-only author protection changed')
            except Exception as error: report['errors'].append({'author_final_guard':repr(error)})
        try: bpy.ops.wm.read_factory_settings(use_empty=True); report['private_scene_disposed']=True
        except Exception as error: report['errors'].append({'factory_disposal':repr(error)})
        try:
            report['artist_after']=disk.proof(args.artist_protection,args.artist_protection_sha); report['source_after']=source.current_manifest()
            report['source_helpers_Artist_exact']=before_source==report['source_after'] and all(sha(path)==value for path,value in pins.items())
            need(report['source_helpers_Artist_exact'],'Disk/source/observer fingerprints changed')
        except Exception as error: report['errors'].append({'disk_source_final_guard':repr(error)})
        report['collection_success']=report['collection_success'] and not report['errors'] and report.get('private_scene_disposed') is True
        report['new_render_image_receipts']=render_images; report['new_render_images_removed_exact']=render_images_removed
        report['native_total_seconds']=time.perf_counter()-started; write()
    print(json.dumps({'collection_success':report['collection_success'],'report':str(args.output/'report.json'),'errors':report['errors']}))
    return 0 if report['collection_success'] else 2


def pure_checks():
    points=[[0.,0.,0.],[1.,0.,0.],[1.,1.,0.],[0.,1.,0.],[2.,0.,0.],[2.,1.,0.]]
    faces=[[0,1,2,3],[1,4,5,2]]
    def edges_of(faces): return [list(edge) for edge in sorted({tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1])})]
    joined=topology_summary(points,faces,edges_of(faces))
    need(len(joined['face_components_shared_edge'])==1 and joined['closed_boundary_loop_count']==1,'Shared index connectivity/loop failed')
    split_points=[list(p) for p in points[:4]]+[list(p) for p in points[:4]]; split_faces=[[0,1,2,3],[4,5,6,7]]
    split=topology_summary(split_points,split_faces,edges_of(split_faces))
    need(len(split['face_components_shared_edge'])==2 and split['closed_boundary_loop_count']==2
         and len(split['exact_coincident_different_indices'])==4,'Unshared exact-coincident panels not recorded')
    split_points[4][0]+=1.e-8
    need(len(topology_summary(split_points,split_faces,edges_of(split_faces))['exact_coincident_different_indices'])==3,'Near points falsely nearest-paired')
    need(not split['panel_fault_or_Cloth_tearing_proved'],'Disconnected panel mislabeled tearing')
    loose=topology_summary([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[2.,2.,0.],[2.,2.,0.]],
                          [[0,1,2]],[[0,1],[1,2],[0,2]])
    need(loose['unused_face_vertices']==[3,4] and loose['exact_coincident_different_indices'][0]['incident_face_components']==[],
         'Coincident unused vertices incorrectly classified as face-used')
    for p,f,e in (([],[],[]),(points,[[0,1,99]],[[0,1]]),(points,faces,[])):
        try: topology_summary(p,f,e)
        except RuntimeError: pass
        else: need(False,'Missing/index/connectivity data admitted')
    need(all(sha(HERE/name)==value for name,value in PINS.items()) and sha(RECEIPT)==RECEIPT_SHA,'Frozen helpers/current protection changed')
    tree=ast.parse(Path(__file__).read_text(encoding='utf-8'))
    need(not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in
        ('frame_set','mode_set','save_as_mainfile','keyframe_insert','shape_key_add','vertices_merge') for n in ast.walk(tree)),
        'Read-only diagnostic includes scene/model mutation API')
    disk=load('artist_disk_protection52.py'); disk.proof(RECEIPT,RECEIPT_SHA)
    print(json.dumps({'source_prepared':True,'native_executed':False,'exact_index_topology_and_boundary_controls':True,
        'exact_coincident_unshared_candidates':True,'near_point_not_paired':True,'coincident_loose_vertices_remain_unused':True,
        'missing_invalid_connectivity_rejected':True,
        'read_only_API_AST_and_current_typed_Artist':True,'tearing_or_panel_fault_proved':False}))


if __name__=='__main__':
    if '--pure-checks' in sys.argv: pure_checks()
    else: raise SystemExit(main())
