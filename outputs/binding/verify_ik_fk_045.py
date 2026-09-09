"""Disposable, headless integration of canonical CDesigner with saved X.

Run with --factory-startup X.blend --python this_file. Never save X.
"""
import hashlib
import json
import math
import struct
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Euler, Vector

ROOT = Path(r"D:\MyRepository\Blender-addons-by-Randy")
OUT = Path(__file__).with_suffix('.json')
sys.path.insert(0, str(ROOT / 'addons'))
import character_designer
from character_designer import bone_collections as groups
from character_designer import character_setup, forearm_twist, limb_ik, limb_ik_fk as switching

REPORT = {'file': bpy.data.filepath, 'addon': character_designer.bl_info['version'],
          'production_file_saved': False, 'steps': []}


def update(rig):
    rig.update_tag(refresh={'OBJECT'})
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get().update()


def profile():
    state = bpy.context.scene.character_designer_setup
    return {'rig': state.rig.name if state.rig else None,
            'body': state.body.name if state.body else None,
            'assets': [(a.object.name if a.object else None, a.role) for a in state.assets],
            'hips': character_setup.bone_mapping_status(bpy.context, 'HIPS')['name'],
            'head': character_setup.bone_mapping_status(bpy.context, 'HEAD')['name']}


def payload_signature():
    """Authored mesh data, groups, custom records, modifier setup, and profile."""
    signatures = {}
    for obj in sorted((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: o.name):
        if obj.get(limb_ik.OWNER_KEY) == limb_ik.OWNER_VALUE:
            continue
        digest = hashlib.sha256()
        digest.update(obj.name.encode())
        for vertex in obj.data.vertices:
            digest.update(struct.pack('<3f', *vertex.co))
            for assignment in vertex.groups:
                digest.update(struct.pack('<If', assignment.group, assignment.weight))
        for polygon in obj.data.polygons:
            digest.update(bytes(str(tuple(polygon.vertices)), 'ascii'))
        for layer in obj.data.uv_layers:
            digest.update(layer.name.encode())
            for item in layer.data:
                digest.update(struct.pack('<2f', *item.uv))
        keys = obj.data.shape_keys
        runtime_keys = {record['key'] for record in forearm_twist._records(obj).values()}
        if keys:
            for block in keys.key_blocks:
                digest.update(block.name.encode())
                # Shape-key values can be driven by the requested test pose;
                # the authored key coordinates must remain bit-identical.
                # Existing forearm correction writes its owned key coordinates
                # on each pose update. Calibration records remain checked below,
                # and evaluated correction is covered by surface comparisons.
                if block.name not in runtime_keys:
                    for vertex in block.data:
                        digest.update(struct.pack('<3f', *vertex.co))
        metadata = {
            'groups': [(g.name, g.lock_weight) for g in obj.vertex_groups],
            'parent': obj.parent.name if obj.parent else None,
            'parent_type': obj.parent_type, 'parent_bone': obj.parent_bone,
            'basis': [list(row) for row in obj.matrix_basis],
            'parent_inverse': [list(row) for row in obj.matrix_parent_inverse],
            'modifiers': [(m.name, m.type, getattr(getattr(m, 'object', None), 'name', None),
                           m.show_viewport, m.show_render) for m in obj.modifiers],
            'properties': {key: str(obj[key]) for key in sorted(obj.keys())},
        }
        signatures[obj.name] = {'geometry': digest.hexdigest(), 'metadata': metadata}
    signatures['__profile__'] = profile()
    return signatures


def poses(rig, names):
    update(rig)
    evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return {name: evaluated.pose.bones[name].matrix.copy() for name in names}


def pose_errors(rig, expected):
    current = poses(rig, expected)
    worst = {'position': (0.0, ''), 'rotation': (0.0, ''), 'scale': (0.0, '')}
    for name, before in expected.items():
        now = current[name]
        errors = {'position': (now.translation - before.translation).length,
                  'rotation': limb_ik._rotation_error(now, before),
                  'scale': (now.to_scale() - before.to_scale()).length}
        for kind, value in errors.items():
            if value > worst[kind][0]:
                worst[kind] = (value, name)
    assert worst['position'][0] <= 3e-4, worst
    assert worst['rotation'][0] <= 3e-3, worst
    assert worst['scale'][0] <= 3e-4, worst
    return worst


def surfaces():
    result = {}
    graph = bpy.context.evaluated_depsgraph_get()
    for name in ('Cosha', 'Clothes', 'Stocking', 'Shoes'):
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            count = len(mesh.vertices)
            indices = sorted({min(count - 1, (count - 1) * i // 512) for i in range(513)}) if count else []
            result[name] = (count, [(i, evaluated.matrix_world @ mesh.vertices[i].co) for i in indices])
        finally:
            evaluated.to_mesh_clear()
    return result


def surface_errors(expected):
    current = surfaces()
    worst = {}
    for name, (count, points) in expected.items():
        assert count == current[name][0], name
        values = [(a - b).length for (ia, a), (ib, b) in zip(points, current[name][1]) if ia == ib]
        assert len(values) == len(points)
        worst[name] = max(values, default=0.0)
        assert worst[name] <= 4e-4, worst
    return worst


def roundtrip(rig, names, keys, label):
    baseline = poses(rig, names)
    skin = surfaces()
    item = {'label': label, 'switches': []}
    REPORT['steps'].append(item)
    for mode in ('FK', 'IK'):
        for key in keys:
            result = switching.switch_limb(bpy.context, rig, key, mode, keyframe=False)
            item['switches'].append({'limb': key, 'mode': mode, 'result': result,
                                     'all_native_pose_errors': pose_errors(rig, baseline)})
        item[mode + '_surface_errors'] = surface_errors(skin)
        previous = groups.snapshot_layout(rig)
        groups.finish_rig_edit(rig, previous)
        collection = rig.data.collections_all['Animation']
        if mode == 'FK':
            assert set(names).issubset(set(collection.bones.keys()))
        else:
            replaced = {n for r in limb_ik._validate_inventory(rig)['rigs'].values() for n in r['chain']}
            assert not replaced.intersection(collection.bones.keys())


def main():
    assert Path(bpy.data.filepath).resolve() == Path(r'D:\Blender\Projects\Character\X\X.blend').resolve()
    character_designer.register()
    rig = bpy.data.objects['CoshaRig']
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    update(rig)
    inventory = limb_ik._validate_inventory(rig)
    keys = sorted(inventory['rigs'])
    native = sorted(b.name for b in rig.data.bones if b not in inventory['bones'])
    REPORT.update(schema=inventory['schema'], built_limbs=keys, native_count=len(native),
                  generated_count=len(inventory['bones']), original_profile=profile(),
                  action=rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None)
    assert keys, 'Saved X has no generated limbs to test'
    original_payload = payload_signature()
    original_layout = groups.snapshot_layout(rig)
    original_pose = poses(rig, native)
    skin = surfaces()
    switching.ensure_switching(rig, inventory)
    update(rig)
    switching.ensure_switching(rig)
    REPORT['upgrade_pose_errors'] = pose_errors(rig, original_pose)
    REPORT['upgrade_surface_errors'] = surface_errors(skin)
    groups.simplify_body_collections(rig)
    assert not rig.data.collections_all['Original'].is_visible
    assert rig.data.collections_all['Animation'].is_visible
    REPORT['collection_pose_errors'] = pose_errors(rig, original_pose)
    roundtrip(rig, native, keys, 'Saved X pose')

    # Exercise each current IK control using a small translated/rotated pose.
    inventory = limb_ik._validate_inventory(rig)
    for index, key in enumerate(keys):
        target = rig.pose.bones[inventory['rigs'][key]['target'].name]
        matrix = target.matrix.copy()
        matrix.translation += Vector((0.006 if key[1] == 'L' else -0.006, 0.010, 0.008))
        target.matrix = matrix
        update(rig)
    roundtrip(rig, native, keys, 'Small translated current IK controls')
    final_payload = payload_signature()
    assert final_payload == original_payload, ('Authored mesh/weights/profile/attachment state changed',
        [name for name in set(original_payload) | set(final_payload)
         if original_payload.get(name) != final_payload.get(name)])
    REPORT['authored_mesh_weights_profile_attachments_unchanged'] = True
    REPORT['runtime_forearm_corrective_coordinates_excluded_from_static_digest'] = True

    restore = groups.restore_bone_collections(rig)
    restored = groups.snapshot_layout(rig)
    assert restored['collections'] == original_layout['collections'], 'Original collections not restored exactly'
    assert restored['hidden'] == original_layout['hidden'], 'Bone hide flags changed'
    REPORT['restored_collections'] = restore
    assert not groups.has_layout_backup(rig)

    # Removal operates only on this background process; compare native identities
    # and foreign records, and require no dangling switch drivers afterward.
    groups.simplify_body_collections(rig)
    result = bpy.ops.character_designer.limb_ik_remove()
    assert result == {'FINISHED'}, result
    assert sorted(rig.data.bones.keys()) == native
    assert not limb_ik._validate_inventory(rig)['bones']
    animation = rig.animation_data
    assert not animation or not any('ik_fk' in c.driver.expression or 'CTRL_' in c.data_path for c in animation.drivers)
    removed_payload = payload_signature()
    migrated = []
    for name, before in original_payload.items():
        if name == '__profile__' or name not in removed_payload:
            continue
        old_props = before['metadata']['properties']
        new_props = removed_payload[name]['metadata']['properties']
        if old_props.get(forearm_twist.RECORD_KEY) == new_props.get(forearm_twist.RECORD_KEY):
            continue
        old_records = json.loads(old_props[forearm_twist.RECORD_KEY])
        new_records = json.loads(new_props[forearm_twist.RECORD_KEY])
        assert old_records.keys() == new_records.keys()
        for side in old_records:
            old_record, new_record = old_records[side], new_records[side]
            assert new_record['target'] == new_record['chain'][-1]
            assert new_record['rest'] == forearm_twist._rest_signature(rig, new_record['chain'])
            for record in (old_record, new_record):
                for field in ('target', 'rest', 'positions'):
                    record.pop(field, None)
                for ring in record['rings']:
                    ring.pop('position', None)
            assert old_record == new_record, 'Forearm authored loop membership/ratios changed'
        # Existing Forearm Twist explicitly migrates its computed rest frame and
        # target from removed IK controls to original hands. Profile is preserved.
        new_props[forearm_twist.RECORD_KEY] = old_props[forearm_twist.RECORD_KEY]
        migrated.append(name)
    REPORT['remove_forearm_migration_preserved_artist_loop_profiles'] = migrated
    differences = {}
    for name in set(removed_payload) | set(original_payload):
        if original_payload.get(name) != removed_payload.get(name):
            before, after = original_payload.get(name), removed_payload.get(name)
            differences[name] = {'before': before, 'after': after}
    REPORT['remove_payload_differences'] = differences
    assert not differences, ('Remove changed character meshes/weights/profile/attachment state', list(differences))
    REPORT['remove_restored_native_rig_without_dangling_drivers'] = True
    REPORT['ok'] = True


try:
    main()
except Exception as exc:
    REPORT['ok'] = False
    REPORT['error'] = str(exc)
    REPORT['traceback'] = traceback.format_exc()
    raise
finally:
    OUT.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    print('X_IK_FK_045_RESULT', json.dumps({key: REPORT[key] for key in ('ok', 'error') if key in REPORT}), str(OUT))
