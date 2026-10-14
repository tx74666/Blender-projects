"""Actual UI dispatch and refusal guards; substitutes do not prove native Rigging."""

from contextlib import ExitStack
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


_helper_spec = importlib.util.spec_from_file_location(
    '_prepared_rigging_ui_helpers', Path(__file__).with_name('test_animation_worklist_ui.py'))
_helpers = importlib.util.module_from_spec(_helper_spec)
_helper_spec.loader.exec_module(_helpers)


class PreparedRiggingUI(unittest.TestCase):
    def setUp(self):
        # Reuse the existing fake Blender bootstrap, then execute the complete
        # canonical UI module. No native module or backend is imported here.
        _helpers.WorklistUI.setUp(self)
        self.main = SimpleNamespace(name='CoshaRig', type='ARMATURE', library=None,
            animation_data=SimpleNamespace(action=None),
            get=Mock(side_effect=lambda key: 'owned snapshot' if
                key == 'character_designer_worklist_main_session_v1' else
                'sealed rigging session' if key == 'character_designer_rigging_session_v1' else None))
        self.context.scene.character_designer_setup = SimpleNamespace(rig=self.main)
        self.context.scene.objects = {self.main.name: self.main}
        self.state.rig = self.main
        self.context.window_manager.fileselect_add = Mock()
        self.backend.attach_prepared_rigging_work = Mock()
        self.backend.validate_rigging_entry = Mock()
        self.backend.adopt_main_rig = Mock()
        for item in self.state.items:
            item.rig = self.main
        self.item = self.state.items[0]
        self.item.custom_action = SimpleNamespace(name='Walk Custom')
        self.item.source_action = SimpleNamespace(name='Walk Source')
        self.main.animation_data.action = self.item.custom_action
        self.session = dict(rig=self.main, scene=self.context.scene,
            base_action=self.item.custom_action, base_slot=4,
            input_action=SimpleNamespace(name='Walk Controls'), input_slot=7,
            work_item_id='prepared-work-id', source_packet_sha256='a' * 64,
            source_read_only=False, enabled=True, edit_role='RIGGING')
        self.native = ModuleType(self.ui.__package__ + '.unity_animation_rigging')
        self.native.current = Mock(return_value=self.session)
        self.native.display_state = Mock(return_value=None)
        self.native.activate, self.native.key_current = Mock(), Mock()
        # Composition owns a separate session/ID fixture. Isolate its sibling
        # renderer while retaining the actual Worklist drawing and guards.
        composition = ModuleType(self.ui.__package__ + '.animation_composition_ui')
        composition.draw_composition = Mock()
        modules = patch.dict(sys.modules, {self.native.__name__: self.native,
                                          composition.__name__: composition})
        modules.start()
        self.addCleanup(modules.stop)
        setattr(sys.modules[self.ui.__package__], 'unity_animation_rigging', self.native)
        # Prime Worklist drawing before measuring poll/draw data-file I/O.
        self.ui.draw_worklist(_helpers.Layout(), self.context)

    def attach_operator(self, path='D:/Prepared/Cosha.workspace.json'):
        operator = self.ui.CHARACTERDESIGNER_OT_worklist_add_prepared_animation()
        operator.filepath = path
        return operator

    def cached_state(self):
        return (self.state.workspace_path, tuple(self.state.catalog), tuple(self.state.items),
                self.state.rig, self.state.active_index)

    def no_file_access(self):
        stack = ExitStack()
        for method in ('open', 'read_text', 'read_bytes', 'stat', 'exists', 'is_file', 'is_dir'):
            stack.enter_context(patch.object(Path, method,
                side_effect=AssertionError('UI attempted disk I/O: ' + method)))
        stack.enter_context(patch('builtins.open', side_effect=AssertionError('UI attempted open')))
        return stack

    def test_only_cached_same_adopted_main_rig_is_eligible(self):
        self.assertTrue(self.attach_operator().poll(self.context))
        cases = (
            ('missing rig', None, self.main, 'owned snapshot'),
            ('different Main Rig', self.main, SimpleNamespace(), 'owned snapshot'),
            ('missing Main Rig', self.main, None, 'owned snapshot'),
            ('restored or unadopted', self.main, self.main, None),
        )
        for label, rig, main, record in cases:
            with self.subTest(label=label):
                self.state.rig = rig
                self.context.scene.character_designer_setup.rig = main
                self.main.get.side_effect = None
                self.main.get.return_value = record
                self.assertFalse(self.attach_operator().poll(self.context))
                layout = _helpers.Layout()
                self.ui.draw_worklist(layout, self.context)
                self.assertNotIn(self.attach_operator().bl_idname,
                    [value[0] for kind, value, _ in layout.records if kind == 'operator'])
        self.backend.attach_prepared_rigging_work.assert_not_called()
        self.backend.validate_rigging_entry.assert_not_called()

        self.state.rig = self.context.scene.character_designer_setup.rig = self.main
        self.main.get.return_value = 'owned snapshot'
        self.context.scene.objects.clear()
        self.assertFalse(self.attach_operator().poll(self.context))
        self.context.scene.objects[self.main.name] = self.main
        self.main.library = object()
        self.assertFalse(self.attach_operator().poll(self.context))

    def test_poll_and_draw_have_no_file_access_or_backend_authentication(self):
        before = self.cached_state()
        with self.no_file_access():
            self.assertTrue(self.attach_operator().poll(self.context))
            layout = _helpers.Layout()
            self.ui.draw_worklist(layout, self.context)
        buttons = [value[0] for kind, value, _ in layout.records if kind == 'operator']
        self.assertEqual(buttons.count(self.attach_operator().bl_idname), 1)
        self.assertIn('character_designer.worklist_add_ready', buttons)
        self.assertIn('character_designer.worklist_sync_changed', buttons)
        self.assertIn(self.ui.CHARACTERDESIGNER_OT_worklist_add_prepared_animation,
                      self.ui.WORKLIST_CLASSES)
        self.backend.attach_prepared_rigging_work.assert_not_called()
        self.backend.validate_rigging_entry.assert_not_called()
        self.assertEqual(self.cached_state(), before)

    def test_busy_owning_context_disables_entry_without_reading_files(self):
        self.animation._link_idle.return_value = False
        with self.no_file_access():
            self.assertFalse(self.attach_operator().poll(self.context))
            layout = _helpers.Layout()
            self.ui.draw_worklist(layout, self.context)
        button = [(value, enabled) for kind, value, enabled in layout.records
                  if kind == 'operator' and value[0] == self.attach_operator().bl_idname]
        self.assertEqual(len(button), 1)
        self.assertFalse(button[0][1])
        self.backend.attach_prepared_rigging_work.assert_not_called()

    def test_file_selector_preserves_explicit_path_without_guessing_workspace(self):
        for path in ('', 'D:/NewPrepare/character_animation_workspace.json',
                     'D:/Animations/Cosha.workspace.json'):
            with self.subTest(path=path), self.no_file_access():
                operator = self.attach_operator(path)
                self.assertEqual(operator.invoke(self.context, None), {'RUNNING_MODAL'})
                self.assertEqual(operator.filepath, path)
                self.context.window_manager.fileselect_add.assert_called_with(operator)
        self.backend.attach_prepared_rigging_work.assert_not_called()
        self.backend.connect.assert_not_called()

    def test_execute_dispatches_exact_file_with_omitted_work_id_and_keeps_cached_old_rows(self):
        # Backend transaction/admission has its own tests. This verifies the UI
        # neither selects a row from the old catalog nor swaps cached ownership.
        self.state.items.extend(SimpleNamespace(item_id='old-' + str(i)) for i in range(6))
        self.assertEqual(len(self.state.items), 9)
        before = self.cached_state()
        for path in ('D:/NewPrepare/character_animation_workspace.json',
                     'D:/Animations/Cosha.workspace.json'):
            with self.subTest(path=path):
                operator = self.attach_operator(path)
                self.assertEqual(operator.execute(self.context), {'FINISHED'})
                self.backend.attach_prepared_rigging_work.assert_called_with(self.context, path)
                self.assertEqual(self.cached_state(), before)
        for method in ('connect', 'refresh', 'adopt_main_rig', 'add', 'activate', 'remove'):
            getattr(self.backend, method).assert_not_called()

    def test_direct_execute_rechecks_same_main_rig_and_idle_before_backend(self):
        for stale_rig, idle in ((None, True), (self.main, False)):
            with self.subTest(stale_rig=stale_rig, idle=idle):
                self.state.rig = stale_rig
                self.animation._link_idle.return_value = idle
                operator = self.attach_operator()
                self.assertEqual(operator.execute(self.context), {'CANCELLED'})
                self.assertTrue(self.state.has_error)
                self.assertIn('same adopted Main Rig', self.state.status)
        self.backend.attach_prepared_rigging_work.assert_not_called()

    def test_backend_ordinary_ambiguous_and_stale_refusals_retain_feedback_and_old_ownership(self):
        before = self.cached_state()
        for message in ('Choose a workspace JSON containing prepared Rigging work.',
                        'Expected exactly one request-matched prepared Rigging work item.',
                        'The prepared packet or Link changed after Prepare.'):
            with self.subTest(message=message):
                self.backend.attach_prepared_rigging_work.side_effect = ValueError(message)
                operator = self.attach_operator()
                self.assertEqual(operator.execute(self.context), {'CANCELLED'})
                self.assertEqual(self.state.status, message)
                self.assertTrue(self.state.has_error)
                self.assertEqual(operator.last_report, ({'ERROR'}, message))
                self.assertEqual(self.cached_state(), before)
        self.backend.connect.assert_not_called()
        self.backend.adopt_main_rig.assert_not_called()

    def assert_rigging_order(self, role):
        events = []
        self.backend.validate_rigging_entry.side_effect = lambda *args: events.append(('validate', args))
        self.native.activate.side_effect = lambda *args, **kwargs: events.append(('activate', args, kwargs))
        self.native.key_current.side_effect = lambda *args: events.append(('key', args))
        if role is None:
            operator = self.ui.CHARACTERDESIGNER_OT_worklist_save_controls()
        else:
            operator = self.ui.CHARACTERDESIGNER_OT_worklist_rigging_edit()
            operator.edit_role = role
        operator.item_id = self.item.item_id
        self.assertEqual(operator.execute(self.context), {'FINISHED'})
        self.assertEqual(events[0], ('validate', (self.context, self.item, self.session)))
        if role is None:
            self.assertEqual(events[1], ('key', (self.context, self.session)))
            self.native.activate.assert_not_called()
        else:
            self.assertEqual(events[1], ('activate', (self.context, self.session),
                                        {'edit_role': role, 'enabled': True}))
            self.native.key_current.assert_not_called()
        self.assertEqual(len(events), 2)
        self.assertFalse(self.state.has_error)

    def test_edit_base_reauthenticates_before_activation(self):
        self.assert_rigging_order('BASE')

    def test_edit_controls_reauthenticates_before_activation(self):
        self.assert_rigging_order('RIGGING')

    def test_save_controls_reauthenticates_before_keying(self):
        self.assert_rigging_order(None)

    def test_reacquired_row_wrapper_is_passed_to_backend_by_current_stable_item_id(self):
        # RNA collection access can return a fresh Python row wrapper. The
        # backend owns native pointer/WorkID validation; UI must pass the current
        # wrapper rather than bind editing to an earlier Python row instance.
        current_row = SimpleNamespace(**vars(self.item), as_pointer=lambda: 1234)
        self.state.items[0] = current_row
        self.assertIsNot(current_row, self.item)
        operator = self.ui.CHARACTERDESIGNER_OT_worklist_save_controls()
        operator.item_id = self.item.item_id
        self.assertEqual(operator.execute(self.context), {'FINISHED'})
        self.backend.validate_rigging_entry.assert_called_once_with(
            self.context, current_row, self.session)
        self.native.key_current.assert_called_once_with(self.context, self.session)

    def test_stale_link_packet_capture_slot_or_work_id_refusal_prevents_mutation(self):
        for message in ('Link belongs to another target.', 'The full packet hash changed.',
                        'Custom capture differs from the prepared packet.',
                        'Base or Custom slot changed.', 'Session WorkID differs from the row.'):
            for role in ('BASE', 'RIGGING', None):
                with self.subTest(message=message, role=role):
                    self.backend.validate_rigging_entry.side_effect = ValueError(message)
                    operator = (self.ui.CHARACTERDESIGNER_OT_worklist_save_controls()
                                if role is None else self.ui.CHARACTERDESIGNER_OT_worklist_rigging_edit())
                    operator.item_id = self.item.item_id
                    operator.edit_role = role
                    self.assertEqual(operator.execute(self.context), {'CANCELLED'})
                    self.assertEqual(operator.last_report, ({'ERROR'}, message))
                    self.assertEqual(self.state.status, message)
                    self.assertTrue(self.state.has_error)
        self.native.activate.assert_not_called()
        self.native.key_current.assert_not_called()

    def test_source_foreign_session_and_stale_selection_fail_before_reauthentication(self):
        operator = self.ui.CHARACTERDESIGNER_OT_worklist_save_controls()
        operator.item_id = self.item.item_id
        cases = (
            dict(side='SOURCE'),
            dict(item_id='other-row'),
            dict(source_read_only=True),
            dict(scene=SimpleNamespace()),
            dict(base_action=SimpleNamespace(name='Other Custom')),
        )
        for changes in cases:
            with self.subTest(changes=changes):
                original_item = self.item.side, operator.item_id
                original_session = self.session.copy()
                self.item.side = changes.get('side', self.item.side)
                operator.item_id = changes.get('item_id', operator.item_id)
                self.session.update({key: value for key, value in changes.items()
                                     if key not in {'side', 'item_id'}})
                self.assertEqual(operator.execute(self.context), {'CANCELLED'})
                self.item.side, operator.item_id = original_item
                self.session.clear()
                self.session.update(original_session)
        self.backend.validate_rigging_entry.assert_not_called()
        self.native.activate.assert_not_called()
        self.native.key_current.assert_not_called()

    def test_edit_and_save_poll_use_only_cached_display(self):
        self.native.display_state.return_value = self.session
        with self.no_file_access():
            self.assertTrue(self.ui.CHARACTERDESIGNER_OT_worklist_rigging_edit.poll(self.context))
            self.assertTrue(self.ui.CHARACTERDESIGNER_OT_worklist_save_controls.poll(self.context))
        self.backend.validate_rigging_entry.assert_not_called()
        self.native.current.assert_not_called()


if __name__ == '__main__':
    unittest.main()
