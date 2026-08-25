#!/usr/bin/env python3
"""Self-contained end-to-end verifier for the LoomQ LQ-Q32 extension."""

import json

from .adapter import compile_hybrid
from .quantum_riscv import CUSTOM_0_OPCODE, encode_program, format_machine_code
from .riscv_emulator import TinyRISCVEmulator


SOURCE = '''OPENQASM 2.0;
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


def verify():
    operations, classical_assembly = compile_hybrid(SOURCE)
    words = encode_program(operations)
    expected_words = [0x0200000B, 0x0E00800B, 0x1220800B, 0x1401010B]
    if words != expected_words:
        raise AssertionError("machine-code words differ from the published encoding")
    if not all((word & 0x7F) == CUSTOM_0_OPCODE for word in words):
        raise AssertionError("machine-code stream does not use custom-0")

    emulator = TinyRISCVEmulator()
    emulator.load_machine_code(words)
    trace = emulator.execute_machine_code()
    if trace != operations:
        raise AssertionError("decoded execution trace differs from compiler operations")

    classical_results = {}
    for measured, expected in ((0, 3), (1, 7)):
        classical = TinyRISCVEmulator()
        classical.load_program(classical_assembly)
        classical.set_register("x12", measured)
        observed = classical.execute().get("x1", 0)
        if observed != expected:
            raise AssertionError("classical branch result is incorrect")
        classical_results[str(measured)] = observed

    return {
        "schema": "loomq.quantum-riscv-e2e.v1",
        "status": "PASS",
        "opcode": "0x%02x" % CUSTOM_0_OPCODE,
        "instruction_count": len(words),
        "machine_code": format_machine_code(words).splitlines(),
        "decoded_trace": trace,
        "classical_results": classical_results,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
