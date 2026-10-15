"""Serializer regression only; no bpy import or Blender process is required."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    '_inspect_live_hair_serializer_test', Path(__file__).with_name('inspect_live_hair.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class SequenceOnly:
    def __init__(self, values):
        self.values = tuple(values)

    def __len__(self):
        return len(self.values)

    def __getitem__(self, index):
        return self.values[index]


class Vector(SequenceOnly):
    pass


class Euler(SequenceOnly):
    def __init__(self, values, order='XYZ'):
        super().__init__(values)
        self.order = order


class Matrix(SequenceOnly):
    pass


class Quaternion(SequenceOnly):
    pass


class Color(SequenceOnly):
    pass


class IDPropertyArray:
    def __init__(self, values):
        self.values = values

    def to_list(self):
        return list(self.values)


class SerializerTests(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType('mathutils')
        for cls in (Vector, Euler, Matrix, Quaternion, Color):
            setattr(fake, cls.__name__, cls)
        self.modules = patch.dict(sys.modules, {'mathutils': fake})
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def test_five_mathutils_types_without_iter_are_serialized(self):
        cases = (Vector((1.0, -0.0, 3.0)), Euler((0.1, 0.2, 0.3), 'ZYX'),
                 Quaternion((1.0, 0.0, 0.0, 0.0)), Color((0.1, 0.5, 1.0)),
                 Matrix((Vector((1.0, 2.0, 3.0)), Vector((4.0, 5.0, 6.0)))))
        for value in cases:
            with self.subTest(kind=type(value).__name__):
                self.assertFalse(hasattr(value, '__iter__'))
                result = helper._plain(value)
                self.assertEqual(result['$mathutils'], type(value).__name__)
                self.assertEqual(len(helper._digest(value)), 64)
        self.assertEqual(helper._plain(cases[1])['order'], 'ZYX')
        matrix = helper._plain(cases[-1])
        self.assertEqual(matrix['dimensions'], [2, 3])
        self.assertEqual(matrix['rows'], helper._plain(((1.0, 2.0, 3.0), (4.0, 5.0, 6.0))))

    def test_id_property_array_without_iter_uses_to_list(self):
        value = IDPropertyArray((1, -0.0, 2.5))
        self.assertFalse(hasattr(value, '__iter__'))
        self.assertEqual(helper._plain(value), helper._plain([1, -0.0, 2.5]))

    def test_exact_components_and_euler_order_affect_hash(self):
        self.assertNotEqual(helper._digest(Vector((0.0,))), helper._digest(Vector((-0.0,))))
        self.assertNotEqual(helper._digest(Euler((0.0, 0.0, 0.0), 'XYZ')),
                            helper._digest(Euler((0.0, 0.0, 0.0), 'ZYX')))

    def test_other_sequence_only_types_are_still_refused(self):
        with self.assertRaisesRegex(TypeError, 'Unsupported protected-state value'):
            helper._plain(SequenceOnly((1.0, 2.0)))


if __name__ == '__main__':
    unittest.main()
