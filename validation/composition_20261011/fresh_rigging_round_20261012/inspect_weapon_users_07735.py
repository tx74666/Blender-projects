"""Read the failed owned clone's weapon users without CD handlers or any scene writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROUND = Path(__file__).resolve().parent
CLONE = ROUND / 'recovery_gun_undo_07735_01/failed_original20_recovery_gun_undo.blend'
CLONE_SHA = '2c13f8fc3a42a008b8120b515c86f60ffb6d2fd40972afb24b35701cd023bd36'
ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
ARTIST_SHA = 'cc9a624dfc3e8a939ee62d0f4b14ccef3456ad9152c9091661968a9a0593c756'
RECORD = 'character_designer_composition_weapon_v1'
OWNER = 'character_designer_composition_weapon_owner'


def pin(path, expected):
    data = Path(path).read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    assert actual == expected, str(path)
    return {'path': str(Path(path).resolve()), 'sha256': actual, 'bytes': len(data)}


def ref(value):
    return None if value is None else {'type': value.bl_rna.identifier, 'name': value.name,
        'library': value.library.filepath if value.library else None, 'pointer': str(value.as_pointer())}


def id_refs(value, path=()):
    import bpy
    if isinstance(value, bpy.types.ID):
        return [{'path': list(path), 'target': ref(value)}]
    if hasattr(value, 'items'):
        return [row for key, item in value.items() for row in id_refs(item, path + (str(key),))]
    return []


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--source-sha256', required=True)
    args.add_argument('--output-root', required=True)
    opts = args.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = Path(opts.output_root).resolve()
    assert output.is_relative_to(ROUND) and output.is_dir() and not any(output.iterdir())
    source, clone, artist = pin(__file__, opts.source_sha256), pin(CLONE, CLONE_SHA), pin(ARTIST, ARTIST_SHA)
    import bpy
    assert bpy.app.background and not bpy.data.filepath
    assert not any(name == 'character_designer' or name.startswith('character_designer.') for name in sys.modules)
    assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
    assert bpy.ops.wm.open_mainfile('EXEC_DEFAULT', False, filepath=str(CLONE), use_scripts=False, load_ui=False) == {'FINISHED'}
    rig = bpy.data.objects['CoshaRig']
    record = rig[RECORD]
    collection, scene = record['collection'], record['scene']
    objects = tuple(record['objects'].values())
    allowed = {rig, collection, *objects}
    users = bpy.data.user_map()
    all_targets = {collection, *objects}
    rows = []
    for obj in objects:
        owners = users.get(obj, set())
        rows.append({'object': ref(obj), 'owner_tag': obj.get(OWNER),
            'collections': [ref(c) for c in obj.users_collection],
            'users_count': obj.users, 'users': [ref(o) for o in owners],
            'unexpected_users': [ref(o) for o in owners if o not in allowed]})
    external = {o for obj in objects for o in users.get(obj, set()) if o not in allowed}
    details = []
    for owner in external:
        row = {'owner': ref(owner), 'id_property_references': id_refs(owner),
            'per_target_user_of_id': [{'target': ref(t), 'count': owner.user_of_id(t)} for t in all_targets]}
        pointers = []
        for prop in owner.bl_rna.properties:
            if prop.type != 'POINTER' or prop.identifier == 'rna_type':
                continue
            try:
                value = getattr(owner, prop.identifier)
                if isinstance(value, bpy.types.ID):
                    pointers.append({'field': prop.identifier, 'target': ref(value)})
            except (AttributeError, RuntimeError, TypeError):
                pass
        row['RNA_ID_pointers'] = pointers
        if isinstance(owner, bpy.types.Scene):
            row['scene_membership'] = {obj.name: obj.name in owner.objects for obj in objects}
            row['marker_cameras'] = [{'name': m.name, 'camera': ref(m.camera)} for m in owner.timeline_markers if m.camera]
            row['view_layers'] = [{'name': layer.name, 'active': ref(layer.objects.active),
                'owned_members': [obj.name for obj in objects if obj.name in layer.objects]} for layer in owner.view_layers]
        details.append(row)
    report = {'schema': 'x.validation.weapon-user-map-diagnostic/1', 'completed': True,
        'diagnostic_only': True, 'semantic_validation_pass': False, 'pid': os.getpid(),
        'source': source, 'clone': clone, 'protected_artist': artist,
        'version': list(bpy.app.version), 'rig': ref(rig), 'scene': ref(scene),
        'collection': ref(collection), 'collection_users_count': collection.users,
        'collection_user_map': [ref(o) for o in users.get(collection, set())],
        'record_owner': record['owner'], 'allowed': [ref(o) for o in allowed],
        'objects': rows, 'external_details': details,
        'rig_id_property_references': id_refs(rig),
        'native_session': rig.get('character_designer_rigging_session_v1'),
        'tweak_mode': bool(rig.animation_data.use_tweak_mode),
        'scene_written': False, 'CD_registered': False, 'save_performed': False}
    pin(CLONE, CLONE_SHA); pin(ARTIST, ARTIST_SHA); pin(__file__, opts.source_sha256)
    destination = output / 'weapon_user_map_report.json'
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('WEAPON_USER_MAP ' + json.dumps({'report': str(destination), 'external': [ref(o) for o in external]}), flush=True)


if __name__ == '__main__':
    main()
