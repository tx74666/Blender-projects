import bpy, json, hashlib, importlib.util, sys, traceback
from pathlib import Path

ROOT=Path(r'D:\Blender\Projects\Character\X')
ASSET=Path(r'D:\Unity Projects\RandomRealm2\Assets\Art\Character\Cosha')
OUT=ROOT/'outputs/unity_export_0575/weight_diagnosis.json'
SOURCE=ROOT/'X.blend'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
report={'source':str(SOURCE),'source_sha256_before':sha(SOURCE),'fbx':str(ASSET/'Cosha.fbx')}
manifest=json.loads((ASSET/'Cosha.cdesigner.json').read_text('utf-8'))
report['manifest_files']={p:{'expected':expected,'actual':sha(ASSET/p),'match':sha(ASSET/p)==expected} for p,expected in manifest['files'].items()}
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)

def inspect(obj):
    mesh=obj.data
    deform={b.name for mod in obj.modifiers if mod.type=='ARMATURE' and mod.object and mod.show_viewport for b in mod.object.data.bones if b.use_deform}
    names={g.index:g.name for g in obj.vertex_groups}
    ids={i for i,n in names.items() if n in deform}
    invalid=[v for v in mesh.vertices if not any(g.group in ids and g.weight>1e-8 for g in v.groups)]
    linked_edges={v.index:[] for v in invalid}; linked_faces={v.index:[] for v in invalid}
    for e in mesh.edges:
        for i in e.vertices:
            if i in linked_edges:linked_edges[i].append(e.index)
    for p in mesh.polygons:
        for i in p.vertices:
            if i in linked_faces:linked_faces[i].append(p.index)
    return {'vertices':len(mesh.vertices),'polygons':len(mesh.polygons),'unweighted_count':len(invalid),'unweighted':[
        {'index':v.index,'co':list(v.co),'world':list(obj.matrix_world@v.co),'groups':{names[g.group]:g.weight for g in v.groups},'edges':linked_edges[v.index],'faces':linked_faces[v.index]} for v in invalid],
        'shape_keys':[k.name for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else []}

obj=bpy.data.objects['Cosha']
report['source_mesh']=inspect(obj)
report['source_mesh']['unweighted_neighbors']={}
for item in report['source_mesh']['unweighted']:
    i=item['index']
    neighbors=sorted({v for e in obj.data.edges if i in e.vertices for v in e.vertices if v!=i})
    report['source_mesh']['unweighted_neighbors'][str(i)]={
        'adjacent':[{'index':j,'world':list(obj.matrix_world@obj.data.vertices[j].co),'groups':{obj.vertex_groups[g.group].name:g.weight for g in obj.data.vertices[j].groups}} for j in neighbors],
        'materials':list({obj.data.materials[obj.data.polygons[f].material_index].name for f in item['faces']}),
        'shape_delta':{k.name:(k.data[i].co-k.relative_key.data[i].co).length for k in obj.data.shape_keys.key_blocks if k!=obj.data.shape_keys.reference_key}
    }
report['head_bones']={b.name:{'head_world':list(bpy.data.objects['CoshaRig'].matrix_world@b.head_local),'tail_world':list(bpy.data.objects['CoshaRig'].matrix_world@b.tail_local)} for b in bpy.data.objects['CoshaRig'].data.bones if b.name in ('Head','Neck','eye.L','eye.R')}
raw=obj.get('character_designer_forearm_twist_v1','{}')
records=json.loads(raw)
report['calibration']={}
owned=[]
for side,rec in records.items():
    key=obj.data.shape_keys.key_blocks.get(rec['key'])
    owned.append(rec['key'])
    item={k:v for k,v in rec.items() if k in ('enabled','key','armature','upper','forearm','hand','topology','mesh','version','created_basis')}
    item['record_keys']=list(rec)
    item['key_exists']=key is not None
    if key:
        distances=[(a.co-b.co).length for a,b in zip(key.data,key.relative_key.data)]
        item.update({'value':key.value,'mute':key.mute,'nonzero_deltas':sum(d>1e-8 for d in distances),'max_delta':max(distances,default=0)})
    report['calibration'][side]=item
report['source_rig']={'bones':len(bpy.data.objects['CoshaRig'].data.bones),'pose_basis_nonidentity':[p.name for p in bpy.data.objects['CoshaRig'].pose.bones if sum(abs(p.matrix_basis[i][j]-(1 if i==j else 0)) for i in range(4) for j in range(4))>1e-5]}

# Check whether saved calibration actually remains valid and updates the skin in this saved source.
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
try:
    from character_designer import forearm_twist
    forearm_twist.update_runtime(bpy.context.scene)
    report['calibration_runtime_errors']=dict(forearm_twist._ERRORS)
    report['calibration_after_runtime']={side:{'mute':obj.data.shape_keys.key_blocks[rec['key']].mute,'value':obj.data.shape_keys.key_blocks[rec['key']].value} for side,rec in records.items()}
    from mathutils import Matrix
    import math
    arm=bpy.data.objects['CoshaRig']
    saved={p.name:p.matrix_basis.copy() for p in arm.pose.bones}
    report['isolated_calibration_45deg_probe']={}
    for side,rec in records.items():
        hand=arm.pose.bones[rec['chain'][-1]]
        hand.matrix_basis=saved[hand.name]@Matrix.Rotation(math.radians(45),4,'Y')
        bpy.context.view_layer.update()
        forearm_twist.update_runtime(bpy.context.scene)
        key=obj.data.shape_keys.key_blocks[rec['key']]
        distances=[(a.co-b.co).length for a,b in zip(key.data,key.relative_key.data)]
        report['isolated_calibration_45deg_probe'][side]={'runtime_errors':dict(forearm_twist._ERRORS),'mute':key.mute,'nonzero_deltas_gt_1e6':sum(d>1e-6 for d in distances),'max_delta':max(distances,default=0)}
        hand.matrix_basis=saved[hand.name]
        bpy.context.view_layer.update()
        forearm_twist.update_runtime(bpy.context.scene)
except Exception as exc:
    report['calibration_runtime_diagnostic_error']=repr(exc)

path=Path(r'D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\unity_export_worker.py')
spec=importlib.util.spec_from_file_location('isolated_export_worker',path)
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
warnings=[]
report['baked_mesh_info']=worker._bake_mesh(bpy.context,obj,owned,warnings)
report['baked_mesh']=inspect(obj)
report['baker_warnings']=warnings

# Import the exact user's existing FBX into a disposable empty scene. No save/export.
bpy.ops.wm.read_factory_settings(use_empty=True)
report['fbx_import_result']=list(bpy.ops.import_scene.fbx(filepath=str(ASSET/'Cosha.fbx'),use_anim=False))
report['fbx_armatures']={o.name:len(o.data.bones) for o in bpy.context.scene.objects if o.type=='ARMATURE'}
report['fbx_meshes']={o.name:inspect(o) for o in bpy.context.scene.objects if o.type=='MESH'}
report['source_sha256_after']=sha(SOURCE)
report['source_unchanged']=report['source_sha256_before']==report['source_sha256_after']
report['output_assets_unchanged']=all(sha(ASSET/p)==v['actual'] for p,v in report['manifest_files'].items())
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False),'utf-8')
print('WEIGHT_DIAGNOSIS_PASSED',str(OUT))
