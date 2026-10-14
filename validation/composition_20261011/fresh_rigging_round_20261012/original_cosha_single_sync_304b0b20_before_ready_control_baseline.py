"""Source preparation: one public Sync of a completed original-clone control round.

No execution is authorized by this file. A separate fresh headful plus one-worker
resource scope is mandatory. Never open the live artist, recreate the Rig, author
new inputs, Sync old rows, invoke a batch, deploy a release or apply in Unity.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback


DONOR_SHA = '0854aa755b0e50438d0be054f885aa57f68f67862e8de97f6e3b86f56f8f325b'
RESOURCE_SCOPE = 'original-cosha-single-manual-sync'


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared-report', 'protected-artist', 'source-freeze', 'package-manifest',
                 'latest-snapshot-receipt', 'latest-seed', 'preservation-oracle',
                 'control-report', 'control-harness', 'resource-token-file', 'source-ready-index'):
        parser.add_argument('--' + name, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    for name in ('script-sha256', 'unity-project-root', 'output-root', 'profile-root'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--confirm-isolated-headful', required=True, action='store_true')
    parser.add_argument('--confirm-one-manual-sync-worker', required=True, action='store_true')
    parser.add_argument('--quit-on-completion', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    args.reference_packet = args.reference_packet_sha256 = None
    return args


def main():
    args = arguments()
    own_path, harness = Path(__file__).resolve(), Path(args.control_harness).resolve()
    def raw_sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if (harness.parent != own_path.parent or harness.name != 'original_cosha_control_round.py'
            or raw_sha(harness) != args.control_harness_sha256
            or raw_sha(own_path) != args.script_sha256):
        raise RuntimeError('Use the exact reviewed original-clone successor scripts, never the factory control harness.')
    spec = importlib.util.spec_from_file_location('original_control_for_single_sync', harness)
    control_helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(control_helper)
    helper = control_helper.base
    require, pin, sha, document, digest = helper.require, helper.pin, helper.sha, helper.document, helper.digest
    physical_sha = args.script_sha256
    resource_pin = pin(args.resource_token_file, args.resource_token_file_sha256)
    ready_pin = pin(args.source_ready_index, args.source_ready_index_sha256)
    resource, ready = document(resource_pin['path']), document(ready_pin['path'])
    start = datetime.fromisoformat(resource['actual_start_utc'].replace('Z', '+00:00'))
    age = (datetime.now(timezone.utc) - start).total_seconds()
    require(start.tzinfo is not None and start.utcoffset().total_seconds() == 0
            and 0 <= age <= 900 and resource['schema'] == 'x.validation.fresh-native-resource-start/1'
            and resource['status'] == 'ACTUAL_START' and resource['scope'] == RESOURCE_SCOPE
            and isinstance(resource['token'], str) and resource['token']
            and resource['owner_thread'] == '01a12751-d08f-7630-b790-18db26fe3186'
            and resource['parent_thread'] == '01a12305-aada-7273-b72c-54a41aad77e4'
            and type(resource['native_process_limit']) is int and resource['native_process_limit'] == 2
            and resource['worker_allowed'] is True and resource['ready_index_sha256'] == ready_pin['sha256'],
            'Require a fresh original single-Sync START allowing one owned headful process plus one owned worker; no old control grant.')
    require(ready['schema'] == 'x.validation.original-cosha-source-ready/1'
            and ready['status'] == 'SOURCE_READY_FRESH_NATIVE_SCOPE_PENDING'
            and ready['source_only'] is True and ready['native_execution_performed'] is False,
            'Require the separately reviewed complete original-route Source index.')
    for label, path, expected in (('control_harness', harness, args.control_harness_sha256),
            ('single_sync_harness', own_path, physical_sha), ('source_freeze', args.source_freeze, args.source_freeze_sha256),
            ('package_manifest', args.package_manifest, args.package_manifest_sha256),
            ('latest_snapshot_receipt', args.latest_snapshot_receipt, args.latest_snapshot_receipt_sha256)):
        require(ready['pins'][label] == pin(path, expected), 'The fresh resource Source index differs: ' + label)

    class SyncRound(control_helper.OriginalRound):
        def __init__(self, args):
            admitted = copy.copy(args)
            admitted.script_sha256 = args.control_harness_sha256
            super().__init__(admitted)
            self.args = args
            self.pins.update(script=pin(own_path, physical_sha), control_harness=pin(harness, args.control_harness_sha256),
                control_report=pin(args.control_report, args.control_report_sha256),
                resource_token=resource_pin, source_ready_index=ready_pin,
                reviewed_factory_Sync_pattern=pin(own_path.parent / 'new_official_cosha_single_sync.py', DONOR_SHA))
            self.control = document(args.control_report)
            require(self.control['schema'] == 'x.validation.original-cosha-control-save/1'
                and self.control['completed'] is True and self.control['native_execution_performed'] is True
                and self.control['original_clone_Rig_acceptance'] is True
                and self.control['original_Rig_acceptance'] is False
                and self.control['live_original_integration_verified'] is False
                and self.control['artist_writes_performed'] is False
                and self.control['full_original_asset_preservation_verified'] is True
                and self.control['original_recovery_Restore_readopt_verified'] is True
                and self.control['formal_public_Attach_Activate_verified'] is True
                and self.control['explicit_input_save_verified'] is True
                and self.control['save_reopen_verified'] is True and self.control['real_Undo_Redo_verified'] is True
                and self.control['automatic_saved_cache_before_manual_Activate'] is True
                and self.control['Sync_performed'] is False and self.control['worker_performed'] is False
                and self.control['workItemId'] == self.work_id and not self.control.get('failure_phase'),
                'Consume actual complete original-clone control/asset/Restore/reopen/Undo proof, never factory or failed/Source-only results.')
            for label in ('prepared_report', 'protected_artist', 'source_freeze', 'package_manifest',
                    'latest_snapshot_receipt', 'latest_seed', 'preservation_oracle', 'workspace', 'link',
                    'packet', 'model', 'weapon_context', 'weapon_model'):
                require(self.control['source_inputs'][label] == self.pins[label], 'Physical Sync input differs from the original control proof: ' + label)
            require(self.control['source_inputs']['script'] == self.pins['control_harness']
                    and self.control['package_files'] == self.files, 'The successful control script or full package differs.')
            self.pins['control_scene'] = pin(self.control['saved_scene']['path'], self.control['saved_scene']['sha256'])
            self.pins['control_return'] = pin(self.control['local_Return']['path'], self.control['local_Return']['sha256'])
            require(Path(self.pins['control_scene']['path']).name == 'original_cosha_recovered.blend', 'Use the final actual restored/re-adopted original-clone save.')
            self.saved_dto = document(self.pins['control_return']['path'])
            row = self.control['public_row']
            self.names = {'item': row['item_id'], 'scene': row['scene'], 'rig': row['rig']}
            require(self.names['scene'] == self.seed_names['scene'] and self.names['rig'] == self.seed_names['rig'], 'The control report substituted its original Scene/Rig.')
            motions = self.control['protected_action_motions']
            self.base_sha, self.source_sha, self.input_sha = (motions[k] for k in ('custom_base', 'source_base', 'custom_input'))
            self.presentation_before = self.control['native_controller_presentation']['proof']
            require(digest(self.presentation_before) == self.control['native_controller_presentation']['sha256'], 'Controller presentation receipt is not self-consistent.')
            self.old = copy.deepcopy(self.control['original_before']['worklist'])
            final_assets = self.control['original_asset_snapshots'][-1]
            require(final_assets['boundary'] == 'final_reopen' and not final_assets['qualified_original_changes'], 'The control proof lacks its full final original asset snapshot.')
            self.assets_before = final_assets['snapshot']
            self.original_objects = sorted(self.assets_before['original_object_ids'])
            self.original_capture, self.original_mapped_names = None, None
            self.original_entry_actions = None
            self.report.update(schema='x.validation.original-cosha-single-sync/1',
                control_trial=self.pins['control_report'], manual_single_new_row=True,
                control_original_clone_acceptance_inherited=True, original_clone_Rig_acceptance=False,
                full_original_asset_preservation_verified=False, worker_launch_performed=False,
                physical_pair_verified=False, normal_new_workitem_publication_allowed=True,
                old_row_or_release_publication_performed=False, Unity_Apply_verified=False,
                collection_receipt_error=None, completed=False)
            self.report_path = self.output / 'original_cosha_single_sync_report.json'
            with self.report_path.open('x', encoding='utf-8') as stream:
                json.dump(self.report, stream, indent=2, ensure_ascii=False, allow_nan=False)
            with (self.output / 'original_cosha_report.json').open('w', encoding='utf-8') as stream:
                json.dump({'schema': 'x.validation.original-sync-inherited-admission/1', 'completed': False,
                    'native_execution_performed': False, 'successor_report': str(self.report_path)}, stream, indent=2)
            self.phase, self.job, self.archived, self.primary_error = 'open_control_scene', None, False, None
            self.claim = self.output / 'single_manual_Sync_claim.json'
            require(not self.claim.exists(), 'The one-worker claim already exists.')
            self.checkpoint('original_physical_inputs_admitted_no_worker_yet')

        def unchanged(self, ctx):
            item, session = self.current(ctx)
            require(self.dto(ctx, session) == self.saved_dto
                and self.native._motion(item.custom_action, item.custom_slot) == self.base_sha
                and self.native._motion(item.source_action, item.source_slot) == self.source_sha
                and self.native._motion(session['input_action'], session['input_slot']) == self.input_sha
                and digest(self.presentation(item.rig)) == self.control['native_controller_presentation']['sha256'],
                'Physical Sync changed formal Base/Source/Input20/controller presentation.')
            require(item.item_id == self.control['public_row']['item_id'] and item.work_item_id.replace('-', '') == self.work_id,
                    'Only the actual newly attached prepared row may Sync.')
            return item, session

        def exact_old(self, ctx, boundary, *, full=False):
            self.guard_old(ctx, boundary, full_motions=full)
            require(set(i.item_id for i in self.worklist.state(ctx).items) == set(self.old['rows']) | {self.names['item']},
                    'Physical Sync added or removed an unrelated Worklist row.')

        def establish_entry(self, ctx):
            saved, rig = self.worklist.state(ctx), self.worklist.state(ctx).rig
            record = self.target._load(rig)
            self.original_capture, self.original_mapped_names = self.plain(record['capture']), list(record['mapped_names'])
            require(digest(self.original_capture) == self.control['original_before']['recovery_capture_sha256'],
                    'The saved original control recovery capture differs from its completed proof.')
            self.oracle = control_helper.load_source(self.pins['preservation_oracle']['path'], control_helper.ORACLE_SHA, 'sync_original_assets_260b')
            self.guard_old(ctx, 'physical_entry_authenticated_control_final', changed_motion_refs=True, full_motions=True)
            require(set(i.item_id for i in saved.items) == set(self.old['rows']) | {self.names['item']}, 'Physical entry has a missing or unrelated extra row.')
            self.original_entry_actions = self.actions()
            self.old['actions'] = copy.deepcopy(self.original_entry_actions)
            self.report['original_entry_baseline'] = {'old_state': self.old_state(ctx),
                'old_Action_final_recovery_refs_and_full_motions': self.original_entry_actions,
                'capture_sha256': digest(self.original_capture), 'mapped_names': self.original_mapped_names,
                'derived_from_exact_completed_saved_control_file': self.pins['control_scene'],
                'control_final_asset_snapshot_reused_as_before': True}

        def archive_worker(self):
            if self.archived:
                return
            require(self.job is not None and self.job['process'].poll() is not None,
                    'Archive the complete stdout/pair only after this owned worker ends.')
            if self.job.get('log'):
                self.job['log'].flush()
            directory = self.output / 'actual_worker_evidence'
            require(not directory.exists(), 'Never overwrite old worker evidence.')
            shutil.copytree(self.job['root'], directory)
            self.report['worker_evidence'] = {p.relative_to(directory).as_posix(): pin(p, sha(p))
                for p in sorted(directory.rglob('*')) if p.is_file()}
            self.archived = True

        def worker_finished(self):
            if self.job['process'].poll() is None:
                require(time.monotonic() - self.job['started'] <= 600, 'The one owned worker exceeded the official timeout.')
                return False
            self.report['worker_natural_exit_code'] = self.job['process'].returncode
            self.archive_worker()  # poll_export disposes its root: archive first.
            return True

        def launch_sync(self):
            with self.context() as ctx:
                self.cached_lifecycle(ctx, 'physical_load_post')
                self.establish_entry(ctx)
                item, _session = self.unchanged(ctx)
                self.immutable()
                self.before_link = self.links.load_link(item.manifest_path)
                before = self.output / 'new_Link_before.json'
                with before.open('xb') as stream:
                    stream.write(Path(item.manifest_path).read_bytes())
                self.report['new_Link_before'] = pin(before, sha(before))
                self.report['scan_before'] = self.collector.scan_changes(ctx)
                self.exact_old(ctx, 'physical_scan_before')
                self.report['proof_before'] = self.collector.item_fingerprint(ctx, item)
                require(0 <= (datetime.now(timezone.utc) - start).total_seconds() <= 900,
                        'The worker START expired during admission; obtain a new scope, never extend this token.')
                require(self.exporter.active_job() is None, 'Do not take over a foreign or prior export job.')
                require(not self.claim.exists(), 'The explicit new-row Sync was already claimed.')
                with self.claim.open('x', encoding='utf-8') as stream:
                    json.dump({'schema': 'x.validation.original-single-sync-claim/1',
                        'resource_token': resource_pin, 'pid': os.getpid(), 'item_id': item.item_id,
                        'workItemId': self.work_id, 'worker_limit': 1}, stream, indent=2)
                self.report['manual_Sync_claim'] = pin(self.claim, sha(self.claim))
                self.checkpoint('before_one_public_manual_new_row_Sync')
                self.job = self.worklist.sync(ctx)
                scheduled = self.bpy.app.timers.is_registered(self.animation._poll_action_export)
                if scheduled:
                    self.bpy.app.timers.unregister(self.animation._poll_action_export)
                require(self.exporter.active_job() is self.job and self.job['_worklist_scene'] == ctx.scene
                        and self.job['_worklist_item_id'] == item.item_id, 'Public Sync did not return the exact new-row job.')
                require(scheduled, 'The public completion poll owner is missing.')
                self.report.update(worker_launch_performed=True, Sync_performed=True, worker_pid=self.job['process'].pid,
                    launch_proof=self.job['_worklist_fingerprint'], launch_export_implementation=self.job['_worklist_export_implementation'])
                require(self.job['rigging_export'] == self.saved_dto, 'Public Sync lost the frozen exact Return14.')
                self.phase = 'poll_one_worker'
                self.checkpoint('one_owned_worker_started_no_batch_or_old_row_Sync')

        def accept_pair(self):
            require(self.report['worker_natural_exit_code'] == 0, 'Actual worker did not naturally succeed.')
            result = self.exporter.poll_export(self.job)
            require(result is not None, 'Naturally completed worker lacks its actual publication result.')
            error = self.collector.export_finished(self.job, result=result)
            self.report['collection_receipt_error'] = error
            require(not error, 'Actual new-row publication Collect receipt: ' + error)
            self.animation._export_window_manager = None
            with self.context() as ctx:
                item, session = self.unchanged(ctx)
                after = self.links.load_link(item.manifest_path)
                mutable = set(self.links.OUTPUT_FIELDS) | {'revision'}
                require({k: v for k, v in after.items() if k not in mutable}
                    == {k: v for k, v in self.before_link.items() if k not in mutable}
                    and after['revision'] == self.before_link.get('revision', 0) + 1,
                    'Only the exact new prepared Link outputs and one revision may change.')
                fbx, metadata = pin(after['fbxFile'], after['fbxSha256']), pin(after['metadataFile'], after['metadataSha256'])
                payload = document(metadata['path'])
                returned = self.contract.validate_export(payload['rigging'], session['capture'],
                    source_packet_sha256=self.pins['packet']['sha256'], work_item_id=self.work_id,
                    new_action_id=session['new_action_id'], source_action=item.custom_action.name,
                    source_action_slot=item.custom_slot, target_input_action=session['input_action'].name,
                    target_input_action_slot=session['input_slot'])
                require(fbx['bytes'] > 0 and payload['fbx_sha256'] == fbx['sha256']
                    and payload['action'] == item.custom_action.name and payload['actionSlot'] == item.custom_slot
                    and payload['source_package_sha256'] == self.pins['packet']['sha256']
                    and Path(payload['source_package']).resolve() == Path(self.pins['packet']['path'])
                    and len(returned) == 14 and returned == self.saved_dto, 'Physical FBX/slot/packet/Return14/Input20 differs from the saved original control proof.')
                worker = document(self.output / 'actual_worker_evidence/stage/result.json')
                require(worker.get('ok', worker.get('success', False)) and worker['action_slot'] == item.custom_slot
                    and isinstance(worker['bones'], list) and worker['bones'], 'Archived actual worker slot/bone result is incomplete.')
                # The expected new Link update is qualified above. Never change
                # the old prepared-input evidence copies or any old Link pin.
                self.pins['link'] = pin(item.manifest_path, sha(item.manifest_path))
                after_file = self.output / 'new_Link_after.json'
                with after_file.open('xb') as stream:
                    stream.write(Path(item.manifest_path).read_bytes())
                self.report.update(fbx=fbx, metadata=metadata, published_Return=returned, new_revision=after['revision'],
                    new_Link_after=pin(after_file, sha(after_file)), qualified_current_Link=self.pins['link'],
                    actual_last_synced_receipt=json.loads(item.last_synced_receipt), physical_pair_verified=True,
                    scan_after=self.collector.scan_changes(ctx), proof_after=self.collector.item_fingerprint(ctx, item))
                self.exact_old(ctx, 'physical_finish', full=True)
                self.guard_assets(ctx, 'physical_finish')
                self.immutable()
                self.runtime_paths()
                scene = self.output / 'original_cosha_after_single_sync.blend'
                require(not scene.exists() and self.bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT',
                    filepath=str(scene), check_existing=False) == {'FINISHED'} and Path(self.bpy.data.filepath).resolve() == scene,
                    'Save the new owned original-clone Sync result, never the live artist or earlier seed.')
                self.report['saved_scene'] = pin(scene, sha(scene))
                self.report.update(completed=True, worker_performed=True, original_clone_Rig_acceptance=True,
                    original_Rig_acceptance=False, live_original_integration_verified=False,
                    full_original_asset_preservation_verified=True, artist_writes_performed=False,
                    natural_exit_verified=False, Unity_Apply_verified=False)
                self.phase = 'done'
                self.checkpoint('completed_one_original_clone_physical_pair_no_Unity_Apply')

        def tick(self):
            try:
                if self.phase == 'open_control_scene':
                    require(os.getpid() not in {self.control['blender']['pid'], self.snapshot_receipt['pid']}, 'Use a new process, never the artist or control process.')
                    row = self.pins['control_scene']
                    pin(row['path'], row['sha256'])
                    require(self.bpy.ops.wm.open_mainfile('EXEC_DEFAULT', filepath=row['path'], use_scripts=False, load_ui=False) == {'FINISHED'}, 'Actual final original control clone did not open.')
                    self.phase = 'launch_single_sync'
                    self.checkpoint('original_control_clone_opened_new_RNA_next_tick')
                elif self.phase == 'launch_single_sync': self.launch_sync()
                elif self.phase == 'poll_one_worker':
                    if not self.worker_finished(): return .25
                    self.accept_pair()
                elif self.phase == 'drain_failed_worker':
                    if not self.worker_finished(): return .25
                    self.exporter.cancel_export(self.job)  # Process is gone; dispose without a publication callback.
                    self.animation._export_window_manager = None
                    self.phase = 'failed'
                    self.checkpoint('failed_owned_worker_naturally_closed_evidence_preserved')
                if self.phase == 'done' and self.args.quit_on_completion:
                    with self.context():
                        returned = self.bpy.ops.wm.quit_blender('EXEC_DEFAULT')
                        self.checkpoint('normal_quit_requested', operator_result=sorted(returned), natural_exit_verified=False)
                return None if self.phase in {'done', 'failed'} else .25
            except Exception as error:
                self.report.update(completed=False, original_clone_Rig_acceptance=False,
                    failure_phase=self.phase, error=str(error), traceback=traceback.format_exc())
                self.primary_error = self.primary_error or str(error)
                if self.job is not None and self.exporter.active_job() is self.job:
                    if self.job['process'].poll() is None and time.monotonic() - self.job['started'] <= 600:
                        self.phase = 'drain_failed_worker'
                        self.checkpoint('failure_draining_only_owned_worker_no_retry_or_publication')
                        return .25
                    try:
                        if self.job['process'].poll() is not None:
                            self.archive_worker()
                        else:
                            self.report['worker_forced_timeout_cleanup'] = True
                        self.exporter.cancel_export(self.job)
                    except Exception as cleanup:
                        self.report['owned_worker_cleanup_error'] = str(cleanup)
                self.animation._export_window_manager = None
                self.phase = 'failed'
                self.checkpoint('failed_no_retry_old_row_Sync_or_artist_write')
                return None

        def start(self):
            super().start()
            for attr, name in (('exporter', 'animation_export'), ('links', 'animation_link'), ('animation', 'animation')):
                setattr(self, attr, importlib.import_module('character_designer.' + name))
            self.runtime_paths()

    run = SyncRound(args)
    try:
        run.start()
    except Exception as error:
        run.report.update(completed=False, failure_phase='startup', error=str(error), traceback=traceback.format_exc())
        run.checkpoint('original_physical_startup_failed_no_retry')
        raise


if __name__ == '__main__':
    main()
