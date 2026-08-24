"""Opt-in 36-case robustness evaluation for the LoomQ Level 2 agent.

This is a local development pack, not the competition's undisclosed 12 cases.
It deliberately varies language, formatting, state families, and constraints.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .agent import agent_chat
from .backend import nearest_backend, select_backends
from .qasm import require_measurements, target_state_fidelity


FORMAL_MODEL = "deepseek-v4-flash"


@dataclass(frozen=True)
class RobustnessCase:
    name: str
    category: str
    prompt: str
    target_state: Optional[Mapping[str, Any]] = None
    backend_constraints: Optional[Mapping[str, Any]] = None


def _state(*items: Tuple[str, Any]) -> Dict[str, Any]:
    return dict(items)


SQRT2 = math.sqrt(0.5)
SQRT3 = math.sqrt(1.0 / 3.0)
SQRT4 = 0.5


GENERATION_CASES: Tuple[RobustnessCase, ...] = (
    RobustnessCase("gen-bell-en", "generation", "Create and measure a two-qubit Bell state (|00> + |11>)/sqrt(2). Return OpenQASM 2.0.", _state(("00", SQRT2), ("11", SQRT2))),
    RobustnessCase("gen-ghz3-zh", "generation", "请生成三量子比特 GHZ 态，并测量所有量子比特。", _state(("000", SQRT2), ("111", SQRT2))),
    RobustnessCase("gen-ghz4-paraphrase", "generation", "Entangle four qubits so that only 0000 and 1111 can be observed, each with equal probability; measure all four.", _state(("0000", SQRT2), ("1111", SQRT2))),
    RobustnessCase("gen-w3", "generation", "Prepare the 3-qubit W state with equal amplitudes on |001>, |010>, and |100>, then measure.", _state(("001", SQRT3), ("010", SQRT3), ("100", SQRT3))),
    RobustnessCase("gen-basis-101", "generation", "Build a three-qubit circuit whose measured state is certainly 101 (bit string ordered q2 q1 q0).", _state(("101", 1.0),)),
    RobustnessCase("gen-basis-0101", "generation", "用 4 个量子比特制备 |0101⟩，并把每个量子比特测量到对应经典位。", _state(("0101", 1.0),)),
    RobustnessCase("gen-plus-zero", "generation", "Prepare |+0> where labels use q1q0 order, then measure both qubits.", _state(("00", SQRT2), ("10", SQRT2))),
    RobustnessCase("gen-minus", "generation", "Create the one-qubit |-> state = (|0>-|1>)/sqrt(2) and measure it.", _state(("0", SQRT2), ("1", -SQRT2))),
    RobustnessCase("gen-complex-bell", "generation", "Prepare (|00> + i|11>)/sqrt(2), preserving the relative phase, and measure both qubits.", _state(("00", SQRT2), ("11", [0.0, SQRT2]))),
    RobustnessCase("gen-psi-plus", "generation", "Generate the Bell state psi-plus: (|01> + |10>)/sqrt(2). Add full measurement.", _state(("01", SQRT2), ("10", SQRT2))),
    RobustnessCase("gen-toffoli-result", "generation", "Starting from |000>, use the allowed gates so a Toffoli produces |111>, then measure all three qubits.", _state(("111", 1.0),)),
    RobustnessCase("gen-swapped-one", "generation", "Put q0 in |1>, swap q0 with q1, and measure; the q1q0 target is |10>.", _state(("10", 1.0),)),
)


REPAIR_CASES: Tuple[RobustnessCase, ...] = (
    RobustnessCase("repair-bell-case-comma", "repair", "Repair this malformed Bell circuit without changing its target (|00>+|11>)/sqrt(2):\nOPENQASM 2.0\ninclude \"qelib1.inc\"\nqreg q[2]\ncreg c[2]\nH q[0]\nCX q[0] q[1]\nmeasure q -> c", _state(("00", SQRT2), ("11", SQRT2))),
    RobustnessCase("repair-ghz3-measurement", "repair", "This should prepare GHZ3 but forgot classical output. Repair it and measure every qubit:\nOPENQASM 2.0; include \"qelib1.inc\"; qreg q[3]; h q[0]; cx q[0],q[1]; cx q[0],q[2];", _state(("000", SQRT2), ("111", SQRT2))),
    RobustnessCase("repair-wrong-basis-101", "repair", "Fix the circuit so the final measured q2q1q0 state is exactly |101>; it currently flips the wrong qubit:\nOPENQASM 2.0; include \"qelib1.inc\"; qreg q[3]; creg c[3]; x q[1]; measure q -> c;", _state(("101", 1.0),)),
    RobustnessCase("repair-plus", "repair", "修复下面的线路，使目标态为 |+> 并进行测量： OPENQASM 2.0; include \"qelib1.inc\"; qreg q[1]; creg c[1]; x q[0]; measure q -> c;", _state(("0", SQRT2), ("1", SQRT2))),
    RobustnessCase("repair-complex-phase", "repair", "Repair the semantic error: the target is (|00>+i|11>)/sqrt(2), not an ordinary Bell state. Include full measurement. Current body: h q[0]; cx q[0],q[1];", _state(("00", SQRT2), ("11", [0.0, SQRT2]))),
    RobustnessCase("repair-w3-fragment", "repair", "Replace this invalid fragment with a complete allowed-gate OpenQASM 2 circuit for W3 = (|001>+|010>+|100>)/sqrt(3), then measure: w q[0],q[1],q[2];", _state(("001", SQRT3), ("010", SQRT3), ("100", SQRT3))),
    RobustnessCase("repair-swap-direction", "repair", "The target q1q0 state is |10>, but this program returns |01>. Repair and measure it: OPENQASM 2.0; include \"qelib1.inc\"; qreg q[2]; creg c[2]; x q[0]; measure q -> c;", _state(("10", 1.0),)),
    RobustnessCase("repair-toffoli-controls", "repair", "Repair this so the measured target is |111>. The Toffoli controls were never enabled: OPENQASM 2.0; include \"qelib1.inc\"; qreg q[3]; creg c[3]; ccx q[0],q[1],q[2]; measure q -> c;", _state(("111", 1.0),)),
    RobustnessCase("repair-minus-sign", "repair", "This makes |+>, but the target is |-> = (|0>-|1>)/sqrt(2). Correct it using allowed gates and keep measurement: h q[0];", _state(("0", SQRT2), ("1", -SQRT2))),
    RobustnessCase("repair-ghz4-width", "repair", "Repair the incomplete GHZ circuit to produce (|0000>+|1111>)/sqrt(2) on four qubits and measure all: h q[0]; cx q[0],q[1]; cx q[0],q[2];", _state(("0000", SQRT2), ("1111", SQRT2))),
    RobustnessCase("repair-psi-plus", "repair", "The circuit currently produces phi-plus. Change it to psi-plus (|01>+|10>)/sqrt(2) and measure both: h q[0]; cx q[0],q[1];", _state(("01", SQRT2), ("10", SQRT2))),
    RobustnessCase("repair-registers", "repair", "Turn this gate-only snippet into complete OpenQASM 2.0 for target |0101> in q3q2q1q0 order, with matching registers and full measurement: x q[0]; x q[2];", _state(("0101", 1.0),)),
)


def _backend(name: str, prompt: str, **constraints: Any) -> RobustnessCase:
    defaults = {
        "min_qubits": None,
        "allowed_kinds": None,
        "allowed_platforms": None,
        "queue_policy": "any",
        "cost_policy": "any",
        "account_policy": "any",
        "optimize": "balanced",
    }
    defaults.update(constraints)
    return RobustnessCase(name, "backend", prompt, backend_constraints=defaults)


BACKEND_CASES: Tuple[RobustnessCase, ...] = (
    _backend("backend-15-no-queue", "I need at least 15 qubits and cannot wait in a queue. Which backend fits?", min_qubits=15, queue_policy="none"),
    _backend("backend-26-no-queue-zh", "我需要至少 26 个量子比特，而且不能排队，请推荐后端。", min_qubits=26, queue_policy="none"),
    _backend("backend-real-no-pay", "Recommend real quantum hardware with at least 5 qubits, but I cannot pay; an included free quota is acceptable.", min_qubits=5, allowed_kinds=["qpu"], cost_policy="not_paid"),
    _backend("backend-qpu-10", "Choose a physical QPU with ten or more qubits. I can register and pay if necessary.", min_qubits=10, allowed_kinds=["qpu"], account_policy="account_ok", cost_policy="paid_ok"),
    _backend("backend-braket-no-account", "I want an Amazon Braket option for 20 qubits without creating or using an account.", min_qubits=20, allowed_platforms=["braket"], account_policy="no_account"),
    _backend("backend-originq-local", "Select an Origin Quantum backend with no queue and at least 20 qubits.", min_qubits=20, allowed_platforms=["originq"], queue_policy="none"),
    _backend("backend-spinq-free-exact", "SpinQ only, at least 20 qubits, and only an exactly free backend—not credits or a quota.", min_qubits=20, allowed_platforms=["spinq"], cost_policy="free_only"),
    _backend("backend-free-capacity", "Among strictly free choices, prioritize the largest qubit capacity.", cost_policy="free_only", optimize="capacity"),
    _backend("backend-fast-simulator", "I need a simulator with 18 qubits and zero queue; optimize for queue time.", min_qubits=18, allowed_kinds=["simulator"], queue_policy="none", optimize="queue"),
    _backend("backend-account-required", "I specifically need a backend that requires an account and has at least 10 qubits.", min_qubits=10, account_policy="account_required"),
    _backend("backend-cloud-platforms", "Pick a cloud backend from SpinQ or Origin Quantum with at least 5 qubits and no personal payment.", min_qubits=5, allowed_kinds=["cloud"], allowed_platforms=["spinq", "originq"], cost_policy="not_paid"),
    _backend("backend-impossible-qpu-no-login", "I need a real QPU with at least five qubits, but I refuse any account or login. State if no exact match exists and give the closest option.", min_qubits=5, allowed_kinds=["qpu"], account_policy="no_account"),
)


ALL_CASES: Tuple[RobustnessCase, ...] = GENERATION_CASES + REPAIR_CASES + BACKEND_CASES


def _expected_backend(case: RobustnessCase) -> Tuple[str, bool]:
    constraints, matches = select_backends(case.backend_constraints)
    if matches:
        return matches[0]["id"], True
    alternative = nearest_backend(constraints)
    if alternative is None:
        return "", False
    return alternative["id"], False


def grade_answer(case: RobustnessCase, answer: str) -> Tuple[bool, str]:
    """Grade one local response without consulting the model or a network."""

    if case.category in {"generation", "repair"}:
        require_measurements(answer)
        fidelity = target_state_fidelity(answer, case.target_state)
        passed = fidelity is not None and fidelity >= 0.97
        return passed, "target-state fidelity=%.6f" % (fidelity or 0.0)
    expected, exact = _expected_backend(case)
    passed = bool(expected and expected in answer)
    if not exact:
        passed = passed and answer.startswith("No backend")
    return passed, "expected %s backend=%s" % ("exact" if exact else "closest", expected)


def _run_case(case: RobustnessCase) -> Dict[str, Any]:
    started = time.monotonic()
    try:
        answer = agent_chat(case.prompt)
        passed, detail = grade_answer(case, answer)
        return {
            "name": case.name,
            "category": case.category,
            "status": "PASS" if passed else "FAIL",
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "detail": detail,
            "answer": answer,
        }
    except Exception as exc:
        return {
            "name": case.name,
            "category": case.category,
            "status": "ERROR",
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "detail": "%s: %s" % (type(exc).__name__, str(exc)),
            "answer": None,
        }


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if name and name not in os.environ:
            os.environ[name] = value


def run_suite(*, jobs: int = 3) -> Dict[str, Any]:
    if jobs < 1 or jobs > 8:
        raise ValueError("jobs must be between 1 and 8")
    started = time.monotonic()
    indexed: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = {executor.submit(_run_case, case): case for case in ALL_CASES}
        for future in as_completed(futures):
            result = future.result()
            indexed[result["name"]] = result
            print("%-5s %-8s %s" % (result["status"], result["category"], result["name"]), flush=True)
    results = [indexed[case.name] for case in ALL_CASES]
    passed = sum(result["status"] == "PASS" for result in results)
    model = os.environ.get("LOOMQ_LLM_MODEL", "")
    pass_rate = passed / len(results)
    return {
        "schema": "loomq-l2-local-robustness-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "formal_model_match": model == FORMAL_MODEL,
        "disclaimer": "Local adversarial development pack; these are not the competition's hidden cases or an official score.",
        "case_count": len(results),
        "passed": passed,
        "pass_rate": round(pass_rate, 6),
        "local_objective_score_estimate": round(pass_rate * 20.0, 3),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "results": results,
    }


def regrade_report(value: Mapping[str, Any]) -> Dict[str, Any]:
    """Regrade saved agent answers after a transparent grader correction."""

    report = dict(value)
    raw_results = report.get("results")
    if not isinstance(raw_results, list):
        raise ValueError("report has no results list")
    cases = {case.name: case for case in ALL_CASES}
    if {item.get("name") for item in raw_results if isinstance(item, Mapping)} != set(cases):
        raise ValueError("report case names do not match the current 36-case pack")
    results = []
    for raw_result in raw_results:
        result = dict(raw_result)
        answer = result.get("answer")
        try:
            if not isinstance(answer, str):
                raise ValueError("saved answer is missing")
            passed, detail = grade_answer(cases[result["name"]], answer)
            result["status"] = "PASS" if passed else "FAIL"
            result["detail"] = detail
        except Exception as exc:
            result["status"] = "ERROR"
            result["detail"] = "%s: %s" % (type(exc).__name__, str(exc))
        results.append(result)
    passed = sum(result["status"] == "PASS" for result in results)
    pass_rate = passed / len(results)
    report.update(
        {
            "regraded_at": datetime.now(timezone.utc).isoformat(),
            "grading_revision": "Corrected |+0> q1q0 target ordering; no model answers were changed.",
            "case_count": len(results),
            "passed": passed,
            "pass_rate": round(pass_rate, 6),
            "local_objective_score_estimate": round(pass_rate * 20.0, 3),
            "results": results,
        }
    )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--regrade-report",
        type=Path,
        help="Regrade the saved answers in a prior report without making model calls.",
    )
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument(
        "--allow-other-model",
        action="store_true",
        help="Allow a development run, but never label it as formal-model compatible.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    _load_env_file(args.env_file)
    prior_report = None
    if args.regrade_report:
        prior_report = json.loads(args.regrade_report.read_text(encoding="utf-8"))
    model = (
        prior_report.get("model", "")
        if isinstance(prior_report, Mapping)
        else os.environ.get("LOOMQ_LLM_MODEL", "")
    )
    if model != FORMAL_MODEL and not args.allow_other_model:
        print(
            "Refusing a formal-model run: LOOMQ_LLM_MODEL is %r, expected %r. "
            "Use --allow-other-model only for a clearly labeled development run."
            % (model, FORMAL_MODEL)
        )
        return 2
    report = regrade_report(prior_report) if prior_report is not None else run_suite(jobs=args.jobs)
    output_path = args.json_out or args.regrade_report
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Report: %s" % output_path)
    print(
        "Passed {passed}/{case_count} ({pass_rate:.1%}); local objective estimate "
        "{local_objective_score_estimate:.3f}/20; formal model match={formal_model_match}".format(**report)
    )
    return 0 if report["passed"] == report["case_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
