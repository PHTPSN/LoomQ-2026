# OriginQ / pyQPanda Adapter Knowledge

## Pinned environment

- SDK: `pyqpanda==3.8.5`
- Interpreter: Python 3.10
- Local environment: `.venv-originq`
- Locked dependencies: `requirements/originq.lock.txt`
- Credential-free backend: `CPUQVM`

## QASM execution path

```python
import pyqpanda as pq

machine = pq.CPUQVM()
machine.init_qvm()
try:
    prog, qreg, creg = pq.convert_qasm_string_to_qprog(qasm_str, machine)
    counts = machine.run_with_configuration(prog, creg, shots)
finally:
    machine.finalize()
```

The pinned SDK also exposes file-based `convert_qasm_to_qprog`. Prefer the string function when available and keep a file-based compatibility path isolated behind an adapter.

## OriginIR execution path

The installed function name is `convert_originir_str_to_qprog`, not `convert_originir_string_to_qprog`:

```python
prog, qreg, creg = pq.convert_originir_str_to_qprog(originir, machine)
counts = machine.run_with_configuration(prog, creg, shots)
```

Always call `finalize()` in `finally`, including after parse or execution errors.

## Translation profiles

The formal LoomQ contract accepts the OriginIR names documented in `../target_ir_contract.md`. The pinned pyQPanda parser has narrower local behavior, so the local-runner profile uses:

| Source gate | Local OriginIR |
|---|---|
| `h` | `H` |
| `x` | `X` |
| `s` | `S` |
| `sdg` | `RZ q[k],(-1.5707963267948966)` |
| `t` | `T` |
| `tdg` | `RZ q[k],(-0.7853981633974483)` |
| `rz(θ)` | `RZ q[k],(θ)` |
| `ry(θ)` | `RY q[k],(θ)` |
| `cx` | `CNOT` |
| `cu1(θ)` | `CR q[a],q[b],(θ)` |
| `swap` | `SWAP` |
| `ccx` | `TOFFOLI` |

`sdg` and `tdg` lowerings are equivalent up to global phase. `CR` is the locally verified spelling for the controlled phase operation represented by source `cu1`.

The complete lowered matrix was parsed and executed successfully with pyQPanda 3.8.5 CPUQVM on 2026-08-22.

## Counts pitfall

pyQPanda returns bit-string keys in the tested path. A string such as `"11"` is already binary and must remain `"11"`; converting `int("11")` to binary would incorrectly produce `"1011"`. Only actual integer keys should be interpreted as decimal state indices.

## Out of scope until explicitly implemented

- Origin Quantum cloud authentication and Wukong job submission;
- API Token storage;
- hardware job submission and account quota management;
- QPanda3 migration.

Keep cloud credentials outside the repository and consult the current official documentation before enabling hardware execution.

## Read-only cloud discovery

The current official QPanda3 cloud interface supports authenticated backend
discovery without submitting a task:

```python
from pyqpanda3.qcloud import QCloudService

service = QCloudService(api_key=api_key)
availability = service.backends()
```

The returned mapping uses backend names as keys and booleans as current
availability values. Official examples currently include `WK_C180` and older
or maintenance backends. This live inventory is intentionally separate from
LoomQ's frozen `originq_wukong` scoring record.

Use `scripts/backend_observations.py --provider originq` for a redacted,
timestamped report. It reads `ORIGINQ_API_KEY` or `QPANDA3_API_KEY`, does not
print the key, and never submits a quantum job.
