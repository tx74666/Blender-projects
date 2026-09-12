"""Fit the stock global outline to the sole displays without moving its pivot."""
import bpy, hashlib, importlib, json, sys
from pathlib import Path
from datetime import datetime
from mathutils import Matrix, Vector
ROOT=Path(r'D:\Blender\Projects\Character\X')
OUT=ROOT/'outputs/rig'
live=not bpy.app.background
if not live:
    sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
    import character_designer as cd
    cd.register()
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'X.blend'),use_scripts=False)
from character_designer import limb_ik, limb_ik_fk, root_control, head_neck_visuals, eye_controls
if live:
    # Load only the new pure helper, keeping every registered module untouched.
    import ast
    tree=ast.parse((Path(r'D:\MyRepository\Blender-addons-by-Randy\addons\character_designer\limb_ik.py')).read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_master_widget_translation')
    exec(compile(ast.Module(body=[node],type_ignores=[]),'root_display_height','exec'),limb_ik.__dict__)
assert Path(bpy.data.filepath).resolve()==(ROOT/'X.blend').resolve()
rig=bpy.data.objects['CoshaRig']
record=root_control.validate(rig)
master=rig.pose.bones[record['master']]
assert tuple(master.custom_shape_translation)==(0.,0.,0.), 'Root display was edited; preserve it for review.'
assert not master.custom_shape_transform
limb_ik_fk._update(bpy.context,rig)
before={pb.name:pb.matrix.copy() for pb in rig.pose.bones}
rest={b.name:root_control._state(b) for b in rig.data.bones}
displays={pb.name:limb_ik._pose_shape_json_state(pb) for pb in rig.pose.bones}

def assets():
    values=[]
    for obj in bpy.data.objects:
        if obj.type=='MESH':
            values.append([obj.name,[list(v.co) for v in obj.data.vertices],
                           [[(g.group,g.weight) for g in v.groups] for v in obj.data.vertices]])
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()

digest=assets()
translation=limb_ik._master_widget_translation(rig)
assert -.15 < translation[2] < -.12 and max(abs(v) for v in translation[:2])<1e-6,translation
backup=None
if live:
    backup=OUT/'backups'/('X_before_root_height_0523_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
    backup.parent.mkdir(parents=True,exist_ok=True)
    assert bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True)=={'FINISHED'}
    class CD_OT_fit_root_height_0523(bpy.types.Operator):
        bl_idname='character_designer.fit_root_height_0523'
        bl_label='Align Root Outline to Shoe Soles'
        bl_options={'REGISTER','UNDO'}
        def execute(self,context):
            master.custom_shape_translation=translation
            return {'FINISHED'}
    bpy.utils.register_class(CD_OT_fit_root_height_0523)
    try:
        assert bpy.ops.character_designer.fit_root_height_0523()=={'FINISHED'}
    finally:
        bpy.utils.unregister_class(CD_OT_fit_root_height_0523)
else:
    master.custom_shape_translation=translation
limb_ik_fk._update(bpy.context,rig)
root_control.validate(rig)
limb_ik._validate_inventory(rig)
head_neck_visuals.validate(rig)
eye_controls.validate(rig)
error=max(abs(rig.pose.bones[n].matrix[i][j]-m[i][j]) for n,m in before.items() for i in range(4) for j in range(4))
assert error<2e-6
assert rest=={b.name:root_control._state(b) for b in rig.data.bones}
assert assets()==digest
expected=json.loads(json.dumps(displays))
expected[master.name]['translation']=list(master.custom_shape_translation)
assert expected=={pb.name:limb_ik._pose_shape_json_state(pb) for pb in rig.pose.bones}
report={'ok':True,'pose_error':error,'translation':list(master.custom_shape_translation),
        'world_lowered':abs(translation[2])*rig.scale.z,'native_pivots_unchanged':True,
        'geometry_weights_other_displays_unchanged':True,'live':live,'main_file_saved':False,
        'backup':str(backup) if backup else None}
if not live:
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'X_root_height_0523_preview.blend'),copy=True)
(OUT/('root_height_0523_live_result.json' if live else 'root_height_0523_validation.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('ROOT_HEIGHT_0523',json.dumps(report),flush=True)
