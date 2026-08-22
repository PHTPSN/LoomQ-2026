# LoomQ Compiler Knowledge Base

This directory contains the bounded, versioned knowledge used to implement and review the LoomQ compiler and backend adapters. It is intentionally smaller than the complete OpenQASM and vendor SDK documentation.

## Authority order

1. LoomQ competition contracts in `../target_ir_contract.md`, `../submission.yaml`, `../l2_policy.json`, and `../backend_capabilities.json`.
2. Machine-readable rules under `spec/`.
3. The explanatory documents in this directory.
4. Primary language and vendor sources indexed by `WEB_LINKS.md` and recorded in `sources.lock.json`.
5. Context7 or other retrieval output, which is advisory until verified against a pinned local SDK and converted into a test.

If two layers disagree, preserve the higher-priority contract, document the discrepancy, and add an executable regression test.

## Reading routes

| Work | Read first | Then use |
|---|---|---|
| Parse or validate source QASM | `qasm2_subset.md` | `spec/qasm2_subset.ebnf`, `spec/gates.json` |
| Design or review translation | `translation_method.md` | `spec/target_mappings.json`, `../gate_identities.md` |
| Integrate SpinQit | `sdk_spinq.md` | `.venv-spinq`, `../examples/run_spinq.py` |
| Integrate pyQPanda / OriginIR | `sdk_originq.md` | `.venv-originq`, `../examples/run_originq.py` |
| Integrate Amazon Braket | `sdk_braket.md` | `.venv-braket`, `../examples/run_braket.py` |
| Normalize execution results | `translation_method.md` | `spec/result_schema.json`, `../QUANTUM_101.md` |
| Refresh technical references | `WEB_LINKS.md` | `sources.lock.json`, pinned requirement locks, executable tests |

## Runtime rule

Formal evaluation must not need web access, Context7, or a documentation service. Runtime decisions must come from local versioned files. External retrieval is only a development aid for reviewing or refreshing those files.

## Update workflow

1. Identify the contract or SDK behavior being changed.
2. Read the relevant primary source from `WEB_LINKS.md`.
3. Verify the behavior against the pinned environment from `DEVELOPMENT.md`.
4. Update the explanatory document and machine-readable specification together.
5. Add or update a deterministic test.
6. Update `sources.lock.json` when a source, version, or retrieval date changes.
