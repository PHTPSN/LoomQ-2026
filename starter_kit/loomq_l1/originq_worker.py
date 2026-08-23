#!/usr/bin/env python3
"""Origin Quantum SDK worker for the isolated pyQPanda environment."""

from collections import Counter
from datetime import datetime, timezone
import json
import sys
import uuid


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _key(value, width: int) -> str:
    if isinstance(value, int):
        return format(value, "0%db" % width)
    text = str(value).replace(" ", "")
    if text and not (set(text) - {"0", "1"}):
        return text.zfill(width)
    if text.isdigit():
        return format(int(text), "0%db" % width)
    raise ValueError("unsupported count key: %r" % (value,))


def _counts(raw, width: int):
    normalized = Counter()
    for key, value in raw.items():
        normalized[_key(key, width)] += int(value)
    return dict(sorted(normalized.items()))


def main() -> None:
    import pyqpanda as pq

    payload = json.load(sys.stdin)
    machine = pq.CPUQVM()
    machine.init_qvm()
    try:
        converted = pq.convert_originir_str_to_qprog(payload["source"], machine)
        if isinstance(converted, (list, tuple)) and len(converted) == 3:
            program, _, classical = converted
        else:
            program = converted
            classical = machine.get_allocate_cbits()
        raw = machine.run_with_configuration(program, classical, payload["shots"])
    finally:
        machine.finalize()
    result = {
        "backend": "originq_cpu_simulator",
        "job_id": str(uuid.uuid4()),
        "shots": payload["shots"],
        "counts": _counts(raw, payload["num_clbits"]),
        "bit_order": "little",
        "timestamp": _timestamp(),
        "meta": {"qubits_count": payload["num_qubits"], "sdk": "pyqpanda"},
    }
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
