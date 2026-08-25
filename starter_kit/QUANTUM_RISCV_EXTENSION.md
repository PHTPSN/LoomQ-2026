# LoomQ quantum RISC-V extension (`LQ-Q32`)

## Scope

`LQ-Q32` is a minimal, executable 32-bit custom instruction extension for the
12-gate LoomQ OpenQASM 2.0 whitelist plus measurement. It is not a complete
RISC-V assembler or processor. Its purpose is to make quantum instruction
encoding enter a real, locally reproducible encode/decode/execute path while
the existing tiny RISC-V emulator continues to execute the classical control
program.

The reference implementation is dependency-free and runs on a normal CPU.
An optional dispatcher may forward decoded instructions to another simulator,
including a GPU-backed one, without changing the instruction encoding.

## Common field

Every `LQ-Q32` instruction uses the standard RISC-V `custom-0` major opcode:

| Bits | Field | Value |
| --- | --- | --- |
| `6:0` | `opcode` | `0001011` (`0x0B`) |

Qubit and classical-bit operands are unsigned five-bit indices, so one
instruction can address indices `0..31`. Any nonzero reserved field is an
invalid encoding rather than an ignored value.

## QR format: gates without parameters and measurement

```text
31          25 24       20 19       15 14    12 11        7 6         0
+--------------+-----------+-----------+--------+-----------+-----------+
|    funct7    |    rs2    |    rs1    |  000   |    rd     |  0001011  |
+--------------+-----------+-----------+--------+-----------+-----------+
```

Operand order is preserved exactly: `rd = q0`, `rs1 = q1`, and `rs2 = q2`.
Unused operand fields must be zero. For measurement, `rd` is the measured
qubit and `rs1` is the destination classical bit.

| `funct7` | Mnemonic | Meaning | Operands |
| ---: | --- | --- | --- |
| `0x01` | `qh` | Hadamard | `rd` |
| `0x02` | `qx` | Pauli-X | `rd` |
| `0x03` | `qs` | S phase | `rd` |
| `0x04` | `qsdg` | inverse S | `rd` |
| `0x05` | `qt` | T phase | `rd` |
| `0x06` | `qtdg` | inverse T | `rd` |
| `0x07` | `qcx` | controlled X | `rd, rs1` |
| `0x08` | `qswap` | swap | `rd, rs1` |
| `0x09` | `qccx` | Toffoli | `rd, rs1, rs2` |
| `0x0A` | `qmeasure` | measurement | `rd -> rs1` |

Examples:

```text
h q[0];                  -> 0x0200000b
cx q[0], q[1];           -> 0x0e00800b
measure q[1] -> c[0];    -> 0x1400008b
```

## QI format: parameterized gates

```text
31                      20 19       15 14    12 11        7 6         0
+--------------------------+-----------+--------+-----------+-----------+
|       imm[11:0]          |    rs1    | funct3 |    rd     |  0001011  |
+--------------------------+-----------+--------+-----------+-----------+
```

| `funct3` | Mnemonic | Operands |
| ---: | --- | --- |
| `001` | `qry` | `rd`; `rs1` is zero |
| `010` | `qrz` | `rd`; `rs1` is zero |
| `011` | `qcu1` | `rd, rs1` |

The immediate stores an angle in signed Q3.9 fixed-point radians:

```text
encoded = round(canonical_angle * 512)
decoded = sign_extend(imm[11:0]) / 512
```

Before encoding, angles are reduced to the equivalent interval `[-pi, pi]`.
The maximum quantization error is `1/1024` radian. This normalization is valid
for `ry`, `rz`, and `cu1`, which are `2*pi` periodic up to an irrelevant global
phase. Parameterized examples should therefore be compared within the stated
quantization tolerance rather than by decimal string equality.

## Executable reference path

The implementation and its executable path are:

```text
Hybrid-QASM
  -> starter_kit.adapter.compile_hybrid()
  -> canonical ordered quantum operations
  -> starter_kit.quantum_riscv.encode_program()
  -> unsigned 32-bit instruction words
  -> TinyRISCVEmulator.load_machine_code()
  -> starter_kit.quantum_riscv.decode_instruction()
  -> TinyRISCVEmulator.execute_machine_code()
  -> ordered semantic operation trace / optional dispatcher
```

The decoder rejects an incorrect opcode, unknown `funct3` or `funct7`, nonzero
reserved fields, repeated qubit operands, and values outside an unsigned
32-bit word. Consequently, the custom opcode participates in execution and is
not merely a documentation-only assignment.

## Compatibility and verification

`adapter.compile_hybrid()` retains its official return type of `(quantum_ops,
assembly)`. The existing classical assembly remains accepted by
`TinyRISCVEmulator.load_program()`. The binary quantum stream is an additional
path and does not alter the competition interface.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m starter_kit.quantum_riscv_e2e
.\.venv\Scripts\python.exe -m unittest tests.test_quantum_riscv_extension -v
.\.venv\Scripts\python.exe -m unittest tests.test_l3_compiler -v
.\.venv\Scripts\python.exe starter_kit\evaluator.py --level l3
```

The first suite fixes representative instruction words as hexadecimal
constants, covers all 12 whitelist gates and measurement, checks invalid
encodings and angle bounds, and runs Hybrid-QASM through the complete binary
execution path.
