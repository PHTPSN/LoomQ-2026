"""LoomQ 32-bit custom quantum RISC-V instruction encoding.

This module is deliberately dependency-free.  It turns the canonical quantum
operation strings returned by ``compile_hybrid`` into real 32-bit instruction
words and decodes those words back into executable semantic operations.
"""

from dataclasses import dataclass
import math
import re
from typing import Iterable, List, Optional, Sequence, Tuple


CUSTOM_0_OPCODE = 0x0B
ANGLE_SCALE = 512


class QuantumRISCVError(ValueError):
    """Raised when a quantum instruction cannot be encoded or decoded."""


@dataclass(frozen=True)
class QuantumInstruction:
    """Decoded semantic form of one LoomQ quantum RISC-V instruction."""

    name: str
    qubits: Tuple[int, ...]
    params: Tuple[float, ...] = ()
    clbit: Optional[int] = None

    def to_operation(self) -> str:
        if self.name == "measure":
            return "measure q[%d] -> c[%d];" % (self.qubits[0], self.clbit)
        parameter_text = ""
        if self.params:
            parameter_text = "(" + ",".join(format(value, ".17g") for value in self.params) + ")"
        qubit_text = ", ".join("q[%d]" % index for index in self.qubits)
        return "%s%s %s;" % (self.name, parameter_text, qubit_text)


# funct7 values used when funct3 == 000 (QR format).
_BASE_GATE_CODES = {
    "h": 0x01,
    "x": 0x02,
    "s": 0x03,
    "sdg": 0x04,
    "t": 0x05,
    "tdg": 0x06,
    "cx": 0x07,
    "swap": 0x08,
    "ccx": 0x09,
    "measure": 0x0A,
}
_BASE_CODE_GATES = {value: key for key, value in _BASE_GATE_CODES.items()}

# funct3 values used for the QI immediate format.
_PARAMETER_GATE_CODES = {"ry": 0x1, "rz": 0x2, "cu1": 0x3}
_PARAMETER_CODE_GATES = {value: key for key, value in _PARAMETER_GATE_CODES.items()}

_QUBIT_COUNTS = {
    "h": 1,
    "x": 1,
    "s": 1,
    "sdg": 1,
    "t": 1,
    "tdg": 1,
    "ry": 1,
    "rz": 1,
    "cx": 2,
    "cu1": 2,
    "swap": 2,
    "ccx": 3,
    "measure": 1,
}

_MEASURE_RE = re.compile(
    r"^measure\s+q\[(\d+)\]\s*->\s*c\[(\d+)\]\s*;$", re.IGNORECASE
)
_GATE_RE = re.compile(
    r"^([a-z][a-z0-9]*)(?:\(([^()]*)\))?\s+(.+?)\s*;$", re.IGNORECASE
)
_QUBIT_RE = re.compile(r"^q\[(\d+)\]$", re.IGNORECASE)


def _check_index(index: int, kind: str) -> int:
    if not isinstance(index, int) or isinstance(index, bool) or index < 0 or index > 31:
        raise QuantumRISCVError("%s index must fit the five-bit range 0..31" % kind)
    return index


def _normalise_angle(value: float) -> float:
    if not math.isfinite(value):
        raise QuantumRISCVError("gate angle must be finite")
    # All three parameterized whitelist gates are 2*pi periodic up to an
    # irrelevant global phase, so canonicalisation avoids an artificial range
    # restriction while retaining a compact immediate.
    normalised = (value + math.pi) % (2.0 * math.pi) - math.pi
    if normalised == -math.pi and value > 0:
        return math.pi
    return normalised


def _encode_angle(value: float) -> int:
    scaled = int(round(_normalise_angle(value) * ANGLE_SCALE))
    if scaled < -2048 or scaled > 2047:
        # +pi rounds beyond signed Q3.9.  -pi represents the same rotation up
        # to global phase and is exactly representable.
        if scaled == 2048:
            scaled = -int(round(math.pi * ANGLE_SCALE))
        else:
            raise QuantumRISCVError("normalised gate angle does not fit signed Q3.9")
    return scaled & 0xFFF


def _decode_angle(immediate: int) -> float:
    signed = immediate - 0x1000 if immediate & 0x800 else immediate
    return signed / float(ANGLE_SCALE)


def parse_operation(operation: str) -> QuantumInstruction:
    """Parse one canonical L3 quantum operation without requiring Qiskit."""

    if not isinstance(operation, str):
        raise QuantumRISCVError("quantum operation must be text")
    text = operation.strip()
    measurement = _MEASURE_RE.fullmatch(text)
    if measurement is not None:
        qubit = _check_index(int(measurement.group(1)), "qubit")
        clbit = _check_index(int(measurement.group(2)), "classical bit")
        return QuantumInstruction("measure", (qubit,), clbit=clbit)

    match = _GATE_RE.fullmatch(text)
    if match is None:
        raise QuantumRISCVError("invalid canonical quantum operation: %s" % operation)
    name = match.group(1).lower()
    if name not in _QUBIT_COUNTS or name == "measure":
        raise QuantumRISCVError("unsupported quantum instruction: %s" % name)

    params_text = match.group(2)
    params: Tuple[float, ...] = ()
    if params_text is not None:
        pieces = [piece.strip() for piece in params_text.split(",")]
        try:
            params = tuple(float(piece) for piece in pieces)
        except ValueError as exc:
            raise QuantumRISCVError("gate parameter must be a canonical number") from exc

    operands = [piece.strip() for piece in match.group(3).split(",")]
    qubits: List[int] = []
    for operand in operands:
        qubit_match = _QUBIT_RE.fullmatch(operand)
        if qubit_match is None:
            raise QuantumRISCVError("invalid qubit operand: %s" % operand)
        qubits.append(_check_index(int(qubit_match.group(1)), "qubit"))

    expected_params = 1 if name in _PARAMETER_GATE_CODES else 0
    if len(params) != expected_params:
        raise QuantumRISCVError("%s expects %d parameter(s)" % (name, expected_params))
    if len(qubits) != _QUBIT_COUNTS[name]:
        raise QuantumRISCVError("%s expects %d qubit operand(s)" % (name, _QUBIT_COUNTS[name]))
    if len(set(qubits)) != len(qubits):
        raise QuantumRISCVError("quantum instruction repeats a qubit operand")
    return QuantumInstruction(name, tuple(qubits), params)


def encode_instruction(instruction: QuantumInstruction) -> int:
    """Encode one semantic instruction as an unsigned 32-bit word."""

    if not isinstance(instruction, QuantumInstruction):
        raise QuantumRISCVError("expected a QuantumInstruction")
    name = instruction.name.lower()
    expected_qubits = _QUBIT_COUNTS.get(name)
    if expected_qubits is None or len(instruction.qubits) != expected_qubits:
        raise QuantumRISCVError("invalid operands for quantum instruction %s" % name)
    qubits = tuple(_check_index(index, "qubit") for index in instruction.qubits)
    if len(set(qubits)) != len(qubits):
        raise QuantumRISCVError("quantum instruction repeats a qubit operand")

    if name in _BASE_GATE_CODES:
        if instruction.params:
            raise QuantumRISCVError("%s does not accept a gate parameter" % name)
        rd = qubits[0]
        rs1 = qubits[1] if len(qubits) > 1 else 0
        rs2 = qubits[2] if len(qubits) > 2 else 0
        if name == "measure":
            if instruction.clbit is None:
                raise QuantumRISCVError("measure requires a classical-bit destination")
            rs1 = _check_index(instruction.clbit, "classical bit")
        elif instruction.clbit is not None:
            raise QuantumRISCVError("only measure accepts a classical-bit destination")
        return (
            (_BASE_GATE_CODES[name] << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (rd << 7)
            | CUSTOM_0_OPCODE
        )

    if name in _PARAMETER_GATE_CODES:
        if len(instruction.params) != 1 or instruction.clbit is not None:
            raise QuantumRISCVError("%s requires one angle and no classical bit" % name)
        rd = qubits[0]
        rs1 = qubits[1] if len(qubits) == 2 else 0
        immediate = _encode_angle(instruction.params[0])
        return (
            (immediate << 20)
            | (rs1 << 15)
            | (_PARAMETER_GATE_CODES[name] << 12)
            | (rd << 7)
            | CUSTOM_0_OPCODE
        )
    raise QuantumRISCVError("unsupported quantum instruction: %s" % name)


def decode_instruction(word: int) -> QuantumInstruction:
    """Decode and validate one unsigned LoomQ 32-bit custom instruction."""

    if not isinstance(word, int) or isinstance(word, bool) or word < 0 or word > 0xFFFFFFFF:
        raise QuantumRISCVError("instruction word must be an unsigned 32-bit integer")
    opcode = word & 0x7F
    if opcode != CUSTOM_0_OPCODE:
        raise QuantumRISCVError("unsupported opcode 0x%02x" % opcode)
    rd = (word >> 7) & 0x1F
    funct3 = (word >> 12) & 0x7
    rs1 = (word >> 15) & 0x1F

    if funct3 == 0:
        rs2 = (word >> 20) & 0x1F
        funct7 = (word >> 25) & 0x7F
        name = _BASE_CODE_GATES.get(funct7)
        if name is None:
            raise QuantumRISCVError("unknown base quantum funct7 0x%02x" % funct7)
        count = _QUBIT_COUNTS[name]
        if name == "measure":
            if rs2 != 0:
                raise QuantumRISCVError("measure reserves the rs2 field")
            return QuantumInstruction(name, (rd,), clbit=rs1)
        if count == 1:
            if rs1 != 0 or rs2 != 0:
                raise QuantumRISCVError("single-qubit instruction has nonzero reserved operands")
            qubits = (rd,)
        elif count == 2:
            if rs2 != 0:
                raise QuantumRISCVError("two-qubit instruction has nonzero reserved rs2")
            qubits = (rd, rs1)
        else:
            qubits = (rd, rs1, rs2)
        if len(set(qubits)) != len(qubits):
            raise QuantumRISCVError("decoded instruction repeats a qubit operand")
        return QuantumInstruction(name, qubits)

    name = _PARAMETER_CODE_GATES.get(funct3)
    if name is None:
        raise QuantumRISCVError("unknown parameterized quantum funct3 0x%x" % funct3)
    immediate = (word >> 20) & 0xFFF
    if name in ("ry", "rz"):
        if rs1 != 0:
            raise QuantumRISCVError("single-qubit rotation reserves the rs1 field")
        qubits = (rd,)
    else:
        qubits = (rd, rs1)
        if rd == rs1:
            raise QuantumRISCVError("decoded instruction repeats a qubit operand")
    return QuantumInstruction(name, qubits, (_decode_angle(immediate),))


def encode_operation(operation: str) -> int:
    return encode_instruction(parse_operation(operation))


def encode_program(operations: Iterable[str]) -> List[int]:
    return [encode_operation(operation) for operation in operations]


def decode_program(words: Iterable[int]) -> List[QuantumInstruction]:
    return [decode_instruction(word) for word in words]


def format_machine_code(words: Sequence[int]) -> str:
    """Return a stable, review-friendly hexadecimal machine-code listing."""

    return "\n".join("0x%08x" % word for word in words) + ("\n" if words else "")
