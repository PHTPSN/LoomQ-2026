"""LoomQ Level 2 model-assisted, locally verified agent."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Mapping, Optional

try:
    from ..llm_client import chat_completion
except ImportError:
    from llm_client import chat_completion

from .backend import BackendConstraintError, format_recommendation
from .qasm import (
    QASMAnswerError,
    canonical_qasm,
    distribution_comparison,
    extract_qasm,
    require_measurements,
    sanitize_qasm2,
    synthesize_target_state_qasm,
    target_state_fidelity,
)


SYSTEM_PROMPT = r"""You are the reasoning component of LoomQ Level 2. Interpret the user's
request, but return exactly one JSON object and no Markdown.

Choose exactly one task:
- generate_qasm: create a circuit from natural-language intent.
- repair_qasm: repair supplied circuit text while preserving the explicitly stated target.
- select_backend: interpret backend requirements; local code will select from official data.

Return this schema:
{
  "task": "generate_qasm|repair_qasm|select_backend",
  "qasm": "complete OpenQASM 2.0 string or null",
  "expected_distribution": {"bitstring": probability} or null,
  "target_state": {"bitstring": amplitude} or null,
  "backend_constraints": {
    "min_qubits": positive integer or null,
    "allowed_kinds": ["simulator"|"qpu"|"cloud"] or null,
    "allowed_platforms": ["spinq"|"originq"|"braket"] or null,
    "queue_policy": "any"|"none"|"up_to_minutes_to_hours"|"up_to_hours",
    "cost_policy": "any"|"free_only"|"not_paid"|"paid_ok",
    "account_policy": "any"|"no_account"|"account_ok"|"account_required",
    "optimize": "balanced"|"queue"|"cost"|"capacity"
  } or null
}

For QASM, use only OpenQASM 2.0 with exactly one include "qelib1.inc", positive qreg
and creg declarations, lowercase gate names, and only h, x, s, sdg, t, tdg, rz, ry,
cx, cu1, swap, ccx, and measure. Include all measurements requested by the user.
For every generate_qasm or repair_qasm response, semantic verification metadata is
mandatory: provide target_state, expected_distribution, or both. A response with both
fields null will be rejected even if its QASM is syntactically valid. For a stated target
state, expected_distribution should describe the final classical measurement probabilities
when that is unambiguous; otherwise use null. Also provide target_state for every explicit
pure target state as a sparse map in q[n-1]...q[0]
bitstring order. Use a decimal real amplitude or [real, imaginary] pair, include only
nonzero amplitudes, and use null when no pure target is explicit.

For backend interpretation, do not invent or select a backend ID. Use cost_policy="not_paid"
when the user says free, cannot pay, does not want to spend money, or otherwise requires
zero personal payment: the official free_quota category satisfies those requests. Use
cost_policy="free_only" only when the user explicitly rejects quotas/credits or explicitly
requires the snapshot's exact free category. A request for real hardware with no payment
therefore uses allowed_kinds=["qpu"] and cost_policy="not_paid". A user who has, can create,
or is willing to create an account uses account_policy="account_ok"; use "no_account" only
when login/registration is rejected. Do not use "account_required" merely because a viable
backend happens to require an account. Zero wait means queue_policy="none". Use null/"any"
when the user did not impose a constraint."""


class ModelResponseError(ValueError):
    """Raised when the model response cannot drive a safe local decision."""


def _case_budget_seconds() -> float:
    try:
        configured = float(os.environ.get("LOOMQ_LLM_TIMEOUT_SECONDS", "120"))
    except ValueError as exc:
        raise RuntimeError("invalid LOOMQ_LLM_TIMEOUT_SECONDS") from exc
    if configured <= 0:
        raise RuntimeError("LOOMQ_LLM_TIMEOUT_SECONDS must be positive")
    return min(configured, 118.0)


def _response_content(response: Any) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ModelResponseError("model response has no assistant content") from exc
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts = [item.get("text") for item in content if isinstance(item, Mapping)]
        joined = "".join(part for part in parts if isinstance(part, str)).strip()
        if joined:
            return joined
    raise ModelResponseError("model returned empty assistant content")


def _json_objects(text: str):
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            yield value


def _interpret(content: str) -> Dict[str, Any]:
    last_error: Optional[ModelResponseError] = None
    for value in _json_objects(content):
        try:
            return _normalize_document(value)
        except ModelResponseError as exc:
            last_error = exc
    qasm = extract_qasm(content)
    if qasm is not None:
        return _normalize_document(
            {
                "task": "generate_qasm",
                "qasm": qasm,
                "expected_distribution": None,
                "target_state": None,
                "backend_constraints": None,
            }
        )
    if last_error is not None:
        raise last_error
    raise ModelResponseError("model did not return the requested JSON object")


def _normalize_document(value: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the first response object that satisfies the control schema."""

    document = dict(value)
    task = document.get("task")
    if task not in {"generate_qasm", "repair_qasm", "select_backend"}:
        raise ModelResponseError("model returned an unsupported task classification")
    for field in ("qasm", "expected_distribution", "target_state", "backend_constraints"):
        document.setdefault(field, None)
    if document["qasm"] is not None and not isinstance(document["qasm"], str):
        raise ModelResponseError("qasm must be a string or null")
    for field in ("expected_distribution", "target_state", "backend_constraints"):
        if document[field] is not None and not isinstance(document[field], Mapping):
            raise ModelResponseError("%s must be an object or null" % field)
    if task in {"generate_qasm", "repair_qasm"} and not document["qasm"]:
        raise ModelResponseError("a QASM task requires a non-empty qasm string")
    if task == "select_backend" and document["backend_constraints"] is None:
        raise ModelResponseError("backend selection requires backend_constraints")
    return document


def _call(messages: List[Dict[str, str]], deadline: float, *, first: bool) -> str:
    remaining = deadline - time.monotonic()
    if remaining <= 0.5:
        raise RuntimeError("LoomQ L2 case time budget exhausted")
    if first:
        timeout = min(85.0, max(0.5, remaining - min(25.0, remaining * 0.25)))
    else:
        timeout = max(0.5, remaining - min(5.0, remaining * 0.2))
    response = chat_completion(messages, _request_timeout_seconds=timeout)
    return _response_content(response)


def _correction_message(error: Exception) -> str:
    return (
        "Your previous response could not be accepted: %s. Return a corrected JSON object "
        "using the original schema. Preserve the user's intent and do not add Markdown."
    ) % str(error)


def _qasm_answer(document: Mapping[str, Any]) -> str:
    if (
        document.get("expected_distribution") is None
        and document.get("target_state") is None
    ):
        raise QASMAnswerError(
            "semantic verification requires target_state or expected_distribution"
        )
    qasm = canonical_qasm(document.get("qasm"))
    require_measurements(qasm)
    comparison = distribution_comparison(qasm, document.get("expected_distribution"))
    if comparison is not None and comparison[0] > 0.08:
        distance, expected, observed = comparison
        raise QASMAnswerError(
            "the circuit's measured distribution differs from the declared target: "
            "expected=%s, observed=%s, total-variation distance=%.6f. Rebuild the "
            "circuit from the target amplitudes instead of making a cosmetic edit"
            % (
                json.dumps(expected, sort_keys=True),
                json.dumps(observed, sort_keys=True),
                distance,
            )
        )
    fidelity = target_state_fidelity(qasm, document.get("target_state"))
    if fidelity is not None and fidelity < 0.97:
        raise QASMAnswerError(
            "the circuit differs from the declared pure target state: fidelity=%.6f. "
            "Rebuild it from the declared target amplitudes" % fidelity
        )
    return qasm


def _answer(document: Mapping[str, Any]) -> str:
    if document["task"] == "select_backend":
        return format_recommendation(document.get("backend_constraints"))
    return _qasm_answer(document)


def _synthesized_fallback(*documents: Optional[Mapping[str, Any]]) -> Optional[str]:
    for document in documents:
        if not document or document.get("task") not in {"generate_qasm", "repair_qasm"}:
            continue
        target_state = document.get("target_state")
        if target_state is None:
            continue
        try:
            qasm = synthesize_target_state_qasm(target_state)
            candidate = dict(document)
            candidate["qasm"] = qasm
            return _qasm_answer(candidate)
        except (QASMAnswerError, ValueError):
            continue
    return None


def _sanitized_fallback(*documents: Optional[Mapping[str, Any]]) -> Optional[str]:
    """Repair mechanical QASM syntax only, then run the full semantic verifier."""

    for document in documents:
        if not document or document.get("task") not in {"generate_qasm", "repair_qasm"}:
            continue
        if (
            document.get("expected_distribution") is None
            and document.get("target_state") is None
        ):
            continue
        qasm = sanitize_qasm2(document.get("qasm"))
        if qasm is None:
            continue
        candidate = dict(document)
        candidate["qasm"] = qasm
        try:
            return _qasm_answer(candidate)
        except (QASMAnswerError, ValueError):
            continue
    return None


def agent_chat(prompt: str) -> str:
    """Interpret one L2 prompt with a required model call and local verification."""

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    deadline = time.monotonic() + _case_budget_seconds()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt.strip()},
    ]

    content = _call(messages, deadline, first=True)
    messages.append({"role": "assistant", "content": content})
    first_document: Optional[Dict[str, Any]] = None
    try:
        first_document = _interpret(content)
        return _answer(first_document)
    except (BackendConstraintError, ModelResponseError, QASMAnswerError, ValueError) as first_error:
        messages.append({"role": "user", "content": _correction_message(first_error)})
        corrected = _call(messages, deadline, first=False)
        corrected_document: Optional[Dict[str, Any]] = None
        try:
            corrected_document = _interpret(corrected)
            return _answer(corrected_document)
        except (BackendConstraintError, ModelResponseError, QASMAnswerError, ValueError):
            fallback = _synthesized_fallback(corrected_document, first_document)
            if fallback is not None:
                return fallback
            fallback = _sanitized_fallback(corrected_document, first_document)
            if fallback is not None:
                return fallback
            raise
