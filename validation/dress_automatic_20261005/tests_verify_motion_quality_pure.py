"""Re-run the 20 motion-quality checks plus two focused render selections.

Reads only two function definitions and their existing numerical constant from
the sibling QA script via AST. Synthetic scalar inputs test the diagnostic
decisions, not native bone motion, Cloth, artist assets, renders or visual
acceptance. No bpy import, registration, child process or filesystem mutation.

Run with ordinary Python 3.12: python tests_verify_motion_quality_pure.py
"""

import ast
import math
from pathlib import Path
from types import SimpleNamespace
import unittest


SOURCE = Path(__file__).with_name("verify_actual_surface_workflow.py")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def motion_check(result, _qa, name, condition, **facts):
    require(condition, name)
    result.setdefault("checks", []).append({"name": name, "passed": condition, **facts})


def runtime():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    names = {"motion_quality_summary", "native_input_summary"}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    require({node.name for node in functions} == names and len(functions) == len(names),
            "The focused QA function inventory changed")
    guard = next(ast.literal_eval(node.value) for node in tree.body
                 if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                                                        and target.id == "NATIVE_WORLD_LIMIT" for target in node.targets))
    namespace = {"math": math, "require": require, "motion_check": motion_check, "NATIVE_WORLD_LIMIT": guard}
    # Do not execute the QA module's imports, Blender functions or entry point.
    focused = ast.Module(body=functions, type_ignores=[])
    exec(compile(focused, str(SOURCE), "exec"), namespace)
    return namespace


class MotionQualityPureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.namespace = runtime()

    def setUp(self):
        self.args = SimpleNamespace(max_edge_ratio=3., max_stop_jitter_mm=1., max_penetration_mm=2.)
        self.measurements = [{
            "frame": frame, "final_max_edge_ratio_to_frame1": 1.1,
            "final_edge_connectivity_exact": True, "final_positive_reference_edges": 9,
            "final_hem_identity_complete": True, "final_free_hem_vertices": 5,
            "final_hem_waist_step_max_m": .0005 if frame > 1 else None,
            "final_hem_waist_from_frame1_max_m": .01, "synthetic_input_stopped": frame >= 34,
            "native_knee_motion_without_root_m": {"L": .1, "R": .1},
            "native_body_rig_frame_motion_m": .1, "native_rig_translation_m": .2,
            "native_waist_translation_m": .2, "native_rig_rotation_rad": math.radians(100),
            "native_waist_rotation_rad": math.radians(100),
        } for frame in range(1, 61)]
        self.samples = []
        for frame in (1, 7, 25, 30, 40, 60):
            self.samples.append({
                "frame": frame, "final_weight_layer_complete": True,
                "body_weight_layer_complete": True, "final_free_vertices": 15,
                "final_body": {"status": "measured", "coplanar_unresolved_count": 0,
                               "degenerate_unresolved_count": 0, "boundary_unresolved_count": 0},
                "final_body_contact_classification": {
                    "baseline_coverage_complete": True,
                    "counts": {name: 0 for name in ("moving_free_leg_crossings", "moving_free_other_body_crossings",
                        "baseline_or_stationary_free_contacts", "baseline_unproven_free_contacts", "waist_transition_contacts")}},
                "old3": [{"object": role, "role": role, "final_free_vertices": {
                    "sampled_vertices": 15, "maximum_penetration_m": 0., "minimum_signed_distance_m": .001}}
                    for role in ("leg.L", "leg.R", "pelvis_or_other")],
            })
        self.qa = SimpleNamespace(representative_values=lambda *_: (None, math.radians(100), None))

    def quality(self, samples=None):
        result = {}
        render = self.namespace["motion_quality_summary"](
            "abrupt_stop", self.args, self.measurements, self.samples if samples is None else samples, 40, result)
        return result, render

    def native(self, case):
        result = {}
        self.namespace["native_input_summary"](case, self.args, self.measurements, 1., 1., result, self.qa)
        return result

    def assert_unproven(self, result):
        self.assertEqual(result["effect_quality"]["status"], "UNPROVEN")
        self.assertFalse(result["effect_quality"]["bounded_diagnostics_passed"])

    def assert_rejected(self, result):
        self.assertEqual(result["effect_quality"]["status"], "REJECTED_BY_BOUNDED_DIAGNOSTIC")
        self.assertFalse(result["effect_quality"]["bounded_diagnostics_passed"])

    def test_01_bounded_pass_keeps_visual_and_whole_body_unproven(self):
        result, render = self.quality()
        self.assertTrue(result["effect_quality"]["bounded_diagnostics_passed"])
        self.assertIsNone(result["collision_acceptance"])
        self.assertEqual(result["effect_quality"]["visual_acceptance"], "PENDING_HUMAN_REVIEW")
        self.assertEqual(result["effect_quality"]["whole_body_separation_acceptance"], "UNPROVEN")
        self.assertEqual(render["frame"], 40)

    def test_02_14mm_rejected_by_2mm_metre_limit_and_selects_worst_frame(self):
        metric = self.samples[2]["old3"][0]["final_free_vertices"]
        metric["maximum_penetration_m"] = .002
        self.assertTrue(self.quality()[0]["effect_quality"]["bounded_diagnostics_passed"])
        metric["maximum_penetration_m"] = .014
        result, render = self.quality()
        self.assert_rejected(result)
        self.assertIs(result["collision_acceptance"], False)
        self.assertEqual(result["signed_final_collider_summary"]["diagnostic_limit_m"], .002)
        self.assertEqual(render["frame"], 25)

    def test_03_empty_signed_vertex_samples_are_unproven(self):
        for sample in self.samples:
            for collider in sample["old3"]:
                collider["final_free_vertices"]["sampled_vertices"] = 0
        self.assert_unproven(self.quality()[0])

    def test_04_exhausted_triangle_budget_is_unproven(self):
        self.samples[1]["final_body"]["status"] = "skipped_candidate_limit"
        self.assert_unproven(self.quality()[0])

    def test_05_missing_crossing_field_is_not_default_zero_pass(self):
        del self.samples[1]["final_body"]["boundary_unresolved_count"]
        self.assert_unproven(self.quality()[0])

    def test_06_moving_free_leg_crossing_rejects_and_selects_crossing_frame(self):
        self.samples[3]["final_body_contact_classification"]["counts"]["moving_free_leg_crossings"] = 2
        result, render = self.quality()
        self.assert_rejected(result)
        self.assertEqual(render["frame"], 30)

    def test_07_fixed_waist_transition_contact_is_not_dynamic_failure(self):
        self.samples[0]["final_body_contact_classification"]["counts"]["waist_transition_contacts"] = 4
        self.assertTrue(self.quality()[0]["effect_quality"]["bounded_diagnostics_passed"])

    def test_08_existing_free_contact_remains_unproven(self):
        self.samples[0]["final_body_contact_classification"]["counts"]["baseline_or_stationary_free_contacts"] = 2
        self.assert_unproven(self.quality()[0])

    def test_09_unmeasured_baseline_is_unproven(self):
        self.samples[0]["final_body_contact_classification"]["baseline_coverage_complete"] = False
        self.assert_unproven(self.quality()[0])

    def test_10_final_hem_tail_1p2mm_rejected_by_1mm_per_frame(self):
        self.measurements[-1]["final_hem_waist_step_max_m"] = .001
        self.assertTrue(self.quality()[0]["effect_quality"]["bounded_diagnostics_passed"])
        self.measurements[-1]["final_hem_waist_step_max_m"] = .0012
        self.assert_rejected(self.quality()[0])

    def test_11_incomplete_final_hem_is_unproven(self):
        self.measurements[-1]["final_hem_identity_complete"] = False
        self.measurements[-1]["final_hem_waist_step_max_m"] = None
        self.assert_unproven(self.quality()[0])

    def test_12_final_edge_ratio_3p1_rejected_by_old_limit_3(self):
        self.measurements[-1]["final_max_edge_ratio_to_frame1"] = 3.
        self.assertTrue(self.quality()[0]["effect_quality"]["bounded_diagnostics_passed"])
        self.measurements[-1]["final_max_edge_ratio_to_frame1"] = 3.1
        self.assert_rejected(self.quality()[0])

    def test_13_missing_collision_samples_are_unproven(self):
        self.assert_unproven(self.quality(samples=[])[0])

    def test_14_evaluated_leg_body_and_root_inputs_pass(self):
        self.assertEqual(len(self.native("walk")["checks"]), 3)

    def test_15_unmoving_evaluated_knees_are_rejected(self):
        for measurement in self.measurements:
            measurement["native_knee_motion_without_root_m"] = {"L": 0., "R": 0.}
        with self.assertRaisesRegex(RuntimeError, "representative_native_leg_inputs_reach_evaluated_bones"):
            self.native("walk")

    def test_16_stationary_turn_uses_evaluated_rotation(self):
        for measurement in self.measurements:
            measurement["native_rig_translation_m"] = measurement["native_waist_translation_m"] = 0.
        self.assertEqual(len(self.native("turn")["checks"]), 1)

    def test_17_incomplete_final_weight_layer_is_unproven(self):
        self.samples[0]["final_weight_layer_complete"] = False
        self.assert_unproven(self.quality()[0])

    def test_18_no_positive_reference_edges_is_unproven(self):
        for measurement in self.measurements:
            measurement["final_positive_reference_edges"] = 0
        self.assert_unproven(self.quality()[0])

    def test_19_unmoving_actual_body_skin_is_rejected(self):
        for measurement in self.measurements:
            measurement["native_body_rig_frame_motion_m"] = 0.
        with self.assertRaisesRegex(RuntimeError, "representative_native_leg_input_reaches_actual_body_skin"):
            self.native("walk")

    def test_20_turn_without_evaluated_angular_response_is_rejected(self):
        for measurement in self.measurements:
            measurement["native_rig_rotation_rad"] = measurement["native_waist_rotation_rad"] = 0.
        with self.assertRaisesRegex(RuntimeError, "representative_turn_reaches_evaluated_rig_and_waist_rotation"):
            self.native("turn")

    def test_21_edge_failure_selects_worst_final_surface_frame(self):
        self.measurements[-1]["final_max_edge_ratio_to_frame1"] = 3.1
        result, render = self.quality()
        self.assert_rejected(result)
        self.assertEqual(render["frame"], 60)
        self.assertEqual(result["effect_quality"]["visual_acceptance"], "PENDING_HUMAN_REVIEW")

    def test_22_stop_hem_failure_selects_worst_step_without_visual_pass(self):
        self.measurements[-1]["final_hem_waist_step_max_m"] = .0012
        result, render = self.quality()
        self.assert_rejected(result)
        self.assertEqual(render["frame"], 60)
        self.assertEqual(result["effect_quality"]["long_run_settling_acceptance"], "UNPROVEN")
        self.assertEqual(result["effect_quality"]["visual_acceptance"], "PENDING_HUMAN_REVIEW")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MotionQualityPureTests)
    outcome = unittest.TextTestRunner(verbosity=1).run(suite)
    print(f"Focused motion quality pure: {outcome.testsRun} tests, failures={len(outcome.failures)}, errors={len(outcome.errors)}")
    raise SystemExit(0 if outcome.wasSuccessful() else 1)
