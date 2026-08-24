import math
import os
import random
import unittest

from starter_kit import adapter
from starter_kit.loomq_l1.frontend import parse_qasm2
from starter_kit.loomq_l1.semantics import exact_distribution


RUN_SDK_TESTS = os.environ.get("LOOMQ_RUN_SDK_TESTS") == "1"
TARGETS = tuple(
    target.strip()
    for target in os.environ.get("LOOMQ_SDK_TARGETS", "spinq,originq,braket").split(",")
    if target.strip()
)
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


@unittest.skipUnless(RUN_SDK_TESTS, "set LOOMQ_RUN_SDK_TESTS=1 to run real SDKs")
class L1SDKIntegrationTests(unittest.TestCase):
    def test_partial_measurement_preserves_classical_destination(self):
        source = HEADER + '''qreg q[2];
creg c[2];
x q[0];
measure q[0] -> c[1];
'''
        for target in TARGETS:
            with self.subTest(target=target):
                result = adapter.run(source, target, 128)
                self.assertEqual(result["counts"], {"10": 128})

    def test_complete_gate_matrix_matches_reference_semantics(self):
        source = HEADER + '''qreg q[3];
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
'''
        expected = exact_distribution(parse_qasm2(source))
        for target in TARGETS:
            with self.subTest(target=target):
                shots = 4096
                result = adapter.run(source, target, shots)
                observed = {key: value / shots for key, value in result["counts"].items()}
                self.assertGreaterEqual(hellinger_fidelity(observed, expected), 0.97)

    def test_seeded_random_circuits_match_reference_semantics(self):
        generator = random.Random(20260823)
        signatures = {
            "h": (0, 1), "x": (0, 1), "s": (0, 1), "sdg": (0, 1),
            "t": (0, 1), "tdg": (0, 1), "rz": (1, 1), "ry": (1, 1),
            "cx": (0, 2), "cu1": (1, 2), "swap": (0, 2), "ccx": (0, 3),
        }
        names = tuple(signatures)
        for case_index in range(2):
            statements = []
            for _ in range(12):
                name = generator.choice(names)
                parameter_count, qubit_count = signatures[name]
                qubits = generator.sample(range(3), qubit_count)
                parameter = ""
                if parameter_count:
                    parameter = "(%.16g)" % generator.uniform(-math.pi, math.pi)
                statements.append(
                    "%s%s %s;" % (name, parameter, ",".join("q[%d]" % q for q in qubits))
                )
            source = HEADER + "qreg q[3];\ncreg c[3];\n" + "\n".join(statements) + "\nmeasure q -> c;\n"
            expected = exact_distribution(parse_qasm2(source))
            for target in TARGETS:
                with self.subTest(case=case_index, target=target):
                    shots = 4096
                    result = adapter.run(source, target, shots)
                    observed = {key: value / shots for key, value in result["counts"].items()}
                    fidelity = hellinger_fidelity(observed, expected)
                    self.assertGreaterEqual(
                        fidelity,
                        0.96,
                        "source:\n%s\nexpected=%r\nobserved=%r" % (source, expected, observed),
                    )


if __name__ == "__main__":
    unittest.main()
