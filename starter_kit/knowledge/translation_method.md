# LoomQ Translation Method

## Required architecture

Use a small deterministic compiler pipeline:

```text
OpenQASM 2.0 source
  -> Qiskit qasm2 strict parser
  -> whitelist and arity validation
  -> canonical LoomQCircuit
  -> target-specific lowering
  -> target emitter
  -> target parser or SDK runner
  -> result normalization
```

Do not implement translation as regular-expression replacement, prompt-only generation, or independent hard-coded circuits per backend.

## Phase responsibilities

### Parse

The pinned frontend is `qiskit==2.5.2` using `qasm2.loads(..., strict=True)`. Use `LEGACY_INCLUDE_PATH` and `LEGACY_CUSTOM_INSTRUCTIONS` so the complete Qiskit `qelib1.inc` definitions, including `swap` and `cu1`, are available. The strict parser supplies syntax diagnostics; parsing does not call a vendor SDK. `spec/qasm2_subset.ebnf` remains the competition boundary and review checklist.

### Semantic validation

Qiskit resolves declarations, register references, bounds, expression values, and whole-register expansion. The frontend must then reject every parsed operation outside the 12-gate whitelist and recheck parameter arity, qubit arity, finite numeric parameters, distinct operands, and measurement shape before constructing canonical nodes. Qiskit is a parser dependency, not a substitute for the LoomQ subset validator.

### Canonicalization

- Convert Qiskit's expanded measurements into indexed measurements.
- Convert evaluated parameter expressions into finite numeric values.
- Normalize numeric output to a deterministic representation.
- Preserve operation order.
- Do not optimize away gates unless semantic equivalence is independently proven and tested.

### Target-specific lowering

Lower only when the target cannot consume a source operation directly. `spec/target_mappings.json` records the canonical mappings verified with the pinned SDKs. `../gate_identities.md` records approved semantic decompositions.

Important distinctions:

- The competition target contract is authoritative for formal output acceptance.
- A pinned vendor parser may support a narrower spelling. Use a local-runner profile when necessary, without changing the formal semantic contract.
- Global-phase-equivalent substitutions are allowed only where they preserve all measurement distributions, including later interference and controlled use.

### Emit

Emit complete target programs with declarations and measurement statements:

- `spinq`: OpenQASM 2.0.
- `originq`: the LoomQ OriginIR subset.
- `braket`: Braket-compatible OpenQASM 3.0.

The emitter must be a pure function of the validated AST and target profile. It must not contact a service or inspect live queue state.

### Execute

Keep SDK code in isolated runners. Import a vendor SDK lazily so a missing backend package cannot break parsing or another target. Local simulators require no credentials.

### Normalize results

Return the schema in `spec/result_schema.json` and enforce these invariants:

- `shots` is a positive integer;
- every `counts` value is a non-negative integer;
- every counts key is a zero-padded binary string of the classical-register width;
- the rightmost character is `c[0]`;
- the sum of counts equals `shots` for completed sampled execution;
- `bit_order` is exactly `"little"`;
- `timestamp` is UTC ISO 8601;
- secrets and raw credentials never appear in errors or metadata.

Treat a string key containing only `0` and `1` as an existing bit string. Do not reinterpret a key such as `"11"` as decimal eleven.

## Verified target mappings

The following compatibility behavior was executed locally on 2026-08-22 with the pinned environments:

- SpinQit 0.2.4 accepted the complete LoomQ OpenQASM 2.0 whitelist directly.
- SpinQit's complete-measurement counts use measurement-operation order rather than the competition's classical display order. The runner reconstructs classical bits from the canonical measurement map; partial-measurement keys that already have full classical width remain unchanged.
- pyQPanda 3.8.5 accepted OriginIR with `CR` for `cu1`; its parser required `sdg` and `tdg` to be lowered to negative `RZ` rotations for local execution.
- Amazon Braket SDK 1.110.1 with default simulator 1.33.0 accepted Braket-native `si`, `ti`, `cnot`, `cphaseshift`, and `ccnot` spellings.
- The pinned Braket local parser treated `include "stdgates.inc"` as a filesystem include. The local-runner profile therefore omits that include and uses native gate spellings. The competition contract remains authoritative for formal output acceptance.

## LLM boundary

An LLM may generate a candidate program, explain diagnostics, or propose a repair. Deterministic code must parse, validate, translate, execute, and compare semantics. The recommended L2 loop is:

```text
generate candidate -> validate -> transpile -> simulate -> diagnose -> repair
```

Stop retries within the published L2 timeout and call budget. Never let the model invent backend capability facts; load `../backend_capabilities.json`.

## Verification standard

At minimum, maintain:

- one positive and one negative parser case per syntax construct;
- every gate against every target mapping;
- whole-register and indexed measurement cases;
- boundary and failure cases for register sizes and indices;
- semantic-equivalence tests for gate decompositions;
- randomized valid circuits for each target;
- result-schema and bit-order tests;
- local SDK smoke tests using the pinned environments.

The implemented regression suites are `tests/test_l1_translation.py` and the opt-in real-SDK suite `tests/test_l1_sdk_integration.py`.
