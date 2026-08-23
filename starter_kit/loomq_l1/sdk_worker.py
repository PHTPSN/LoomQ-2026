#!/usr/bin/env python3
"""Backend SDK worker. This file runs inside a target-specific environment."""

from collections import Counter
from contextlib import redirect_stdout
from datetime import datetime, timezone
import json
import os
import sys
import tempfile
import uuid


def _timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _key(value, width):
    if isinstance(value, int):
        return format(value, "0%db" % width)
    text = str(value).replace(" ", "")
    if text and not (set(text) - {"0", "1"}):
        return text.zfill(width)
    if text.isdigit():
        return format(int(text), "0%db" % width)
    raise ValueError("unsupported count key: %r" % (value,))


def _counts(raw, width):
    normalized = Counter()
    for key, value in raw.items():
        normalized[_key(key, width)] += int(value)
    return dict(sorted(normalized.items()))


def _braket_counts(result, payload):
    """Map Braket's measured-qubit columns back to declared classical bits."""

    positions = {int(qubit): index for index, qubit in enumerate(result.measured_qubits)}
    normalized = Counter()
    for row in result.measurements:
        classical = [0] * payload["num_clbits"]
        for measurement in payload["measurements"]:
            position = positions.get(measurement["qubit"])
            if position is not None:
                classical[measurement["clbit"]] = int(row[position])
        key = "".join(str(classical[index]) for index in reversed(range(len(classical))))
        normalized[key] += 1
    return dict(sorted(normalized.items()))


def _spinq_counts(raw, payload):
    """Correct SpinQit's full-measurement operation-order bit strings."""

    width = payload["num_clbits"]
    measurements = payload["measurements"]
    normalized = Counter()
    for raw_key, value in raw.items():
        text = str(raw_key).replace(" ", "")
        if (
            text
            and not (set(text) - {"0", "1"})
            and len(text) == len(measurements)
            and len(measurements) == width
        ):
            classical = [0] * width
            for position, measurement in enumerate(measurements):
                classical[measurement["clbit"]] = int(text[position])
            key = "".join(str(classical[index]) for index in reversed(range(width)))
        else:
            key = _key(raw_key, width)
        normalized[key] += int(value)
    return dict(sorted(normalized.items()))


def _spinq(payload):
    from spinqit import BasicSimulatorConfig, get_basic_simulator, get_compiler

    descriptor, path = tempfile.mkstemp(suffix=".qasm", text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload["source"])
        ir = get_compiler("qasm").compile(path, 0)
    finally:
        os.unlink(path)
    config = BasicSimulatorConfig()
    config.configure_shots(payload["shots"])
    result = get_basic_simulator().execute(ir, config)
    return {
        "backend": "spinq_basic_simulator",
        "job_id": str(
            getattr(result, "job_id", None)
            or getattr(result, "task_id", None)
            or uuid.uuid4()
        ),
        "counts": _spinq_counts(result.counts, payload),
        "meta": {"qubits_count": payload["num_qubits"], "sdk": "spinqit"},
    }


def _originq(payload):
    import pyqpanda as pq

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
    return {
        "backend": "originq_cpu_simulator",
        "job_id": str(uuid.uuid4()),
        "counts": _counts(raw, payload["num_clbits"]),
        "meta": {"qubits_count": payload["num_qubits"], "sdk": "pyqpanda"},
    }


def _braket(payload):
    from braket.devices import LocalSimulator
    from braket.ir.openqasm import Program

    result = LocalSimulator().run(
        Program(source=payload["source"]), shots=payload["shots"]
    ).result()
    return {
        "backend": "braket_local_simulator",
        "job_id": str(getattr(result.task_metadata, "id", None) or uuid.uuid4()),
        "counts": _braket_counts(result, payload),
        "meta": {
            "qubits_count": payload["num_qubits"],
            "measured_qubits": list(result.measured_qubits),
            "sdk": "amazon-braket-sdk",
        },
    }


def main():
    payload = json.load(sys.stdin)
    runners = {"spinq": _spinq, "originq": _originq, "braket": _braket}
    with redirect_stdout(sys.stderr):
        partial = runners[payload["target"]](payload)
    partial.update(
        {
            "shots": payload["shots"],
            "bit_order": "little",
            "timestamp": _timestamp(),
        }
    )
    print(json.dumps(partial, separators=(",", ":")))


if __name__ == "__main__":
    main()
