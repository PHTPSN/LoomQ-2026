# Real-hardware evidence workflows

- Origin Quantum: continue with this document.
- SpinQ Cloud: follow [`SPINQ.md`](SPINQ.md).

## Origin Quantum

This optional workflow is separate from `adapter.run()` and is never used by
the offline automatic evaluator. It submits the public Bell circuit to an
Origin Quantum real chip and stores the task ID before polling.

## Credential

Put the token in the ignored repository-root `.env`; never commit it:

```text
LOOMQ_ORIGINQ_API_TOKEN=<fill locally>
LOOMQ_ORIGINQ_BACKEND=WK_C180
```

Use the current **API token** from the
[Origin Quantum account center](https://account.originqc.com.cn/), not a web
login password, browser cookie, page URL, or a token issued for another
Origin Quantum product. A successful website login alone does not authorize
the SDK.

`WK_C180` is the backend identifier shown for the online Origin Wukong 180
device. The hardware workflow uses the current, isolated `pyqpanda3==0.4.0`
SDK; it does not alter the pinned legacy pyQPanda environment used for formal
offline L1 evaluation.

Build the hardware-only image once:

```powershell
docker build -f starter_kit/hardware/Dockerfile.originq `
  -t loomq-originq-hardware:0.4.0 .
```

## 1. Prepare the exact executed artifact offline

From the repository root in PowerShell:

```powershell
docker run --rm --network none `
  --mount type=bind,source=${PWD},target=/workspace/repo `
  -w /workspace/repo loomq-submission:l1 `
  python starter_kit/hardware/originq_hardware.py prepare
```

Inspect `starter_kit/evidence/files/originq-bell/originq-bell-executed.originir` before any
real submission.

## 2. Check credentials and availability without consuming quota

```powershell
docker run --rm --env-file .env `
  --mount type=bind,source=${PWD},target=/workspace/repo `
  loomq-originq-hardware:0.4.0 preflight
```

This only queries the account's backend list; it does not create a task.

## 3. Submit exactly one real-chip task

This command consumes the account's real-hardware quota. It requires the
explicit confirmation flag and refuses to overwrite an existing task record:

```powershell
docker run --rm --env-file .env `
  --mount type=bind,source=${PWD},target=/workspace/repo `
  loomq-originq-hardware:0.4.0 submit --confirm-real-hardware
```

The task ID is immediately written to
`starter_kit/evidence/files/originq-bell/originq-bell-task.json`.

## 4. Poll safely by saved task ID

```powershell
docker run --rm --env-file .env `
  --mount type=bind,source=${PWD},target=/workspace/repo `
  loomq-originq-hardware:0.4.0 poll --wait
```

The collector preserves the exact SDK-returned status and result in
`originq-bell-sdk-result.json`, then creates
`originq-bell-normalized-result.json`. For
Bell, `meta.top_k_bell_pass` must be `true`; the two largest counts must be
`00` and `11`.

Finally, download or screenshot the Origin Quantum workbench task page showing
the real device, task ID, platform execution time, shots, and completion status.
Store it as `starter_kit/evidence/files/originq-bell/originq-bell-task.png`, then fill the L1
hardware section in `starter_kit/evidence/README.md`. The screenshot supplies
the provider-side timestamp that the SDK result does not expose.

## Optional GHZ-3 evidence profile

The same safety workflow supports the second public circuit without
overwriting Bell evidence. Add `--profile ghz3` to the `prepare`, `submit`, and
`poll` commands. The GHZ-3 files use the `originq-ghz3-*` prefix. For example:

```powershell
docker run --rm --network none `
  --mount type=bind,source=${PWD},target=/workspace/repo `
  -w /workspace/repo loomq-submission:l1 `
  python starter_kit/hardware/originq_hardware.py prepare --profile ghz3

docker run --rm --env-file .env `
  --mount type=bind,source=${PWD},target=/workspace/repo `
  loomq-originq-hardware:0.4.0 submit --profile ghz3 `
    --shots 512 --confirm-real-hardware

docker run --rm --env-file .env `
  --mount type=bind,source=${PWD},target=/workspace/repo `
  loomq-originq-hardware:0.4.0 poll --profile ghz3 --wait
```
