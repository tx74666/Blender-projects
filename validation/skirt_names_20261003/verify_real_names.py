"""Isolated real-X Dress name migration, with immutable artist input checks.

Run in a factory background Blender with --disable-autoexec. This script opens
--source itself, renames only verified Dress resources in that isolated scene,
saves an exclusive validation copy, and reopens it. It never saves the artist
input, switches Original/Controls, repairs Body, or starts another process.
"""
import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
import traceback

import bpy


CANONICAL = Path(r'D:\MyRepository\Blender-addons-by-Randy')
OUTPUT_ROOT = Path(__file__).resolve().parent
SNAPSHOT_HELPER = OUTPUT_ROOT.parent / 'bone_palette_20261003' / 'verify_saved_x.py'
WORLD_LIMIT = 5e-5
MAPPING = {}
MESH_MAPPING = {}
MANAGED_RECORDS = set()


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fingerprint(path):
    path = Path(path).resolve()
    before = path.stat()
    digest = sha_file(path)
    after = path.stat()
    return {'path': str(path), 'sha256': digest, 'bytes': after.st_size,
            'mtime_ns': after.st_mtime_ns,
            'stable_during_hash': (before.st_size, before.st_mtime_ns)
            == (after.st_size, after.st_mtime_ns)}


def digest_json(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def output_path(path):
    path = Path(path).resolve()
    if OUTPUT_ROOT.resolve() not in path.parents:
        raise ValueError('Validation outputs must remain under ' + str(OUTPUT_ROOT))
    return path


def normalize(value, mapping, *, field=None):
    """Exact bone selectors/RNA and exact generated Hook labels, never prose.

    ID custom properties are normalized separately and only when the typed
    recovery planner has identified that exact holder/key for a rewrite.
    """
    if field in {'props', 'properties'}:
        return value
    if isinstance(value, dict):
        return {mapping.get(key, key): normalize(item, mapping, field=key)
                for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [normalize(item, mapping) for item in value]
    if isinstance(value, str):
        if value in mapping:
            return mapping[value]
        if value.startswith('Control '):
            label = re.fullmatch(r'Control (.+?)(\.\d{3})?', value)
            if label and label.group(1) in mapping:
                return 'Control ' + mapping[label.group(1)] + (label.group(2) or '')
        if 'bones[' not in value:
            return value
        for old, new in mapping.items():
            for selector in ('pose.bones', 'bones'):
                value = value.replace(selector + '[' + json.dumps(old) + ']',
                                      selector + '[' + json.dumps(new) + ']')
    return value


def holder_key(holder):
    if isinstance(holder, bpy.types.ID):
        return holder.bl_rna.identifier + ':' + holder.name
    owner = getattr(holder, 'id_data', None)
    return (holder.bl_rna.identifier + ':' + getattr(owner, 'name', '') + ':'
            + MAPPING.get(getattr(holder, 'name', ''), getattr(holder, 'name', '')))


def load_helpers(evidence_root):
    spec = importlib.util.spec_from_file_location('names_saved_x_snapshot', SNAPSHOT_HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUTPUT_ROOT = evidence_root
    old_plain, old_mesh_state, old_digest = module.plain, module.mesh_state, module.Digest
    old_animation_state = module.animation_state

    def plain(value):
        if isinstance(value, bpy.types.ID):
            library = value.library
            return {'id_type': value.bl_rna.identifier, 'name': value.name,
                    'library': str(Path(bpy.path.abspath(library.filepath)).resolve())
                    if library else None}
        return old_plain(value)

    def properties(owner, **_ignored):
        result = {}
        try:
            items = owner.items()
        except TypeError:  # Native sockets/modifiers cannot store IDProperties in 5.1.
            return result
        for key, value in items:
            if (holder_key(owner), key) in MANAGED_RECORDS:
                if not isinstance(value, str):
                    raise ValueError('A planned recovery record is no longer JSON text.')
                result[key] = normalize(json.loads(value), MAPPING)
            else:
                result[key] = plain(value)
        return result

    class NamesDigest(old_digest):
        def add(self, tag, value):
            # Coordinates, weights, Shape Key arrays and arbitrary metadata
            # remain exact. Only bound mesh group selectors may follow bones.
            if tag == 'groups':
                value = [[MESH_MAPPING.get(entry[0], entry[0]), *entry[1:]]
                         for entry in value]
            elif tag == 'key':
                value = list(value)
                value[6] = MESH_MAPPING.get(value[6], value[6])
            return super().add(tag, value)

    def mesh_state(obj):
        global MESH_MAPPING
        previous = MESH_MAPPING
        MESH_MAPPING = {}
        for plan in PLANS:
            rig = bpy.data.objects.get(plan['rig'])
            if rig and bound(obj, rig):
                MESH_MAPPING.update({old: new for old, new in plan['mapping'].items()
                                     if old in MAPPING})
        try:
            return old_mesh_state(obj)
        finally:
            MESH_MAPPING = previous

    module.plain, module.properties = plain, properties
    module.Digest, module.mesh_state = NamesDigest, mesh_state
    module.animation_state = lambda item: (old_animation_state(item)
                                          if hasattr(item, 'animation_data') else None)
    return module


def bound(obj, rig):
    return obj.type == 'MESH' and (obj.parent == rig or any(
        modifier.type == 'ARMATURE' and modifier.object == rig for modifier in obj.modifiers))


PLANS = []


def naming_plans(skirt, names, records):
    result, mappings = [], {}
    for source in sorted(bpy.data.objects, key=lambda item: item.name):
        if skirt.RECORD_KEY not in source:
            continue
        record = skirt.read_record(source)
        rig = source[skirt.RIG_KEY]
        owned = sorted(set.union(*skirt._bone_collection_layout(record)))
        legacy = re.compile(r'^SK_.+_' + re.escape(record['owner'][:6]) + r'(_.+)$')
        prefix = 'SK_' + names.label(source.name, 37)
        mapping = {name: prefix + match.group(1) for name in owned
                   if (match := legacy.fullmatch(name))}
        for old, new in mapping.items():
            if old in mappings and mappings[old] != new:
                raise ValueError('Two Dress owners require ambiguous global normalization.')
            mappings[old] = new
        hooks = []
        for object_name in record['owned_objects']:
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                raise ValueError('A recorded Dress helper is missing: ' + object_name)
            for index, modifier in enumerate(obj.modifiers):
                label = re.fullmatch(re.escape('Control ' + modifier.subtarget)
                                     + r'(\.\d{3})?', modifier.name) if modifier.type == 'HOOK' else None
                if (modifier.type == 'HOOK' and modifier.object == rig
                        and modifier.subtarget in mapping and label):
                    hooks.append({'object': obj.name, 'index': index,
                                  'from': modifier.name,
                                  'to': 'Control ' + mapping[modifier.subtarget] + (label.group(1) or ''),
                                  'old_subtarget': modifier.subtarget,
                                  'new_subtarget': mapping[modifier.subtarget]})
        saved_records = records.snapshots(source, rig, mapping) if mapping else []
        updates = []
        for holder, key, raw, updated in saved_records:
            # Independently require the planner to change only exact selectors.
            if normalize(json.loads(raw), mapping) != normalize(json.loads(updated), {}):
                raise ValueError('A recovery plan changes data beyond the exact name map: ' + key)
            MANAGED_RECORDS.add((holder_key(holder), key))
            updates.append({'holder': holder_key(holder), 'key': key,
                            'before_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                            'after_sha256': hashlib.sha256(updated.encode()).hexdigest()})
        result.append({'source': source.name, 'rig': rig.name, 'owner': record['owner'],
                       'shared': skirt.is_shared(record), 'owned_bones': owned,
                       'mapping': mapping, 'hooks': hooks, 'record_updates': updates})
    return result, mappings


def extra_ids(helper):
    result = {}
    # Object/data None and non-mesh objects are handled by the focused helper.
    # Include animation/ID refs outside the mesh and armature domains as well.
    for domain in ('cameras', 'lights', 'worlds', 'materials', 'node_groups',
                   'textures', 'cache_files', 'shape_keys'):
        for item in getattr(bpy.data, domain, ()):
            state = {'properties': helper.properties(item), 'fields': helper.rna(item),
                     'animation': helper.animation_state(item)}
            tree = getattr(item, 'node_tree', None)
            if tree is None and isinstance(item, bpy.types.NodeTree):
                tree = item
            if tree is not None:
                state['node_tree'] = {'properties': helper.properties(tree),
                    'animation': helper.animation_state(tree),
                    'nodes': [{'fields': helper.rna(node), 'properties': helper.properties(node),
                               'inputs': [{'fields': helper.rna(socket),
                                           'properties': helper.properties(socket)}
                                          for socket in node.inputs]}
                              for node in tree.nodes],
                    'links': [(link.from_node.name, link.from_socket.identifier,
                               link.to_node.name, link.to_socket.identifier, link.is_muted)
                              for link in tree.links]}
            result[domain + ':' + item.name] = state
    for obj in bpy.data.objects:
        if obj.data is not None and obj.type not in {'MESH', 'CURVE', 'ARMATURE', 'CAMERA', 'LIGHT'}:
            result['other_object_data:' + obj.name] = {
                'fields': helper.rna(obj.data), 'properties': helper.properties(obj.data),
                'animation': helper.animation_state(obj.data)}
    for image in bpy.data.images:
        fields = helper.rna(image, skip={'filepath', 'filepath_raw', 'pixels'})
        # copy=True rebases relative paths for the validation directory. Their
        # resolved identity must stay exact, including unresolved artist refs.
        path = (str(Path(bpy.path.abspath(image.filepath, library=image.library)).resolve())
                if image.filepath else '')
        packed = [hashlib.sha256(item.packed_file.data).hexdigest()
                  for item in image.packed_files]
        result['images:' + image.name] = {
            'fields': fields, 'resolved_path': path, 'packed_sha256': packed,
            'properties': helper.properties(image), 'animation': helper.animation_state(image)}
    return result


def identity_inventory():
    result = {}
    for prop in bpy.data.bl_rna.properties:
        if prop.type != 'COLLECTION':
            continue
        items = getattr(bpy.data, prop.identifier)
        if prop.identifier == 'libraries':
            result[prop.identifier] = sorted(
                str(Path(bpy.path.abspath(item.filepath)).resolve()) for item in items)
        else:
            result[prop.identifier] = sorted(item.name for item in items)
    return result


def scene_state(helper, mapping):
    global MAPPING
    MAPPING = mapping
    result = helper.protected_state([])
    result['pose_colors_exact'] = {
        obj.name: {pb.name: {'palette': pb.color.palette,
                            'constraints': pb.color.custom.show_colored_constraints,
                            **{field: list(getattr(pb.color.custom, field))
                               for field in ('normal', 'select', 'active')}}
                   for pb in obj.pose.bones}
        for obj in bpy.data.objects if obj.type == 'ARMATURE'}
    result['extra_ids'] = extra_ids(helper)
    result = normalize(result, mapping)
    # Names of IDs and opaque values have no permission to follow bone renames.
    result['identity_inventory'] = identity_inventory()
    return result


def session_observations(original):
    observations = []
    for rig in bpy.data.objects:
        if rig.type != 'ARMATURE':
            continue
        raw = rig.get(original.SESSION)
        if raw is None:
            continue
        saved = json.loads(raw)
        observations.append({'rig': rig.name, 'active': original.active(rig),
                             'version': saved.get('version'),
                             'body_constraint_entries': len(saved.get('constraints', [])),
                             'dress_edit_owners': [entry.get('owner')
                                                  for entry in saved.get('dress_edit', [])],
                             'raw_sha256': hashlib.sha256(raw.encode()).hexdigest()})
    return observations


def recovery_texts():
    result = {}
    for identity, key in sorted(MANAGED_RECORDS):
        domain, name = identity.split(':', 1)
        holders = [item for item in tuple(bpy.data.objects) + tuple(bpy.data.armatures)
                   if item.bl_rna.identifier == domain and item.name == name]
        if len(holders) != 1:
            raise ValueError('A recovery record holder is missing or ambiguous: ' + identity)
        raw = holders[0].get(key)
        if not isinstance(raw, str):
            raise ValueError('A saved recovery record is missing: ' + key)
        result[identity + '/' + key] = raw
    return result


def verify_bones(helper, expected, mapping):
    actual = helper.world_bones()
    wanted = normalize(expected, mapping)
    differences = helper.compare(actual, wanted, tolerance=WORLD_LIMIT, path='world_bones')
    maximum = 0.0
    for rig, bones in wanted.items():
        for name, matrix in bones.items():
            current = actual.get(rig, {}).get(name)
            if current is not None:
                maximum = max(maximum, max(abs(a-b) for row, changed in zip(matrix, current)
                                           for a, b in zip(row, changed)))
    if differences:
        raise AssertionError('World bone poses changed: ' + '\n'.join(differences[:20]))
    return {'rigs': len(actual), 'bones': sum(len(bones) for bones in actual.values()),
            'maximum_matrix_error': maximum}


def check_raw(helper, actual, expected, stage, report):
    differences = helper.compare(actual, expected, tolerance=0, path='protected')
    report[stage] = {'passed': not differences,
                     'expected_sha256': digest_json(expected),
                     'actual_sha256': digest_json(actual),
                     'differences': differences[:50]}
    if differences:
        raise AssertionError(stage + ' changed protected raw data: ' + '\n'.join(differences[:20]))


def clean_pass(skirt, cleaner, plans, *, expected_events):
    result = []
    for plan in plans:
        source = bpy.data.objects.get(plan['source'])
        if source is None or source.get(skirt.OWNER_KEY) != plan['owner']:
            raise ValueError('The exact Dress source ownership changed.')
        events = cleaner.clean(source)
        expected = ([('bone', old, new) for old, new in plan['mapping'].items()]
                    + [('hook', hook['from'], hook['to']) for hook in plan['hooks']])
        if expected_events and Counter((event['kind'], event['from'], event['to'])
                                       for event in events) != Counter(expected):
            raise AssertionError('Cleanup events differ from the exact bone/Hook plan.')
        if not expected_events and events:
            raise AssertionError('Dress name cleanup is not idempotent.')
        record = skirt.read_record(source)
        skirt._check_existing_geometry(source, record)
        result.append({'source': source.name, 'owner': plan['owner'], 'events': events})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Fresh saved artist .blend input')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, help='Exclusive validation copy under this evidence folder')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    source = args.source.resolve()
    report_path = output_path(args.report)
    candidate = output_path(args.candidate or report_path.with_name(report_path.stem + '_validation_copy.blend'))
    evidence = output_path(report_path.with_name(report_path.stem + '_evidence'))
    if source.suffix.lower() != '.blend' or not source.is_file():
        raise ValueError('--source must be an existing saved .blend file.')
    if source in {report_path, candidate} or report_path == candidate:
        raise ValueError('Artist input and validation outputs must be different paths.')
    if candidate.suffix.lower() != '.blend':
        raise ValueError('The validation candidate must have a .blend extension.')
    if any(path.exists() for path in (report_path, candidate, evidence)):
        raise FileExistsError('Use fresh validation output names; existing evidence is retained.')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    evidence.mkdir()
    before = fingerprint(source)
    report = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'blender_version': bpy.app.version_string, 'blender_binary': bpy.app.binary_path,
              'artist_input': str(source), 'input_before': before, 'candidate': str(candidate),
              'report': str(report_path), 'script_sha256': sha_file(__file__),
              'snapshot_helper': str(SNAPSHOT_HELPER), 'snapshot_helper_sha256': sha_file(SNAPSHOT_HELPER),
              'limits': {'raw_state': 'exact after only allowed bone selectors/Hook labels',
                         'world_bone_matrix': WORLD_LIMIT, 'world_mesh_position': WORLD_LIMIT},
              'errors': [], 'passed': False}
    helper, code_before = None, None
    started = time.perf_counter()
    global PLANS, MAPPING
    try:
        if not before['stable_during_hash']:
            raise ValueError('Artist input changed while the initial fingerprint was read.')
        if not bpy.app.background:
            raise ValueError('Run only in an isolated background Blender, never the artist GUI.')
        bpy.context.preferences.filepaths.use_scripts_auto_execute = False
        report['autoexec_disabled'] = not bpy.context.preferences.filepaths.use_scripts_auto_execute
        report['open_result'] = sorted(bpy.ops.wm.open_mainfile(filepath=str(source),
                                                              load_ui=False, use_scripts=False))
        if report['open_result'] != ['FINISHED'] or Path(bpy.data.filepath).resolve() != source:
            raise AssertionError('Blender did not open the requested saved input.')
        sys.path[:0] = [str(CANONICAL / 'addons')]
        import character_designer
        from character_designer import (
            body_original_mode as original, generated_names as names,
            skirt_names as cleaner, skirt_name_records as records, skirt_rig as skirt,
        )
        if Path(character_designer.__file__).resolve() != CANONICAL / 'addons' / 'character_designer' / '__init__.py':
            raise ValueError('The imported add-on is not the canonical source.')
        helper = load_helpers(evidence)
        code_before = helper.source_hashes(CANONICAL)
        report['canonical_source_hashes'] = code_before
        report['original_before'] = session_observations(original)
        report['runtime_dirty_before'] = bpy.data.is_dirty
        # Read-only planning does not attempt to repair existing Body state.
        PLANS, mapping = naming_plans(skirt, names, records)
        report['plans'] = PLANS
        report['dress_sources'] = len(PLANS)
        report['owned_dress_bones'] = sum(len(plan['owned_bones']) for plan in PLANS)
        report['planned_bone_renames'] = len(mapping)
        report['planned_hook_renames'] = sum(len(plan['hooks']) for plan in PLANS)
        if not PLANS or not mapping:
            raise ValueError('No verified legacy Dress bone names were found in the fresh source.')
        bpy.context.view_layer.update()
        baseline = scene_state(helper, mapping)
        poses = helper.world_bones()
        vertices = helper.world_meshes(capture=True)
        report['protected_counts'] = {'objects': len(baseline['objects']),
                                      'meshes': len(baseline['meshes']),
                                      'rigs': len(baseline['armatures'])}
        baseline_path = evidence / 'normalized_baseline.json.gz'
        with gzip.open(baseline_path, 'xt', encoding='utf-8') as handle:
            json.dump({'artist_input': str(source), 'input_fingerprint': before,
                       'protected': baseline, 'world_bones': poses, 'world_meshes': vertices},
                      handle, ensure_ascii=False, allow_nan=False)
        report['baseline'] = str(baseline_path)
        report['baseline_sha256'] = sha_file(baseline_path)
        report['first_clean'] = clean_pass(skirt, cleaner, PLANS, expected_events=True)
        MAPPING = {}
        check_raw(helper, scene_state(helper, {}), baseline, 'after_clean', report)
        report['world_bones_after_clean'] = verify_bones(helper, poses, mapping)
        report['world_meshes_after_clean'] = helper.world_meshes(expected=vertices)
        report['second_clean'] = clean_pass(skirt, cleaner, PLANS, expected_events=False)
        saved_texts = recovery_texts()
        report['recovery_records_after_clean'] = {key: hashlib.sha256(raw.encode()).hexdigest()
                                                  for key, raw in saved_texts.items()}
        report['original_after_clean'] = session_observations(original)
        result = bpy.ops.wm.save_as_mainfile(filepath=str(candidate), copy=True,
                                           relative_remap=True, check_existing=False)
        report['save_result'] = sorted(result)
        if result != {'FINISHED'} or not candidate.is_file():
            raise AssertionError('Blender did not confirm saving the validation-only copy.')
        if Path(bpy.data.filepath).resolve() != source:
            raise AssertionError('copy=True unexpectedly changed the artist input filepath.')
        report['candidate_fingerprint'] = fingerprint(candidate)
        result = bpy.ops.wm.open_mainfile(filepath=str(candidate), load_ui=False, use_scripts=False)
        report['reopen_result'] = sorted(result)
        if result != {'FINISHED'} or Path(bpy.data.filepath).resolve() != candidate:
            raise AssertionError('Blender did not reopen the validation-only copy.')
        bpy.context.view_layer.update()
        check_raw(helper, scene_state(helper, {}), baseline, 'after_reopen', report)
        if recovery_texts() != saved_texts:
            raise AssertionError('Managed record/session JSON did not persist byte-for-byte after cleanup.')
        report['recovery_records_reopened_exact'] = True
        report['original_after_reopen'] = session_observations(original)
        report['runtime_dirty_after_reopen'] = bpy.data.is_dirty
        report['reopen_clean'] = clean_pass(skirt, cleaner, PLANS, expected_events=False)
        report['world_bones_after_reopen'] = verify_bones(helper, poses, mapping)
        report['world_meshes_after_reopen'] = helper.world_meshes(expected=vertices)
        report['canonical_source_unchanged'] = helper.source_hashes(CANONICAL) == code_before
        if not report['canonical_source_unchanged']:
            raise AssertionError('Canonical source changed during validation.')
        report['passed'] = True
    except Exception as exc:
        report['errors'].append(type(exc).__name__ + ': ' + str(exc))
        report['traceback'] = traceback.format_exc()
    finally:
        if helper is not None and code_before is not None:
            report['canonical_source_unchanged'] = helper.source_hashes(CANONICAL) == code_before
            if not report['canonical_source_unchanged']:
                report['passed'] = False
                report['errors'].append('Canonical source changed during validation.')
        after = fingerprint(source)
        report['input_after'] = after
        report['artist_input_unchanged'] = before == after
        report['input_sha256_before'], report['input_sha256_after'] = before['sha256'], after['sha256']
        if not report['artist_input_unchanged']:
            report['passed'] = False
            report['errors'].append('Artist disk input changed; hash/size/mtime guard failed.')
        report['elapsed_seconds'] = time.perf_counter() - started
        report['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with report_path.open('x', encoding='utf-8') as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        print(json.dumps({key: report.get(key) for key in (
            'passed', 'planned_bone_renames', 'planned_hook_renames',
            'artist_input_unchanged', 'candidate', 'errors')}, ensure_ascii=False, indent=2), flush=True)
    if not report['passed']:
        raise RuntimeError('Real-X Dress name validation failed; see ' + str(report_path))


if __name__ == '__main__':
    main()
