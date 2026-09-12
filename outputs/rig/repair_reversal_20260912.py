"""Restore verified unchanged-axis native bone roll only; keep current X assets.

Call repair() inside existing X. Standalone execution reads an immutable copy,
verifies invariants, and writes another copy. Never opens/saves production X.
"""
import bpy,sys,json,math,hashlib,runpy
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import limb_ik as limb, root_control, foot_controls, torso_controls, spine_ik_fk, eye_controls, limb_fk_visuals, bone_display, bone_display_sync, forearm_twist
OUT=Path(__file__).parent
AUDIT=OUT/'reversal_20260912_audit.json'
SOURCE=OUT/'fixtures/X_before_setup_repair_20260912_163011.blend'
DEST=OUT/'fixtures/X_repaired_roll_20260912.blend'

def digest_meshes():
    result={}
    for obj in bpy.data.objects:
        if obj.type!='MESH' or obj.get(limb.OWNER_KEY):continue
        h=hashlib.sha256()
        h.update(repr([(tuple(v.co),tuple((g.group,g.weight) for g in v.groups)) for v in obj.data.vertices]).encode())
        h.update(repr([(e.vertices[0],e.vertices[1]) for e in obj.data.edges]).encode())
        h.update(repr([tuple(p.vertices) for p in obj.data.polygons]).encode())
        if obj.data.shape_keys:
            h.update(repr([(k.name,k.value,k.mute,[tuple(v.co) for v in k.data]) for k in obj.data.shape_keys.key_blocks]).encode())
        result[obj.name]={'mesh_pointer':obj.data.as_pointer(),'object_pointer':obj.as_pointer(),'digest':h.hexdigest(),'groups':[g.name for g in obj.vertex_groups],'matrix':list(map(list,obj.matrix_world)),'modifiers':[(m.name,m.type,m.show_viewport,m.show_render) for m in obj.modifiers]}
    return result
def err(a,b):return max(abs(x-y) for ar,br in zip(a,b) for x,y in zip(ar,br))
def update(rig):
    rig.data.update_tag();rig.update_tag(refresh={'OBJECT'});bpy.context.view_layer.update()
def repair(*,restore_display=True):
    ref=json.loads(AUDIT.read_text(encoding='utf8'))['before']
    rig=bpy.data.objects['CoshaRig']
    if rig.mode=='EDIT':raise RuntimeError('Finish Edit Mode before repairing this rig.')
    ctx=limb._capture_context(bpy.context,rig)
    meshes=digest_meshes();before_bones={b.name:(b.matrix_local.copy(),b.head_local.copy(),b.tail_local.copy(),b.parent.name if b.parent else None,b.use_connect) for b in rig.data.bones}
    bases={p.name:(p.rotation_mode,p.matrix_basis.copy()) for p in rig.pose.bones}
    control_matrices={p.name:p.matrix.copy() for p in rig.pose.bones if p.bone.get(limb.OWNER_KEY)}
    shapes={p.name:(p.custom_shape,p.custom_shape_transform,tuple(p.custom_shape_scale_xyz),tuple(p.custom_shape_translation),tuple(p.custom_shape_rotation_euler)) for p in rig.pose.bones}
    animation_state=runpy.run_path(str(OUT/'verify_root_height_0523_saved.py'))['animation_state']
    animation=animation_state()
    corrective_metadata={o.name:o[forearm_twist.RECORD_KEY] for o in bpy.data.objects if o.type=='MESH' and forearm_twist.RECORD_KEY in o}
    candidates={};skipped=[]
    for b in rig.data.bones:
        if b.get(limb.OWNER_KEY) or b.name not in ref['bones']:continue
        old=ref['bones'][b.name];oldrest=Matrix(old['rest'])
        if err(b.matrix_local,oldrest)<1e-5:continue
        headmatch=(b.head_local-oldrest.translation).length<2e-6
        axismatch=(b.matrix_local.to_3x3().col[1]-oldrest.to_3x3().col[1]).length<2e-5
        parentmatch=(b.parent.name if b.parent else None)==old['parent']
        if not (headmatch and axismatch and parentmatch):
            skipped.append({'bone':b.name,'reason':'Newer bone joint/axis edit preserved'});continue
        roll=bpy.types.Bone.AxisRollFromMatrix(b.matrix_local.to_3x3())[1]
        if abs(roll)>1e-4:raise RuntimeError(f'{b.name}: nonzero current Roll does not match the diagnosed reset; refusing.')
        candidates[b.name]=oldrest.to_3x3().col[2].copy()
    if not candidates:raise RuntimeError('No verified zero-roll mismatches found.')
    mirror=rig.data.use_mirror_x
    paused=(forearm_twist._BUSY,bone_display_sync._BUSY)
    forearm_twist._BUSY=bone_display_sync._BUSY=True
    try:
        rig.data.use_mirror_x=False;limb._mode_set(bpy.context,rig,'EDIT')
        for name,z in candidates.items():rig.data.edit_bones[name].align_roll(z)
        limb._mode_set(bpy.context,rig,'OBJECT');update(rig)
        for name,(mode,basis) in bases.items():
            rig.pose.bones[name].rotation_mode=mode;rig.pose.bones[name].matrix_basis=basis
        update(rig)
        vals={}
        for mod in (limb,root_control,foot_controls,torso_controls,spine_ik_fk,eye_controls,limb_fk_visuals):
            v=mod._validate_inventory(rig) if mod is limb else mod.validate(rig)
            vals[mod.__name__.split('.')[-1]]=bool(v)
        for n,(m,head,tail,parent,connect) in before_bones.items():
            b=rig.data.bones[n]
            assert (b.head_local-head).length<2e-6 and (b.tail_local-tail).length<2e-6,(n,'joint moved')
            assert (b.parent.name if b.parent else None)==parent and b.use_connect==connect,(n,'hierarchy changed')
            if n not in candidates:assert err(b.matrix_local,m)<2e-5,(n,'unrelated rest changed',err(b.matrix_local,m))
        after_mesh=digest_meshes();assert meshes==after_mesh,'Mesh, weights, shape keys, objects or modifiers changed'
        assert animation==animation_state(),'Actions, drivers or animation assignments changed'
        assert corrective_metadata=={o.name:o[forearm_twist.RECORD_KEY] for o in bpy.data.objects if o.type=='MESH' and forearm_twist.RECORD_KEY in o},'Corrective calibration metadata changed'
        for n,s in shapes.items():
            p=rig.pose.bones[n];assert (p.custom_shape,p.custom_shape_transform,tuple(p.custom_shape_scale_xyz),tuple(p.custom_shape_translation),tuple(p.custom_shape_rotation_euler))==s,(n,'display changed')
        control_errors={n:err(rig.pose.bones[n].matrix,m) for n,m in control_matrices.items()}
        report={'ok':True,'restored_roll_bones':list(candidates),'preserved_newer_joint_edits':skipped,'validators':vals,'meshes_weights_shapes_objects_unchanged':True,'animations_unchanged':True,'corrective_metadata_unchanged':True,'native_errors_from_baseline':{},'control_pose_errors':control_errors,'existing_corrective_status':{}}
        for objname in corrective_metadata:
            obj=bpy.data.objects[objname]
            for side,record in forearm_twist._records(obj).items():
                current=forearm_twist._rest_signature(rig,record['chain'])
                report['existing_corrective_status'][objname+'/'+side]={'topology_matches':record['topology']==forearm_twist._topology(obj.data),'rest_exact_match':record['rest']==current,'rest_max_error':max(abs(a-b) for (_,old),(_,new) in zip(record['rest'],current) for a,b in zip(old,new)),'key_muted':obj.data.shape_keys.key_blocks[record['key']].mute}
        for n in ('upper_arm.L','forearm.L','hand.L','upper_arm.R','forearm.R','hand.R','thigh.L','shin.L','thigh.R','shin.R','Head','breast.L','breast.R'):
            p=rig.pose.bones[n];o=Matrix(ref['bones'][n]['pose']);report['native_errors_from_baseline'][n]={'matrix_error':err(p.matrix,o),'rotation_degrees':math.degrees(o.to_quaternion().rotation_difference(p.matrix.to_quaternion()).angle),'head_distance':(p.matrix.translation-o.translation).length}
        if restore_display:report['display_restored']=bone_display.restore_view(rig)
    except Exception:
        limb._mode_set(bpy.context,rig,'EDIT')
        for n,(m,*_) in before_bones.items():rig.data.edit_bones[n].align_roll(m.to_3x3().col[2])
        limb._mode_set(bpy.context,rig,'OBJECT')
        for n,(mode,basis) in bases.items():rig.pose.bones[n].rotation_mode=mode;rig.pose.bones[n].matrix_basis=basis
        update(rig);raise
    finally:
        try:
            rig.data.use_mirror_x=mirror;limb._restore_context(bpy.context,rig,ctx)
        finally:
            forearm_twist._BUSY,bone_display_sync._BUSY=paused
    bone_display_sync.completed(rig)
    return report
if __name__=='__main__':
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False,use_scripts=False)
    report=repair()
    bpy.ops.wm.save_as_mainfile(filepath=str(DEST),copy=True)
    report['output']=str(DEST)
    (OUT/'reversal_20260912_repair_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('REPAIRED_REPORT',json.dumps(report),flush=True)
