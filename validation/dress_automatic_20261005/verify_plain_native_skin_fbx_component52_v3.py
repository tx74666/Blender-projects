"""SOURCE PREPARED: private model FBX component; no public admission or Unity proof."""
import ast, copy, hashlib, importlib, importlib.util, json, sys, time, math
from array import array
from pathlib import Path
from types import SimpleNamespace
HERE = Path(__file__).resolve().parent
V4_FILE = HERE/'verify_plain_native_skin_model52_v4.py'
V4_SHA = 'c3f59ff67196cd4cf205a2d6e0a2868df39ab7b35f99bf667c41c8f4a27d4d85'
RUN = HERE/'actual_plain_native_skin_model_v4_e0b_52_20261007_123727_962_feab010a295d467eae8019cccff98ca8/result'
PROOF, SNAPSHOT = RUN/'report.json', RUN/'cdesigner-unity-pns-qa/character.blend'
PROOF_SHA, SNAPSHOT_SHA = '803b8ec6297eb51f23e4a664e76e21ff354d3d1a97748a826ec41da3bfd67aa9', 'ab48a806f8e228f3c878da65bab59fe9cdaff2bcbca037f258cf74cacd88dc71'
WORKER = Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/unity_export_worker.py')
FBX = Path('D:/Blender5.2/5.2/scripts/addons_core/io_scene_fbx')
FBX_PINS = {WORKER:'1716ff49a231cee8c0663fd17949583eabbfb7ce79791a459682930f40744dcb', FBX/'__init__.py':'b7a2c06c11267ff9baaeb30ebc6add17b044d27f754340f17345dc78d74db336', FBX/'export_fbx_bin.py':'8fd324e4ee0d25cc89cd53507b0f93c057b17b699601ac90f81085d5be09e44a', FBX/'fbx_utils.py':'66a15d79d5eaf490176b439f22fb01963efcd46e06702eff224a84135e636fb3', FBX/'import_fbx.py':'e4e55c2e344959b75d840e20c4d45d079ec8fd4f4bc375491cea76e55cce8013'}
def load_v4():
    assert hashlib.sha256(V4_FILE.read_bytes()).hexdigest() == V4_SHA
    spec=importlib.util.spec_from_file_location('pns_fbx_frozen_v4',V4_FILE); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
V4=load_v4()
ORIGINAL = HERE/'verify_plain_native_skin_fbx_component52.py'
ORIGINAL_SHA = '55a2833db4e4fc69ec6b5167267559832c898c867d841d7ca8d1a457116c1cfd'
FAILED = HERE/'actual_plain_native_skin_fbx_component_e0b_52_20261007_143947_577_bdb155baac8d4f5b813422e001e06d61/result/report.json'
FAILED_SHA = '27584f5327eb8ef6576ed75a31b5720b21e0951f322f31334f0bab2f451551cd'
PREVIOUS = HERE/'verify_plain_native_skin_fbx_component52_v2.py'
PREVIOUS_SHA = 'f277b0a3ec00a8318ac638f8da82de2c6e7426b12a73a0e7576b8cc82b79c1b5'
TIMED_OUT_REPORT = HERE/'actual_plain_native_skin_fbx_component_v2_e0b_52_20261007_151611_882_c3e632a19b434c3ca1940f416c838cd3/result/report.json'
TIMED_OUT_REPORT_SHA = '085c1d72829fbf521e77f4e8fe5bc29367b9e501d9d4227f91afd965b3f53299'
TIMED_OUT_PROCESS = TIMED_OUT_REPORT.parent.parent/'process.json'
TIMED_OUT_PROCESS_SHA = '93ed2ff85714bd160f86b9e49486577321ba4ae9b9e5fb3eb9269ce9a9ca25d8'
class ImageRNAWithoutPixels:
    def __init__(self,image):
        self.image=image
        self.bl_rna=SimpleNamespace(properties=tuple(prop for prop in image.bl_rna.properties if prop.identifier!='pixels'))
    def __getattr__(self,name): return getattr(self.image,name)

def content_assets(bpy,q,report,write,phase):
    result={}
    for tree in list(bpy.data.node_groups)+[m.node_tree for m in bpy.data.materials if m.node_tree]:
        result['tree:'+tree.name]=q.digest([q.simple_rna(tree), [[q.simple_rna(n),[q.simple_rna(s) for s in n.inputs],[q.simple_rna(s) for s in n.outputs],{k:q.custom_content(v) for k,v in n.items()}] for n in tree.nodes], [q.simple_rna(l) for l in tree.links]])
    for material in bpy.data.materials: result['material:'+material.name]=q.digest([q.simple_rna(material),{k:q.custom_content(v) for k,v in material.items()}])
    for image in bpy.data.images:
        label=phase+':image:'+image.name; progress(report,write,label,'start')
        prop=next((prop for prop in image.bl_rna.properties if prop.identifier=='pixels'),None)
        started=time.perf_counter(); values=array('f',[0.])*len(image.pixels); image.pixels.foreach_get(values)
        V4.need(all(math.isfinite(value) for value in values),'Original Image pixels nonfinite')
        pixels_sha=hashlib.sha256(values).hexdigest(); bulk_seconds=time.perf_counter()-started
        started=time.perf_counter(); rna=q.simple_rna(ImageRNAWithoutPixels(image)); rna_seconds=time.perf_counter()-started
        started=time.perf_counter(); packed=[hashlib.sha256(item.packed_file.data).hexdigest() for item in image.packed_files]; packed_seconds=time.perf_counter()-started
        result['image:'+image.name]=q.digest([rna,pixels_sha,packed])
        report.setdefault('image_asset_phases',[]).append({'phase':phase,'image':image.name,'pixel_float32_count':len(values),'pixel_SHA':pixels_sha,'bulk_pixel_seconds':bulk_seconds,'RNA_except_pixels_seconds':rna_seconds,'packed_bytes_seconds':packed_seconds,'pixels_RNA_present':prop is not None,'pixels_RNA_type':getattr(prop,'type',None),'pixels_RNA_is_array':getattr(prop,'is_array',None),'pixel_reads_bulk_only':True,'cause_confirmed':False})
        progress(report,write,label,'complete')
    return result

def native_skin(obj,graph):
    evaluated=obj.evaluated_get(graph); mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=graph)
    try: return {'groups':[g.name for g in obj.vertex_groups], 'weights':[{obj.vertex_groups[g.group].name:g.weight for g in v.groups} for v in mesh.vertices], 'UV':[(u.name,[(list(x.uv)) for x in u.data]) for u in mesh.uv_layers], 'materials':[m.name if m else None for m in mesh.materials], 'material_indices':[face.material_index for face in mesh.polygons]}
    finally: evaluated.to_mesh_clear()

def source_snapshot_guard(reference,report,write):
    # Compare the actual native file identity; Windows pathname case is not content.
    snapshot=reference.get('library_snapshot',{}); snapshot=snapshot if type(snapshot) is dict else {}
    reported_path=snapshot.get('path'); reported_sha=snapshot.get('sha256')
    sources=(reference.get('source_before'),reference.get('source_after'),report.get('source_before'))
    row={'recorded_path':reported_path if type(reported_path) is str else None,
         'recorded_path_repr':repr(reported_path),'recorded_path_type':type(reported_path).__name__,
         'expected_path':str(SNAPSHOT),'expected_path_repr':repr(str(SNAPSHOT)),
         'expected_path_type':type(SNAPSHOT).__name__,'exact_path_string':reported_path==str(SNAPSHOT),
         'recorded_sha256':reported_sha,'recorded_sha256_type':type(reported_sha).__name__,
         'expected_sha256':SNAPSHOT_SHA,'source_types':[type(v).__name__ for v in sources],
         'source_counts':[len(v) if type(v) is dict else None for v in sources],
         'same_native_file':None,'actual_recorded_sha256':None,'actual_expected_sha256':None,
         'errors':[],'accepted':False,'prior_failure':{'path':str(FAILED),'sha256':FAILED_SHA,'preserved':True}}
    predicates={'all_source_manifests_present':all(type(v) is dict and bool(v) for v in sources),
                'source_before_after_current_exact':sources[0]==sources[1]==sources[2],
                'recorded_full_SHA_exact':type(reported_sha) is str and reported_sha==SNAPSHOT_SHA,
                'native_snapshot_file_identity_exact':False,'actual_snapshot_SHA_exact':False}
    try:
        V4.need(type(reported_path) is str and Path(reported_path).is_absolute(),'Saved snapshot path identity Unknown')
        reported=Path(reported_path); row['same_native_file']=reported.samefile(SNAPSHOT)
        row['actual_recorded_sha256']=V4.sha(reported); row['actual_expected_sha256']=V4.sha(SNAPSHOT)
        predicates['native_snapshot_file_identity_exact']=row['same_native_file'] is True
        predicates['actual_snapshot_SHA_exact']=row['actual_recorded_sha256']==row['actual_expected_sha256']==SNAPSHOT_SHA
    except Exception as exc: row['errors'].append(repr(exc))
    row['predicates']=predicates; row['passed']=not row['errors'] and all(value is True for value in predicates.values())
    report['source_snapshot_guard']=row; write()
    V4.need(row['passed'],'Current source or exact saved snapshot differs')

def progress(report,write,label,event):
    now=time.perf_counter(); origin=report.setdefault('phase_origin',now)
    row={'phase':label,'event':event,'elapsed_seconds':now-origin}
    report.setdefault('phase_progress',[]).append(row); report['active_phase']=row
    # Progress I/O must not prevent native cleanup; any failure poisons completion.
    try: write()
    except Exception as exc: report.setdefault('errors',[]).append({'progress_write':label,'exception':repr(exc)})
    try: print(json.dumps({'FBX_phase':row},ensure_ascii=False,allow_nan=False),flush=True)
    except Exception as exc: report.setdefault('errors',[]).append({'progress_stdout':label,'exception':repr(exc)})

def restore_saved_flags(bpy,q,report,write):
    original=V4.action_inventory; calls=[]
    def observed(*args):
        label='complete_Action_inventory_'+str(len(calls)+1); calls.append(label)
        progress(report,write,label,'start'); result=original(*args)
        report.setdefault('Action_scan_receipts',[]).append({'phase':label,'actual_action_count':len(result),'complete_content_read':True})
        progress(report,write,label,'complete'); return result
    V4.action_inventory=observed
    try: V4.restore_reopened_action_flags(bpy,q,SNAPSHOT,report,write)
    finally:
        V4.action_inventory=original
        V4.need(V4.action_inventory is original,'Original Action reader restoration failed')

def exercise(bpy,args,base,cold,p,q,direct,plain,_source,_rig,_body,report,write,budget):
    from character_designer import forearm_twist
    progress(report,write,'completed_PNS_report_read','start'); reference=json.loads(PROOF.read_text(encoding='utf-8')); progress(report,write,'completed_PNS_report_read','complete'); V4.need(all(reference.get(k) is True for k in ('native_component_verified','native_stages_completed','source_files_Artist_exact','private_scene_disposed','reopen_contract_exact','stripped_author_contract_exact')) and not reference['errors'], 'Completed PNS proof missing')
    progress(report,write,'completed_snapshot_proof','start'); source_snapshot_guard(reference,report,write)
    V4.need(reference['identity']['body']==args.body_object and reference['identity']['source']==args.dress_object,'Explicit saved snapshot selection differs')
    progress(report,write,'completed_snapshot_proof','complete')
    report.update(stage='PRIVATE_PNS_MODEL_FBX_COMPONENT52', FBX_component_written=False, FBX_reimport_verified=False, physics_omitted=True,body_attachment_omitted=True,simulation_baked=False,final_surface_equivalent=False,animation_verified=False)
    report['snapshot_transport']={k:copy.deepcopy(reference['snapshot_transport'][k]) for k in ('Action_content_before','keepalive_names','scene_custom_before')}
    report['component_input_scope']={'fixed_completed_PNS_snapshot':True,'artist_scene_loaded':False,'fresh_install_or_Original_replayed':False,'current_artist_memory_registration_verified':False,'Action_scans_before_export_expected':6,'Action_scans_finally_expected':2,'scan_counts_are_source_plan_not_timing_proof':True,'prior_timeout_preserved':{'report':str(TIMED_OUT_REPORT),'sha256':TIMED_OUT_REPORT_SHA,'process':str(TIMED_OUT_PROCESS),'process_sha256':TIMED_OUT_PROCESS_SHA,'upgraded_to_success':False}}
    progress(report,write,'load_saved_PNS','start'); bpy.ops.wm.open_mainfile(filepath=str(SNAPSHOT),load_ui=False); progress(report,write,'load_saved_PNS','complete')
    progress(report,write,'restore_saved_Action_flags','start'); V4.clear_reopened_keepalive(bpy,report); restore_saved_flags(bpy,q,report,write); progress(report,write,'restore_saved_Action_flags','complete'); budget()
    V4.need({k:q.custom_content(v) for k,v in bpy.context.scene.items()}==report['snapshot_transport']['scene_custom_before'], 'Original Scene properties changed')
    progress(report,write,'installed_graph_validation','start'); source,rig,body,record=base.installed_objects(bpy,direct,reference['identity']); expected=reference['authored_contract_before_snapshot']; progress(report,write,'installed_graph_validation','complete')
    progress(report,write,'complete_reopened_author_mode_cache','start')
    V4.need(base.authored_contract(bpy,p,q,direct,source,rig,body)==expected and base.mode_contract(q,direct,source,record)==reference['born_mode'] and base.private_cache_scope(direct,source,record)==reference['cache_scope_before'], 'Reopened author/mode/cache hard guard differs')
    progress(report,write,'complete_reopened_author_mode_cache','complete'); budget()
    progress(report,write,'validate_prepare_strip','start'); receipt=reference['captured_model_receipt']; plain.validate(source,receipt); prepared=plain.prepare(source,receipt); V4.need(V4.digest(prepared)==V4.digest(receipt), 'PNS receipt differs'); report['strip']=plain.strip(source,prepared); progress(report,write,'validate_prepare_strip','complete')
    progress(report,write,'complete_preFBX_author_material_image','start')
    progress(report,write,'complete_preFBX_Protection_capture','start'); protected=q.Protection(); progress(report,write,'complete_preFBX_Protection_capture','complete')
    progress(report,write,'complete_preFBX_authored_contract','start'); before=base.authored_contract(bpy,p,q,direct,source,rig,body); progress(report,write,'complete_preFBX_authored_contract','complete')
    assets=content_assets(bpy,q,report,write,'before_FBX'); context=bpy.context; home=context.scene
    progress(report,write,'complete_preFBX_author_material_image','complete'); budget()
    progress(report,write,'current_plain_skin_native3040','start'); graph=context.evaluated_depsgraph_get(); target=base.native_mesh(source,graph); skin=native_skin(source,graph); V4.need(len(target['points'])==3040 and source.data.shape_keys is None,'Native no-Key 3040 scope differs'); progress(report,write,'current_plain_skin_native3040','complete')
    clone=None; data=None; imported_scene=None
    with forearm_twist.defer_runtime(context,flush_on_exit=False):
        try:
            progress(report,write,'clone_native_bake_and_protection','start'); clone=source.copy(); data=source.data.copy(); clone.data=data; context.scene.collection.objects.link(clone); clone.name='.PNS Private FBX Dress'
            for name in tuple(clone.keys()):
                if name.startswith('character_designer_'): del clone[name]
            worker=importlib.import_module('character_designer.unity_export_worker'); V4.need(Path(worker.__file__).resolve()==WORKER.resolve(),'Wrong native worker module')
            warnings=[]; report['clone_baker']=worker._bake_mesh(context,clone,set(),warnings); graph=context.evaluated_depsgraph_get()
            report['clone_current_input_error']=base.geometry_pair(cold,target,base.native_mesh(clone,graph),home.unit_settings.scale_length)
            report['clone_native_skin_exact']=native_skin(clone,graph)==skin; report['clone_warnings']=warnings
            V4.need(report['clone_current_input_error']['maximum_m']<=base.LIMIT_M and report['clone_native_skin_exact'] and len(clone.modifiers)==1 and clone.modifiers[0].type=='ARMATURE' and clone.modifiers[0].object==rig and protected.verify()['success'], 'Subsurf baked clone cannot prove current Manual/native skin fidelity')
            progress(report,write,'clone_native_bake_and_protection','complete'); budget()
            bone_names=set(rig.data.bones.keys()); metres=home.unit_settings.scale_length; rest={n:rig.matrix_world@rig.data.bones[n].matrix_local for n in bone_names}; pose={n:rig.matrix_world@rig.evaluated_get(graph).pose.bones[n].matrix for n in bone_names}; parents={n:rig.data.bones[n].parent.name if rig.data.bones[n].parent else None for n in bone_names}
            direct.skirt._activate(context,clone,'OBJECT')
            for obj in context.view_layer.objects: obj.select_set(obj in (clone,rig))
            context.view_layer.objects.active=rig; bpy.ops.preferences.addon_enable(module='io_scene_fbx')
            calls=[n for n in ast.walk(ast.parse(WORKER.read_text(encoding='utf-8'))) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='fbx']
            V4.need(len(calls)==1,'Actual model-only FBX ABI ambiguous'); stage=args.output; filename='plain_native_skin_component.fbx'
            progress(report,write,'native_FBX_writer','start'); result=eval(compile(ast.Expression(body=calls[0]),str(WORKER),'eval'),{'bpy':bpy,'stage':stage,'filename':filename})
            fbx_path=stage/filename; V4.need('FINISHED' in result and fbx_path.is_file(),'Native FBX writer failed'); report['FBX_component_written']=True; report['fbx']={'path':str(fbx_path),'sha256':V4.sha(fbx_path),'bytes':fbx_path.stat().st_size}; write(); budget()
            progress(report,write,'native_FBX_writer','complete'); progress(report,write,'native_FBX_reimport_and_complete_correspondence','start')
            imported_scene=bpy.data.scenes.new('PNS Private FBX Reimport'); imported_scene.unit_settings.scale_length=metres; context.window.scene=imported_scene
            imported=bpy.ops.import_scene.fbx(filepath=str(fbx_path),use_anim=False,use_custom_props=False,automatic_bone_orientation=False,force_connect_children=False,ignore_leaf_bones=False)
            meshes=[o for o in imported_scene.objects if o.type=='MESH']; rigs=[o for o in imported_scene.objects if o.type=='ARMATURE']; V4.need('FINISHED' in imported and len(meshes)==len(rigs)==1,'Native reimport identity Unknown')
            mesh,arm=meshes[0],rigs[0]; graph=context.evaluated_depsgraph_get(); observed=base.native_mesh(mesh,graph)
            report['reimport_current_Manual_error']=base.geometry_pair(cold,target,observed,metres); imported_skin=native_skin(mesh,graph); report['reimport_native_skin_exact']=set(imported_skin['groups'])==set(skin['groups']) and all(imported_skin[k]==skin[k] for k in ('weights','UV','material_indices')); report['imported_material_fidelity']='Unmeasured; original assets remain strictly protected'
            report['reimport_rest_pose_index_scope']='Unknown until all ordered native fields and bone matrices pass'
            V4.need(set(arm.data.bones.keys())==bone_names and {n:arm.data.bones[n].parent.name if arm.data.bones[n].parent else None for n in bone_names}==parents,'Native bone hierarchy Unknown')
            matrices=[(rest[n],arm.matrix_world@arm.data.bones[n].matrix_local) for n in bone_names]+[(pose[n],arm.matrix_world@arm.evaluated_get(graph).pose.bones[n].matrix) for n in bone_names]
            report['reimport_bone_matrix_maxcomponent']=max(abs(a[r][c]-b[r][c])*(metres if c==3 and r<3 else 1.) for a,b in matrices for r in range(4) for c in range(4))
            V4.need(report['reimport_bone_matrix_maxcomponent']<=base.LIMIT_M and report['reimport_current_Manual_error']['maximum_m']<=base.LIMIT_M and report['reimport_native_skin_exact'],'FBX Rest/Manual/index/skin correspondence Unknown; no nearest mapping allowed')
            report['reimport_rest_pose_index_scope']='Exact ordered faces/UV/named weights, same-index current surface and complete native bone matrix guards passed'; report['FBX_reimport_verified']=True; progress(report,write,'native_FBX_reimport_and_complete_correspondence','complete')
        finally:
            progress(report,write,'owned_FBX_cleanup_and_complete_author_guard','start'); context.window.scene=home
            if imported_scene is not None: bpy.data.scenes.remove(imported_scene)
            if clone is not None:
                final_data=clone.data; bpy.data.objects.remove(clone,do_unlink=True)
                for owned in set((data,final_data)):
                    V4.need(owned.users==0,'Owned clone Mesh has outside users'); bpy.data.meshes.remove(owned)
            progress(report,write,'complete_final_Protection_verify','start'); report['protected_original_assets']=protected.verify(); progress(report,write,'complete_final_Protection_verify','complete'); after_assets=content_assets(bpy,q,report,write,'after_FBX')
            report['original_material_images_exact']=all(after_assets.get(n)==value for n,value in assets.items()); report['original_author_contract_exact']=base.authored_contract(bpy,p,q,direct,source,rig,body)==before; write()
            V4.need(report['protected_original_assets']['success'] and report['original_material_images_exact'] and report['original_author_contract_exact'],'Original private author assets changed; no FBX success')
            progress(report,write,'owned_FBX_cleanup_and_complete_author_guard','complete')
    report['FBX_verified']=False; report['native_stages_completed']=True; report['Unity_verified']=False; report['export_accepted']=False

def main():
    pins={Path(__file__).resolve():V4.sha(__file__), ORIGINAL:ORIGINAL_SHA, FAILED:FAILED_SHA, PREVIOUS:PREVIOUS_SHA, TIMED_OUT_REPORT:TIMED_OUT_REPORT_SHA, TIMED_OUT_PROCESS:TIMED_OUT_PROCESS_SHA, V4_FILE:V4_SHA, PROOF:PROOF_SHA, SNAPSHOT:SNAPSHOT_SHA,**FBX_PINS}
    V4.need(all(V4.sha(p)==value for p,value in pins.items()),'Frozen private FBX inputs differ')
    ns=dict(vars(V4)); ns.update(exercise=exercise,_FBX_PINS=pins,progress=progress)
    tree=ast.parse(V4_FILE.read_text(encoding='utf-8')); node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    source=ast.get_source_segment(V4_FILE.read_text(encoding='utf-8'),node); anchor="    need(all(sha(path) == value for path, value in pins.items()), 'Postcase source/helper/self/artist pins differ; do not start Native')"
    V4.need(source.count(anchor)==1,'Frozen full-source Main pin ABI differs'); source=source.replace(anchor,'    pins.update(_FBX_PINS)\n'+anchor)
    redundant="""        locator = load(cold.LOCATOR, cold.LOCATOR_SHA, 'pns_model_locator'); q = p.readers(bpy)
        scene, rig, body, source, _record, choices = cold.load_artist(bpy, p, locator,
            Path(report['artist_before']['receipt']['artist_path']), args.body_object, args.dress_object)
        loaded, pose = q.Protection(), q.pose_channels(rig)
"""
    replacement="""        progress(report,write,'factory_registration_only','start'); q = p.readers(bpy)
        loaded = q.Protection(); source = rig = body = None
        choices = {'basis':'completed_saved_PNS_identity_only','artist_scene_loaded':False,'body':args.body_object,'dress':args.dress_object}
"""
    original_registration="""             and loaded.verify()['success'] and q.pose_channels(rig) == pose, 'Canonical registration changed loaded author content')"""
    V4.need(source.count(redundant)==source.count(original_registration)==1,'Frozen redundant Artist prelude ABI differs')
    source=source.replace(redundant,replacement).replace(original_registration,"             and loaded.verify()['success'], 'Canonical registration changed private factory content')")
    source=source.replace("        report['explicit_selection'] = choices", "        progress(report,write,'factory_registration_only','complete'); report['explicit_selection'] = choices")
    history="        report['historical_provenance'] = historical_provenance(json.loads(HISTORY.read_text(encoding='utf-8')))"
    disk_before="        report['artist_before'] = disk.proof(args.artist_protection, args.artist_protection_sha)"
    disposal="            bpy.ops.wm.read_factory_settings(use_empty=True); report['private_scene_disposed'] = True"
    final_guard="            need(report['source_files_Artist_exact'], 'Current source/helper/self/Artist bytes changed')"
    V4.need(all(source.count(anchor)==1 for anchor in (history,disk_before,disposal,final_guard)),'Frozen protected Main progress ABI differs')
    source=source.replace(history,"        progress(report,write,'pinned_PNS_history','start'); "+history.strip())
    source=source.replace(disk_before,"        progress(report,write,'pinned_PNS_history','complete'); progress(report,write,'Artist_disk_only_before','start'); "+disk_before.strip()+"; progress(report,write,'Artist_disk_only_before','complete')")
    source=source.replace(disposal,"            progress(report,write,'private_factory_disposal','start'); "+disposal.strip()+"; progress(report,write,'private_factory_disposal','complete')")
    source=source.replace("            report['artist_after'] = disk.proof(args.artist_protection, args.artist_protection_sha)","            progress(report,write,'complete_Source_Artist_pins_after','start'); report['artist_after'] = disk.proof(args.artist_protection, args.artist_protection_sha)")
    source=source.replace(final_guard,final_guard+"; progress(report,write,'complete_Source_Artist_pins_after','complete')")
    exec(compile(source,str(V4_FILE),'exec'),ns); return ns['main']()
if __name__=='__main__': raise SystemExit(main())
