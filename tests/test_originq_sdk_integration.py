import math
import os
import unittest

from starter_kit import adapter
from starter_kit.loomq_l1.frontend import parse_qasm2
from starter_kit.loomq_l1.semantics import exact_distribution


RUN_SDK_TESTS = os.environ.get("LOOMQ_RUN_SDK_TESTS") == "1"
HEADER = 'OPENQASM 2.0;\ninclude "qelib1.inc";\n'


def hellinger_fidelity(observed, expected):
    states = set(observed) | set(expected)
    distance = math.sqrt(
        sum(
            (math.sqrt(observed.get(state, 0.0)) - math.sqrt(expected.get(state, 0.0))) ** 2
            for state in states
        )
    ) / math.sqrt(2.0)
    return 1.0 - distance


@unittest.skipUnless(RUN_SDK_TESTS, "set LOOMQ_RUN_SDK_TESTS=1 to run pyQPanda")
class OriginQSDKIntegrationTests(unittest.TestCase):
    def test_partial_measurement_preserves_classical_destination(self):
        source = HEADER + """qreg q[2];
creg c[2];
x q[0];
measure q[0] -> c[1];
"""
        result = adapter.run(source, "originq", 128)
        self.assertEqual(result["counts"], {"10": 128})

    def test_complete_gate_matrix_matches_reference_semantics(self):
        source = HEADER + """qreg q[3];
creg c[3];
h q[0];
x q[1];
s q[0];
sdg q[0];
t q[1];
tdg q[1];
rz(pi/7) q[0];
ry(-pi/3) q[1];
cx q[0],q[1];
cu1(pi/5) q[0],q[1];
swap q[1],q[2];
ccx q[0],q[1],q[2];
measure q -> c;
"""
        expected = exact_distribution(parse_qasm2(source))
        shots = 4096
        result = adapter.run(source, "originq", shots)
        observed = {key: value / shots for key, value in result["counts"].items()}
        self.assertGreaterEqual(hellinger_fidelity(observed, expected), 0.97)


if __name__ == "__main__":
    unittest.main()
