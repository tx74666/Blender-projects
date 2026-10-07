"""Reviewed phase API only; importing this file performs no Blender operation.

Future use is pending human scope clarification; this preparation is not an
installation/release authorization. Root supplies runtime_policy={addon_dir:
active installed package directory, version: explicitly reviewed version,
files: complete relative .py path -> SHA256 mapping}.
Create ArtistIntegration(policy), then call backup_before_refresh(), optionally
refresh_load_checkpoint(refresh=True), and after the native refresh completes
refresh_load_checkpoint(). public_install() is a separate checkpoint. Only
save_completed(observed_ui=...) may save X, after Root's actual visual review.

Direct public export remains rejected. No Plain admission, animation/FBX/Unity
acceptance, clearance claim, reset, bake, artist pose edit or recovery reopening.
SOURCE_ONLY_UNEXECUTED / FUTURE_USE_PENDING. The provider internally binds at
frame zero and must restore artist frame39.
Actual native Undo execution is a separate optional review, not proved here.
"""
import hashlib, importlib, importlib.util, json, sys, traceback, uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTIST = HERE.parents[1] / 'X.blend'
CANONICAL = Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer')
AUDIT = HERE / 'audit_current_scene_checkpoint52.py'
AUDIT_SHA = 'e0ea24c7697eabb816a3c8d9dcac4e61b72af7fe91e8bfacdc14525d7209691a'
CHECKPOINT = HERE / 'live_readonly_checkpoint_20261007_1601.json'
CHECKPOINT_SHA = '3a7494bf2dc9014e629643c5f8e8f92bfa1665d940c8f42fd74eab5c777cee3f'


def need(value, message):
    if not value: raise RuntimeError('ArtistDirect52: ' + message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()


def plain(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def manifest(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*.py'))
            if '__pycache__' not in p.parts and not any(x.startswith('.') for x in p.relative_to(root).parts)}


class ArtistIntegration:
    def __init__(self, runtime_policy):
        import bpy
        self.bpy = bpy
        need(not bpy.app.background and bpy.app.version[:2] == (5, 2), 'Paused artist Blender5.2 required')
        need(sha(AUDIT) == AUDIT_SHA and sha(CHECKPOINT) == CHECKPOINT_SHA, 'Reviewed reader/checkpoint differs')
        spec = importlib.util.spec_from_file_location('_cd_artist_direct_audit', AUDIT)
        self.audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.audit)
        self.q, self.p = self.audit.read_helpers(bpy)
        self.policy = plain(runtime_policy)
        need(set(self.policy) == {'addon_dir', 'version', 'files'} and len(self.policy['version']) == 3
             and all(type(v) is int for v in self.policy['version']), 'Explicit Root runtime policy required')
        self.addon_dir = Path(self.policy['addon_dir']).resolve()
        need(Path(self.policy['addon_dir']).is_absolute() and self.addon_dir.name == 'character_designer'
             and self.policy['files'] and all(type(v) is str and len(v) == 64 for v in self.policy['files'].values()), 'Invalid complete runtime manifest')
        self.prior = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
        need(self.prior['collection_success'] and self.prior['physics']['classification'] == 'CONTROLS_ONLY_LEGACY', 'Actual audit must pass controls-only scope')
        self.source, self.rig, self.body = self.objects()
        self.protection = self.q.Protection()
        self.author = self.author_state()
        need(self.author == self.prior['author'], 'Artist authored state changed since actual checkpoint')
        self.context = plain(self.audit.scene_state(bpy, self.q, self.p))
        need(self.context == self.prior['scene'] and self.context['frame'] == [39, 0.0], 'Fresh actual artist context differs')
        self.disk_before = self.audit.disk_state(ARTIST)
        need(self.disk_before == self.prior['disk_after'], 'Artist disk differs from actual checkpoint')
        self.extra = self.extra_state()
        self.ui = self.ui_state()
        self.ids = {kind: {o.name for o in getattr(bpy.data, kind)} for kind in ('objects', 'meshes', 'collections', 'node_groups')}
        self.pre_record = self.source[self.audit.RECORD_KEY]
        record = json.loads(self.pre_record); self.waist = record['controls']['waist'] if record.get('shared') else None
        holder = self.rig.pose.bones[self.waist] if self.waist else self.rig
        self.pre_backup = {'record_raw': self.pre_record, 'profile_raw': self.source.get(self.audit.PROFILE_KEY),
                          'state_raw': self.source.get(self.audit.STATE_KEY), 'influence': holder.get('physics_influence'),
                          'influence_ui': plain(holder.id_properties_ui('physics_influence').as_dict())}
        self.pre_wm = (self.bpy.context.window_manager.character_designer_skirt.source,
                       self.bpy.context.window_manager.character_designer_skirt.armature)
        need(self.pre_wm == (None, None), 'Observed empty WM pointers changed')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f') + '_' + uuid.uuid4().hex[:8]
        self.output, self.recovery = HERE / ('artist_direct_' + stamp + '.json'), HERE / ('X_before_Direct_' + stamp + '.blend')
        self.report = {'schema': 'ARTIST_DIRECT_PHASE52_V1', 'phase': 'prepared', 'status': 'prepared',
            'checkpoint': str(CHECKPOINT), 'checkpoint_sha256': CHECKPOINT_SHA, 'self_sha256': sha(__file__),
            'runtime_policy': self.policy, 'native_backup': False, 'installed': False, 'artist_saved': False,
            'actual_Undo_verified': False, 'FBX_verified': False, 'Unity_verified': False,
            'public_Direct_export_rejected': True, 'Plain_consumer_admission': False,
            'protected_frame': [39, 0.0], 'errors': []}
        with self.output.open('x', encoding='utf-8') as stream: json.dump(self.report, stream, ensure_ascii=False, indent=2)

    def objects(self):
        bpy = self.bpy; source, rig, body = (bpy.data.objects.get(n) for n in ('Dress', 'CoshaRig', 'Cosha'))
        setup = getattr(bpy.context.scene, 'character_designer_setup', None)
        need(source and rig and body and source.type == body.type == 'MESH' and rig.type == 'ARMATURE'
             and all(o.name in bpy.context.scene.objects for o in (source, rig, body)), 'Explicit artist inputs missing')
        need(setup and setup.rig == rig and setup.body == body and source.get(self.audit.RIG_KEY) == rig, 'Actual Setup/native Rig pointers differ')
        record = json.loads(source[self.audit.RECORD_KEY])
        need(record['source'] == 'Dress' and record['rig'] == 'CoshaRig' and source.data.shape_keys is None
             and len(source.data.vertices) == 800 and body.data.shape_keys is not None
             and len(body.data.shape_keys.key_blocks) == 12, 'Exact Dress800/noKeys/Body12 identity required')
        return source, rig, body

    def author_state(self):
        return plain(self.audit.authored_state(self.bpy, self.q, self.p, *self.objects()))

    def extra_state(self):
        q = self.q
        return plain({'bindings': {str(q.id_name(o)): self.p.animation(o, q) for o in
            list(self.bpy.data.objects) + list(self.bpy.data.meshes) + list(self.bpy.data.armatures) + list(self.bpy.data.shape_keys)},
            'actions': {a.name: q.digest(q.action_content(a)) for a in self.bpy.data.actions},
            'poses': {o.name: q.pose_channels(o) for o in self.bpy.data.objects if o.type == 'ARMATURE'},
            'custom': {str(q.id_name(o)): q.custom_content(dict(o.items())) for o in
                (self.source, self.source.data, self.rig, self.rig.data, self.body, self.body.data, self.body.data.shape_keys)},
            'pose_custom': {o.name: {pb.name: q.custom_content(dict(pb.items())) for pb in o.pose.bones}
                            for o in self.bpy.data.objects if o.type == 'ARMATURE'},
            'constraints': {o.name: {pb.name: [(c.name, q.simple_rna(c)) for c in pb.constraints]
                for pb in o.pose.bones} for o in self.bpy.data.objects if o.type == 'ARMATURE'}})

    def ui_state(self):
        bpy = self.bpy; q = self.q; state = {'objects': {}, 'rigs': {}}
        for o in bpy.context.view_layer.objects:
            if hasattr(self, 'ui') and o.name not in self.ui['objects']: continue
            state['objects'][o.name] = [o.select_get(), o.hide_get(), o.hide_viewport, o.hide_render, o.hide_select]
            if o.type != 'ARMATURE': continue
            state['rigs'][o.name] = {'display': [o.show_in_front, o.display_type, {n: getattr(o.data, n) for n in
                ('display_type', 'show_bone_custom_shapes', 'show_names', 'show_axes', 'axes_position', 'show_wire') if hasattr(o.data, n)}],
                'collections': {c.name: [c.is_visible, c.is_solo] for c in o.data.collections_all},
                'bones': self.p.bone_selection(o), 'active': None if o.data.bones.active is None else o.data.bones.active.name,
                'shapes': {pb.name: {n: (None if pb.custom_shape_transform is None else [q.id_name(pb.custom_shape_transform.id_data), pb.custom_shape_transform.name]) if n == 'custom_shape_transform'
                    else (q.custom_content(getattr(pb, n)) if n == 'custom_shape' else list(getattr(pb, n))) for n in
                    ('custom_shape', 'custom_shape_transform', 'custom_shape_scale_xyz', 'custom_shape_translation', 'custom_shape_rotation_euler')}
                    for pb in o.pose.bones},
                'shape_flags': {pb.name: {n: getattr(pb, n) for n in ('use_custom_shape_bone_size', 'custom_shape_wire_width') if hasattr(pb, n)} for pb in o.pose.bones},
                'colors': {pb.name: [[q.simple_rna(c), q.simple_rna(c.custom)] for c in (pb.color, pb.bone.color)] for pb in o.pose.bones}}
        return plain(state)

    def restore_ui(self):
        bpy = self.bpy; current = bpy.context.view_layer.objects.active
        if current and current.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        for name, flags in self.ui['objects'].items():
            o = bpy.data.objects[name]; o.select_set(flags[0]); o.hide_set(flags[1])
            o.hide_viewport, o.hide_render, o.hide_select = flags[2:]
        for name, row in self.ui['rigs'].items():
            o = bpy.data.objects[name]
            for n, flags in row['collections'].items(): o.data.collections_all[n].is_visible, o.data.collections_all[n].is_solo = flags
            for bone in row['bones']:
                pb = o.pose.bones[bone['name']]; owner = pb if hasattr(pb, 'select') else pb.bone
                for n, v in bone['fields'].items(): setattr(owner, n, v)
                pb.hide, pb.bone.hide = bone['pose_bone_hide'], bone['data_bone_hide']
            o.data.bones.active = o.data.bones.get(row['active']) if row['active'] else None
        bpy.context.view_layer.objects.active = bpy.data.objects.get(self.context['active']['ID'][1])
        if self.context['mode'] == 'POSE': bpy.ops.object.mode_set(mode='POSE')
        for role, row in self.author['objects'].items():
            o = bpy.data.objects[row['identity']['ID'][1]]
            for name, _kind, _pointer, fields in row['modifiers']:
                o.modifiers[name].is_active = fields['is_active']

    def check(self, installed=False, dirty=None):
        self.source, self.rig, self.body = self.objects()
        need(self.protection.verify()['success'], 'Original raw Mesh/UV/weights/Rest/Actions/NLA assets changed')
        now = self.author_state(); extras = self.extra_state()
        if installed:
            record = json.loads(self.source[self.audit.RECORD_KEY]); surface = record['physics']['surface']
            sys.modules['character_designer.skirt_surface_direct'].validate(self.source, self.rig, record)
            need(all(plain(surface['backup'][k]) == plain(v) for k, v in self.pre_backup.items()), 'Saved rollback metadata/influence/UI differs')
            need(all({o.name for o in getattr(self.bpy.data, kind)} == self.ids[kind] | set(self.report['owned_IDs'][kind]) for kind in self.ids), 'Owned Direct inventory changed')
            now['objects']['Dress']['modifiers'] = [m for m in now['objects']['Dress']['modifiers'] if m[0] != surface['overlay']]
            for key in (self.audit.RECORD_KEY, self.audit.PROFILE_KEY, self.audit.STATE_KEY):
                custom_key = str(self.q.id_name(self.source))
                if key in self.extra['custom'][custom_key]: extras['custom'][custom_key][key] = self.extra['custom'][custom_key][key]
                else: extras['custom'][custom_key].pop(key, None)
            custom = extras['pose_custom']['CoshaRig'][self.waist] if self.waist else extras['custom'][str(self.q.id_name(self.rig))]
            custom['physics_influence'] = self.pre_backup['influence']
            for name, constraint, _mute in surface['backup']['rotations']:
                expected = dict(self.extra['constraints']['CoshaRig'][name])[constraint]['mute']
                dict(extras['constraints']['CoshaRig'][name])[constraint]['mute'] = expected
            for name in list(extras['bindings']):
                if name not in self.extra['bindings']: del extras['bindings'][name]
        else:
            need(all({o.name for o in getattr(self.bpy.data, kind)} == self.ids[kind] for kind in self.ids), 'Rollback/refresh left unexpected data')
            holder = self.rig.pose.bones[self.waist] if self.waist else self.rig
            need(plain(holder.id_properties_ui('physics_influence').as_dict()) == self.pre_backup['influence_ui'], 'Original influence property UI differs')
        need(now == self.author and extras == self.extra and self.ui_state() == self.ui, 'Protected pose/Keys/bindings/selection/display/modifier UI changed')
        state = plain(self.audit.scene_state(self.bpy, self.q, self.p))
        if not self.report.get('artist_saved'): need(self.audit.disk_state(ARTIST) == self.disk_before, 'Artist disk changed before final save')
        for key in ('filepath', 'Scene', 'view_layer', 'frame', 'mode', 'active', 'selected', 'units', 'autokey'):
            need(state[key] == self.context[key], 'Protected context differs: ' + key)
        need(self.bpy.context.window_manager.character_designer_skirt.armature is None, 'WM Rig pointer changed')
        need(self.bpy.context.window_manager.character_designer_skirt.source == (self.source if installed else self.pre_wm[0]), 'Explicit WM source differs')
        need(not self.bpy.context.screen.is_animation_playing, 'Artist playback is no longer paused')
        if dirty is not None: need(state['is_dirty'] == dirty, 'Native backup/save dirty state differs')
        return {'raw_author_UI_exact': True, 'frame': state['frame'], 'dirty': state['is_dirty']}

    def phase(self, name, action):
        need(self.report['status'] != 'failed', 'Failed attempt is retained; review recovery before starting another phase')
        self.report.update(phase=name, status='running')
        try:
            value = action(); self.report.update(status='passed'); return value
        except Exception as exc:
            self.report.update(status='failed'); self.report['errors'].append({'phase': name, 'error': repr(exc), 'traceback': traceback.format_exc()}); raise
        finally:
            self.report['updated_UTC'] = datetime.now(timezone.utc).isoformat()
            self.output.write_text(json.dumps(self.report, ensure_ascii=False, allow_nan=False, indent=2), encoding='utf-8')

    def backup_before_refresh(self):
        def action():
            need(not self.report['native_backup'] and not self.recovery.exists(), 'One new recovery per session required')
            self.check(dirty=self.context['is_dirty'])
            need(not self.bpy.context.screen.is_animation_playing, 'Fresh paused artist required')
            need(self.bpy.ops.wm.save_as_mainfile(filepath=str(self.recovery), copy=True, check_existing=False) == {'FINISHED'}, 'Native recovery did not finish')
            need(self.recovery.is_file() and self.recovery.stat().st_size > 0, 'Native recovery missing')
            self.report['backup'] = self.audit.disk_state(self.recovery)
            self.report['backup_check'] = self.check(dirty=self.context['is_dirty']); self.report['native_backup'] = True
            return self.report['backup']
        return self.phase('backup_before_refresh', action)

    def runtime(self):
        need(manifest(CANONICAL) == self.policy['files'] == manifest(self.addon_dir), 'Root release source/deployment manifest differs')
        addon = sys.modules.get('character_designer')
        need(addon and Path(addon.__file__).resolve().parent == self.addon_dir and list(addon.bl_info['version']) == self.policy['version'], 'Actual loaded release/path differs')
        need(not addon.ADDON_REFRESH_PENDING and not addon.ADDON_REFRESH_LAST_ERROR
             and addon.ADDON_LOADED_SIGNATURE == addon._source_signature(), 'Refresh has not completed against installed source')
        addon._validate_registration_integrity()
        modules = {n: importlib.import_module('character_designer.' + n) for n in ('skirt', 'skirt_surface_direct', 'skirt_motion_tuning', 'skirt_physics')}
        need(all(Path(m.__file__).resolve().parent == self.addon_dir for m in modules.values()), 'Mixed runtime package paths')
        return addon, modules

    def refresh_load_checkpoint(self, *, refresh=False):
        def action():
            need(self.report['native_backup'] and sha(self.recovery) == self.report['backup']['sha256'], 'Verified native recovery required')
            self.check()
            if refresh:
                need(not self.report.get('refresh_requested'), 'Refresh already requested')
                need(self.bpy.ops.character_designer.refresh_addon('EXEC_DEFAULT') == {'FINISHED'}, 'Public refresh did not schedule')
                self.report['refresh_requested'] = True
                return {'await_native_refresh_completion': True}
            addon, _modules = self.runtime(); self.report['refresh_check'] = self.check()
            self.report['runtime_ready'] = True
            return {'loaded_version': list(addon.bl_info['version']), 'protected': True}
        return self.phase('refresh_load_checkpoint', action)

    def public_install(self):
        def action():
            need(self.report.get('runtime_ready') and not self.report['installed'], 'Clean reviewed runtime checkpoint required')
            self.check(); _addon, modules = self.runtime(); ui, direct = modules['skirt'], modules['skirt_surface_direct']
            need(not json.loads(self.source[self.audit.RECORD_KEY]).get('physics'), 'Controls-only required; no migration')
            need(self.bpy.context.preferences.edit.use_global_undo and 'UNDO' in ui.CHARACTERDESIGNER_OT_skirt_add_physics.bl_options, 'Native Undo preference/operator required')
            wm = self.bpy.context.window_manager.character_designer_skirt; old_message = wm.last_message
            installed = False
            try:
                need(self.bpy.ops.ed.undo_push(message='Before Direct Dress installation') == {'FINISHED'}, 'Native Undo barrier did not finish')
                wm.source = self.source  # Explicit verified user Dress input; was None, now intentionally initialized.
                self.report['WM_source_initialization'] = {'before': None, 'after': 'Dress', 'preexisting_registration_claimed': False}
                direct.skirt._activate(self.bpy.context, self.source, 'OBJECT')
                need(ui._source(self.bpy.context) == self.source and self.bpy.ops.character_designer.skirt_add_physics.poll(), 'Public Dress resolution/poll differs')
                result = self.bpy.ops.character_designer.skirt_add_physics('EXEC_DEFAULT', True, actual_surface=True)
                self.report['operator_result'] = sorted(result)
                record = direct.skirt.read_record(self.source); installed = (record.get('physics') or {}).get('backend') == direct.BACKEND
                need(result == {'FINISHED'} and installed, 'Public Direct installation did not finish')
                actual, cloth = direct.validate(self.source, self.rig, record)
                need(record['owner'] == json.loads(self.pre_record)['owner'] and record['physics']['surface']['body'] == 'Cosha', 'Owned graph/actual Body differs')
                surface = record['physics']['surface']; owned = {n for names in surface['roles'].values() for n in names}
                allowed = {'objects': owned, 'meshes': {self.bpy.data.objects[n].data.name for n in owned},
                           'collections': {record['physics']['collection']}, 'node_groups': {n for names in surface['node_roles'].values() for n in names}}
                need(all({o.name for o in getattr(self.bpy.data, kind)} == self.ids[kind] | allowed[kind] for kind in self.ids), 'Unexpected removed/unowned new data')
                self.report['owned_IDs'] = {kind: sorted(names) for kind, names in allowed.items()}
                snapshot = modules['skirt_motion_tuning']._snapshot(self.source, record, self.rig, actual, cloth)
                snapshot['change_native'] = False
                try:
                    need(self.bpy.ops.character_designer.dress_motion_mode('EXEC_DEFAULT', False, mode='AUTOMATIC') == {'FINISHED'}, 'Public Automatic check failed')
                    direct.validate(self.source, self.rig, record)
                    need(cloth.show_viewport and cloth.show_render and direct.preview_status(self.source, record)['mode'] == 'AUTOMATIC', 'Automatic did not enable owned Cloth')
                    self.report['Automatic'] = {'state': direct.preview_status(self.source, record), 'cloth_flags': [True, True]}
                    need(self.bpy.ops.character_designer.dress_motion_mode('EXEC_DEFAULT', False, mode='MANUAL') == {'FINISHED'}, 'Public Manual check failed')
                    direct.validate(self.source, self.rig, record)
                    need(not cloth.show_viewport and not cloth.show_render, 'Manual did not pause owned Cloth')
                    self.report['Manual'] = {'state': direct.preview_status(self.source, record), 'cloth_flags': [False, False], 'transient_no_reset': True}
                finally: modules['skirt_motion_tuning']._restore(snapshot)
                direct.validate(self.source, self.rig, record); self.restore_ui(); wm.last_message = old_message
                self.report['restored_install_mode'] = direct.preview_status(self.source, record)
                self.report['install_check'] = self.check(installed=True); self.report['installed'] = True
                return {'backend': direct.BACKEND, 'artist_saved': False, 'await_actual_visual_review': True}
            except Exception:
                failures = []
                try:
                    record = direct.skirt.read_record(self.source)
                    if (record.get('physics') or {}).get('backend') == direct.BACKEND:
                        direct.commit_remove(self.source, direct.preflight_remove(self.bpy.context, self.source, self.rig, record))
                except Exception as exc: failures.append('Direct-only cleanup: ' + repr(exc))
                for label, callback in (('WM', lambda: setattr(wm, 'source', self.pre_wm[0])), ('message', lambda: setattr(wm, 'last_message', old_message)), ('UI', self.restore_ui), ('protected fingerprints', self.check)):
                    try: callback()
                    except Exception as exc: failures.append(label + ': ' + repr(exc))
                self.report['rollback'] = {'exact': not failures, 'failures': failures, 'recovery_retained': str(self.recovery), 'recovery_opened': False}
                if failures: raise RuntimeError('Rollback incomplete; preserve recovery and review: ' + '; '.join(failures))
                raise
        return self.phase('public_install', action)

    def save_completed(self, *, observed_ui, previous_editor):
        def action():
            need(self.report['installed'] and not self.report['artist_saved'], 'Clean completed installation required')
            need(type(observed_ui) is dict and observed_ui.get('accepted') is True
                 and observed_ui.get('checkpoint_report') == str(self.output) and observed_ui.get('native_visual_review') is True,
                 'Separate Root observed artist UI acceptance receipt required')
            self.runtime(); self.check(installed=True)
            area = self.bpy.context.area
            need(area and area.type == 'CONSOLE' and set(previous_editor) == {'type', 'ui_type'} and previous_editor['type'] != 'CONSOLE', 'Observed temporary Console/editor required')
            area.type, area.ui_type = previous_editor['type'], previous_editor['ui_type']
            need(area.type == previous_editor['type'] and area.ui_type == previous_editor['ui_type'], 'Artist editor did not restore')
            result = self.bpy.ops.wm.save_as_mainfile(filepath=str(ARTIST), copy=False, check_existing=False)
            self.report['save_result'] = sorted(result)
            need(result == {'FINISHED'} and Path(self.bpy.data.filepath).resolve() == ARTIST.resolve(), 'Artist save did not finish')
            self.report['artist_saved'] = True; self.report['artist_after'] = self.audit.disk_state(ARTIST)
            self.report['save_check'] = self.check(installed=True, dirty=False); self.report['observed_ui'] = plain(observed_ui)
            return {'artist_saved': True, 'native_result': sorted(result), 'path': str(ARTIST)}
        return self.phase('save_completed', action)
