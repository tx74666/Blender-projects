"""Generate only in an immutable saved-X copy; never remove or write production."""
import copy
import importlib.util
import json
import sys
import traceback
from pathlib import Path
import bpy
from bpy.props import PointerProperty

OUT = Path(__file__).parent
FIXTURE = OUT / 'fixtures/X_repaired_roll_20260912.blend'
PREVIEW = OUT / 'X_body_setup_repaired_0550_generated_preview.blend'
REPORT = OUT / 'body_setup_repaired_0550_validation.json'
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
from character_designer import (body_setup, body_setup_removal, limb_ik, control_colors,
    head_neck_visuals, body_detail_visuals, eye_controls, root_control, limb_fk_visuals)

spec = importlib.util.spec_from_file_location('body_setup_scene_checks', OUT/'validate_bone_display_0540.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
h = checks.helpers
DISPLAY_NAMES = {'Head', 'Neck', 'Hips', 'breast.L', 'breast.R'}
EYE_NAMES = {'eye.L', 'eye.R'}
DISPLAY_FIELDS = {'custom_shape', 'custom_shape_transform', 'custom_shape_translation',
    'custom_shape_rotation_euler', 'custom_shape_scale_xyz', 'use_custom_shape_bone_size',
    'custom_shape_wire_width', 'show_wire'}


def exact(a, b, label):
    if a == b:
        return
    differences = []
    def walk(x, y, path):
        if x == y or len(differences) >= 10:
            return
        if isinstance(x, dict) and isinstance(y, dict):
            for key in sorted(x.keys() | y.keys()):
                walk(x.get(key, '<MISSING>'), y.get(key, '<MISSING>'), path+'/'+str(key))
        elif isinstance(x, (list,tuple)) and isinstance(y, (list,tuple)) and len(x) == len(y):
            for i,(v,w) in enumerate(zip(x,y)):
                walk(v,w,path+'/'+str(i))
        else:
            differences.append([path, str(x)[:150], str(y)[:150]])
    walk(a,b,label)
    raise AssertionError(json.dumps(differences))


def numeric(a,b,label,tolerance=1e-5):
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        assert abs(a-b)<=tolerance,(label,a,b)
    elif isinstance(a,dict) and isinstance(b,dict):
        assert a.keys()==b.keys(),label
        for key in a:
            numeric(a[key],b[key],label+'/'+str(key),tolerance)
    elif isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)):
        assert len(a)==len(b),label
        for index,(x,y) in enumerate(zip(a,b)):
            numeric(x,y,label+'/'+str(index),tolerance)
    else:
        exact(a,b,label)


def capture_current():
    result = checks.capture_current(details=True)
    rig = bpy.data.objects['CoshaRig']
    result['skin'] = {name: h.plain(matrix) for name,matrix in body_setup._native_skin(rig).items()}
    result['key_data'] = h.digest([[key.name, h.properties(key), h.rna_values(key),
        [[block.name, h.rna_values(block), [list(v.co) for v in block.data]] for block in key.key_blocks]]
        for key in sorted(bpy.data.shape_keys, key=lambda item:item.name)])
    result['special_displays'] = {name: limb_ik._pose_shape_json_state(rig.pose.bones[name])
        for name in ('CTRL_hand_IK.L','CTRL_hand_IK.R','CTRL_master') if name in rig.pose.bones}
    result['manual_hands'] = {side: rig.data.bones['CTRL_hand_IK.'+side][limb_ik.AUTO_ALIGN_KEY] for side in 'LR'}
    result['ids'] = {kind: {item.name:item.as_pointer() for item in getattr(bpy.data,kind)}
                     for kind in ('objects','meshes','armatures','shape_keys','actions')}
    result['native_rest'] = {name: root_control._state(rig.data.bones[name]) for name in result['skin']}
    result['shader_data'] = h.digest([[material.name, h.properties(material), h.rna_values(material),
        None if material.node_tree is None else [
            h.properties(material.node_tree), h.rna_values(material.node_tree),
            [[node.name, h.properties(node), h.rna_values(node),
              [h.rna_values(socket) for socket in node.inputs], [h.rna_values(socket) for socket in node.outputs],
              [[element.position, list(element.color)] for element in node.color_ramp.elements] if hasattr(node,'color_ramp') else None]
             for node in material.node_tree.nodes],
            [[link.from_node.name, link.from_socket.identifier, link.to_node.name, link.to_socket.identifier]
             for link in material.node_tree.links]]]
        for material in sorted(bpy.data.materials,key=lambda item:item.name)])
    depsgraph = bpy.context.evaluated_depsgraph_get()
    result['evaluated_vertices'] = {}
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and not obj.get(limb_ik.OWNER_KEY):
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            try:
                result['evaluated_vertices'][obj.name] = [list(vertex.co) for vertex in mesh.vertices]
            finally:
                evaluated.to_mesh_clear()
    return result


def compare_generation(before, after, *, reopening=False):
    a,b = before['details'], after['details']
    for section in ('objects','meshes'):
        old,new = {row[0]:row for row in a[section]}, {row[0]:row for row in b[section]}
        assert not old.keys()-new.keys(), section+' removed original IDs'
        for name,row in old.items():
            other = new[name]
            if section == 'objects':
                row,other = copy.deepcopy(row),copy.deepcopy(other)
                row[3].pop('dimensions',None)
                other[3].pop('dimensions',None)
            exact(row,other,section+'/'+name)
    exact(a['actions']['actions'],b['actions']['actions'],'Actions and keyframes')
    old_assignments = {str(row[0]):row for row in a['actions']['assignments']}
    new_assignments = {str(row[0]):row for row in b['actions']['assignments']}
    for key, row in old_assignments.items():
        other = new_assignments[key]
        exact(row[:3],other[:3],'animation assignments/'+key)
        for driver in row[3]:
            identity = (driver['settings']['data_path'],driver['settings']['array_index'])
            candidates = [curve for curve in other[3]
                          if (curve['settings']['data_path'],curve['settings']['array_index']) == identity]
            assert len(candidates)==1, ('existing driver missing',key,identity)
            exact(driver,candidates[0],'existing driver/'+key+'/'+str(identity))
    exact(before['key_data'],after['key_data'],'full corrective/Key data')
    exact(before['shader_data'],after['shader_data'],'shader material and nodes')
    exact(before['native_rest'],after['native_rest'],'native Rest frames including edited fingers')
    for name, value in before['special_displays'].items():
        exact(value,after['special_displays'][name],'existing Manual display/'+name)
    exact(before['manual_hands'],after['manual_hands'],'Manual hand modes')
    allowed = {head_neck_visuals.RECORD_KEY,head_neck_visuals.REFERENCE_KEY,head_neck_visuals.ID_KEY,
               body_detail_visuals.RECORD_KEY,body_detail_visuals.REFERENCE_KEY,body_detail_visuals.ID_KEY,
               eye_controls.RECORD_KEY,root_control.RECORD_KEY,
               limb_fk_visuals.RECORD_KEY,limb_fk_visuals.ID_KEY}
    for row,other in zip(a['armature_settings'],b['armature_settings']):
        row,other = copy.deepcopy(row),copy.deepcopy(other)
        if row[0] == 'CoshaRig':
            for value in (row,other):
                for key in allowed:
                    value[3].pop(key,None)
        exact(row,other,'armature settings/'+row[0])
    old,new = {row[0]:row for row in a['bones']}, {row[0]:row for row in b['bones']}
    assert not old.keys()-new.keys(), 'Original bones removed'
    added = sorted(new.keys()-old.keys())
    expected_added = {'CoshaRig/'+name for name in eye_controls.get_record(bpy.data.objects['CoshaRig'])['bones'].values()}
    expected_added.add('CoshaRig/'+root_control.get_record(bpy.data.objects['CoshaRig'])['master'])
    assert set(added)==expected_added, added
    rig = bpy.data.objects['CoshaRig']
    display_names = DISPLAY_NAMES | set(limb_fk_visuals.get_record(rig)['bindings'])
    root = root_control.get_record(rig)
    inventory = limb_ik._validate_inventory(rig)
    wrist_offsets = {(pb.name,con.name) for data in inventory['rigs'].values()
                     for pb,con,entry in data['entries'] if entry['role']=='AUTO_OFFSET_ROTATION'
                     and data.get('auto_rotation_space')=='PARENT_DELTA'}
    new_constraints = {(entry['owner'],entry['name']) for entry in root['constraints']}
    new_constraints |= {(entry['owner'],entry['name']) for entry in eye_controls.get_record(rig)['constraints']}
    for full,row in old.items():
        row,other = copy.deepcopy(row),copy.deepcopy(new[full])
        name = full.removeprefix('CoshaRig/') if full.startswith('CoshaRig/') else None
        if name in display_names:
            for value in (row,other):
                for field in DISPLAY_FIELDS:
                    value[2].pop(field,None)
                    value[3].pop(field,None)
                value[5].pop(control_colors.BACKUP_KEY,None)
                value[7] = value[8] = None
        if name in root['controls']:
            assert row[1]['parent']=='' and other[1]['parent']==root['master']
            row[1]['parent'] = other[1]['parent']
        if name and rig.data.bones[name].get(limb_ik.OWNER_KEY) in limb_ik.GENERATED_CONTROL_OWNERS:
            numeric(row[1],other[1],'generated control Rest/'+name)
            row[1] = other[1]
        if name in {'MCH_hand_rotation.L','MCH_hand_rotation.R'}:
            numeric(row[6],other[6],'wrist reference basis/'+name)
            row[6] = other[6]
            for field in ('location','rotation_euler','rotation_quaternion','rotation_axis_angle','scale'):
                numeric(row[3][field],other[3][field],'wrist reference channel/'+name+'/'+field)
                row[3][field] = other[3][field]
        other[9] = [c for c in other[9] if (name,c['name']) not in new_constraints]
        # Root changes the reference space of managed wrist offsets while keeping
        # the evaluated hand and visible target unchanged. Its validator checks
        # the exact new fields; every unrelated constraint remains exact below.
        for old_constraint,new_constraint in zip(row[9],other[9]):
            if (name,old_constraint['name']) in wrist_offsets:
                assert new_constraint['space_subtarget']==root['master']
                assert new_constraint['space_object']==['Object',rig.name]
                assert new_constraint['owner_space']==new_constraint['target_space']=='CUSTOM'
                for field in ('space_object','space_subtarget','owner_space','target_space'):
                    old_constraint[field] = new_constraint.get(field)
        exact(row,other,'bone/'+full)
    pose_error = max(abs(matrix[i][j]-after['poses'][name][i][j])
        for name,matrix in before['poses'].items() for i in range(4) for j in range(4))
    skin_error = max(abs(matrix[i][j]-after['skin'][name][i][j])
        for name,matrix in before['skin'].items() for i in range(4) for j in range(4))
    assert pose_error < 1e-4 and skin_error < 1e-4, (pose_error,skin_error)
    surface_error = 0.
    for name, vertices in before['evaluated_vertices'].items():
        other = after['evaluated_vertices'][name]
        assert len(vertices)==len(other), ('evaluated vertex count',name)
        surface_error = max(surface_error,max((abs(a-b) for vertex,current in zip(vertices,other)
                                               for a,b in zip(vertex,current)),default=0.))
    assert surface_error < 1e-4, surface_error
    if not reopening:
        for kind,values in before['ids'].items():
            for name,pointer in values.items():
                assert after['ids'][kind].get(name)==pointer, ('original ID replaced',kind,name)
    return {'pose_error':pose_error,'skin_error':skin_error,'surface_error':surface_error,'added_bones':added,
            'added_objects':len(b['objects'])-len(a['objects']),'added_meshes':len(b['meshes'])-len(a['meshes'])}


def preflight(rig):
    result = {}
    for keep in (False,True):
        try:
            value = body_setup_removal.preflight(bpy.context,rig,keep_native_rest=keep)
            result[str(keep)] = {'ok':True,'fields':sorted(value),
                'bones':len(value.get('names',())),'rest_states':len(value.get('rest',{}))}
        except Exception as exc:
            result[str(keep)] = {'ok':False,'error':str(exc)}
    return result


def main():
    assert bpy.app.background
    digest = h.sha_file(FIXTURE)
    report = {'ok':False,'source':str(FIXTURE),'source_sha256':digest,'preview':str(PREVIEW),
              'production_file_written':False,'removal_executed':False}
    try:
        # Only the required transient settings are registered. Keep all saved corrective Key
        # coordinates frozen while checking the generator's explicit transaction.
        bpy.utils.register_class(limb_ik.CharacterDesignerLimbIKState)
        bpy.types.WindowManager.character_designer_limb_ik = PointerProperty(type=limb_ik.CharacterDesignerLimbIKState)
        bpy.ops.wm.open_mainfile(filepath=str(FIXTURE),use_scripts=False)
        rig = bpy.data.objects['CoshaRig']
        checks.activate(rig)
        before = capture_current()
        report['initial_plan'] = body_setup.plan(bpy.context,rig)
        report['initial_preflight'] = preflight(rig)
        report['generate'] = body_setup.generate(bpy.context,rig)
        assert set(report['generate']['created']) == {'ROOT','FK_RINGS','EYES','HEAD_NECK','BODY_DETAIL'}
        after = capture_current()
        report['preservation'] = compare_generation(before,after)
        report['second_generate'] = body_setup.generate(bpy.context,rig)
        assert report['second_generate']['created'] == []
        again = capture_current()
        exact(after['digests'],again['digests'],'second Generate state')
        exact(after['key_data'],again['key_data'],'second Generate Key data')
        exact(after['shader_data'],again['shader_data'],'second Generate shaders')
        exact(after['ids'],again['ids'],'second Generate IDs')
        report['generated_preflight'] = preflight(rig)
        preflight_after = capture_current()
        exact(again['digests'],preflight_after['digests'],'preflight data mutation')
        exact(again['key_data'],preflight_after['key_data'],'preflight Key mutation')
        assert bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW),copy=True) == {'FINISHED'}
        bpy.ops.wm.open_mainfile(filepath=str(PREVIEW),use_scripts=False)
        rig = bpy.data.objects['CoshaRig']
        checks.activate(rig)
        report['reopen_plan'] = body_setup.plan(bpy.context,rig)
        assert not report['reopen_plan']['blocked']
        assert all(c['status']=='REUSE' for c in report['reopen_plan']['components'])
        report['reopen_preservation'] = compare_generation(before,capture_current(),reopening=True)
        report['ok'] = True
    except Exception as exc:
        report.update(error=str(exc),traceback=traceback.format_exc())
    report['source_unchanged'] = h.sha_file(FIXTURE)==digest
    REPORT.write_text(json.dumps(report,indent=2),encoding='utf8')
    print('BODY_SETUP_REPAIRED_0550',json.dumps(report),flush=True)
    assert report['ok'] and report['source_unchanged'], report.get('error')


if __name__ == '__main__':
    main()
