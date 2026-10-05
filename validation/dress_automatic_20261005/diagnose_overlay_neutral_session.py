"""Read-only saved QA evidence for Body Original versus Dress neutral inputs.

Open only the exact sealed f4 QA copy in an empty factory background process.
Do not register add-on handlers, evaluate/replay Cloth, change frame or mode,
remove metadata, change a guard, or save a blend. This report is diagnostic
evidence, not permission to accept a Body Original branch in the overlay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import traceback

import bpy

HERE = Path(__file__).resolve().parent
OVERLAY_SHA = '7a0cb8d621e2e9630ffb4f9f497debad3796172a332dbbf878e45833608c94a9'
OVERLAY = HERE / 'prototype_native_dress_overlay.py'
if hashlib.sha256(OVERLAY.read_bytes()).hexdigest() != OVERLAY_SHA:
    raise RuntimeError('Frozen overlay changed')
sys.path.insert(0, str(HERE))
import prototype_native_dress_overlay as overlay

diag, qa, skirt, require = overlay.diag, overlay.qa, overlay.skirt, overlay.require
ORIGINAL, CORRECTIONS = overlay.ORIGINAL, overlay.CORRECTIONS
DISPLAY_REFS = 'character_designer_original_display_refs_v1'
DISPLAY_OWNER = 'character_designer_original_display_owner_v1'


def schema(value):
    result = {'type': type(value).__name__, 'sha256': qa.digest(value)}
    if isinstance(value, (dict, list, str)):
        result['count'] = len(value)
    if value is None or isinstance(value, (bool, int, float)):
        result['value'] = value
    return result


def stored_json(owner, key):
    if key not in owner:
        return {'present': False}, None
    raw = owner[key]
    encoded = raw.encode('utf-8') if isinstance(raw, str) else json.dumps(
        qa.custom_content(raw), sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')
    result = {'present': True, 'native_type': type(raw).__name__, 'bytes': len(encoded),
              'raw_sha256': hashlib.sha256(encoded).hexdigest(), 'truthy': bool(raw)}
    if not isinstance(raw, str):
        result['parse_error'] = 'Expected JSON string; native metadata left untouched'
        return result, None
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError) as exc:
        result['parse_error'] = str(exc)
        return result, None
    result['parsed'] = schema(parsed)
    if isinstance(parsed, dict):
        result['top_level_schema'] = {key: schema(value) for key, value in parsed.items()}
        result['scalar_identity'] = {key: parsed[key] for key in
            ('version', 'mode', 'rig', 'target', 'source', 'character', 'owner')
            if key in parsed and (parsed[key] is None or isinstance(parsed[key], (str, bool, int, float)))}
    return result, parsed


def name_summary(value, names):
    if isinstance(value, dict):
        values = list(value)
    elif isinstance(value, list):
        values = value
    else:
        return schema(value)
    strings = [name for name in values if isinstance(name, str)]
    return {'type': type(value).__name__, 'count': len(value), 'sha256': qa.digest(value),
            'current_owned_name_intersection': sorted(set(strings) & names)}


def dress_entry_summary(entry, record, names):
    if not isinstance(entry, dict):
        return schema(entry)
    result = {'keys': sorted(entry), 'sha256': qa.digest(entry),
              'scalar_identity': {key: entry[key] for key in ('owner', 'rig', 'target', 'source', 'mode')
                  if key in entry and (entry[key] is None or isinstance(entry[key], (str, bool, int, float)))},
              'matches_current_owner': entry.get('owner') == record['owner']}
    for key in ('names', 'bones', 'constraints', 'channels', 'pose', 'rest', 'parents'):
        if key in entry:
            result[key] = name_summary(entry[key], names)
    nested = entry.get('record')
    if isinstance(nested, dict):
        result['record_identity'] = {key: nested.get(key) for key in ('version', 'owner', 'source', 'rig')}
    return result


def session_summary(rig, record, names):
    result, parsed = stored_json(rig, ORIGINAL)
    result['presence_means_body_original_active'] = ORIGINAL in rig
    result['display_refs'] = qa.custom_content(rig.get(DISPLAY_REFS, {}))
    result['display_owner'] = qa.id_name(rig.get(DISPLAY_OWNER))
    if not isinstance(parsed, dict):
        return result
    result['saved_name_scopes'] = {key: name_summary(parsed[key], names) for key in
        ('bones', 'names', 'rest', 'channels', 'entered_channels', 'pose') if key in parsed}
    groups = parsed.get('native_groups')
    result['native_groups'] = ({role: {target: name_summary(bones, names) for target, bones in part.items()}
        if isinstance(part, dict) else schema(part) for role, part in groups.items()}
        if isinstance(groups, dict) else schema(groups))
    result['dress_fields'] = {}
    for key, value in parsed.items():
        if 'dress' not in key.casefold() and 'skirt' not in key.casefold():
            continue
        entries = value if isinstance(value, list) else [value]
        result['dress_fields'][key] = {'schema': schema(value),
            'entries': [dress_entry_summary(entry, record, names) for entry in entries]}
    saved_constraints = parsed.get('constraints', [])
    result['saved_body_constraint_states'] = []
    if isinstance(saved_constraints, list):
        for entry in saved_constraints:
            if not isinstance(entry, dict):
                result['saved_body_constraint_states'].append(schema(entry))
                continue
            bone = rig.pose.bones.get(entry.get('bone', ''))
            constraint = bone.constraints.get(entry.get('name', '')) if bone else None
            result['saved_body_constraint_states'].append({'saved': entry, 'found': constraint is not None,
                'current_type': constraint.type if constraint else None,
                'current_mute': constraint.mute if constraint else None,
                'belongs_to_current_dress': entry.get('bone') in names})
    return result


def basis_error(pose):
    return max(abs(pose.matrix_basis[row][col] - (1. if row == col else 0.))
               for row in range(4) for col in range(4))


def bone_channels(rig, name, owner):
    pose = rig.pose.bones.get(name)
    if pose is None:
        return {'name': name, 'exists': False}
    error = basis_error(pose)
    return {'name': name, 'exists': True, 'owner': pose.bone.get(skirt.OWNER_KEY),
            'owner_matches': pose.bone.get(skirt.OWNER_KEY) == owner,
            'basis_identity_max_abs_error': error, 'identity_at_overlay_1e7_gate': error < 1.e-7,
            'channels': diag.channels(pose)}


def def_contracts(rig, record):
    result = []
    for chain in record['chains']:
        for name, manual_name, physics_name in zip(chain['def'], chain['manual'], chain['phys']):
            pose = rig.pose.bones[name]
            constraints = list(pose.constraints)
            manual_ok = physics_ok = False
            if len(constraints) >= 2:
                manual, physics = constraints[:2]
                manual_ok = (manual.type == 'COPY_TRANSFORMS' and manual.name == 'Skirt manual pose'
                    and manual.target == rig and manual.subtarget == manual_name
                    and manual.owner_space == manual.target_space == 'LOCAL'
                    and manual.mix_mode == 'REPLACE' and not manual.mute and manual.influence == 1.)
                physics_ok = (physics.type == 'COPY_ROTATION' and physics.name == 'Skirt physics delta'
                    and physics.target == rig and physics.subtarget == physics_name
                    and physics.owner_space == physics.target_space == 'LOCAL'
                    and physics.mix_mode == 'BEFORE' and not physics.mute)
            result.append({'bone': name, 'parent': pose.bone.parent.name if pose.bone.parent else None,
                'connected': pose.bone.use_connect, 'channels': bone_channels(rig, name, record['owner']),
                'expected_manual': manual_name, 'expected_physics': physics_name,
                'exactly_two': len(constraints) == 2, 'overlay_manual_contract_matches': manual_ok,
                'overlay_physics_contract_matches': physics_ok,
                'constraints_complete_writable_RNA': [overlay.strict(constraint) for constraint in constraints],
                'extra_constraints': [{'name': con.name, 'type': con.type, 'mute': con.mute}
                                      for con in constraints[2:]],
                'constraint_name_mentions_original_correction': [con.name for con in constraints
                    if 'original' in con.name.casefold() or 'correction' in con.name.casefold()]})
    return result


def state_hashes(source, rig):
    return {'source': direct_source_hash(source),
        'graph': qa.digest(overlay.graph_content(rig)), 'drivers': qa.digest(overlay.drivers_content(rig)),
        'channels': qa.digest({pose.name: diag.channels(pose) for pose in rig.pose.bones}),
        'rig_metadata': qa.digest({key: qa.custom_content(value) for key, value in rig.items()}),
        'frame': [bpy.context.scene.frame_current, bpy.context.scene.frame_subframe],
        'rig_pose_position': rig.data.pose_position, 'context_mode': bpy.context.mode}


def direct_source_hash(source):
    return overlay.direct.source_signature(source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.output = args.output.resolve()
    require(bpy.app.background and '--factory-startup' in sys.argv and '--disable-autoexec' in sys.argv
            and not bpy.data.filepath, 'Refuse active artist Console; empty factory background only')
    require(args.output.is_relative_to(HERE) and args.output != HERE and not args.output.exists(), 'Fresh QA output only')
    capture = overlay.capture
    require(hashlib.sha256(capture.EVIDENCE.read_bytes()).hexdigest() == capture.EVIDENCE_SHA, 'Frozen f4 report changed')
    evidence = json.loads(capture.EVIDENCE.read_text('utf-8'))
    sealed = Path(evidence['saved_candidate']).resolve()
    require(sealed.is_relative_to(HERE) and sealed.name.startswith('Cosha_Dress_QA_')
            and qa.file_state(sealed) == evidence['candidate_file'], 'Refuse artist or changed sealed input')
    artist = HERE.parents[1] / 'X.blend'
    artist_before, code_before = qa.file_state(artist), diag.source_manifest()
    args.output.mkdir()
    report = {'status': 'starting', 'artist_operation': False, 'scene_saved': False,
        'cloth_replayed': False, 'addon_handlers_registered': False, 'overlay_guard_changed': False,
        'body_original_branch_accepted': False, 'production_effect_accepted': False,
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'frozen_overlay_sha256': OVERLAY_SHA, 'sealed_input': str(sealed),
        'frozen_evidence_sha256': capture.EVIDENCE_SHA, 'errors': [],
        'limits': ['Saved raw RNA and native channel evidence only; no frame or cache evaluation.',
            'Session presence is active Body Original metadata, not an inactive flag.',
            'A nonidentity DEF basis may be dormant under REPLACE; it alone does not prove a correction.',
            'No automatic permission to remove a session or weaken a neutral preflight.']}
    source = rig = protect = before = None
    try:
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(sealed), load_ui=False), 'Sealed QA open failed')
        record = evidence['frozen_record']
        source, rig = bpy.data.objects[record['source']], bpy.data.objects[record['rig']]
        require(skirt.read_record(source) == record, 'Authoritative saved Dress ownership changed')
        names = {name for chain in record['chains'] for name in chain['def']}
        require(len(names) == 32 and len(record['chains']) == 8, 'Exact saved32 Dress required')
        protect = qa.Protection()
        before = state_hashes(source, rig)
        report['protected_before'] = protect.summary()
        report['saved_native_context'] = {key: before[key] for key in ('frame', 'rig_pose_position', 'context_mode')}
        report['current_owner'] = {'source': qa.id_name(source), 'rig': qa.id_name(rig), 'owner': record['owner'],
            'source_rig_pointer': qa.id_name(source.get(skirt.RIG_KEY)),
            'shared_registry': qa.custom_content(rig.get(skirt.SHARED_SOURCES_KEY, {}))}
        report['body_original_session'] = session_summary(rig, record, names)
        correction, parsed = stored_json(source, CORRECTIONS)
        if isinstance(parsed, dict):
            correction['matches_current_owner'] = parsed.get('owner') == record['owner']
            correction['bones'] = name_summary(parsed.get('bones'), names)
        report['source_corrections'] = correction
        manual_names = overlay.owned_names(record)
        require(len(set(manual_names)) == len(manual_names), 'Saved manual names duplicate')
        report['owned_manual_channels'] = [bone_channels(rig, name, record['owner']) for name in manual_names]
        prefixes = tuple(rig.pose.bones[name].path_from_id() + '.' for name in manual_names)
        animation = rig.animation_data
        report['manual_animation_inputs'] = {'action': qa.id_name(animation.action) if animation else None,
            'nla_tracks': [track.name for track in animation.nla_tracks] if animation else [],
            'owned_paths': [{'kind': kind, 'path': curve.data_path, 'index': curve.array_index}
                for kind, curves in (('Action', overlay.action_curves(animation.action if animation else None)),
                                     ('Driver', overlay.driver_curves(rig)))
                for curve in curves if curve.data_path.startswith(prefixes)]}
        report['exact32_def_contracts'] = def_contracts(rig, record)
        owned_prefixes = tuple(rig.pose.bones[name].path_from_id() + '.' for name in names)
        report['owned_def_driver_paths'] = [{'curve': overlay.strict(curve), 'driver': overlay.strict(curve.driver),
            'variables': [{'rna': overlay.strict(variable), 'targets': [overlay.strict(target) for target in variable.targets]}
                          for variable in curve.driver.variables]} for curve in overlay.driver_curves(rig)
            if curve.data_path.startswith(owned_prefixes)]
        report['ExtraOriginalCorrection_observations'] = {
            'source_corrections_present': correction['present'],
            'source_corrections_truthy': correction.get('truthy', False),
            'manual_before_full_bones': [item['bone'] for item in report['exact32_def_contracts']
                if any(con.get('mix_mode') == 'BEFORE_FULL' for con in item['constraints_complete_writable_RNA'])],
            'extra_constraint_bones': [item['bone'] for item in report['exact32_def_contracts'] if not item['exactly_two']],
            'named_original_or_correction': {item['bone']: item['constraint_name_mentions_original_correction']
                for item in report['exact32_def_contracts'] if item['constraint_name_mentions_original_correction']},
            'nonidentity_raw_DEF_basis': [item['bone'] for item in report['exact32_def_contracts']
                if not item['channels']['identity_at_overlay_1e7_gate']]}
        report['status'] = 'diagnostic_collected'
    except BaseException:
        report['errors'].append(traceback.format_exc())
        report['status'] = 'failed'
    finally:
        if protect is not None:
            report['protected_after'] = protect.verify()
            report['saved_native_state_exact'] = state_hashes(source, rig) == before
            if not report['protected_after']['success'] or not report['saved_native_state_exact']:
                report['errors'].append('Read-only native asset/state protection failed')
                report['status'] = 'failed'
        report['artist_disk_exact'] = qa.file_state(artist) == artist_before
        report['code_exact'] = diag.source_manifest() == code_before
        report['sealed_input_exact'] = qa.file_state(sealed) == evidence['candidate_file']
        report['frozen_overlay_exact'] = hashlib.sha256(OVERLAY.read_bytes()).hexdigest() == OVERLAY_SHA
        if not all(report[key] for key in ('artist_disk_exact', 'code_exact', 'sealed_input_exact', 'frozen_overlay_exact')):
            report['errors'].append('Read-only protected file guard failed')
            report['status'] = 'failed'
        (args.output / 'overlay_neutral_session.json').write_text(
            json.dumps(diag.json_content(report), ensure_ascii=False, allow_nan=False, indent=2), 'utf-8')
    require(report['status'] == 'diagnostic_collected', 'Read-only diagnostic failed; inspect report')


if __name__ == '__main__':
    main()
