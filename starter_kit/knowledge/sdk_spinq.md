# SpinQ Adapter Knowledge

## Keep the three SpinQ profiles separate

| Profile | Purpose | Authority | Measurement rule |
|---|---|---|---|
| LoomQ L1 `spinq` output | Formal translation artifact | `starter_kit/target_ir_contract.md` | Emit complete OpenQASM 2.0, including declarations and measurements. |
| SpinQit 0.2.4 BasicSimulator | Credential-free local verification | Pinned SDK and executable tests | Consume the formal artifact unchanged. |
| SpinQ Cloud hardware | Optional real-machine validation | Authenticated cloud documentation plus live `get_platforms` results | Remove explicit measurements only in the cloud-submission adapter; the platform measures active qubits automatically. |

Do not weaken the formal L1 emitter to accommodate the cloud submission API. A cloud adapter is a deployment boundary: it derives a hardware submission program from the already validated canonical circuit, checks the selected live platform, and preserves the formal translator as a pure function.

## Pinned environment

- SDK: `spinqit==0.2.4`
- Interpreter: Python 3.10
- Local environment: `.venv-spinq`
- Locked dependencies: `requirements/spinq.lock.txt`
- Credential-free backend: BasicSimulator

## Supported LoomQ path

SpinQit accepts complete OpenQASM 2.0 through its QASM compiler. The installed compiler expects a file path, so a string-based adapter should write the validated source to a secure temporary `.qasm` file, compile it, and remove the file in a `finally` block.

```python
from spinqit import BasicSimulatorConfig, get_basic_simulator, get_compiler

compiler = get_compiler("qasm")
ir = compiler.compile(qasm_path, 0)

config = BasicSimulatorConfig()
config.configure_shots(shots)
result = get_basic_simulator().execute(ir, config)
counts = result.counts
```

Do not use the mock fallback from the public example in scoring code. A missing SDK, compile failure, or execution failure must produce a clear error.

## Translation profile

- Output language: complete OpenQASM 2.0.
- Header: `OPENQASM 2.0;`.
- Include: `include "qelib1.inc";`.
- Gate names: preserve the 12 canonical lowercase source names.
- Measurement: preserve indexed measurement or emit an equivalent whole-register measurement.

The complete 12-gate whitelist was compiled and executed successfully with SpinQit 0.2.4 BasicSimulator on 2026-08-22.

## SpinQ Cloud QASM profile

The authenticated QASM Editor documentation describes an OpenQASM 2.0-derived interface with these restrictions:

- require `OPENQASM 2.0;` and use only `include "qelib1.inc";`;
- declare at most one quantum register, sized no larger than the selected platform;
- user-defined gates, `opaque`, control flow, and `reset` are unsupported;
- classical-register declarations are ignored by the web editor;
- explicit measurement is unnecessary because the platform automatically measures every active qubit after the final gate;
- the MCP `qasm_submit` interface currently rejects a program containing `measure`, so a hardware-submission adapter must omit it;
- two-qubit operations must follow the live platform coupling graph;
- rotation expressions are limited to real values, `pi`, and explicit arithmetic; only the two-qubit NMR platform documents arbitrary `rx`, `ry`, and `rz` angles;
- the web editor uses a nonstandard barrier form whose first argument is a depth value. Do not emit it from the formal translator.

An **active qubit** is a qubit touched by at least one gate. Cloud documentation warns that unused or skipped qubits may not produce measurement results, so hardware evidence should avoid sparse layouts unless the exact mapping has been verified.

### Live capability discovery

Query `get_platforms` immediately before preparing a hardware task. Platform availability, gate spelling, topology, and online machine count are dynamic and must not be inferred from the older static tables in the documentation.

Observed on 2026-08-23:

| Platform ID | Technology | Qubits | Online machines | Relevant native capabilities |
|---|---:|---:|---:|---|
| `gemini_vp` | NMR | 2 | 1 | `H`, `X`, `Rx`, `Ry`, `Rz`, `CNOT`, `U`, barriers, and fixed-axis rotations; bidirectional coupling between qubits 1 and 2. |
| `triangulum_vp` | NMR | 3 | 0 | Includes `CNOT` and `CCNOT`; all-to-all connectivity in the returned topology. |
| `hercules_vp` | NMR | 5 | 0 | Includes `CNOT` and `CCNOT`; all-to-all connectivity in the returned topology. |
| `superconductor_vp` | Superconducting | 8 | 0 | Includes `CZ` but not `CNOT` in the returned gate list; nearest-neighbor line topology. |

This is a dated observation, not a stable compatibility promise. For example, the authenticated documentation still refers to four- and six-qubit NMR machines while live discovery returned three- and five-qubit machines.

### Hardware submission checklist

1. Parse and validate the source with the normal LoomQ frontend.
2. Select a platform returned by `get_platforms`; confirm that a machine is online.
3. Validate qubit count, every native or lowered gate, parameter restrictions, and every two-qubit edge against the selected platform.
4. Derive cloud QASM with one quantum register and no explicit `measure` statement.
5. Submit only after human approval because a submission may consume quota or create a queued task.
6. Record task ID, platform ID, shots, submitted QASM, result counts or probabilities, timestamps, and screenshots according to the competition evidence format.
7. Compare the normalized hardware distribution with the canonical expected distribution; keep raw vendor output as evidence.

SpinQ's authenticated documentation explains task execution and result export but does not publish billing, price, free-quota, or shot-cost rules. Treat cost as unknown and check the account UI before each real-machine submission.

### Observed Gemini hardware diagnostics

Three deterministic 1,000-shot diagnostics were executed on `gemini_vp` on
2026-08-23 after the Bell result showed a large wrong-parity component:

- `x q[0]; x q[1];` returned a uniform 25% distribution instead of deterministic `11`;
- `x q[0]; cx q[0],q[1];` returned `11` as the dominant state at 72.39%;
- `x q[1]; cx q[1],q[0];` returned `11` as the dominant state at 67.04%.

These observations rule out a simple CNOT-operand reversal and show that the
anomaly is present before any CNOT or superposition in the X-only baseline.
They localize the discrepancy after LoomQ's emitted QASM, but do not distinguish
SpinQ cloud compilation or scheduling from NMR state preparation, calibration,
measurement, or result reconstruction. The raw evidence and exact programs are
indexed in `../evidence/files/spinq-diagnostics/spinq-diagnostics-report.json`.

## Cloud MCP environment

- Package documented by SpinQ: `spinqit_mcp_tools`.
- Required Python: 3.10 or newer.
- Server module: `python -m spinqit_mcp_tools.qasm_submitter`.
- Authentication variables: `PRIVATEKEYPATH` and `SPINQCLOUDUSERNAME`.
- The matching public key must be registered in SpinQ Cloud Account Settings.

Keep the private key outside the repository. Never print environment variables, serialize credentials into evidence, or enable an environment-inspection tool. A successful SSH/MCP login proves only authentication; it does not prove that a submitted circuit satisfies a machine's current capabilities.

## Result normalization

- Convert keys to strings without decimal reinterpretation.
- Zero-pad to the classical-register width when necessary.
- Confirm the rightmost character represents `c[0]` with targeted tests.
- Use a stable local job identifier without claiming it is a cloud job.
- Generate the timestamp at execution time in UTC.

## Not part of the formal L1 translator

- cloud-specific removal of measurements;
- live platform selection, topology routing, and native-gate lowering;
- account provisioning, private-key handling, and billing discovery;
- relying on a remote compiler during formal L1 evaluation.

These belong in an explicitly named cloud execution adapter, not in `transpile(qasm_str, "spinq")`. Consult `WEB_LINKS.md` before refreshing cloud behavior, and keep credentials only in ignored environment variables.
