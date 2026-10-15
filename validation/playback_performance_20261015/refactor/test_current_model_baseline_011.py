"""Pure current baseline admission, extraction and startup-state checks."""
import ast
import copy
import io
import sys
import types
import unittest
from unittest.mock import patch

import current_model_private_gui_fps_probe_011 as probe
import native_current_baseline_gui_011 as startup


def config():
    return {'expected_pid': 777, 'private_blend': 'current.blend', 'private_sha256': 'a'*64,
        'private_bytes': 123, 'artist': 'artist.blend', 'addons': str(probe.STAGE/'addons'),
        'source_manifest': str(probe.STAGE/'source_manifest.json'), 'source_manifest_sha256': probe.MANIFEST_SHA,
        'mode': 'MATERIAL', 'kind': 'current-baseline', 'report': 'unused.json',
        'snapshot_report': 'snapshot.json', 'snapshot_report_sha256': 'b'*64,
        'startup_report': 'startup.json', 'startup_report_sha256': 'c'*64}


class BaselineTests(unittest.TestCase):
    def test_current_config_never_accepts_legacy_or_unknown_input_route(self):
        valid = config()
        self.assertEqual(probe.validate_config(valid, 777), valid)
        for change in ({'kind': 'baseline'}, {'kind': 'baked'}, {'allow_fixed_baseline': True},
                       {'private_bytes': True}, {'expected_pid': True}, {'private_sha256': 'x'*64},
                       {'source_manifest_sha256': 'd'*64}, {'addons': 'other'}):
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                probe.validate_config({**valid, **change}, 777)

    def test_startup_receipt_requires_real_pid_all_flags_and_current_input(self):
        script = {'path': 'startup.py', 'sha256': probe.STARTUP_SHA, 'bytes': 1}
        source, receipt = {'path': 'current.blend'}, {'path': 'snapshot.json'}
        report = {'schema': 'x.current-private-baseline-gui/1', 'completed': True, 'pid': 777,
            'errors': [], 'input_before': source, 'current_snapshot_receipt': receipt, 'script': script,
            'settled_scene': {'frame': 1, 'subframe': 0.}, **dict.fromkeys(probe.STARTUP_FLAGS, True)}
        with patch.object(probe, 'pin', return_value=script):
            probe.validate_startup(report, 777, source, receipt)
            for key in probe.STARTUP_FLAGS:
                with self.subTest(key=key), self.assertRaises(RuntimeError):
                    probe.validate_startup({**report, key: False}, 777, source, receipt)
            for change in ({'pid': 778}, {'schema': 'x.fixed-private-baseline-gui/1'}, {'completed': False},
                           {'errors': ['failed']}, {'input_before': {}}, {'settled_scene': {'frame': 21, 'subframe': 0.}}):
                with self.subTest(change=change), self.assertRaises(RuntimeError):
                    probe.validate_startup({**report, **change}, 777, source, receipt)

    def test_missing_snapshot_fails_before_bpy_or_constructor(self):
        with patch.object(probe.core.os, 'getpid', return_value=777), \
             patch.object(probe.current, 'load_snapshot', side_effect=RuntimeError('missing true receipt')), \
             patch.object(probe, '_initialize', side_effect=AssertionError('native ctor must not run')):
            with self.assertRaisesRegex(RuntimeError, 'missing true receipt'):
                probe.Probe(config())
        self.assertNotIn('bpy', sys.modules)

    def test_precise_constructor_extraction_and_untouched_clock_methods(self):
        old = probe.core.FIXED_BASELINE
        constructor, extraction = probe.sealed_constructor()
        self.assertEqual(extraction['v5_to_v9_literal_changes'], 2)
        self.assertEqual(set(extraction['removed_legacy_branches']),
            {"config['kind'] == 'baseline'", "config['kind'] == 'baked'"})
        self.assertIs(constructor.__globals__['validate_config'], probe.validate_config)
        self.assertEqual(constructor.__globals__['__file__'], probe.core.__file__)
        self.assertNotIn('FIXED_BASELINE', constructor.__code__.co_names)
        self.assertIn('native_validation_support_v9', constructor.__code__.co_consts)
        self.assertEqual(probe.core.FIXED_BASELINE, old)
        for name in ('tick', 'on_pre', 'on_post', 'on_draw', 'in_hot', 'context_state'):
            self.assertIs(getattr(probe.Probe, name), getattr(probe.core.Probe, name))
        self.assertEqual((probe.core.WARM_SECONDS, probe.core.MEASURE_SECONDS), (2., 16.))
        old_tree = ast.parse(probe.CORE_PATH.read_text(encoding='utf8'))
        node = next(item for cls in old_tree.body if isinstance(cls, ast.ClassDef) and cls.name == 'Probe'
            for item in cls.body if isinstance(item, ast.FunctionDef) and item.name == 'full_state')
        newer = copy.deepcopy(node)
        for item in ast.walk(newer):
            if isinstance(item, ast.Assign) and ast.unparse(item.targets[0]) == "parts['stored_actions']":
                item.value = ast.parse('action_witness(self.scene)', mode='eval').body
        self.assertEqual(probe.FULL_STATE_AST_SHA, probe.hashlib.sha256(ast.dump(newer, include_attributes=False).encode()).hexdigest())

    def test_v9_actions_include_unused_author_flags_and_original_owner_scope(self):
        calls = []
        class Reader:
            OMIT_ID_FIELDS = {'users'}
            bulk_keyframe_collections, bulk_keyframe_points = 2, 50
            def __init__(self, native_type):
                pass
            def rna(self, value, path):
                calls.append(path)
                return copy.deepcopy(value.fields)
        used = types.SimpleNamespace(name_full='Used', fields={'slots': [{'selected': True}], 'points': [1., 2.]})
        unused = types.SimpleNamespace(name_full='Unused', fields={'curves': [{'select': True}], 'raw': {'x': 4}})
        scene = types.SimpleNamespace(name_full='Scene', animation_data=types.SimpleNamespace(fields={'action_slot': 3}),
            objects=[types.SimpleNamespace(type='ARMATURE', name_full='Rig', animation_data=types.SimpleNamespace(fields={'nla': ['A']})),
                     types.SimpleNamespace(type='MESH', name_full='Body', animation_data=None)])
        bpy = types.SimpleNamespace(types=types.SimpleNamespace(ID=object), data=types.SimpleNamespace(actions=[used, unused]))
        extension = types.SimpleNamespace(Reader=Reader, object_hash=probe.current.base.object_hash)
        with patch.dict(sys.modules, bpy=bpy), patch.object(probe.importlib, 'import_module', return_value=extension):
            before = probe.action_witness(scene)
            self.assertEqual(set(before['actions']), {'Used', 'Unused'})
            self.assertEqual(len(before['scene_and_rig_animation']), 2)
            self.assertIn('animation:Rig', calls)
            self.assertNotIn('animation:Body', calls)
            unused.fields['curves'][0]['select'] = False
            after = probe.action_witness(scene)
            self.assertNotEqual(before['actions']['Unused'], after['actions']['Unused'])
            used.fields['slots'][0]['selected'] = False
            self.assertNotEqual(before['actions']['Used'], probe.action_witness(scene)['actions']['Used'])
            with patch.object(Reader, 'rna', side_effect=ValueError('guard failure')), self.assertRaises(ValueError):
                probe.action_witness(scene)

    def test_view_comparison_rejects_camera_and_keeps_all_requested_fields(self):
        context = {key: key for key in probe.VIEW_FIELDS}
        context.update(perspective='PERSP', local_view=False, unrelated_pointer=99)
        self.assertEqual(set(probe.comparison_view(context)), set(probe.VIEW_FIELDS))
        self.assertNotIn('unrelated_pointer', probe.comparison_view(context))
        for change in ({'perspective': 'CAMERA'}, {'local_view': True}):
            with self.assertRaises(RuntimeError):
                probe.comparison_view({**context, **change})

    def test_private_startup_base_keeps_actual_pins_and_does_not_mutate010(self):
        original_input = startup.original.INPUT
        source = {'copy': {'path': str(probe.HERE/'new_current.blend'), 'sha256': 'a'*64, 'bytes': 12}}
        cls, digest = startup.private_base(source)
        scope = cls.__init__.__globals__
        self.assertEqual(scope['INPUT'], probe.HERE/'new_current.blend')
        self.assertEqual(scope['INPUT_SHA'], 'a'*64)
        self.assertEqual(scope['STAGE'], probe.STAGE)
        self.assertEqual(scope['stage_pins'].__globals__['STAGE'], probe.STAGE)
        self.assertEqual(startup.original.INPUT, original_input)
        self.assertEqual(len(digest), 64)

    def test_startup_two_settles_one_normal_seek_then_proof_or_failure(self):
        for proof_error in (False, True):
            with self.subTest(proof_error=proof_error):
                calls = []
                class Base:
                    def __init__(self, report):
                        self.report, self.ready_count, self.last = {'natural_lifecycle_changes': []}, 0, None
                        self.started, self.timer = startup.original.time.monotonic(), self.tick
                    def start(self):
                        calls.append('standard_load')
                    def finish(self, error=None):
                        self.report.update(completed=error is None, errors=[error] if error else [])
                class Native:
                    def __init__(self, name):
                        self.name = self.name_full = name
                    def as_pointer(self):
                        return id(self)
                layer = Native('SourceLayer')
                class Objects(list):
                    active = None
                layer.objects = Objects()
                scene = Native('SourceScene')
                scene.frame_current, scene.frame_subframe, scene.sync_mode = 21, 0., 'NONE'
                scene.view_layers = types.SimpleNamespace(get=lambda name: layer if name == layer.name else None)
                def seek(frame, subframe):
                    calls.append(('normal_seek', frame, subframe))
                    scene.frame_current = frame
                scene.frame_set = seek
                context = types.SimpleNamespace(scene=scene, view_layer=layer, window=types.SimpleNamespace(view_layer=layer))
                bpy = types.SimpleNamespace(context=context, data=types.SimpleNamespace(filepath=str(probe.HERE/'new.blend'), is_dirty=False),
                    app=types.SimpleNamespace(timers=types.SimpleNamespace(is_registered=lambda _: False)))
                runtime = types.SimpleNamespace(_RUNTIME_REGISTERED=True, _SCENE_STATE_ACTIVE=True, _BUSY=False,
                    _INITIALIZE_PENDING=False, _SCENE_CLEANUP_PENDING=False, _ERRORS={}, _complete_runtime_lifecycle=lambda: None)
                Base.runtime = runtime
                snapshot = {'copy': {'path': bpy.data.filepath}, 'source_identity':
                    {'scene': scene.name, 'view_layer': layer.name, 'frame': [21, 0.]}}
                witness = types.SimpleNamespace(handler_snapshot=lambda: {}, source_property_witness=lambda scene:
                    (_ for _ in ()).throw(ValueError('unsafe getter')) if proof_error else {'sha256': 'c'*64})
                args = types.SimpleNamespace(snapshot_report='receipt.json', snapshot_report_sha256='a'*64,
                    input_sha256='b'*64, input_bytes=12, report='unused.json')
                with patch.dict(sys.modules, bpy=bpy), patch.object(startup, 'private_base', return_value=(Base, 'd'*64)), \
                     patch.object(probe.current, 'load_snapshot', return_value=(snapshot, {'path': 'receipt.json'})), \
                     patch.object(startup, 'pin', side_effect=lambda path: {'path': str(path)}), \
                     patch.object(probe.importlib, 'import_module', return_value=witness):
                    controller = startup.start(args)
                    for _ in range(4):
                        controller.tick()
                    self.assertEqual(calls, ['standard_load', ('normal_seek', 1, 0.)], controller.report.get('errors'))
                    self.assertEqual(controller.report['completed'], not proof_error)
                    self.assertTrue(controller.report['normal_source_frame1_settled'])

    def test_finish_failure_clears_own_session(self):
        controller = object.__new__(probe.Probe)
        controller.closed, controller.collecting, controller.report = False, True, {}
        controller.post_events, controller.draw_events = [], []
        probe.SESSION = controller
        try:
            with patch.object(probe.core.Probe, 'finish', side_effect=ValueError('native cleanup')):
                with self.assertRaises(ValueError):
                    controller.finish()
            self.assertIsNone(probe.SESSION)
        finally:
            probe.SESSION = None

    def test_constructor_handler_mismatch_closes_stream_before_install(self):
        stream = io.StringIO()
        def initialize(controller, config):
            controller.stream, controller.handlers_before = stream, {'post': [1]}
        with patch.object(probe.core.os, 'getpid', return_value=777), \
             patch.object(probe.current, 'load_snapshot', return_value=({'copy': {'path': 'current.blend'}}, {})), \
             patch.object(probe.core, 'load_pinned_json', return_value=({'callbacks_after_natural_settle': {'post': [2]}}, {})), \
             patch.object(probe, 'validate_startup'), patch.object(probe, '_initialize', side_effect=initialize):
            with self.assertRaisesRegex(RuntimeError, 'callback identities'):
                probe.Probe(config())
        self.assertTrue(stream.closed)

    def test_hot_current_health_uses_only_literal_file_and_rna(self):
        class Mesh(dict):
            type = 'MESH'
            session_uid = 2
            def as_pointer(self):
                return 1
        mesh = Mesh(record=1)
        controller = object.__new__(probe.Probe)
        controller.collecting, controller.config = True, {'expected_pid': 777}
        controller.loaded_filepath_literal = 'verified-current.blend'
        controller.scene = types.SimpleNamespace(name_full='Source', objects=[mesh], frame_start=1, frame_end=30,
            use_preview_range=False, frame_preview_start=1, frame_preview_end=30, sync_mode='NONE',
            render=types.SimpleNamespace(fps=30, fps_base=1.))
        controller.snapshot = {'source_identity': {'scene': 'Source', 'view_layer': 'SourceLayer'}}
        controller.runtime = types.SimpleNamespace(RECORD_KEY='record')
        controller.area = types.SimpleNamespace(type='VIEW_3D', spaces=types.SimpleNamespace(active=types.SimpleNamespace(
            region_3d=types.SimpleNamespace(view_perspective='PERSP'))))
        controller.screen = types.SimpleNamespace(areas=[controller.area])
        layer = types.SimpleNamespace(name='SourceLayer', as_pointer=lambda: 3)
        controller.window = types.SimpleNamespace(screen=controller.screen, scene=controller.scene, view_layer=layer)
        controller.hot_layer, controller.hot_objects = 3, frozenset({(1, 2)})
        controller.hot_scene_settings = probe.scene_settings(controller.scene)
        bpy = types.SimpleNamespace(data=types.SimpleNamespace(filepath=controller.loaded_filepath_literal))
        with patch.dict(sys.modules, bpy=bpy), patch.object(probe.core.Probe, 'assert_runtime'), \
             patch.object(probe.core.os, 'getpid', return_value=777), \
             patch.object(probe.Path, 'resolve', side_effect=AssertionError('hot path IO')), \
             patch.object(probe, 'pin', side_effect=AssertionError('hot file proof')):
            controller.assert_owned()
            controller.scene.sync_mode = 'AUDIO_SYNC'
            with self.assertRaises(RuntimeError):
                controller.assert_owned()
            controller.scene.sync_mode = 'NONE'
            controller.area.spaces.active.region_3d.view_perspective = 'CAMERA'
            with self.assertRaises(RuntimeError):
                controller.assert_owned()

    def test_pure_import(self):
        self.assertNotIn('bpy', sys.modules)


if __name__ == '__main__':
    unittest.main()
