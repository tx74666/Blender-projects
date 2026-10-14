"""Fresh, owned headful native control/save probe; preparing this file does not run it.

This deliberately does not call Worklist Sync, an export worker, a Unity importer,
or a publication writer. Its Return result is a locally validated input DTO, not
proof of a physical FBX or Unity application. A separate fresh launch grant is
required. Every file load occurs outside a Window override; the next timer tick
reacquires the one real owned Window and all native IDs.
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


FREEZE_SHA = '71fd41971f2e7c889dcb1ff7a427ddb7cd58b6560015b658c960c067c869ed89'
PACKAGE_MANIFEST_SHA = 'ac12952c816f17ae86ac732ab18f4dcb5dc37dfa68aa39be600b27ef1d6b362f'
NATIVE_SHA = 'b459668d166ef0b20b488414f3ae115aa53dd4bbeaec0645aea4ebba2e64d04d'
INIT_SHA = 'd66a88023e93c3db64f1b64cfaf8089d4c956adc0f97896c591e34a54d8e4dd2'
QA_ID = '923c041bf09342249800cd4454c884d5'
SCHEMA = 'x.validation.fresh-native-rigging-control-save/1'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def pin(path, digest):
    path = Path(path).resolve()
    require(re.fullmatch('[0-9a-f]{64}', digest) and path.is_file()
            and sha(path) == digest, 'A required immutable input pin is missing or changed: ' + str(path))
    return {'path': str(path), 'sha256': digest, 'bytes': path.stat().st_size}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def finite(values):
    require(all(type(value) in (int, float) and math.isfinite(value) for value in values),
            'Native numeric evidence contains a non-finite or non-numeric value.')
    return [float(value) for value in values]


def matrix_rows(matrix):
    return finite([value for row in matrix for value in row])


def maximum_delta(left, right):
    require(len(left) == len(right) and bool(left), 'Native comparisons need the same nonempty domain.')
    left, right = finite(left), finite(right)
    return max(abs(a - b) for a, b in zip(left, right))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('script', 'isolated-clone', 'actualpacket', 'prepared-link',
                 'source-freeze', 'package-manifest', 'protected-artist'):
        if name != 'script':
            parser.add_argument('--' + name, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    for name in ('addon-root', 'output-root', 'scene-name', 'rig-name', 'work-item-id'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--confirm-isolated-headful', action='store_true', required=True)
    # Completion requests a quit in a fresh owning Window scope. FINISHED is
    # only the operator return; the external owner must record natural exit.
    parser.add_argument('--quit-on-completion', action='store_true')
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return parser.parse_args(argv)


def admit(args):
    script = Path(__file__).resolve()
    pin(script, args.script_sha256)
    rows = {}
    for name in ('isolated_clone', 'actualpacket', 'prepared_link', 'source_freeze',
                 'package_manifest', 'protected_artist'):
        rows[name] = pin(getattr(args, name), getattr(args, name + '_sha256'))
    fresh = script.parent
    clone, artist = Path(rows['isolated_clone']['path']), Path(rows['protected_artist']['path'])
    require(clone.suffix.lower() == '.blend' and clone != artist
            and clone.is_relative_to(fresh) and not artist.is_relative_to(fresh),
            'Use a separately hash-pinned clone inside this fresh scope, never the artist file.')
    require(args.source_freeze_sha256 == FREEZE_SHA
            and args.package_manifest_sha256 == PACKAGE_MANIFEST_SHA,
            'Use the reviewed r4 Source freeze and its exact complete package manifest.')
    freeze = read_json(rows['source_freeze']['path'])
    require(freeze['schema'] == 'cdesigner.x-rigging-source-freeze/1'
            and freeze['status'] == 'SOURCE_FROZEN_NATIVE_PENDING'
            and freeze['source_only'] is True and freeze['native_execution_performed'] is False,
            'The Source freeze contract changed.')
    root = Path(args.addon_root).resolve()
    manifest = read_json(rows['package_manifest']['path'])
    require(root.name == 'character_designer' and root.is_dir()
            and manifest.get('module') == 'character_designer'
            and type(manifest.get('schema_version')) is int and manifest['schema_version'] == 1
            and manifest.get('version') == '0.77.25'
            and type(manifest.get('source_provenance')) is dict and bool(manifest['source_provenance'])
            and Path(manifest['source_root']).resolve() == root
            and type(manifest.get('files')) is dict and bool(manifest['files']),
            'Pin one complete isolated package using the existing source_root/files projection contract.')
    package_pins = {}
    for relative, expected in manifest['files'].items():
        path = root / relative
        require(type(relative) is str and not Path(relative).is_absolute()
                and path.resolve().is_relative_to(root) and '__pycache__' not in path.parts,
                'A package file leaves its admitted root.')
        package_pins[relative] = pin(path, expected)
    actual = {str(path.relative_to(root)).replace('\\', '/') for path in root.rglob('*') if path.is_file()}
    require(actual == set(package_pins), 'The isolated package has missing or additional files before import.')
    require(package_pins['__init__.py']['sha256'] == INIT_SHA
            and package_pins['unity_animation_rigging.py']['sha256'] == NATIVE_SHA,
            'The actual init or native module differs from the frozen implementation.')
    for row in freeze['source_pins']:
        path = Path(row['path'])
        if 'addons' in path.parts:
            require(package_pins[path.name]['sha256'] == row['sha256']
                    and package_pins[path.name]['bytes'] == row['bytes'],
                    'A frozen Rigging runtime leaf is not present exactly in the complete package.')
    packet = read_json(rows['actualpacket']['path'])
    capture = packet.get('rigging')
    require(type(capture) is dict and capture.get('previewEnabled') is True,
            'Use the complete genuine packet with its explicit enabled preview choice.')
    work_id = uuid.UUID(args.work_item_id).hex
    require(uuid.UUID(work_id).int != 0 and work_id != capture['newActionId']
            and work_id != QA_ID, 'The real Unity WorkID must be independent of the draft and QA directory UUID.')
    link = read_json(rows['prepared_link']['path'])
    require(uuid.UUID(link['workItemId']).hex == work_id
            and Path(link['sourcePackage']).resolve() == Path(rows['actualpacket']['path'])
            and link['sourcePackageSha256'].lower() == rows['actualpacket']['sha256']
            and all(link[key] == packet[key] for key in ('targetGuid', 'clipGuid', 'clipLocalId')),
            'The externally prepared typed Link must bind this exact packet and real WorkID.')
    output = Path(args.output_root).resolve()
    require(output != fresh and output.is_relative_to(fresh)
            and not clone.is_relative_to(output) and len(str(output).encode('utf-16-le')) // 2 < 210,
            'Use a fresh short output child, separate from the immutable clone.')
    require(output.is_dir() and {path.name for path in output.iterdir()} == {'CONFIG', 'DATAFILES'}
            and all((output / name).is_dir() and not any((output / name).iterdir())
                    for name in ('CONFIG', 'DATAFILES')),
            'The fresh caller must create only empty owned CONFIG/DATAFILES siblings before launch.')
    for key, name in (('BLENDER_USER_CONFIG', 'CONFIG'), ('BLENDER_USER_DATAFILES', 'DATAFILES')):
        require(os.environ.get(key) and Path(os.environ[key]).resolve() == output / name,
                'The isolated process must use its own exact profile roots.')
    return rows, root, package_pins, work_id, output


class Round:
    def __init__(self, args, rows, root, package_pins, work_id, output):
        self.args, self.rows, self.root = args, rows, root
        self.package_pins, self.work_id, self.output = package_pins, work_id, output
        self.phase = 'import_and_edit'
        self.saved = {}
        self.report_path = output / 'native_control_save_report.json'
        self.report = {'schema': SCHEMA, 'completed': False, 'native_execution_performed': False,
            'scope': 'native-control-save-and-local-Return-DTO', 'physical_fbx_verified': False,
            'unity_application_verified': False, 'weapon_visual_acceptance_verified': False,
            'ui_buttons_and_screenshots_verified': False, 'base_leg_edit_verified': False,
            'linked_worklist_Source_verified': False,
            'source_inputs': rows, 'package_root': str(root), 'package_files': package_pins,
            'package_file_count': len(package_pins), 'package_bytes': sum(row['bytes'] for row in package_pins.values()),
            'workItemId': work_id, 'sceneName': args.scene_name, 'rigName': args.rig_name,
            'checkpoints': [], 'quit_requested': False, 'natural_exit_verified': False}
        with self.report_path.open('x', encoding='utf-8') as stream:
            json.dump(self.report, stream, ensure_ascii=False, indent=2, allow_nan=False)

    def checkpoint(self, name, **fields):
        self.report['current_phase'] = name
        self.report['checkpoints'].append({'phase': name, **fields})
        # This one owned progress report is intentionally rewritten durably;
        # no pre-existing output or failed previous attempt is overwritten.
        with self.report_path.open('w', encoding='utf-8') as stream:
            json.dump(self.report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())

    def verify_immutable(self):
        for row in self.rows.values():
            pin(row['path'], row['sha256'])
        for row in self.package_pins.values():
            pin(row['path'], row['sha256'])
        for row in self.report.get('optional_weapon_input_pins', {}).values():
            pin(row['path'], row['sha256'])

    @contextmanager
    def context(self, *, view=False):
        bpy = self.bpy
        require(not bpy.app.background, 'Native Tweak editing requires the fresh headful owning Window.')
        windows = tuple(bpy.context.window_manager.windows)
        scenes = [scene for scene in bpy.data.scenes if scene.name == self.args.scene_name]
        require(len(windows) == 1 and len(scenes) == 1 and scenes[0].library is None,
                'Reacquire the one real owned Window and exact local Scene after every load.')
        window = windows[0]
        if window.scene != scenes[0]:
            window.scene = scenes[0]
        with bpy.context.temp_override(window=window):
            ctx = bpy.context
            require(ctx.window == window and ctx.scene == scenes[0]
                    and ctx.view_layer == window.view_layer
                    and ctx.preferences.filepaths.use_scripts_auto_execute is False,
                    'The owning Window override or disabled auto-execution policy changed.')
            for name, key in (('CONFIG', 'BLENDER_USER_CONFIG'), ('DATAFILES', 'BLENDER_USER_DATAFILES')):
                require(Path(bpy.utils.user_resource(name, create=False)).resolve()
                        == Path(os.environ[key]).resolve(), 'The actual process profile changed.')
            if view:
                areas = [area for area in window.screen.areas if area.type == 'VIEW_3D']
                require(len(areas) == 1, 'Use the unique factory View3D; do not create an uninitialized native area.')
                regions = [region for region in areas[0].regions if region.type == 'WINDOW']
                require(len(regions) == 1, 'The native View3D needs its actual Window region.')
                with bpy.context.temp_override(area=areas[0], region=regions[0]):
                    yield bpy.context
            else:
                yield ctx

    def rig(self, ctx):
        candidates = [obj for obj in self.bpy.data.objects if obj.name == self.args.rig_name]
        require(len(candidates) == 1 and candidates[0].type == 'ARMATURE'
                and not candidates[0].library and not candidates[0].data.library
                and candidates[0] in tuple(ctx.scene.objects)
                and candidates[0] in tuple(ctx.view_layer.objects), 'The exact original local Rig is not in the owning Scene/layer.')
        return candidates[0]

    def pose(self, ctx, rig):
        if ctx.object is not None and ctx.object.mode != 'OBJECT' and ctx.object != rig:
            require(self.bpy.ops.object.mode_set(mode='OBJECT') == {'FINISHED'}, 'Could not leave the other isolated object mode.')
        for obj in ctx.selected_objects:
            obj.select_set(False)
        rig.select_set(True)
        ctx.view_layer.objects.active = rig
        if rig.mode != 'POSE':
            require(self.bpy.ops.object.mode_set(mode='POSE') == {'FINISHED'}, 'Could not enter the actual original Rig Pose mode.')
        require(ctx.pose_object == rig and ctx.active_object == rig and ctx.mode == 'POSE',
                'The exact native Pose owner changed.')

    def graph(self, rig):
        def reference(obj):
            return None if obj is None else [obj.bl_rna.identifier, obj.name,
                obj.library.filepath if obj.library else None]
        def color(value):
            return [value.palette, list(value.custom.normal), list(value.custom.select), list(value.custom.active)]
        refs = {}
        display = self.composition._encode(self.native.bone_display._snapshot(rig), refs)
        return {'bones': sorted(rig.data.bones.keys()), 'rest': self.ua._rest_state(rig.data),
            'display_snapshot': {'payload': display, 'refs': {key: reference(value) for key, value in refs.items()}},
            'colors': {pb.name: {'pose': color(pb.color), 'bone': color(pb.bone.color)} for pb in rig.pose.bones},
            'controllers': {pb.name: {'shape': reference(pb.custom_shape),
                'shape_transform': pb.custom_shape_transform.name if pb.custom_shape_transform else None,
                'constraints': [[con.name, con.type, reference(getattr(con, 'target', None)),
                    getattr(con, 'subtarget', None), reference(getattr(con, 'pole_target', None)),
                    getattr(con, 'pole_subtarget', None)] for con in pb.constraints]} for pb in rig.pose.bones},
            'collections': {item.name: {'parent': item.parent.name if item.parent else None,
                'members': sorted(item.bones.keys()), 'visible': item.is_visible, 'solo': item.is_solo}
                for item in rig.data.collections_all},
            'visibility': {pb.name: [pb.hide, pb.bone.hide, pb.bone.hide_select] for pb in rig.pose.bones},
            'locks': {pb.name: [list(pb.lock_location), list(pb.lock_rotation), list(pb.lock_scale),
                pb.lock_rotation_w, pb.lock_rotations_4d] for pb in rig.pose.bones}}

    def session(self, ctx):
        rig = self.rig(ctx)
        session = self.native.current(rig)
        require(session is not None and session['scene'] == ctx.scene
                and session['source_packet_sha256'] == self.rows['actualpacket']['sha256']
                and session['work_item_id'] == self.work_id, 'The persistent native owner changed.')
        return rig, session

    def reacquired_before_manual_operation(self, ctx, boundary):
        # Check only the already authenticated cache first. Calling current,
        # seek or Activate before this check could conceal a missing lifecycle
        # callback. Native read-only validation follows the cache witness.
        rig = self.rig(ctx)
        cached = self.native.display_state(rig)
        require(cached is not None and cached['rig'] == rig and cached['scene'] == ctx.scene,
                'The owned lifecycle callback did not reacquire the saved native session.')
        counts = {}
        for name, callback in (('load_post', self.native._reacquire),
                ('undo_post', self.native._reacquire), ('redo_post', self.native._reacquire),
                ('frame_change_post', self.native._frame), ('depsgraph_update_post', self.native._depsgraph)):
            counts[name] = sum(item is callback for item in getattr(self.bpy.app.handlers, name))
        require(all(value == 1 for value in counts.values()) and not self.native._HANDLER_ERRORS,
                'The five owned callbacks are absent, duplicated or reported a native owner error.')
        witness = {'boundary': boundary, 'callbacks': counts,
            'base_action': cached['base_action'].name, 'input_action': cached['input_action'].name,
            'edit_role': cached['edit_role'], 'enabled': cached['enabled'],
            'tweak_enabled': cached['tweak_enabled'], 'source_read_only': cached['source_read_only'],
            'manual_seek_or_activate_before_check': False}
        self.report.setdefault('lifecycle_before_manual_operation', []).append(witness)
        del cached
        rig, session = self.session(ctx)
        require(session['base_action'].name == self.saved['base_name']
                and session['base_slot'] == self.saved['base_slot']
                and session['input_action'].name == self.saved['input_name']
                and session['input_slot'] == self.saved['input_slot']
                and session['new_action_id'] == self.saved['draft_id']
                and self.native._motion(session['base_action'], session['base_slot']) == self.saved['base_motion'],
                'A lifecycle boundary changed the original base or the input owner/slot.')
        return rig, session

    def weapon_proof(self, rig, session):
        expected = session['capture'].get('weaponPreview')
        require(session['capture'] == self.contract.validate_capture(session['capture']),
                'The native session changed the complete captured input contract.')
        if expected is None:
            require('weapon_preview' not in session, 'A no-weapon packet acquired an unrelated display.')
            return {'packet_has_weaponPreview': False, 'native_display_proof': None,
                    'visual_acceptance_verified': False}
        record, objects = self.weapon.validate_owned(rig)
        proof = json.loads(record['proof_json'])
        require(record['rigging_session_owner'] == session['owner']
                and record['owner'] == session['weapon_preview']['display_owner']
                and record['identity'] == session['weapon_preview']['identity']
                and proof['captured_unity_geometry'] is True and proof['actual_fbx_import'] is False
                and proof['prefab_scale_applied_once'] is True and proof['automatic_hand_ik'] is False,
                'The optional display must retain its real captured geometry and exact owning session.')
        return {'packet_has_weaponPreview': True, 'native_display_proof': proof,
            'owned_objects': sorted(obj.name for obj in objects),
            'capture_weapon_sha256': digest(expected), 'visual_acceptance_verified': False}

    def return_dto(self, ctx, session):
        before = [self.native._motion(session['base_action'], session['base_slot']),
            self.native._motion(session['input_action'], session['input_slot']),
            ctx.scene.frame_current, ctx.scene.frame_subframe, session['rig'][self.native.SESSION_KEY]]
        result = self.native.capture_inputs(ctx, session,
            source_packet_sha256=self.rows['actualpacket']['sha256'], work_item_id=self.work_id,
            source_action=session['base_action'], source_action_slot=session['base_slot'])
        result = self.contract.validate_export(result, session['capture'],
            source_packet_sha256=self.rows['actualpacket']['sha256'], work_item_id=self.work_id,
            new_action_id=session['new_action_id'], source_action=session['base_action'].name,
            source_action_slot=session['base_slot'], target_input_action=session['input_action'].name,
            target_input_action_slot=session['input_slot'])
        after = [self.native._motion(session['base_action'], session['base_slot']),
            self.native._motion(session['input_action'], session['input_slot']),
            ctx.scene.frame_current, ctx.scene.frame_subframe, session['rig'][self.native.SESSION_KEY]]
        require(before == after, 'Reading the Return DTO mutated keys, time or persistent native ownership.')
        require(len(self.native._curves(session['input_action'], session['input_slot'])) == 20,
                'Only the exact twenty Target/Hint input curves are admitted.')
        return result

    def seek(self, ctx, session, seconds):
        require(math.isfinite(seconds) and 0 <= seconds <= session['capture']['duration'], 'Use an admitted source phase.')
        frame = session['scene_start'] + seconds * (ctx.scene.render.fps / ctx.scene.render.fps_base)
        self.ua._set_frame(ctx.scene, frame)
        ctx.view_layer.update()
        session = self.native.current(session['rig'])
        require(session is not None and session['enabled'] and not self.native._HANDLER_ERRORS,
                'A native owned handler failed; the probe does not replay or repair it.')
        return session

    def select(self, ctx, session, name):
        rig, pb = session['rig'], session['rig'].pose.bones[name]
        require(not pb.hide and not pb.bone.hide_select
                and not any(pb.lock_location), 'The exact Target/Hint must be editable and visible without reveal overrides.')
        memberships = tuple(pb.bone.collections)
        solo = any(item.is_solo for item in rig.data.collections_all)
        require((not memberships and not solo) or any(item.is_visible_effectively for item in memberships),
                'The native input is in a hidden effective Bone Collection; no flags are changed by the probe.')
        rig.data.bones.active = pb.bone
        for bone in rig.pose.bones:
            self.composition._pose_selection_owner(bone).select = bone.name == name
        require(ctx.active_pose_bone == pb and tuple(ctx.selected_pose_bones or ()) == (pb,),
                'Actual context selection differs from the single owned Target/Hint.')
        ad = rig.animation_data
        require(ad.use_tweak_mode and ad.action == session['input_action']
                and ad.action_slot_handle == session['input_slot']
                and session['edit_role'] == 'RIGGING' and session['tweak_enabled']
                and not ctx.scene.tool_settings.use_keyframe_insert_auto,
                'Use the exact input carrier Tweak with Auto Key off.')
        return pb

    def independent_base(self, ctx, rig, session):
        before = self.native._motion(session['base_action'], session['base_slot'])
        preview = {name: matrix_rows(rig.pose.bones[name].matrix_basis)
            for row in session['native_bindings'] for name in (row['target'], row['pole'])}
        with self.native.base_only(ctx, rig, action=session['base_action']):
            with self.native.base_only(ctx, rig, action=session['base_action']):
                ad = rig.animation_data
                require(not ad.use_tweak_mode and not ad.use_nla and ad.action == session['base_action']
                        and ad.action_slot_handle == session['base_slot'], 'Nested base_only does not bind the independent base.')
                for row in session['native_bindings']:
                    entry = self.native._inventory(session)['rigs']['ARM', row['native_side']]
                    require(self.fk.mode_for_rig(rig, entry) == 'FK', 'Preview IK leaked into the independent base.')
                # Test snapshot reference isolation without writing a library or invoking a worker.
                with self.native.snapshot_base_refs(rig, session['base_action']):
                    require(self.native.SESSION_KEY not in rig
                            and self.native._INPUT_REF not in session['base_action'],
                            'Owned forward references were not hidden for a base-only snapshot.')
                require(self.native.SESSION_KEY in rig and self.native._INPUT_REF in session['base_action'],
                        'Snapshot references did not restore exactly.')
        require(self.native._motion(session['base_action'], session['base_slot']) == before
                and preview == {name: matrix_rows(rig.pose.bones[name].matrix_basis)
                    for row in session['native_bindings'] for name in (row['target'], row['pole'])},
                'Base-only isolation changed the base keys or lost live input matrices.')
        return {'base_motion_sha256': before, 'nested_base_only': True, 'snapshot_refs_restored': True,
                'native_arm_modes_inside': ['FK', 'FK'], 'combined_pose_baked_into_base': False}

    def import_and_edit(self):
        with self.context(view=True) as ctx:
            rig = self.rig(ctx)
            require(not any(self.native.SESSION_KEY in obj for obj in self.bpy.data.objects),
                    'This isolated clone must not contain another persisted Rigging preview owner.')
            require(self.target.managed(rig) and self.target.is_adopted(rig),
                    'Use the managed adopted native Rig clone; translation-data ownership cannot be guessed.')
            require(self.native.current(rig) is None and not self.composition.active(rig)
                    and not self.ua.active_preview(rig) and not (rig.animation_data and rig.animation_data.use_tweak_mode),
                    'The isolated clone must begin outside another motion or Tweak session.')
            self.pose(ctx, rig)
            self.target.ensure_active(ctx, rig)
            self.report['adoption_admission'] = {'existing_managed_record_authenticated': True,
                'scene_view_layer_workspace_rig_Rest_saved_packet_action_validated': True,
                'new_adoption_or_workspace_created': False,
                'prepared_Link_model_association_verified': False}
            packet = self.ua.load_package(self.rows['actualpacket']['path'])
            capture = self.contract.validate_capture(packet['rigging'], packet=packet)
            preview = capture.get('weaponPreview')
            self.report['optional_weapon_input_pins'] = {} if preview is None else {
                'weapon_context': pin(preview['weaponContextFile'], preview['weaponContextSha256']),
                'weapon_model': pin(preview['weaponModelFile'], preview['weaponModelSha256'])}
            link = read_json(self.rows['prepared_link']['path'])
            self.link._validate_identity(link)
            require(packet['_sha256'] == self.rows['actualpacket']['sha256'], 'The actual package changed after admission.')
            self.report['actual_packet'] = {'targetGuid': packet['targetGuid'], 'clipGuid': packet['clipGuid'],
                'clipLocalId': packet['clipLocalId'], 'duration': packet['duration'], 'sampleRate': packet['sampleRate'],
                'base_frame_count': len(packet['frames']), 'input_frame_count': len(capture['frames']),
                'newActionId': capture['newActionId'], 'bindingsSha256': capture['bindingsSha256'],
                'previewEnabled': capture['previewEnabled'],
                'weaponPreview_present': capture.get('weaponPreview') is not None,
                'capture_sha256': self.contract.capture_digest(capture)}
            original = self.graph(rig)
            self.checkpoint('before_base_import', native_execution_performed=True,
                original_graph_sha256=digest(original), actual_clock=[ctx.scene.render.fps, ctx.scene.render.fps_base])
            result = self.source._import_action(ctx, rig, packet, 1., native_timebase=True)
            base = result.action
            self.target.restore_import_preview(ctx, rig, base)
            self.worklist._clean_action(base)
            base.name = 'Native QA · Base ' + packet['clipName']
            slot = self.worklist._slot(base).handle
            rig.animation_data_create().action = base
            rig.animation_data.action_slot = self.composition._slot(base, slot)
            require(self.ua.active_preview(rig) is None and self.ua.native_action_frame_rate(base) == capture['sampleRate'],
                    'The ordinary import preview was not restored on the authenticated packet clock.')
            baseline_graph = self.graph(rig)
            # Rest/data names can change under the already authenticated import
            # transaction; the original controller/color/collection graph cannot.
            require(all(original[key] == baseline_graph[key] for key in
                ('bones', 'colors', 'controllers', 'collections')), 'Base import replaced the original controllers or presentation graph.')
            self.saved['closed_graph'] = baseline_graph
            session = self.native.import_inputs(ctx, rig, packet, base_action=base, base_slot=slot,
                work_item_id=self.work_id)
            require(session is not None and session['enabled'] and session['capture']['previewEnabled'] is True,
                    'The explicit Unity previewEnabled choice was not honored.')
            require(session['capture'] == capture, 'The importer omitted or changed original captured fields.')
            self.report['optional_weapon'] = self.weapon_proof(rig, session)
            self.pose(ctx, rig)
            session = self.native.activate(ctx, session, edit_role='RIGGING', enabled=True)
            base_motion = self.native._motion(base, slot)
            initial = self.return_dto(ctx, session)
            index = len(capture['frames']) // 2
            seconds = capture['frames'][index]['time']
            session = self.seek(ctx, session, seconds)
            require(self.bpy.ops.ed.undo_push.poll(), 'The isolated native undo checkpoint cannot be created.')
            returned = self.bpy.ops.ed.undo_push('EXEC_DEFAULT', message='Native QA · Before Input Save')
            require(returned == {'FINISHED'}, 'The real pre-edit undo checkpoint was not created.')
            self.checkpoint('undo_checkpoint_before_input_edits', operator_result=sorted(returned))
            edits = []
            for side_index, row in enumerate(session['native_bindings']):
                for field, name in (('targetPosition', row['target']), ('hintPosition', row['pole'])):
                    session = self.native.current(rig)
                    pb = self.select(ctx, session, name)
                    before = matrix_rows(pb.matrix_basis)
                    input_before = self.native._motion(session['input_action'], session['input_slot'])
                    self.report['pendingNativeOperator'] = True
                    self.checkpoint('before_native_translate', control=name, field=field, source_time=seconds,
                        raw_frame=ctx.scene.frame_current + ctx.scene.frame_subframe,
                        selected_pose_bones=[item.name for item in ctx.selected_pose_bones], pendingNativeOperator=True)
                    require(self.bpy.ops.transform.translate.poll(), 'The real native transform poll failed.')
                    returned = self.bpy.ops.transform.translate('EXEC_DEFAULT', True,
                        value=(.005, 0., 0.), orient_type='LOCAL')
                    ctx.view_layer.update()
                    after = matrix_rows(rig.pose.bones[name].matrix_basis)
                    delta = maximum_delta(before, after)
                    self.checkpoint('native_translate_returned', control=name, operator_result=sorted(returned),
                        native_basis_before=before, native_basis_after=after, native_basis_delta=delta,
                        pendingNativeOperator=True)
                    require(returned == {'FINISHED'} and delta > 1e-7, 'A native input did not actually move.')
                    self.report['pendingNativeOperator'] = False
                    self.checkpoint('native_input_verified', control=name, pendingNativeOperator=False,
                        literal_FINISHED=True, finite_positive_delta=delta)
                    require(self.native._motion(session['input_action'], session['input_slot']) == input_before,
                            'Auto Key or another operation keyed inputs before explicit Save Rigging.')
                    saved = self.native.key_current(ctx, session)
                    dto = self.return_dto(ctx, session)
                    change = maximum_delta(initial['frames'][index]['controls'][side_index][field],
                        dto['frames'][index]['controls'][side_index][field])
                    require(change > 1e-7 and self.native._motion(base, slot) == base_motion,
                            'Explicit Save Rigging did not preserve a changed local input independently of base keys.')
                    edits.append({'control': name, 'side_index': side_index, 'field': field,
                        'operator_result': sorted(returned), 'native_basis_delta': delta,
                        'saved_local_delta': change, 'explicit_saved_values': saved[side_index][field]})
            final_dto = self.return_dto(ctx, session)
            self.report['input_edit_witnesses'] = edits
            self.report['base_isolation'] = self.independent_base(ctx, rig, session)
            # Store only detached names/slots/hashes/DTOs. Actual Undo replaces
            # native IDs; every subsequent operator and readback is a new tick.
            session = self.native.activate(ctx, session, edit_role='BASE', enabled=False)
            require(session['enabled'] is True and session['edit_role'] == 'BASE'
                    and session['tweak_enabled'] is False and not rig.animation_data.use_tweak_mode,
                    'Checkpoint the enabled preview with transient native Tweak ended.')
            self.saved.update(base_name=base.name, base_slot=slot, base_motion=base_motion,
                input_name=session['input_action'].name, input_slot=session['input_slot'],
                input_motion=self.native._motion(session['input_action'], session['input_slot']),
                draft_id=session['new_action_id'], scene_name=ctx.scene.name, source_time=seconds, dto=final_dto)
            require(self.bpy.ops.ed.undo_push.poll(), 'The saved-input native undo checkpoint cannot be created.')
            returned = self.bpy.ops.ed.undo_push('EXEC_DEFAULT', message='Native QA · Saved Input Keys')
            require(returned == {'FINISHED'}, 'The real post-save undo checkpoint was not created.')
            self.checkpoint('undo_checkpoint_after_input_saves', operator_result=sorted(returned),
                input_motion_sha256=self.saved['input_motion'], base_motion_sha256=base_motion)
            self.phase = 'undo_inputs'
        self.checkpoint('saved_input_undo_scope_ended')

    def undo_or_redo(self, redo=False):
        # No native object is dereferenced after the operator. The old context
        # override ends before a later tick obtains new IDs from actual data.
        name = 'redo' if redo else 'undo'
        with self.context(view=True):
            operator = self.bpy.ops.ed.redo if redo else self.bpy.ops.ed.undo
            require(operator.poll(), 'The actual isolated native ' + name + ' poll failed.')
            self.checkpoint('before_real_' + name, new_native_readback_deferred=True)
            returned = operator('EXEC_DEFAULT')
            require(returned == {'FINISHED'}, 'The actual isolated native ' + name + ' was not FINISHED.')
            del operator
        self.phase = 'check_redo' if redo else 'check_undo'
        self.checkpoint('real_' + name + '_scope_ended', operator_result=sorted(returned))

    def check_undo(self):
        with self.context(view=True) as ctx:
            rig, session = self.reacquired_before_manual_operation(ctx, 'undo_post')
            motion = self.native._motion(session['input_action'], session['input_slot'])
            require(motion != self.saved['input_motion'],
                    'Actual Undo did not undo any explicit saved input keys.')
            self.report['undo_saved_inputs'] = {'operator_FINISHED': True,
                'input_motion_before': self.saved['input_motion'], 'input_motion_after': motion,
                'base_motion_unchanged': True, 'native_IDs_reacquired_after_operator': True}
            self.phase = 'redo_inputs'
        self.checkpoint('real_undo_readback_complete')

    def check_redo(self):
        with self.context(view=True) as ctx:
            rig, session = self.reacquired_before_manual_operation(ctx, 'redo_post')
            require(self.native._motion(session['input_action'], session['input_slot']) == self.saved['input_motion']
                    and self.return_dto(ctx, session) == self.saved['dto'],
                    'Actual Redo did not recover exact saved input curves and Return values.')
            self.report['redo_saved_inputs'] = {'operator_FINISHED': True,
                'input_motion_restored_exactly': True, 'Return_values_restored_exactly': True,
                'base_motion_unchanged': True, 'native_IDs_reacquired_after_operator': True}
            self.phase = 'finish_checks'
        self.checkpoint('real_redo_readback_complete')

    def finish_checks(self):
        with self.context(view=True) as ctx:
            rig, session = self.session(ctx)
            self.pose(ctx, rig)
            packet = self.ua.load_package(self.rows['actualpacket']['path'])
            base, slot = session['base_action'], session['base_slot']
            base_motion, final_dto = self.saved['base_motion'], self.saved['dto']
            baseline_graph, seconds = self.saved['closed_graph'], self.saved['source_time']
            require(packet['_sha256'] == self.rows['actualpacket']['sha256']
                    and self.native._motion(session['input_action'], session['input_slot']) == self.saved['input_motion'],
                    'The real Redo readback changed before subsequent ownership checks.')
            # Simulate the same native owned transaction close/rollback API used
            # by Worklist, without changing any existing workspace or row.
            original_ids = [base.as_pointer(), session['input_action'].as_pointer()]
            input_motion = self.native._motion(session['input_action'], session['input_slot'])
            weapon_before = self.weapon_proof(rig, session)
            weapon_ids = None
            if session['capture'].get('weaponPreview') is not None:
                record, objects = self.weapon.validate_owned(rig)
                weapon_ids = sorted(obj.as_pointer() for obj in objects)
                del record, objects
            token = self.native._capture_owned(ctx, rig)
            self.native.restore_owned(ctx, rig)
            require(self.graph(rig) == baseline_graph, 'Close did not restore entry controllers/collections/colors/locks exactly.')
            self.native._restore_owned_state(ctx, rig, token)
            session = self.native.current(rig)
            require(token['status'] == 'restored' and original_ids ==
                    [session['base_action'].as_pointer(), session['input_action'].as_pointer()]
                    and self.native._motion(session['input_action'], session['input_slot']) == input_motion,
                    'Owned rollback replaced the committed input or base native ID.')
            require(self.weapon_proof(rig, session) == weapon_before,
                    'Owned rollback changed the optional display proof.')
            if weapon_ids is not None:
                record, objects = self.weapon.validate_owned(rig)
                require(sorted(obj.as_pointer() for obj in objects) == weapon_ids,
                        'Owned display rollback replaced original native geometry IDs.')
                del record, objects
            self.report['transaction_rollback'] = {'same_base_and_input_native_IDs': True,
                'input_motion_sha256': input_motion,
                'optional_weapon_native_ID_rollback_tested': weapon_ids is not None,
                'optional_weapon_visual_acceptance_verified': False}
            self.native.restore_owned(ctx, rig)
            source_session = self.native.import_inputs(ctx, rig, packet, base_action=base,
                base_slot=slot, work_item_id=self.work_id, source=True)
            source_before = self.native._motion(source_session['input_action'], source_session['input_slot'])
            rejected = None
            try:
                self.native.key_current(ctx, source_session)
            except ValueError as error:
                rejected = str(error)
            require(rejected is not None and self.native._motion(source_session['input_action'],
                source_session['input_slot']) == source_before and self.native._motion(base, slot) == base_motion,
                'The native Source input carrier did not reject editing read-only.')
            self.report['read_only_source_input'] = {'rejected': rejected,
                'input_motion_sha256': source_before, 'linked_worklist_Source_tested': False}
            self.native.restore_owned(ctx, rig)
            session = self.native.import_inputs(ctx, rig, packet, base_action=base, base_slot=slot, work_item_id=self.work_id)
            require(session['input_action'].as_pointer() == original_ids[1]
                    and self.return_dto(ctx, session) == final_dto,
                    'Custom reactivation replaced the committed draft with original packet inputs.')
            session = self.seek(ctx, session, seconds)
            session = self.native.activate(ctx, session, edit_role='BASE', enabled=False)
            # Persist stable full-stack ownership; transient Tweak is explicitly
            # resumed after reload instead of assuming a saved operator context.
            require(session['enabled'] is True and session['edit_role'] == 'BASE'
                    and session['tweak_enabled'] is False and not rig.animation_data.use_tweak_mode,
                    'Save the enabled full preview in BASE role without a transient Tweak owner.')
            dto = self.return_dto(ctx, session)
            require(dto == final_dto, 'Source/Custom ownership checks changed committed input values.')
            self.saved['preview_state'] = {'enabled': True, 'edit_role': 'BASE',
                'tweak_enabled': False, 'source_read_only': False}
            self.saved['active_frame'] = ctx.scene.frame_current + ctx.scene.frame_subframe
            path = self.output / 'rigging_inputs_return.json'
            with path.open('x', encoding='utf-8') as stream:
                json.dump(dto, stream, ensure_ascii=False, indent=2, allow_nan=False)
            self.report['local_return_dto'] = pin(path, sha(path))
            self.report['twenty_control_curves'] = sorted([path, component] for path, component
                in self.native._curves(session['input_action'], session['input_slot']))
            self.verify_immutable()
            self.save(ctx, 'active.blend')
            self.phase = 'open_active'
        self.checkpoint('saved_active_scope_ended')

    def save(self, ctx, name):
        path = self.output / name
        require(not path.exists(), 'Never overwrite an existing native scene artifact.')
        self.checkpoint('before_save_' + name, save_path=str(path))
        returned = self.bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=str(path), check_existing=False)
        require(returned == {'FINISHED'} and Path(self.bpy.data.filepath).resolve() == path and path.is_file(),
                'Blender did not save the exact new isolated scene artifact.')
        self.report[name] = pin(path, sha(path))
        self.checkpoint('saved_' + name)

    def reopen(self, name, next_phase):
        # No native context or RNA reference is retained in this phase or in
        # self.saved. open_mainfile clears Window context even with load_ui=False.
        require(self.bpy.context.window is None or self.bpy.context.window in tuple(self.bpy.context.window_manager.windows),
                'The outside-load context has an unknown Window.')
        row = self.report[name]
        pin(row['path'], row['sha256'])
        self.checkpoint('before_open_' + name, old_override_ended=True)
        returned = self.bpy.ops.wm.open_mainfile('EXEC_DEFAULT', filepath=row['path'], use_scripts=False, load_ui=False)
        require(returned == {'FINISHED'}, 'The exact isolated saved scene did not reopen.')
        self.phase = next_phase
        self.checkpoint('open_returned_' + name, new_native_IDs_deferred_to_next_tick=True)

    def check_reopened(self):
        with self.context(view=True) as ctx:
            rig, session = self.reacquired_before_manual_operation(ctx, 'load_post')
            cached_witness = self.report['lifecycle_before_manual_operation'][-1]
            require(all(cached_witness[key] == value for key, value in self.saved['preview_state'].items())
                    and all(session[key] == value for key, value in self.saved['preview_state'].items())
                    and not rig.animation_data.use_tweak_mode
                    and abs(ctx.scene.frame_current + ctx.scene.frame_subframe - self.saved['active_frame']) <= 1e-7,
                    'Saved enabled BASE preview role/frame was not restored before any manual operation.')
            require(self.native._motion(session['input_action'], session['input_slot']) == self.saved['input_motion']
                    and self.return_dto(ctx, session) == self.saved['dto'],
                    'Saved/reopened identities, slots, keys or Return source-local inputs changed.')
            self.report['saved_enabled_preview_before_manual_activation'] = {
                **self.saved['preview_state'], 'source_frame_restored': True,
                'five_callbacks_exact_once': True, 'persistent_native_IDs_authenticated': True,
                'load_callback_is_read_only': True, 'automatic_solver_pose_evaluation_claimed': False}
            self.report['weapon_after_saved_reopen'] = self.weapon_proof(rig, session)
            self.pose(ctx, rig)
            session = self.seek(ctx, session, self.saved['source_time'])
            session = self.native.activate(ctx, session, edit_role='RIGGING', enabled=True)
            require(session['tweak_enabled'] and self.return_dto(ctx, session) == self.saved['dto'],
                    'The restored input draft cannot resume its exact native Tweak owner.')
            endpoints = []
            for time in (0., session['capture']['duration']):
                session = self.seek(ctx, session, time)
                measured = self.native._time(ctx, session)
                require(abs(measured - time) <= 1e-7, 'The source endpoint wrapped or used the wrong Scene/native clock.')
                endpoints.append({'source_time': time, 'native_source_time': measured,
                    'scene_frame': ctx.scene.frame_current + ctx.scene.frame_subframe})
            self.report['save_reopen'] = {'same_action_names_slots_keys_and_Return': True,
                'saved_enabled_BASE_preview_restored_before_manual_activate': True,
                'native_RIGGING_tweak_explicitly_resumed': True, 'inclusive_source_endpoints': endpoints,
                'trusted_blend_scripts_used': False}
            self.native.restore_owned(ctx, rig)
            require(self.native.current(rig) is None and self.graph(rig) == self.saved['closed_graph'],
                    'Reopened close did not restore the original native presentation/control graph.')
            self.verify_immutable()
            self.save(ctx, 'closed.blend')
            self.phase = 'open_closed'
        self.checkpoint('closed_scope_ended')

    def check_closed(self):
        with self.context() as ctx:
            rig = self.rig(ctx)
            require(self.native.current(rig) is None and self.graph(rig) == self.saved['closed_graph'],
                    'The closed saved file changed original collections/controllers/colors or retained active preview.')
            base = self.bpy.data.actions.get(self.saved['base_name'])
            carrier = self.bpy.data.actions.get(self.saved['input_name'])
            require(base is not None and carrier is not None
                    and self.native._motion(base, self.saved['base_slot']) == self.saved['base_motion']
                    and self.native._motion(carrier, self.saved['input_slot']) == self.saved['input_motion'],
                    'Closing/saving discarded the committed input or modified independent base keys.')
            proof = self.native.input_proof(rig, base, self.saved['base_slot'], self.work_id)
            require(proof['input_motion_sha256'] == self.saved['input_motion'], 'Inactive-row input proof lost saved native ownership.')
            self.report['inactive_input_proof'] = proof
            self.verify_immutable()
            self.report.update(completed=True, native_execution_performed=True,
                original_presentation_controls_restored=True, immutable_inputs_and_artist_preserved=True)
            self.phase = 'done'
            self.checkpoint('completed_native_control_save_only')
        if self.args.quit_on_completion:
            with self.context():
                self.report['quit_requested'] = True
                self.checkpoint('before_normal_quit_request')
                returned = self.bpy.ops.wm.quit_blender('EXEC_DEFAULT')
                self.checkpoint('normal_quit_operator_returned', operator_result=sorted(returned),
                    natural_exit_verified=False)

    def tick(self):
        try:
            if self.phase == 'import_and_edit':
                self.import_and_edit()
            elif self.phase == 'undo_inputs':
                self.undo_or_redo()
            elif self.phase == 'check_undo':
                self.check_undo()
            elif self.phase == 'redo_inputs':
                self.undo_or_redo(redo=True)
            elif self.phase == 'check_redo':
                self.check_redo()
            elif self.phase == 'finish_checks':
                self.finish_checks()
            elif self.phase == 'open_active':
                self.reopen('active.blend', 'check_reopened')
            elif self.phase == 'check_reopened':
                self.check_reopened()
            elif self.phase == 'open_closed':
                self.reopen('closed.blend', 'check_closed')
            elif self.phase == 'check_closed':
                self.check_closed()
            return None if self.phase == 'done' else .5
        except Exception as error:
            self.report.update(completed=False, failure_phase=self.phase, failure=str(error),
                traceback=traceback.format_exc(), native_execution_performed=True)
            recovery = []
            try:
                with self.context() as ctx:
                    rig = self.rig(ctx)
                    if self.native.current(rig) is not None:
                        self.native.restore_owned(ctx, rig)
                    self.verify_immutable()
                    recovery.append('owned preview closed; immutable inputs and artist hash unchanged')
            except Exception as cleanup_error:
                recovery.append('recovery incomplete: ' + str(cleanup_error))
            self.checkpoint('failed', recovery=recovery)
            # Retain the fresh disposable process for its owner to inspect/close.
            # Never substitute a quit return for a natural exit failure receipt.
            self.phase = 'failed'
            return None

    def start(self):
        import bpy
        self.bpy = bpy
        require(tuple(bpy.app.version[:2]) == (5, 2) and not bpy.app.background
                and not bpy.data.filepath and len(bpy.context.window_manager.windows) == 1
                and bpy.context.preferences.filepaths.use_scripts_auto_execute is False,
                'Start one fresh headful factory process with --disable-autoexec, not the artist process.')
        require(not any(name == 'character_designer' or name.startswith('character_designer.') for name in sys.modules),
                'Do not reuse a cached add-on package from another process/session.')
        # The source package is immutable evidence; bytecode goes nowhere in it.
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(self.root.parent))
        addon = importlib.import_module('character_designer')
        require(Path(addon.__file__).resolve() == self.root / '__init__.py', 'The isolated package import resolved elsewhere.')
        self.report['native_execution_performed'] = True
        self.checkpoint('before_complete_package_register', actual_init_file=str(Path(addon.__file__).resolve()))
        addon.register()
        modules = {name: importlib.import_module('character_designer.' + name) for name in
            ('unity_animation', 'unity_animation_rigging', 'animation_rigging_contract',
             'animation_composition', 'animation_worklist', 'animation_worklist_target',
             'animation_link_source', 'animation_link', 'limb_ik_fk', 'animation_composition_weapon')}
        for name, module in modules.items():
            require(Path(module.__file__).resolve() == self.root / (name + '.py'), 'A native helper came from another source root.')
        self.report['registered_runtime_modules'] = {name: pin(module.__file__, self.package_pins[name + '.py']['sha256'])
            for name, module in modules.items()}
        self.ua, self.native, self.contract = (modules[name] for name in
            ('unity_animation', 'unity_animation_rigging', 'animation_rigging_contract'))
        self.composition, self.worklist, self.target, self.source, self.link, self.fk = (modules[name] for name in
            ('animation_composition', 'animation_worklist', 'animation_worklist_target',
             'animation_link_source', 'animation_link', 'limb_ik_fk'))
        self.weapon = modules['animation_composition_weapon']
        self.verify_immutable()
        self.report['blender'] = {'version': list(bpy.app.version), 'binary_path': bpy.app.binary_path,
            'build_hash': bpy.app.build_hash.decode('ascii'), 'background': bpy.app.background,
            'pid': os.getpid(), 'autoexec': bpy.context.preferences.filepaths.use_scripts_auto_execute}
        self.checkpoint('before_initial_isolated_load')
        returned = bpy.ops.wm.open_mainfile('EXEC_DEFAULT', filepath=self.rows['isolated_clone']['path'],
            use_scripts=False, load_ui=False)
        require(returned == {'FINISHED'}, 'The admitted isolated clone did not load.')
        # No old Scene, Rig, Window, context or package session object survives
        # in this driver's state. Fresh native acquisition begins next tick.
        # The same plain-state driver timer must survive its own save/reopen.
        # No Window, Scene, Rig or Action is retained by the timer between ticks.
        bpy.app.timers.register(self.tick, first_interval=1., persistent=True)


def main():
    args = arguments()
    rows, root, package_pins, work_id, output = admit(args)
    round_ = Round(args, rows, root, package_pins, work_id, output)
    try:
        round_.start()
    except Exception as error:
        round_.report.update(completed=False, failure_phase='startup', failure=str(error), traceback=traceback.format_exc())
        round_.checkpoint('startup_failed')
        raise


if __name__ == '__main__':
    main()
