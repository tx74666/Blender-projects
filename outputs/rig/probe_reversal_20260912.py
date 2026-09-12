import bpy,sys,json,math
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import limb_ik as limb,root_control,limb_fk_visuals,control_colors,bone_display
OUT=Path(__file__).parent
r=json.loads((OUT/'reversal_20260912_audit.json').read_text())
for key in ('before','after'):
    b=r[key]['bones']; print('ROLLS',key,{n:math.degrees(bpy.types.Bone.AxisRollFromMatrix(Matrix(b[n]['rest']).to_3x3())[1]) for n in ('Chest','Head','upper_arm.L','forearm.L','upper_arm.R','forearm.R','breast.L','thigh.L','shin.L','f_index.01.L')})
bpy.ops.wm.open_mainfile(filepath=r['before']['path'],load_ui=False,use_scripts=False)
rig=bpy.data.objects['CoshaRig'];limb._mode_set(bpy.context,rig,'OBJECT')
before={b.name:b.matrix_local.copy() for b in rig.data.bones}
for label,fn in [('FK Remove',lambda:limb_fk_visuals.remove(bpy.context,rig)),('Root Remove',lambda:root_control.remove(bpy.context,rig)),('Color Restore',lambda:control_colors.restore(rig))]:
    try:print('OP',label,fn())
    except Exception as e:print('OPERROR',label,repr(e))
    print('REST_CHANGES',label,{n:max(abs(a-b) for ro,rn in zip(m,rig.data.bones[n].matrix_local) for a,b in zip(ro,rn)) for n,m in before.items() if n in rig.data.bones and max(abs(a-b) for ro,rn in zip(m,rig.data.bones[n].matrix_local) for a,b in zip(ro,rn))>1e-5})
