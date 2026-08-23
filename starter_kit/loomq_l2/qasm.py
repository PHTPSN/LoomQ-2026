"""Extraction and deterministic validation for Level 2 OpenQASM answers."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Mapping, Optional, Tuple

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import StatePreparation
from qiskit.quantum_info import Statevector

try:
    from ..loomq_l1 import emit_target, parse_qasm2
    from ..loomq_l1.model import Gate, LoomQCircuit, Measure
    from ..loomq_l1.semantics import _qiskit_gate, exact_distribution
except ImportError:
    from loomq_l1 import emit_target, parse_qasm2
    from loomq_l1.model import Gate, LoomQCircuit, Measure
    from loomq_l1.semantics import _qiskit_gate, exact_distribution


class QASMAnswerError(ValueError):
    """Raised when a model response does not contain a valid scored QASM answer."""


_QASM_START = re.compile(r"OPENQASM\s+2\.0\s*;", re.IGNORECASE)
_FENCE_END = re.compile(r"^\s*```", re.MULTILINE)


def extract_qasm(text: Any) -> Optional[str]:
    """Extract an OpenQASM 2 program from plain text or a Markdown code fence."""

    if not isinstance(text, str):
        return None
    match = _QASM_START.search(text)
    if not match:
        return None
    candidate = text[match.start() :]
    fence = _FENCE_END.search(candidate)
    if fence:
        candidate = candidate[: fence.start()]
    return candidate.strip()


def canonical_qasm(text: Any) -> str:
    """Parse a candidate through L1 and emit canonical OpenQASM 2.0."""

    candidate = extract_qasm(text)
    if candidate is None:
        raise QASMAnswerError("model response contains no OpenQASM 2.0 program")
    try:
        circuit = parse_qasm2(candidate)
    except Exception as exc:
        raise QASMAnswerError(str(exc)) from exc
    return emit_target(circuit, "spinq")


def normalize_distribution(value: Any) -> Optional[Dict[str, float]]:
    """Validate an optional expected measurement distribution from the model."""

    if value is None:
        return None
    if not isinstance(value, Mapping) or not value:
        raise QASMAnswerError("expected_distribution must be an object or null")
    distribution: Dict[str, float] = {}
    for key, probability in value.items():
        if not isinstance(key, str) or not key or set(key) - {"0", "1"}:
            raise QASMAnswerError("expected_distribution contains an invalid bit string")
        if isinstance(probability, bool) or not isinstance(probability, (int, float)):
            raise QASMAnswerError("expected_distribution contains a non-numeric probability")
        number = float(probability)
        if not math.isfinite(number) or number < 0:
            raise QASMAnswerError("expected_distribution contains an invalid probability")
        if number > 1e-12:
            distribution[key] = number
    total = sum(distribution.values())
    if not distribution or not math.isclose(total, 1.0, abs_tol=0.03):
        raise QASMAnswerError("expected_distribution probabilities must sum to one")
    return {key: probability / total for key, probability in distribution.items()}


def distribution_comparison(
    qasm: str, expected: Any
) -> Optional[Tuple[float, Dict[str, float], Dict[str, float]]]:
    """Return distance, target, and observation for a usable distribution."""

    target = normalize_distribution(expected)
    if target is None:
        return None
    circuit = parse_qasm2(qasm)
    if not circuit.measurements:
        raise QASMAnswerError("the proposed circuit has no measurements")
    if any(len(key) != circuit.num_clbits for key in target):
        raise QASMAnswerError("expected_distribution bit strings have the wrong width")
    observed = exact_distribution(circuit)
    keys = set(target) | set(observed)
    distance = 0.5 * sum(
        abs(target.get(key, 0.0) - observed.get(key, 0.0)) for key in keys
    )
    return distance, target, observed


def distribution_error(qasm: str, expected: Any) -> Optional[float]:
    """Return total-variation distance for a usable expected distribution."""

    comparison = distribution_comparison(qasm, expected)
    return None if comparison is None else comparison[0]


def normalize_target_state(value: Any) -> Optional[Tuple[int, np.ndarray]]:
    """Convert a sparse JSON amplitude map into a normalized statevector."""

    if value is None:
        return None
    if not isinstance(value, Mapping) or not value:
        raise QASMAnswerError("target_state must be an amplitude object or null")
    if any(not isinstance(key, str) for key in value):
        raise QASMAnswerError("target_state basis labels must be strings")
    widths = {len(key) for key in value}
    if len(widths) != 1:
        raise QASMAnswerError("target_state basis strings must have one consistent width")
    num_qubits = next(iter(widths))
    if num_qubits <= 0 or num_qubits > 10:
        raise QASMAnswerError("target_state supports between one and ten qubits")
    vector = np.zeros(1 << num_qubits, dtype=complex)
    for basis, raw_amplitude in value.items():
        if not isinstance(basis, str) or set(basis) - {"0", "1"}:
            raise QASMAnswerError("target_state contains an invalid basis string")
        if isinstance(raw_amplitude, bool):
            raise QASMAnswerError("target_state contains an invalid amplitude")
        if isinstance(raw_amplitude, (int, float)):
            amplitude = complex(float(raw_amplitude), 0.0)
        elif (
            isinstance(raw_amplitude, list)
            and len(raw_amplitude) == 2
            and all(
                isinstance(component, (int, float)) and not isinstance(component, bool)
                for component in raw_amplitude
            )
        ):
            amplitude = complex(float(raw_amplitude[0]), float(raw_amplitude[1]))
        else:
            raise QASMAnswerError(
                "target_state amplitudes must be numbers or [real, imaginary] pairs"
            )
        if not math.isfinite(amplitude.real) or not math.isfinite(amplitude.imag):
            raise QASMAnswerError("target_state contains a non-finite amplitude")
        vector[int(basis, 2)] = amplitude
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12:
        raise QASMAnswerError("target_state cannot be the zero vector")
    return num_qubits, vector / norm


def target_state_fidelity(qasm: str, target_state: Any) -> Optional[float]:
    """Compare the pre-measurement pure state with a model-declared target."""

    normalized = normalize_target_state(target_state)
    if normalized is None:
        return None
    num_qubits, target = normalized
    circuit = parse_qasm2(qasm)
    if circuit.num_qubits != num_qubits:
        raise QASMAnswerError("target_state width differs from the circuit qubit count")
    executable = QuantumCircuit(num_qubits)
    measurement_seen = False
    for instruction in circuit.instructions:
        if isinstance(instruction, Measure):
            measurement_seen = True
            continue
        if measurement_seen:
            raise QASMAnswerError(
                "pure-state validation does not permit gates after measurement"
            )
        executable.append(_qiskit_gate(instruction), list(instruction.qubits))
    observed = Statevector.from_instruction(executable).data
    return float(abs(np.vdot(target, observed)) ** 2)


def synthesize_target_state_qasm(target_state: Any, *, measure: bool = True) -> str:
    """Synthesize any small sparse pure state into the LoomQ gate whitelist."""

    normalized = normalize_target_state(target_state)
    if normalized is None:
        raise QASMAnswerError("no target_state is available for deterministic synthesis")
    num_qubits, vector = normalized
    source = QuantumCircuit(num_qubits)
    source.append(StatePreparation(vector), range(num_qubits))
    compiled = transpile(source, basis_gates=["u", "cx"], optimization_level=1)

    instructions = []
    for item in compiled.data:
        qubits = tuple(compiled.find_bit(qubit).index for qubit in item.qubits)
        if item.operation.name == "cx":
            instructions.append(Gate("cx", (), qubits))
            continue
        if item.operation.name != "u" or len(qubits) != 1:
            raise QASMAnswerError(
                "state synthesis produced an unsupported operation: %s"
                % item.operation.name
            )
        theta, phi, lam = (float(parameter) for parameter in item.operation.params)
        # U(theta, phi, lambda) equals RZ(phi) RY(theta) RZ(lambda), up to
        # an irrelevant global phase. Circuit statements execute right-to-left.
        instructions.extend(
            (
                Gate("rz", (lam,), qubits),
                Gate("ry", (theta,), qubits),
                Gate("rz", (phi,), qubits),
            )
        )
    if measure:
        instructions.extend(Measure(index, index) for index in range(num_qubits))
    circuit = LoomQCircuit(num_qubits, num_qubits, tuple(instructions))
    qasm = emit_target(circuit, "spinq")
    fidelity = target_state_fidelity(qasm, target_state)
    if fidelity is None or fidelity < 0.999999:
        raise QASMAnswerError("deterministic state synthesis failed its fidelity check")
    return qasm
