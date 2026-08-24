# LoomQ Development Environment

## Runtime layout

The compiler and repository tests use Python 3.10 with Qiskit's maintained OpenQASM 2 parser in `.venv`. Each vendor SDK has an isolated environment because their numerical and parser dependencies are not safely interchangeable:

| Environment | Purpose | Direct dependency |
|---|---|---|
| `.venv` | Compiler core, submission tools, and repository tests | `starter_kit/requirements.txt` |
| `.venv-spinq` | SpinQit compiler and local simulator | `spinqit==0.2.4` |
| `.venv-originq` | pyQPanda and CPUQVM | `pyqpanda==3.8.5` |
| `.venv-braket` | Amazon Braket OpenQASM 3 and LocalSimulator | `amazon-braket-sdk==1.110.1` |

The short files under `requirements/` record direct SDK choices. The corresponding `*.lock.txt` files freeze every resolved package used by the reproducible setup script.

`adapter.run()` discovers these environments automatically. CI or another installation layout can override the interpreters with `LOOMQ_SPINQ_PYTHON`, `LOOMQ_ORIGINQ_PYTHON`, and `LOOMQ_BRAKET_PYTHON`.

## Core setup and activation

From the repository root in PowerShell:

```powershell
.\scripts\setup.ps1
.\scripts\activate.ps1
```

`setup.ps1` installs both the core and all three isolated backend environments.
It validates the actual `python.exe` inside each environment, so an empty or
interrupted `.venv-*` directory is repaired instead of being accepted as ready.
It also runs one local shot through every vendor SDK before reporting success.

To set up if necessary and start the browser workspace with one command:

```powershell
.\scripts\start-ui.ps1
```

Use `setup.ps1 -SkipBackends` only for compiler-only development where the
three local vendor simulators are intentionally unnecessary.

Activation loads local variables from `.env`. The file is ignored by Git. `.env.example` is the safe template committed to the repository.

## DeepSeek configuration

The local `.env` is prepared with the formal model configuration, but the API key is intentionally blank:

```text
LOOMQ_LLM_BASE_URL=https://api.deepseek.com
LOOMQ_LLM_API_KEY=
LOOMQ_LLM_MODEL=deepseek-v4-flash
LOOMQ_LLM_TIMEOUT_SECONDS=120
```

Ask the user to fill `LOOMQ_LLM_API_KEY` immediately before an L2 model call is required. Never print, log, or commit the value.

## Backend setup

Install or refresh every isolated backend environment:

```powershell
.\scripts\setup-backends.ps1 -Backend all
```

The backend installer is idempotent: it can be rerun after an interrupted
download or a damaged environment. It finishes by running
`scripts/check-backends.py` through the core Python environment.

Install only selected environments:

```powershell
.\scripts\setup-backends.ps1 -Backend spinq,originq
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
$env:LOOMQ_RUN_SDK_TESTS = "1"
.\.venv\Scripts\python.exe -m unittest tests.test_l1_sdk_integration -v
.\.venv\Scripts\python.exe starter_kit\evaluator.py --level l1 --target spinq,originq,braket
.\.venv-spinq\Scripts\python.exe starter_kit\examples\run_spinq.py
.\.venv-originq\Scripts\python.exe starter_kit\examples\run_originq.py
.\.venv-braket\Scripts\python.exe starter_kit\examples\run_braket.py
```

The repository also includes `starter_kit/Dockerfile` for the official Linux/Python 3.10 baseline. It creates three isolated SDK environments under `/opt/loomq-backends/` from the locks shipped inside `starter_kit/backend_requirements/`. The SpinQ environment uses PyTorch's exact CPU wheel (`torch==2.13.0+cpu`) to avoid bundling unused CUDA libraries. Docker is not required for local compiler development, but the final submission should be built and tested with that file on a machine where Docker is available.

The competition-shaped L1 acceptance suite covers Bell, GHZ-3, GHZ-5, QFT-4,
Grover-3, and three seeded random circuits. It validates all three exact target-IR
artifacts, runs the real SDKs with the official 8192 shots and 0.97 fidelity
threshold, and enforces the complete normalized result contract. Run it in the
offline judging profile from the repository root:

```powershell
docker build -t loomq-submission:l1 starter_kit
docker run --rm --network none `
  -e LOOMQ_RUN_SDK_TESTS=1 `
  --mount type=bind,source=${PWD},target=/workspace/repo,readonly `
  -w /workspace/repo loomq-submission:l1 `
  python -m unittest tests.test_l1_acceptance -v
```
