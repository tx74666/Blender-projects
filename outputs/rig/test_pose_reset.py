import bpy, sys, json
from pathlib import Path
from mathutils import Matrix
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import limb_ik, limb_ik_fk
ROOT=Path(r'D:\Blender\Projects\Character\X\outputs\rig')
rig=bpy.data.objects['CoshaRig']
bpy.context.view_layer.objects.active=rig
rig.select_set(True)
inventory=limb_ik._validate_inventory(rig)
print('SCHEMA',inventory['schema'])
def err(a,b):return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))
for key,r in inventory['rigs'].items():
    print('LIMB',key, 'chain',r['chain'],'mode',limb_ik_fk.mode_for_rig(rig,r))
    print('BEFORE',[(n,err(rig.pose.bones[n].matrix,rig.data.bones[n].matrix_local)) for n in limb_ik_fk.pose_names(r)])
report=[]
for key,r in inventory['rigs'].items():
    desired={n:rig.data.bones[n].matrix_local.copy() for n in limb_ik_fk.pose_names(r)}
    try:
        res=limb_ik_fk.match_existing_pose(bpy.context,rig,key,desired,keyframe=False)
        print('MATCH',key,res)
        report.append(dict(key=list(key),result=res))
    except Exception as e:
        print('FAIL',key,repr(e))
        raise
after={n:dict(basis=[list(row) for row in pb.matrix_basis], mode=pb.rotation_mode) for n,pb in rig.pose.bones.items()}
for key,r in inventory['rigs'].items():
    print('AFTER',[(n,err(rig.pose.bones[n].matrix,rig.data.bones[n].matrix_local)) for n in limb_ik_fk.pose_names(r)])
(ROOT/'pose_reset_solution.json').write_text(json.dumps(dict(results=report,bones=after),indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'X_pose_reset_preview.blend'),copy=True)
