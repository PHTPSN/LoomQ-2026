"""Validated canonical circuit model for the L1 OpenQASM subset."""

from dataclasses import dataclass
import math
from typing import Tuple, Union


class CircuitValidationError(ValueError):
    """Raised when a circuit is outside the competition's L1 subset."""


@dataclass(frozen=True)
class GateSpec:
    parameter_count: int
    qubit_count: int


GATE_SPECS = {
    "h": GateSpec(0, 1),
    "x": GateSpec(0, 1),
    "s": GateSpec(0, 1),
    "sdg": GateSpec(0, 1),
    "t": GateSpec(0, 1),
    "tdg": GateSpec(0, 1),
    "rz": GateSpec(1, 1),
    "ry": GateSpec(1, 1),
    "cx": GateSpec(0, 2),
    "cu1": GateSpec(1, 2),
    "swap": GateSpec(0, 2),
    "ccx": GateSpec(0, 3),
}


@dataclass(frozen=True)
class Gate:
    name: str
    params: Tuple[float, ...]
    qubits: Tuple[int, ...]

    def __post_init__(self) -> None:
        spec = GATE_SPECS.get(self.name)
        if spec is None:
            raise CircuitValidationError("unsupported gate: %s" % self.name)
        if len(self.params) != spec.parameter_count:
            raise CircuitValidationError(
                "%s expects %d parameter(s), received %d"
                % (self.name, spec.parameter_count, len(self.params))
            )
        if len(self.qubits) != spec.qubit_count:
            raise CircuitValidationError(
                "%s expects %d qubit(s), received %d"
                % (self.name, spec.qubit_count, len(self.qubits))
            )
        if len(set(self.qubits)) != len(self.qubits):
            raise CircuitValidationError("%s uses the same qubit more than once" % self.name)
        if any(not math.isfinite(value) for value in self.params):
            raise CircuitValidationError("gate parameters must be finite numbers")


@dataclass(frozen=True)
class Measure:
    qubit: int
    clbit: int


Instruction = Union[Gate, Measure]


@dataclass(frozen=True)
class LoomQCircuit:
    """A register-independent, ordered circuit with explicit measurements."""

    num_qubits: int
    num_clbits: int
    instructions: Tuple[Instruction, ...]

    def __post_init__(self) -> None:
        if self.num_qubits <= 0:
            raise CircuitValidationError("the circuit must declare at least one qubit")
        if self.num_clbits <= 0:
            raise CircuitValidationError("the circuit must declare at least one classical bit")
        for instruction in self.instructions:
            if isinstance(instruction, Gate):
                if any(index < 0 or index >= self.num_qubits for index in instruction.qubits):
                    raise CircuitValidationError("gate qubit index is outside the circuit")
            elif isinstance(instruction, Measure):
                if instruction.qubit < 0 or instruction.qubit >= self.num_qubits:
                    raise CircuitValidationError("measurement qubit index is outside the circuit")
                if instruction.clbit < 0 or instruction.clbit >= self.num_clbits:
                    raise CircuitValidationError("measurement classical index is outside the circuit")
            else:
                raise CircuitValidationError("unknown canonical instruction type")

    @property
    def measurements(self) -> Tuple[Measure, ...]:
        return tuple(item for item in self.instructions if isinstance(item, Measure))
