"""Explicit new-Action returns in an existing verified character workspace.

No original clip is invented. One local Action uses the workspace's editing rig
and model provenance, and publishes complete immutable FBX/metadata revisions.
Unity must collect and validate the return before any target purpose is chosen.
"""

import json
import math
import os
import os
from pathlib import Path
import uuid

from . import animation_link as links, animation_workspace as workspace


SCHEMA = 'randomrealm.animation-new-action/1'
FILE_NAME = 'character_animation_new.json'
PROVENANCE = ('workspaceId', 'projectId', 'targetGuid', 'targetHash',
              'baseControllerGuid', 'avatarGuid', 'avatarHash', 'modelFile', 'modelSha256',
              'workspaceTemplateLinkGuid')


def _composition(record):
    spec = record.get('composition')
    if spec is None:
        if record.get('editScope') != 'All':
            raise ValueError('A legacy new animation must return a complete playable Action.')
        return None
    from . import animation_composition_contract as contract
    spec = contract.validate(spec)
    if (record.get('editScope') != contract.SCOPE or not spec['editNewActionId']
            or uuid.UUID(spec['editWorkItemId']).hex != uuid.UUID(record['workItemId']).hex
            or uuid.UUID(spec['editNewActionId']).hex != uuid.UUID(record['newActionId']).hex):
        raise ValueError('The composition scope or editable B creation identity differs from the new Action.')
    return spec


def _bind_packet(packet, record):
    if str(packet.get('targetGuid', '')).lower() != record['targetGuid'].lower():
        raise ValueError('The B bind packet identifies a different character target.')
    roots = [bone for bone in packet['bones'] if bone['parent'] == -1]
    if (len(roots) != 1 or roots[0]['restSource'] != 'hierarchy'
            or roots[0].get('weighted') or roots[0]['name'] != roots[0].get('path')):
        raise ValueError('The B bind packet requires one explicit unweighted model object root.')
    name = roots[0]['name']
    if (not name or len(name) > 128 or name != name.strip()
            or any(ord(c) < 32 or ord(c) == 127 or c in '/\\' for c in name)
            or len({bone['name'] for bone in packet['bones']}) != len(packet['bones'])):
        raise ValueError('The B bind packet has an invalid root or ambiguous native bone names.')
    return name


def identity(record):
    if not isinstance(record, dict) or record.get('schema') != SCHEMA:
        raise ValueError('Unsupported new animation return schema.')
    try:
        action_id = uuid.UUID(record['newActionId']).hex
        item_id = uuid.UUID(record['workItemId']).hex
        uuid.UUID(record['workspaceId'])
        uuid.UUID(record['projectId'])
    except (KeyError, ValueError, AttributeError, TypeError) as exc:
        raise ValueError('The new animation lost its stable creation/workspace identity.') from exc
    for field, size in (('targetGuid', 32), ('targetHash', 32), ('baseControllerGuid', 32),
                        ('avatarGuid', 32), ('avatarHash', 32), ('modelSha256', 64),
                        ('workspaceTemplateLinkGuid', 32)):
        value = record.get(field)
        if (not isinstance(value, str) or len(value) != size
                or any(char not in '0123456789abcdefABCDEF' for char in value)):
            raise ValueError('New animation provenance is missing or invalid: ' + field)
    if not record.get('projectId') or not Path(record.get('modelFile', '')).is_absolute():
        raise ValueError('A new animation requires a verified project and absolute model path.')
    if not Path(record.get('workspaceManifest', '')).is_absolute():
        raise ValueError('A new animation requires its absolute Unity workspace path.')
    spec = _composition(record)
    scope = record['editScope']
    # A/config revisions may change explicitly, while mandatory B scope/model
    # identity remains exact. Full DTO revision is separately receipt-bound.
    composition_identity = ()
    if spec is not None:
        from . import animation_composition_contract as contract
        composition_identity = (contract.ROLE, contract.digest({key: spec[key] for key in (
            'compositionId', 'editWorkItemId', 'editNewActionId', 'mask', 'blendMode',
            'weight', 'humanRoles', 'allowedBonePaths', 'editableControlIds', 'sourceRestSha256')}))
    return (SCHEMA, action_id, item_id,
            *(record.get(field) for field in PROVENANCE),
            os.path.normcase(str(Path(record['workspaceManifest']).resolve())), scope,
            *composition_identity)


def load(path):
    path = Path(path).resolve()
    if path.name != FILE_NAME or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError('The new animation return is missing or exceeds 1 MiB.')
    record = json.loads(path.read_text(encoding='utf-8'))
    identity(record)
    if path.parent.name != uuid.UUID(record['newActionId']).hex or path.parent.parent.name != 'new_actions':
        raise ValueError('The new animation return is outside its creation folder.')
    expected = Path(record['workspaceManifest']).resolve().parent / 'new_actions' / path.parent.name
    if expected != path.parent:
        raise ValueError('The new animation return belongs to another workspace folder.')
    revision = record.get('revision')
    if type(revision) is not int or not 0 <= revision < 2**31:
        raise ValueError('The new animation revision is invalid.')
    return record


def validate(saved, item, catalog):
    record = load(item.manifest_path)
    if (identity(record) != identity(json.loads(item.link_identity))
            or item.new_action_id != uuid.UUID(record['newActionId']).hex
            or item.work_item_id != uuid.UUID(record['workItemId']).hex
            or any(record.get(field) != catalog.get(field) for field in PROVENANCE if field != 'targetHash')
            or str(Path(getattr(item, 'workspace_path', '') or saved.workspace_path).resolve())
                != str(Path(record['workspaceManifest']).resolve())):
        raise ValueError('The new Action belongs to a different workspace, model or character revision.')
    model = Path(record['modelFile'])
    if not model.is_file() or links._sha256(model) != record['modelSha256'].lower():
        raise ValueError('The new Action model changed or is missing; existing edits are retained.')
    if _composition(record) is not None:
        from . import animation_composition as composition
        if composition.item_spec(item) != _composition(record):
            raise ValueError('Refresh the explicit B composition configuration before export.')
        _bind_packet(composition._packet_for_item(item), record)
    return record


def _write(path, record, *, expected=None):
    identity(record)
    path = Path(path).resolve()
    if expected is not None:
        current = load(path)
        if current != expected:
            raise ValueError('The new Action publication changed; completed revisions were retained.')
    elif path.exists():
        raise ValueError('The new Action creation already exists; nothing was overwritten.')
    temporary = path.with_name('.' + uuid.uuid4().hex + '.new-action.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        if expected is not None and load(path) != expected:
            raise ValueError('The new Action publication changed during writing; retry explicitly.')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def publish(path, captured, result, *, blend_file, source_action,
            composition_metadata=None, composition_export=None):
    """Publish only an already-complete native export pair; source stays absent."""
    path = Path(path).resolve()
    identity(captured)
    directory = path.parent / 'revisions'
    fbx, metadata = Path(result['filepath']).resolve(), Path(result['metadata']).resolve()
    if (not fbx.is_relative_to(directory) or fbx.suffix.lower() != '.fbx'
            or metadata != fbx.with_suffix('.animation.json') or not fbx.is_file() or not metadata.is_file()):
        raise ValueError('The completed new Action does not belong to its immutable revision folder.')
    fbx_hash = links._sha256(fbx)
    if metadata.stat().st_size > 1024 * 1024:
        raise ValueError('The new Action metadata exceeds 1 MiB.')
    report = json.loads(metadata.read_text(encoding='utf-8'))
    duration = report.get('duration')
    if (fbx_hash != result.get('fbx_sha256') or report.get('fbx_sha256') != fbx_hash
            or report.get('action') != source_action or report.get('channels') != 'skeletal-only'
            or type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0):
        raise ValueError('The new Action FBX and metadata do not match.')
    if result.get('unsupported_channels'):
        raise ValueError('The new Action contains unsupported channels; its return was not registered.')
    spec = _composition(captured)
    if spec is not None:
        from .animation_worklist_collection import _composition_metadata, _composition_export
        item = type('NewIdentity', (), {'work_item_id': captured['workItemId'],
            'new_action_id': captured['newActionId'], 'new_animation': True})()
        expected_metadata = _composition_metadata(composition_metadata, item)
        expected_export = _composition_export(composition_export, expected_metadata, item)
        if (expected_metadata['composition'] != spec or report.get('composition') != spec
                or report.get('composition_export') != expected_export
                or expected_export['sourceAction'] != source_action):
            raise ValueError('The new B metadata differs from its frozen composition or isolated export proof.')
    elif report.get('composition') is not None or report.get('composition_export') is not None:
        raise ValueError('A legacy new Action cannot publish an unregistered composition.')
    model = Path(captured['modelFile'])
    if not model.is_file() or links._sha256(model) != captured['modelSha256'].lower():
        raise ValueError('The new Action model changed during export; its return was not registered.')
    merged = {**captured, 'revision': captured['revision'] + 1,
              'sourceAction': source_action, 'blendFile': blend_file,
              'fbxFile': str(fbx), 'fbxSha256': fbx_hash,
              'metadataFile': str(metadata), 'metadataSha256': links._sha256(metadata)}
    _write(path, merged, expected=captured)
    return {**result, 'link_manifest': str(path), 'new_action_id': captured['newActionId'],
            'revision': merged['revision']}


def register(context, *, composition=None, packet_path=None):
    if composition is not None:
        return _register_composition(context, composition, packet_path)
    if packet_path is not None:
        raise ValueError('An explicit B bind packet requires a composition contract.')
    import bpy
    from . import animation_worklist as worklist
    worklist._idle(context)
    saved = worklist.state(context)
    catalog = worklist._fresh_workspace(saved)
    rig = saved.rig
    action = rig.animation_data.action if rig and rig.animation_data else None
    if (rig is None or rig.library or rig.type != 'ARMATURE' or rig.name not in context.scene.objects
            or action is None or action.library):
        raise ValueError('Select a local new Action on this workspace\'s editing rig.')
    existing = next((item for item in saved.items if item.custom_action is action), None)
    if existing:
        if not getattr(existing, 'new_animation', False):
            raise ValueError('This Action already belongs to a source work item. Create a separate new Action first.')
        # Blender returns fresh RNA wrappers while iterating CollectionProperty;
        # Python object identity is not the persisted work-item identity.
        saved.active_index = next(index for index, item in enumerate(saved.items)
                                  if item.item_id == existing.item_id)
        return existing
    slot = worklist._slot(action)
    start, end = action.frame_range
    if not math.isfinite(start) or not math.isfinite(end) or end <= start:
        raise ValueError('The new Action needs a complete nonempty playable range.')
    template = next((clip for clip in catalog.get('clips', ()) if clip.get('linkManifest')
                     and not clip.get('needsRebuild')), None)
    if template is None:
        raise ValueError('Prepare one verified workspace model handoff before registering a new Action.')
    # This packet establishes the model's exported rig root, not a Source or
    # Original relationship for C. Do not guess from a renamed editing object.
    _record, _clip, _link, _packet, export_name, _model = worklist._prepared(saved, worklist._clip_key(template))
    action_id, item_id = uuid.uuid4().hex, uuid.uuid4().hex
    record = {**{field: catalog.get(field) for field in PROVENANCE},
              'schema': SCHEMA, 'newActionId': action_id, 'workItemId': item_id,
              'targetName': catalog.get('targetName', ''), 'sourceAction': action.name,
              'workspaceManifest': str(Path(saved.workspace_path).resolve()),
              'editScope': 'All', 'revision': 0}
    identity(record)
    model = Path(record['modelFile'])
    if not model.is_file() or links._sha256(model) != record['modelSha256'].lower():
        raise ValueError('The workspace model changed. Refresh the verified source before registering a new Action.')
    folder = Path(record['workspaceManifest']).parent / 'new_actions' / action_id
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / FILE_NAME
    _write(path, record)
    item = saved.items.add()
    item.item_id, item.work_item_id, item.clip_key = item_id, item_id, 'new:' + action_id
    item.new_animation, item.new_action_id = True, action_id
    item.name, item.rig, item.custom_action, item.custom_slot = action.name, rig, action, slot.handle
    item.manifest_path, item.link_identity = str(path), worklist._encoded(record)
    item.model_file, item.model_sha256 = record['modelFile'], record['modelSha256']
    item.export_rig_name = export_name
    item.side = 'CUSTOM'
    action.use_fake_user = True
    saved.active_index = len(saved.items) - 1
    saved.status, saved.has_error = 'Registered new Action. Sync returns a complete animation; Unity chooses its Use as.', False
    return item


def _register_composition(context, spec, packet_path):
    from . import animation_worklist as worklist, animation_worklist_target as target
    saved = worklist.state(context)
    rig = saved.rig
    action = rig.animation_data.action if rig and rig.animation_data else None
    if action is None or action.library:
        return _register_composition_record(context, spec, packet_path)
    keys = (*target._action_motion_keys(), links.PACKAGE_KEY, links.PACKAGE_HASH_KEY,
            'unity_sample_rate', 'unity_start_frame', 'unity_duration')
    prior = {key: action[key] for key in keys if key in action}
    prior_fake_user = action.use_fake_user
    try:
        return _register_composition_record(context, spec, packet_path)
    except Exception:
        for key in keys:
            if key in prior:
                action[key] = prior[key]
            elif key in action:
                del action[key]
        action.use_fake_user = prior_fake_user
        raise


def _local_b_timing(context, action, handle, scope, spec, exporter):
    """Seed a new local B from proved native timing; never rescale its curves."""
    if any(key in action for key in ('unity_sample_rate', 'unity_start_frame', 'unity_duration')):
        # Existing authored timing is validated by effective_fingerprint; partial
        # or contradictory metadata cannot silently become a new local baseline.
        return
    rate = context.scene.render.fps / context.scene.render.fps_base
    if not math.isfinite(rate) or rate != spec['fps']:
        raise ValueError('Set the new B Scene rate to its explicit composition fps; no curve rescale was applied.')
    if spec['timeMode'] == 'HoldPose':
        selected = [curve for curve in exporter._simple_action(action, handle)
                    if (curve.data_path, curve.array_index) in set(scope.channels)]
        if not selected or spec['sampleStart'] < 0 or spec['sampleEnd'] <= 0:
            raise ValueError('Hold B needs actual constant selected FK curves and a positive local interval.')
        for curve in selected:
            exporter.assert_constant_curve(curve)
        duration = spec['sampleEnd']
    else:
        start, end = action.frame_range
        if (not all(type(v) in (int, float) and math.isfinite(v) for v in (start, end))
                or start != 1. or end <= start):
            raise ValueError('Moving local B must start at frame 1 with a positive native range; no frame shift was applied.')
        duration = (end - start) / rate
    action['unity_sample_rate'], action['unity_start_frame'], action['unity_duration'] = rate, 1., duration


def _register_composition_record(context, spec, packet_path):
    """Register real B IDs from its explicit contract; A remains a reference."""
    from . import animation_worklist as worklist, animation_composition as composition
    from . import animation_composition_contract as contract, unity_animation as ua
    from . import animation_composition_export as exporter, animation_worklist_target as target
    worklist._idle(context)
    spec = contract.validate(spec)
    if not spec['editNewActionId'] or not packet_path:
        raise ValueError('Register B requires its actual new Action identity and prepared B bind packet.')
    saved = worklist.state(context)
    catalog, route = composition._library_state(context)
    rig = saved.rig
    action = rig.animation_data.action if rig and rig.animation_data else None
    if (rig is None or rig.library or rig.type != 'ARMATURE' or rig.name not in context.scene.objects
            or action is None or action.library or composition.active(rig)):
        raise ValueError('Select a local B Action on the editing rig and finish its active composition session first.')
    existing = next((row for row in saved.items if row.custom_action is action), None)
    if existing is not None:
        if not existing.new_animation or composition.item_spec(existing) != spec:
            raise ValueError('This Action already belongs to another work item; create a separate B Action.')
        saved.active_index = next(index for index, row in enumerate(saved.items)
                                  if row.item_id == existing.item_id)
        return existing
    action_id, item_id = uuid.UUID(spec['editNewActionId']).hex, uuid.UUID(spec['editWorkItemId']).hex
    if any(row.work_item_id == item_id or getattr(row, 'new_action_id', '') == action_id for row in saved.items):
        raise ValueError('The explicit B creation identity is already registered to another Action.')
    slot = worklist._slot(action)
    packet = ua.load_package(packet_path)
    scope = exporter.resolve_scope(context, rig, spec, packet)
    _local_b_timing(context, action, slot.handle, scope, spec, exporter)
    proof = exporter.effective_fingerprint(action, slot.handle, scope, spec)
    if not proof['fingerprint_known']:
        raise ValueError('B export inputs are unproved: ' + proof['proof_reason'])
    record = {**{field: catalog.get(field) for field in PROVENANCE},
        'schema': SCHEMA, 'newActionId': action_id, 'workItemId': item_id,
        'targetName': catalog.get('targetName', ''), 'sourceAction': action.name,
        'workspaceManifest': str(Path(route.workspace_path).resolve()),
        'editScope': contract.SCOPE, 'composition': spec, 'revision': 0}
    identity(record)
    export_name = _bind_packet(packet, record)
    model = Path(record['modelFile'])
    if not model.is_file() or links._sha256(model) != record['modelSha256'].lower():
        raise ValueError('The explicit composition model changed; B was not registered.')
    if packet.get('_sha256') != links._sha256(Path(packet_path)):
        raise ValueError('The prepared B packet changed during registration.')
    target.attach_action_motion_data(rig, action)
    # No Source relationship is invented. Package refs identify B's bind mapping.
    folder = Path(record['workspaceManifest']).parent / 'new_actions' / action_id
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / FILE_NAME
    item = None
    keys = (links.PACKAGE_KEY, links.PACKAGE_HASH_KEY)
    prior = {key: action[key] for key in keys if key in action}
    prior_fake_user = action.use_fake_user
    try:
        _write(path, record)
        item = saved.items.add()
        item.item_id, item.work_item_id, item.clip_key = item_id, item_id, 'new:' + action_id
        item.new_animation, item.new_action_id = True, action_id
        item.name, item.rig, item.custom_action, item.custom_slot = action.name, rig, action, slot.handle
        item.manifest_path, item.link_identity = str(path), worklist._encoded(record)
        item.model_file, item.model_sha256 = record['modelFile'], record['modelSha256']
        item.export_rig_name = export_name
        item.side = 'CUSTOM'
        action[links.PACKAGE_KEY] = str(Path(packet_path).resolve())
        action[links.PACKAGE_HASH_KEY] = packet['_sha256']
        composition.bind_item(item, record, workspace_path=route.workspace_path,
                              workspace_identity=route.workspace_identity)
        action.use_fake_user = True
        saved.active_index = len(saved.items) - 1
        saved.status, saved.has_error = 'Registered B. Sync returns isolated Upper Body motion with its composition metadata.', False
        return item
    except Exception:
        for key in keys:
            if key in prior:
                action[key] = prior[key]
            elif key in action:
                del action[key]
        action.use_fake_user = prior_fake_user
        if item is not None:
            for index, row in enumerate(saved.items):
                if row.item_id == item_id:
                    saved.items.remove(index)
                    break
        path.unlink(missing_ok=True)
        folder.rmdir()
        raise


def _destination(directory):
    # Work/new-Action IDs remain full UUIDs. Only these immutable file labels
    # are compact so Windows' temporary publication pair stays below MAX_PATH.
    for _attempt in range(8):
        candidate = directory / ('a-' + uuid.uuid4().hex[:16] + '.fbx')
        metadata = candidate.with_suffix('.animation.json')
        temporary_metadata = directory / '.cdesigner-action-xxxxxxxx' / metadata.name
        if os.name == 'nt' and len(str(temporary_metadata).encode('utf-16-le')) // 2 >= 260:
            raise ValueError('The animation exchange path is too long for complete Windows publication. Use a shorter workspace path.')
        if not candidate.exists() and not metadata.exists():
            return candidate
    raise ValueError('Could not reserve a unique immutable Action filename; retry explicitly.')


def sync(context, item, *, collection=False, collection_proof=None):
    if _composition(json.loads(item.link_identity)) is not None:
        from . import animation_composition as composition
        return composition.begin_sync(context, item, collection=collection,
                                      collection_proof=collection_proof)
    import bpy
    from . import animation_worklist as worklist, animation_export, animation
    from .animation_worklist_collection import export_implementation, item_fingerprint, unchanged_proof
    saved = worklist.state(context)
    captured = validate(saved, item, worklist._fresh_workspace(saved))
    proof, implementation = item_fingerprint(context, item), export_implementation()
    if collection_proof is not None and (not collection or not collection_proof(proof)):
        raise ValueError('The new Action export lost its collection owner.')
    if unchanged_proof(item, captured, implementation, proof):
        raise ValueError('This new Action matches its last successful publication; no duplicate was exported.')
    directory = Path(item.manifest_path).parent / 'revisions'
    directory.mkdir(parents=True, exist_ok=True)
    action, rig = item.custom_action, item.rig
    start, end = map(float, action.frame_range)
    rate = action.get('unity_sample_rate', context.scene.render.fps / context.scene.render.fps_base)
    name = action.name
    blend_file = str(Path(bpy.data.filepath).resolve()) if bpy.data.filepath else ''

    def completed(_job, result):
        if item.custom_action is not action or item.rig is not rig:
            raise ValueError('The new Action work item changed during export; its return was not published.')
        validate(saved, item, worklist._fresh_workspace(saved))
        return publish(item.manifest_path, captured, result, blend_file=blend_file, source_action=name)

    lock = links._LinkLock(Path(item.manifest_path))
    try:
        if load(item.manifest_path) != captured:
            raise ValueError('The new Action publication changed before launch; retry explicitly.')
        destination = _destination(directory)
        job = animation_export.begin_export(context, rig, action, destination, frame_start=start,
            frame_end=end, loop=bool(action.get('unity_loop_time', False)), sample_rate=rate,
            export_rig_name=item.export_rig_name)
    except Exception:
        lock.release()
        raise
    job['_publish_callback'], job['_dispose_callback'] = completed, lock.release
    job['_worklist_scene'], job['_worklist_item_id'] = context.scene, item.item_id
    job['_worklist_fingerprint'], job['_worklist_export_implementation'] = proof, implementation
    animation._export_window_manager = context.window_manager
    bpy.app.timers.register(animation._poll_action_export, first_interval=.25)
    saved.status, saved.has_error = 'Syncing new Action ' + item.name + '. Collect Updates in Unity to preview.', False
    return job
