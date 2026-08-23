import math
import unittest

from starter_kit import adapter
from starter_kit.loomq_l1.frontend import QASM2FrontendError, parse_qasm2
from starter_kit.loomq_l1.model import Gate, Measure
from starter_kit.loomq_l1.semantics import exact_distribution


HEADER = '''OPENQASM 2.0;
include "qelib1.inc";
'''


class L1FrontendTests(unittest.TestCase):
    def test_complete_gate_matrix_remains_canonical(self):
        source = HEADER + '''qreg qa[3];
creg ca[3];
h qa[0];
x qa[1];
s qa[0];
sdg qa[0];
t qa[0];
tdg qa[0];
rz(pi/7) qa[0];
ry(-pi/3) qa[1];
cx qa[0],qa[1];
cu1(pi/5) qa[0],qa[1];
swap qa[1],qa[2];
ccx qa[0],qa[1],qa[2];
measure qa -> ca;
'''
        circuit = parse_qasm2(source)
        gates = [item for item in circuit.instructions if isinstance(item, Gate)]
        self.assertEqual(
            [gate.name for gate in gates],
            ["h", "x", "s", "sdg", "t", "tdg", "rz", "ry", "cx", "cu1", "swap", "ccx"],
        )
        self.assertAlmostEqual(gates[6].params[0], math.pi / 7)
        self.assertEqual(len(circuit.measurements), 3)

    def test_multiple_registers_are_flattened_without_changing_references(self):
        source = HEADER + '''qreg left[1];
qreg right[2];
creg low[1];
creg high[2];
cx left[0],right[1];
measure right[0] -> high[1];
'''
        circuit = parse_qasm2(source)
        self.assertEqual(circuit.num_qubits, 3)
        self.assertEqual(circuit.num_clbits, 3)
        self.assertEqual(circuit.instructions[0], Gate("cx", (), (0, 2)))
        self.assertEqual(circuit.instructions[1], Measure(1, 2))

    def test_rejects_an_instruction_outside_the_whitelist(self):
        source = HEADER + "qreg q[1];\ncreg c[1];\nreset q[0];\n"
        with self.assertRaisesRegex(QASM2FrontendError, "unsupported gate: reset"):
            parse_qasm2(source)

    def test_rejects_classical_feedback(self):
        source = HEADER + '''qreg q[1];
creg c[1];
if(c==1) x q[0];
'''
        with self.assertRaises(QASM2FrontendError):
            parse_qasm2(source)

    def test_rejects_user_defined_gates(self):
        source = HEADER + '''gate custom a { h a; }
qreg q[1];
creg c[1];
custom q[0];
'''
        with self.assertRaisesRegex(QASM2FrontendError, "unsupported gate: custom"):
            parse_qasm2(source)

    def test_rejects_uppercase_builtin_cx_spelling(self):
        source = HEADER + "qreg q[2];\ncreg c[2];\nCX q[0],q[1];\n"
        with self.assertRaisesRegex(QASM2FrontendError, "use lowercase cx"):
            parse_qasm2(source)

    def test_rejects_non_qelib_include_before_file_lookup(self):
        source = '''OPENQASM 2.0;
include "private.inc";
qreg q[1];
creg c[1];
'''
        with self.assertRaisesRegex(QASM2FrontendError, "exactly one include"):
            parse_qasm2(source)

    def test_rejects_nonstandard_relaxed_syntax(self):
        source = 'include "qelib1.inc"; qreg q[1]; creg c[1]; h q[0];'
        with self.assertRaises(QASM2FrontendError):
            parse_qasm2(source)


class L1EmitterTests(unittest.TestCase):
    def setUp(self):
        self.source = HEADER + '''qreg source[2];
creg result[2];
h source[0];
cu1(pi/2) source[0],source[1];
measure source[0] -> result[1];
'''

    def test_spinq_emits_complete_openqasm2(self):
        native = adapter.transpile(self.source, "spinq")
        self.assertIn("OPENQASM 2.0;", native)
        self.assertIn("cu1(1.5707963267948966) q[0], q[1];", native)
        self.assertIn("measure q[0] -> c[1];", native)

    def test_originq_uses_formal_contract_names(self):
        native = adapter.transpile(self.source, "originq")
        self.assertIn("QINIT 2", native)
        self.assertIn("CU1 q[0], q[1],(1.5707963267948966)", native)
        self.assertIn("MEASURE q[0], c[1]", native)

    def test_braket_emits_standard_openqasm3(self):
        native = adapter.transpile(self.source, "braket")
        self.assertIn("OPENQASM 3.0;", native)
        self.assertIn('include "stdgates.inc";', native)
        self.assertIn("cp(1.5707963267948966) q[0], q[1];", native)
        self.assertIn("c[1] = measure q[0];", native)

    def test_rejects_unknown_target(self):
        with self.assertRaisesRegex(ValueError, "unsupported target"):
            adapter.transpile(self.source, "unknown")


class L1SemanticTests(unittest.TestCase):
    def test_bell_distribution_and_little_bit_order(self):
        source = HEADER + '''qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
'''
        distribution = exact_distribution(parse_qasm2(source))
        self.assertEqual(set(distribution), {"00", "11"})
        self.assertAlmostEqual(distribution["00"], 0.5)
        self.assertAlmostEqual(distribution["11"], 0.5)

    def test_mid_circuit_measurement_creates_semantic_branches(self):
        source = HEADER + '''qreg q[1];
creg c[2];
h q[0];
measure q[0] -> c[0];
x q[0];
measure q[0] -> c[1];
'''
        distribution = exact_distribution(parse_qasm2(source))
        self.assertAlmostEqual(distribution["01"], 0.5)
        self.assertAlmostEqual(distribution["10"], 0.5)
        self.assertEqual(set(distribution), {"01", "10"})


if __name__ == "__main__":
    unittest.main()
