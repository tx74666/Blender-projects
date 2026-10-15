"""Thin fixed-factory proofs only; Blender is never loaded."""
import dis
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import native_unset_cycles_copy_fixture_011 as fixture


class Tests(unittest.TestCase):
    def test_private_factory_code_is_exact010_with_only_owned_stage_bindings(self):
        function = fixture.private_main()
        self.assertIs(function.__code__, fixture.original.main.__code__)
        self.assertIsNot(function.__globals__, fixture.original.main.__globals__)
        for key in ('STAGE', 'SCENE_SHA', 'MANIFEST_SHA'):
            self.assertEqual(function.__globals__[key], getattr(fixture, key))
            self.assertNotEqual(function.__globals__[key], getattr(fixture.original, key))
        self.assertEqual(function.__globals__['__file__'], str(fixture.Path(fixture.__file__).resolve()))
        self.assertEqual(fixture.original.STAGE.name, 'staged_20261015_09')

    def test_fixed_success_requires_all_native_flags_and_honest_stage10_cleanup_label(self):
        def factory(args, report):
            report.update(**dict.fromkeys(fixture.FLAGS, True), reproduced_remapper_materialization=False,
                cleanup={'errors': [], 'stage09_unchanged': True})
        with patch.object(fixture, '_factory', side_effect=factory):
            report = {}
            fixture.main(None, report)
        self.assertEqual(report['schema'], fixture.SCHEMA)
        self.assertTrue(report['fixed_stage10_preserves_unset_pg'])
        self.assertTrue(report['cleanup']['stage10_unchanged'])
        self.assertNotIn('stage09_unchanged', report['cleanup'])

    def test_each_missing_native_proof_or_materialization_is_rejected(self):
        for key in fixture.FLAGS + ('reproduced_remapper_materialization',):
            def factory(args, report):
                report.update(**dict.fromkeys(fixture.FLAGS, True), reproduced_remapper_materialization=False,
                    cleanup={'errors': [], 'stage09_unchanged': True})
                report[key] = key == 'reproduced_remapper_materialization'
            with self.subTest(key=key), patch.object(fixture, '_factory', side_effect=factory):
                with self.assertRaisesRegex(RuntimeError, 'did not preserve'):
                    fixture.main(None, {})

    def test_original_exception_not_overwritten_or_retried(self):
        failure = ValueError('original native failure')
        with patch.object(fixture, '_factory', side_effect=failure) as called:
            with self.assertRaisesRegex(ValueError, 'original native failure'):
                fixture.main(None, {})
        called.assert_called_once()


if __name__ == '__main__':
    unittest.main()
