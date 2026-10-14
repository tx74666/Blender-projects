"""Portable tests of the narrow diagnostic-bound qualification; no Blender import."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('linear_qualification', ROOT / 'original20_linear_redo_qualification.py')
q = importlib.util.module_from_spec(spec); spec.loader.exec_module(q)
EVIDENCE = ROOT / 'action_undo_diagnostic_07734_01'


class QualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = json.loads((EVIDENCE / 'before_curve_undo_full20_payload.json').read_text(encoding='utf-8'))
        cls.after = json.loads((EVIDENCE / 'after_curve_redo_full20_payload.json').read_text(encoding='utf-8'))

    def qualify(self, before, after):
        return q.qualify_redo(before, after, self.before, self.after)

    def changed(self, mutate):
        value = copy.deepcopy(self.after); mutate(value)
        with self.assertRaises((ValueError, KeyError, TypeError)): self.qualify(self.before, value)

    @staticmethod
    def curves(value): return value['layers'][0]['strips'][0]['curves']

    def test_actual_exact_observed_rewrite(self):
        result = self.qualify(self.before, self.after)
        self.assertEqual(result['difference_count'], 200)
        self.assertFalse(result['whole_payload_exact'])

    def test_exact_payload_allowed(self):
        self.assertTrue(self.qualify(self.before, self.before)['whole_payload_exact'])

    def test_non_linear_rejected(self):
        self.changed(lambda v: self.curves(v)[0]['keyframe_points'][0].update(interpolation='BEZIER'))

    def test_equal_non_linear_rejected(self):
        value = copy.deepcopy(self.before); self.curves(value)[0]['keyframe_points'][0]['interpolation'] = 'BEZIER'
        with self.assertRaises(ValueError): self.qualify(value, value)

    def test_unproved_curve_domain_rejected(self):
        for field, changed in (('mute', True), ('extrapolation', 'LINEAR')):
            value = copy.deepcopy(self.before); self.curves(value)[0][field] = changed
            with self.assertRaises(ValueError): self.qualify(value, value)

    def test_type_and_signed_zero_changes_rejected(self):
        for changed in (0, -0.0):
            before = copy.deepcopy(self.before)
            after = copy.deepcopy(self.after)
            before['settings']['custom_probe'] = 0.0
            after['settings']['custom_probe'] = changed
            with self.assertRaises(ValueError): self.qualify(before, after)

    def test_two_ulp_rejected(self):
        def mutate(value):
            key = self.curves(value)[0]['keyframe_points'][0]
            bits = q.float32_bits(key['handle_right'][0]); key['handle_right'][0] = struct.unpack('<f', struct.pack('<I', bits + 1))[0]
        self.changed(mutate)

    def test_handle_y_rejected(self):
        self.changed(lambda v: self.curves(v)[0]['keyframe_points'][0]['handle_right'].__setitem__(1, 0.5))

    def test_key_co_rejected(self):
        self.changed(lambda v: self.curves(v)[0]['keyframe_points'][0]['co'].__setitem__(1, 0.5))

    def test_unknown_key_position_rejected(self):
        self.changed(lambda v: self.curves(v)[0]['keyframe_points'][4]['handle_right'].__setitem__(0, 5.5))

    def test_curve_order_rejected(self):
        self.changed(lambda v: self.curves(v).reverse())

    def test_other_key_setting_rejected(self):
        self.changed(lambda v: self.curves(v)[0]['keyframe_points'][0].update(easing='EASE_IN'))

    def test_action_setting_rejected(self):
        self.changed(lambda v: v['settings'].update(use_frame_range=not v['settings']['use_frame_range']))

    def test_missing_transition_rejected(self):
        x = self.curves(self.before)[0]['keyframe_points'][0]['handle_right'][0]
        self.changed(lambda v: self.curves(v)[0]['keyframe_points'][0]['handle_right'].__setitem__(0, x))

    def test_reverse_transition_rejected(self):
        with self.assertRaises(ValueError): self.qualify(self.after, self.before)


if __name__ == '__main__': unittest.main()
