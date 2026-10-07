"""Public Add Physics selection-failure injection; no Blender/native proof."""
import ast
import copy
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SOURCE = Path('D:/MyRepository/Blender-addons-by-Randy/addons/character_designer/skirt.py')


class Named(list):
    def __getitem__(self, key):
        return next(item for item in self if item.name == key) if isinstance(key, str) else super().__getitem__(key)


class AddPhysicsSelectionRollback(unittest.TestCase):
    def fixture(self, *, actual=True, existing=False, selection_error=True, rollback_error=None, install_error=False):
        calls, reports = [], []
        collection = NS(is_visible=False)
        control = NS(name='Waist', hide=True, collections=[collection])
        other = NS(name='Artist Bone', hide=False, collections=[])
        bones = Named([control, other]); bones.active = other
        poses = Named([NS(name='Waist', select=False, hide=True), NS(name='Artist Bone', select=True, hide=False)])
        hidden = [True]
        rig = NS(data=NS(bones=bones), pose=NS(bones=poses), hide_get=lambda: hidden[0],
                 hide_set=lambda value: hidden.__setitem__(0, value))
        source = NS(modifiers=[NS(is_active=True), NS(is_active=False)])
        # Keep the artist controls and data separate from the disposable installation.
        metadata = {'record': {'controls': {'waist': 'Waist'}, 'physics':
                    {'backend': 'DIRECT_MAIN_CLOTH_V1'} if existing else None},
                    'profile': 'original profile', 'state': None, 'rotation_mute': False,
                    'influence': .35, 'artist_data': 'untouched', 'controls': ['Waist', 'Artist Bone']}
        before = copy.deepcopy(metadata)
        settings = NS(source='previous selected source')
        context = NS(active='artist active', mode='OBJECT', selected=['artist selection'])

        class Source(dict):
            pass
        chosen = Source(rig=rig); chosen.modifiers = source.modifiers

        def context_state(ctx):
            calls.append('capture context')
            return (ctx.active, ctx.mode, list(ctx.selected))

        def restore_context(ctx, saved):
            calls.append('restore context')
            ctx.active, ctx.mode, ctx.selected = saved

        def install(*args, **kwargs):
            calls.append('install')
            if install_error:
                raise ValueError('installation injection')
            if actual:
                metadata.update(record={'controls': {'waist': 'Waist'}, 'physics': {'backend': 'DIRECT_MAIN_CLOTH_V1'}},
                                profile='Direct profile', state='Direct state', rotation_mute=True, influence=0.)
                chosen.modifiers[0].is_active = False
                chosen.modifiers[1].is_active = True
            return metadata['record']

        def select(ctx, obj):
            calls.append('select')
            ctx.active, ctx.mode, ctx.selected = 'rig active', 'POSE', ['rig selection']
            for bone in poses:
                bone.select = bone.name == 'Waist'
            bones.active = control
            control.hide = poses['Waist'].hide = hidden[0] = False
            collection.is_visible = True
            if selection_error:
                raise RuntimeError('selection injection after mutation')

        def preflight(ctx, obj, arm, record):
            calls.append('preflight')
            self.assertIs(obj, chosen); self.assertIs(arm, rig)
            self.assertEqual(record['physics']['backend'], 'DIRECT_MAIN_CLOTH_V1')
            if rollback_error == 'preflight':
                raise ValueError('preflight injection')
            return before

        def commit(obj, plan):
            calls.append('commit')
            self.assertIs(obj, chosen)
            if rollback_error == 'commit':
                raise RuntimeError('commit injection')
            metadata.clear(); metadata.update(copy.deepcopy(plan))

        provider = NS(preflight_remove=preflight, commit_remove=commit)
        physics = NS(DIRECT_SURFACE_BACKEND='DIRECT_MAIN_CLOTH_V1',
                     backend=lambda row: row['physics']['backend'] if row.get('physics') else 'LEGACY_CAGE',
                     _surface_module=lambda **kwargs: provider)
        service = NS(RIG_KEY='rig', read_record=lambda obj: metadata['record'],
                     _context_state=context_state, _restore_context=restore_context,
                     select_controls=select,
                     remove_skirt=lambda *args: self.fail('Rollback must not remove artist Dress controls'))
        package = ModuleType('public_add_physics_test')
        tuning = ModuleType(package.__name__ + '.skirt_motion_tuning')
        tuning.initialize = lambda *args, **kwargs: calls.append('legacy initialize')
        package.skirt_motion_tuning = tuning
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        operator = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                        and node.name == 'CHARACTERDESIGNER_OT_skirt_add_physics')
        scope = {'__package__': package.__name__, 'Operator': object, 'BoolProperty': lambda **kwargs: None,
                 '_source': lambda ctx: chosen, '_settings': lambda ctx: settings, '_physics': lambda: physics,
                 '_rig': lambda: service, '_add_requested_physics': install,
                 '_report': lambda op, ctx, message, **kwargs: reports.append((message, kwargs))}
        exec(compile(ast.Module(body=[operator], type_ignores=[]), str(SOURCE), 'exec'), scope)
        instance = scope[operator.name](); instance.actual_surface = actual

        def execute():
            with patch.dict(sys.modules, {package.__name__: package, tuning.__name__: tuning}):
                return instance.execute(context)

        def state():
            return (metadata, settings.source, (context.active, context.mode, context.selected),
                    [(bone.name, bone.select) for bone in poses], bones.active.name,
                    hidden[0], control.hide, poses['Waist'].hide, collection.is_visible,
                    [modifier.is_active for modifier in chosen.modifiers])

        return NS(execute=execute, state=state, original=copy.deepcopy(state()), calls=calls,
                  reports=reports, metadata=metadata)

    def test_new_direct_selection_failure_restores_graph_author_context_and_ui(self):
        f = self.fixture()
        self.assertEqual(f.execute(), {'CANCELLED'})
        self.assertEqual(f.state(), f.original)
        self.assertEqual(f.calls, ['capture context', 'install', 'select', 'preflight', 'commit', 'restore context'])
        self.assertEqual(f.reports, [('selection injection after mutation', {'error': True})])

    def test_success_keeps_direct_and_selected_controls(self):
        f = self.fixture(selection_error=False)
        self.assertEqual(f.execute(), {'FINISHED'})
        self.assertEqual(f.metadata['record']['physics']['backend'], 'DIRECT_MAIN_CLOTH_V1')
        self.assertNotIn('preflight', f.calls)
        self.assertNotEqual(f.state(), f.original)

    def test_existing_direct_and_legacy_selection_failures_keep_previous_behavior(self):
        for kwargs in ({'existing': True}, {'actual': False}):
            with self.subTest(kwargs=kwargs):
                f = self.fixture(**kwargs)
                self.assertEqual(f.execute(), {'CANCELLED'})
                self.assertNotIn('capture context', f.calls)
                self.assertNotIn('preflight', f.calls)
                self.assertEqual('legacy initialize' in f.calls, kwargs.get('actual') is False)

    def test_removal_failure_reports_separately_and_still_restores_context(self):
        for failure in ('preflight', 'commit'):
            with self.subTest(failure=failure):
                f = self.fixture(rollback_error=failure)
                self.assertEqual(f.execute(), {'CANCELLED'})
                self.assertEqual(f.state()[1:], f.original[1:])
                self.assertEqual(f.reports[0], ('selection injection after mutation', {'error': True}))
                self.assertEqual(f.reports[1], ('Direct rollback needs recovery: Direct installation: '
                                              + failure + ' injection', {'error': True}))
                self.assertEqual(f.metadata['controls'], ['Waist', 'Artist Bone'])

    def test_native_install_failure_does_not_attempt_provider_removal(self):
        f = self.fixture(install_error=True)
        self.assertEqual(f.execute(), {'CANCELLED'})
        self.assertNotIn('select', f.calls)
        self.assertNotIn('preflight', f.calls)
        self.assertEqual(f.metadata, f.original[0])


if __name__ == '__main__':
    unittest.main()
