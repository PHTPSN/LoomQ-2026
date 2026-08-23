"""Launch the Origin Quantum SDK in its isolated Python environment."""

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict

from .emitters import emit_local_target
from .model import LoomQCircuit


def _originq_python() -> str:
    configured = os.environ.get("LOOMQ_ORIGINQ_PYTHON")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_file():
            raise RuntimeError("configured LOOMQ_ORIGINQ_PYTHON does not exist")
        return str(path)

    repository_root = Path(__file__).resolve().parents[2]
    if os.name == "nt":
        candidates = (repository_root / ".venv-originq" / "Scripts" / "python.exe",)
    else:
        candidates = (
            repository_root / ".venv-originq" / "bin" / "python",
            Path("/opt/loomq-backends/originq/bin/python"),
        )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def run_originq_isolated(circuit: LoomQCircuit, shots: int) -> Dict[str, Any]:
    worker = Path(__file__).with_name("originq_worker.py")
    payload = {
        "source": emit_local_target(circuit, "originq"),
        "shots": shots,
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
    }
    completed = subprocess.run(
        [_originq_python(), str(worker)],
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no diagnostic output"
        raise RuntimeError("originq SDK worker failed: %s" % detail)
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("originq SDK worker returned no result")
    try:
        result = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise RuntimeError("originq SDK worker returned invalid JSON") from exc
    if sum(result.get("counts", {}).values()) != shots:
        raise RuntimeError("originq SDK counts do not sum to shots")
    return result
