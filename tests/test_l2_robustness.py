import unittest

from starter_kit.loomq_l2.qasm import synthesize_target_state_qasm
from starter_kit.loomq_l2.robustness_eval import (
    ALL_CASES,
    BACKEND_CASES,
    GENERATION_CASES,
    REPAIR_CASES,
    grade_answer,
    regrade_report,
)


class Level2RobustnessPackTests(unittest.TestCase):
    def test_pack_has_36_unique_cases_balanced_across_three_categories(self):
        self.assertEqual(len(ALL_CASES), 36)
        self.assertEqual(len(GENERATION_CASES), 12)
        self.assertEqual(len(REPAIR_CASES), 12)
        self.assertEqual(len(BACKEND_CASES), 12)
        self.assertEqual(len({case.name for case in ALL_CASES}), 36)

    def test_every_qasm_case_accepts_a_synthesized_target(self):
        for case in GENERATION_CASES + REPAIR_CASES:
            with self.subTest(case=case.name):
                answer = synthesize_target_state_qasm(case.target_state)
                passed, detail = grade_answer(case, answer)
                self.assertTrue(passed, detail)

    def test_backend_grader_accepts_deterministic_expected_answer(self):
        from starter_kit.loomq_l2.backend import format_recommendation

        for case in BACKEND_CASES:
            with self.subTest(case=case.name):
                answer = format_recommendation(case.backend_constraints)
                passed, detail = grade_answer(case, answer)
                self.assertTrue(passed, detail)

    def test_saved_answers_can_be_regraded_without_model_calls(self):
        results = []
        for case in ALL_CASES:
            if case.category == "backend":
                from starter_kit.loomq_l2.backend import format_recommendation

                answer = format_recommendation(case.backend_constraints)
            else:
                answer = synthesize_target_state_qasm(case.target_state)
            results.append({"name": case.name, "status": "FAIL", "answer": answer})
        report = regrade_report({"results": results})
        self.assertEqual(report["passed"], 36)
        self.assertEqual(report["pass_rate"], 1.0)
        self.assertIn("no model answers were changed", report["grading_revision"])


if __name__ == "__main__":
    unittest.main()
