import unittest

from starter_kit.hardware.originq_hardware import (
    _safe_error,
    probabilities_to_counts,
    result_measurements,
)


class _ProbabilityOnlyResult:
    def get_counts(self):
        return {}

    def get_probs(self):
        return {"00": 0.48, "11": 0.52}


class OriginQHardwareEvidenceTests(unittest.TestCase):
    def test_probability_rounding_preserves_shots(self):
        counts = probabilities_to_counts({"00": 0.501, "11": 0.499}, 1000)
        self.assertEqual(counts, {"00": 501, "11": 499})
        self.assertEqual(sum(counts.values()), 1000)

    def test_largest_remainder_is_deterministic(self):
        counts = probabilities_to_counts({"00": 1, "01": 1, "10": 1}, 10)
        self.assertEqual(counts, {"00": 4, "01": 3, "10": 3})

    def test_existing_integer_counts_are_preserved(self):
        self.assertEqual(
            probabilities_to_counts({"00": 480, "01": 20, "11": 500}, 1000),
            {"00": 480, "01": 20, "11": 500},
        )

    def test_secret_is_redacted_from_provider_errors(self):
        message = _safe_error(RuntimeError("bad token secret-value"), "secret-value")
        self.assertNotIn("secret-value", message)
        self.assertIn("[redacted]", message)

    def test_empty_counts_fall_back_to_probabilities(self):
        self.assertEqual(
            result_measurements(_ProbabilityOnlyResult()),
            {"00": 0.48, "11": 0.52},
        )


if __name__ == "__main__":
    unittest.main()
