"""Strict OpenQASM 2 frontend backed by Qiskit's maintained parser."""

import re
from typing import List

from qiskit import qasm2
from qiskit.qasm2.exceptions import QASM2ParseError

from .model import CircuitValidationError, Gate, Instruction, LoomQCircuit, Measure


class QASM2FrontendError(CircuitValidationError):
    """Raised for invalid syntax or instructions outside the L1 contract."""


def _strip_line_comments(source: str) -> str:
    """Remove QASM line comments while preserving quoted include paths."""

    output = []
    index = 0
    quoted = False
    while index < len(source):
        char = source[index]
        if char == '"':
            quoted = not quoted
            output.append(char)
            index += 1
        elif not quoted and source.startswith("//", index):
            while index < len(source) and source[index] not in "\r\n":
                output.append(" ")
                index += 1
        else:
            output.append(char)
            index += 1
    return "".join(output)


def _preflight_source(source: str) -> None:
    """Enforce source distinctions that Qiskit's circuit model normalizes away."""

    visible = _strip_line_comments(source)
    includes = re.findall(r'\binclude\s*"([^"\r\n]+)"\s*;', visible)
    if includes != ["qelib1.inc"]:
        raise QASM2FrontendError('exactly one include "qelib1.inc"; statement is required')
    if re.search(r"\bCX(?=\s)", visible):
        raise QASM2FrontendError("unsupported gate spelling: CX; use lowercase cx")


def parse_qasm2(source: str) -> LoomQCircuit:
    """Parse standard OpenQASM 2 and convert it to the canonical L1 model.

    The legacy include configuration is intentional: the competition permits
    gates such as ``swap`` and ``cu1`` from Qiskit's complete qelib1.inc file.
    Strict mode still rejects the permissive syntax extensions of older importers.
    """

    if not isinstance(source, str) or not source.strip():
        raise QASM2FrontendError("OpenQASM source must be a non-empty string")
    _preflight_source(source)
    try:
        parsed = qasm2.loads(
            source,
            include_path=qasm2.LEGACY_INCLUDE_PATH,
            custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
            strict=True,
        )
    except QASM2ParseError as exc:
        raise QASM2FrontendError("invalid OpenQASM 2: %s" % exc) from exc

    instructions: List[Instruction] = []
    for item in parsed.data:
        operation = item.operation
        name = operation.name
        qubits = tuple(parsed.find_bit(bit).index for bit in item.qubits)
        clbits = tuple(parsed.find_bit(bit).index for bit in item.clbits)
        if name == "measure":
            if len(qubits) != 1 or len(clbits) != 1:
                raise QASM2FrontendError("measurement must map one qubit to one classical bit")
            instructions.append(Measure(qubits[0], clbits[0]))
            continue
        if clbits:
            raise QASM2FrontendError("gate instructions cannot consume classical bits")
        try:
            params = tuple(float(value) for value in operation.params)
        except (TypeError, ValueError) as exc:
            raise QASM2FrontendError("gate parameters must be numeric constants") from exc
        try:
            instructions.append(Gate(name, params, qubits))
        except CircuitValidationError as exc:
            raise QASM2FrontendError(str(exc)) from exc

    return LoomQCircuit(
        num_qubits=parsed.num_qubits,
        num_clbits=parsed.num_clbits,
        instructions=tuple(instructions),
    )
