"""One live-scene read-only checkpoint, before any refresh/install/save decision.
Explicit Body/Dress inputs are QA selections, never a missing Setup fallback.
No addon import/register, bpy.ops, evaluation, seek, cache or Blender RNA writes.
The only output is a new JSON beneath HERE; live-vs-disk content identity Unknown.
"""
import argparse, ast, hashlib, json, sys, traceback
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent
CANONICAL=Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer')
COMPARATOR=HERE/'compare_current_artist_fixture52.py'; COMPARATOR_SHA='b0b4730dac104dc6ad750eaba2ee7cb89acf6ed57a274d15f8c7bc57f296ec6f'
QA=HERE/'validate_real_dress.py'; QA_SHA='613e9d32f3674f1e01d98725a99d1dd70911d22af1526f36a43f442c47649046'
COLD=HERE/'verify_direct_cold_install52_v4.py'; COLD_SHA='4bb8e79fbad87950c75c1999e27d97657733ea42695df8e0f2b3a2ae4f58c536'
RECORD_KEY='character_designer_skirt_v1'; RIG_KEY='character_designer_skirt_armature'
STATE_KEY='character_designer_dress_direct_state_v1'; PROFILE_KEY='character_designer_dress_motion_v1'
READ=('digest','id_name','custom_content','simple_rna','curve_content','action_content','raw_mesh_content','rest_content','pose_channels')
def need(value,message):
    if not value: raise RuntimeError('SceneReadOnly52: '+message)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''): h.update(block)
    return h.hexdigest()
def disk_state(path):
    first=path.stat(); digest=sha(path); after=path.stat()
    need((first.st_size,first.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'Disk changed during read')
    return {'path':str(path),'bytes':after.st_size,'mtime_ns':after.st_mtime_ns,'sha256':digest}
def source_manifest():
    return {str(p.relative_to(CANONICAL)).replace('\\','/'):{'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns,'sha256':sha(p)}
            for p in sorted(CANONICAL.rglob('*.py')) if '__pycache__' not in p.parts}
def selected_nodes(path,names):
    tree=ast.parse(path.read_text(encoding='utf-8')); nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    need({n.name for n in nodes}==set(names),'Frozen reader symbols differ'); return nodes
def read_helpers(bpy):
    need(all(sha(p)==s for p,s in ((COMPARATOR,COMPARATOR_SHA),(QA,QA_SHA),(COLD,COLD_SHA))),'Readonly reader SHA differs')
    # Compile only the exact existing readers/animation and selection functions;
    # never execute either helper's main, import addon, or registered locator.
    values={'ast':ast,'hashlib':hashlib,'json':json,'SimpleNamespace':SimpleNamespace,'QA':QA,'READ':READ,'need':need}
    exec(compile(ast.Module(body=selected_nodes(COMPARATOR,('readers','animation')),type_ignores=[]),str(COMPARATOR),'exec'),values)
    q=values['readers'](bpy); values.update(bpy=bpy)
    exec(compile(ast.Module(body=selected_nodes(COLD,('bone_selection',)),type_ignores=[]),str(COLD),'exec'),values)
    return q,SimpleNamespace(animation=values['animation'],bone_selection=values['bone_selection'])
def identity(obj,q):
    return None if obj is None else {'ID':q.id_name(obj),'pointer':obj.as_pointer(),'type':getattr(obj,'type',None),
        'data_ID':q.id_name(getattr(obj,'data',None)),'data_pointer':None if getattr(obj,'data',None) is None else obj.data.as_pointer()}
def observe(owner,name,q):
    if owner is None or not hasattr(owner,name): return {'status':'Unknown','reason':'RNA owner/property absent'}
    try: return {'status':'measured','value':q.custom_content(getattr(owner,name))}
    except Exception as exc: return {'status':'Unknown','reason':repr(exc)}
def json_property(owner,key):
    raw=owner.get(key)
    if raw is None: return {'status':'absent','raw':None}
    if type(raw) is not str: return {'status':'Unknown','raw_type':type(raw).__name__}
    try:
        value=json.loads(raw); need(type(value) is dict,'Expected JSON dictionary')
        return {'status':'measured','raw_sha256':hashlib.sha256(raw.encode('utf-8')).hexdigest(),'value':value}
    except Exception as exc: return {'status':'Unknown','reason':repr(exc),'raw_sha256':hashlib.sha256(raw.encode('utf-8')).hexdigest()}
def scene_state(bpy,q,p):
    context=bpy.context; scene=context.scene; setup=getattr(scene,'character_designer_setup',None); wm=getattr(context.window_manager,'character_designer_skirt',None)
    return {'filepath':bpy.data.filepath,'is_dirty':bpy.data.is_dirty,'Scene':identity(scene,q),'view_layer':context.view_layer.name,
        'frame':[scene.frame_current,scene.frame_subframe],'mode':context.mode,'active':identity(context.view_layer.objects.active,q),
        'selected':[identity(o,q) for o in context.selected_objects],
        'Setup':{'RNA_present':setup is not None,'raw_storage':q.custom_content(scene.get('character_designer_setup')),
                 'MainRig':observe(setup,'rig',q),'Body':observe(setup,'body',q)},
        'WindowManager':{'RNA_present':wm is not None,'Dress':observe(wm,'source',q),'Rig':observe(wm,'armature',q)},
        'units':q.simple_rna(scene.unit_settings),'autokey':scene.tool_settings.use_keyframe_insert_auto}
def authored_state(bpy,q,p,dress,rig,body):
    result={'objects':{},'pose':q.pose_channels(rig),'pose_position':rig.data.pose_position,
        'active_bone':None if rig.data.bones.active is None else rig.data.bones.active.name,
        'bone_selection':p.bone_selection(rig),'bone_collections':[{'name':c.name,'pointer':c.as_pointer(),'rna':q.simple_rna(c)} for c in rig.data.collections_all],
        'Rest_sha256':q.digest(q.rest_content(rig)),'Rest_endpoints_sha256':q.digest([(b.name,list(b.head_local),list(b.tail_local)) for b in rig.data.bones])}
    for role,obj in (('Dress',dress),('MainRig',rig),('Body',body)):
        owners=[obj,obj.data]+([obj.data.shape_keys] if obj.type=='MESH' and obj.data.shape_keys else [])
        row={'identity':identity(obj,q),'data_users':obj.data.users,'bindings':[p.animation(o,q) for o in owners],
            'parent':identity(obj.parent,q),'parent_type':obj.parent_type,'parent_bone':obj.parent_bone,
            'parent_inverse':[list(r) for r in obj.matrix_parent_inverse],'basis':[list(r) for r in obj.matrix_basis],
            'world_raw':[list(r) for r in obj.matrix_world],'constraints':[q.simple_rna(c) for c in obj.constraints],
            'modifiers':[(m.name,m.type,m.as_pointer(),q.simple_rna(m)) for m in obj.modifiers]}
        if obj.type=='MESH':
            raw=q.raw_mesh_content(obj); row['raw_fields']={k:{'sha256':q.digest(v),'count':len(v) if isinstance(v,(list,dict)) else None} for k,v in raw.items()}
            keys=obj.data.shape_keys; row['Keys']=None if keys is None else {'identity':identity(keys,q),'channel_rna':q.simple_rna(keys),
                'count':len(keys.key_blocks),'blocks':[{'name':b.name,'channels':q.simple_rna(b),'coordinates_sha256':q.digest([tuple(v.co) for v in b.data])} for b in keys.key_blocks]}
        result['objects'][role]=row
    return result
def loaded_modules():
    result={}
    for name,module in tuple(sys.modules.items()):
        if module is None or not (name=='character_designer' or '.character_designer' in name or name.startswith('character_designer.')): continue
        path=getattr(module,'__file__',None); info=getattr(module,'bl_info',None)
        result[name]={'path':path,'bl_info':info,'disk_sha256':sha(path) if path and Path(path).is_file() else None,
                      'in_memory_code_equals_disk':'Unknown; loaded path and current file bytes are separate observations'}
    return result
def physics_state(bpy,q,dress):
    parsed=json_property(dress,RECORD_KEY); value=parsed.get('value'); result={'record':parsed,'classification':'Unknown',
        'Direct_state':json_property(dress,STATE_KEY),'motion_profile':json_property(dress,PROFILE_KEY),'cache_payload_preserved':'Unknown'}
    if type(value) is not dict: return result
    physics=value.get('physics'); result['physics']=physics
    if physics is None and type(value.get('controls')) is dict: result['classification']='CONTROLS_ONLY_LEGACY'
    elif type(physics) is dict:
        backend=physics.get('backend'); result['classification']={'DIRECT_MAIN_CLOTH_V1':'DIRECT','ACTUAL_SURFACE_DELTA_V1':'DELTA','LEGACY_CAGE':'LEGACY_PHYSICS'}.get(backend,'Unknown')
        if backend is None: result['classification']='LEGACY_UNTAGGED_PHYSICS'
        name=physics.get('proxy'); proxy=bpy.data.objects.get(name) if type(name) is str else None
        result['proxy']=identity(proxy,q); result['cache']=[]
        if proxy:
            for mod in proxy.modifiers:
                if mod.type!='CLOTH': continue
                cache=mod.point_cache; row={'modifier':mod.name,'flags':[mod.show_viewport,mod.show_render],'cache_pointer':cache.as_pointer(),'fields':{}}
                for field in ('frame_start','frame_end','frame_step','is_baked','is_baking','is_outdated','info','use_disk_cache','use_external','filepath','use_library_path','index','name'):
                    row['fields'][field]=observe(cache,field,q)
                result['cache'].append(row)
    return result
def audit(bpy,output,body_name,dress_name):
    output=Path(output); need(output.is_absolute() and output.resolve().is_relative_to(HERE) and output.suffix=='.json' and output.parent.is_dir() and not output.exists(),'One fresh HERE JSON required')
    q,p=read_helpers(bpy); pins={str(x):s for x,s in ((COMPARATOR,COMPARATOR_SHA),(QA,QA_SHA),(COLD,COLD_SHA))}; before_source=source_manifest()
    filepath=Path(bpy.data.filepath) if bpy.data.filepath else None; before_disk=disk_state(filepath) if filepath and filepath.is_file() else None
    report={'schema':'READ_ONLY_LIVE_SCENE_CHECKPOINT52_V1','captured_UTC':datetime.now(timezone.utc).isoformat(),'collection_success':False,'accepted':False,
        'scope':'Actual loaded current scene; explicit QA selection; no addon import/register/operators/evaluation/RNA writes; output checkpoint only',
        'BlenderVersion':list(bpy.app.version),'BlenderVersionString':bpy.app.version_string,'background':bpy.app.background,'loaded_modules':loaded_modules(),
        'reader_pins':pins,'self_sha256':sha(__file__),'source_before':before_source,'disk_before':before_disk,
        'live_raw_content_equals_saved_disk':'Unknown; disk SHA proves bytes only, no second scene is loaded','saved_any_blend':False,'errors':[]}
    protected=q.Protection(); initial_context=scene_state(bpy,q,p); report['scene']=initial_context; initial_authored=None
    try:
        dress=bpy.data.objects.get(dress_name); body=bpy.data.objects.get(body_name)
        need(dress is not None and body is not None and dress.type==body.type=='MESH','Explicit input objects absent or not Mesh')
        rig=dress.get(RIG_KEY); need(isinstance(rig,bpy.types.Object) and rig.type=='ARMATURE','Dress native RIG pointer absent/invalid; no name fallback')
        record=json_property(dress,RECORD_KEY); need(record['status']=='measured' and record['value'].get('source')==dress.name and record['value'].get('rig')==rig.name,'Dress saved identity/record mismatch')
        need(dress.name in bpy.context.scene.objects and body.name in bpy.context.scene.objects and rig.name in bpy.context.scene.objects,'Explicit objects outside current scene')
        report['selection_provenance']={'method':'Explicit Body/Dress QA input plus native saved Dress RIG pointer','registered_setup_claimed':False,
            'Dress':identity(dress,q),'MainRig':identity(rig,q),'Body':identity(body,q),'Body_enabled_ARM_targets':[identity(m.object,q) for m in body.modifiers if m.type=='ARMATURE' and m.show_viewport]}
        initial_authored=authored_state(bpy,q,p,dress,rig,body); report['author']=initial_authored; report['physics']=physics_state(bpy,q,dress)
        report['whole_scene_raw_protection_before']={'meshes':protected.meshes,'rest':protected.rests,'actions':protected.actions,'NLA_assets_sha256':q.digest(protected.start_nla)}
        report['author_readback_exact']=authored_state(bpy,q,p,dress,rig,body)==initial_authored
        need(report['author_readback_exact'],'Read-only author/raw/pose/selection/Keys/bindings fingerprint changed')
        report['collection_success']=True
    except Exception as exc: report['errors'].append({'error':repr(exc),'traceback':traceback.format_exc()})
    finally:
        report['whole_scene_raw_protection_after']=protected.verify(); report['context_readback_exact']=scene_state(bpy,q,p)==initial_context
        report['source_after']=source_manifest(); report['source_exact']=before_source==report['source_after']
        report['disk_after']=disk_state(filepath) if before_disk else None
        report['disk_protection_measured']=before_disk is not None
        report['disk_exact']=before_disk==report['disk_after'] if before_disk is not None else 'Unknown'
        report['reader_pins_exact']=all(sha(path)==value for path,value in pins.items())
        report['collection_success']=bool(report['collection_success'] and not report['errors'] and report['whole_scene_raw_protection_after']['success'] and report['context_readback_exact'] and report['source_exact'] and report['disk_exact'] is True and report['reader_pins_exact'])
        with output.open('x',encoding='utf-8') as stream: json.dump(report,stream,ensure_ascii=False,allow_nan=False,indent=2)
    return report
def readonly_source_proof():
    paths={Path(__file__):None,COMPARATOR:('readers','animation'),COLD:('bone_selection',),QA:set(READ)|{'Protection'}}
    count=0
    for path,names in paths.items():
        tree=ast.parse(path.read_text(encoding='utf-8')); nodes=tree.body if names is None else selected_nodes(path,names)
        for node in nodes:
            for item in ast.walk(node):
                if isinstance(item,(ast.Import,ast.ImportFrom)):
                    modules=[a.name for a in item.names] if isinstance(item,ast.Import) else [item.module or '']
                    need(not any('character_designer' in m or 'mathutils' in m for m in modules),'Addon/evaluation import found')
                if isinstance(item,ast.Attribute): need(not ast.unparse(item).startswith('bpy.ops'),'Operator reference found')
                if isinstance(item,ast.Call):
                    name=ast.unparse(item.func); need(not any(s in name for s in ('evaluated_get','evaluated_depsgraph_get','frame_set','update_tag','foreach_set','to_mesh','register','select_set','hide_set')),'Mutation/evaluation call found: '+name)
                if isinstance(item,ast.Attribute) and isinstance(item.ctx,(ast.Store,ast.Del)): need(isinstance(item.value,ast.Name) and item.value.id=='self' and path==QA,'RNA/foreign attribute assignment found')
            count+=1
    need(all(sha(p)==s for p,s in ((COMPARATOR,COMPARATOR_SHA),(QA,QA_SHA),(COLD,COLD_SHA))),'Frozen reader pins differ')
    print(json.dumps({'SOURCE_ONLY':True,'AST_nodes_checked':count,'operator_or_evaluation_calls':0,'Blender_RNA_attribute_writes':0,'Native_executed':False}))
def main():
    if '--source-only-checks' in sys.argv: readonly_source_proof(); return 0
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True); parser.add_argument('--body-object',required=True); parser.add_argument('--dress-object',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    import bpy
    result=audit(bpy,args.output,args.body_object,args.dress_object); return 0 if result['collection_success'] else 2
if __name__=='__main__': raise SystemExit(main())
