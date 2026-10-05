"""Lightweight, read-only saved-X Dress ownership and armature user inventory.

Run with factory background Blender and --disable-autoexec. Only the exclusive
--report JSON is written. No add-on is registered, no scene data is changed,
and no .blend is saved. The artist GUI/unsaved scene is never accessed.
"""
import argparse
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import traceback

import bpy


CANONICAL = Path(r'D:\MyRepository\Blender-addons-by-Randy')
OUTPUT_ROOT = Path(__file__).resolve().parent


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(path):
    first = path.stat()
    digest = sha_file(path)
    last = path.stat()
    return {'path': str(path), 'sha256': digest, 'bytes': last.st_size,
            'mtime_ns': last.st_mtime_ns,
            'stable_during_hash': (first.st_size, first.st_mtime_ns)
            == (last.st_size, last.st_mtime_ns)}


def plain(value):
    if isinstance(value, bpy.types.ID):
        return {'type': value.bl_rna.identifier, 'name': value.name,
                'library': str(Path(bpy.path.abspath(value.library.filepath)).resolve())
                if value.library else None}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, 'items'):
        return {str(key): plain(item) for key, item in value.items()}
    try:
        return [plain(item) for item in value]
    except TypeError:
        return {'type': type(value).__name__}


def managed_properties(holder, *, full_record_key=None):
    result = {}
    for key, value in holder.items():
        if not (key.startswith('character_designer') or key.startswith('_cd')):
            continue
        if isinstance(value, str) and value.startswith(('{', '[')):
            try:
                payload = json.loads(value)
            except (TypeError, ValueError):
                payload = None
            result[key] = {'json_characters': len(value),
                           'raw_sha256': hashlib.sha256(value.encode()).hexdigest(),
                           'top_keys': sorted(payload) if isinstance(payload, dict) else None}
            if key == full_record_key:
                result[key]['record'] = payload
            elif isinstance(payload, dict):
                result[key]['version'] = payload.get('version')
                result[key]['owner'] = payload.get('owner')
                result[key]['dress_edit_owners'] = [item.get('owner') for item in payload.get('dress_edit', [])]
        else:
            result[key] = plain(value)
    return result


def armature_object(obj, skirt):
    actual = sorted(item.name for item in bpy.data.objects
                    if item.type == 'ARMATURE' and item.data == obj.data)
    return {'object': obj.name, 'data': obj.data.name, 'mode': obj.mode,
            'data_users': obj.data.users, 'object_users': obj.users,
            'actual_armature_objects': actual, 'actual_armature_object_count': len(actual),
            'library': plain(obj.library), 'override': bool(obj.override_library),
            'editable': obj.is_editable, 'parent': plain(obj.parent),
            'parent_type': obj.parent_type, 'parent_bone': obj.parent_bone,
            'source_ref': plain(obj.get(skirt.SOURCE_KEY)),
            'owner': obj.get(skirt.OWNER_KEY),
            'shared_source_refs': plain(obj.get(skirt.SHARED_SOURCES_KEY)),
            'managed_properties': managed_properties(obj)}


def inspect(skirt, names):
    rigs = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
    result = {'rig_key_holders': [], 'armature_data': [],
              'armature_objects': [armature_object(obj, skirt)
                                   for obj in sorted(rigs, key=lambda item: item.name)]}
    for source in sorted(bpy.data.objects, key=lambda item: item.name):
        if skirt.RIG_KEY not in source and skirt.RECORD_KEY not in source:
            continue
        rig = source.get(skirt.RIG_KEY)
        entry = {'object': source.name, 'type': source.type,
                 'rig_ref': plain(rig), 'owner': source.get(skirt.OWNER_KEY),
                 'source_ref': plain(source.get(skirt.SOURCE_KEY)),
                 'parent': plain(source.parent), 'parent_type': source.parent_type,
                 'parent_bone': source.parent_bone,
                 'managed_properties': managed_properties(source, full_record_key=skirt.RECORD_KEY)}
        raw = source.get(skirt.RECORD_KEY)
        try:
            record = json.loads(raw) if isinstance(raw, str) else None
            if not isinstance(record, dict):
                raise ValueError('Missing or non-dictionary source record.')
            controls, deform, mechanism = skirt._bone_collection_layout(record)
            owned = sorted(controls | deform | mechanism)
            owner = record.get('owner')
            legacy = re.compile(r'^SK_.+_' + re.escape(owner[:6]) + r'(_.+)$') if isinstance(owner, str) else None
            prefix = 'SK_' + names.label(source.name, 37)
            entry['record'] = {'owner': owner, 'rig_name': record.get('rig'),
                               'source_name': record.get('source'), 'character': record.get('character'),
                               'shared': skirt.is_shared(record), 'shared_payload': record.get('shared'),
                               'controls': sorted(controls), 'deform': sorted(deform),
                               'mechanism': sorted(mechanism), 'all_owned_names': owned,
                               'legacy_mapping': {name: prefix + match.group(1) for name in owned
                                                  if legacy and (match := legacy.fullmatch(name))}}
            if isinstance(rig, bpy.types.Object) and rig.type == 'ARMATURE':
                actual = sorted(obj.name for obj in rigs if obj.data == rig.data)
                entry['rig_data'] = {'name': rig.data.name, 'users': rig.data.users,
                                     'objects': actual, 'actual_armature_object_count': len(actual),
                                     'missing_record_bones': sorted(set(owned) - set(rig.data.bones.keys()))}
            # Validation is read-only; preserve failures as observations rather
            # than repairing source records or changing the active pose mode.
            try:
                validated = skirt.read_record(source)
                entry['read_record_valid'] = validated is not None
            except Exception as exc:
                entry['read_record_valid'] = False
                entry['read_record_error'] = type(exc).__name__ + ': ' + str(exc)
        except Exception as exc:
            entry['record_parse_error'] = type(exc).__name__ + ': ' + str(exc)
        result['rig_key_holders'].append(entry)
    for data in sorted(bpy.data.armatures, key=lambda item: item.name):
        users = bpy.data.user_map(subset={data}).get(data, set())
        actual = sorted(obj.name for obj in rigs if obj.data == data)
        bone_owners = Counter(str(bone.get(skirt.OWNER_KEY)) for bone in data.bones)
        result['armature_data'].append({
            'name': data.name, 'users': data.users, 'use_fake_user': data.use_fake_user,
            'library': plain(data.library), 'override': bool(data.override_library),
            'editable': data.is_editable, 'objects': actual,
            'actual_armature_object_count': len(actual),
            'native_user_map': [plain(user) for user in sorted(users, key=lambda item: (item.bl_rna.identifier, item.name))],
            'owner': data.get(skirt.OWNER_KEY), 'source_ref': plain(data.get(skirt.SOURCE_KEY)),
            'bone_count': len(data.bones), 'bone_owner_counts': dict(bone_owners),
            'owned_bones': [{'name': bone.name, 'owner': bone.get(skirt.OWNER_KEY),
                             'source_ref': plain(bone.get(skirt.SOURCE_KEY))}
                            for bone in data.bones if bone.get(skirt.OWNER_KEY) or bone.get(skirt.SOURCE_KEY)],
            'managed_properties': managed_properties(data)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    source, output = args.source.resolve(), args.report.resolve()
    if not source.is_file() or source.suffix.lower() != '.blend':
        raise ValueError('Use an existing saved .blend source.')
    if OUTPUT_ROOT.resolve() not in output.parents or source == output or output.exists():
        raise ValueError('Use a fresh report JSON under the validation evidence directory.')
    output.parent.mkdir(parents=True, exist_ok=True)
    before = fingerprint(source)
    report = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source': str(source), 'blender_version': bpy.app.version_string,
              'blender_binary': bpy.app.binary_path, 'input_before': before,
              'script_sha256': sha_file(__file__), 'errors': [], 'passed': False}
    try:
        if not bpy.app.background or not before['stable_during_hash']:
            raise ValueError('Use a background process and a stable saved input.')
        bpy.context.preferences.filepaths.use_scripts_auto_execute = False
        result = bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
        report['open_result'] = sorted(result)
        if result != {'FINISHED'} or Path(bpy.data.filepath).resolve() != source:
            raise ValueError('Blender did not open the requested input.')
        report['runtime_dirty_observation'] = bpy.data.is_dirty
        report['context_mode'] = bpy.context.mode
        sys.path[:0] = [str(CANONICAL / 'addons')]
        import character_designer
        from character_designer import skirt_rig as skirt, generated_names as names
        if Path(character_designer.__file__).resolve() != CANONICAL / 'addons' / 'character_designer' / '__init__.py':
            raise ValueError('Imported add-on is not the canonical source.')
        report.update(inspect(skirt, names))
        report['passed'] = True
    except Exception as exc:
        report['errors'].append(type(exc).__name__ + ': ' + str(exc))
        report['traceback'] = traceback.format_exc()
    finally:
        after = fingerprint(source)
        report['input_after'] = after
        report['artist_input_unchanged'] = before == after
        if not report['artist_input_unchanged']:
            report['passed'] = False
            report['errors'].append('Artist disk hash/size/mtime changed during inventory.')
        report['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with output.open('x', encoding='utf-8') as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        print(json.dumps({key: report.get(key) for key in ('passed', 'artist_input_unchanged', 'errors')},
                         ensure_ascii=False), flush=True)
    if not report['passed']:
        raise RuntimeError('Read-only Dress inventory failed; see ' + str(output))


if __name__ == '__main__':
    main()
