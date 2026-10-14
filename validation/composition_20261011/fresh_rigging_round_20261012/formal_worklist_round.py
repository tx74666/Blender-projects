"""Owned clone only: formal Worklist readiness, optionally Add + Activate.

Preparing this Source does not launch Blender or authorize a launch. Parent must
provide a fresh launch grant and genuine Prepare inputs. No Sync, worker, model
repair, re-adoption, row removal, artist save, or local Return experiment occurs.
"""

import argparse
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import traceback
import uuid


SCHEMA = 'x.validation.formal-worklist-admission-round/1'
FREEZE_SHA = '71fd41971f2e7c889dcb1ff7a427ddb7cd58b6560015b658c960c067c869ed89'
MANIFEST_SHA = 'ac12952c816f17ae86ac732ab18f4dcb5dc37dfa68aa39be600b27ef1d6b362f'
INIT_SHA = 'd66a88023e93c3db64f1b64cfaf8089d4c956adc0f97896c591e34a54d8e4dd2'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def pin(path, expected):
    path = Path(path).resolve()
    require(re.fullmatch('[0-9a-fA-F]{64}', expected or '') and path.is_file()
            and sha(path) == expected.lower(), 'Missing or changed immutable input: ' + str(path))
    return {'path': str(path), 'sha256': expected.lower(), 'bytes': path.stat().st_size}


def document(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('isolated-clone', 'protected-artist', 'initial-workspace',
                  'workspace', 'prepared-link', 'model', 'actualpacket',
                  'source-freeze', 'package-manifest'):
        parser.add_argument('--' + field, required=True)
        parser.add_argument('--' + field + '-sha256', required=True)
    parser.add_argument('--script-sha256', required=True)
    for field in ('addon-root', 'output-root', 'scene-name', 'rig-name',
                  'work-item-id', 'initial-workspace-identity', 'workspace-identity'):
        parser.add_argument('--' + field, required=True)
    parser.add_argument('--initial-row-count', required=True, type=int)
    parser.add_argument('--confirm-isolated-headful', required=True, action='store_true')
    parser.add_argument('--add-activate', action='store_true',
        help='Explicitly perform public connect, Add and Custom Activate after readiness.')
    parser.add_argument('--quit-on-completion', action='store_true')
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return parser.parse_args(argv)


class Round:
    def __init__(self, args):
        self.args, self.phase = args, 'source_admission'
        scope = Path(__file__).resolve().parent
        self.output = Path(args.output_root).resolve()
        require(self.output != scope and self.output.is_relative_to(scope)
                and self.output.is_dir(), 'Use a fresh output child of this owned script directory.')
        require({p.name for p in self.output.iterdir()} == {'CONFIG', 'DATAFILES'}
                and all((self.output / name).is_dir() and not (self.output / name).is_symlink()
                    and not any((self.output / name).iterdir()) for name in ('CONFIG', 'DATAFILES')),
                'Before launch the output must contain only empty owned profile directories.')
        for key, name in (('BLENDER_USER_CONFIG', 'CONFIG'), ('BLENDER_USER_DATAFILES', 'DATAFILES')):
            require(os.environ.get(key) and Path(os.environ[key]).resolve() == self.output / name,
                    'The process must use its own exact CONFIG/DATAFILES.')
        self.report_path = self.output / 'formal_worklist_report.json'
        self.report = {'schema': SCHEMA, 'completed': False, 'readiness_completed': False,
            'formal_add_activate_completed': False, 'native_execution_performed': False,
            'mode': 'ADD_ACTIVATE' if args.add_activate else 'READINESS_ONLY',
            'sync_executed': False, 'worker_executed': False, 'artist_saved': False,
            'repair_or_re_adoption_performed': False, 'rows_cleared': False,
            'physical_return_verified': False, 'control_save_or_local_DTO_verified': False,
            'natural_exit_verified': False, 'checkpoints': []}
        with self.report_path.open('x', encoding='utf-8') as stream:
            json.dump(self.report, stream, ensure_ascii=False, indent=2, allow_nan=False)

    def checkpoint(self, phase, **fields):
        self.report['phase'] = phase
        self.report['checkpoints'].append({'phase': phase, **fields})
        with self.report_path.open('w', encoding='utf-8') as stream:
            json.dump(self.report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())

    def memory(self, phase):
        class Status(ctypes.Structure):
            _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [
                (name, ctypes.c_ulonglong) for name in
                ('total', 'available', 'total_page', 'available_page', 'total_virtual',
                 'available_virtual', 'available_extended')]
        def sample():
            value = Status()
            value.length = ctypes.sizeof(value)
            require(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)),
                    'The actual memory guard could not read capacity.')
            return {'available_bytes': value.available, 'load_percent': value.load}
        readings = [sample()]
        if readings[-1]['available_bytes'] < 200 * 1024 * 1024 or readings[-1]['load_percent'] >= 98:
            time.sleep(5)
            readings.append(sample())
        self.checkpoint('memory_' + phase, readings=readings)
        require(readings[-1]['available_bytes'] >= 200 * 1024 * 1024
                and readings[-1]['load_percent'] < 98, 'Pause this serial round until the fresh memory gate passes.')

    def admit(self):
        args = self.args
        self.pins = {'script': pin(__file__, args.script_sha256)}
        for field in ('isolated_clone', 'protected_artist', 'initial_workspace', 'workspace',
                      'prepared_link', 'model', 'actualpacket', 'source_freeze', 'package_manifest'):
            self.pins[field] = pin(getattr(args, field), getattr(args, field + '_sha256'))
        clone, artist = (Path(self.pins[name]['path']) for name in ('isolated_clone', 'protected_artist'))
        require(clone != artist and clone.suffix.lower() == '.blend'
                and clone.is_relative_to(Path(__file__).resolve().parent)
                and not clone.is_relative_to(self.output), 'Never load the artist file as this QA clone.')
        self.report['original_clone_relative_path'] = clone.relative_to(Path(__file__).resolve().parent).as_posix()
        require(args.source_freeze_sha256.lower() == FREEZE_SHA
                and args.package_manifest_sha256.lower() == MANIFEST_SHA,
                'Use the reviewed r4 Source freeze and complete content-addressed package.')
        self.root = Path(args.addon_root).resolve()
        manifest = document(self.pins['package_manifest']['path'])
        freeze = document(self.pins['source_freeze']['path'])
        require(manifest['schema_version'] == 1 and type(manifest['schema_version']) is int
                and manifest['module'] == 'character_designer' and manifest['version'] == '0.77.25'
                and Path(manifest['source_root']).resolve() == self.root
                and len(manifest['files']) == 187 and self.root.name == 'character_designer'
                and freeze['source_only'] is True and freeze['native_execution_performed'] is False,
                'The complete Source candidate contract changed.')
        self.package = {}
        for relative, expected in manifest['files'].items():
            path = self.root / relative
            require(not Path(relative).is_absolute() and path.resolve().is_relative_to(self.root)
                    and not path.is_symlink(), 'A package entry escapes its immutable root.')
            self.package[relative] = pin(path, expected)
        actual = {p.relative_to(self.root).as_posix() for p in self.root.rglob('*') if p.is_file()}
        require(actual == set(self.package) and self.package['__init__.py']['sha256'] == INIT_SHA,
                'The complete package set or registration source changed.')
        for row in freeze['source_pins']:
            if 'addons' in Path(row['path']).parts:
                require(self.package[Path(row['path']).name]['sha256'] == row['sha256'],
                        'A reviewed runtime leaf differs from the package.')
        require(args.initial_row_count >= 0, 'The original row count must be an explicit nonnegative count.')
        self.work_id = uuid.UUID(args.work_item_id).hex
        require(uuid.UUID(self.work_id).int != 0, 'Use the genuine prepared nonzero WorkID.')
        self.report.update(immutable_inputs=self.pins, package_manifest=self.pins['package_manifest'],
            package_files=self.package, package_file_count=len(self.package), work_item_id=self.work_id)
        self.checkpoint('source_admission_passed', original_clone=self.pins['isolated_clone'])

    def verify_inputs(self):
        for row in (*self.pins.values(), *self.package.values()):
            pin(row['path'], row['sha256'])

    @contextmanager
    def context(self):
        bpy = self.bpy
        windows = tuple(bpy.context.window_manager.windows)
        scenes = [s for s in bpy.data.scenes if s.name == self.args.scene_name]
        require(len(windows) == 1 and len(scenes) == 1 and scenes[0].library is None,
                'Reacquire the unique actual owning Window and exact local Scene.')
        window = windows[0]
        window.scene = scenes[0]
        with bpy.context.temp_override(window=window):
            ctx = bpy.context
            require(ctx.scene == scenes[0] and ctx.window == window
                    and ctx.view_layer == window.view_layer
                    and not ctx.preferences.filepaths.use_scripts_auto_execute,
                    'The fresh QA context or disabled auto-execution policy changed.')
            for name, key in (('CONFIG', 'BLENDER_USER_CONFIG'), ('DATAFILES', 'BLENDER_USER_DATAFILES')):
                require(Path(bpy.utils.user_resource(name, create=False)).resolve()
                        == Path(os.environ[key]).resolve(), 'Blender resolved another process profile.')
            yield ctx

    def snapshot(self, ctx):
        saved = self.worklist.state(ctx)
        def action(value):
            return None if value is None else {'name': value.name, 'pointer': value.as_pointer(),
                'library': None if value.library is None else value.library.filepath,
                'slots': [slot.handle for slot in value.slots]}
        rows = []
        for row in saved.items:
            fields = {key: getattr(row, key) for key in ('item_id', 'clip_key', 'work_item_id',
                'manifest_path', 'model_file', 'model_sha256', 'source_file', 'source_hash',
                'link_identity', 'source_slot', 'custom_slot')}
            fields.update(rig=None if row.rig is None else row.rig.name,
                source_action=action(row.source_action), custom_action=action(row.custom_action))
            rows.append(fields)
        return {'workspace_path': saved.workspace_path, 'workspace_identity': saved.workspace_identity,
            'workspace_id': saved.workspace_id, 'model_file': saved.model_file,
            'model_sha256': saved.model_sha256, 'target_guid': saved.target_guid,
            'rig': None if saved.rig is None else saved.rig.name, 'rows': rows}

    def run_formal(self):
        self.memory('formal_admission')
        with self.context() as ctx:
            before = self.snapshot(ctx)
            self.report['initial_saved_worklist'] = before
            self.checkpoint('before_original_target_ensure_active')
            saved = self.worklist.state(ctx)
            candidates = [r for r in self.bpy.data.objects if r.name == self.args.rig_name]
            require(len(candidates) == 1 and saved.rig == candidates[0]
                    and candidates[0].type == 'ARMATURE' and candidates[0].library is None
                    and candidates[0] in tuple(ctx.scene.objects)
                    and candidates[0] in tuple(ctx.view_layer.objects), 'Use the exact original adopted Worklist Rig.')
            rig = candidates[0]
            require(self.target.is_adopted(rig), 'This round never adopts or repairs a Rig.')
            self.target.ensure_active(ctx, rig)
            require(len(saved.items) == self.args.initial_row_count
                    and saved.workspace_identity == self.args.initial_workspace_identity
                    and Path(saved.workspace_path).resolve() == Path(self.pins['initial_workspace']['path']),
                    'The original rows, workspace or adopted owner differ from the supplied original clone evidence.')
            original = self.workspace.load_workspace(self.pins['initial_workspace']['path'])
            require(self.worklist._identity(original) == saved.workspace_identity,
                    'The recorded original workspace identity changed; do not reconnect it.')
            record = self.workspace.load_workspace(self.pins['workspace']['path'])
            require(self.worklist._identity(record) == self.args.workspace_identity,
                    'The fresh Prepare workspace differs from its explicit identity.')
            link = self.links.load_link(self.pins['prepared_link']['path'])
            clip = [row for row in record['clips'] if self.workspace.work_item_id(row) == self.work_id]
            require(len(clip) == 1 and not clip[0].get('needsRebuild')
                    and Path(clip[0]['linkManifest']).resolve() == Path(self.pins['prepared_link']['path'])
                    and self.workspace.work_item_id(link) == self.work_id
                    and link['targetGuid'].lower() == record['targetGuid'].lower()
                    and self.workspace.route_identity(clip[0]) == self.workspace.route_identity(link),
                    'The real prepared row, WorkID and typed Link must agree exactly.')
            require(Path(record['modelFile']).resolve() == Path(self.pins['model']['path'])
                    and record['modelSha256'].lower() == self.pins['model']['sha256']
                    and Path(link['modelFile']).resolve() == Path(self.pins['model']['path'])
                    and link['modelSha256'].lower() == self.pins['model']['sha256']
                    and Path(link['sourcePackage']).resolve() == Path(self.pins['actualpacket']['path'])
                    and link['sourcePackageSha256'].lower() == self.pins['actualpacket']['sha256'],
                    'The exact physical model and full packet pins do not match Prepare.')
            packet, export_name = self.source._packet(link)
            require(packet['_sha256'] == self.pins['actualpacket']['sha256'], 'The authenticated full packet changed.')
            self.report['prepared_route'] = {'clip_key': self.workspace.row_key(clip[0]),
                'work_item_id': self.work_id, 'target_guid': link['targetGuid'],
                'workspace_identity': self.worklist._identity(record), 'export_rig_name': export_name}
            self.checkpoint('before_workspace_compatibility_guard')
            require(not (saved.items or saved.rig) or saved.workspace_identity == self.worklist._identity(record),
                    'Existing Worklist rows/owner use another workspace or model revision; keep them intact.')
            self.report['readiness_completed'] = True
            if self.args.add_activate:
                self.memory('formal_add')
                self.checkpoint('before_public_worklist_connect')
                self.worklist.connect(ctx, self.pins['workspace']['path'])
                self.target.ensure_active(ctx, rig)
                self.checkpoint('before_public_worklist_add')
                item = self.worklist.add(ctx, self.workspace.row_key(clip[0]), activate_new=False)
                require(item.rig == rig and item.work_item_id == self.work_id,
                        'Formal Add did not retain the exact original Rig and real prepared WorkID.')
                self.checkpoint('before_public_worklist_activate_custom', item_id=item.item_id)
                self.worklist.activate(ctx, item.item_id, 'CUSTOM')
                self.target.ensure_active(ctx, rig)
                require(self.worklist.current(ctx) == item and item.side == 'CUSTOM',
                        'The official Custom Activate did not finish on the real work item.')
                after = self.snapshot(ctx)
                indexed = {row['item_id']: row for row in after['rows']}
                require(all(indexed.get(row['item_id']) == row for row in before['rows']),
                        'A pre-existing Worklist row, native Action or slot identity changed.')
                self.report.update(formal_add_activate_completed=True, completed=True,
                    created_new_row=item.item_id not in {row['item_id'] for row in before['rows']},
                    active_item_id=item.item_id, active_custom_action=item.custom_action.name,
                    active_custom_slot=item.custom_slot)
            self.report['final_saved_worklist'] = self.snapshot(ctx)
            self.verify_inputs()
            self.checkpoint('formal_round_finished', artist_and_clone_files_unchanged=True)
        if self.args.quit_on_completion:
            with self.context():
                self.checkpoint('before_normal_quit_request', natural_exit_verified=False)
                self.bpy.ops.wm.quit_blender('EXEC_DEFAULT')

    def tick(self):
        try:
            self.phase = 'formal_worklist_readiness_or_add_activate'
            self.run_formal()
        except Exception as error:
            self.report.update(completed=False, failure_phase=self.report.get('phase', self.phase),
                failure=str(error), traceback=traceback.format_exc())
            try:
                with self.context() as ctx:
                    self.report['failure_saved_worklist'] = self.snapshot(ctx)
                self.verify_inputs()
                self.report['immutable_inputs_and_artist_preserved'] = True
            except Exception as guard_error:
                self.report['failure_readback_error'] = str(guard_error)
            self.checkpoint('failed_without_repair_or_row_removal')
        return None

    def start(self):
        self.admit()
        import bpy
        self.bpy = bpy
        require(tuple(bpy.app.version[:2]) == (5, 2) and not bpy.app.background
                and not bpy.data.filepath and len(bpy.context.window_manager.windows) == 1
                and not bpy.context.preferences.filepaths.use_scripts_auto_execute,
                'Use a fresh factory headful process with --disable-autoexec, never the artist process.')
        require(not any(name == 'character_designer' or name.startswith('character_designer.')
                for name in sys.modules), 'Do not reuse a cached add-on package.')
        self.memory('complete_package_register')
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(self.root.parent))
        addon = importlib.import_module('character_designer')
        require(Path(addon.__file__).resolve() == self.root / '__init__.py', 'The complete package resolved elsewhere.')
        self.report['native_execution_performed'] = True
        self.checkpoint('before_complete_package_register', init_source=self.package['__init__.py'])
        addon.register()
        registered = {}
        for name, module in tuple(sys.modules.items()):
            if name == 'character_designer' or name.startswith('character_designer.'):
                source_file = Path(module.__file__).resolve()
                require(source_file.is_relative_to(self.root), 'A registered package module resolved outside its root.')
                relative = source_file.relative_to(self.root).as_posix()
                require(relative in self.package, 'A registered module is not in the complete approved payload.')
                registered[name] = pin(source_file, self.package[relative]['sha256'])
        self.report['registered_package_modules'] = registered
        for name, attribute in (('animation_worklist', 'worklist'), ('animation_worklist_target', 'target'),
                ('animation_workspace', 'workspace'), ('animation_link', 'links'), ('animation_link_source', 'source')):
            module = importlib.import_module('character_designer.' + name)
            require(Path(module.__file__).resolve() == self.root / (name + '.py'), 'A registered helper resolved elsewhere.')
            setattr(self, attribute, module)
        self.verify_inputs()
        self.checkpoint('before_open_original_isolated_clone')
        returned = bpy.ops.wm.open_mainfile('EXEC_DEFAULT', filepath=self.pins['isolated_clone']['path'],
            use_scripts=False, load_ui=False)
        require(returned == {'FINISHED'}, 'The exact original isolated clone did not load.')
        self.checkpoint('clone_open_returned', fresh_context_deferred_to_next_tick=True)
        bpy.app.timers.register(self.tick, first_interval=1., persistent=True)


def main():
    round_ = Round(arguments())
    try:
        round_.start()
    except Exception as error:
        round_.report.update(completed=False, failure_phase=round_.phase,
            failure=str(error), traceback=traceback.format_exc())
        round_.checkpoint('startup_failed_without_native_repair')
        raise


if __name__ == '__main__':
    main()
