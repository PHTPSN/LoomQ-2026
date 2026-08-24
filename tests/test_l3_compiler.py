import itertools
import importlib.util
import random
import re
import unittest

from starter_kit.loomq_l3 import HybridSyntaxError
from starter_kit.loomq_l3 import compiler as l3_compiler
from starter_kit.riscv_emulator import TinyRISCVEmulator


if importlib.util.find_spec("qiskit") is not None:
    from starter_kit import adapter

    _compile_hybrid = adapter.compile_hybrid
else:
    def _dependency_free_quantum_operations(source):
        declaration = re.search(r"\bcreg\s+\w+\[(\d+)\]\s*;", source)
        if declaration is None:
            raise ValueError("test fallback requires one creg declaration")
        operations = []
        for statement in source.split(";"):
            statement = statement.strip()
            if not statement:
                continue
            lowered = statement.lower()
            if lowered.startswith(("openqasm", "include", "qreg", "creg")):
                continue
            operations.append(statement + ";")
        return operations, int(declaration.group(1))

    l3_compiler._quantum_operations = _dependency_free_quantum_operations
    _compile_hybrid = l3_compiler.compile_hybrid


def _source(classical, width=3, quantum=None):
    if quantum is None:
        quantum = "measure q -> c;"
    return '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[%d];
creg c[%d];
%s
classical {
%s
}
''' % (width, width, quantum, classical)


def _execute(assembly, measurements):
    emulator = TinyRISCVEmulator()
    emulator.load_program(assembly)
    for index, value in enumerate(measurements):
        emulator.set_register("x%d" % (10 + index), value)
    return emulator.execute()


def _registers(state):
    return tuple(state.get("x%d" % index, 0) for index in range(1, 10))


class L3CompilerTests(unittest.TestCase):
    def test_public_branch_and_quantum_order(self):
        source = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
measure q[0] -> c[0];
classical {
  if (c[0] == 1) { r1 = 7; } else { r1 = 3; }
}
cx q[0], q[1];
'''

        operations, assembly = _compile_hybrid(source)

        self.assertEqual(
            operations,
            ["h q[0];", "measure q[0] -> c[0];", "cx q[0], q[1];"],
        )
        self.assertEqual(_execute(assembly, (0, 0)).get("x1", 0), 3)
        self.assertEqual(_execute(assembly, (1, 0)).get("x1", 0), 7)

    def test_quantum_parameters_and_whole_register_measurements_are_canonical(self):
        source = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
ry(pi/7) q[0];
classical { r1 = c[1] - c[0]; }
cu1(-pi/3) q[0], q[1];
measure q -> c;
'''

        operations, assembly = _compile_hybrid(source)

        self.assertEqual(
            operations,
            [
                "ry(0.44879895051282759) q[0];",
                "cu1(-1.0471975511965976) q[0], q[1];",
                "measure q[0] -> c[0];",
                "measure q[1] -> c[1];",
            ],
        )
        self.assertEqual(_execute(assembly, (0, 1)).get("x1", 0), 1)

    def test_nested_branches_parentheses_and_unary_minus(self):
        classical = '''
r1 = 4;
r2 = 9;
if (c[0] == 1) {
  if (c[1] != 0) {
    r1 = r2 - r1;
  } else {
    r1 = -(r1 + 2);
  }
} else {
  r1 = r1 + 5;
}
r3 = (r1 + r2) - c[1];
'''
        _, assembly = _compile_hybrid(_source(classical, width=2))
        expected = {
            (0, 0): (9, 9, 18),
            (0, 1): (9, 9, 17),
            (1, 0): (-6, 9, 3),
            (1, 1): (5, 9, 13),
        }
        for measurements, registers in expected.items():
            with self.subTest(measurements=measurements):
                state = _execute(assembly, measurements)
                self.assertEqual(_registers(state)[:3], registers)

    def test_assignment_preserves_old_destination_value(self):
        _, assembly = _compile_hybrid(
            _source("r1 = 5; r2 = 2; r1 = r2 - r1;", width=1)
        )
        self.assertEqual(_registers(_execute(assembly, (0,)))[:2], (-3, 2))

    def test_in_place_assignment_preserves_repeated_target_values(self):
        classical = """
r1 = 4;
r2 = 3;
r1 = (r1 + r2) + r1;
r2 = (-r2) + r2;
"""
        _, assembly = _compile_hybrid(_source(classical, width=1))
        self.assertEqual(_registers(_execute(assembly, (0,)))[:2], (11, 0))

    def test_high_measurement_register_is_not_used_as_scratch(self):
        source = _source(
            "if (c[21] == 1) { r1 = 7; } else { r1 = 3; }",
            width=22,
            quantum="measure q[21] -> c[21];",
        )
        _, assembly = _compile_hybrid(source)
        zeros = (0,) * 22
        ones = (0,) * 21 + (1,)
        self.assertEqual(_execute(assembly, zeros).get("x1", 0), 3)
        self.assertEqual(_execute(assembly, ones).get("x1", 0), 7)
        self.assertNotIn("li x31, 1", assembly)

    def test_maximum_width_nested_assignment_needs_no_scratch_register(self):
        classical = """
r1 = 1;
r2 = 2;
r3 = 3;
r4 = 4;
r5 = 5;
r6 = 6;
r7 = 7;
r8 = 8;
r9 = 9;
r1 = ((r1 + r2) + (r3 - r4)) + (r1 + (r5 - (r6 - (r7 + (r8 - r9))))) + c[21];
"""
        _, assembly = _compile_hybrid(_source(classical, width=22))
        zeros = (0,) * 22
        highest_bit = (0,) * 21 + (1,)
        self.assertEqual(_execute(assembly, zeros).get("x1", 0), 8)
        self.assertEqual(_execute(assembly, highest_bit).get("x1", 0), 9)

    def test_one_remaining_scratch_handles_deep_condition(self):
        classical = """
r1 = 1;
r2 = 2;
r3 = 3;
r4 = 4;
r5 = 5;
r6 = 6;
r7 = 7;
r8 = 8;
r9 = 9;
if (((r1 + r2) - r3) + (r4 - r5) == ((r6 - r7) + (r8 - r9)) + 1 + c[20]) {
  r1 = 100;
} else {
  r1 = 200;
}
"""
        _, assembly = _compile_hybrid(_source(classical, width=21))
        zeros = (0,) * 21
        highest_bit = (0,) * 20 + (1,)
        self.assertEqual(_execute(assembly, zeros).get("x1", 0), 100)
        self.assertEqual(_execute(assembly, highest_bit).get("x1", 0), 200)
        self.assertIn("x31", assembly)

    def test_measurement_literal_conditions_cover_both_operand_orders(self):
        cases = (
            ("c[0] == 0", (7, 3)),
            ("0 == c[0]", (7, 3)),
            ("c[0] == 1", (3, 7)),
            ("1 == c[0]", (3, 7)),
            ("c[0] == 2", (3, 3)),
            ("c[0] != 0", (3, 7)),
            ("0 != c[0]", (3, 7)),
            ("c[0] != 1", (7, 3)),
            ("1 != c[0]", (7, 3)),
            ("c[0] != 2", (7, 7)),
        )
        for condition, expected in cases:
            with self.subTest(condition=condition):
                classical = "if (%s) { r1 = 7; } else { r1 = 3; }" % condition
                _, assembly = _compile_hybrid(_source(classical, width=1))
                actual = tuple(
                    _execute(assembly, (measurement,)).get("x1", 0)
                    for measurement in (0, 1)
                )
                self.assertEqual(actual, expected)

    def test_constant_conditions_and_empty_blocks(self):
        classical = """
r1 = 1;
if (2 - 1 == 1) { r1 = r1 + 4; }
if (3 != 3) { r1 = 99; } else { }
if (0 == 1) { } else { r1 = r1 + 2; }
"""
        _, assembly = _compile_hybrid(_source(classical, width=1))
        self.assertEqual(_execute(assembly, (0,)).get("x1", 0), 7)

    def test_comments_cannot_terminate_the_classical_block(self):
        classical = '''
// This brace is inert: }
r1 = 2;
/* This brace is also inert: { */
r1 = r1 + 3;
'''
        _, assembly = _compile_hybrid(_source(classical, width=1))
        self.assertEqual(_execute(assembly, (0,)).get("x1", 0), 5)

    def test_invalid_tokens_are_rejected_instead_of_ignored(self):
        with self.assertRaisesRegex(HybridSyntaxError, "unexpected classical syntax"):
            _compile_hybrid(_source("r1 = 2 $ 3;", width=1))

    def test_multiple_classical_blocks_are_rejected(self):
        source = _source("r1 = 1;", width=1) + "classical { r2 = 2; }\n"
        with self.assertRaisesRegex(HybridSyntaxError, "multiple classical blocks"):
            _compile_hybrid(source)

    def test_measurement_mapping_cannot_exceed_x31(self):
        with self.assertRaisesRegex(HybridSyntaxError, "x10..x31"):
            _compile_hybrid(_source("r1 = 1;", width=23))


def _eval_expression(expression, registers, measurements):
    kind = expression[0]
    if kind == "integer":
        return expression[1]
    if kind == "register":
        return registers[expression[1]]
    if kind == "measurement":
        return measurements[expression[1]]
    if kind == "negative":
        return -_eval_expression(expression[1], registers, measurements)
    left = _eval_expression(expression[2], registers, measurements)
    right = _eval_expression(expression[3], registers, measurements)
    return left + right if expression[1] == "+" else left - right


def _eval_statements(statements, registers, measurements):
    for statement in statements:
        if statement[0] == "assignment":
            registers[statement[1]] = _eval_expression(statement[2], registers, measurements)
            continue
        left = _eval_expression(statement[2], registers, measurements)
        right = _eval_expression(statement[3], registers, measurements)
        truth = left == right if statement[1] == "==" else left != right
        _eval_statements(statement[4] if truth else statement[5], registers, measurements)


def _render_expression(expression):
    kind = expression[0]
    if kind == "integer":
        return str(expression[1])
    if kind == "register":
        return "r%d" % expression[1]
    if kind == "measurement":
        return "c[%d]" % expression[1]
    if kind == "negative":
        return "-(%s)" % _render_expression(expression[1])
    return "(%s %s %s)" % (
        _render_expression(expression[2]),
        expression[1],
        _render_expression(expression[3]),
    )


def _render_statements(statements, indent=""):
    lines = []
    for statement in statements:
        if statement[0] == "assignment":
            lines.append(
                "%sr%d = %s;"
                % (indent, statement[1], _render_expression(statement[2]))
            )
            continue
        lines.append(
            "%sif (%s %s %s) {"
            % (
                indent,
                _render_expression(statement[2]),
                statement[1],
                _render_expression(statement[3]),
            )
        )
        lines.extend(_render_statements(statement[4], indent + "  "))
        lines.append(indent + "} else {")
        lines.extend(_render_statements(statement[5], indent + "  "))
        lines.append(indent + "}")
    return lines


class L3RandomizedDifferentialTests(unittest.TestCase):
    def test_random_programs_match_independent_interpreter(self):
        rng = random.Random(20260824)

        def atom():
            choice = rng.randrange(3)
            if choice == 0:
                return ("integer", rng.randint(-5, 8))
            if choice == 1:
                return ("register", rng.randint(1, 3))
            return ("measurement", rng.randint(0, 2))

        def expression(depth=0):
            if depth >= 3 or rng.random() < 0.3:
                result = atom()
            else:
                result = (
                    "binary",
                    rng.choice(("+", "-")),
                    expression(depth + 1),
                    expression(depth + 1),
                )
            if rng.random() < 0.2:
                result = ("negative", result)
            return result

        def assignment():
            return ("assignment", rng.randint(1, 3), expression())

        for program_index in range(60):
            statements = [
                ("assignment", 1, ("integer", rng.randint(-3, 6))),
                ("assignment", 2, ("integer", rng.randint(-3, 6))),
                ("assignment", 3, ("integer", rng.randint(-3, 6))),
            ]
            for _ in range(3):
                if rng.random() < 0.55:
                    condition = (
                        "branch",
                        rng.choice(("==", "!=")),
                        expression(2),
                        expression(2),
                        (assignment(),),
                        (assignment(),),
                    )
                    if rng.random() < 0.3:
                        condition = (
                            "branch",
                            rng.choice(("==", "!=")),
                            expression(2),
                            expression(2),
                            (condition,),
                            (assignment(),),
                        )
                    statements.append(condition)
                else:
                    statements.append(assignment())
            rendered = "\n".join(_render_statements(statements))
            _, assembly = _compile_hybrid(_source(rendered, width=3))

            for measurements in itertools.product((0, 1), repeat=3):
                with self.subTest(program=program_index, measurements=measurements):
                    expected = {index: 0 for index in range(1, 10)}
                    _eval_statements(statements, expected, measurements)
                    actual = _registers(_execute(assembly, measurements))
                    self.assertEqual(
                        actual,
                        tuple(expected[index] for index in range(1, 10)),
                    )


if __name__ == "__main__":
    unittest.main()
