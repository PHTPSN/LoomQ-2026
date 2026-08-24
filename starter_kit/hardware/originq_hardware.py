#!/usr/bin/env python3
"""Prepare, submit, and collect Origin Quantum real-hardware evidence.

The three commands are intentionally separate:

* ``prepare`` is offline and writes the exact OriginIR artifact.
* ``submit`` is the only command that creates a real-chip task.
* ``poll`` resumes by task ID and writes provider plus normalized evidence.

Credentials are read only from ``LOOMQ_ORIGINQ_API_TOKEN`` and are never
written to evidence files or included in diagnostic messages.
"""

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "starter_kit" / "circuits" / "bell.qasm"
DEFAULT_EVIDENCE = ROOT / "starter_kit" / "evidence" / "files"
BELL_EVIDENCE = DEFAULT_EVIDENCE / "originq-bell"
GHZ3_EVIDENCE = DEFAULT_EVIDENCE / "originq-ghz3"
EXECUTED_IR = BELL_EVIDENCE / "originq-bell-executed.originir"
TASK_RECORD = BELL_EVIDENCE / "originq-bell-task.json"
SDK_RESULT = BELL_EVIDENCE / "originq-bell-sdk-result.json"
NORMALIZED_RESULT = BELL_EVIDENCE / "originq-bell-normalized-result.json"
FINISHED_STATUS = 3
FAILED_STATUS = 4

PROFILES = {
    "bell": {
        "source": DEFAULT_SOURCE,
        "executed_ir": EXECUTED_IR,
        "task_record": TASK_RECORD,
        "sdk_result": SDK_RESULT,
        "normalized_result": NORMALIZED_RESULT,
        "expected_top_states": {"00", "11"},
        "default_task_name": "LoomQ L1 Bell evidence",
    },
    "ghz3": {
        "source": ROOT / "starter_kit" / "circuits" / "ghz3.qasm",
        "executed_ir": GHZ3_EVIDENCE / "originq-ghz3-executed.originir",
        "task_record": GHZ3_EVIDENCE / "originq-ghz3-task.json",
        "sdk_result": GHZ3_EVIDENCE / "originq-ghz3-sdk-result.json",
        "normalized_result": GHZ3_EVIDENCE / "originq-ghz3-normalized-result.json",
        "expected_top_states": {"000", "111"},
        "default_task_name": "LoomQ L1 GHZ-3 evidence",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("task record must contain a JSON object")
    return value


def _secret() -> str:
    token = os.environ.get("LOOMQ_ORIGINQ_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("LOOMQ_ORIGINQ_API_TOKEN is not configured")
    return token


def _safe_error(exc: BaseException, token: str = "") -> str:
    text = str(exc)
    if token:
        text = text.replace(token, "[redacted]")
    return "%s: %s" % (type(exc).__name__, text or "provider request failed")


def probabilities_to_counts(values: Mapping[str, Any], shots: int) -> Dict[str, int]:
    """Convert provider probabilities to integer counts using largest remainder."""

    if shots <= 0:
        raise ValueError("shots must be positive")
    numeric = {str(key): float(value) for key, value in values.items()}
    if not numeric or any(not math.isfinite(value) or value < 0 for value in numeric.values()):
        raise ValueError("provider result must contain finite non-negative values")
    total = sum(numeric.values())
    if total <= 0:
        raise ValueError("provider result total must be positive")

    # Some API variants return counts and others return probabilities.
    if all(float(value).is_integer() for value in numeric.values()) and round(total) == shots:
        return dict(sorted((key, int(value)) for key, value in numeric.items()))

    scaled = {key: value * shots / total for key, value in numeric.items()}
    counts = {key: int(math.floor(value)) for key, value in scaled.items()}
    remaining = shots - sum(counts.values())
    order = sorted(scaled, key=lambda key: (-(scaled[key] - counts[key]), key))
    for key in order[:remaining]:
        counts[key] += 1
    return dict(sorted(counts.items()))


def result_measurements(result: Any) -> Mapping[str, Any]:
    """Return the first nonempty count or probability mapping from a result."""

    for accessor in ("get_counts", "get_probs"):
        try:
            values = getattr(result, accessor)()
        except Exception:
            continue
        if isinstance(values, Mapping) and values:
            return values
    raise ValueError("provider result contains no measurement probabilities or counts")


def _top_k_pass(counts: Mapping[str, int], expected_top_states=None) -> bool:
    if expected_top_states is None:
        expected_top_states = {"00", "11"}
    top = sorted(counts, key=lambda key: (-counts[key], key))[:2]
    return set(top) == set(expected_top_states)


def profile_config(profile: str) -> Dict[str, Any]:
    try:
        return PROFILES[profile]
    except KeyError as exc:
        raise ValueError("unknown evidence profile: %s" % profile) from exc


def prepare(source_path: Path = DEFAULT_SOURCE, output_path: Path = EXECUTED_IR) -> Path:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from starter_kit import adapter

    source = source_path.read_text(encoding="utf-8")
    origin_ir = adapter.transpile(source, "originq")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(origin_ir, encoding="utf-8")
    return output_path


def _qcloud(token: str):
    try:
        from pyqpanda3.qcloud import QCloudService
    except ImportError as exc:
        raise RuntimeError(
            "pyqpanda3 is unavailable; run this command with the hardware-only container"
        ) from exc
    return QCloudService(api_key=token)


def preflight(backend_name: str) -> Dict[str, Any]:
    """Validate credentials and backend availability without creating a task."""

    token = _secret()
    try:
        service = _qcloud(token)
        try:
            available = service.backends()
        except Exception:
            # Some service responses are not decoded cleanly by ``backends``.
            # A metadata request is still read-only and provides a clearer
            # authentication/availability error without creating a task.
            service.backend(backend_name).chip_info()
            available = {backend_name: True}
        if backend_name not in available:
            raise RuntimeError("backend %s is not listed for this account" % backend_name)
        return {
            "backend": backend_name,
            "available": bool(available[backend_name]),
            "checked_at": _utc_now(),
        }
    except Exception as exc:
        raise RuntimeError(_safe_error(exc, token)) from None


def submit(
    shots: int,
    backend_name: str,
    task_name: str,
    confirm: bool,
    profile: str = "bell",
) -> Dict[str, Any]:
    config = profile_config(profile)
    executed_ir = config["executed_ir"]
    task_record = config["task_record"]
    if not confirm:
        raise RuntimeError("refusing real-hardware submission without --confirm-real-hardware")
    if not executed_ir.is_file():
        raise RuntimeError("executed OriginIR is missing; run the prepare command first")
    if task_record.exists():
        existing = _read_json(task_record)
        raise RuntimeError(
            "a task record already exists for job %s; archive it before another submission"
            % existing.get("job_id", "unknown")
        )
    token = _secret()
    try:
        from pyqpanda3.intermediate_compiler import convert_originir_string_to_qprog
        from pyqpanda3.qcloud import QCloudOptions

        service = _qcloud(token)
        available = service.backends()
        if backend_name not in available:
            raise RuntimeError("backend %s is not listed for this account" % backend_name)
        if not available[backend_name]:
            raise RuntimeError("backend %s is currently unavailable" % backend_name)
        backend = service.backend(backend_name)
        program = convert_originir_string_to_qprog(executed_ir.read_text(encoding="utf-8"))
        options = QCloudOptions()
        options.set_amend(True)
        options.set_mapping(True)
        options.set_optimization(True)
        job = backend.run(program, shots, options)
        job_id = job.job_id()
    except Exception as exc:
        raise RuntimeError(_safe_error(exc, token)) from None
    if not isinstance(job_id, str) or not job_id.strip():
        raise RuntimeError("Origin Quantum returned no task ID")
    record = {
        "provider": "origin_quantum",
        "device": backend_name,
        "job_id": job_id.strip(),
        "shots": shots,
        "submitted_at": _utc_now(),
        "status": "submitted",
        "task_name": task_name,
        "profile": profile,
        "source_qasm": str(config["source"].relative_to(ROOT)).replace("\\", "/"),
        "executed_ir": str(executed_ir.relative_to(ROOT)).replace("\\", "/"),
    }
    _write_json(task_record, record)
    return record


def poll(wait: bool, timeout: int, interval: int, profile: str = "bell") -> Dict[str, Any]:
    config = profile_config(profile)
    task_record = config["task_record"]
    sdk_result = config["sdk_result"]
    normalized_result = config["normalized_result"]
    record = _read_json(task_record)
    token = _secret()
    deadline = time.monotonic() + timeout
    try:
        from pyqpanda3.qcloud import JobStatus, QCloudJob

        # QCloudJob uses the credential initialized by QCloudService in this
        # process when querying historical jobs.
        _qcloud(token)
        job = QCloudJob(record["job_id"])
        while True:
            status = job.status()
            status_code = int(status.value)
            provider_result = {
                "provider": "origin_quantum",
                "job_id": record["job_id"],
                "queried_at": _utc_now(),
                "status_code": status_code,
                "status_name": status.name,
            }
            if status == JobStatus.FINISHED:
                # Fetch the standard result first. Supplying ``keys`` asks the
                # service for optional fields and can omit the normal
                # probability payload from that response.
                result = job.result()
                metadata_result = job.result(
                    keys=["convertQProg", "mappingQprog", "mappingQubit"]
                )
                raw_fields = {}
                field_names = (
                    "origin_data", "prob_count_raw", "instructions",
                    "mapping_qprog", "mapping_qubit", "measure_qubits",
                    "src_qubits", "target_cbits", "timing_info",
                )
                for prefix, source in (
                    ("result", result),
                    ("metadata", metadata_result),
                ):
                    for name in field_names:
                        try:
                            value = getattr(source, name)()
                        except Exception:
                            continue
                        try:
                            json.dumps(value)
                        except TypeError:
                            value = repr(value)
                        raw_fields["%s_%s" % (prefix, name)] = value
                counts_or_probs = result_measurements(result)
                provider_result["result"] = counts_or_probs
                provider_result["raw_fields"] = raw_fields
            _write_json(sdk_result, provider_result)
            if status_code in (FINISHED_STATUS, FAILED_STATUS) or not wait:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("poll timeout; the task ID remains saved and can be polled later")
            time.sleep(interval)
    except Exception as exc:
        raise RuntimeError(_safe_error(exc, token)) from None

    if int(provider_result["status_code"]) == FINISHED_STATUS:
        if not isinstance(provider_result["result"], dict):
            raise RuntimeError("completed provider result is not a probability/count object")
        provider_values = provider_result["result"]
        shots = int(record["shots"])
        provider_total = sum(float(value) for value in provider_values.values())
        provider_value_kind = (
            "counts"
            if all(float(value).is_integer() for value in provider_values.values())
            and round(provider_total) == shots
            else "probabilities"
        )
        counts = probabilities_to_counts(provider_values, shots)
        completed_at = _utc_now()
        normalized = {
            "backend": record["device"],
            "job_id": record["job_id"],
            "shots": record["shots"],
            "counts": counts,
            "bit_order": "little",
            "timestamp": completed_at,
            "meta": {
                "hardware": True,
                "provider": "origin_quantum",
                "provider_value_kind": provider_value_kind,
                "count_normalization": (
                    "provider counts preserved"
                    if provider_value_kind == "counts"
                    else "largest-remainder conversion from provider probabilities"
                ),
                "top_k_pass": _top_k_pass(counts, config["expected_top_states"]),
                "expected_top_states": sorted(config["expected_top_states"]),
                "provider_result": sdk_result.name,
                "timestamp_source": "local collection time; verify platform time in task screenshot",
            },
        }
        if profile == "bell":
            normalized["meta"]["top_k_bell_pass"] = normalized["meta"]["top_k_pass"]
        _write_json(normalized_result, normalized)
        record.update({"status": "finished", "collected_at": completed_at})
        _write_json(task_record, record)
    elif int(provider_result["status_code"]) == FAILED_STATUS:
        record["status"] = "failed"
        _write_json(task_record, record)
    return provider_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Origin Quantum real-hardware evidence tool")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare", help="offline: emit exact OriginIR")
    prepare_parser.add_argument("--profile", choices=tuple(PROFILES), default="bell")
    prepare_parser.add_argument("--source", type=Path)
    preflight_parser = commands.add_parser(
        "preflight", help="read-only: verify credentials and backend availability"
    )
    preflight_parser.add_argument(
        "--backend", default=os.environ.get("LOOMQ_ORIGINQ_BACKEND", "WK_C180")
    )
    submit_parser = commands.add_parser("submit", help="create one real-chip task")
    submit_parser.add_argument("--profile", choices=tuple(PROFILES), default="bell")
    submit_parser.add_argument("--shots", type=int, default=512)
    submit_parser.add_argument(
        "--backend", default=os.environ.get("LOOMQ_ORIGINQ_BACKEND", "WK_C180")
    )
    submit_parser.add_argument("--task-name")
    submit_parser.add_argument("--confirm-real-hardware", action="store_true")
    poll_parser = commands.add_parser("poll", help="query the saved task ID")
    poll_parser.add_argument("--profile", choices=tuple(PROFILES), default="bell")
    poll_parser.add_argument("--wait", action="store_true")
    poll_parser.add_argument("--timeout", type=int, default=1800)
    poll_parser.add_argument("--interval", type=int, default=10)
    args = parser.parse_args()

    try:
        if args.command == "prepare":
            config = profile_config(args.profile)
            path = prepare(args.source or config["source"], config["executed_ir"])
            print("prepared %s" % path.relative_to(ROOT))
        elif args.command == "preflight":
            status = preflight(args.backend)
            print(
                "Origin Quantum backend %s available=%s"
                % (status["backend"], str(status["available"]).lower())
            )
        elif args.command == "submit":
            if args.shots <= 0:
                raise RuntimeError("shots must be positive")
            config = profile_config(args.profile)
            record = submit(
                args.shots,
                args.backend,
                args.task_name or config["default_task_name"],
                args.confirm_real_hardware,
                args.profile,
            )
            print("submitted Origin Quantum task %s" % record["job_id"])
            print("task record: %s" % config["task_record"].relative_to(ROOT))
        else:
            config = profile_config(args.profile)
            provider_result = poll(args.wait, args.timeout, args.interval, args.profile)
            print(
                "Origin Quantum task %s status=%s"
                % (provider_result["job_id"], provider_result["status_code"])
            )
            print("provider result: %s" % config["sdk_result"].relative_to(ROOT))
    except Exception as exc:
        print("error: %s" % _safe_error(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
