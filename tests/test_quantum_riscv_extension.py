import importlib.util
import math
import re
import unittest

from starter_kit.quantum_riscv import (
    ANGLE_SCALE,
    CUSTOM_0_OPCODE,
    QuantumInstruction,
    QuantumRISCVError,
    decode_instruction,
    decode_program,
    encode_instruction,
    encode_operation,
    encode_program,
    format_machine_code,
    parse_operation,
)
from starter_kit.riscv_emulator import TinyRISCVEmulator


class QuantumRISCVEncodingTests(unittest.TestCase):
    def test_fixed_instruction_words_cover_the_whitelist_and_measurement(self):
        expected = {
            "h q[0];": 0x0200000B,
            "x q[1];": 0x0400008B,
            "s q[2];": 0x0600010B,
            "sdg q[3];": 0x0800018B,
            "t q[4];": 0x0A00020B,
            "tdg q[5];": 0x0C00028B,
            "cx q[0], q[1];": 0x0E00800B,
            "swap q[2], q[3];": 0x1001810B,
            "ccx q[1], q[2], q[3];": 0x1231008B,
            "measure q[1] -> c[2];": 0x1401008B,
            "ry(0) q[6];": 0x0000130B,
            "rz(1) q[7];": 0x2000238B,
            "cu1(-1) q[4], q[5];": 0xE002B20B,
        }
        for operation, word in expected.items():
            with self.subTest(operation=operation):
                self.assertEqual(encode_operation(operation), word)
                self.assertEqual(word & 0x7F, CUSTOM_0_OPCODE)

    def test_encode_decode_round_trip_preserves_semantics(self):
        operations = [
            "h q[31];",
            "x q[0];",
            "s q[1];",
            "sdg q[2];",
            "t q[3];",
            "tdg q[4];",
            "ry(0.44879895051282759) q[5];",
            "rz(-2.75) q[6];",
            "cx q[7], q[8];",
            "cu1(-1.0471975511965976) q[9], q[10];",
            "swap q[11], q[12];",
            "ccx q[13], q[14], q[15];",
            "measure q[16] -> c[17];",
        ]
        decoded = decode_program(encode_program(operations))
        original = [parse_operation(operation) for operation in operations]
        for before, after in zip(original, decoded):
            with self.subTest(operation=before.name):
                self.assertEqual(after.name, before.name)
                self.assertEqual(after.qubits, before.qubits)
                self.assertEqual(after.clbit, before.clbit)
                if before.params:
                    self.assertAlmostEqual(
                        after.params[0], before.params[0], delta=0.5 / ANGLE_SCALE
                    )

    def test_angles_are_periodic_and_quantized_with_documented_error(self):
        base = decode_instruction(encode_operation("rz(0.25) q[3];"))
        periodic = decode_instruction(
            encode_operation("rz(%s) q[3];" % (0.25 + 8.0 * math.pi))
        )
        self.assertEqual(encode_instruction(base), encode_instruction(periodic))
        self.assertAlmostEqual(base.params[0], 0.25, delta=0.5 / ANGLE_SCALE)

    def test_invalid_operation_and_machine_fields_are_rejected(self):
        invalid_operations = [
            "y q[0];",
            "h q[32];",
            "h(1) q[0];",
            "cx q[1], q[1];",
            "measure q[0] -> c[32];",
        ]
        for operation in invalid_operations:
            with self.subTest(operation=operation):
                with self.assertRaises(QuantumRISCVError):
                    encode_operation(operation)

        invalid_words = [
            0x00000000,  # Not custom-0.
            CUSTOM_0_OPCODE | (0x7 << 12),  # Unknown funct3.
            0x0200000B | (1 << 15),  # qh has a nonzero reserved rs1.
            0x0E00000B,  # qcx repeats q[0].
            -1,
            0x100000000,
        ]
        for word in invalid_words:
            with self.subTest(word=word):
                with self.assertRaises(QuantumRISCVError):
                    decode_instruction(word)

    def test_machine_code_listing_is_stable(self):
        self.assertEqual(
            format_machine_code([0x0200000B, 0x0E00800B]),
            "0x0200000b\n0x0e00800b\n",
        )


class QuantumRISCVExecutionTests(unittest.TestCase):
    @staticmethod
    def _compile_hybrid(source):
        if importlib.util.find_spec("qiskit") is not None:
            from starter_kit.adapter import compile_hybrid

            return compile_hybrid(source)

        # Keep the extension suite dependency-free in minimal development
        # environments while exercising the real L3 parser and lowerer.
        from starter_kit.loomq_l3 import compiler

        def fallback(quantum_source):
            declaration = re.search(r"\bcreg\s+\w+\[(\d+)\]\s*;", quantum_source)
            if declaration is None:
                raise ValueError("test fallback requires one creg declaration")
            operations = []
            for statement in quantum_source.split(";"):
                statement = statement.strip()
                if not statement:
                    continue
                lowered = statement.lower()
                if lowered.startswith(("openqasm", "include", "qreg", "creg")):
                    continue
                operations.append(statement + ";")
            return operations, int(declaration.group(1))

        original = compiler._quantum_operations
        compiler._quantum_operations = fallback
        try:
            return compiler.compile_hybrid(source)
        finally:
            compiler._quantum_operations = original

    def test_hybrid_qasm_machine_code_decode_and_execution_loop(self):
        source = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0], q[1];
ccx q[0], q[1], q[2];
measure q[2] -> c[2];
classical {
  if (c[2] == 1) { r1 = 7; } else { r1 = 3; }
}
'''
        operations, assembly = self._compile_hybrid(source)
        words = encode_program(operations)

        dispatched = []
        emulator = TinyRISCVEmulator()
        emulator.load_machine_code(words)
        trace = emulator.execute_machine_code(dispatched.append)

        self.assertEqual(trace, operations)
        self.assertEqual([item.to_operation() for item in dispatched], operations)
        self.assertTrue(all((word & 0x7F) == CUSTOM_0_OPCODE for word in words))

        for measured, expected in ((0, 3), (1, 7)):
            classical = TinyRISCVEmulator()
            classical.load_program(assembly)
            classical.set_register("x12", measured)
            self.assertEqual(classical.execute().get("x1", 0), expected)

    def test_decoder_failure_occurs_in_execution_path(self):
        emulator = TinyRISCVEmulator()
        emulator.load_machine_code([0x00000000])
        with self.assertRaises(QuantumRISCVError):
            emulator.execute_machine_code()


if __name__ == "__main__":
    unittest.main()
