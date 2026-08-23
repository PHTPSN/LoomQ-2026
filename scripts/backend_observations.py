#!/usr/bin/env python3
"""Collect advisory live backend observations without submitting quantum work.

Formal LoomQ L2 selection remains based exclusively on
``starter_kit/backend_capabilities.json``. This module supplies optional,
timestamped operational context for development and an interactive product.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


AWS_BRAKET_REGIONS = (
    "us-east-1",
    "us-west-1",
    "us-west-2",
    "eu-north-1",
    "eu-west-2",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _base_observation(provider: str, source: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "source": source,
        "fetched_at": _now(),
        "advisory_only": True,
    }


def collect_originq(
    *,
    api_key: str | None = None,
    service_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Read Origin Quantum backend availability through the official SDK.

    The function never submits a task. Credentials are read from the explicit
    argument, ``ORIGINQ_API_KEY``, or ``QPANDA3_API_KEY``, in that order.
    """

    result = _base_observation(
        "originq", "pyqpanda3.qcloud.QCloudService.backends"
    )
    resolved_key = (
        api_key
        or os.environ.get("ORIGINQ_API_KEY")
        or os.environ.get("QPANDA3_API_KEY")
    )
    if not resolved_key:
        result.update(
            {
                "status": "authentication_required",
                "credential_environment": ["ORIGINQ_API_KEY", "QPANDA3_API_KEY"],
                "devices": [],
            }
        )
        return result

    try:
        if service_factory is None:
            from pyqpanda3.qcloud import QCloudService

            service_factory = QCloudService
        service = service_factory(api_key=resolved_key)
        backend_states = service.backends()
        if not isinstance(backend_states, Mapping):
            raise RuntimeError("QCloudService.backends() returned a non-mapping")
        result.update(
            {
                "status": "ok",
                "devices": [
                    {"id": str(name), "online": bool(online)}
                    for name, online in sorted(backend_states.items())
                ],
            }
        )
    except Exception as exc:
        result.update(
            {
                "status": "unavailable",
                "error_type": type(exc).__name__,
                "devices": [],
            }
        )
    return result


def _extract_qubit_count(capabilities: Any) -> int | None:
    if not isinstance(capabilities, str):
        return None
    try:
        parsed = json.loads(capabilities)
        value = parsed.get("paradigm", {}).get("qubitCount")
        return value if isinstance(value, int) and not isinstance(value, bool) else None
    except (AttributeError, TypeError, ValueError):
        return None


def _search_aws_region(client: Any) -> Iterable[dict[str, Any]]:
    next_token: str | None = None
    while True:
        request: dict[str, Any] = {"filters": [], "maxResults": 100}
        if next_token:
            request["nextToken"] = next_token
        page = client.search_devices(**request)
        yield from page.get("devices", [])
        next_token = page.get("nextToken")
        if not next_token:
            return


def collect_aws_braket(
    *,
    regions: Iterable[str] = AWS_BRAKET_REGIONS,
    profile: str | None = None,
    client_factory: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Read Braket device status and queue depth through official read APIs.

    Only ``SearchDevices`` and ``GetDevice`` are called. No quantum task, S3
    resource, reservation, or spending limit is created or modified.
    """

    result = _base_observation("aws_braket", "Amazon Braket API")
    if client_factory is None:
        try:
            import boto3

            session = boto3.Session(profile_name=profile)
            client_factory = lambda region: session.client(
                "braket", region_name=region
            )
        except Exception as exc:
            result.update(
                {
                    "status": "unavailable",
                    "error_type": type(exc).__name__,
                    "devices": [],
                }
            )
            return result

    devices: dict[str, dict[str, Any]] = {}
    region_errors: list[dict[str, str]] = []
    for region in regions:
        try:
            client = client_factory(region)
            for summary in _search_aws_region(client):
                arn = summary.get("deviceArn")
                if not arn or arn in devices:
                    continue
                details = client.get_device(deviceArn=arn)
                devices[arn] = {
                    "id": arn,
                    "name": details.get("deviceName", summary.get("deviceName")),
                    "provider": details.get(
                        "providerName", summary.get("providerName")
                    ),
                    "type": details.get("deviceType", summary.get("deviceType")),
                    "status": details.get("deviceStatus", summary.get("deviceStatus")),
                    "region_checked": region,
                    "qubits": _extract_qubit_count(details.get("deviceCapabilities")),
                    "queues": details.get("deviceQueueInfo", []),
                }
        except Exception as exc:
            region_errors.append(
                {"region": region, "error_type": type(exc).__name__}
            )

    authentication_errors = {
        "AccessDeniedException",
        "NoCredentialsError",
        "PartialCredentialsError",
        "ProfileNotFound",
        "UnauthorizedException",
        "UnrecognizedClientException",
    }
    if devices:
        status = "partial" if region_errors else "ok"
    elif region_errors and all(
        error["error_type"] in authentication_errors for error in region_errors
    ):
        status = "authentication_required"
    elif region_errors:
        status = "unavailable"
    else:
        status = "ok"
    result.update(
        {
            "status": status,
            "profile": profile or os.environ.get("AWS_PROFILE") or "default",
            "devices": sorted(devices.values(), key=lambda item: item["id"]),
            "region_errors": region_errors,
            "required_permissions": ["braket:SearchDevices", "braket:GetDevice"],
        }
    )
    return result


def build_report(
    providers: Iterable[str],
    *,
    originq_api_key: str | None = None,
    aws_profile: str | None = None,
    aws_regions: Iterable[str] = AWS_BRAKET_REGIONS,
) -> dict[str, Any]:
    observations = []
    for provider in providers:
        if provider == "originq":
            observations.append(collect_originq(api_key=originq_api_key))
        elif provider == "aws":
            observations.append(
                collect_aws_braket(profile=aws_profile, regions=aws_regions)
            )
        else:
            raise ValueError(f"unsupported observation provider: {provider}")
    return {
        "schema_version": "1.0",
        "generated_at": _now(),
        "formal_l2_baseline": "starter_kit/backend_capabilities.json",
        "observations": observations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=("originq", "aws", "all"),
        default="all",
    )
    parser.add_argument("--aws-profile")
    parser.add_argument("--aws-region", action="append", dest="aws_regions")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    providers = ("originq", "aws") if args.provider == "all" else (args.provider,)
    report = build_report(
        providers,
        aws_profile=args.aws_profile,
        aws_regions=args.aws_regions or AWS_BRAKET_REGIONS,
    )
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
