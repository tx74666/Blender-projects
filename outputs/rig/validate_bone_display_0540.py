"""Immutable-copy X verification for Body/Hair/Dress/Original display only.

Import capture_current/assert_unchanged around a live operation. Importing never
changes a scene, switches mode, registers the add-on, or saves a file.
"""
import bpy
import importlib
import importlib.util
import json
import shutil
import sys
import traceback
from pathlib import Path

ROOT = Path(r'D:\Blender\Projects\Character\X')
OUT = ROOT / 'outputs/rig'
SOURCE = ROOT / 'X.blend'
FIXTURE = OUT / 'X_bone_display_0540_input.blend'
PREVIEW = OUT / 'X_bone_display_0540_preview.blend'
NATIVE_PREVIEW = OUT / 'X_bone_display_0540_native_preview.blend'
REPORT = OUT / 'bone_display_0540_validation.json'
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
spec = importlib.util.spec_from_file_location('display_readonly_helpers', OUT / 'verify_root_height_0523_saved.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
plain, properties, rna_values, digest = helpers.plain, helpers.properties, helpers.rna_values, helpers.digest


def modules():
    return {name: importlib.import_module('character_designer.' + name) for name in
            ('bone_collections', 'bone_display', 'skirt_rig', 'limb_ik', 'limb_ik_fk',
             'root_control', 'head_neck_visuals', 'eye_controls', 'body_detail_visuals', 'control_colors')}


def update():
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get().update()


def capture_current(*, details=False):
    """Hash scene data, allowing only collection/display-view state to change.

    Selection and active UI context are not rig data. Every rest transform,
    pose basis, custom shape, constraint, action/driver, mesh and weight remains
    protected; evaluated pose matrices are compared numerically.
    """
    api = modules()
    groups, display = api['bone_collections'], api['bone_display']
    allowed = {groups.PROFILE_KEY, groups.AUTO_KEY, groups.BACKUP_KEY, groups.BACKUP_REFS_KEY,
               display.VIEW_KEY, display.REFS_KEY}
    update()
    values = {'objects': [], 'meshes': [], 'armature_settings': [], 'bones': [],
              'actions': helpers.animation_state()}
    poses, counts = {}, {'objects': len(bpy.data.objects), 'meshes': len(bpy.data.meshes), 'armatures': 0,
                        'bones': 0, 'mesh_vertices': 0}
    for obj in sorted(bpy.data.objects, key=lambda o:o.name):
        settings = rna_values(obj)
        if obj.type == 'ARMATURE':
            # Blender recomputes these bounds from visible bones/widgets. Scale,
            # matrices and all bone/widget coordinates remain protected below.
            settings.pop('dimensions', None)
        # Object visibility is protected; selection is merely interface state.
        values['objects'].append([obj.name, obj.type, plain(obj.data), settings, properties(obj),
            plain(obj.matrix_world), plain(obj.matrix_basis), obj.hide_get(),
            [rna_values(c) for c in obj.constraints], [rna_values(m) for m in obj.modifiers],
            [[g.name, g.lock_weight] for g in obj.vertex_groups]])
        if obj.type != 'ARMATURE':
            continue
        counts['armatures'] += 1
        data_settings = rna_values(obj.data)
        for key in ('show_bone_custom_shapes', 'display_type'):
            data_settings.pop(key, None)
        custom = {key:value for key,value in properties(obj.data).items() if key not in allowed}
        values['armature_settings'].append([obj.name, obj.data.name, data_settings, custom])
        for pb in sorted(obj.pose.bones, key=lambda p:p.name):
            counts['bones'] += 1
            key = obj.name + '/' + pb.name
            bone_settings, pose_settings = rna_values(pb.bone), rna_values(pb)
            for field in ('hide', 'hide_select', 'select', 'select_head', 'select_tail'):
                bone_settings.pop(field, None)
                pose_settings.pop(field, None)
            # Evaluated transforms use numeric tolerances, while original basis
            # transforms and every editable rotation/location channel stay exact.
            for field in ('matrix', 'matrix_channel', 'matrix_basis'):
                pose_settings.pop(field, None)
            values['bones'].append([key, api['root_control']._state(pb.bone), bone_settings,
                pose_settings, properties(pb.bone), properties(pb), plain(pb.matrix_basis),
                api['limb_ik']._pose_shape_json_state(pb), api['control_colors'].capture_bone(pb),
                [rna_values(c) for c in pb.constraints]])
            poses[key] = plain(pb.matrix)
    # Includes unlinked original artist widgets retained by recovery ID pointers.
    for mesh in sorted(bpy.data.meshes, key=lambda m:m.name):
        counts['mesh_vertices'] += len(mesh.vertices)
        keys = None if mesh.shape_keys is None else [
            [k.name, k.value, k.relative_key.name, [list(p.co) for p in k.data]] for k in mesh.shape_keys.key_blocks]
        values['meshes'].append([mesh.name, properties(mesh), rna_values(mesh),
            [list(v.co) for v in mesh.vertices], [list(e.vertices) for e in mesh.edges],
            [[list(p.vertices), p.material_index, p.use_smooth] for p in mesh.polygons],
            [[(g.group, g.weight) for g in v.groups] for v in mesh.vertices],
            [plain(m) for m in mesh.materials], keys])
    result = {'counts': counts, 'digests': {key:digest(value) for key,value in values.items()}, 'poses': poses}
    if details:
        result['details'] = values
    return result


def assert_unchanged(before, after):
    """Return the largest evaluated pose error; raise on any protected change."""
    assert before['counts'] == after['counts'], 'Object, mesh or bone counts changed.'
    bad = [key for key in before['digests'] if before['digests'][key] != after['digests'][key]]
    assert not bad, 'Protected scene data changed: ' + ', '.join(bad)
    assert before['poses'].keys() == after['poses'].keys(), 'Pose bone set changed.'
    error = max((abs(matrix[i][j]-after['poses'][name][i][j]) for name,matrix in before['poses'].items()
                 for i in range(4) for j in range(4)), default=0.)
    assert error < 3e-6, f'Evaluated pose changed by {error}.'
    return error


def validate_existing(rig):
    api = modules()
    api['limb_ik']._validate_inventory(rig)
    for name in ('root_control', 'head_neck_visuals', 'eye_controls', 'body_detail_visuals'):
        api[name].validate(rig)


def display_snapshot(rigs):
    display = modules()['bone_display']
    return {rig.name:display._snapshot(rig) for rig in rigs}


def activate(rig):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    update()


def main():
    assert bpy.app.background
    report = {'ok':False, 'production_file_written':False, 'preview':str(PREVIEW), 'fixture':str(FIXTURE)}
    # Capture a single immutable input. A user may keep saving their real file
    # while this independent background check runs; those saves are not ours.
    shutil.copy2(SOURCE, FIXTURE)
    protected = helpers.sha_file(FIXTURE)
    report['fixture_sha_before'] = protected
    try:
        cd.register()
        bpy.ops.wm.open_mainfile(filepath=str(FIXTURE), use_scripts=False)
        api = modules()
        groups, display, skirt = api['bone_collections'], api['bone_display'], api['skirt_rig']
        rig = bpy.data.objects['CoshaRig']
        activate(rig)
        validate_existing(rig)
        baseline = capture_current()
        dresses = display.dress_rigs(bpy.context, rig)
        affected = [rig] + [armature for armature,record in dresses]
        before_roots = list(rig.data.collections.keys())
        groups.simplify_body_collections(rig)
        for dress,record in dresses:
            skirt.migrate_skirt_bone_collections(dress)
        roots = list(rig.data.collections.keys())
        expected = ['Body'] + (['Hair'] if rig.data.collections_all.get('Hair') else []) + ['Original']
        assert roots == expected, (roots, expected)
        assert not {'Animation','Controls','Facial','All','Dress'} & set(roots)
        internal = rig.data.collections_all.get(groups.INTERNAL_NAME)
        assert internal and internal.parent == groups.body_collection(rig) and not internal.is_visible
        assert not groups.body_collection(rig).is_expanded
        report['organize_pose_error'] = assert_unchanged(baseline, capture_current())
        validate_existing(rig)
        display.show_controls(bpy.context, rig, 'ALL')
        report['controls_pose_error'] = assert_unchanged(baseline, capture_current())
        daily = display_snapshot(affected)
        originals = set(rig.data.collections_all['Original'].bones.keys())
        display.show_native(bpy.context, rig, 'ORIGINAL')
        assert not rig.data.show_bone_custom_shapes and rig.data.display_type == 'OCTAHEDRAL'
        assert {b.name for b in rig.data.bones if not b.hide} == originals
        assert display.view_mode(rig) == 'ORIGINAL'
        report['native_pose_error'] = assert_unchanged(baseline, capture_current())
        native_display = display_snapshot(affected)
        frame = bpy.context.scene.frame_current
        bpy.context.scene.frame_set(frame+1)
        assert display_snapshot(affected) == native_display, 'Frame change overwrote native view.'
        bpy.context.scene.frame_set(frame)
        report['frame_return_pose_error'] = assert_unchanged(baseline, capture_current())
        assert bpy.ops.wm.save_as_mainfile(filepath=str(NATIVE_PREVIEW), copy=True) == {'FINISHED'}
        names = [r.name for r in affected]
        bpy.ops.wm.open_mainfile(filepath=str(NATIVE_PREVIEW), use_scripts=False)
        rig = bpy.data.objects['CoshaRig']
        activate(rig)
        affected = [bpy.data.objects[name] for name in names]
        assert display.view_mode(rig) == 'ORIGINAL'
        assert display_snapshot(affected) == native_display
        assert display.restore_view(rig)
        assert display_snapshot(affected) == daily, 'Restored display differs from saved daily layout.'
        report['reopen_restore_pose_error'] = assert_unchanged(baseline, capture_current())
        display.show_controls(bpy.context, rig, 'BODY')
        assert display.view_mode(rig) is None and rig.data.show_bone_custom_shapes
        report['body_controls_pose_error'] = assert_unchanged(baseline, capture_current())
        hair_bones = set(rig.data.collections_all['Hair'].bones.keys()) if rig.data.collections_all.get('Hair') else set()
        report['hair_native_view_tested'] = False
        if any(rig.data.bones[name].use_deform for name in hair_bones):
            before_hair = display_snapshot(affected)
            display.show_native(bpy.context, rig, 'HAIR')
            assert_unchanged(baseline, capture_current())
            display.restore_view(rig)
            assert display_snapshot(affected) == before_hair
            report['hair_native_view_tested'] = True
        report['dress_native_view_tested'] = False
        if dresses:
            before_dress = display_snapshot(affected)
            display.show_native(bpy.context, rig, 'DRESS')
            assert_unchanged(baseline, capture_current())
            display.restore_view(rig)
            assert display_snapshot(affected) == before_dress
            report['dress_native_view_tested'] = True
        assert bpy.ops.wm.save_as_mainfile(filepath=str(PREVIEW), copy=True) == {'FINISHED'}
        bpy.ops.wm.open_mainfile(filepath=str(PREVIEW), use_scripts=False)
        rig = bpy.data.objects['CoshaRig']
        activate(rig)
        validate_existing(rig)
        report['final_reopen_pose_error'] = assert_unchanged(baseline, capture_current())
        report.update(ok=True, version=list(cd.bl_info['version']), counts=baseline['counts'],
                      roots_before=before_roots, roots_after=list(rig.data.collections.keys()),
                      original_bones=len(originals), hair_bones=len(hair_bones), dress_rigs=len(dresses),
                      only_bone_collection_and_display_state_changed=True, native_and_controller_views_verified=True)
    except Exception as exc:
        report.update(error=str(exc), traceback=traceback.format_exc())
    finally:
        report['fixture_sha_after'] = helpers.sha_file(FIXTURE)
        report['fixture_unchanged'] = report['fixture_sha_after'] == protected
        assert report['fixture_unchanged'], 'Immutable input copy was changed.'
        REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('BONE_DISPLAY_0540_VALIDATION',json.dumps(report),flush=True)
    assert report['ok'], report.get('error')


if __name__ == '__main__':
    main()
