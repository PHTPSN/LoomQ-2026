"""Pure emitters from the canonical circuit to each formal target contract."""

from typing import Callable, Dict, List

from .model import Gate, LoomQCircuit, Measure


def _number(value: float) -> str:
    if abs(value) < 1e-15:
        value = 0.0
    return format(value, ".17g")


def _arguments(gate: Gate, gate_name: str, qref: Callable[[int], str]) -> str:
    params = ""
    if gate.params:
        params = "(" + ",".join(_number(value) for value in gate.params) + ")"
    qubits = ", ".join(qref(index) for index in gate.qubits)
    return "%s%s %s;" % (gate_name, params, qubits)


def emit_spinq(circuit: LoomQCircuit) -> str:
    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        "qreg q[%d];" % circuit.num_qubits,
        "creg c[%d];" % circuit.num_clbits,
    ]
    for instruction in circuit.instructions:
        if isinstance(instruction, Gate):
            lines.append(_arguments(instruction, instruction.name, lambda index: "q[%d]" % index))
        else:
            lines.append("measure q[%d] -> c[%d];" % (instruction.qubit, instruction.clbit))
    return "\n".join(lines) + "\n"


ORIGIN_GATE_NAMES: Dict[str, str] = {
    "h": "H",
    "x": "X",
    "s": "S",
    "sdg": "SDAG",
    "t": "T",
    "tdg": "TDAG",
    "rz": "RZ",
    "ry": "RY",
    "cx": "CNOT",
    "cu1": "CU1",
    "swap": "SWAP",
    "ccx": "TOFFOLI",
}


def emit_originq(circuit: LoomQCircuit) -> str:
    lines = ["QINIT %d" % circuit.num_qubits, "CREG %d" % circuit.num_clbits]
    for instruction in circuit.instructions:
        if isinstance(instruction, Measure):
            lines.append("MEASURE q[%d], c[%d]" % (instruction.qubit, instruction.clbit))
            continue
        name = ORIGIN_GATE_NAMES[instruction.name]
        qubits = ", ".join("q[%d]" % index for index in instruction.qubits)
        if instruction.params:
            lines.append("%s %s,(%s)" % (name, qubits, _number(instruction.params[0])))
        else:
            lines.append("%s %s" % (name, qubits))
    return "\n".join(lines) + "\n"


BRAKET_GATE_NAMES: Dict[str, str] = {
    "h": "h",
    "x": "x",
    "s": "s",
    "sdg": "sdg",
    "t": "t",
    "tdg": "tdg",
    "rz": "rz",
    "ry": "ry",
    "cx": "cx",
    "cu1": "cp",
    "swap": "swap",
    "ccx": "ccx",
}

BRAKET_LOCAL_GATE_NAMES: Dict[str, str] = {
    **BRAKET_GATE_NAMES,
    "sdg": "si",
    "tdg": "ti",
    "cx": "cnot",
    "cu1": "cphaseshift",
    "ccx": "ccnot",
}


def emit_braket(circuit: LoomQCircuit) -> str:
    lines = [
        "OPENQASM 3.0;",
        'include "stdgates.inc";',
        "qubit[%d] q;" % circuit.num_qubits,
        "bit[%d] c;" % circuit.num_clbits,
    ]
    for instruction in circuit.instructions:
        if isinstance(instruction, Gate):
            lines.append(
                _arguments(
                    instruction,
                    BRAKET_GATE_NAMES[instruction.name],
                    lambda index: "q[%d]" % index,
                )
            )
        else:
            lines.append("c[%d] = measure q[%d];" % (instruction.clbit, instruction.qubit))
    return "\n".join(lines) + "\n"


def emit_originq_local(circuit: LoomQCircuit) -> str:
    """Emit the syntax accepted by the pinned pyqpanda 3.8.5 parser."""

    lines = ["QINIT %d" % circuit.num_qubits, "CREG %d" % circuit.num_clbits]
    for instruction in circuit.instructions:
        if isinstance(instruction, Measure):
            lines.append("MEASURE q[%d],c[%d]" % (instruction.qubit, instruction.clbit))
            continue
        qubits = ["q[%d]" % index for index in instruction.qubits]
        if instruction.name == "sdg":
            lines.append("RZ %s,(-1.5707963267948966)" % qubits[0])
        elif instruction.name == "tdg":
            lines.append("RZ %s,(-0.7853981633974483)" % qubits[0])
        elif instruction.name == "cu1":
            lines.append(
                "CR %s,%s,(%s)"
                % (qubits[0], qubits[1], _number(instruction.params[0]))
            )
        else:
            name = ORIGIN_GATE_NAMES[instruction.name]
            if instruction.params:
                lines.append("%s %s,(%s)" % (name, qubits[0], _number(instruction.params[0])))
            else:
                lines.append("%s %s" % (name, ",".join(qubits)))
    return "\n".join(lines) + "\n"


def emit_braket_local(circuit: LoomQCircuit) -> str:
    """Emit the native gate spellings accepted by the pinned local simulator."""

    lines = [
        "OPENQASM 3.0;",
        "qubit[%d] q;" % circuit.num_qubits,
        "bit[%d] c;" % circuit.num_clbits,
    ]
    for instruction in circuit.instructions:
        if isinstance(instruction, Gate):
            lines.append(
                _arguments(
                    instruction,
                    BRAKET_LOCAL_GATE_NAMES[instruction.name],
                    lambda index: "q[%d]" % index,
                )
            )
        else:
            lines.append("c[%d] = measure q[%d];" % (instruction.clbit, instruction.qubit))
    return "\n".join(lines) + "\n"


EMITTERS = {"spinq": emit_spinq, "originq": emit_originq, "braket": emit_braket}


def emit_target(circuit: LoomQCircuit, target: str) -> str:
    try:
        emitter = EMITTERS[target]
    except KeyError as exc:
        raise ValueError("unsupported target: %s" % target) from exc
    return emitter(circuit)


def emit_local_target(circuit: LoomQCircuit, target: str) -> str:
    emitters = {
        "spinq": emit_spinq,
        "originq": emit_originq_local,
        "braket": emit_braket_local,
    }
    try:
        emitter = emitters[target]
    except KeyError as exc:
        raise ValueError("unsupported target: %s" % target) from exc
    return emitter(circuit)
