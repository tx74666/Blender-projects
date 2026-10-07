"""Direct author-channel refusal using the existing pure Dress export fixtures.

No Blender evaluation, strip, FBX, Unity, or public Direct admission is exercised.
"""
import ast
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
REPO = Path('D:/MyRepository/Blender-addons-by-Randy')
EVIDENCE = Path(__file__).resolve().parent
SOURCE = REPO / 'addons/character_designer/dress_export_snapshot.py'
spec = importlib.util.spec_from_file_location('existing_dress_animation_tests',
                                            REPO / 'tests/test_dress_animation_export.py')
existing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(existing)


class DirectPhysicalEndpoints(unittest.TestCase):
    def fixture(self):
        env = existing.DressAnimationExport()
        env.setUp()
        self.addCleanup(env.doCleanups)
        source, rig = env.source, env.rig
        source.holder['physics_influence'] = 0.
        source.record['physics']['backend'] = 'DIRECT_MAIN_CLOTH_V1'
        surface = source.record['physics']['surface']
        del surface['cloth_modifier']
        del surface['roles']['NEUTRAL_RIG']
        env.bpy.data.objects.remove(source.neutral)
        source.cloth.modifiers[:0] = [NS(name='Native skin', type='ARMATURE'),
                                     NS(name='Body input', type='SURFACE_DEFORM')]
        chain = source.record['chains'][0]
        chain['manual'] = ['Dress Manual']
        bone = rig.pose.bones[chain['def'][0]]
        manual, rotation = bone.constraints
        manual.type, manual.target, manual.subtarget = 'COPY_TRANSFORMS', rig, 'Dress Manual'
        rotation.type, rotation.target, rotation.subtarget = 'COPY_ROTATION', rig, chain['phys'][0]
        rotation.mute = True
        hook = NS(type='HOOK', show_viewport=True, show_render=True, object=rig, subtarget='Dress Mid')
        wire = NS(name='Native Manual wire', modifiers=[hook])
        spline = NS(name='Native Manual Spline IK', type='SPLINE_IK', mute=False, influence=1., target=wire)
        rig.pose.bones.append(NS(name='Dress Manual', constraints=existing.Named([spline])))
        source.properties[env.module.RECORD_KEY] = json.dumps(source.record)
        env.rotation, env.manual, env.wire, env.spline = rotation, manual, wire, spline
        return env

    def guard(self, env):
        return env.module._physical_animation_guard(env.source, env.source.record, env.selected)

    def state(self, env):
        ad = env.rig.animation_data
        return (copy.deepcopy(env.source.holder),
                tuple((c.name, c.mute, getattr(c, 'type', None), getattr(c, 'subtarget', None))
                      for b in env.rig.pose.bones for c in b.constraints),
                tuple((m.name, getattr(m, 'show_viewport', None), getattr(m, 'show_render', None))
                      for m in env.source.cloth.modifiers),
                (env.spline.mute, env.spline.influence, env.spline.target is env.wire),
                tuple((m.show_viewport, m.show_render, m.object is env.rig, m.subtarget)
                      for m in env.wire.modifiers),
                tuple((c.data_path, c.mute) for a in env.module._actions(env.rig, env.selected)
                      for c in env.module._curves(a)),
                tuple((c.data_path, c.mute, getattr(getattr(c, 'driver', None), 'type', None))
                      for c in ad.drivers))

    def refuse(self, env, message):
        before = self.state(env)
        with self.assertRaisesRegex(ValueError, message):
            self.guard(env)
        self.assertEqual(self.state(env), before)

    def install_author_channel(self, env, kind, path):
        authored = existing.action(path, layered=(kind == 'layered'))
        authored.fcurves[0].keyframe_value = False
        if kind in ('selected', 'layered'):
            env.selected = authored
        elif kind == 'active':
            env.rig.animation_data.action = authored
        elif kind == 'nla_meta':
            child = NS(action=authored, strips=[])
            env.rig.animation_data.nla_tracks = [NS(strips=[NS(action=None, strips=[child])])]
        elif kind == 'driver':
            driver = existing.curve(path)
            driver.driver = NS(type='SCRIPTED', variables=[])
            env.rig.animation_data.drivers.append(driver)

    def test_direct_plan_is_read_only_and_contains_no_manual_endpoints(self):
        env = self.fixture()
        env.selected = existing.action('pose.bones["Dress Mid"].rotation_euler', layered=True)
        env.selected.fcurves.extend([existing.curve('pose.bones["Dress Manual"].rotation_quaternion'),
                                    existing.curve(env.manual.path_from_id() + '.mute')])
        before = self.state(env)
        cloth, endpoints = self.guard(env)
        self.assertIs(cloth, env.source.cloth.modifiers[-1])
        self.assertEqual(endpoints, [env.rotation])
        self.assertNotIn(env.manual, endpoints)
        self.assertNotIn(env.spline, endpoints)
        self.assertEqual(self.state(env), before)

    def test_numeric_zero_excludes_bools_missing_nonfinite_and_nonzero(self):
        for value in (False, True, None, '0', .001, float('nan'), float('inf')):
            with self.subTest(value=value):
                env = self.fixture()
                env.source.holder['physics_influence'] = value
                # NaN cannot be compared with itself in the state assertion.
                with self.assertRaisesRegex(ValueError, 'numeric zero'):
                    self.guard(env)
                self.assertIs(env.source.holder['physics_influence'], value)
                self.assertTrue(env.rotation.mute)
        for value in (0, 0., -0.):
            with self.subTest(accepted=value):
                env = self.fixture()
                env.source.holder['physics_influence'] = value
                self.assertEqual(self.guard(env)[1], [env.rotation])

    def test_edited_or_live_old_copy_rotation_is_refused(self):
        for attribute, value in (('mute', False), ('type', 'COPY_TRANSFORMS'),
                                 ('target', None), ('subtarget', 'Artist Bone')):
            with self.subTest(attribute=attribute):
                env = self.fixture()
                setattr(env.rotation, attribute, value)
                self.refuse(env, 'Copy Rotation')

    def test_selected_active_layered_and_nested_nla_constraint_channels_are_refused(self):
        paths = ('pose.bones["Dress DEF"].constraints["Skirt physics delta"].mute',
                 "pose.bones['Dress DEF'].constraints['Skirt physics delta'].influence",
                 'pose.bones["Dress DEF"].constraints[1].target',
                 "pose.bones['Dress DEF'].constraints[1].subtarget",
                 'pose.bones["Dress DEF"].constraints[1]["custom_property"]')
        for kind in ('selected', 'active', 'layered', 'nla_meta'):
            for path in paths:
                with self.subTest(kind=kind, path=path):
                    env = self.fixture()
                    self.install_author_channel(env, kind, path)
                    # Even a muted curve / false key is retained and refused.
                    self.refuse(env, 'author Action/NLA')

    def test_zero_influence_property_cannot_be_rewritten_by_author_channels(self):
        for kind in ('selected', 'active', 'layered', 'nla_meta', 'driver'):
            for path_kind in ('shared', 'shared_quote_alias', 'rig_property'):
                with self.subTest(kind=kind, path_kind=path_kind):
                    env = self.fixture()
                    if path_kind == 'rig_property':
                        env.source.path = '["physics_influence"]'
                        env.rig.animation_data.drivers[0].driver.variables[0].targets[0].data_path = env.source.path
                    path = env.source.path.replace('"', "'") if path_kind == 'shared_quote_alias' else env.source.path
                    self.install_author_channel(env, kind, path)
                    self.refuse(env, 'physics_influence has author')

    def test_only_the_unique_generated_influence_driver_is_allowed(self):
        for reason in ('mute_property', 'target_property', 'indexed_influence', 'scripted',
                       'muted_generated', 'wrong_target', 'wrong_path', 'wrong_variable',
                       'extra_variable', 'missing', 'duplicate'):
            with self.subTest(reason=reason):
                env = self.fixture()
                drivers = env.rig.animation_data.drivers
                generated = drivers[0]
                if reason in ('mute_property', 'target_property', 'indexed_influence'):
                    path = env.rotation.path_from_id() + ('.mute' if reason == 'mute_property' else '.target')
                    if reason == 'indexed_influence':
                        path = "pose.bones['Dress DEF'].constraints[1].influence"
                    self.install_author_channel(env, 'driver', path)
                elif reason == 'scripted': generated.driver.type = 'SCRIPTED'
                elif reason == 'muted_generated': generated.mute = True
                elif reason == 'wrong_target': generated.driver.variables[0].targets[0].id = None
                elif reason == 'wrong_path': generated.driver.variables[0].targets[0].data_path = '["other"]'
                elif reason == 'wrong_variable': generated.driver.variables[0].type = 'TRANSFORMS'
                elif reason == 'extra_variable': generated.driver.variables.append(generated.driver.variables[0])
                elif reason == 'missing': drivers.clear()
                elif reason == 'duplicate': drivers.append(generated)
                self.refuse(env, 'physical.*driver|generated physical influence driver')

    def test_every_def_endpoint_is_checked(self):
        env = self.fixture()
        second = copy.copy(env.rig.pose.bones['Dress DEF'])
        second.name = 'Second DEF'
        rotation = copy.copy(env.rotation)
        rotation.subtarget = 'Second PHYS'
        second.path_from_id = lambda: 'pose.bones["Second DEF"]'
        rotation.path_from_id = lambda: 'pose.bones["Second DEF"].constraints["Skirt physics delta"]'
        second.constraints = existing.Named([copy.copy(env.manual), rotation])
        env.rig.pose.bones.append(second)
        env.source.record['chains'].append({'def': ['Second DEF'], 'phys': ['Second PHYS']})
        generated = copy.deepcopy(env.rig.animation_data.drivers[0])
        generated.data_path = rotation.path_from_id() + '.influence'
        generated.driver.variables[0].targets[0].id = env.rig
        env.rig.animation_data.drivers.append(generated)
        self.assertEqual(self.guard(env)[1], [env.rotation, rotation])
        env.selected = existing.action('pose.bones["Second DEF"].constraints[1].mute')
        self.refuse(env, 'author Action/NLA')

    def test_public_direct_record_reject_and_other_functions_are_unchanged(self):
        env = self.fixture()
        with self.assertRaisesRegex(ValueError, 'Direct Dress skeletal export validation is pending'):
            env.module._record(env.source)
        def remaining(path):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            changed = {'_physical_animation_guard', '_service_for_record',
                       'capture_animation_surfaces', '_proved_sources', 'prepare_animation_snapshot'}
            tree.body = [node for node in tree.body if not (isinstance(node, ast.FunctionDef)
                         and node.name in changed)]
            return ast.dump(tree, include_attributes=False)
        self.assertEqual(remaining(SOURCE), remaining(EVIDENCE / 'before_dress_export_snapshot.py'))


class MixedBackendDispatch(unittest.TestCase):
    def fixture(self, delta_name='A Delta'):
        env = DirectPhysicalEndpoints.fixture(self)
        delta = env.fixture(delta_name)
        env.delta = delta
        direct_service = ModuleType('_dress_animation_test.skirt_surface_direct')
        direct_service.BACKEND = 'DIRECT_MAIN_CLOTH_V1'
        env.direct_service = direct_service

        def proof_for(source):
            return {'version': 1, 'backend': source.record['physics']['backend'],
                    'source': source.name, 'rig': env.rig.name, 'owner': source.record['owner']}

        def direct_capture(source):
            self.assertEqual(source.record['physics']['backend'], direct_service.BACKEND)
            env.calls.append(('capture_direct', source.name))
            return proof_for(source)

        def direct_validate(source, proof):
            env.calls.append(('prove_direct', source.name))
            if not source.valid or proof != proof_for(source):
                raise ValueError('Direct snapshot proof rejected')

        def direct_strip(source, proof):
            direct_validate(source, proof)
            env.calls.append(('strip_direct', source.name))
            # Delta's endpoints must remain unchanged until both strips finish.
            self.assertFalse(env.rig.pose.bones[delta.record['chains'][0]['def'][0]].constraints[1].mute)
            self.assertFalse(env.rig.pose.bones[delta.record['chains'][0]['phys'][0]].constraints[0].mute)
            self.assertFalse(env.manual.mute)
            self.assertTrue(source.cloth.modifiers[-1].show_viewport)
            source.cloth.modifiers[-1].show_viewport = source.cloth.modifiers[-1].show_render = False
            source.stripped = True

        direct_service.export_capture = direct_capture
        direct_service.validate_snapshot = direct_validate
        direct_service.strip_export_snapshot = direct_strip
        delta_capture, delta_validate, delta_strip = (env.service.export_capture,
                                                     env.service.validate_snapshot,
                                                     env.service.strip_export_snapshot)

        def require_delta(source):
            self.assertEqual(source.record['physics']['backend'], env.service.BACKEND)

        def capture_delta(source):
            require_delta(source)
            env.calls.append(('capture_delta', source.name))
            return delta_capture(source)

        def validate_delta(source, proof):
            require_delta(source)
            return delta_validate(source, proof)

        def strip_delta(source, proof):
            require_delta(source)
            return delta_strip(source, proof)

        env.service.export_capture, env.service.validate_snapshot, env.service.strip_export_snapshot = (
            capture_delta, validate_delta, strip_delta)
        modules = patch.dict(sys.modules, {'_dress_animation_test.skirt_surface_direct': direct_service})
        modules.start()
        self.addCleanup(modules.stop)
        env.proof_for = proof_for
        return env

    def proved_records(self, env):
        # A private test seam only. Production _record continues to reject Direct.
        return patch.object(env.module, '_record', lambda source: getattr(source, 'record', None))

    def flags(self, env):
        return (DirectPhysicalEndpoints.state(self, env), env.source.stripped,
                env.native_flags(env.delta), env.source.cloth.modifiers[-1].show_viewport)

    def prepare(self, env, proofs):
        return env.module.prepare_animation_snapshot(env.rig, proofs, env.selected,
                    private_snapshot=env.bpy.data.filepath)

    def test_service_selection_uses_record_and_preserves_delta_service(self):
        env = self.fixture()
        original = env.module._service
        with patch.object(env.module, '_service', wraps=original) as delta_lookup:
            self.assertIs(env.module._service_for_record(env.delta.record), env.service)
            delta_lookup.assert_called_once_with()
        self.assertIs(env.module._service_for_record(env.source.record), env.direct_service)
        env.direct_service.BACKEND = 'OTHER_BACKEND'
        with self.assertRaisesRegex(ValueError, 'Direct Dress snapshot service'):
            env.module._service_for_record(env.source.record)
        with self.assertRaisesRegex(ValueError, 'snapshot backend'):
            env.module._service_for_record({'physics': {'backend': 'UNKNOWN'}})

    def test_mixed_capture_validation_roots_and_strip_dispatch_each_subset(self):
        for delta_name in ('A Delta', 'Z Delta'):
            with self.subTest(capture_order=delta_name):
                env = self.fixture(delta_name)
                before = self.flags(env)
                with self.proved_records(env):
                    captured = env.module.capture_animation_surfaces(NS(), env.rig, env.selected)
                    self.assertEqual({p['source']: p['backend'] for p in captured},
                                     {s.name: s.record['physics']['backend'] for s in (env.source, env.delta)})
                    self.assertEqual(self.flags(env), before)
                    self.assertEqual(env.module.snapshot_scene_roots(captured), {env.source.home, env.delta.home})
                    # Reverse proof order too; no cached first-provider assumption.
                    result = self.prepare(env, list(reversed(captured)))
                self.assertEqual({r['source']: r['backend'] for r in result},
                                 {s.name: s.record['physics']['backend'] for s in (env.source, env.delta)})
                self.assertTrue(env.source.stripped and env.delta.stripped)
                self.assertEqual({kind for kind, _name in env.calls if kind.startswith('strip')},
                                 {'strip', 'strip_direct'})
                self.assertFalse(env.manual.mute)
                self.assertFalse(env.spline.mute)
                self.assertTrue(all(m.show_viewport and m.show_render for m in env.wire.modifiers))
                self.assertFalse(env.rig.pose.bones['Dress PHYS'].constraints[0].mute)
                self.assertTrue(env.rig.pose.bones[env.delta.record['chains'][0]['def'][0]].constraints[1].mute)

    def test_tampered_proof_backend_cannot_choose_another_provider(self):
        env = self.fixture()
        proof = env.proof_for(env.source)
        proof['backend'] = env.service.BACKEND
        before = self.flags(env)
        with self.proved_records(env), self.assertRaisesRegex(ValueError, 'Direct snapshot proof rejected'):
            env.module._proved_sources([proof])
        self.assertEqual(env.calls, [('prove_direct', env.source.name)])
        self.assertEqual(self.flags(env), before)

    def test_later_subset_proof_or_author_channel_failure_precedes_every_strip(self):
        for reason in ('native_proof', 'selected_physical_channel'):
            with self.subTest(reason=reason):
                env = self.fixture()
                if reason == 'native_proof': env.source.valid = False
                else: env.selected = existing.action(env.rotation.path_from_id() + '.mute')
                before = self.flags(env)
                proofs = [env.proof_for(env.delta), env.proof_for(env.source)]
                with self.proved_records(env), self.assertRaises(ValueError):
                    self.prepare(env, proofs)
                self.assertEqual(self.flags(env), before)
                self.assertFalse(any(kind.startswith('strip') for kind, _name in env.calls))

    def test_every_planned_service_is_resolved_before_the_first_strip(self):
        env = self.fixture()
        proofs = [env.proof_for(env.delta), env.proof_for(env.source)]
        original = env.module._service_for_record
        direct_lookups = 0

        def lookup(record):
            nonlocal direct_lookups
            if record['physics']['backend'] == env.direct_service.BACKEND:
                direct_lookups += 1
                if direct_lookups == 2:
                    raise ValueError('Later Direct service unavailable during plan preflight')
            return original(record)

        before = self.flags(env)
        with self.proved_records(env), patch.object(env.module, '_service_for_record', side_effect=lookup), \
                self.assertRaisesRegex(ValueError, 'plan preflight'):
            self.prepare(env, proofs)
        self.assertEqual(self.flags(env), before)
        self.assertFalse(any(kind.startswith('strip') for kind, _name in env.calls))

    def test_public_direct_capture_and_prepare_still_refuse(self):
        env = self.fixture()
        before = self.flags(env)
        with self.assertRaisesRegex(ValueError, 'Direct Dress skeletal export validation is pending'):
            env.module.capture_animation_surfaces(NS(), env.rig, env.selected)
        with self.assertRaisesRegex(ValueError, 'Direct Dress skeletal export validation is pending'):
            self.prepare(env, [env.proof_for(env.source)])
        self.assertEqual(self.flags(env), before)
        self.assertFalse(any('direct' in kind for kind, _name in env.calls))
        self.assertFalse(any(kind.startswith('strip') for kind, _name in env.calls))


if __name__ == '__main__':
    loader = unittest.TestLoader()
    legacy = loader.loadTestsFromModule(existing)
    direct = loader.loadTestsFromTestCase(DirectPhysicalEndpoints)
    dispatch = loader.loadTestsFromTestCase(MixedBackendDispatch)
    counts = {'existing_delta_tests': legacy.countTestCases(), 'direct_tests': direct.countTestCases(),
              'mixed_dispatch_tests': dispatch.countTestCases()}
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.TestSuite([legacy, direct, dispatch]))
    (EVIDENCE / 'pure_tests.log').write_text(log.getvalue(), encoding='utf-8')
    hashes = json.loads((EVIDENCE / 'before_hashes.json').read_text(encoding='utf-8-sig'))
    unchanged = all(hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
                    for item in hashes if Path(item['path']) != SOURCE)
    report = dict(counts, tests_run=result.testsRun, passed=result.wasSuccessful(),
                  failures=[(str(test), message) for test, message in result.failures],
                  errors=[(str(test), message) for test, message in result.errors],
                  public_guard_and_worker_files_unchanged=unchanged,
                  source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  scope='PURE_SOURCE_ONLY', Blender_run=False, Unity_run=False,
                  export_admission_opened=False, deployed=False,
                  limitation='Fake RNA fixtures exercise preflight logic; native evaluation and export remain unverified.')
    (EVIDENCE / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(log.getvalue())
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
