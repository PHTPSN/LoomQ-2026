# Amazon Braket Adapter Knowledge

## Pinned environment

- SDK: `amazon-braket-sdk==1.110.1`
- Default simulator: `amazon-braket-default-simulator==1.33.0`
- Interpreter: Python 3.10
- Local environment: `.venv-braket`
- Locked dependencies: `requirements/braket.lock.txt`
- Credential-free backend: `LocalSimulator`

## Local execution path

```python
from braket.devices import LocalSimulator
from braket.ir.openqasm import Program

device = LocalSimulator()
task = device.run(Program(source=qasm3_source), shots=shots)
result = task.result()
counts = dict(result.measurement_counts)
job_id = result.task_metadata.id
```

LocalSimulator does not require AWS credentials or an S3 output location.

## Locally verified OpenQASM 3 profile

Use the Braket-native gate names verified with the pinned default simulator:

| Source gate | Braket OpenQASM 3 |
|---|---|
| `h` | `h` |
| `x` | `x` |
| `s` | `s` |
| `sdg` | `si` |
| `t` | `t` |
| `tdg` | `ti` |
| `rz(θ)` | `rz(θ)` |
| `ry(θ)` | `ry(θ)` |
| `cx` | `cnot` |
| `cu1(θ)` | `cphaseshift(θ)` |
| `swap` | `swap` |
| `ccx` | `ccnot` |

Emit declarations and measurement as:

```qasm
OPENQASM 3.0;
qubit[2] q;
bit[2] c;
c = measure q;
```

The complete mapped gate matrix was executed successfully with 32 shots on 2026-08-22.

## `stdgates.inc` compatibility note

The competition target contract shows `include "stdgates.inc";`, and the OpenQASM standard defines that library. In the pinned local environment, default simulator 1.33.0 attempts to open the include as a filesystem file and raises `FileNotFoundError` when it is absent. The local-runner profile therefore:

- omits the include;
- uses Braket-native gate names;
- validates by executing the emitted program with LocalSimulator.

Keep this behavior in a versioned profile. Do not remove the formal-contract interpretation or assume every Braket service/device behaves identically to the pinned local parser.

## Result normalization

- Convert `measurement_counts` to a plain dictionary.
- Verify bit order with asymmetric test circuits before applying any reversal.
- Use `result.task_metadata.id` as the local task identifier.
- Generate a UTC timestamp at execution time; do not assume `additional_metadata.action.startTime` exists.

## Cloud execution boundary

AWS credentials are unnecessary for LocalSimulator. Cloud devices require separately authorized AWS configuration, service enablement, region selection, S3 output, and cost approval. Do not infer permission to submit paid cloud tasks from permission to run locally.

## Read-only cloud discovery

Amazon Braket provides stable official control-plane APIs for current device
information:

- `SearchDevices` lists device ARN, name, provider, type, and status;
- `GetDevice` returns status, capability JSON, and queue information;
- valid device states are `ONLINE`, `OFFLINE`, and `RETIRED`.

These calls still require AWS credentials. A least-privilege discovery identity
needs only `braket:SearchDevices` and `braket:GetDevice`; it does not need
`braket:CreateQuantumTask`. The standard Boto3 credential chain or a named
`AWS_PROFILE` should be used instead of storing keys in this repository.

Use `scripts/backend_observations.py --provider aws` to query every documented
Braket region and produce a timestamped advisory report. Pricing remains a
separate public source because it is not included in `GetDevice`.
