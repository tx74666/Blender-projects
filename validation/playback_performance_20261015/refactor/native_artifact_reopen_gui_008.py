"""Independent owned GUI-process artifact reopen; no launch or save operation.

Requires a real completed Artifact009 receipt. Standard add-on registration and
load handlers remain active. One verification timer advances one frame, yields
to the event loop, then reads its output. PASS keeps the preview GUI alive.
"""
import argparse
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_validation_support_v5 as witness
import native_bone_support as geometry
import native_artifact_action_witness_008 as portable
geometry.base = witness
_SESSION = None


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def same_pin(left, right):
    return left['sha256'] == right['sha256'] and left['bytes'] == right['bytes']


def load_receipt(path, expected_sha256):
    """No bpy/scene access until real artifact evidence exists and is pinned."""
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected_sha256, 'Artifact receipt SHA differs')
    result = json.loads(raw.decode('utf-8-sig'))
    require(result.get('schema') == 'x.private-helper-bone-bake-artifact/1'
            and result.get('completed') is True and 'error' not in result,
            'A real completed Artifact009 receipt is required')
    require(result.get('artifact_published') is True and result.get('artifact_publication_complete') is True
            and result['artifact_publication']['completed'] is True,
            'Artifact publication did not complete')
    require('native_bone_bake_artifact_runner_009.py' in result['scripts'], 'Artifact009 portable proof is required')
    contract = result['reopen_contract']
    require(contract['portable_animation']['schema'] == portable.SCHEMA, 'Missing portable Action contract')
    require(same_pin(contract['portable_animation_helper'], witness.pin(portable.__file__)), 'Portable Action helper changed')
    require(same_pin(result['artifact'], witness.pin(result['artifact']['path'])), 'Candidate artifact pin differs')
    required = ('source_restored_exact', 'input_disk_unchanged', 'artist_disk_unchanged', 'staged_source_unchanged',
                'runner_dependencies_unchanged', 'witness_dependencies_unchanged', 'decision_policy_unchanged',
                'strict_nonvector_outputs_exact', 'existing_actions_slots_curves_unchanged',
                'native_only_replay_sequences_completed', 'bake_exact_live_equivalence',
                'source_live_declared_screen_passed', 'source_bake_declared_screen_passed')
    require(all(result.get(key) is True for key in required), 'Artifact receipt failed a required gate')
    require(result['cleanup']['errors'] == [] and all(value is True for key, value in result['cleanup'].items()
                                                     if key != 'errors'), 'Artifact cleanup failed')
    require(all(value is True for key, value in result['serialization_proof'].items() if key.endswith('_exact')),
            'Artifact serialization changed protected source/candidate content')
    return result, {'path': str(path), 'sha256': expected_sha256, 'bytes': len(raw)}


def handlers():
    import bpy
    return {name: [{'module': getattr(item, '__module__', None), 'name': getattr(item, '__qualname__', repr(item)),
                    'identity': id(item)} for item in value]
            for name in dir(bpy.app.handlers) if isinstance((value := getattr(bpy.app.handlers, name)), list)}


class PythonErrorTee:
    """Observe Python callback errors without wrapping/changing any handler."""
    def __init__(self, original):
        self.original, self.text, self.truncated = original, '', False

    def write(self, text):
        self.original.write(text)
        remaining = 32768-len(self.text)
        if remaining > 0:
            self.text += text[:remaining]
        self.truncated |= len(text) > max(remaining, 0)
        return len(text)

    def flush(self):
        self.original.flush()

    def __getattr__(self, name):
        return getattr(self.original, name)

    def has_error(self):
        return 'Traceback (most recent call last)' in self.text or 'Error in bpy.app.handlers' in self.text


def normalize_ids(contract):
    """Only explicit serialized ID pairs normalize logical display identities."""
    import bpy
    inventory = {}
    for prop in bpy.data.bl_rna.properties:
        if prop.type == 'COLLECTION':
            for item in getattr(bpy.data, prop.identifier):
                if isinstance(item, bpy.types.ID):
                    inventory.setdefault((type(item).__name__, item.name_full), []).append(item)
    reverse = {}
    for item in contract['logical_ids']:
        route = item['route']
        if route['kind'] == 'embedded':
            require(route['attribute'] in ('collection', 'node_tree'), 'Unknown embedded native ID route')
            owners = inventory.get((route['owner_type'], route['owner_name']), ())
            require(len(owners) == 1 and owners[0].library is None and not owners[0].is_embedded_data,
                    'Embedded native ID owner is not one exact local Main ID')
            target = getattr(owners[0], route['attribute'], None)
            require(target is not None and target.is_embedded_data, 'Embedded owner lost its native child')
        else:
            require(route['kind'] == 'main', 'Unknown serialized native ID route')
            matches = inventory.get((item['target_type'], item['target_name']), ())
            require(len(matches) == 1, 'Serialized Main ID mapping is ambiguous or missing')
            target = matches[0]
            require(not target.is_embedded_data, 'Embedded ID was incorrectly routed through Main')
        require(type(target).__name__ == item['target_type'] and target.name_full == item['target_name']
                and bool(target.is_embedded_data) == item['is_embedded_data'] and target.library is None,
                'Serialized private ID identity/type/name/ownership changed')
        proxy = type(item['source_type'], (), {})()
        proxy.name_full = item['source_name']
        proxy.library = type('LogicalLibrary', (), {'filepath': item['source_library']})() if item['source_library'] else None
        require(target.as_pointer() not in reverse, 'Repeated serialized native ID mapping')
        reverse[target.as_pointer()] = proxy
    return reverse


class ReopenSession:
    def __init__(self, args, stream):
        self.args, self.stream = args, stream
        self.timer = self.tick
        self.receipt, self.receipt_pin = load_receipt(args.artifact_report, args.artifact_report_sha256)
        self.contract = self.receipt['reopen_contract']
        self.artifact = Path(self.receipt['artifact']['path']).resolve()
        self.artist = Path(args.artist).resolve(strict=True)
        require(self.artifact != self.artist and not os.path.samefile(self.artifact, self.artist), 'Never reopen artist')
        self.artist_pin = witness.pin(self.artist)
        require(same_pin(self.artist_pin, self.receipt['artist_after']), 'Artist disk differs from candidate proof')
        self.package = Path(args.addons).resolve() / 'character_designer'
        self.manifest_path = Path(args.source_manifest).resolve(strict=True)
        self.manifest = json.loads(self.manifest_path.read_text(encoding='utf-8-sig'))
        require(same_pin(witness.pin(self.manifest_path), self.receipt['source_manifest']), 'Source Stage manifest differs')
        self.package_pins = witness.verify_package_manifest(self.package, self.manifest)
        require(self.package_pins == self.receipt['source_seal'], 'Source Stage/package differs')
        require(witness.witness_dependency_pins() == self.receipt['witness_dependency_pins'], 'Native witness changed')
        for pin in self.receipt['scripts'].values():
            require(same_pin(pin, witness.pin(pin['path'])), 'Artifact runner dependency changed')
        self.phase, self.frame, self.stable_ticks = 'WAIT_STANDARD_LOAD', 1, 0
        self.standard_handlers = self.stderr_tee = None
        self.started = time.monotonic()
        self.report = {'schema': 'x.independent-artifact-gui-reopen/1', 'completed': False,
            'pid': os.getpid(), 'artifact_receipt': self.receipt_pin, 'artifact': self.receipt['artifact'],
            'artist_before': self.artist_pin, 'script': witness.pin(__file__),
            'portable_helper': witness.pin(portable.__file__), 'frames': [], 'lifecycle_observations': [],
            'gui_fps_verified': False, 'no_scene_save': True, 'no_manual_helper_or_core_calls': True,
            'no_handler_disable_or_runtime_defer': True, 'preview_process_left_alive': True,
            'limits': 'Integer clip geometry/animation reopening only; GUI FPS, subframes, other clips/physics remain unverified.'}

    def flush(self):
        self.stream.seek(0)
        self.stream.write(json.dumps(self.report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
        self.stream.truncate()
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def start(self):
        import bpy
        require(not bpy.app.background and '--factory-startup' in sys.argv, 'A new factory-startup GUI process is required')
        require(not bpy.data.filepath and not bpy.data.is_dirty, 'Refuse an already opened or dirty artist/window')
        require(bpy.app.version_string == self.receipt['blender'], 'Native Blender version differs')
        require(math.isfinite(self.args.timeout) and 0 < self.args.timeout <= 3600., 'Invalid bounded GUI verification timeout')
        self.stderr_tee = PythonErrorTee(sys.stderr)
        sys.stderr = self.stderr_tee
        self.report['callbacks_before_registration'] = handlers()
        sys.path.insert(0, str(self.package.parent))
        self.addon = importlib.import_module('character_designer')
        self.runtime = importlib.import_module('character_designer.forearm_twist')
        require(Path(self.addon.__file__).resolve().parent == self.package, 'Imported another add-on package')
        self.addon.register()
        self.report['callbacks_after_standard_registration'] = handlers()
        require('FINISHED' in bpy.ops.wm.open_mainfile(filepath=str(self.artifact)), 'Candidate open failed')
        require(Path(bpy.data.filepath).resolve() == self.artifact, 'Opened a different file')
        require(self.contract['scene_name'] in bpy.data.scenes, 'Serialized candidate Scene is missing')
        self.scene = bpy.data.scenes[self.contract['scene_name']]
        require(bpy.context.scene is self.scene, 'Standard open did not select the candidate Scene')
        require(set(self.scene.objects.keys()) == set(self.contract['logical_objects'].values()), 'Candidate object membership differs')
        self.pairs = [(logical, self.scene.objects[actual]) for logical, actual in self.contract['logical_objects'].items()]
        self.objects = dict(self.pairs)
        self.reverse = normalize_ids(self.contract)
        require(not any(obj.type == 'MESH' and self.runtime.RECORD_KEY in obj for obj in self.scene.objects),
                'Loaded candidate enrolled a mesh in the authoring solver')
        self.actions = tuple(bpy.data.actions[name] for name in self.contract['portable_animation']['actions'])
        self.forward = {row['frame']: row for row in self.receipt['replay_checks'] if row['sequence'] == 'forward'}
        require(set(self.forward) == set(range(1, 31)), 'Candidate forward receipt coverage differs')
        self.report['callbacks_after_standard_open'] = handlers()
        self.report['worker_dirty_after_open'] = bpy.data.is_dirty
        self.flush()
        # Registered only after open: normal file load cannot discard this
        # nonpersistent timer before it has observed natural lifecycle completion.
        bpy.app.timers.register(self.timer, first_interval=.1)

    def lifecycle(self):
        import bpy
        runtime = self.runtime
        observed = {name: bool(getattr(runtime, name)) for name in
                    ('_RUNTIME_REGISTERED', '_INITIALIZE_PENDING', '_SCENE_CLEANUP_PENDING', '_SCENE_STATE_ACTIVE', '_BUSY')}
        observed['natural_lifecycle_timer_registered'] = bpy.app.timers.is_registered(runtime._complete_runtime_lifecycle)
        observed['errors'] = dict(runtime._ERRORS)
        return observed

    def verify_frame(self):
        import bpy
        require(self.scene.frame_current == self.frame and self.scene.frame_subframe == 0., 'Candidate frame changed during event-loop yield')
        graph = bpy.context.evaluated_depsgraph_get()
        current, raw = geometry.bone_frame_witness(self.scene, self.pairs, self.runtime, self.reverse,
            self.contract['converted_meshes'], self.contract['original_rig_bones'])
        expected = self.forward[self.frame]
        require(current['sha256'] == expected['versus_source']['candidate_strict_sha256'], 'Reopened strict geometry/foreign keys/original Rig output changed')
        for name, fields in raw.items():
            for field, values in fields.items():
                match = expected['versus_source']['meshes'][name][field]
                require(len(values)//12 == match['vector_count'] and hashlib.sha256(values).hexdigest() == match['candidate_sha256'],
                        'Reopened full coordinate/normal output differs: ' + name + ':' + field)
        worlds = witness.object_hash({name: current['scope'][name]['evaluated_object_world_matrix_hex'] for name in raw})
        require(worlds == expected['mesh_world_sha256'], 'Reopened mesh world transforms changed')
        helper_hashes = {}
        for owner, names in self.contract['helper_names'].items():
            mesh = self.objects[owner]
            require(mesh.modifiers and mesh.modifiers[0].type == 'ARMATURE', 'Candidate Armature binding changed')
            rig = mesh.modifiers[0].object
            require(rig is not None and rig.type == 'ARMATURE', 'Candidate private rig is missing')
            rests = {name: witness.exact_matrix(rig.data.bones[name].matrix_local) for name in names}
            require(witness.object_hash(rests) == self.contract['helper_rest_sha256'][owner], 'Reopened helper Rest changed')
            evaluated = rig.evaluated_get(graph)
            matrices = {name: witness.exact_matrix(evaluated.pose.bones[name].matrix @ rig.data.bones[name].matrix_local.inverted())
                        for name in names}
            helper_hashes[owner] = witness.object_hash(matrices)
            require(helper_hashes[owner] == expected['helper_matrix_oracle'][owner]['deformation_sha256'], 'Reopened helper deformation matrix differs')
        require(portable.capture(self.scene, self.actions) == self.contract['portable_animation'],
                'Reopened stored Action/curves/slots/drivers/clip/custom-ID content changed')
        require(handlers() == self.standard_handlers, 'Standard callback set changed during frame validation')
        self.report['frames'].append({'frame': self.frame, 'strict_geometry_sha256': current['sha256'],
            'all_full_coordinates_normals_exact': True, 'mesh_world_sha256': worlds,
            'helper_deformation_hashes': helper_hashes, 'portable_animation_exact': True})

    def finish(self, error=None):
        import bpy
        if error is not None:
            self.report['error'] = error
        cleanup_errors = []
        try:
            self.report['callbacks_at_finish'] = handlers()
            if bpy.app.timers.is_registered(self.timer):
                bpy.app.timers.unregister(self.timer)
            require(not bpy.app.timers.is_registered(self.timer), 'Own verification timer did not unregister')
            self.report['own_verification_timer_removed'] = True
        except BaseException:
            cleanup_errors.append(traceback.format_exc())
        try:
            self.report['artist_after'] = witness.pin(self.artist)
            require(self.artist_pin == self.report['artist_after'], 'Artist disk changed during GUI validation')
            require(same_pin(self.receipt['artifact'], witness.pin(self.artifact)), 'Candidate disk changed')
            require(self.package_pins == witness.verify_package_manifest(self.package, self.manifest), 'Source package changed')
            require(same_pin(self.receipt['source_manifest'], witness.pin(self.manifest_path)), 'Source manifest changed')
            require(same_pin(self.receipt_pin, witness.pin(self.receipt_pin['path'])), 'Candidate receipt changed')
            require(same_pin(self.receipt['decision_policy'], witness.pin(self.receipt['decision_policy']['path'])),
                    'Decision policy changed')
            require(same_pin(self.report['script'], witness.pin(__file__))
                    and same_pin(self.report['portable_helper'], witness.pin(portable.__file__)),
                    'Reopen entry or portable Action helper changed during verification')
            for pin in self.receipt['scripts'].values():
                require(same_pin(pin, witness.pin(pin['path'])), 'Artifact runner dependency changed during verification')
            require(witness.witness_dependency_pins() == self.receipt['witness_dependency_pins'], 'Native witness changed')
            require(self.standard_handlers is not None and handlers() == self.standard_handlers,
                    'Standard callbacks changed, were removed or never settled')
            require(self.stderr_tee is not None and not self.stderr_tee.has_error(), 'Python standard callback errors were emitted')
            self.report['protected_disks_sources_callbacks_unchanged'] = True
        except BaseException:
            cleanup_errors.append(traceback.format_exc())
        self.report['cleanup_errors'] = cleanup_errors
        self.report['completed'] = error is None and not cleanup_errors and len(self.report['frames']) == 30
        self.report['normal_addon_lifecycle_reopen_verified'] = self.report['completed']
        self.report['addon_left_registered'] = self.runtime._RUNTIME_REGISTERED
        if self.stderr_tee is not None:
            self.report['python_stderr'] = {'text': self.stderr_tee.text, 'truncated': self.stderr_tee.truncated,
                'scope': 'Python stderr only; owned process native stderr log still requires independent inspection'}
            sys.stderr = self.stderr_tee.original
        self.flush()
        self.stream.close()

    def tick(self):
        import bpy
        try:
            require(time.monotonic()-self.started < self.args.timeout, 'GUI lifecycle/frame verification timeout')
            require(Path(bpy.data.filepath).resolve() == self.artifact and bpy.context.scene is self.scene,
                    'Owned preview window opened another file/Scene')
            observed = self.lifecycle()
            require(not observed['errors'], 'Natural standard lifecycle raised Forearm errors')
            require(not self.stderr_tee.has_error(), 'Natural Python callback emitted a traceback')
            if self.phase == 'WAIT_STANDARD_LOAD':
                self.report['lifecycle_observations'].append(observed)
                ready = (observed['_RUNTIME_REGISTERED'] and observed['_SCENE_STATE_ACTIVE']
                         and not observed['_INITIALIZE_PENDING'] and not observed['_SCENE_CLEANUP_PENDING']
                         and not observed['_BUSY'] and not observed['natural_lifecycle_timer_registered'])
                self.stable_ticks = self.stable_ticks+1 if ready else 0
                if self.stable_ticks < 2:
                    return .1
                self.standard_handlers = handlers()
                self.report['callbacks_after_natural_settle'] = self.standard_handlers
                require(portable.capture(self.scene, self.actions) == self.contract['portable_animation'], 'Natural load changed stored animation')
                self.phase = 'ADVANCE'
            require(not observed['_INITIALIZE_PENDING'] and not observed['_SCENE_CLEANUP_PENDING'] and not observed['_BUSY'],
                    'Runtime lifecycle became pending/busy during proof')
            if self.phase == 'ADVANCE':
                self.scene.frame_set(self.frame)
                self.phase = 'VERIFY'
                return .05
            self.verify_frame()
            self.flush()
            if self.frame == 30:
                self.finish()
                return None
            self.frame += 1
            self.phase = 'ADVANCE'
            return .05
        except BaseException:
            self.finish(traceback.format_exc())
            return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('artifact-report', 'artifact-report-sha256', 'artist', 'addons', 'source-manifest', 'report'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--timeout', type=float, default=180.)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    report_path = Path(args.report).resolve()
    protected = {Path(args.artist).resolve(), Path(args.artifact_report).resolve(),
                 Path(args.source_manifest).resolve(), Path(__file__).resolve(), Path(portable.__file__).resolve()}
    require(report_path not in protected and not report_path.exists(), 'Never overwrite protected evidence or artist')
    stream = report_path.open('x', encoding='utf-8')
    try:
        _SESSION = ReopenSession(args, stream)
        require(report_path != _SESSION.artifact, 'Report cannot replace candidate artifact')
        _SESSION.start()
    except BaseException:
        payload = _SESSION.report if _SESSION is not None else {'schema': 'x.independent-artifact-gui-reopen/1'}
        payload.update(completed=False, error=traceback.format_exc(), no_scene_save=True, gui_fps_verified=False)
        if _SESSION is not None and _SESSION.stderr_tee is not None:
            payload['python_stderr'] = {'text': _SESSION.stderr_tee.text, 'truncated': _SESSION.stderr_tee.truncated}
            sys.stderr = _SESSION.stderr_tee.original
        stream.seek(0)
        stream.write(json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
        stream.truncate()
        stream.flush()
        os.fsync(stream.fileno())
        stream.close()
        raise
