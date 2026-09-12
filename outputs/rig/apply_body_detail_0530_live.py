"""Install tested local body displays into the current X scene, with a full backup."""
import bpy, hashlib, importlib, json, math
from datetime import datetime
from pathlib import Path
from mathutils import Matrix, Quaternion

ROOT = Path(r'D:\Blender\Projects\Character\X')
OUT = ROOT / 'outputs/rig'
assert not bpy.app.background, 'Run this against the current Blender scene.'
assert Path(bpy.data.filepath).resolve() == (ROOT / 'X.blend').resolve()
assert bpy.context.mode in {'OBJECT', 'POSE'}, 'Finish the current modeling operation first.'
rig = bpy.data.objects['CoshaRig']
targets = {'Hips', 'breast.L', 'breast.R'}
assert all(name in rig.pose.bones for name in targets)
assert all(rig.pose.bones[name].custom_shape is None for name in targets), 'Preserve existing edited displays.'

backup = OUT / 'backups' / ('X_before_body_detail_0530_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.blend')
backup.parent.mkdir(parents=True, exist_ok=True)
assert bpy.ops.wm.save_as_mainfile(filepath=str(backup), copy=True) == {'FINISHED'}
import character_designer as cd
if tuple(cd.bl_info['version']) != (0, 53, 0):
    cd._reload_addon_deferred()
    cd = importlib.import_module('character_designer')
assert tuple(cd.bl_info['version']) == (0, 53, 0), 'The tested add-on did not reload.'
from character_designer import body_detail_visuals as service, limb_ik, limb_ik_fk, root_control, head_neck_visuals, eye_controls, control_colors

if bpy.context.object and bpy.context.object.mode == 'POSE' and bpy.context.object != rig:
    bpy.ops.object.mode_set(mode='OBJECT')
for obj in bpy.context.selected_objects:
    obj.select_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
limb_ik_fk._update(bpy.context, rig)
original_objects = set(bpy.data.objects.keys())
original_meshes = set(bpy.data.meshes.keys())

def preserved_state():
    result = {'objects': [], 'meshes': [], 'bones': [], 'collections': [], 'actions': []}
    for name in sorted(original_objects):
        obj = bpy.data.objects[name]
        result['objects'].append([name, obj.type, [list(row) for row in obj.matrix_world]])
    for name in sorted(original_meshes):
        mesh = bpy.data.meshes[name]
        result['meshes'].append([name, [list(v.co) for v in mesh.vertices],
            [list(p.vertices) for p in mesh.polygons],
            [[(g.group, g.weight) for g in v.groups] for v in mesh.vertices]])
    for pb in rig.pose.bones:
        shape = limb_ik._pose_shape_json_state(pb)
        if pb.name == 'CTRL_master':
            shape = dict(shape)
            shape.pop('translation')
        color = control_colors.capture_bone(pb)
        result['bones'].append([pb.name, root_control._state(pb.bone),
            [list(row) for row in pb.matrix_basis],
            [(c.name, c.type) for c in pb.constraints],
            None if pb.name in targets else shape, None if pb.name in targets else color])
    result['collections'] = [[c.name, sorted(c.bones.keys()), c.is_visible] for c in rig.data.collections_all]
    for action in bpy.data.actions:
        curves = []
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves += [[fc.data_path, fc.array_index,
                        [(list(p.co), p.interpolation) for p in fc.keyframe_points]] for fc in bag.fcurves]
        result['actions'].append([action.name, curves])
    return hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()

before_digest = preserved_state()
before_pose = {pb.name: pb.matrix.copy() for pb in rig.pose.bones}
master = rig.pose.bones['CTRL_master']
root_before = list(master.custom_shape_translation)
root_desired = list(limb_ik._master_widget_translation(rig))
assert max(abs(a-b) for a,b in zip(root_before, root_desired)) < 1e-6 or max(map(abs, root_before)) < 1e-6, 'Root display has a manual offset; keep it for review.'

assert bpy.ops.character_designer.body_detail_visuals(action='BUILD', hips_name='Hips',
    left_name='breast.L', right_name='breast.R') == {'FINISHED'}
record = service.validate(rig)
assert set(record['bindings']) == targets
master.custom_shape_translation = root_desired
limb_ik_fk._update(bpy.context, rig)
root_control.validate(rig)
limb_ik._validate_inventory(rig)
head_neck_visuals.validate(rig)
eye_controls.validate(rig)
error = max(abs(rig.pose.bones[name].matrix[i][j]-matrix[i][j])
    for name,matrix in before_pose.items() for i in range(4) for j in range(4))
assert error < 2e-6, error
assert preserved_state() == before_digest, 'Unrelated scene data changed.'
assert all(pb.custom_shape for pb in rig.pose.bones
    if not pb.bone.hide and not pb.bone.get('character_designer_owner')
    and any(c.name == 'Animation' for c in pb.bone.collections))
report = {'ok': True, 'version': list(cd.bl_info['version']), 'backup': str(backup),
    'record_id': record['id'], 'controls': {name:rig.pose.bones[name].custom_shape.name for name in targets},
    'pose_error':error, 'unrelated_geometry_weights_animation_displays_preserved':True,
    'root_before':root_before, 'root_after':list(master.custom_shape_translation),
    'root_pivot_preserved':True, 'main_file_saved':False,
    'original_objects':sorted(original_objects), 'original_meshes':sorted(original_meshes),
    'preserved_digest':before_digest}
result_path = OUT / 'body_detail_0530_live_result.json'
result_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

# Return to a useful character view before saving; leave the fitted Hips selected.
area = bpy.context.area
if area and area.type == 'CONSOLE':
    area.type = 'VIEW_3D'
    view = area.spaces.active.region_3d
    view.view_rotation = Quaternion((math.sqrt(.5), math.sqrt(.5), 0, 0))
    view.view_perspective = 'ORTHO'
    view.view_location = rig.matrix_world @ ((rig.pose.bones['Head'].head + rig.pose.bones['Hips'].head) * .5)
    view.view_distance = 1.65
for window in bpy.context.window_manager.windows:
    for item in window.screen.areas:
        item.tag_redraw()
assert bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'X.blend')) == {'FINISHED'}
report['main_file_saved'] = True
result_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('BODY_DETAIL_0530_LIVE', json.dumps({k:v for k,v in report.items()
    if k not in {'original_objects','original_meshes'}}), flush=True)
