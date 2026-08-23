"""Competition-shaped L1 acceptance tests.

These tests close gaps intentionally left by the small public evaluator:
eight circuit categories, the official sampling settings, strict result
validation, and semantic checks of the exact public target-IR artifacts.
"""

from datetime import datetime
import math
import os
import random
import re
import unittest

from starter_kit import adapter
from starter_kit.loomq_l1.frontend import parse_qasm2
from starter_kit.loomq_l1.model import Gate, LoomQCircuit, Measure
from starter_kit.loomq_l1.semantics import exact_distribution


RUN_SDK_TESTS = os.environ.get("LOOMQ_RUN_SDK_TESTS") == "1"
TARGETS = ("spinq", "originq", "braket")
SHOTS = 8192
MINIMUM_FIDELITY = 0.97
HEADER = 'OPENQASM 2.0;\ninclude "qelib1.inc";\n'


def _program(qubits, statements):
    return (
        HEADER
        + "qreg q[%d];\ncreg c[%d];\n" % (qubits, qubits)
        + "\n".join(statements)
        + "\nmeasure q -> c;\n"
    )


def _random_program(seed, qubits, gate_count):
    generator = random.Random(seed)
    signatures = {
        "h": (0, 1),
        "x": (0, 1),
        "s": (0, 1),
        "sdg": (0, 1),
        "t": (0, 1),
        "tdg": (0, 1),
        "rz": (1, 1),
        "ry": (1, 1),
        "cx": (0, 2),
        "cu1": (1, 2),
        "swap": (0, 2),
        "ccx": (0, 3),
    }
    names = tuple(signatures)
    statements = []
    # Begin with every gate once so each random case is also a complete gate
    # matrix. The shuffled tail then exercises interactions and varied operands.
    choices = list(names)
    choices.extend(generator.choice(names) for _ in range(gate_count - len(names)))
    generator.shuffle(choices)
    for name in choices:
        parameter_count, operand_count = signatures[name]
        operands = generator.sample(range(qubits), operand_count)
        parameter = ""
        if parameter_count:
            parameter = "(%.17g)" % generator.uniform(-math.pi, math.pi)
        statements.append(
            "%s%s %s;"
            % (name, parameter, ",".join("q[%d]" % index for index in operands))
        )
    return _program(qubits, statements)


COMPETITION_CASES = {
    "bell": _program(2, ["h q[0];", "cx q[0],q[1];"]),
    "ghz3": _program(3, ["h q[0];", "cx q[0],q[1];", "cx q[1],q[2];"]),
    "ghz5": _program(
        5,
        [
            "h q[0];",
            "cx q[0],q[1];",
            "cx q[1],q[2];",
            "cx q[2],q[3];",
            "cx q[3],q[4];",
        ],
    ),
    "qft4": _program(
        4,
        [
            # A phase-bearing superposition makes controlled-phase mistakes
            # observable; QFT of a basis state alone would be uniformly sampled.
            "ry(pi/3) q[0];",
            "h q[1];",
            "t q[1];",
            "x q[2];",
            "h q[3];",
            "cu1(pi/2) q[2],q[3];",
            "cu1(pi/4) q[1],q[3];",
            "cu1(pi/8) q[0],q[3];",
            "h q[2];",
            "cu1(pi/2) q[1],q[2];",
            "cu1(pi/4) q[0],q[2];",
            "h q[1];",
            "cu1(pi/2) q[0],q[1];",
            "h q[0];",
            "swap q[0],q[3];",
            "swap q[1],q[2];",
        ],
    ),
    "grover3": _program(
        3,
        [
            "h q[0];",
            "h q[1];",
            "h q[2];",
            "h q[2];",
            "ccx q[0],q[1],q[2];",
            "h q[2];",
            "h q[0];",
            "h q[1];",
            "h q[2];",
            "x q[0];",
            "x q[1];",
            "x q[2];",
            "h q[2];",
            "ccx q[0],q[1],q[2];",
            "h q[2];",
            "x q[0];",
            "x q[1];",
            "x q[2];",
            "h q[0];",
            "h q[1];",
            "h q[2];",
        ],
    ),
    "random1": _random_program(2026082301, 3, 24),
    "random2": _random_program(2026082302, 4, 28),
    "random3": _random_program(2026082303, 5, 32),
}


def _fidelity(observed, expected):
    states = set(observed) | set(expected)
    distance = math.sqrt(
        sum(
            (math.sqrt(observed.get(key, 0.0)) - math.sqrt(expected.get(key, 0.0)))
            ** 2
            for key in states
        )
    ) / math.sqrt(2.0)
    return 1.0 - distance


def _assert_result_contract(test, result, shots, width):
    test.assertIs(type(result), dict)
    test.assertEqual(
        set(result),
        {"backend", "job_id", "shots", "counts", "bit_order", "timestamp", "meta"},
    )
    test.assertIsInstance(result["backend"], str)
    test.assertTrue(result["backend"])
    test.assertIsInstance(result["job_id"], str)
    test.assertTrue(result["job_id"])
    test.assertIs(type(result["shots"]), int)
    test.assertEqual(result["shots"], shots)
    test.assertIs(type(result["counts"]), dict)
    test.assertTrue(result["counts"])
    test.assertEqual(sum(result["counts"].values()), shots)
    for key, value in result["counts"].items():
        test.assertRegex(key, "^[01]{%d}$" % width)
        test.assertIs(type(value), int)
        test.assertGreaterEqual(value, 0)
    test.assertEqual(result["bit_order"], "little")
    test.assertIsInstance(result["timestamp"], str)
    parsed = datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
    test.assertIsNotNone(parsed.tzinfo)
    test.assertIs(type(result["meta"]), dict)
    test.assertFalse(result["meta"].get("is_mock", False))


_QUBIT = re.compile(r"q\[(\d+)\]")
_CLBIT = re.compile(r"c\[(\d+)\]")


def _qubit(text):
    match = _QUBIT.fullmatch(text.strip())
    if not match:
        raise AssertionError("invalid target qubit reference: %s" % text)
    return int(match.group(1))


def _clbit(text):
    match = _CLBIT.fullmatch(text.strip())
    if not match:
        raise AssertionError("invalid target classical reference: %s" % text)
    return int(match.group(1))


def _parse_braket_contract(source):
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    if lines[:2] != ["OPENQASM 3.0;", 'include "stdgates.inc";']:
        raise AssertionError("invalid Braket OpenQASM 3 header")
    qdecl = re.fullmatch(r"qubit\[(\d+)\] q;", lines[2])
    cdecl = re.fullmatch(r"bit\[(\d+)\] c;", lines[3])
    if not qdecl or not cdecl:
        raise AssertionError("invalid Braket declarations")
    names = {
        "h": "h", "x": "x", "s": "s", "sdg": "sdg", "t": "t",
        "tdg": "tdg", "rz": "rz", "ry": "ry", "cx": "cx",
        "cnot": "cx", "cp": "cu1", "swap": "swap", "ccx": "ccx",
    }
    instructions = []
    for line in lines[4:]:
        measured = re.fullmatch(r"(c\[\d+\])\s*=\s*measure\s+(q\[\d+\]);", line)
        if measured:
            instructions.append(Measure(_qubit(measured.group(2)), _clbit(measured.group(1))))
            continue
        call = re.fullmatch(r"([a-z]+)(?:\(([^()]*)\))?\s+(.+);", line)
        if not call or call.group(1) not in names:
            raise AssertionError("invalid Braket instruction: %s" % line)
        params = () if call.group(2) is None else (float(call.group(2)),)
        operands = tuple(_qubit(item) for item in call.group(3).split(","))
        instructions.append(Gate(names[call.group(1)], params, operands))
    return LoomQCircuit(int(qdecl.group(1)), int(cdecl.group(1)), tuple(instructions))


def _parse_origin_contract(source):
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    qdecl = re.fullmatch(r"QINIT\s+(\d+)", lines[0])
    cdecl = re.fullmatch(r"CREG\s+(\d+)", lines[1])
    if not qdecl or not cdecl:
        raise AssertionError("invalid OriginIR declarations")
    names = {
        "H": "h", "X": "x", "S": "s", "SDAG": "sdg", "T": "t",
        "TDAG": "tdg", "RZ": "rz", "RY": "ry", "CNOT": "cx",
        "CU1": "cu1", "CR": "cu1", "SWAP": "swap", "TOFFOLI": "ccx",
        "CCX": "ccx",
    }
    instructions = []
    for line in lines[2:]:
        measured = re.fullmatch(r"MEASURE\s+(q\[\d+\])\s*,\s*(c\[\d+\])", line)
        if measured:
            instructions.append(Measure(_qubit(measured.group(1)), _clbit(measured.group(2))))
            continue
        call = re.fullmatch(r"([A-Z0-9]+)\s+(.+?)(?:,\(([^()]*)\))?", line)
        if not call or call.group(1) not in names:
            raise AssertionError("invalid OriginIR instruction: %s" % line)
        params = () if call.group(3) is None else (float(call.group(3)),)
        operands = tuple(_qubit(item) for item in call.group(2).split(","))
        instructions.append(Gate(names[call.group(1)], params, operands))
    return LoomQCircuit(int(qdecl.group(1)), int(cdecl.group(1)), tuple(instructions))


def _parse_target_artifact(source, target):
    if target == "spinq":
        return parse_qasm2(source)
    if target == "originq":
        return _parse_origin_contract(source)
    if target == "braket":
        return _parse_braket_contract(source)
    raise AssertionError("unknown target: %s" % target)


class L1TargetArtifactAcceptanceTests(unittest.TestCase):
    def test_exact_transpile_artifacts_round_trip_all_eight_cases(self):
        for case_name, source in COMPETITION_CASES.items():
            expected = exact_distribution(parse_qasm2(source))
            for target in TARGETS:
                with self.subTest(case=case_name, target=target):
                    native = adapter.transpile(source, target)
                    reconstructed = _parse_target_artifact(native, target)
                    self.assertEqual(reconstructed.num_qubits, parse_qasm2(source).num_qubits)
                    self.assertEqual(reconstructed.num_clbits, parse_qasm2(source).num_clbits)
                    observed = exact_distribution(reconstructed)
                    self.assertGreaterEqual(_fidelity(observed, expected), 1.0 - 1e-10)


@unittest.skipUnless(RUN_SDK_TESTS, "set LOOMQ_RUN_SDK_TESTS=1 to run real SDKs")
class L1CompetitionExecutionAcceptanceTests(unittest.TestCase):
    def test_eight_cases_on_three_sdks_at_official_settings(self):
        for case_name, source in COMPETITION_CASES.items():
            circuit = parse_qasm2(source)
            expected = exact_distribution(circuit)
            for target in TARGETS:
                with self.subTest(case=case_name, target=target):
                    result = adapter.run(source, target, SHOTS)
                    _assert_result_contract(self, result, SHOTS, circuit.num_clbits)
                    observed = {
                        key: count / SHOTS for key, count in result["counts"].items()
                    }
                    self.assertGreaterEqual(
                        _fidelity(observed, expected),
                        MINIMUM_FIDELITY,
                        "case=%s target=%s expected=%r observed=%r"
                        % (case_name, target, expected, observed),
                    )


if __name__ == "__main__":
    unittest.main()
