"""Executable reference semantics for canonical circuits."""

from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, Dict, List, Tuple

import numpy as np
from qiskit.circuit.library import (
    CCXGate,
    CU1Gate,
    CXGate,
    HGate,
    RYGate,
    RZGate,
    SdgGate,
    SGate,
    SwapGate,
    TdgGate,
    TGate,
    XGate,
)
from qiskit.quantum_info import Statevector

from .model import Gate, LoomQCircuit, Measure


@dataclass
class _Branch:
    weight: float
    state: np.ndarray
    classical: Tuple[int, ...]


def _qiskit_gate(gate: Gate):
    constructors = {
        "h": HGate,
        "x": XGate,
        "s": SGate,
        "sdg": SdgGate,
        "t": TGate,
        "tdg": TdgGate,
        "rz": RZGate,
        "ry": RYGate,
        "cx": CXGate,
        "cu1": CU1Gate,
        "swap": SwapGate,
        "ccx": CCXGate,
    }
    return constructors[gate.name](*gate.params)


def _measure(branch: _Branch, instruction: Measure) -> List[_Branch]:
    indices = np.arange(branch.state.size)
    bit_values = (indices >> instruction.qubit) & 1
    children = []
    for outcome in (0, 1):
        keep = bit_values == outcome
        probability = float(np.sum(np.abs(branch.state[keep]) ** 2))
        if probability <= 1e-15:
            continue
        state = np.where(keep, branch.state, 0.0) / np.sqrt(probability)
        classical = list(branch.classical)
        classical[instruction.clbit] = outcome
        children.append(_Branch(branch.weight * probability, state, tuple(classical)))
    return children


def exact_distribution(circuit: LoomQCircuit) -> Dict[str, float]:
    """Return the exact observable distribution, with c[0] at the right."""

    initial = np.zeros(1 << circuit.num_qubits, dtype=complex)
    initial[0] = 1.0
    branches = [_Branch(1.0, initial, (0,) * circuit.num_clbits)]
    for instruction in circuit.instructions:
        if isinstance(instruction, Gate):
            operation = _qiskit_gate(instruction)
            for branch in branches:
                branch.state = Statevector(branch.state).evolve(
                    operation, qargs=list(instruction.qubits)
                ).data
        else:
            branches = [child for branch in branches for child in _measure(branch, instruction)]

    probabilities: DefaultDict[str, float] = defaultdict(float)
    for branch in branches:
        key = "".join(str(branch.classical[index]) for index in reversed(range(circuit.num_clbits)))
        probabilities[key] += branch.weight
    return {
        key: value
        for key, value in sorted(probabilities.items())
        if value > 1e-12
    }
