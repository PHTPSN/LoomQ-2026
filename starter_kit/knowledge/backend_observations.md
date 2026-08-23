# Backend Knowledge and Live Observations

LoomQ uses two deliberately separate data layers.

## 1. Formal L2 baseline

`../backend_capabilities.json` is the sole source for automatic L2 scoring. It
is a competition snapshot, not a claim about current vendor inventory. Never
rewrite it from a network response.

## 2. Advisory live observations

`scripts/backend_observations.py` performs read-only discovery for an
interactive product or development review. Every report is timestamped and
marked `advisory_only`. Reports should normally be written under `.cache/`,
which is ignored by Git:

```powershell
py -m pip install -r requirements/backend-observations.lock.txt
py scripts/backend_observations.py --provider all `
  --output .cache/loomq/backend-observations.json
```

If credentials are absent, the report records `authentication_required`
instead of failing the formal agent path.

### Origin Quantum

Public manuals require no login. Live backend discovery uses the official
`pyqpanda3.qcloud.QCloudService.backends()` call and requires an API key from
the user's Origin Quantum account. The helper reads `ORIGINQ_API_KEY`, falling
back to the official ecosystem name `QPANDA3_API_KEY`. It never submits a job.

The current Origin Quantum documentation lists backends newer than the LoomQ
snapshot, including `WK_C180`. This is expected: the live layer can explain a
current option to a user, while the formal answer must still use the canonical
LoomQ backend IDs.

The observation environment pins `pyqpanda3==0.4.0`; this does not replace the
separate `pyqpanda==3.8.5` environment used to verify the L1 adapter.

### AWS Braket

Device documentation and pricing are public. Current status, capabilities, and
queue depth are available through the official `SearchDevices` and `GetDevice`
APIs. They require an AWS credential profile and the following least-privilege
IAM actions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["braket:SearchDevices", "braket:GetDevice"],
      "Resource": "*"
    }
  ]
}
```

Use a named profile where possible:

```powershell
$env:AWS_PROFILE = "loomq-readonly"
py scripts/backend_observations.py --provider aws
```

The collector does not call `CreateQuantumTask`, create S3 resources, make a
reservation, or change spending limits. Running a real circuit remains a
separate, explicit, potentially chargeable operation.

## Refresh and promotion policy

1. Run the observation collector manually or on a development machine's
   schedule; never run it inside formal evaluation.
2. Treat failures and stale data as `unknown`, not as proof that a device is
   offline.
3. Compare observations with official public documentation.
4. If a durable change affects product guidance, update `backend_sources.json`,
   `sources.lock.json`, and the relevant SDK note in one reviewed commit.
5. Change the competition baseline only when the organizers publish a new
   contract or capability snapshot.
