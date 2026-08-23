# SpinQit Adapter Knowledge

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

## Result normalization

- Convert keys to strings without decimal reinterpretation.
- Zero-pad to the classical-register width when necessary.
- Confirm the rightmost character represents `c[0]` with targeted tests.
- Use a stable local job identifier without claiming it is a cloud job.
- Generate the timestamp at execution time in UTC.

## Out of scope until explicitly implemented

- SpinQ Cloud authentication and hardware job submission;
- account provisioning or private-key handling;
- live queue, pricing, or hardware-capability discovery;
- relying on a remote compiler during formal L1 evaluation.

Consult `WEB_LINKS.md` before adding cloud support, and keep credentials only in ignored environment variables.

## Development-only visitor access

SpinQ Cloud's web client was inspected and directly verified on 2026-08-24.
Visitor Login does not require browser automation:

- method: `POST`;
- URL: `https://cloud.spinq.cn/prod/api/user/loginAsVisitor`;
- request body: none;
- useful request headers: `Accept: application/json` and `lang: en`;
- response fields: `status`, `msg`, `token`, `name`, and `hasPassword`;
- follow-up web API authentication: request header `token: <temporary-token>`.

Run `python scripts/spinq_visitor.py` to verify the flow. Its CLI output is
redacted by default; Python callers can import `create_visitor_session()` and
keep the token in memory. Do not commit, print, or cache a returned token.

This is an observed internal web endpoint, not a documented stable public API.
It may change without notice. It is suitable for development-time access to
visitor-permitted resources only; it does not grant real-machine execution,
and it must never replace `backend_capabilities.json` during L2 evaluation.
