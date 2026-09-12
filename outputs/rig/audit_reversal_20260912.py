"""Read-only two immutable-file comparison for limb removal incident."""
import bpy, sys, json, math, hashlib
from pathlib import Path
from mathutils import Matrix
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import limb_ik as limb, limb_ik_fk as ikfk
from character_designer import root_control, foot_controls, torso_controls, spine_ik_fk, eye_controls, limb_fk_visuals

OUT = Path(__file__).parent
FILES = [OUT/'fixtures/X_body_setup_20260911_053445_231.blend', OUT/'fixtures/X_before_setup_repair_20260912_163011.blend']
def plain(v):
    if isinstance(v,bpy.types.ID): return v.name
    if isinstance(v,(str,int,float,bool)) or v is None: return v
    if hasattr(v,'items'): return {str(k):plain(x) for k,x in v.items()}
    try:return [plain(x) for x in v]
    except:return str(v)
def mat(m):return [list(r) for r in m]
def get():
    rig=bpy.data.objects['CoshaRig']; bpy.context.view_layer.update()
    r={'path':bpy.data.filepath,'frame':bpy.context.scene.frame_current,'rig_matrix':mat(rig.matrix_world),'props':plain(dict(rig.items())),'data_props':plain(dict(rig.data.items())),'bones':{},'validators':{},'inventory':{}}
    for b in rig.data.bones:
        p=rig.pose.bones[b.name]
        r['bones'][b.name]={'parent':b.parent.name if b.parent else None,'rest':mat(b.matrix_local),'pose':mat(p.matrix),'basis':mat(p.matrix_basis),'head':list(p.head),'tail':list(p.tail),'props':plain(dict(b.items())),'pose_props':plain(dict(p.items())),'constraints':[],'hidden':b.hide,'deform':b.use_deform}
        for c in p.constraints:
            d={}
            for prop in c.bl_rna.properties:
                if prop.identifier in ('rna_type','error_location','error_rotation'):continue
                try:d[prop.identifier]=plain(getattr(c,prop.identifier))
                except:pass
            r['bones'][b.name]['constraints'].append(d)
    for mod in [limb,root_control,foot_controls,torso_controls,spine_ik_fk,eye_controls,limb_fk_visuals]:
        try:
            data=mod._validate_inventory(rig) if mod is limb else mod.validate(rig)
            r['validators'][mod.__name__]={'ok':True,'present':bool(data)}
            if mod is limb:
                for key,v in data['rigs'].items():
                    r['inventory'][':'.join(key)]={k:plain(x) for k,x in v.items() if k in ('schema','chain','auto_align','auto_rotation_space','pole_direction','target_rotation_version','configured_pole_direction')}
                    r['inventory'][':'.join(key)].update({k:v[k].name if v.get(k) else None for k in ('target','pole','solver_target','auto_offset_rotation','ori_upper','ori_lower')})
                    r['inventory'][':'.join(key)]['mode']=ikfk.mode_for_rig(rig,v)
        except Exception as e:r['validators'][mod.__name__]={'ok':False,'error':str(e)}
    return r
records=[]
for f in FILES:
    before=hashlib.sha256(f.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(f),load_ui=False,use_scripts=False)
    records.append(get());assert before==hashlib.sha256(f.read_bytes()).hexdigest()
a,b=records
diff={'removed_bones':sorted(set(a['bones'])-set(b['bones'])),'added_bones':sorted(set(b['bones'])-set(a['bones'])),'native':{},'control':{}}
for name,old in a['bones'].items():
    if name not in b['bones']:continue
    new=b['bones'][name]
    delta={}
    for k in ('rest','pose','basis'):
        om,nm=Matrix(old[k]),Matrix(new[k]);err=max(abs(x-y) for ro,rn in zip(om,nm) for x,y in zip(ro,rn))
        if err>1e-5:delta[k]={'max_error':err,'rotation_degrees':math.degrees(om.to_quaternion().rotation_difference(nm.to_quaternion()).angle),'translation_distance':(om.translation-nm.translation).length}
    for k in ('parent','constraints','props','pose_props'):
        if old[k]!=new[k]:delta[k]={'before':old[k],'after':new[k]}
    if delta:diff['native' if not old['props'].get(limb.OWNER_KEY) else 'control'][name]=delta
result={'before':a,'after':b,'diff':diff}
(OUT/'reversal_20260912_audit.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('REVERSAL_AUDIT',json.dumps({'before_validators':a['validators'],'after_validators':b['validators'],'inventory_before':a['inventory'],'inventory_after':b['inventory'],'removed':diff['removed_bones'],'added':diff['added_bones'],'native_diffs':{n:{k:v for k,v in d.items() if k in ('rest','pose','basis','parent')} for n,d in diff['native'].items()} }),flush=True)
