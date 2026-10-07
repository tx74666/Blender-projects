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
from types import SimpleNamespace as NS
import unittest

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
            tree.body = [node for node in tree.body if not (isinstance(node, ast.FunctionDef)
                         and node.name == '_physical_animation_guard')]
            return ast.dump(tree, include_attributes=False)
        self.assertEqual(remaining(SOURCE), remaining(EVIDENCE / 'before_dress_export_snapshot.py'))


if __name__ == '__main__':
    loader = unittest.TestLoader()
    legacy = loader.loadTestsFromModule(existing)
    direct = loader.loadTestsFromTestCase(DirectPhysicalEndpoints)
    counts = {'existing_delta_tests': legacy.countTestCases(), 'direct_tests': direct.countTestCases()}
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.TestSuite([legacy, direct]))
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
