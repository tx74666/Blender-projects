"""Explicit serial collection operations; drawing never scans or starts work.

Only the owning window/scene may advance a batch. A native export must publish
and dispose before another Action is activated. Receipts describe the frozen
successful publication, never whatever the artist edited while it ran.
"""

import json
import hashlib
from pathlib import Path

import bpy

from . import animation_link as links, animation_worklist as worklist
from . import animation_workspace as workspace
from .animation_worklist_fingerprint import SCHEMA as FINGERPRINT_SCHEMA, fingerprint_native
from .animation_worklist_queue import ADD, SYNC, QueueItem, SerialQueue


RECEIPT_SCHEMA = 'character-designer.animation-worklist-receipt/1'
SOURCE_BASELINE_SCHEMA = 'character-designer.animation-source-baseline/1'
_batch = None


def export_implementation():
    """Explicit scan/launch IO only; receipts also bind the export semantics."""
    root = Path(__file__).resolve().parent
    result = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in (
        'animation_export.py', 'animation_export_worker.py', 'unity_export_worker.py',
        'animation_worklist_fingerprint.py')}
    # Approved releases before Dress export integration have neither optional
    # guard. Bind their absence explicitly; adding/removing either invalidates
    # receipts, while a partially installed pair is never a valid implementation.
    guards = ('dress_export_snapshot.py', 'dress_export_guard.py')
    present = [(root / name).is_file() for name in guards]
    if any(present) and not all(present):
        raise ValueError('The optional Dress export guard pair is incomplete.')
    result.update({name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                   if exists else 'absent' for name, exists in zip(guards, present)})
    return result


def item_fingerprint(context, item):
    proof = fingerprint_native(item.custom_action, item.rig, context.scene, item.custom_slot)
    from . import hair_wiggle_adapter
    if hair_wiggle_adapter.status(context).get('active'):
        # begin_export stops transient Hair before freezing its snapshot. Until
        # that happens, this current pose is not the snapshot's dependency proof.
        proof = {**proof, 'fingerprint_known': False, 'fingerprint': '',
                 'proof_reason': 'Active Hair preview changes snapshot inputs; unchanged is unproven.'}
    return proof


def remember_source_baseline(context, item):
    """Freeze the prepared Source content, not a fabricated export receipt.

    This is called once during Add. Never seed an older row during Scan: its rig
    inputs may already be edited. Unknown dependencies remain explicitly Unknown.
    """
    proof = fingerprint_native(item.source_action, item.rig, context.scene, item.source_slot)
    from . import hair_wiggle_adapter
    if hair_wiggle_adapter.status(context).get('active'):
        proof = {**proof, 'fingerprint_known': False, 'fingerprint': '',
                 'proof_reason': 'Active Hair preview changes prepared inputs; unchanged is unproven.'}
    receipt = {'schema': SOURCE_BASELINE_SCHEMA, 'proof': proof,
               'workItemId': getattr(item, 'work_item_id', ''),
               'identity': list(links._identity(json.loads(item.link_identity))),
               'source_hash': item.source_hash, 'implementation': export_implementation()}
    item.source_baseline_receipt = worklist._encoded(receipt)


def _valid_proof(proof):
    return (isinstance(proof, dict) and proof.get('schema') == FINGERPRINT_SCHEMA
            and type(proof.get('fingerprint_known')) is bool
            and (not proof['fingerprint_known'] or isinstance(proof.get('fingerprint'), str)
                 and len(proof['fingerprint']) == 64
                 and all(char in '0123456789abcdef' for char in proof['fingerprint'])))


def _source_baseline(item, link, implementation):
    try:
        receipt = json.loads(getattr(item, 'source_baseline_receipt', ''))
        if (not isinstance(receipt, dict) or receipt.get('schema') != SOURCE_BASELINE_SCHEMA
                or not _valid_proof(receipt.get('proof'))
                or receipt.get('workItemId', '') != workspace.work_item_id(link)
                or receipt.get('identity') != list(links._identity(link))
                or receipt.get('source_hash') != item.source_hash
                or receipt.get('implementation') != implementation):
            return None
        return receipt
    except (AttributeError, TypeError, ValueError, OSError):
        return None


def comparison_receipt(item, link, implementation):
    # A failed/tampered later publication proof must not fall back to the
    # prepared Source and mistakenly treat the prior edits as unchanged.
    if getattr(item, 'last_synced_receipt', ''):
        return _receipt(item, link, implementation)
    return _source_baseline(item, link, implementation)


def unchanged_proof(item, link, implementation, proof):
    receipt = comparison_receipt(item, link, implementation)
    previous = receipt.get('proof', {}) if receipt else {}
    return (proof.get('fingerprint_known') is True and previous.get('fingerprint_known') is True
            and proof.get('fingerprint') == previous.get('fingerprint'))


def running():
    return _batch is not None and _batch['queue'].busy


def _status(saved, message, error=False):
    saved.status, saved.collection_status, saved.has_error = message, message, error
    saved.collection_feedback = True


def _redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {'VIEW_3D', 'DOPESHEET_EDITOR', 'GRAPH_EDITOR'}:
                area.tag_redraw()


def _current_link(saved, item, catalog):
    worklist._check_baseline(item)
    worklist._item(saved, item.item_id)
    if item.custom_action is None or item.custom_action.library is not None:
        raise ValueError('The local editable Custom Action is missing.')
    worklist._slot(item.custom_action, item.custom_slot)
    if getattr(item, 'new_animation', False):
        from .animation_worklist_new import validate
        return validate(saved, item, catalog)
    clip = next((entry for entry in catalog['clips']
                 if worklist._clip_key(entry) == item.clip_key), None)
    if (clip is None or clip.get('needsRebuild') or not clip.get('linkManifest')
            or Path(clip['linkManifest']).resolve() != Path(item.manifest_path).resolve()):
        raise ValueError('Prepare this Controller slot in Unity; existing Custom edits are kept.')
    link = links.load_link(item.manifest_path)
    worklist._validate_route(saved, clip, link, item)
    if links._identity(link) != links._identity(json.loads(item.link_identity)):
        raise ValueError('This Link was rebuilt. Keep existing edits and use a separate fresh worklist.')
    return link


def _publication(link):
    """Exact already-verified Link outputs; display names have no authority."""
    return {field: link.get(field) for field in (
        'revision', 'fbxFile', 'fbxSha256', 'metadataFile', 'metadataSha256')}


def _identity(item, link):
    if getattr(item, 'new_animation', False):
        from .animation_worklist_new import identity
        return identity(link)
    return links._identity(link)


def _receipt(item, link, implementation):
    try:
        receipt = json.loads(item.last_synced_receipt)
        proof = receipt.get('proof') if isinstance(receipt, dict) else None
        if (not isinstance(proof, dict) or proof.get('schema') != FINGERPRINT_SCHEMA
                or type(proof.get('fingerprint_known')) is not bool
                or (proof['fingerprint_known'] and (not isinstance(proof.get('fingerprint'), str)
                    or len(proof['fingerprint']) != 64
                    or any(char not in '0123456789abcdef' for char in proof['fingerprint'])))):
            return None
        if (receipt.get('schema') != RECEIPT_SCHEMA
                or receipt.get('workItemId', '') != workspace.work_item_id(link)
                or receipt.get('identity') != list(_identity(item, link))
                or receipt.get('publication') != _publication(link)
                or receipt.get('implementation') != implementation
                or receipt.get('source_hash') != item.source_hash):
            return None
        for file_field, hash_field in (('fbxFile', 'fbxSha256'),
                                       ('metadataFile', 'metadataSha256')):
            path, digest = link.get(file_field), link.get(hash_field)
            if not path or not digest or links._sha256(Path(path)) != digest:
                return None
        return receipt
    except (AttributeError, TypeError, ValueError, OSError):
        return None


def scan_changes(context):
    """Read selected-slot content/dependencies once, without activating Actions."""
    worklist._idle(context)
    saved = worklist.state(context)
    catalog = worklist._fresh_workspace(saved)
    implementation = export_implementation()
    counts = dict.fromkeys(('CHANGED', 'UNCHANGED', 'UNKNOWN', 'BLOCKED'), 0)
    for item in saved.items:
        old_state = item.scan_state
        try:
            link = _current_link(saved, item, catalog)
            proof = item_fingerprint(context, item)
            receipt = comparison_receipt(item, link, implementation)
            old_proof = receipt.get('proof', {}) if receipt else {}
            if not proof['fingerprint_known']:
                state, reason = 'UNKNOWN', proof['proof_reason']
            elif not receipt and getattr(item, 'new_animation', False) and link.get('revision') == 0:
                state, reason = 'CHANGED', 'New complete Action; no original version or return exists yet.'
            elif not receipt or not old_proof.get('fingerprint_known'):
                state, reason = 'UNKNOWN', 'No complete preparation or successful export proof for this comparison.'
            elif proof['fingerprint'] == old_proof.get('fingerprint'):
                state, reason = 'UNCHANGED', 'Matches its prepared Source or last successful publication, including timing and rig inputs.'
            else:
                state, reason = 'CHANGED', 'Content, export timing or necessary rig inputs changed since successful Sync.'
        except (ValueError, RuntimeError, OSError, ReferenceError, TypeError) as exc:
            state, reason = 'BLOCKED', str(exc)
        item.scan_state, item.scan_reason = state, reason
        if state in {'UNCHANGED', 'BLOCKED'}:
            item.sync_selected = False
        elif state == 'UNKNOWN' and old_state != 'UNKNOWN':
            item.sync_selected = False
        elif state == 'CHANGED' and old_state in {'NOT_SCANNED', 'UNCHANGED'}:
            item.sync_selected = True
        # Unknown is never selected automatically. Preserve only an explicit
        # artist selection, including the operator's mandatory rescan.
        counts[state] += 1
    saved.scan_completed = True
    _status(saved, 'Scan: ' + ', '.join(str(counts[key]) + ' ' + key.title() for key in counts) + '.')
    _redraw()
    return counts


def _begin(context, mode, entries):
    global _batch
    worklist._idle(context)
    if context.window is None:
        raise ValueError('Run collection operations in an owning Blender window.')
    queue = SerialQueue(mode, entries)
    if not queue.busy:
        _status(worklist.state(context), 'No selected work to perform.')
        return queue
    batch = {'queue': queue, 'window': context.window, 'scene': context.scene, 'job': None}
    _batch = batch
    try:
        bpy.app.timers.register(_poll_collection, first_interval=0.1)
    except Exception:
        if _batch is batch:
            _batch = None
        raise
    _status(worklist.state(context), ('Adding' if mode == ADD else 'Syncing') +
            ' collection: 0 / ' + str(queue.total) + '.')
    _redraw()
    return queue


def begin_add_ready(context):
    worklist._idle(context)
    saved = worklist.state(context)
    catalog = worklist._fresh_workspace(saved)
    request = workspace.prepare_request(catalog)
    requested = set(request[1]) if request is not None else None
    included = {item.clip_key for item in saved.items}
    entries = [QueueItem(worklist._clip_key(clip)) for clip in catalog['clips']
               if (requested is None or workspace.work_item_id(clip) in requested)
               and worklist._clip_key(clip) not in included and not clip.get('needsRebuild')
               and clip.get('linkManifest') and Path(clip['linkManifest']).is_file()]
    queue = _begin(context, ADD, entries)
    if not queue.busy:
        return queue
    _batch['prepare_request'] = request
    # Freeze every selected row's route before the first native import. A later
    # request/source/slot change stops the remainder, retaining completed rows.
    _batch['add_routes'] = {worklist._clip_key(clip): (workspace.route_identity(clip), clip['linkManifest'])
                            for clip in catalog['clips'] if worklist._clip_key(clip) in queue.remaining_keys}
    return queue


def begin_sync_changed(context, *, changed_only=False):
    saved = worklist.state(context)
    if not saved.scan_completed:
        raise ValueError('Scan Changes first; Unknown entries require explicit selection.')
    entries = [QueueItem(item.item_id) for item in saved.items
               if (item.scan_state == 'CHANGED' if changed_only else
                   item.sync_selected and item.scan_state in {'CHANGED', 'UNKNOWN'})]
    queue = _begin(context, SYNC, entries)
    if changed_only:
        unresolved = sum(item.scan_state in {'UNKNOWN', 'BLOCKED'} for item in saved.items)
        notice = (str(unresolved) + ' animation(s) need attention and were kept locally.'
                  if unresolved else '')
        if queue.busy:
            _batch['changed_only'] = True
            _batch['skipped_notice'] = notice
        else:
            _status(saved, 'Nothing ready to export. ' + notice if notice else 'No changes to export.')
    return queue


def _record_launch_proof(batch, attempt, item, link, proof):
    if batch.get('changed_only'):
        receipt = comparison_receipt(item, link, export_implementation())
        previous = receipt.get('proof', {}) if receipt else {}
        first_export = getattr(item, 'new_animation', False) and link.get('revision') == 0
        if (not _valid_proof(proof) or proof.get('fingerprint_known') is not True
                or not first_export and previous.get('fingerprint_known') is not True):
            raise ValueError('The change comparison is no longer complete; this animation was kept locally.')
        if not first_export and proof['fingerprint'] == previous.get('fingerprint'):
            raise ValueError('This animation is unchanged; no duplicate was exported.')
    return batch['queue'].record_fingerprint(attempt.token, proof)


def _start(context, batch, attempt):
    queue = batch['queue']
    if queue.mode == ADD:
        saved = worklist.state(context)
        catalog = worklist._fresh_workspace(saved)
        if workspace.prepare_request(catalog) != batch['prepare_request']:
            raise ValueError('The Unity preparation request changed; completed Custom work was kept.')
        clip = next((clip for clip in catalog['clips'] if worklist._clip_key(clip) == attempt.key), None)
        if clip is None or (workspace.route_identity(clip), clip.get('linkManifest')) != batch['add_routes'][attempt.key]:
            raise ValueError('A requested work-item source or destination changed; its import was stopped.')
        item = worklist.add(context, attempt.key, activate_new=False, _collection=True)
        # The first import owns a new independent scene. Subsequent imports use
        # that one rig and leave the artist's active Action untouched.
        batch['scene'] = context.window.scene
        queue.complete(attempt.token, success=True, result={'item_id': item.item_id}, published=True)
    else:
        saved = worklist.state(context)
        item = worklist._item(saved, attempt.key)
        link = _current_link(saved, item, worklist._fresh_workspace(saved))
        worklist.activate(context, attempt.key, 'CUSTOM', _collection=True)
        # Sync records its one complete proof before it starts the worker. The
        # queue and receipt use that same snapshot within this event-loop turn.
        job = worklist.sync(context, _collection=True,
            _collection_proof=lambda proof: _record_launch_proof(batch, attempt, item, link, proof))
        job['_collection_token'] = attempt.token
        batch['job'] = job


def _finish(batch):
    global _batch
    queue = batch['queue']
    message = (('Added' if queue.mode == ADD else 'Synced') + ' ' + str(len(queue.successes)) +
               ' / ' + str(queue.total) + '; ' + queue.state.title() + '.')
    if queue.failure:
        message += ' ' + queue.failure.message
    if queue.cancel_error:
        message += ' ' + queue.cancel_error
    elif queue.cancel_message:
        message += ' ' + queue.cancel_message
    if batch.get('skipped_notice'):
        message += ' ' + batch['skipped_notice']
    try:
        _status(batch['scene'].character_designer_animation_worklist, message,
                bool(queue.failure or queue.cancel_error))
    except ReferenceError:
        pass
    if _batch is batch:
        _batch = None
    _redraw()


def _poll_collection():
    batch = _batch
    if batch is None:
        return None
    queue = batch['queue']
    if not queue.busy:
        _finish(batch)
        return None
    try:
        window = batch['window']
        if window not in tuple(bpy.context.window_manager.windows) or window.scene != batch['scene']:
            cancel(message='The owning window or scene changed; completed items were kept.')
        elif batch['job'] is not None:
            from . import animation_export
            if animation_export.active_job() is None:
                # Someone disposed this worker outside its completion adapter.
                # No result means no receipt and no successful publication claim.
                export_finished(batch['job'], error='The owned export stopped without a publication result.')
        elif queue.running is None:
            from .animation import _link_idle
            if _link_idle(include_collection=False):
                with bpy.context.temp_override(window=window):
                    queue.tick(lambda attempt: _start(bpy.context, batch, attempt))
        if not queue.busy:
            _finish(batch)
            return None
        _status(batch['scene'].character_designer_animation_worklist,
                ('Adding' if queue.mode == ADD else 'Syncing') + ' collection: ' +
                str(len(queue.successes)) + ' / ' + str(queue.total) + '.')
    except (ReferenceError, RuntimeError, ValueError) as exc:
        cancel(message=str(exc))
        if not queue.busy:
            _finish(batch)
            return None
    _redraw()
    return 0.25


def export_finished(job, result=None, error=''):
    """Called only after native publication/disposal (or confirmed cancellation)."""
    scene = job.get('_worklist_scene')
    receipt_error = ''
    batch = _batch
    token = job.get('_collection_token')
    if token is not None:
        attempt = batch['queue'].running if batch is not None else None
        if (batch is None or batch['job'] is not job or attempt is None or attempt.token != token):
            return 'Ignored stale collection completion; no publication proof was recorded.'
    if result is not None and scene is not None:
        try:
            saved = scene.character_designer_animation_worklist
            item = worklist._item(saved, job['_worklist_item_id'])
            if getattr(item, 'new_animation', False):
                from .animation_worklist_new import load
                link = load(item.manifest_path)
            else:
                link = links.load_link(item.manifest_path)
            if (_identity(item, link) != _identity(item, json.loads(item.link_identity))
                    or str(Path(result['link_manifest']).resolve()) != str(Path(item.manifest_path).resolve())
                    or result['revision'] != link.get('revision')
                    or result['fbx_sha256'] != link.get('fbxSha256')
                    or str(Path(result['filepath']).resolve()) != str(Path(link['fbxFile']).resolve())):
                raise ValueError('Published result differs from this worklist Link; no unchanged proof was recorded.')
            proof = job['_worklist_fingerprint']
            if result.get('unsupported_channels'):
                proof = {**proof, 'fingerprint_known': False, 'fingerprint': '',
                         'proof_reason': 'Export omitted unsupported channels; unchanged is unproven.'}
            receipt = {'schema': RECEIPT_SCHEMA, 'proof': proof,
                       'workItemId': workspace.work_item_id(link),
                       'identity': list(_identity(item, link)), 'publication': _publication(link),
                       'implementation': job['_worklist_export_implementation'],
                       'source_hash': item.source_hash}
            item.last_synced_receipt = worklist._encoded(receipt)
            item.scan_state, item.scan_reason = 'NOT_SCANNED', 'Scan to compare current edits with the published snapshot.'
            item.sync_selected, saved.scan_completed = False, False
        except (ValueError, RuntimeError, OSError, ReferenceError, TypeError, KeyError) as exc:
            receipt_error = str(exc)
    if batch is not None and batch['job'] is job:
        accepted = batch['queue'].complete(job['_collection_token'], success=result is not None,
                                          result=result, message=error or receipt_error, published=result is not None)
        if not accepted:
            return 'Ignored stale collection completion.'
        batch['job'] = None
        if receipt_error:
            # Publication is real and remains counted, but fail closed on
            # bookkeeping and do not start another Action.
            batch['queue'].cancel()
            try:
                _status(scene.character_designer_animation_worklist, receipt_error, True)
            except ReferenceError:
                pass
    return receipt_error


def cancel(_context=None, *, message='Collection cancelled; completed items were kept.'):
    batch = _batch
    if batch is None:
        return False

    def cancel_running(attempt):
        from . import animation, animation_export
        job = batch['job']
        if job is not None:
            if animation_export.active_job() is not job:
                raise RuntimeError('The collection lost its native worker owner; wait for completion.')
            animation_export.cancel_export(job)
            if bpy.app.timers.is_registered(animation._poll_action_export):
                bpy.app.timers.unregister(animation._poll_action_export)
            animation._export_window_manager = None
            batch['job'] = None
        batch['queue'].acknowledge_cancel(attempt.token, message=message)

    return batch['queue'].cancel(cancel_running)


def stop():
    """Refresh/load cleanup: no saved queues, surprise launches or shared kills."""
    batch = _batch
    if batch is None:
        return
    cancel(message='Collection stopped for reload; completed items were kept.')
    if not batch['queue'].busy:
        if bpy.app.timers.is_registered(_poll_collection):
            bpy.app.timers.unregister(_poll_collection)
        _finish(batch)
