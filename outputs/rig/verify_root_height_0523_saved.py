"""Read-only verification of saved X against the live pre-root-height backup.

Run with Blender --background --factory-startup --python-exit-code 1 --python
this_file.py.  Scene files are opened with scripts disabled and never saved.
Only outputs/rig/root_height_0523_saved_verification.json is written.
"""
import bpy
import hashlib
import json
import math
import sys
import traceback
from pathlib import Path
from mathutils import Matrix

ROOT = Path(r'D:\Blender\Projects\Character\X')
OUT = ROOT / 'outputs/rig'
DESTINATION = OUT / 'root_height_0523_saved_verification.json'
sys.path.insert(0, r'D:\MyRepository\Blender-addons-by-Randy\addons')
import character_designer as cd
from character_designer import (
    root_control, head_neck_visuals, eye_controls, limb_ik, limb_ik_fk,
)


def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def plain(value):
    if isinstance(value, (str, bool, int, float)) or value is None:
        return value
    if isinstance(value, bpy.types.ID):
        return [value.bl_rna.identifier, value.name_full]
    if hasattr(value, 'to_dict'):
        return {key: plain(item) for key, item in value.to_dict().items()}
    if hasattr(value, 'keys'):
        return {key: plain(value[key]) for key in value.keys()}
    return [plain(item) for item in value]


def properties(item):
    return {key: plain(item[key]) for key in sorted(item.keys())}


def rna_values(item):
    """Stable scalar, array and ID-pointer settings for constraints/modifiers."""
    result = {}
    for prop in item.bl_rna.properties:
        if prop.identifier == 'rna_type' or prop.is_readonly:
            continue
        if prop.type in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}:
            result[prop.identifier] = plain(getattr(item, prop.identifier))
        elif prop.type == 'POINTER':
            value = getattr(item, prop.identifier)
            if value is None or isinstance(value, bpy.types.ID):
                result[prop.identifier] = plain(value)
    return result


def curve_state(curve):
    result = {'settings': rna_values(curve), 'keys': [], 'samples': [],
              'modifiers': [rna_values(mod) for mod in curve.modifiers]}
    result['keys'] = [rna_values(point) for point in curve.keyframe_points]
    result['samples'] = [list(point.co) for point in curve.sampled_points]
    if curve.driver:
        result['driver'] = rna_values(curve.driver)
        result['variables'] = [[rna_values(var), [rna_values(t) for t in var.targets]]
                               for var in curve.driver.variables]
    return result


def animation_state():
    actions = []
    for action in sorted(bpy.data.actions, key=lambda item: item.name):
        layers = []
        for layer in action.layers:
            strips = []
            for strip in layer.strips:
                bags = [[bag.slot_handle, [curve_state(c) for c in bag.fcurves]]
                        for bag in strip.channelbags]
                strips.append([rna_values(strip), bags])
            layers.append([rna_values(layer), strips])
        actions.append([action.name, properties(action),
                        [rna_values(slot) for slot in action.slots], layers])
    assignments = []
    for collection in (bpy.data.objects, bpy.data.armatures, bpy.data.meshes,
                       bpy.data.shape_keys, bpy.data.scenes):
        for block in sorted(collection, key=lambda item: item.name):
            animation = block.animation_data
            if animation is None:
                continue
            tracks = [[rna_values(track), [rna_values(strip) for strip in track.strips]]
                      for track in animation.nla_tracks]
            assignments.append([plain(block), rna_values(animation), tracks,
                                [curve_state(curve) for curve in animation.drivers]])
    return {'actions': actions, 'assignments': assignments}


def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    rig = bpy.data.objects['CoshaRig']
    limb_ik_fk._update(bpy.context, rig)
    record = root_control.validate(rig)
    assert record, 'Root Control record missing.'
    head_neck_visuals.validate(rig)
    eye_controls.validate(rig)
    limb_ik._validate_inventory(rig)
    master = rig.pose.bones[record['master']]
    translation = list(master.custom_shape_translation)
    desired = list(limb_ik._master_widget_translation(rig))
    values = {'objects': [], 'meshes': [], 'bones': [], 'collections': [],
              'records': properties(rig.data), 'animations': animation_state()}
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        values['objects'].append([
            obj.name, obj.type, plain(obj.data), plain(obj.matrix_world),
            plain(obj.matrix_basis), properties(obj),
            [rna_values(con) for con in obj.constraints],
            [rna_values(mod) for mod in obj.modifiers],
        ])
        if obj.type == 'MESH':
            mesh = obj.data
            shape_keys = (None if mesh.shape_keys is None else [
                [key.name, key.value, key.relative_key.name,
                 [list(point.co) for point in key.data]]
                for key in mesh.shape_keys.key_blocks])
            values['meshes'].append([
                obj.name, mesh.name, [list(v.co) for v in mesh.vertices],
                [list(e.vertices) for e in mesh.edges],
                [list(p.vertices) for p in mesh.polygons],
                [group.name for group in obj.vertex_groups],
                [[(g.group, g.weight) for g in v.groups] for v in mesh.vertices],
                shape_keys,
            ])
        if obj.type == 'ARMATURE':
            for pb in sorted(obj.pose.bones, key=lambda item: item.name):
                visual = limb_ik._pose_shape_json_state(pb)
                if obj == rig and pb == master:
                    visual = dict(visual)
                    visual.pop('translation')
                values['bones'].append([
                    obj.name, pb.name, root_control._state(pb.bone),
                    properties(pb.bone), properties(pb), visual,
                    plain(pb.matrix_basis), pb.rotation_mode,
                    plain(pb.lock_location), plain(pb.lock_rotation),
                    plain(pb.lock_scale), [rna_values(con) for con in pb.constraints],
                    pb.color.palette, list(pb.color.custom.normal),
                    list(pb.color.custom.select), list(pb.color.custom.active),
                ])
            values['collections'].append([obj.name, [
                [c.name, sorted(c.bones.keys()), c.is_visible]
                for c in obj.data.collections_all]])
    poses = {obj.name + '/' + pb.name: plain(pb.matrix)
             for obj in bpy.data.objects if obj.type == 'ARMATURE'
             for pb in obj.pose.bones}
    return {'translation': translation, 'desired': desired, 'poses': poses,
            'digests': {key: digest(value) for key, value in values.items()},
            'master': master.name, 'validated': ['root', 'head', 'eye', 'limb_inventory']}


def main():
    assert bpy.app.background, 'This verification must run headlessly.'
    report = {'ok': False, 'read_only': True, 'main_file_saved': False}
    protected = {}
    try:
        live = json.loads((OUT / 'root_height_0523_live_result.json').read_text(encoding='utf-8'))
        assert live.get('ok') and live.get('live') and live.get('backup'), 'Live backup report is not ready.'
        backup = Path(live['backup']).resolve()
        target = (ROOT / 'X.blend').resolve()
        assert backup.is_file() and target.is_file() and backup != target
        protected = {path: sha_file(path) for path in (backup, target)}
        report.update(backup=str(backup), target=str(target), version=list(cd.bl_info['version']))
        cd.register()
        before, after = snapshot(backup), snapshot(target)
        changed = [key for key in before['digests'] if before['digests'][key] != after['digests'][key]]
        report.update(before_translation=before['translation'], translation=after['translation'],
                      desired_translation=after['desired'], changed_categories=changed,
                      before_digests=before['digests'], after_digests=after['digests'])
        assert not changed, 'Unexpected data changes: ' + ', '.join(changed)
        assert before['poses'].keys() == after['poses'].keys(), 'Pose bone set changed.'
        error = max(abs(after['poses'][name][i][j] - matrix[i][j])
                    for name, matrix in before['poses'].items() for i in range(4) for j in range(4))
        report['pose_error'] = error
        assert error < 2e-6, 'Evaluated pose changed.'
        assert before['translation'] != after['translation'], 'The root height change was not saved.'
        assert max(abs(a - b) for a, b in zip(after['translation'], after['desired'])) < 1e-6
        assert max(abs(a - b) for a, b in zip(after['translation'], live['translation'])) < 1e-6
        assert all(math.isfinite(value) for value in after['translation'])
        report.update(ok=True, reopened_verified=True, only_root_translation_changed=True,
                      geometry_weights_rest_pose_other_shapes_actions_unchanged=True,
                      validation=after['validated'])
    except Exception as exc:
        report.update(ok=False, error=str(exc), traceback=traceback.format_exc())
    finally:
        hashes = {str(path): {'before': original, 'after': sha_file(path)}
                  for path, original in protected.items()}
        report['file_hashes'] = hashes
        report['input_files_unchanged'] = all(value['before'] == value['after'] for value in hashes.values())
        if not report['input_files_unchanged']:
            report.update(ok=False, error='An input .blend changed during verification.')
        DESTINATION.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('ROOT_HEIGHT_0523_SAVED_VERIFICATION', json.dumps(report), flush=True)
    assert report['ok'], report.get('error', 'Verification failed.')


if __name__ == '__main__':
    main()
