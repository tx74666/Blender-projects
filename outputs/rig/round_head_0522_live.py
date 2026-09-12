"""Update only the stock head outline in the user's current, unsaved X scene."""
import bpy
import importlib
import json
from pathlib import Path
from datetime import datetime
from mathutils import Matrix, Vector
from character_designer import head_neck_visuals as hn, eye_controls as eyes, limb_ik, limb_ik_fk

hn = importlib.reload(hn)
root = Path(r'D:\Blender\Projects\Character\X')
assert Path(bpy.data.filepath).resolve() == (root/'X.blend').resolve()
rig = bpy.data.objects['CoshaRig']
record = hn.validate(rig)
head = rig.pose.bones[record['head']]
mesh = head.custom_shape.data
local = head.bone.matrix_local.inverted() @ Matrix(record['fit']['head_frame'])
old, old_edges = hn._geometry('HEAD',record['fit'],rounded=False)
assert len(mesh.vertices)==len(old), 'Head widget was edited; preserve it for review.'
assert max((v.co-local@Vector(p)).length for v,p in zip(mesh.vertices,old)) < 1e-6
assert {tuple(sorted(e.vertices)) for e in mesh.edges} == {tuple(sorted(e)) for e in old_edges}
validated = json.loads((root/'outputs/rig/head_round_0522_validation.json').read_text())
assert record['fit']==validated['fit'], 'Current head fit differs from the validated preview.'
before = {pb.name:pb.matrix.copy() for pb in rig.pose.bones}
displays = {pb.name:limb_ik._pose_shape_json_state(pb) for pb in rig.pose.bones}
eye_record = rig.data.get(eyes.RECORD_KEY)
vertices,edges = hn._geometry('HEAD',record['fit'])
backup = root/'outputs/rig/backups'/('X_before_head_round_0522_live_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.blend')
backup.parent.mkdir(parents=True,exist_ok=True)
assert bpy.ops.wm.save_as_mainfile(filepath=str(backup),copy=True)=={'FINISHED'}

class CD_OT_apply_head_round_0522(bpy.types.Operator):
    bl_idname = 'character_designer.apply_head_round_0522'
    bl_label = 'Soften Head Control Side Corners'
    bl_options = {'REGISTER','UNDO'}

    def execute(self,context):
        mesh.clear_geometry()
        mesh.from_pydata([local@Vector(p) for p in vertices],edges,[])
        mesh.update()
        return {'FINISHED'}

bpy.utils.register_class(CD_OT_apply_head_round_0522)
try:
    assert bpy.ops.character_designer.apply_head_round_0522()=={'FINISHED'}
finally:
    bpy.utils.unregister_class(CD_OT_apply_head_round_0522)
limb_ik_fk._update(bpy.context,rig)
hn.validate(rig)
eyes.validate(rig)
pose_error = max(abs(rig.pose.bones[n].matrix[i][j]-m[i][j]) for n,m in before.items() for i in range(4) for j in range(4))
assert pose_error < 2e-6
assert displays == {pb.name:limb_ik._pose_shape_json_state(pb) for pb in rig.pose.bones}
assert eye_record == rig.data.get(eyes.RECORD_KEY)
for area in bpy.context.screen.areas:
    area.tag_redraw()
report = {'ok':True,'backup':str(backup),'pose_error':pose_error,'display_assignments_unchanged':True,
          'eye_record_unchanged':True,'vertices':len(mesh.vertices),'main_file_saved':False}
(root/'outputs/rig/head_round_0522_live_result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HEAD_ROUND_0522_LIVE',json.dumps(report))
