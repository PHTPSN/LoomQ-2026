#!/usr/bin/env python3
"""Create a temporary SpinQ Cloud visitor session without browser automation.

This helper targets the web application's observed visitor endpoint. It is a
development convenience, not a documented public SpinQ API and not an input to
the deterministic LoomQ L2 evaluator.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.request import Request, urlopen


VISITOR_LOGIN_URL = "https://cloud.spinq.cn/prod/api/user/loginAsVisitor"


@dataclass(frozen=True)
class SpinQVisitorSession:
    """A short-lived visitor session returned by SpinQ Cloud."""

    token: str
    status: int
    message: str
    name: str
    has_password: bool

    def auth_headers(self, *, language: str = "en") -> dict[str, str]:
        """Return headers for a follow-up SpinQ web API request."""

        return {
            "Accept": "application/json",
            "lang": language,
            "token": self.token,
        }

    def redacted_summary(self) -> dict[str, Any]:
        """Describe the session without exposing its bearer-like token."""

        return {
            "endpoint": VISITOR_LOGIN_URL,
            "method": "POST",
            "status": self.status,
            "message": self.message,
            "name": self.name,
            "has_password": self.has_password,
            "token_present": bool(self.token),
            "token_length": len(self.token),
        }


def create_visitor_session(
    *,
    timeout: float = 15.0,
    opener: Callable[..., Any] = urlopen,
) -> SpinQVisitorSession:
    """Request a new visitor token and keep it in memory.

    ``opener`` is injectable so callers can test this function without network
    access. The request intentionally has no body, matching SpinQ's web client.
    """

    request = Request(
        VISITOR_LOGIN_URL,
        method="POST",
        headers={"Accept": "application/json", "lang": "en"},
    )
    with opener(request, timeout=timeout) as response:
        payload = json.load(response)

    if not isinstance(payload, dict):
        raise RuntimeError("SpinQ visitor login returned a non-object response")

    status = payload.get("status")
    token = payload.get("token")
    if status != 200 or not isinstance(token, str) or not token:
        message = payload.get("msg") or "unknown visitor-login error"
        raise RuntimeError(f"SpinQ visitor login failed: status={status}, msg={message}")

    return SpinQVisitorSession(
        token=token,
        status=status,
        message=str(payload.get("msg") or ""),
        name=str(payload.get("name") or ""),
        has_password=bool(payload.get("hasPassword", False)),
    )


def main() -> None:
    """Probe the endpoint while keeping the returned token out of logs."""

    session = create_visitor_session()
    print(json.dumps(session.redacted_summary(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
