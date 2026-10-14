"""Source-prepared one-call SaveCopy of the current unsaved original X state.

Root must verify actual process FILETIME/resource ownership externally before
the future SDK call. No SDK/app call occurs while preparing this file. No
candidate runtime is imported, registered or refreshed by the snapshot.
"""

from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import sys


ARTIST = Path(r'D:\Blender\Projects\Character\X\X.blend')
ARTIST_SHA = '3cd5619d70e8b4e21c2483884a04d352a2405f0eab02f00d34d306c81c5aa4b0'
ROUND = Path(r'D:\Blender\Projects\Character\X\validation\composition_20261011\fresh_rigging_round_20261012')
HISTORY = Path(r'D:\Blender\Projects\Character\X\validation\direct_original_rig_return_20261011')
SCRIPT = ROUND / 'snapshot_latest_original_artist.py'


def require(value, text):
    if not value:
        raise RuntimeError(text)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def pin(path, expected):
    p = Path(path).resolve()
    require(p.is_file() and sha(p) == expected, 'Pinned snapshot input changed: ' + str(p))
    return {'path': str(p), 'sha256': expected, 'bytes': p.stat().st_size}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def save_report(path, value, *, first=False):
    with path.open('x' if first else 'w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def reference(value):
    return {'type': type(value).__name__, 'name': value.name,
        'library': value.library.filepath if value.library else None,
        'native_pointer': int(value.as_pointer())}


def plain(value, *, depth=0):
    require(depth <= 24, 'Snapshot metadata exceeds its bounded depth.')
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        require(math.isfinite(value), 'Nonfinite saved metadata is Unknown.')
        return value
    if hasattr(value, 'library') and hasattr(value, 'as_pointer') and hasattr(value, 'name'):
        return reference(value)
    if isinstance(value, set):
        return sorted(plain(v, depth=depth + 1) for v in value)
    if callable(getattr(value, 'items', None)):
        return {str(k): plain(v, depth=depth + 1) for k, v in value.items()}
    if hasattr(value, 'to_list'):
        return plain(value.to_list(), depth=depth + 1)
    require(hasattr(value, '__iter__') and hasattr(value, '__len__') and len(value) <= 10000,
            'Unsupported or unbounded saved metadata: ' + type(value).__name__)
    return [plain(v, depth=depth + 1) for v in value]


def rna_record(block, *, depth=0):
    """Read fixed RNA settings/collections; native ID pointers are detached."""
    require(depth <= 12, 'Snapshot RNA exceeds its bounded depth.')
    result = {}
    for prop in block.bl_rna.properties:
        name = prop.identifier
        if name in {'rna_type', 'execution_time'}:
            continue  # Schema/evaluation timing is not a stored modifier setting.
        value = getattr(block, name)
        if prop.type == 'COLLECTION':
            require(len(value) <= 10000, 'Snapshot RNA collection exceeds its bound: ' + name)
            result[name] = [rna_record(row, depth=depth + 1) for row in value]
        elif prop.type == 'POINTER' and value is not None:
            if hasattr(value, 'library') and hasattr(value, 'name'):
                result[name] = reference(value)
            else:
                result[name] = rna_record(value, depth=depth + 1)
        else:
            result[name] = plain(value)
    custom_keys = getattr(block, 'keys', None)
    require(callable(custom_keys), 'Snapshot custom-property key accessor is unsupported.')
    try:
        keys = custom_keys()
    except TypeError as error:
        if str(error) != "bpy_struct.keys(): this type doesn't support IDProperties":
            raise
        result['$custom_properties'] = {'$unsupported_idproperties': True}
    else:
        result['$custom_properties'] = plain({str(key): block[key] for key in keys})
    return result


def attempt(operation):
    try:
        return {'known': True, 'value': operation()}
    except Exception as error:
        return {'known': False, 'reason': type(error).__name__ + ': ' + str(error)}


def context_record(ctx, bpy):
    active = ctx.view_layer.objects.active
    return {'filepath': str(Path(bpy.data.filepath).resolve()), 'scene': reference(ctx.scene),
        'view_layer': ctx.view_layer.name, 'frame': ctx.scene.frame_current,
        'subframe': ctx.scene.frame_subframe, 'active': reference(active) if active else None,
        'mode': active.mode if active else None, 'selected': sorted(o.name for o in ctx.selected_objects),
        'active_bone': active.data.bones.active.name if active and active.type == 'ARMATURE' and active.data.bones.active else None,
        'selected_pose': sorted(p.name for p in (ctx.selected_pose_bones or ())),
        'autokey': ctx.scene.tool_settings.use_keyframe_insert_auto}


@contextmanager
def original_context(bpy, scene_name, rig_name):
    windows = [w for w in bpy.context.window_manager.windows if w.scene.name == scene_name]
    require(len(windows) == 1, 'The original artist Window/Scene is missing or ambiguous; do not switch it.')
    window = windows[0]
    with bpy.context.temp_override(window=window):
        ctx = bpy.context
        rig = ctx.scene.objects.get(rig_name)
        require(ctx.scene is window.scene and ctx.view_layer.as_pointer() != 0 and ctx.view_layer.as_pointer() == window.view_layer.as_pointer()
                and rig is not None and rig.type == 'ARMATURE' and rig.library is None
                and rig.data.library is None and ctx.view_layer.objects.get(rig_name) == rig
                and getattr(ctx.scene.character_designer_setup, 'rig', None) == rig,
                'Use the real original setup Rig in its own Scene/ViewLayer; no selection/adoption fallback.')
        yield ctx, rig


def snapshot(ctx, rig, bpy, ua):
    """Light original-process inventory; heavy content belongs to its clone."""
    skins = [o for o in ctx.scene.objects if o.type == 'MESH' and
        (o.parent == rig or any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers))]
    modifiers = attempt(lambda: {o.name: [rna_record(m) for m in o.modifiers] for o in skins})
    worklist = attempt(lambda: rna_record(ctx.scene.character_designer_animation_worklist))
    raw = attempt(lambda: {'rig': reference(rig), 'data': reference(rig.data),
        'rig_properties': plain(dict(rig.items())), 'data_properties': plain(dict(rig.data.items())),
        'rawRest': ua._rest_state(rig.data),
        'pose_Action_NLA_clock_state': ua._snapshot(ctx, rig),
        'bones': {b.name: plain(dict(b.items())) for b in rig.data.bones},
        'pose_properties': {p.name: plain(dict(p.items())) for p in rig.pose.bones}})
    actions = []
    for action in bpy.data.actions:
        slots = list(action.slots) if action.is_action_layered else ()
        rows = [{'handle': s.handle, 'target_id_type': s.target_id_type,
                 'identifier': s.identifier, 'name_display': s.name_display} for s in slots]
        handles = [s.handle for s in slots] if slots else [0]
        motions = {str(handle): {'fingerprint_known': False,
            'proof_reason': 'Complete motion content deferred to isolated snapshot clone; no original-process key scan.'} for handle in handles}
        actions.append({'identity': reference(action), 'slots': rows, 'selected_slot_content': motions,
            'custom_properties': attempt(lambda a=action: plain(dict(a.items())))})
    ad = rig.animation_data
    assets = {'known': False, 'reason': 'Full streamed geometry/weights/shape-key/material/color/widget/forearm oracle deferred to isolated snapshot clone.'}
    return {'context': context_record(ctx, bpy), 'assets': assets, 'modifier_stacks': modifiers,
        'full_worklist': worklist, 'original_MainRig_session_and_rawRest': raw,
        'actions': actions, 'active_action': reference(ad.action) if ad and ad.action else None,
        'active_action_slot': ad.action_slot_handle if ad else None, 'six_mesh_count_expected': 6,
        'actual_skin_names': sorted(o.name for o in skins),
        'skin_native_ids': {o.name: {'object': reference(o), 'data': reference(o.data),
            'materials': [reference(m) if m else None for m in o.data.materials],
            'vertex_groups': [g.name for g in o.vertex_groups],
            'shape_keys': [k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else []} for o in skins},
        'all_Action_slot_contents_known': False}


def run(*, expected_pid, external_process_filetime, script_sha256, output_root,
        oracle_sha256, runtime_manifest_sha256, scene_name='Scene', rig_name='CoshaRig'):
    """Future one original SDK call; no native execution during Source preparation."""
    require(type(expected_pid) is int and os.getpid() == expected_pid
            and type(external_process_filetime) is int and external_process_filetime > 0,
            'Root must freshly verify and bind actual original PID/FILETIME before this call.')
    bpy = sys.modules.get('bpy')
    cd = sys.modules.get('character_designer')
    require(bpy is not None and cd is not None and tuple(cd.bl_info['version']) == (0, 77, 24),
            'The actual already-loaded artist runtime must be .24; never load/register a candidate.')
    require(Path(bpy.data.filepath).resolve() == ARTIST.resolve(), 'The live file is not the original X.blend.')
    protected = pin(ARTIST, ARTIST_SHA)
    source = pin(SCRIPT, script_sha256)
    projection = pin(HISTORY / 'release_projection_07724.json', runtime_manifest_sha256)
    manifest = json.loads(Path(projection['path']).read_text(encoding='utf-8-sig'))
    require(manifest['schema_version'] == 1 and manifest['module'] == 'character_designer'
            and manifest['version'] == '0.77.24', 'Use the immutable actual .24 source projection.')
    runtime_root = Path(cd.__file__).resolve().parent
    checked = {}
    def cached(name):
        module = sys.modules.get(name)
        require(module is not None, 'Already-loaded .24 module unavailable: ' + name)
        if name == 'bpy':
            return module
        path = Path(module.__file__).resolve()
        require(path.is_relative_to(runtime_root), 'The actual cached module comes from another root: ' + name)
        relative = path.relative_to(runtime_root).as_posix()
        require(relative in manifest['files'], 'The actual cached module is not in .24: ' + name)
        checked[name] = pin(path, manifest['files'][relative])
        return module
    cached('character_designer')
    ua = cached('character_designer.unity_animation')
    oracle_input = pin(HISTORY / 'validation_preservation.py', oracle_sha256)
    destination = Path(output_root).resolve()
    require(destination != ROUND and destination.is_relative_to(ROUND)
            and destination.is_dir() and not any(destination.iterdir()), 'Use one new empty persistent ROUND child.')
    backup, receipt = destination / 'artist_latest_before_rigging.blend', destination / 'artist_latest_snapshot_receipt.json'
    require(not backup.exists() and not receipt.exists(), 'Never overwrite an earlier artist snapshot.')
    report = {'schema': 'x.validation.latest-original-artist-snapshot/1', 'completed': False,
        'backup_verified': False, 'full_preservation_verified': False, 'source': source,
        'scope': 'Latest recoverable SaveCopy plus light original context/identity metadata only; full content inspection remains isolated-clone pending.',
        'protected_artist': protected, 'oracle': oracle_input, 'runtime_projection': projection,
        'runtime_version': list(cd.bl_info['version']), 'runtime_root': str(runtime_root),
        'pid': os.getpid(), 'external_process_filetime': external_process_filetime,
        'FILETIME_verified_by_script': False, 'candidate_imported_or_registered': False,
        'original_artist_saved': False, 'frame_evaluation_or_pose_edit_performed': False,
        'Unknown_never_promoted': True}
    save_report(receipt, report, first=True)
    try:
        with original_context(bpy, scene_name, rig_name) as (ctx, rig):
            before = snapshot(ctx, rig, bpy, ua)
            report.update(before=before, dirty_before=bool(bpy.data.is_dirty), phase='before_SaveCopy')
            save_report(receipt, report)
            require(bpy.ops.wm.save_as_mainfile.poll(), 'The actual original SaveCopy poll failed.')
            returned = bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=str(backup), copy=True, check_existing=False)
            report['save_result'] = sorted(returned)
            require(returned == {'FINISHED'} and backup.is_file(), 'The latest original SaveCopy did not finish.')
            report['backup'] = pin(backup, sha(backup))
            report['backup_verified'] = True
            after = snapshot(ctx, rig, bpy, ua)
            report.update(after=after, dirty_after=bool(bpy.data.is_dirty), phase='after_SaveCopy', actual_runtime_modules=checked)
            report['original_artist_disk_unchanged'] = pin(ARTIST, ARTIST_SHA) == protected
            require(before['context'] == after['context'], 'SaveCopy changed original filepath/Scene/Rig/mode/frame/selection.')
            known_fields = ('modifier_stacks', 'full_worklist', 'original_MainRig_session_and_rawRest')
            known = all(before[name]['known'] and after[name]['known'] for name in known_fields)
            require(all(before[name] == after[name] for name in known_fields if before[name]['known'] and after[name]['known']),
                    'A known original asset/worklist/session signature changed during SaveCopy.')
            require(before['actions'] == after['actions'] and before['active_action'] == after['active_action']
                    and before['active_action_slot'] == after['active_action_slot'], 'Original Action/slot content or identity changed.')
            require(before['skin_native_ids'] == after['skin_native_ids'], 'Original mesh/data/material/group/shape-key identities changed.')
            report['metadata_preservation_verified'] = bool(known and all(row['custom_properties']['known'] for row in after['actions']))
            report['full_preservation_verified'] = False
            report['completed'] = True  # This stage completes only the stated minimal backup scope.
            report['before_signature'] = digest(before)
            report['after_signature'] = digest(after)
            report['serialization_metadata_only'] = {'dirty_before': report['dirty_before'], 'dirty_after': report['dirty_after']}
    except Exception as error:
        report.update(completed=False, error=type(error).__name__ + ': ' + str(error))
    finally:
        report['actual_runtime_modules'] = checked
        final_disk = attempt(lambda: pin(ARTIST, ARTIST_SHA) == protected)
        report['protected_artist_final_readback'] = final_disk
        report['original_artist_disk_unchanged'] = bool(final_disk['known'] and final_disk.get('value') is True)
        report['completed'] = bool(report['completed'] and report['original_artist_disk_unchanged'])
        save_report(receipt, report)
    result = {'completed': report['completed'], 'backup_verified': report['backup_verified'],
        'full_preservation_verified': report['full_preservation_verified'], 'error': report.get('error'),
        'backup': report.get('backup'), 'receipt': pin(receipt, sha(receipt))}
    print('LATEST_ORIGINAL_ARTIST_SNAPSHOT ' + json.dumps(result, ensure_ascii=False))
    return result
