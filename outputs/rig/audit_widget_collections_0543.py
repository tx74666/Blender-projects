"""Read-only audit of a uniquely copied current X file; never saves Blender data."""
import bpy
import collections
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).parent
PRODUCTION = OUT.parents[1] / 'X.blend'


def label(item):
    return item.bl_rna.identifier + ':' + item.name_full


def main():
    source = Path(bpy.data.filepath)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    production_hash = hashlib.sha256(PRODUCTION.read_bytes()).hexdigest()
    users = bpy.data.user_map()
    ids = set(users)
    for entries in users.values():
        ids.update(entries)
    ids.update(s.collection for s in bpy.data.scenes)
    by_name = collections.defaultdict(list)
    for item in ids:
        by_name[item.name_full].append(item)
    id_refs = collections.defaultdict(list)
    string_refs = collections.defaultdict(list)
    json_records = []

    def walk(value, path, depth=0):
        if depth > 25:
            return
        if isinstance(value, bpy.types.ID):
            id_refs[value].append(path)
        elif isinstance(value, str):
            for match in by_name.get(value, ()):
                string_refs[match].append(path)
            if value[:1] in ('{', '['):
                try:
                    decoded = json.loads(value)
                except (ValueError, TypeError):
                    return
                if isinstance(decoded, (dict, list)):
                    json_records.append(path)
                    walk(decoded, path + '<json>', depth + 1)
        elif hasattr(value, 'items'):
            for key, sub in value.items():
                walk(sub, path + '[' + repr(key) + ']', depth + 1)
        elif isinstance(value, (tuple, list)) or type(value).__name__ == 'IDPropertyArray':
            for index, sub in enumerate(value):
                walk(sub, path + '[' + str(index) + ']', depth + 1)

    def props(item, path):
        try:
            for key, value in item.items():
                walk(value, path + '[' + repr(key) + ']')
        except (AttributeError, TypeError):
            pass

    pose_users = collections.defaultdict(list)
    for item in ids:
        props(item, label(item))
    for arm in bpy.data.armatures:
        for bone in arm.bones:
            props(bone, label(arm) + '.bones[' + repr(bone.name) + ']')
        for group in arm.collections_all:
            props(group, label(arm) + '.collections_all[' + repr(group.name) + ']')
    for obj in bpy.data.objects:
        for modifier in obj.modifiers:
            props(modifier, label(obj) + '.modifiers[' + repr(modifier.name) + ']')
        for constraint in obj.constraints:
            props(constraint, label(obj) + '.constraints[' + repr(constraint.name) + ']')
        if obj.pose is None:
            continue
        for pb in obj.pose.bones:
            path = label(obj) + '.pose.bones[' + repr(pb.name) + ']'
            props(pb, path)
            for constraint in pb.constraints:
                props(constraint, path + '.constraints[' + repr(constraint.name) + ']')
            if pb.custom_shape:
                pose_users[pb.custom_shape].append({'rig': obj.name, 'bone': pb.name,
                    'bone_hide': pb.bone.hide, 'pose_hide': getattr(pb, 'hide', None),
                    'show_custom_shapes': obj.data.show_bone_custom_shapes,
                    'collections': [c.name for c in pb.bone.collections]})

    def references(item):
        return {'users': item.users,
                'user_map': sorted(label(x) for x in users.get(item, ())),
                'idproperty_refs': sorted(set(id_refs[item])),
                'record_or_string_refs': sorted(set(string_refs[item])),
                'fake_user': item.use_fake_user, 'library': item.library.filepath if item.library else None}

    def tags(item):
        return {k: v for k, v in item.items() if isinstance(v, (str, int, float, bool))}

    roots = {c for scene in bpy.data.scenes for c in scene.collection.children}
    candidates = []
    for collection in bpy.data.collections:
        name_match = any(x in collection.name.lower() for x in ('widget', 'wgt', 'shape'))
        tagged = any('widget' in str(v).lower() for v in collection.values())
        objects_match = any(obj in pose_users or obj.name.startswith(('WGT', 'Wgt', 'wgt'))
                            for obj in collection.objects)
        if not (name_match or tagged or objects_match):
            continue
        parents = [c.name for c in bpy.data.collections if collection in tuple(c.children)]
        scene_roots = [s.name for s in bpy.data.scenes if collection in tuple(s.collection.children)]
        scenes = [s.name for s in bpy.data.scenes
                  if collection in tuple(s.collection.children_recursive)]
        entries = []
        for obj in collection.objects:
            entry = {'name': obj.name, 'type': obj.type, 'tags': tags(obj),
                     'collections': [c.name for c in obj.users_collection],
                     'pose_users': pose_users[obj], **references(obj)}
            if obj.data:
                entry['data'] = {'name': obj.data.name, **references(obj.data)}
            external = set(users.get(obj, ())) - {collection}
            entry['only_collection_user'] = not external
            entry['no_direct_or_record_references'] = not (pose_users[obj] or id_refs[obj] or string_refs[obj])
            entry['unreferenced_except_membership'] = bool(entry['only_collection_user'] and
                entry['no_direct_or_record_references'] and not obj.use_fake_user and not obj.library)
            entries.append(entry)
        candidates.append({'name': collection.name, 'tags': tags(collection),
            'root': collection in roots, 'parents': parents, 'scene_roots': scene_roots,
            'scenes': scenes, 'children': list(collection.children.keys()),
            'instance_objects': [obj.name for obj in bpy.data.objects if obj.instance_collection == collection],
            'objects': entries, **references(collection)})
    report = {'source': str(source), 'production': str(PRODUCTION),
              'production_mtime': PRODUCTION.stat().st_mtime,
              'fixture_sha256': source_hash, 'production_sha256_before': production_hash,
              'blender': bpy.app.version_string, 'all_id_count': len(ids),
              'json_property_paths': sorted(set(json_records)),
              'scene_root_collections': {s.name: list(s.collection.children.keys()) for s in bpy.data.scenes},
              'widget_collections': candidates,
              'summary': {'collections': len(candidates),
                          'root_collections': sum(c['root'] for c in candidates),
                          'objects': sum(len(c['objects']) for c in candidates),
                          'assigned_custom_shapes': sum(bool(o['pose_users']) for c in candidates for o in c['objects']),
                          'record_only_shapes': [o['name'] for c in candidates for o in c['objects']
                                                 if not o['pose_users'] and o['record_or_string_refs']],
                          'unreferenced_except_membership': [o['name'] for c in candidates for o in c['objects']
                                                            if o['unreferenced_except_membership']]}}
    report['fixture_unchanged'] = hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    report['production_sha256_after'] = hashlib.sha256(PRODUCTION.read_bytes()).hexdigest()
    report['production_unchanged_during_audit'] = production_hash == report['production_sha256_after']
    (OUT / 'widget_collections_0543_audit.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print('WIDGET_COLLECTION_AUDIT', json.dumps(report['summary']), flush=True)
    for c in candidates:
        print('COLLECTION', c['name'], 'objects', len(c['objects']),
              'assigned', sum(bool(o['pose_users']) for o in c['objects']),
              'record_only', sum(bool(o['record_or_string_refs']) and not o['pose_users'] for o in c['objects']),
              'unreferenced', sum(o['unreferenced_except_membership'] for o in c['objects']), flush=True)


if __name__ == '__main__':
    main()
