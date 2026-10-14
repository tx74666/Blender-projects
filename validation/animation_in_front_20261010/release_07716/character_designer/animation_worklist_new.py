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
    if record.get('editScope') != 'All':
        raise ValueError('A new animation must return a complete playable Action.')
    return (SCHEMA, action_id, item_id,
            *(record.get(field) for field in PROVENANCE),
            os.path.normcase(str(Path(record['workspaceManifest']).resolve())), 'All')


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
            or str(Path(saved.workspace_path).resolve()) != str(Path(record['workspaceManifest']).resolve())):
        raise ValueError('The new Action belongs to a different workspace, model or character revision.')
    model = Path(record['modelFile'])
    if not model.is_file() or links._sha256(model) != record['modelSha256'].lower():
        raise ValueError('The new Action model changed or is missing; existing edits are retained.')
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


def publish(path, captured, result, *, blend_file, source_action):
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


def register(context):
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
