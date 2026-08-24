"""Launch target SDKs in isolated Python environments."""

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict

from .emitters import emit_local_target
from .model import LoomQCircuit


BACKEND_ENVIRONMENT = {
    "spinq": "LOOMQ_SPINQ_PYTHON",
    "originq": "LOOMQ_ORIGINQ_PYTHON",
    "braket": "LOOMQ_BRAKET_PYTHON",
}


def _backend_python(target: str) -> str:
    configured = os.environ.get(BACKEND_ENVIRONMENT[target])
    if configured:
        path = Path(configured).expanduser()
        if not path.is_file():
            raise RuntimeError("configured %s does not exist" % BACKEND_ENVIRONMENT[target])
        return str(path)

    repository_root = Path(__file__).resolve().parents[2]
    if os.name == "nt":
        candidates = (
            repository_root / (".venv-" + target) / "Scripts" / "python.exe",
        )
    else:
        candidates = (
            repository_root / (".venv-" + target) / "bin" / "python",
            Path("/opt/loomq-backends") / target / "bin" / "python",
        )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def run_isolated(circuit: LoomQCircuit, target: str, shots: int) -> Dict[str, Any]:
    worker = Path(__file__).with_name("sdk_worker.py")
    payload = {
        "target": target,
        "source": emit_local_target(circuit, target),
        "shots": shots,
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "measurements": [
            {"qubit": item.qubit, "clbit": item.clbit} for item in circuit.measurements
        ],
    }
    completed = subprocess.run(
        [_backend_python(target), str(worker)],
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no diagnostic output"
        raise RuntimeError("%s SDK worker failed: %s" % (target, detail))
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("%s SDK worker returned no result" % target)
    try:
        result = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise RuntimeError("%s SDK worker returned invalid JSON" % target) from exc
    if sum(result.get("counts", {}).values()) != shots:
        raise RuntimeError("%s SDK counts do not sum to shots" % target)
    return result
