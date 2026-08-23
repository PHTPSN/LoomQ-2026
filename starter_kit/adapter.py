#!/usr/bin/env python3
"""LoomQ submission adapter contract v1.0."""

from typing import Any, Dict, List, Tuple

try:
    from .loomq_l1 import emit_target, parse_qasm2
    from .loomq_l1.originq_runner import run_originq_isolated
except ImportError:
    from loomq_l1 import emit_target, parse_qasm2
    from loomq_l1.originq_runner import run_originq_isolated


SUPPORTED_TARGETS = ("spinq", "originq", "braket")


def transpile(qasm_str: str, target: str) -> str:
    """Translate OpenQASM 2.0 into the target backend's native representation."""
    if target not in SUPPORTED_TARGETS:
        raise ValueError("unsupported target: %s" % target)
    return emit_target(parse_qasm2(qasm_str), target)


def run(qasm_str: str, target: str, shots: int) -> Dict[str, Any]:
    """Execute a circuit and return the unified result schema from the rules."""
    if target not in SUPPORTED_TARGETS:
        raise ValueError("unsupported target: %s" % target)
    if target != "originq":
        raise NotImplementedError("%s execution infrastructure is not committed yet" % target)
    if not isinstance(shots, int) or isinstance(shots, bool) or shots <= 0:
        raise ValueError("shots must be a positive integer")
    return run_originq_isolated(parse_qasm2(qasm_str), shots)


def agent_chat(prompt: str) -> str:
    """Optional L2 entry point using the documented LOOMQ_LLM_* environment."""
    raise NotImplementedError("L2 is optional; implement agent_chat(prompt) to enter")


def compile_hybrid(hybrid_qasm_str: str) -> Tuple[List[str], str]:
    """Optional L3 entry point. Return quantum operations and RISC-V assembly."""
    raise NotImplementedError(
        "L3 is optional; implement compile_hybrid(hybrid_qasm_str) to enter"
    )
