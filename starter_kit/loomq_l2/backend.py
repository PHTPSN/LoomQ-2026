"""Deterministic backend selection from the competition capability snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


CAPABILITIES_PATH = Path(__file__).resolve().parents[1] / "backend_capabilities.json"

_KINDS = {"simulator", "qpu", "cloud"}
_PLATFORMS = {"spinq", "originq", "braket"}
_QUEUE_POLICIES = {"any", "none", "up_to_minutes_to_hours", "up_to_hours"}
_COST_POLICIES = {"any", "free_only", "not_paid", "paid_ok"}
_ACCOUNT_POLICIES = {"any", "no_account", "account_ok", "account_required"}
_OPTIMIZATIONS = {"balanced", "queue", "cost", "capacity"}


class BackendConstraintError(ValueError):
    """Raised when the model emits an invalid backend-constraint object."""


def load_backends(path: Path = CAPABILITIES_PATH) -> List[Dict[str, Any]]:
    """Load and minimally validate the authoritative backend snapshot."""

    document = json.loads(path.read_text(encoding="utf-8"))
    backends = document.get("backends")
    if not isinstance(backends, list) or not backends:
        raise RuntimeError("backend capability snapshot has no backends")
    required = {
        "id",
        "platform",
        "kind",
        "max_qubits",
        "queue",
        "cost",
        "requires_account",
    }
    for backend in backends:
        if not isinstance(backend, dict) or not required.issubset(backend):
            raise RuntimeError("backend capability snapshot contains an invalid entry")
    return backends


def _optional_string_set(
    value: Any, *, name: str, allowed: Iterable[str]
) -> Optional[Tuple[str, ...]]:
    if value is None:
        return None
    values: Sequence[Any]
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        raise BackendConstraintError("%s must be a string, list, or null" % name)
    allowed_values = set(allowed)
    normalized = []
    for item in values:
        if not isinstance(item, str) or item not in allowed_values:
            raise BackendConstraintError("%s contains an unsupported value" % name)
        if item not in normalized:
            normalized.append(item)
    return tuple(normalized) if normalized else None


def normalize_constraints(value: Any) -> Dict[str, Any]:
    """Validate the compact constraint schema requested from the model."""

    if not isinstance(value, Mapping):
        raise BackendConstraintError("backend_constraints must be an object")

    min_qubits = value.get("min_qubits")
    if isinstance(min_qubits, bool) or (
        min_qubits is not None and not isinstance(min_qubits, int)
    ):
        raise BackendConstraintError("min_qubits must be an integer or null")
    if min_qubits is not None and min_qubits <= 0:
        raise BackendConstraintError("min_qubits must be positive")

    queue_policy = value.get("queue_policy", "any") or "any"
    cost_policy = value.get("cost_policy", "any") or "any"
    account_policy = value.get("account_policy", "any") or "any"
    optimize = value.get("optimize", "balanced") or "balanced"
    if queue_policy not in _QUEUE_POLICIES:
        raise BackendConstraintError("unsupported queue_policy")
    if cost_policy not in _COST_POLICIES:
        raise BackendConstraintError("unsupported cost_policy")
    if account_policy not in _ACCOUNT_POLICIES:
        raise BackendConstraintError("unsupported account_policy")
    if optimize not in _OPTIMIZATIONS:
        raise BackendConstraintError("unsupported optimize value")

    return {
        "min_qubits": min_qubits,
        "allowed_kinds": _optional_string_set(
            value.get("allowed_kinds"), name="allowed_kinds", allowed=_KINDS
        ),
        "allowed_platforms": _optional_string_set(
            value.get("allowed_platforms"),
            name="allowed_platforms",
            allowed=_PLATFORMS,
        ),
        "queue_policy": queue_policy,
        "cost_policy": cost_policy,
        "account_policy": account_policy,
        "optimize": optimize,
    }


def _matches(backend: Mapping[str, Any], constraints: Mapping[str, Any]) -> bool:
    min_qubits = constraints["min_qubits"]
    if min_qubits is not None and backend["max_qubits"] < min_qubits:
        return False
    if constraints["allowed_kinds"] and backend["kind"] not in constraints["allowed_kinds"]:
        return False
    if constraints["allowed_platforms"] and backend["platform"] not in constraints["allowed_platforms"]:
        return False

    queue_policy = constraints["queue_policy"]
    queue_rank = {"none": 0, "minutes_to_hours": 1, "hours": 2}
    queue_limits = {"none": 0, "up_to_minutes_to_hours": 1, "up_to_hours": 2}
    if queue_policy != "any" and queue_rank[backend["queue"]] > queue_limits[queue_policy]:
        return False

    cost_policy = constraints["cost_policy"]
    if cost_policy == "free_only" and backend["cost"] != "free":
        return False
    if cost_policy == "not_paid" and backend["cost"] == "paid":
        return False

    account_policy = constraints["account_policy"]
    if account_policy == "no_account" and backend["requires_account"]:
        return False
    if account_policy == "account_required" and not backend["requires_account"]:
        return False
    return True


def _rank_key(backend: Mapping[str, Any], constraints: Mapping[str, Any]) -> Tuple[Any, ...]:
    queue_rank = {"none": 0, "minutes_to_hours": 1, "hours": 2}
    cost_rank = {"free": 0, "free_quota": 1, "paid": 2}
    min_qubits = constraints["min_qubits"] or 1
    surplus = backend["max_qubits"] - min_qubits
    common = (
        queue_rank[backend["queue"]],
        cost_rank[backend["cost"]],
        int(backend["requires_account"]),
        surplus,
        backend["id"],
    )
    if constraints["optimize"] == "capacity":
        return (-backend["max_qubits"],) + common
    if constraints["optimize"] == "cost":
        return (cost_rank[backend["cost"]], queue_rank[backend["queue"]]) + common[2:]
    if constraints["optimize"] == "queue":
        return (queue_rank[backend["queue"]], cost_rank[backend["cost"]]) + common[2:]
    return common


def select_backends(
    raw_constraints: Any, backends: Optional[List[Dict[str, Any]]] = None
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Return normalized constraints and every satisfying backend in rank order."""

    constraints = normalize_constraints(raw_constraints)
    candidates = backends if backends is not None else load_backends()
    matches = [backend for backend in candidates if _matches(backend, constraints)]
    matches.sort(key=lambda backend: _rank_key(backend, constraints))
    return constraints, matches


def nearest_backend(
    constraints: Mapping[str, Any], backends: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """Return a deterministic closest alternative when the exact set is empty."""

    candidates = backends if backends is not None else load_backends()
    if not candidates:
        return None

    def violations(backend: Mapping[str, Any]) -> Tuple[Any, ...]:
        count = 0
        qubit_shortfall = 0
        minimum = constraints["min_qubits"]
        if minimum is not None and backend["max_qubits"] < minimum:
            count += 1
            qubit_shortfall = minimum - backend["max_qubits"]
        if constraints["allowed_kinds"] and backend["kind"] not in constraints["allowed_kinds"]:
            count += 1
        if constraints["allowed_platforms"] and backend["platform"] not in constraints["allowed_platforms"]:
            count += 1
        if constraints["queue_policy"] != "any":
            queue_rank = {"none": 0, "minutes_to_hours": 1, "hours": 2}
            queue_limits = {"none": 0, "up_to_minutes_to_hours": 1, "up_to_hours": 2}
            if queue_rank[backend["queue"]] > queue_limits[constraints["queue_policy"]]:
                count += 1
        if constraints["cost_policy"] == "free_only" and backend["cost"] != "free":
            count += 1
        if constraints["cost_policy"] == "not_paid" and backend["cost"] == "paid":
            count += 1
        if constraints["account_policy"] == "no_account" and backend["requires_account"]:
            count += 1
        if constraints["account_policy"] == "account_required" and not backend["requires_account"]:
            count += 1
        return (count, qubit_shortfall, _rank_key(backend, constraints))

    return min(candidates, key=violations)


def format_recommendation(raw_constraints: Any) -> str:
    """Select a backend and return a concise answer containing its canonical ID."""

    constraints, matches = select_backends(raw_constraints)
    if matches:
        selected = matches[0]
        return (
            "Recommended backend: {id}. It satisfies the requested constraints "
            "in the official LoomQ capability snapshot (kind={kind}, max_qubits={max_qubits}, "
            "queue={queue}, cost={cost}, requires_account={requires_account})."
        ).format(**selected)
    alternative = nearest_backend(constraints)
    if alternative is None:
        return "No backend in the official LoomQ capability snapshot satisfies all constraints."
    return (
        "No backend in the official LoomQ capability snapshot satisfies all constraints. "
        "Closest alternative: {id}; at least one requested constraint must be relaxed."
    ).format(**alternative)
