"""Loopback-only web interface for the LoomQ Level 2 agent."""

from __future__ import annotations

import argparse
import hmac
import ipaddress
import json
import mimetypes
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlparse

try:
    from .agent import agent_chat
    from ..adapter import run as run_circuit
except ImportError:
    from agent import agent_chat
    from starter_kit.adapter import run as run_circuit


UI_ROOT = Path(__file__).resolve().parent / "ui"
MAX_REQUEST_BYTES = 64 * 1024
MAX_PROMPT_CHARACTERS = 24_000
MAX_HISTORY_MESSAGES = 6
MAX_HISTORY_CHARACTERS = 4_000
MAX_SIMULATOR_SHOTS = 8_192
SIMULATOR_TARGETS = {
    "spinq": "SpinQit Basic Simulator",
    "originq": "Origin Quantum CPU Simulator",
    "braket": "Amazon Braket Local Simulator",
}


def _load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE entries without replacing injected variables."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or name in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[name] = value


def _model_configured() -> bool:
    return all(
        os.environ.get(name)
        for name in ("LOOMQ_LLM_BASE_URL", "LOOMQ_LLM_API_KEY", "LOOMQ_LLM_MODEL")
    )


def _safe_error(exc: Exception) -> str:
    message = str(exc).strip() or "The agent could not complete this request."
    secret = os.environ.get("LOOMQ_LLM_API_KEY")
    if secret:
        message = message.replace(secret, "[redacted]")
    return message[:800]


def _normalized_history(value: Any) -> List[Dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("history must be a list")
    history: List[Dict[str, str]] = []
    for item in value[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(item, Mapping):
            raise ValueError("history entries must be objects")
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            raise ValueError("history entries need a user/assistant role and text content")
        text = content.strip()
        if text:
            history.append({"role": role, "content": text[:MAX_HISTORY_CHARACTERS]})
    return history


def _contextual_prompt(prompt: str, history: List[Dict[str, str]]) -> str:
    if not history:
        return prompt
    transcript = "\n\n".join(
        ("Previous user" if item["role"] == "user" else "Previous assistant")
        + ":\n"
        + item["content"]
        for item in history
    )
    return (
        "This is a follow-up in a beginner-facing LoomQ conversation. Use the prior "
        "turns only as context and complete the current request.\n\n"
        + transcript
        + "\n\nCurrent user request:\n"
        + prompt
    )


def _answer_kind(answer: str) -> str:
    if answer.lstrip().startswith("OPENQASM 2.0;"):
        return "qasm"
    if "backend:" in answer.lower() or "alternative:" in answer.lower():
        return "backend"
    return "message"


def _simulation_error(target: str, exc: Exception) -> str:
    detail = _safe_error(exc)
    if "No module named" in detail or "does not exist" in detail:
        return (
            SIMULATOR_TARGETS[target]
            + " is not installed in its isolated environment. See the Level 2 "
            "README for local simulator setup."
        )
    return detail


def _simulation_insight(result: Any) -> Optional[Dict[str, Any]]:
    """Summarize counts deterministically for a beginner-facing explanation."""

    if not isinstance(result, Mapping) or not isinstance(result.get("counts"), Mapping):
        return None
    ranked = []
    for state, count in result["counts"].items():
        if (
            not isinstance(state, str)
            or not state
            or isinstance(count, bool)
            or not isinstance(count, (int, float))
            or count < 0
        ):
            return None
        ranked.append((state, float(count)))
    total = sum(count for _state, count in ranked)
    if not ranked or total <= 0:
        return None
    ranked.sort(key=lambda item: (-item[1], item[0]))
    top = ranked[:2]
    return {
        "top_states": [state for state, _count in top],
        "top_share": round(sum(count for _state, count in top) / total, 6),
        "dominant_share": round(top[0][1] / total, 6),
        "observed_states": len(ranked),
    }


class LoomQUIHandler(BaseHTTPRequestHandler):
    """Serve static UI files and a same-origin JSON agent endpoint."""

    server_version = "LoomQUI/1.0"
    session_token = secrets.token_urlsafe(24)
    agent_lock = threading.Lock()
    simulator_lock = threading.Lock()

    def log_message(self, format_string: str, *args: Any) -> None:
        print("[%s] %s" % (self.log_date_time_string(), format_string % args))

    def end_headers(self) -> None:
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        super().end_headers()

    def _json(self, status: int, payload: Mapping[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _valid_host(self) -> bool:
        expected_port = self.server.server_address[1]
        host = self.headers.get("Host", "")
        return host in {
            "127.0.0.1:%d" % expected_port,
            "localhost:%d" % expected_port,
        }

    def _same_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parsed = urlparse(origin)
        return (
            parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "localhost"}
            and parsed.port == self.server.server_address[1]
        )

    def _serve_file(self, filename: str) -> None:
        path = UI_ROOT / filename
        if not path.is_file():
            self.send_error(404)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith("text/") or content_type == "application/javascript" else ""))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._valid_host():
            self._json(421, {"error": "Invalid local host header."})
            return
        route = urlparse(self.path).path
        if route == "/api/health":
            self._json(
                200,
                {
                    "ok": True,
                    "model_configured": _model_configured(),
                    "session_token": type(self).session_token,
                },
            )
            return
        files = {"/": "index.html", "/index.html": "index.html", "/styles.css": "styles.css", "/app.js": "app.js"}
        filename = files.get(route)
        if filename is None:
            self.send_error(404)
            return
        self._serve_file(filename)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route not in {"/api/chat", "/api/run"}:
            self.send_error(404)
            return
        if not self._valid_host() or not self._same_origin():
            self._json(403, {"error": "This endpoint accepts only same-origin local requests."})
            return
        token = self.headers.get("X-LoomQ-Session", "")
        if not hmac.compare_digest(token, type(self).session_token):
            self._json(403, {"error": "The local UI session has expired. Refresh the page."})
            return
        if route == "/api/run":
            self._run_simulator()
            return
        self._run_agent()

    def _read_payload(self) -> Optional[Mapping[str, Any]]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "Invalid request length."})
            return None
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._json(413, {"error": "The request is empty or too large."})
            return None
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, Mapping):
                raise ValueError("request body must be a JSON object")
            return payload
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            self._json(400, {"error": _safe_error(exc)})
            return None

    def _run_agent(self) -> None:
        payload = self._read_payload()
        if payload is None:
            return
        try:
            prompt = payload.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("Please describe what you want the quantum agent to do.")
            prompt = prompt.strip()
            if len(prompt) > MAX_PROMPT_CHARACTERS:
                raise ValueError("The request is too long; keep it under 24,000 characters.")
            history = _normalized_history(payload.get("history"))
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            self._json(400, {"error": _safe_error(exc)})
            return

        if not type(self).agent_lock.acquire(blocking=False):
            self._json(429, {"error": "LoomQ is finishing another request. Try again in a moment."})
            return
        started = time.monotonic()
        try:
            answer = agent_chat(_contextual_prompt(prompt, history))
        except Exception as exc:
            self._json(502, {"error": _safe_error(exc)})
            return
        finally:
            type(self).agent_lock.release()
        self._json(
            200,
            {
                "answer": answer,
                "kind": _answer_kind(answer),
                "elapsed_ms": round((time.monotonic() - started) * 1000),
            },
        )

    def _run_simulator(self) -> None:
        payload = self._read_payload()
        if payload is None:
            return
        try:
            qasm = payload.get("qasm")
            target = payload.get("target")
            shots = payload.get("shots", 512)
            if not isinstance(qasm, str) or not qasm.strip():
                raise ValueError("Paste an OpenQASM 2.0 program before running it.")
            qasm = qasm.strip()
            if len(qasm) > MAX_PROMPT_CHARACTERS:
                raise ValueError("The QASM program is too long; keep it under 24,000 characters.")
            if target not in SIMULATOR_TARGETS:
                raise ValueError("Choose SpinQ, Origin Quantum, or Amazon Braket.")
            if (
                not isinstance(shots, int)
                or isinstance(shots, bool)
                or shots < 1
                or shots > MAX_SIMULATOR_SHOTS
            ):
                raise ValueError("Shots must be a whole number from 1 to 8,192.")
        except ValueError as exc:
            self._json(400, {"error": _safe_error(exc)})
            return

        if not type(self).simulator_lock.acquire(blocking=False):
            self._json(429, {"error": "A local simulation is already running. Try again in a moment."})
            return
        started = time.monotonic()
        try:
            result = run_circuit(qasm, target, shots)
        except Exception as exc:
            self._json(502, {"error": _simulation_error(target, exc), "target": target})
            return
        finally:
            type(self).simulator_lock.release()
        self._json(
            200,
            {
                "target": target,
                "target_name": SIMULATOR_TARGETS[target],
                "result": result,
                "insight": _simulation_insight(result),
                "elapsed_ms": round((time.monotonic() - started) * 1000),
            },
        )


def _loopback_host(value: str) -> str:
    if value == "localhost":
        return "127.0.0.1"
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("host must be a loopback address") from exc
    if not address.is_loopback or address.version != 4:
        raise argparse.ArgumentTypeError("host must be an IPv4 loopback address")
    return value


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local LoomQ Level 2 web interface")
    parser.add_argument("--host", default="127.0.0.1", type=_loopback_host)
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument(
        "--env-file",
        default=Path(".env"),
        type=Path,
        help="optional local environment file (existing process variables take priority)",
    )
    args = parser.parse_args(argv)
    if args.port < 0 or args.port > 65535:
        parser.error("port must be between 0 and 65535")
    _load_env_file(args.env_file)
    server = ThreadingHTTPServer((args.host, args.port), LoomQUIHandler)
    url = "http://%s:%d" % (args.host, server.server_address[1])
    print("LoomQ Level 2 UI: " + url, flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
