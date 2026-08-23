# SpinQ Cloud real-hardware evidence

This optional workflow is separate from the formal `adapter.transpile()` and
`adapter.run()` paths. It prepares the public Bell circuit for SpinQ Cloud,
where active qubits are measured automatically and the MCP submission tool
rejects explicit `measure` statements.

## 1. Refresh live capabilities without creating a task

Call the SpinQ MCP `get_platforms` tool. Select an active real platform with at
least one online machine and save the selected record as
`starter_kit/evidence/files/spinq-bell/spinq-bell-gemini-preflight.json`. Availability and
capabilities are dynamic; do not reuse an old snapshot without refreshing it.

## 2. Prepare the exact cloud artifact offline

From the repository root in PowerShell:

```powershell
docker run --rm --network none `
  --mount type=bind,source=${PWD},target=/workspace/repo `
  -w /workspace/repo loomq-submission:l1 `
  python -m starter_kit.hardware.spinq_cloud `
    --source starter_kit/circuits/bell.qasm `
    --platforms-json starter_kit/evidence/files/spinq-bell/spinq-bell-gemini-preflight.json `
    --platform gemini_vp `
    --out starter_kit/evidence/files/spinq-bell/spinq-bell-executed.qasm
```

Inspect the output before submission. It must contain one `qreg`, `h`, and
`cx`, but no `creg`, `measure`, comments, credentials, or unrelated circuit.

## 3. Submit exactly one real-machine task

Use the SpinQ MCP `qasm_submit` tool with:

```text
platform_code: gemini_vp
task_name: loomq-l1-bell-20260823
qasm_str: exact contents of evidence/files/spinq-bell/spinq-bell-executed.qasm
```

Submission may consume quota and therefore requires explicit human approval.
The current MCP interface does not expose a shots argument; record the actual
shot count reported by SpinQ rather than assuming a value.

Immediately save the returned task ID. Do not submit a second task merely
because the first result is still pending.

## 4. Retrieve and preserve the result

Use `get_task_result_by_id` with the saved task ID. Preserve the raw response as
`starter_kit/evidence/files/spinq-bell/spinq-bell-sdk-result.json`, then create a normalized
result following `starter_kit/knowledge/spec/result_schema.json`.

For Bell, the dominant states should be `00` and `11`. Hardware noise may add
other states, so report the observed distribution rather than editing it.

Finally, save a task-page screenshot as
`starter_kit/evidence/files/spinq-bell/spinq-bell-task.png`. The evidence entry must identify
the platform, task ID, execution time, actual shots, submitted QASM, raw result,
normalized result, and screenshot. Never include the username, private-key
path, private key, browser cookie, or other account information.
