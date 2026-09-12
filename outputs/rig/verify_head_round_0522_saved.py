"""Read-only comparison of the final saved X with its live pre-change backup."""
import ast
import bpy
import hashlib
import json
import sys
from pathlib import Path
from mathutils import Matrix, Vector
sys.path.insert(0,r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import head_neck_visuals as hn, eye_controls as eyes, limb_ik, limb_ik_fk
root=Path(r'D:\Blender\Projects\Character\X')
out=root/'outputs/rig'
report=json.loads((out/'head_round_0522_live_result.json').read_text())
tree=ast.parse((out/'round_head_0522.py').read_text())
exec(compile(ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in {'digest','poses'}],type_ignores=[]),'verification_helpers','exec'))
cd.register()
results=[]
for path in (report['backup'],str(root/'X.blend')):
    bpy.ops.wm.open_mainfile(filepath=path,use_scripts=False)
    rig=bpy.data.objects['CoshaRig']
    record=hn.validate(rig)
    head=rig.pose.bones[record['head']]
    widget=head.custom_shape.data
    poses()
    eyes.validate(rig)
    results.append(digest())
assert results[0]==results[1], 'Non-head geometry, pose, animation, display, or weights differ.'
vertices,edges=hn._geometry('HEAD',record['fit'])
local=head.bone.matrix_local.inverted()@Matrix(record['fit']['head_frame'])
assert len(widget.vertices)==len(vertices) and len(widget.edges)==len(edges)
assert max((v.co-local@Vector(p)).length for v,p in zip(widget.vertices,vertices)) < 1e-6
report.update(main_file_saved=True,reopened_verified=True,other_geometry_weights_animation_unchanged=True,version=list(cd.bl_info['version']))
(out/'head_round_0522_saved_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HEAD_ROUND_SAVED_VERIFIED',json.dumps(report),flush=True)
