# Level 3 implementation note

`adapter.compile_hybrid()` compiles the documented Hybrid-QASM subset into an
ordered quantum-operation list and assembly for `riscv_emulator.py`.

The optional `LQ-Q32` binary extension then encodes that ordered quantum list
as real 32-bit RISC-V `custom-0` instruction words. Its complete specification
is [`QUANTUM_RISCV_EXTENSION.md`](QUANTUM_RISCV_EXTENSION.md), and the
dependency-free encoder/decoder is implemented in
[`quantum_riscv.py`](quantum_riscv.py).

## Pipeline

1. A comment- and string-aware scanner locates and removes exactly one
   `classical { ... }` block.
2. The remaining OpenQASM 2 program is parsed by the Level 1 frontend, so the
   quantum side uses the competition's 12-gate whitelist and canonical qubit
   and classical-bit numbering.
3. A dedicated tokenizer and recursive-descent parser build an AST for
   assignments, `if/else`, integer literals, `r1..r9`, `c[k]`, parentheses,
   unary negation, and the `+`, `-`, `==`, and `!=` operators.
4. The AST is lowered only to `li`, `add`, `sub`, `addi`, `beq`, `bne`, and
   `j`, the instruction set accepted by the supplied emulator.
5. For the custom quantum RISC-V Bonus, the canonical quantum stream is
   encoded with `quantum_riscv.encode_program()`, loaded through
   `TinyRISCVEmulator.load_machine_code()`, and decoded during
   `execute_machine_code()` before semantic dispatch.

## Registers and pressure handling

- `r1..r9` map to `x1..x9`.
- `c[k]` maps to `x10+k`; therefore at most 22 measurement bits fit in the
  emulator's `x0..x31` register file.
- Additive expressions are normalized to an affine form: a constant plus
  integer coefficients of source registers. Deep expression trees therefore
  do not consume a stack of temporary registers.
- Assignments use their destination as the accumulator whenever the old
  destination has coefficient zero or a signed power-of-two coefficient. This
  covers common repeated-target expressions without a temporary, including at
  the full 22-bit measurement width.
- A complex comparison is lowered as `left - right` and needs only one
  temporary. Scratch registers are selected from registers above the declared
  measurement range, then from user registers never mentioned by the program.

If all 31 writable registers contain live language state, there is no spare
architectural register for a complex comparison or for an assignment whose
old destination has a non-power-of-two coefficient. The compiler raises
`HybridSyntaxError` in that exceptional case instead of corrupting a user or
measurement register. Direct comparisons and the common affine assignment
forms still compile at the maximum width.

## Verification

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_l3_compiler -v
.\.venv\Scripts\python.exe -m unittest tests.test_quantum_riscv_extension -v
.\.venv\Scripts\python.exe starter_kit\evaluator.py --level l3
```

The Level 3 suite includes deterministic boundary cases and seeded randomized
differential tests. Every generated program is compared with an independent
reference interpreter for every possible three-bit measurement assignment.
The binary-extension suite additionally fixes exact hexadecimal instruction
words, covers all 12 whitelist gates and measurement, rejects malformed field
encodings, and exercises the complete Hybrid-QASM-to-machine-code execution
path.
