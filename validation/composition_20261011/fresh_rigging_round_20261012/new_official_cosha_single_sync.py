"""Prepare one explicit physical Sync of a successful isolated Cosha control trial.

This script requires a separate fresh headful/worker resource scope to execute.
It reuses the exact reviewed control harness's full package/input admission,
opens only that trial's saved scene and never opens/reloads the artist session.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import traceback


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared-report', 'protected-artist', 'source-freeze', 'package-manifest',
                 'control-report', 'control-harness'):
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
    import hashlib
    def digest_file(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    harness = Path(args.control_harness).resolve()
    if (harness.parent != Path(__file__).resolve().parent
            or harness.name != 'new_official_cosha_round.py'
            or digest_file(harness) != args.control_harness_sha256
            or digest_file(__file__) != args.script_sha256):
        raise RuntimeError('Use both exact reviewed harness scripts in this owned Source directory.')
    spec = importlib.util.spec_from_file_location('_reviewed_cosha_control_trial', harness)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    physical_sha, args.script_sha256 = args.script_sha256, args.control_harness_sha256

    class SyncRound(helper.Round):
        def __init__(self, args):
            super().__init__(args)
            self.pins['physical_script'] = helper.pin(__file__, physical_sha)
            self.pins['control_report'] = helper.pin(args.control_report, args.control_report_sha256)
            self.control = helper.document(args.control_report)
            helper.require(self.control['schema'] == 'x.validation.new-official-cosha-control-save/1'
                and self.control['completed'] is True and self.control['native_execution_performed'] is True
                and self.control['formal_public_Add_Activate_verified'] is True
                and self.control['explicit_input_save_verified'] is True
                and self.control['save_reopen_verified'] is True and self.control['real_Undo_Redo_verified'] is True
                and self.control['Sync_performed'] is False and self.control['original_Rig_acceptance'] is False
                and self.control['workItemId'] == self.work_id,
                'Use the actual successful public control/Undo/reopen trial; no source receipt qualifies.')
            for name in ('prepared_report', 'protected_artist', 'source_freeze', 'package_manifest',
                         'workspace', 'link', 'packet', 'model', 'weapon_context', 'weapon_model'):
                helper.require(self.control['source_inputs'][name] == self.pins[name],
                               'Physical Sync requires the same admitted control-trial inputs: ' + name)
            helper.require(self.control['package_files'] == self.files, 'The full frozen package changed between phases.')
            self.pins['control_scene'] = helper.pin(self.control['saved_scene']['path'], self.control['saved_scene']['sha256'])
            self.pins['control_return'] = helper.pin(self.control['local_Return']['path'], self.control['local_Return']['sha256'])
            self.saved_dto = helper.document(self.pins['control_return']['path'])
            row = self.control['public_row']
            self.names = {'item': row['item_id'], 'scene': row['scene'], 'rig': row['rig']}
            motions = self.control['protected_action_motions']
            self.base_sha, self.source_sha, self.input_sha = (motions[name] for name in ('custom_base', 'source_base', 'custom_input'))
            self.report.update(schema='x.validation.new-official-cosha-single-sync/1',
                control_trial=self.pins['control_report'], manual_single_selection=True,
                worker_launch_performed=False, physical_pair_verified=False,
                collection_receipt_error=None, completed=False)
            self.phase, self.job, self.archived = 'open_control_scene', None, False
            self.checkpoint('physical_inputs_admitted_no_worker_yet')

        def unchanged(self, ctx):
            item, session = self.current(ctx)
            helper.require(self.dto(ctx, session) == self.saved_dto
                and self.native._motion(item.custom_action, item.custom_slot) == self.base_sha
                and self.native._motion(item.source_action, item.source_slot) == self.source_sha
                and self.native._motion(session['input_action'], session['input_slot']) == self.input_sha
                and helper.digest(self.presentation(item.rig)) == self.control['native_controller_presentation']['sha256'],
                'The formal base, Source, twenty saved inputs or controller presentation changed.')
            return item, session

        def archive_worker(self):
            if self.archived:
                return
            if self.job.get('log'):
                self.job['log'].flush()
            directory = self.output / 'actual_worker_evidence'
            helper.require(not directory.exists(), 'Preserve the previous worker evidence.')
            shutil.copytree(self.job['root'], directory)
            self.report['worker_evidence'] = {
                path.relative_to(directory).as_posix(): helper.pin(path, helper.sha(path))
                for path in sorted(directory.rglob('*')) if path.is_file()}
            self.archived = True

        def tick(self):
            try:
                if self.phase == 'open_control_scene':
                    helper.require(os.getpid() != self.control['blender']['pid'], 'Use a separate fresh process, never the control/artist process.')
                    helper.require(self.bpy.ops.wm.open_mainfile('EXEC_DEFAULT',
                        filepath=self.pins['control_scene']['path'], use_scripts=False, load_ui=False) == {'FINISHED'},
                        'The isolated successful control trial did not reopen.')
                    self.phase = 'launch_single_sync'
                    self.checkpoint('control_scene_opened_new_IDs_next_tick')
                elif self.phase == 'launch_single_sync':
                    with self.context() as ctx:
                        rig = self.bpy.data.objects.get(self.names['rig'])
                        cached = self.native.display_state(rig)
                        helper.require(cached and cached['enabled'] and not cached['tweak_enabled']
                            and cached['edit_role'] == 'BASE', 'Authenticate the load callback before manual current/Activate.')
                        item, session = self.unchanged(ctx)
                        self.immutable()
                        self.before_link = self.links.load_link(item.manifest_path)
                        raw = Path(item.manifest_path).read_bytes()
                        (self.output / 'link_before.json').write_bytes(raw)
                        self.report['link_before'] = helper.pin(self.output / 'link_before.json', helper.sha(item.manifest_path))
                        self.report['scan_before'] = self.collector.scan_changes(ctx)
                        self.report['proof_before'] = self.collector.item_fingerprint(ctx, item)
                        self.checkpoint('before_explicit_manual_single_sync')
                        self.job = self.worklist.sync(ctx)
                        helper.require(self.exporter.active_job() is self.job
                            and self.job['_worklist_scene'] is ctx.scene
                            and self.job['_worklist_item_id'] == item.item_id,
                            'The real public Sync did not return the one owned row/job.')
                        # Replace only this exact job's redundant UI poll owner.
                        helper.require(self.bpy.app.timers.is_registered(self.animation._poll_action_export),
                                       'The public Sync completion owner was not scheduled.')
                        self.bpy.app.timers.unregister(self.animation._poll_action_export)
                        self.report.update(worker_launch_performed=True, Sync_performed=True,
                            worker_pid=self.job['process'].pid, launch_proof=self.job['_worklist_fingerprint'],
                            launch_export_implementation=self.job['_worklist_export_implementation'])
                        helper.require(self.job['rigging_export'] == self.saved_dto, 'The worker launch lost the frozen independent Return14.')
                        self.phase = 'poll_one_worker'
                        self.checkpoint('one_public_worker_launched')
                elif self.phase == 'poll_one_worker':
                    if self.job['process'].poll() is None:
                        import time
                        helper.require(time.monotonic() - self.job['started'] <= 600, 'The owned worker exceeded the official timeout.')
                        return .25
                    self.report['worker_natural_exit_code'] = self.job['process'].returncode
                    self.archive_worker()
                    result = self.exporter.poll_export(self.job)
                    helper.require(result is not None, 'The completed worker has no publication result.')
                    error = self.collector.export_finished(self.job, result=result)
                    self.report['collection_receipt_error'] = error
                    helper.require(not error, 'Physical publication Collect receipt: ' + error)
                    self.animation._export_window_manager = None
                    with self.context() as ctx:
                        item, session = self.unchanged(ctx)
                        after = self.links.load_link(item.manifest_path)
                        mutable = set(self.links.OUTPUT_FIELDS) | {'revision'}
                        helper.require({k:v for k,v in after.items() if k not in mutable}
                            == {k:v for k,v in self.before_link.items() if k not in mutable}
                            and after['revision'] == self.before_link.get('revision',0)+1,
                            'The physical publication changed prepared source identity or advanced an unexpected revision.')
                        fbx = helper.pin(after['fbxFile'], after['fbxSha256'])
                        metadata = helper.pin(after['metadataFile'], after['metadataSha256'])
                        payload = helper.document(metadata['path'])
                        validated = self.contract.validate_export(payload['rigging'], session['capture'],
                            source_packet_sha256=self.pins['packet']['sha256'], work_item_id=self.work_id,
                            new_action_id=session['new_action_id'], source_action=item.custom_action.name,
                            source_action_slot=item.custom_slot, target_input_action=session['input_action'].name,
                            target_input_action_slot=session['input_slot'])
                        helper.require(fbx['bytes'] > 0 and payload['fbx_sha256'] == fbx['sha256']
                            and payload['action'] == item.custom_action.name and payload['actionSlot'] == item.custom_slot
                            and payload['source_package_sha256'] == self.pins['packet']['sha256']
                            and Path(payload['source_package']).resolve() == Path(self.pins['packet']['path'])
                            and len(validated) == 14 and validated == self.saved_dto,
                            'The actual FBX/metadata/selected slot or twenty returned components differ.')
                        worker_result = helper.document(self.output / 'actual_worker_evidence/stage/result.json')
                        helper.require(worker_result.get('ok',worker_result.get('success',False))
                            and worker_result['action_slot'] == item.custom_slot
                            and isinstance(worker_result['bones'],list) and worker_result['bones'],
                            'The archived actual worker result is incomplete or belongs to another slot.')
                        self.pins['link'] = helper.pin(item.manifest_path, helper.sha(item.manifest_path))
                        (self.output / 'link_after.json').write_bytes(Path(item.manifest_path).read_bytes())
                        self.report.update(fbx=fbx, metadata=metadata, published_Return=validated,
                            revision=after['revision'], link_after=self.pins['link'],
                            actual_last_synced_receipt=json.loads(item.last_synced_receipt),
                            scan_after=self.collector.scan_changes(ctx),
                            proof_after=self.collector.item_fingerprint(ctx,item), physical_pair_verified=True)
                        self.immutable()
                        self.runtime_paths()
                        scene = self.output / 'new_official_cosha_after_single_sync.blend'
                        helper.require(not scene.exists() and self.bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT',
                            filepath=str(scene), check_existing=False) == {'FINISHED'}, 'Save the independent physical Sync result.')
                        self.report['saved_scene'] = helper.pin(scene, helper.sha(scene))
                        self.report.update(completed=True, worker_performed=True,
                            Unity_Apply_verified=False, original_Rig_acceptance=False)
                        self.phase = 'done'
                        self.checkpoint('completed_single_sync_physical_pair_only')
                    if self.args.quit_on_completion:
                        with self.context():
                            self.bpy.ops.wm.quit_blender('EXEC_DEFAULT')
                return None if self.phase == 'done' else .25
            except Exception as error:
                self.report.update(completed=False, failure_phase=self.phase,
                                   error=str(error), traceback=traceback.format_exc())
                if self.job is not None and self.exporter.active_job() is self.job:
                    try:
                        self.archive_worker()
                    except Exception as archival:
                        self.report['owned_worker_archive_error'] = str(archival)
                    try:
                        self.exporter.cancel_export(self.job)
                    except Exception as recovery:
                        self.report['owned_worker_cleanup_error'] = str(recovery)
                self.checkpoint('failed_physical_evidence_retained_no_retry')
                return None

        def start(self):
            super().start()
            import importlib
            self.exporter = importlib.import_module('character_designer.animation_export')
            self.links = importlib.import_module('character_designer.animation_link')
            self.animation = importlib.import_module('character_designer.animation')

    run = SyncRound(args)
    try:
        run.start()
    except Exception as error:
        run.report.update(completed=False, failure_phase='startup', error=str(error), traceback=traceback.format_exc())
        run.checkpoint('physical_startup_failed')
        raise


if __name__ == '__main__':
    main()
