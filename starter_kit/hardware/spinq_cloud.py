"""Prepare validated OpenQASM 2.0 for optional SpinQ Cloud hardware evidence.

This module is intentionally separate from the formal L1 ``spinq`` emitter.
SpinQ Cloud automatically measures active qubits and its MCP submission tool
rejects explicit measurement statements.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence, Set, Tuple

from starter_kit.loomq_l1.frontend import parse_qasm2
from starter_kit.loomq_l1.model import Gate, LoomQCircuit, Measure


class SpinQCloudValidationError(ValueError):
    """Raised when a canonical circuit cannot run unchanged on a platform."""


CANONICAL_TO_CAPABILITY = {
    "h": "H",
    "x": "X",
    "s": "S",
    "sdg": "Sdg",
    "t": "T",
    "tdg": "Td",
    "rz": "Rz",
    "ry": "Ry",
    "cx": "CNOT",
    "cu1": "CU1",
    "swap": "SWAP",
    "ccx": "CCNOT",
}


def _number(value: float) -> str:
    if abs(value) < 1e-15:
        value = 0.0
    return format(value, ".17g")


def _platform(items: Sequence[Mapping[str, Any]], platform_code: str) -> Mapping[str, Any]:
    matches = [item for item in items if item.get("pcode") == platform_code]
    if len(matches) != 1:
        raise SpinQCloudValidationError(
            "platform %r was not returned exactly once by get_platforms" % platform_code
        )
    return matches[0]


def _active_qubits(circuit: LoomQCircuit) -> Set[int]:
    return {
        qubit
        for instruction in circuit.instructions
        if isinstance(instruction, Gate)
        for qubit in instruction.qubits
    }


def _validate_measurements(circuit: LoomQCircuit, active_qubits: Set[int]) -> None:
    seen_measurement = False
    mappings = []
    for instruction in circuit.instructions:
        if isinstance(instruction, Measure):
            seen_measurement = True
            mappings.append((instruction.qubit, instruction.clbit))
        elif seen_measurement:
            raise SpinQCloudValidationError(
                "SpinQ Cloud preparation does not support gates after measurement"
            )

    expected = [(index, index) for index in sorted(active_qubits)]
    if mappings != expected:
        raise SpinQCloudValidationError(
            "automatic cloud measurement requires one terminal q[i] -> c[i] "
            "measurement for every active qubit"
        )


def _validate_topology(gate: Gate, coupling: Set[Tuple[int, int]]) -> None:
    if len(gate.qubits) == 2:
        edge = (gate.qubits[0] + 1, gate.qubits[1] + 1)
        if edge not in coupling:
            raise SpinQCloudValidationError(
                "%s uses unsupported directed coupling %s" % (gate.name, edge)
            )
    elif len(gate.qubits) == 3:
        required = {
            (left + 1, right + 1)
            for left in gate.qubits
            for right in gate.qubits
            if left != right
        }
        if not required.issubset(coupling):
            raise SpinQCloudValidationError(
                "%s operands are not fully connected on the selected platform" % gate.name
            )


def prepare_spinq_cloud_qasm(
    circuit: LoomQCircuit,
    platform: Mapping[str, Any],
    *,
    require_online: bool = True,
) -> str:
    """Validate ``circuit`` against one live platform record and emit cloud QASM."""

    platform_code = str(platform.get("pcode") or "<unknown>")
    if platform.get("simu") is not False:
        raise SpinQCloudValidationError("platform %s is not a real machine" % platform_code)
    if platform.get("pstatus") != "ACTIVE":
        raise SpinQCloudValidationError("platform %s is not active" % platform_code)
    if require_online and int(platform.get("countOnlineMachine") or 0) < 1:
        raise SpinQCloudValidationError("platform %s has no online machine" % platform_code)

    active_qubits = _active_qubits(circuit)
    if not active_qubits:
        raise SpinQCloudValidationError("the circuit has no active qubits")
    expected_layout = set(range(max(active_qubits) + 1))
    if active_qubits != expected_layout:
        raise SpinQCloudValidationError(
            "SpinQ Cloud evidence requires a contiguous active layout starting at q[0]"
        )
    if circuit.num_qubits != len(active_qubits):
        raise SpinQCloudValidationError(
            "every declared qubit must be active for unambiguous cloud measurement"
        )
    if circuit.num_qubits > int(platform.get("maxBitNum") or 0):
        raise SpinQCloudValidationError(
            "circuit requires %d qubits but %s supports %s"
            % (circuit.num_qubits, platform_code, platform.get("maxBitNum"))
        )

    _validate_measurements(circuit, active_qubits)

    capabilities = {str(name).casefold() for name in platform.get("supportGateName", [])}
    coupling = {
        (int(edge[0]), int(edge[1]))
        for edge in platform.get("couplingMap", [])
        if isinstance(edge, (list, tuple)) and len(edge) == 2
    }
    gates = [item for item in circuit.instructions if isinstance(item, Gate)]
    for gate in gates:
        capability = CANONICAL_TO_CAPABILITY[gate.name]
        if capability.casefold() not in capabilities:
            raise SpinQCloudValidationError(
                "%s does not advertise native support for LoomQ gate %s (%s)"
                % (platform_code, gate.name, capability)
            )
        _validate_topology(gate, coupling)

    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        "qreg q[%d];" % circuit.num_qubits,
    ]
    for gate in gates:
        params = ""
        if gate.params:
            params = "(" + ",".join(_number(value) for value in gate.params) + ")"
        operands = ", ".join("q[%d]" % index for index in gate.qubits)
        lines.append("%s%s %s;" % (gate.name, params, operands))
    return "\n".join(lines) + "\n"


def prepare_from_discovery(
    qasm_source: str,
    discovery: Mapping[str, Any],
    platform_code: str,
) -> str:
    if discovery.get("status") != 200:
        raise SpinQCloudValidationError("get_platforms did not return status 200")
    items = discovery.get("items")
    if not isinstance(items, list):
        raise SpinQCloudValidationError("get_platforms response has no platform list")
    return prepare_spinq_cloud_qasm(
        parse_qasm2(qasm_source),
        _platform(items, platform_code),
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare QASM for SpinQ Cloud")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--platforms-json", type=Path, required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    source = args.source.read_text(encoding="utf-8")
    discovery = json.loads(args.platforms_json.read_text(encoding="utf-8"))
    output = prepare_from_discovery(source, discovery, args.platform)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(output, encoding="utf-8")
    print("prepared %s for %s" % (args.out, args.platform))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
