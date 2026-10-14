"""Source-only preparation of a fresh-model Worklist control/save probe.

A fresh owned headful process is required. The artist is only hash-checked,
never opened. No Sync, export worker, publication, Unity Apply or runtime Play
is performed. This new-model experiment is not Original X Rig acceptance.
"""

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import sys
import traceback
import uuid


def require(value, text):
    if not value:
        raise RuntimeError(text)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def pin(path, expected):
    path = Path(path).resolve()
    require(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected)
            and path.is_file() and sha(path) == expected, 'Immutable input changed: ' + str(path))
    return {'path': str(path), 'sha256': expected, 'bytes': path.stat().st_size}


def document(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def matrix(matrix):
    result = [float(value) for row in matrix for value in row]
    require(len(result) == 16 and all(math.isfinite(v) for v in result), 'Native matrix is not finite.')
    return result


def delta(a, b):
    require(len(a) == len(b) and bool(a) and all(math.isfinite(v) for v in a + b),
            'Use the same finite nonempty native comparison domain.')
    return max(abs(x - y) for x, y in zip(a, b))


def arguments():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared-report', 'protected-artist', 'source-freeze', 'package-manifest'):
        p.add_argument('--' + name, required=True)
        p.add_argument('--' + name + '-sha256', required=True)
    for name in ('script-sha256', 'unity-project-root', 'output-root', 'profile-root'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--reference-packet')
    p.add_argument('--reference-packet-sha256')
    p.add_argument('--confirm-isolated-headful', required=True, action='store_true')
    p.add_argument('--quit-on-completion', action='store_true')
    return p.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])


class Round:
    def __init__(self, args):
        self.args, self.phase, self.names = args, 'add_activate', {}
        self.output, self.profile = Path(args.output_root).resolve(), Path(args.profile_root).resolve()
        scope = Path(__file__).resolve().parent
        require(self.output != scope and self.output.is_relative_to(scope)
                and self.output.is_dir() and not any(self.output.iterdir()), 'Use a fresh empty owned output child.')
        require(self.profile != self.output and not self.profile.is_relative_to(self.output)
                and self.profile.is_dir() and {p.name for p in self.profile.iterdir()} == {'CONFIG', 'DATAFILES'}
                and all((self.profile / name).is_dir() and not (self.profile / name).is_symlink()
                    and not any((self.profile / name).iterdir()) for name in ('CONFIG', 'DATAFILES')),
                'Use a separate short fresh root containing only empty CONFIG/DATAFILES.')
        # Worklist's native Source cache appends workspace UUID, model SHA and
        # item UUID. A short separate profile prevents a >260 path naturally.
        predicted = self.profile / 'DATAFILES/character_designer/animation_sources' / ('0' * 32) / ('0' * 64) / ('0' * 32 + '.blend')
        require(len(str(predicted).encode('utf-16-le')) // 2 < 260, 'The actual Source-cache profile path would exceed 260 units.')
        for variable, name in (('BLENDER_USER_CONFIG', 'CONFIG'), ('BLENDER_USER_DATAFILES', 'DATAFILES')):
            require(os.environ.get(variable) and Path(os.environ[variable]).resolve() == self.profile / name,
                    'The owned process profile environment differs from the explicit roots.')
        self.pins = {'script': pin(__file__, args.script_sha256)}
        for name in ('prepared_report', 'protected_artist', 'source_freeze', 'package_manifest'):
            self.pins[name] = pin(getattr(args, name), getattr(args, name + '_sha256'))
        artist = Path(self.pins['protected_artist']['path'])
        project = Path(args.unity_project_root).resolve()
        require(not artist.is_relative_to(self.output) and not artist.is_relative_to(self.profile)
                and not self.profile.is_relative_to(project), 'Keep artist/project files outside the owned outputs.')
        prepared = document(self.pins['prepared_report']['path'])
        require(prepared['schema'] == 'randomrealm.two-arm-real-prepare/1' and prepared['passed'] is True
                and prepared['error'] is None and Path(prepared['reportPath']).resolve() == Path(args.prepared_report).resolve()
                and all(prepared[name] is True for name in ('scenesPreserved', 'selectionPreserved',
                    'sourcesPreserved', 'artistQueuePreserved', 'undoHistoryPrefixPreserved', 'previewScenesPreserved')),
                'Use an actual successful real Prepare report; no source generation counts as Prepare.')
        for label, path_key, sha_key in (('workspace', 'workspacePath', 'workspaceSha256'),
                ('link', 'manifestPath', 'manifestSha256'), ('packet', 'packetPath', 'packetSha256'),
                ('model', 'modelFile', 'modelSha256'), ('weapon_context', 'weaponContextFile', 'weaponContextSha256'),
                ('weapon_model', 'weaponModelFile', 'weaponModelSha256')):
            self.pins[label] = pin(prepared[path_key], prepared[sha_key])
        for label, path_key, sha_key in (('base_asset', 'sourceClipPath', 'sourceClipSha256'),
                ('controls_asset', 'controlsPath', 'controlsSha256'), ('weapon_prefab', 'weaponPrefabPath', 'weaponPrefabSha256')):
            path = (project / prepared[path_key]).resolve()
            require(path.is_relative_to(project) and prepared[path_key].startswith('Assets/'), 'A prepared asset path escaped its project.')
            self.pins[label] = pin(path, prepared[sha_key])
        sidecar = Path(self.pins['model']['path']).with_suffix('.cdesigner.json')
        self.sidecar = str(sidecar)
        if sidecar.is_file():
            self.pins['model_sidecar'] = pin(sidecar, sha(sidecar))
        self.work_id = uuid.UUID(prepared['realWorkItemId']).hex
        raw, link = document(self.pins['packet']['path']), document(self.pins['link']['path'])
        c = raw['rigging']
        require(self.work_id != c['newActionId'] and uuid.UUID(self.work_id).int != 0
                and uuid.UUID(link['workItemId']).hex == self.work_id
                and link['targetGuid'] == raw['targetGuid'] == prepared['targetGuid']
                and link['sourcePackageSha256'] == self.pins['packet']['sha256']
                and Path(link['sourcePackage']).resolve() == Path(self.pins['packet']['path'])
                and Path(link['modelFile']).resolve() == Path(self.pins['model']['path'])
                and link['modelSha256'] == self.pins['model']['sha256']
                and c['newActionId'] == prepared['targetControlActionId']
                and c['bindingsSha256'] == prepared['bindingsSha256']
                and all(c[a] == prepared[b] for a, b in (('sourceClipPath', 'controlsPath'),
                    ('sourceClipGuid', 'controlsGuid'), ('sourceClipLocalId', 'controlsLocalId'),
                    ('sourceClipSha256', 'controlsSha256'))), 'Real base/controls/WorkID/Link/model identity disagrees.')
        weapon = c.get('weaponPreview')
        require(weapon is not None and all(weapon[key] == prepared[key] for key in
            ('weaponContextFile', 'weaponContextSha256', 'weaponModelFile', 'weaponModelSha256',
             'weaponPrefabGuid', 'weaponSocketPath')), 'Keep the complete actual weapon payload and its original packet SHA.')
        require(bool(args.reference_packet) == bool(args.reference_packet_sha256), 'Pin both reference path and SHA or neither.')
        if args.reference_packet:
            self.pins['reference_packet'] = pin(args.reference_packet, args.reference_packet_sha256)
        freeze, manifest = document(args.source_freeze), document(args.package_manifest)
        require(freeze['schema'] == 'cdesigner.x-rigging-source-freeze/1'
                and freeze['status'] == 'SOURCE_FROZEN_NATIVE_PENDING' and freeze['source_only'] is True
                and freeze['native_execution_performed'] is False and type(manifest['schema_version']) is int
                and manifest['schema_version'] == 1 and manifest['module'] == 'character_designer'
                and manifest['version'] == '0.77.25' and type(manifest['source_provenance']) is dict
                and manifest['source_provenance'],
                'Use a future reviewed complete Source freeze/package pair, not an old partial package.')
        self.root = Path(manifest['source_root']).resolve()
        self.files = {}
        for relative, value in manifest['files'].items():
            require(not Path(relative).is_absolute() and (self.root / relative).resolve().is_relative_to(self.root)
                    and '__pycache__' not in Path(relative).parts, 'A package file leaves the admitted complete source root.')
            self.files[relative] = pin(self.root / relative, value)
        require(self.root.name == 'character_designer'
                and {p.relative_to(self.root).as_posix() for p in self.root.rglob('*') if p.is_file()} == set(self.files),
                'The complete package has a missing, additional or outside file.')
        runtime = {Path(row['path']).name: row for row in freeze['source_pins'] if 'addons' in Path(row['path']).parts}
        require({'animation_rigging_setup.py', 'animation_link_source.py', 'unity_animation_rigging.py'} <= set(runtime),
                'The new fresh-only bridge/native implementation is absent from the future Source freeze.')
        for name, row in runtime.items():
            require(self.files[name]['sha256'] == row['sha256'] and self.files[name]['bytes'] == row['bytes'], 'Frozen runtime leaf differs: ' + name)
        self.report = {'schema': 'x.validation.new-official-cosha-control-save/1', 'completed': False,
            'source_inputs': self.pins, 'package_files': self.files, 'native_execution_performed': False,
            'original_artist_opened': False, 'original_Rig_acceptance': False, 'new_Rig_trial_only': True,
            'Sync_performed': False, 'worker_performed': False, 'Unity_Apply_verified': False,
            'visible_gun_acceptance_verified': False, 'base_leg_edit_verified': False,
            'deform_pose_verified': False, 'hold_pose_verified': False, 'natural_exit_verified': False,
            'reference_preview_verified': False, 'checkpoints': [], 'workItemId': self.work_id,
            'raw_binding_weights': [{k: b[k] for k in ('rigWeight', 'constraintWeight',
                'targetPositionWeight', 'targetRotationWeight', 'hintWeight')} for b in c['bindings']],
            'previewEnabled': c['previewEnabled'], 'effective_global_preview_expected': 1 if c['previewEnabled'] else 0}
        self.report_path = self.output / 'new_official_cosha_report.json'
        with self.report_path.open('x', encoding='utf-8') as stream:
            json.dump(self.report, stream, ensure_ascii=False, indent=2, allow_nan=False)

    def checkpoint(self, phase, **values):
        self.report['phase'] = phase
        self.report['checkpoints'].append({'phase': phase, **values})
        with self.report_path.open('w', encoding='utf-8') as stream:
            json.dump(self.report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())

    def immutable(self):
        for row in (*self.pins.values(), *self.files.values()):
            pin(row['path'], row['sha256'])
        require(Path(self.sidecar).is_file() == ('model_sidecar' in self.pins), 'Optional model metadata presence changed.')

    @contextmanager
    def context(self, view=False):
        windows = tuple(self.bpy.context.window_manager.windows)
        require(len(windows) == 1 and not self.bpy.app.background, 'Use the one real owned headful Window.')
        window = windows[0]
        if self.names.get('scene'):
            scenes = [s for s in self.bpy.data.scenes if s.name == self.names['scene'] and s.library is None]
            require(len(scenes) == 1, 'The actual public-result Scene is missing or ambiguous.')
            window.scene = scenes[0]
        with self.bpy.context.temp_override(window=window):
            require(self.bpy.context.scene == window.scene and self.bpy.context.view_layer == window.view_layer
                    and self.bpy.context.preferences.filepaths.use_scripts_auto_execute is False,
                    'The fresh owning context or disabled autoexec policy changed.')
            for name in ('CONFIG', 'DATAFILES'):
                require(Path(self.bpy.utils.user_resource(name, create=False)).resolve() == self.profile / name,
                        'Blender uses another actual profile; no cache may be written outside this owned root.')
            if view:
                areas = [a for a in window.screen.areas if a.type == 'VIEW_3D']
                require(len(areas) == 1, 'Use the real unique factory View3D.')
                regions = [r for r in areas[0].regions if r.type == 'WINDOW']
                require(len(regions) == 1, 'The native transform needs its actual Window region.')
                with self.bpy.context.temp_override(area=areas[0], region=regions[0]):
                    yield self.bpy.context
            else:
                yield self.bpy.context

    def current(self, ctx):
        saved = self.worklist.state(ctx)
        items = [i for i in saved.items if i.item_id == self.names['item']]
        require(len(items) == 1 and len(saved.items) == 1, 'The actual owned row identity changed.')
        item = items[0]
        session = self.native.current(item.rig)
        require(session is not None and item.rig == saved.rig and session['rig'] == item.rig
                and session['scene'] == ctx.scene and session['base_action'] == item.custom_action
                and session['base_slot'] == item.custom_slot and session['work_item_id'] == self.work_id
                and session['source_packet_sha256'] == self.pins['packet']['sha256'], 'The exact native row/session owner changed.')
        self.worklist._check_baseline(item)
        require(self.ua.native_action_frame_rate(item.custom_action) == self.packet['sampleRate']
                and self.ua.native_action_frame_rate(item.source_action) == self.packet['sampleRate']
                and len(self.native._curves(session['input_action'], session['input_slot'])) == 20,
                'Both real base Actions and the twenty-component input carrier must retain the authenticated clock.')
        return item, session

    def dto(self, ctx, session):
        before = [self.native._motion(session['base_action'], session['base_slot']),
            self.native._motion(session['input_action'], session['input_slot']),
            ctx.scene.frame_current, ctx.scene.frame_subframe, session['rig'][self.native.SESSION_KEY]]
        result = self.native.capture_inputs(ctx, session, source_packet_sha256=self.pins['packet']['sha256'],
            work_item_id=self.work_id, source_action=session['base_action'], source_action_slot=session['base_slot'])
        result = self.contract.validate_export(result, session['capture'], source_packet_sha256=self.pins['packet']['sha256'],
            work_item_id=self.work_id, new_action_id=session['new_action_id'], source_action=session['base_action'].name,
            source_action_slot=session['base_slot'], target_input_action=session['input_action'].name,
            target_input_action_slot=session['input_slot'])
        require(len(result) == 14, 'Keep the exact fourteen-field local Return contract.')
        require(before == [self.native._motion(session['base_action'], session['base_slot']),
            self.native._motion(session['input_action'], session['input_slot']),
            ctx.scene.frame_current, ctx.scene.frame_subframe, session['rig'][self.native.SESSION_KEY]],
            'Reading a Return DTO changed curves, time or persistent ownership.')
        return result

    def presentation(self, rig):
        return {'bones': sorted(rig.data.bones.keys()),
            'colors': {pb.name: [pb.color.palette, pb.bone.color.palette,
                list(pb.color.custom.normal), list(pb.color.custom.select), list(pb.color.custom.active),
                list(pb.bone.color.custom.normal), list(pb.bone.color.custom.select), list(pb.bone.color.custom.active)]
                for pb in rig.pose.bones},
            'controllers': {pb.name: [pb.custom_shape.name if pb.custom_shape else None,
                pb.custom_shape_transform.name if pb.custom_shape_transform else None,
                [(c.name, c.type, getattr(c, 'subtarget', None), getattr(c, 'pole_subtarget', None))
                    for c in pb.constraints]] for pb in rig.pose.bones},
            'collections': {c.name: {'parent': c.parent.name if c.parent else None,
                'bones': sorted(c.bones.keys())} for c in rig.data.collections_all}}

    def add_activate(self):
        with self.context() as ctx:
            require(not self.bpy.data.filepath and not any(o.type == 'ARMATURE' for o in self.bpy.data.objects),
                    'Do not load the original artist or any old model into this factory process.')
            scene = self.bpy.data.scenes.new('Official Cosha · Input Trial')
            ctx.window.scene = scene
            require(not tuple(ctx.scene.objects) and not self.worklist.state(ctx).items
                    and self.worklist.state(ctx).rig is None, 'Start from an actual empty scene, without fabricated rows.')
            self.worklist.connect(ctx, self.pins['workspace']['path'])
            record = self.workspace.load_workspace(self.pins['workspace']['path'])
            clips = [c for c in record['clips'] if self.workspace.work_item_id(c) == self.work_id]
            require(len(clips) == 1, 'The real prepared WorkID must identify one official row.')
            key = self.workspace.row_key(clips[0])
            self.checkpoint('before_public_Add', workItemId=self.work_id)
            item = self.worklist.add(ctx, key, activate_new=False)
            self.names = {'item': item.item_id, 'scene': ctx.scene.name, 'rig': item.rig.name}
            self.worklist.activate(ctx, item.item_id, 'CUSTOM')
            item, session = self.current(ctx)
            require(Path(item.manifest_path).resolve() == Path(self.pins['link']['path'])
                    and item.model_sha256 == self.pins['model']['sha256']
                    and session['capture'] == self.contract.validate_capture(self.packet['rigging'], packet=self.packet),
                    'Public Add/Activate changed the prepared route or stripped captured fields.')
            setup = json.loads(item.rig['character_designer_fresh_arm_setup_v1'])
            require(setup['model_sha256'] == self.pins['model']['sha256']
                    and setup['source_packet_sha256'] == self.pins['packet']['sha256']
                    and setup['original_rest_unchanged'] is True and setup['source_mapping_unchanged'] is True
                    and setup['base_modes'] == ['FK', 'FK'], 'The new model lacks the real fresh-only setup proof.')
            self.report['fresh_setup_proof'] = setup
            self.report['public_row'] = {'item_id': item.item_id, 'rig': item.rig.name, 'scene': ctx.scene.name,
                'source_action': item.source_action.name, 'source_slot': item.source_slot,
                'custom_action': item.custom_action.name, 'custom_slot': item.custom_slot,
                'source_cache': pin(item.source_file, item.source_hash), 'input_action': session['input_action'].name,
                'input_slot': session['input_slot'], 'draft_id': session['new_action_id']}
            self.base_sha = self.native._motion(item.custom_action, item.custom_slot)
            self.source_sha = self.native._motion(item.source_action, item.source_slot)
            self.presentation_before = self.presentation(item.rig)
            self.report['scan_before'] = self.collector.scan_changes(ctx)
            self.report['proof_before'] = self.collector.item_fingerprint(ctx, item)
            self.phase = 'edit_save'
        self.checkpoint('public_Add_Activate_finished')

    def edit_save(self):
        with self.context(view=True) as ctx:
            item, session = self.current(ctx)
            rig = item.rig
            for selected in ctx.selected_objects:
                selected.select_set(False)
            rig.select_set(True)
            ctx.view_layer.objects.active = rig
            if rig.mode != 'POSE':
                require(self.bpy.ops.object.mode_set(mode='POSE') == {'FINISHED'}, 'Native Pose mode failed.')
            session = self.native.activate(ctx, session, edit_role='RIGGING', enabled=True)
            time = session['capture']['frames'][len(session['capture']['frames']) // 2]['time']
            self.ua._set_frame(ctx.scene, session['scene_start'] + time * ctx.scene.render.fps / ctx.scene.render.fps_base)
            ctx.view_layer.update()
            initial = self.dto(ctx, self.native.current(rig))
            require(self.bpy.ops.ed.undo_push.poll()
                    and self.bpy.ops.ed.undo_push('EXEC_DEFAULT', message='Official Cosha · Before Input Save') == {'FINISHED'},
                    'The actual pre-edit native undo checkpoint was not created.')
            edits = []
            for index, row in enumerate(session['native_bindings']):
                for field, name in (('targetPosition', row['target']), ('hintPosition', row['pole'])):
                    session = self.native.current(rig)
                    pb = rig.pose.bones[name]
                    members = tuple(pb.bone.collections)
                    hidden = (pb if hasattr(pb, 'hide') else pb.bone).hide
                    require(type(hidden) is bool and not hidden and not pb.bone.hide_select and not any(pb.lock_location)
                            and ((not members and not any(c.is_solo for c in rig.data.collections_all))
                                 or any(c.is_visible_effectively for c in members)), 'The actual owned input is not visible/editable; no reveal fallback.')
                    rig.data.bones.active = pb.bone
                    for bone in rig.pose.bones:
                        self.composition._pose_selection_owner(bone).select = bone.name == name
                    require(ctx.active_pose_bone == pb and tuple(ctx.selected_pose_bones or ()) == (pb,)
                            and rig.animation_data.use_tweak_mode and rig.animation_data.action == session['input_action']
                            and rig.animation_data.action_slot_handle == session['input_slot']
                            and not ctx.scene.tool_settings.use_keyframe_insert_auto, 'Wrong native selection/input Tweak owner.')
                    before, input_before = matrix(pb.matrix_basis), self.native._motion(session['input_action'], session['input_slot'])
                    self.checkpoint('before_real_translate', control=name, pendingNativeOperator=True)
                    require(self.bpy.ops.transform.translate.poll(), 'Native translate poll failed.')
                    returned = self.bpy.ops.transform.translate('EXEC_DEFAULT', True, value=(.005, 0., 0.), orient_type='LOCAL')
                    ctx.view_layer.update()
                    moved = delta(before, matrix(rig.pose.bones[name].matrix_basis))
                    self.checkpoint('translate_returned', control=name, operator_result=sorted(returned), native_basis_delta=moved,
                                    pendingNativeOperator=True)
                    require(returned == {'FINISHED'} and moved > 1e-7, 'The actual native input did not move.')
                    require(self.native._motion(session['input_action'], session['input_slot']) == input_before,
                            'Inputs were keyed before explicit Save Rigging.')
                    self.native.key_current(ctx, session)
                    dto = self.dto(ctx, session)
                    sample = len(dto['frames']) // 2
                    changed = delta(initial['frames'][sample]['controls'][index][field], dto['frames'][sample]['controls'][index][field])
                    require(changed > 1e-7 and self.native._motion(item.custom_action, item.custom_slot) == self.base_sha
                            and self.native._motion(item.source_action, item.source_slot) == self.source_sha, 'Input save lost the edit or changed base/Source curves.')
                    edits.append({'control': name, 'field': field, 'native_delta': moved, 'saved_local_delta': changed})
                    self.checkpoint('explicit_input_save_verified', control=name, pendingNativeOperator=False)
            self.report['native_input_edits'] = edits
            session = self.native.activate(ctx, self.native.current(rig), edit_role='BASE', enabled=False)
            self.report['scan_after'] = self.collector.scan_changes(ctx)
            self.report['proof_after'] = self.collector.item_fingerprint(ctx, item)
            before, after = self.report['proof_before'], self.report['proof_after']
            require(before['rigging']['input_motion_sha256'] != after['rigging']['input_motion_sha256'], 'Exact Target-only input proof did not change.')
            require(item.scan_state in {'CHANGED', 'UNKNOWN'} and item.effective_inputs_changed and item.export_needed,
                    'Collect did not retain the real Target-input dirty state; no Sync fallback is allowed.')
            require(self.presentation(item.rig) == self.presentation_before,
                    'Input-only editing changed native controller/collection structure or controller colors.')
            self.report['collection_result'] = {'known': after['fingerprint_known'], 'scan_state': item.scan_state,
                'reason': item.scan_reason, 'effective_inputs_changed': item.effective_inputs_changed,
            'export_needed': item.export_needed, 'UNKNOWN_not_promoted': not after['fingerprint_known']}
            self.report['native_controller_presentation_preserved'] = True
            self.saved_dto = self.dto(ctx, session)
            self.input_sha = self.native._motion(session['input_action'], session['input_slot'])
            require(self.bpy.ops.ed.undo_push.poll()
                    and self.bpy.ops.ed.undo_push('EXEC_DEFAULT', message='Official Cosha · Saved Input Keys') == {'FINISHED'},
                    'The actual saved-input native undo checkpoint was not created.')
            self.phase = 'undo_inputs'
        self.checkpoint('native_control_save_finished')

    def cached_lifecycle(self, ctx, boundary):
        # Cache-only witness first; current/seek/Activate must not manufacture
        # apparent load/Undo/Redo reacquisition before the actual check.
        rigs = [o for o in self.bpy.data.objects if o.name == self.names['rig'] and o.library is None]
        require(len(rigs) == 1, 'The saved public-result Rig is missing or ambiguous.')
        cached = self.native.display_state(rigs[0])
        require(cached and cached['scene'] == ctx.scene and cached['enabled'] is True,
                'The owned lifecycle callback did not reacquire the enabled saved preview.')
        callbacks = {name: sum(h is handler for h in getattr(self.bpy.app.handlers, name)) for name, handler in
            (('load_post', self.native._reacquire), ('undo_post', self.native._reacquire), ('redo_post', self.native._reacquire),
             ('frame_change_post', self.native._frame), ('depsgraph_update_post', self.native._depsgraph))}
        require(all(n == 1 for n in callbacks.values()) and not self.native._HANDLER_ERRORS,
                'Owned callbacks are missing, duplicate or failed.')
        witness = {'boundary': boundary, 'callbacks': callbacks, 'edit_role': cached['edit_role'],
                   'tweak_enabled': cached['tweak_enabled'], 'cache_checked_before_manual_current_or_activate': True}
        self.report.setdefault('lifecycle_witnesses', []).append(witness)
        return witness

    def undo_redo(self, redo=False):
        with self.context(view=True):
            op = self.bpy.ops.ed.redo if redo else self.bpy.ops.ed.undo
            require(op.poll(), 'The real native Undo/Redo poll failed.')
            self.checkpoint('before_real_' + ('redo' if redo else 'undo'), fresh_native_readback_next_tick=True)
            returned = op('EXEC_DEFAULT')
            require(returned == {'FINISHED'}, 'Actual native Undo/Redo did not finish.')
            del op
        self.phase = 'check_redo' if redo else 'check_undo'
        self.checkpoint('real_' + ('redo' if redo else 'undo') + '_old_scope_ended', operator_result=sorted(returned))

    def check_undo_redo(self, redo=False):
        with self.context() as ctx:
            self.cached_lifecycle(ctx, 'redo_post' if redo else 'undo_post')
            item, session = self.current(ctx)
            motion = self.native._motion(session['input_action'], session['input_slot'])
            require(self.native._motion(item.custom_action, item.custom_slot) == self.base_sha
                    and self.native._motion(item.source_action, item.source_slot) == self.source_sha,
                    'Undo/Redo changed formal Base/Source instead of the saved input keys.')
            if redo:
                require(motion == self.input_sha and self.dto(ctx, session) == self.saved_dto,
                        'Actual Redo did not restore the exact input keys and local Return DTO.')
                self.report['real_Undo_Redo_verified'] = True
                self.phase = 'preview_reference' if 'reference_packet' in self.pins else 'save_scene'
            else:
                require(motion != self.input_sha, 'Actual Undo did not undo any explicit saved input key.')
                self.report['undo_input_motion_sha256'] = motion
                self.phase = 'redo_inputs'
        self.checkpoint('real_' + ('redo' if redo else 'undo') + '_fresh_IDs_readback_verified')

    def preview_reference(self):
        with self.context() as ctx:
            item, session = self.current(ctx)
            require(callable(getattr(self.native, 'prepare_preview_reference', None))
                    and callable(getattr(self.native, 'set_preview_reference', None)),
                    'Freeze both reviewed public reference APIs before this optional phase.')
            reference, slot = self.native.prepare_preview_reference(ctx, session,
                self.pins['reference_packet']['path'], self.pins['reference_packet']['sha256'],
                model_file=self.pins['model']['path'], model_sha256=self.pins['model']['sha256'])
            session = self.native.current(item.rig)
            ref_sha = self.native._motion(reference, slot)
            mapping = self.ua._mapping(item.rig, self.packet, ctx.scene.unit_settings.scale_length)
            roles = ('LeftLowerLeg', 'RightLowerLeg', 'LeftFoot', 'RightFoot')
            lower = {role: [b['name'] for b in self.packet['bones'] if b.get('humanRole') == role
                and b['name'] in mapping.indices] for role in roles}
            require(all(len(names) == 1 for names in lower.values()),
                    'The actual packet/mapping needs unique lower-leg and foot roles for the reference witness.')
            domain = {role: names[0] for role, names in lower.items()}
            require(not set(domain.values()).intersection(name for row in session['native_bindings'] for name in row['chain']),
                    'The reference witness must measure native lower-body bones outside arm Rigging.')
            count = len(session['capture']['frames'])
            times = [session['capture']['frames'][i]['time'] for i in sorted({count // 4, count // 2, 3 * count // 4})]
            def seek_pose(time):
                current = self.native.current(item.rig)
                self.ua._set_frame(ctx.scene, current['scene_start'] + time * ctx.scene.render.fps / ctx.scene.render.fps_base)
                ctx.view_layer.update()
                require(not self.native._HANDLER_ERRORS, 'Reference seek reported an owned native handler error.')
                return {role: matrix(item.rig.pose.bones[name].matrix) for role, name in domain.items()}
            formal = {str(time): seek_pose(time) for time in times}
            self.native.set_preview_reference(ctx, session, reference, slot,
                reference_packet_file=self.pins['reference_packet']['path'], reference_packet_sha256=self.pins['reference_packet']['sha256'],
                model_file=self.pins['model']['path'], model_sha256=self.pins['model']['sha256'])
            session = self.native.current(item.rig)
            strip = self.native._tracks(session)['BASE'].strips[0]
            ref_packet = document(self.pins['reference_packet']['path'])
            scene_rate = ctx.scene.render.fps / ctx.scene.render.fps_base
            expected = {'action_frame_start': 1., 'action_frame_end': 1. + ref_packet['duration'] * ref_packet['sampleRate'],
                'frame_start': session['scene_start'], 'frame_end': session['scene_start'] + session['capture']['duration'] * scene_rate,
                'scale': session['capture']['duration'] * scene_rate / (ref_packet['duration'] * ref_packet['sampleRate'])}
            measured = {key: float(getattr(strip, key)) for key in expected}
            require(strip.action == reference and strip.action_slot_handle == slot
                    and all(math.isfinite(measured[key]) and abs(measured[key] - value) <= 1e-6 for key, value in expected.items())
                    and strip.repeat == 1. and strip.extrapolation == 'HOLD',
                    'The actual owned BASE strip did not select the sealed reference on normalized phase.')
            reference_poses = {str(time): seek_pose(time) for time in times}
            differences = {key: {role: delta(formal[key][role], reference_poses[key][role]) for role in domain} for key in formal}
            require(any(value > 1e-7 for row in differences.values() for value in row.values()),
                    'No real lower-body pose difference was observed; a different effective reference is unproved.')
            require(self.dto(ctx, self.native.current(item.rig)) == self.saved_dto
                    and self.native._motion(item.custom_action, item.custom_slot) == self.base_sha
                    and self.native._motion(item.source_action, item.source_slot) == self.source_sha
                    and self.native._motion(reference, slot) == ref_sha, 'Preview reference changed formal Base, input values or protected reference curves.')
            self.native.set_preview_reference(ctx, self.native.current(item.rig))
            require(self.dto(ctx, self.native.current(item.rig)) == self.saved_dto
                    and self.native._motion(session['input_action'], session['input_slot']) == self.input_sha
                    and self.presentation(item.rig) == self.presentation_before,
                    'Restoring formal preview Base changed the input carrier.')
            restored = {str(time): seek_pose(time) for time in times}
            require(all(delta(formal[key][role], restored[key][role]) <= 2e-4 for key in formal for role in domain),
                    'The official formal Base lower-body preview did not recover within existing native pose tolerance.')
            self.report['reference_preview_verified'] = True
            self.report['reference_preview'] = {'action': reference.name, 'slot': slot,
                'motion_sha256': ref_sha, 'formal_Base_restored': True, 'input_carrier_unchanged': True,
                'reference_saved_active': False, 'actual_normalized_BASE_strip': measured,
                'native_role_domain': domain, 'existing_source_times': times, 'formal_lower_poses': formal,
                'reference_lower_poses': reference_poses, 'finite_positive_differences': differences,
                'restored_formal_lower_poses': restored, 'restoration_tolerance': 2e-4}
            self.phase = 'save_scene'
        self.checkpoint('optional_reference_public_API_finished')

    def save_scene(self):
        with self.context() as ctx:
            item, session = self.current(ctx)
            require(session['enabled'] is True and session['edit_role'] == 'BASE'
                    and not session['tweak_enabled'] and not item.rig.animation_data.use_tweak_mode,
                    'Save enabled preview with transient Tweak ended, not a fake saved editing context.')
            record, objects = self.weapon.validate_owned(item.rig)
            self.report['weapon_native_proof'] = json.loads(record['proof_json'])
            self.report['weapon_owned_objects'] = sorted(obj.name for obj in objects)
            dto = self.output / 'local_rigging_Return.json'
            with dto.open('x', encoding='utf-8') as stream:
                json.dump(self.saved_dto, stream, ensure_ascii=False, indent=2, allow_nan=False)
            self.report['local_Return'] = pin(dto, sha(dto))
            self.report['protected_action_motions'] = {'custom_base': self.base_sha,
                'source_base': self.source_sha, 'custom_input': self.input_sha}
            self.report['native_controller_presentation'] = {'sha256': digest(self.presentation_before),
                'proof': self.presentation_before}
            self.immutable()
            scene = self.output / 'new_official_cosha.blend'
            require(not scene.exists(), 'Never overwrite an existing native scene.')
            require(self.bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=str(scene), check_existing=False) == {'FINISHED'}
                    and Path(self.bpy.data.filepath).resolve() == scene, 'The independent scene was not saved successfully.')
            self.report['saved_scene'] = pin(scene, sha(scene))
            self.phase = 'open_scene'
        self.checkpoint('saved_scene_old_scope_ended')

    def tick(self):
        try:
            if self.phase == 'add_activate': self.add_activate()
            elif self.phase == 'edit_save': self.edit_save()
            elif self.phase == 'undo_inputs': self.undo_redo()
            elif self.phase == 'check_undo': self.check_undo_redo()
            elif self.phase == 'redo_inputs': self.undo_redo(redo=True)
            elif self.phase == 'check_redo': self.check_undo_redo(redo=True)
            elif self.phase == 'preview_reference': self.preview_reference()
            elif self.phase == 'save_scene': self.save_scene()
            elif self.phase == 'open_scene':
                row = self.report['saved_scene']
                pin(row['path'], row['sha256'])
                require(self.bpy.ops.wm.open_mainfile('EXEC_DEFAULT', filepath=row['path'], use_scripts=False, load_ui=False) == {'FINISHED'}, 'Owned saved scene did not reopen.')
                self.phase = 'verify_reopen'
                self.checkpoint('open_returned_new_IDs_deferred_to_next_tick')
            elif self.phase == 'verify_reopen':
                with self.context() as ctx:
                    witness = self.cached_lifecycle(ctx, 'load_post')
                    require(witness['edit_role'] == 'BASE' and witness['tweak_enabled'] is False,
                            'Load callback did not restore saved preview before manual current/Activate.')
                    item, session = self.current(ctx)
                    require(self.dto(ctx, session) == self.saved_dto and self.native._motion(item.custom_action, item.custom_slot) == self.base_sha
                            and self.native._motion(item.source_action, item.source_slot) == self.source_sha
                            and self.native._motion(session['input_action'], session['input_slot']) == self.input_sha
                            and self.presentation(item.rig) == self.presentation_before,
                            'Saved input values, base keys or twenty-component carrier changed.')
                    self.immutable()
                    self.runtime_paths()
                    self.report.update(completed=True, native_execution_performed=True,
                        formal_public_Add_Activate_verified=True, explicit_input_save_verified=True,
                        save_reopen_verified=True, automatic_saved_cache_before_manual_Activate=True,
                        callbacks=witness['callbacks'])
                    self.phase = 'done'
                    self.checkpoint('completed_control_save_only')
                if self.args.quit_on_completion:
                    with self.context():
                        returned = self.bpy.ops.wm.quit_blender('EXEC_DEFAULT')
                        self.checkpoint('normal_quit_requested', operator_result=sorted(returned), natural_exit_verified=False)
            return None if self.phase == 'done' else .5
        except Exception as error:
            self.report.update(completed=False, failure_phase=self.phase, error=str(error), traceback=traceback.format_exc())
            self.checkpoint('failed_no_retry_or_publication')
            return None

    def runtime_paths(self):
        self.report['actual_runtime_modules'] = {}
        for name, module in tuple(sys.modules.items()):
            if name == 'character_designer' or name.startswith('character_designer.'):
                require(getattr(module, '__file__', None), 'An unpinned dynamic add-on module was loaded.')
                path = Path(module.__file__).resolve()
                require(path.is_relative_to(self.root), 'An installed/cached add-on module came from another root.')
                relative = path.relative_to(self.root).as_posix()
                require(relative in self.files, 'A runtime module is absent from the complete package.')
                self.report['actual_runtime_modules'][name] = pin(path, self.files[relative]['sha256'])

    def start(self):
        import bpy
        self.bpy = bpy
        require(not bpy.app.background and tuple(bpy.app.version[:2]) == (5, 2)
                and not bpy.data.filepath and len(bpy.context.window_manager.windows) == 1
                and bpy.context.preferences.filepaths.use_scripts_auto_execute is False
                and not any(n == 'character_designer' or n.startswith('character_designer.') for n in sys.modules),
                'Use a fresh factory headful process with autoexec disabled; never an artist/old add-on process.')
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(self.root.parent))
        addon = importlib.import_module('character_designer')
        require(Path(addon.__file__).resolve() == self.root / '__init__.py', 'Complete package registration resolved elsewhere.')
        addon.register()
        for attr, name in (('worklist', 'animation_worklist'), ('workspace', 'animation_workspace'),
                ('source', 'animation_link_source'), ('target', 'animation_worklist_target'),
                ('ua', 'unity_animation'), ('native', 'unity_animation_rigging'), ('contract', 'animation_rigging_contract'),
                ('collector', 'animation_worklist_collection'), ('composition', 'animation_composition'),
                ('weapon', 'animation_composition_weapon')):
            setattr(self, attr, importlib.import_module('character_designer.' + name))
        self.packet = self.ua.load_package(self.pins['packet']['path'])
        self.contract.validate_capture(self.packet['rigging'], packet=self.packet)
        self.runtime_paths()
        self.immutable()
        self.report['native_execution_performed'] = True
        self.report['blender'] = {'pid': os.getpid(), 'version': list(bpy.app.version),
            'binary_path': bpy.app.binary_path, 'build_hash': bpy.app.build_hash.decode('ascii')}
        self.checkpoint('complete_package_registered')
        bpy.app.timers.register(self.tick, first_interval=1., persistent=True)


def main():
    run = Round(arguments())
    try:
        run.start()
    except Exception as error:
        run.report.update(completed=False, failure_phase='startup', error=str(error), traceback=traceback.format_exc())
        run.checkpoint('startup_failed')
        raise


if __name__ == '__main__':
    main()
