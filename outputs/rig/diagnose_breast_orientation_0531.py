"""Compare saved view Z, local Z and global Z using the actual transform operator."""
import bpy
import hashlib
import importlib.util
import json
from pathlib import Path
from mathutils import Vector

OUT = Path(r'D:\Blender\Projects\Character\X\outputs/rig')
SOURCE = OUT.parent.parent / 'X.blend'
spec = importlib.util.spec_from_file_location('diagnostic_helpers', OUT/'diagnose_breast_gz_0531.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),use_scripts=False)
d.rig = rig = bpy.data.objects['CoshaRig']
if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
for obj in bpy.context.selected_objects: obj.select_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='POSE')
d.update()
window,area,region = next((w,a,r) for w in bpy.context.window_manager.windows
    for a in w.screen.areas if a.type=='VIEW_3D' for r in a.regions if r.type=='WINDOW')
view=area.spaces.active.region_3d
report={'saved_orientation':bpy.context.scene.transform_orientation_slots[0].type,
        'view_rotation':list(view.view_rotation),'view_perspective':view.view_perspective,
        'view_axes_world':{axis:list(view.view_rotation@vec) for axis,vec in
            (('X',Vector((1,0,0))),('Y',Vector((0,1,0))),('Z',Vector((0,0,1))))}, 'tests':{}}
for name in ('breast.L','breast.R'):
    pb=rig.pose.bones[name]
    for other in rig.pose.bones: other.select=other==pb
    rig.data.bones.active=pb.bone
    pb.bone.hide=False
    location=pb.location.copy()
    before=d.state(pb)
    report['tests'][name]={'native_local_z_world':list((rig.matrix_world@pb.matrix).to_3x3().col[2].normalized())}
    for orient in ('GLOBAL','VIEW','LOCAL'):
        with bpy.context.temp_override(window=window,area=area,region=region):
            status=bpy.ops.transform.translate(value=(0,0,.01),orient_type=orient,
                constraint_axis=(False,False,True),use_proportional_edit=False)
        d.update()
        after=d.state(pb)
        report['tests'][name][orient]={'status':list(status),
            'head_delta':list(Vector(after['head_world'])-Vector(before['head_world'])),
            'shape_delta':list(Vector(after['shape']['center'])-Vector(before['shape']['center']))}
        pb.location=location
        d.update()
report['source_file_unchanged']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()==sha
(OUT/'breast_orientation_0531_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BREAST_ORIENTATION_DIAGNOSIS',json.dumps(report),flush=True)
assert report['source_file_unchanged']
