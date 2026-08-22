# LoomQ OpenQASM 2.0 Source Subset

## Scope

LoomQ accepts a deliberately bounded OpenQASM 2.0 source language. The compiler must implement this subset completely and reject unsupported constructs explicitly. It must not attempt to support arbitrary OpenQASM 2.0 by string replacement.

The authoritative machine grammar is `spec/qasm2_subset.ebnf`. The official OpenQASM 2.0 specification remains the semantic reference for shared constructs, but the competition subset is narrower.

## Lexical rules

- The language is case-sensitive.
- Whitespace may appear between tokens.
- `//` starts a comment that ends at the next newline.
- Statements end with `;`.
- Identifiers start with a lowercase ASCII letter and continue with letters, digits, or `_`.
- Numeric expressions may contain integer or decimal literals, `pi`, parentheses, unary `+`/`-`, arithmetic `+ - * / ^`, and the standard functions `sin`, `cos`, `tan`, `exp`, `ln`, and `sqrt`.
- Evaluate expressions with a dedicated expression parser. Never pass source text to Python `eval()`.

## Required program structure

1. The first non-comment statement is exactly `OPENQASM 2.0;`.
2. `include "qelib1.inc";` is required and is the only accepted include.
3. One or more `qreg` declarations define quantum registers.
4. One or more `creg` declarations define classical registers used by measurement.
5. Gate and measurement statements follow the declarations.

Declarations must have unique names and positive sizes. All indexed operands must be in range.

## Supported gates

The complete input whitelist is:

| Gate | Parameters | Qubits |
|---|---:|---:|
| `h` | 0 | 1 |
| `x` | 0 | 1 |
| `s` | 0 | 1 |
| `sdg` | 0 | 1 |
| `t` | 0 | 1 |
| `tdg` | 0 | 1 |
| `rz` | 1 | 1 |
| `ry` | 1 | 1 |
| `cx` | 0 | 2 |
| `cu1` | 1 | 2 |
| `swap` | 0 | 2 |
| `ccx` | 0 | 3 |

Gate names are accepted only in the canonical lowercase form above. Parameter and operand arity must match `spec/gates.json` exactly.

## Measurement

Both forms are accepted:

```qasm
measure q[0] -> c[0];
measure q -> c;
```

Whole-register measurement requires equal quantum and classical register sizes and expands deterministically into indexed measurements.

## Unsupported source constructs

Reject these with a source location and a specific diagnostic:

- custom `gate` declarations;
- `opaque` declarations;
- built-in `U` or `CX` spellings outside the LoomQ lowercase whitelist;
- `reset`, `barrier`, and `if`;
- classical arithmetic or feedback outside L3 `classical { ... }` blocks;
- includes other than `qelib1.inc`;
- any gate outside the 12-gate whitelist;
- undeclared registers, duplicate declarations, invalid sizes, out-of-range indices, or wrong arity.

L3 Hybrid-QASM parsing is a separate layer. It must extract the competition-defined `classical` block before the remaining quantum source is validated as this subset.

## Canonical circuit

The strict parser is converted into structured, register-independent nodes rather than edited source strings:

```text
LoomQCircuit(num_qubits, num_clbits, instructions)
Gate(name, numeric_parameters, flattened_qubit_indices)
Measure(flattened_qubit_index, flattened_classical_index)
```

The parser reports source locations for syntax and symbol errors. Whole-register measurement is normalized into ordered indexed `Measure` nodes before canonical validation.

## Acceptance criteria

The parser is complete for LoomQ when it:

- accepts formatting and comment variations without changing semantics;
- accepts every whitelist gate with valid arity;
- handles safe parameter expressions consistently;
- rejects every unsupported construct explicitly;
- never silently drops a statement;
- round-trips the canonical AST through each target emitter and passes semantic-equivalence tests.
