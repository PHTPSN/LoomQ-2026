"""Loopback-only web interface for the LoomQ multi-level workspace."""

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
import urllib.error
import urllib.request
from urllib.parse import urlparse

mimetypes.add_type("text/plain", ".log")

try:
    from .agent import agent_chat
    from ..adapter import run as run_circuit
    from ..loomq_l1 import Gate, Measure, emit_target, parse_qasm2
    from ..loomq_l3 import compile_hybrid
    from ..quantum_riscv import decode_program, encode_program, format_machine_code
except ImportError:
    from agent import agent_chat
    from starter_kit.adapter import run as run_circuit
    from starter_kit.loomq_l1 import Gate, Measure, emit_target, parse_qasm2
    from starter_kit.loomq_l3 import compile_hybrid
    from starter_kit.quantum_riscv import decode_program, encode_program, format_machine_code


UI_ROOT = Path(__file__).resolve().parent / "ui"
EVIDENCE_ROOT = Path(__file__).resolve().parents[1] / "evidence" / "files"
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
TRANSLATION_TARGETS = {
    "spinq": "SpinQ OpenQASM 2.0",
    "originq": "Origin Quantum QRunes",
    "braket": "Amazon Braket OpenQASM 3.0",
}
BACKEND_HEALTH_QASM = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
measure q[0] -> c[0];'''
BACKEND_HEALTH_CACHE_SECONDS = 60.0
MODEL_HEALTH_CACHE_SECONDS = 30.0
BACKEND_PYTHON_ENV = {
    "spinq": "LOOMQ_SPINQ_PYTHON",
    "originq": "LOOMQ_ORIGINQ_PYTHON",
    "braket": "LOOMQ_BRAKET_PYTHON",
}


def _backend_runtime_available(target: str) -> bool:
    configured = os.environ.get(BACKEND_PYTHON_ENV[target])
    if configured:
        return Path(configured).expanduser().is_file()
    repository_root = Path(__file__).resolve().parents[2]
    if os.name == "nt":
        candidates = (
            repository_root / (".venv-" + target) / "Scripts" / "python.exe",
        )
    else:
        candidates = (
            repository_root / (".venv-" + target) / "bin" / "python",
            Path("/opt/loomq-backends") / target / "bin" / "python",
        )
    return any(candidate.is_file() for candidate in candidates)


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


def _probe_model_endpoint() -> Dict[str, Any]:
    """Check the configured model through the provider's read-only model list."""

    if not _model_configured():
        return {"configured": False, "available": False, "state": "missing"}
    base_url = os.environ["LOOMQ_LLM_BASE_URL"].rstrip("/")
    model = os.environ["LOOMQ_LLM_MODEL"]
    request = urllib.request.Request(
        base_url + "/models",
        headers={"Authorization": "Bearer " + os.environ["LOOMQ_LLM_API_KEY"]},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=4.0) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        state = "authentication" if exc.code in {401, 403} else "api_error"
        return {"configured": True, "available": False, "state": state}
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return {"configured": True, "available": False, "state": "unreachable"}
    models = {
        item.get("id")
        for item in payload.get("data", [])
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    } if isinstance(payload, Mapping) else set()
    if models and model not in models:
        return {"configured": True, "available": False, "state": "model_missing"}
    return {"configured": True, "available": True, "state": "ready"}


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


def _canonical_ir(circuit: Any) -> Dict[str, Any]:
    """Return the Level 1 circuit model as a JSON-safe teaching artifact."""

    instructions: List[Dict[str, Any]] = []
    for instruction in circuit.instructions:
        if isinstance(instruction, Gate):
            instructions.append(
                {
                    "kind": "gate",
                    "name": instruction.name,
                    "parameters": list(instruction.params),
                    "qubits": list(instruction.qubits),
                }
            )
        elif isinstance(instruction, Measure):
            instructions.append(
                {
                    "kind": "measure",
                    "qubit": instruction.qubit,
                    "classical_bit": instruction.clbit,
                }
            )
        else:  # The validated model should make this unreachable.
            raise ValueError("unknown canonical instruction type")
    return {
        "qubits": circuit.num_qubits,
        "classical_bits": circuit.num_clbits,
        "instructions": instructions,
    }


class LoomQUIHandler(BaseHTTPRequestHandler):
    """Serve static UI files and a same-origin JSON agent endpoint."""

    server_version = "LoomQUI/1.0"
    session_token = secrets.token_urlsafe(24)
    agent_lock = threading.Lock()
    simulator_lock = threading.Lock()
    backend_health_lock = threading.Lock()
    backend_health_checked_at = 0.0
    backend_health_cache: Dict[str, Dict[str, Any]] = {}
    model_health_lock = threading.Lock()
    model_health_checked_at = 0.0
    model_health_cache: Dict[str, Any] = {}

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

    def _serve_file(self, path: Path) -> None:
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
            handler_type = type(self)
            now = time.monotonic()
            with handler_type.model_health_lock:
                if (
                    not handler_type.model_health_cache
                    or now - handler_type.model_health_checked_at >= MODEL_HEALTH_CACHE_SECONDS
                ):
                    handler_type.model_health_cache = _probe_model_endpoint()
                    handler_type.model_health_checked_at = now
                model_health = dict(handler_type.model_health_cache)
            self._json(
                200,
                {
                    "ok": True,
                    "model_configured": model_health["configured"],
                    "model_available": model_health["available"],
                    "model_state": model_health["state"],
                    "session_token": type(self).session_token,
                },
            )
            return
        if route == "/api/backend-health":
            self._backend_health()
            return
        files = {
            "/": UI_ROOT / "index.html",
            "/index.html": UI_ROOT / "index.html",
            "/styles.css": UI_ROOT / "styles.css",
            "/app.js": UI_ROOT / "app.js",
            "/vendor/katex.min.js": UI_ROOT / "vendor/katex.min.js",
            "/assets/spinq-logo.png": UI_ROOT / "assets/spinq-logo.png",
            "/assets/origin-quantum-logo.svg": UI_ROOT / "assets/origin-quantum-logo.svg",
            "/assets/aws-logo.svg": UI_ROOT / "assets/aws-logo.svg",
            "/evidence/originq-bell-task.png": EVIDENCE_ROOT / "originq-bell/originq-bell-task.png",
            "/evidence/originq-bell-task.json": EVIDENCE_ROOT / "originq-bell/originq-bell-task.json",
            "/evidence/originq-bell-program.originir": EVIDENCE_ROOT / "originq-bell/originq-bell-executed.originir",
            "/evidence/originq-bell-raw.json": EVIDENCE_ROOT / "originq-bell/originq-bell-sdk-result.json",
            "/evidence/originq-bell-normalized.json": EVIDENCE_ROOT / "originq-bell/originq-bell-normalized-result.json",
            "/evidence/originq-ghz3-task.png": EVIDENCE_ROOT / "originq-ghz3/originq-ghz3-task.png",
            "/evidence/spinq-bell-task.png": EVIDENCE_ROOT / "spinq-bell/spinq-bell-task.png",
            "/evidence/spinq-bell-task.json": EVIDENCE_ROOT / "spinq-bell/spinq-bell-task.json",
            "/evidence/spinq-bell-program.qasm": EVIDENCE_ROOT / "spinq-bell/spinq-bell-executed.qasm",
            "/evidence/spinq-bell-raw.json": EVIDENCE_ROOT / "spinq-bell/spinq-bell-sdk-result.json",
            "/evidence/spinq-bell-normalized.json": EVIDENCE_ROOT / "spinq-bell/spinq-bell-normalized-result.json",
            "/evidence/spinq-diagnostics.json": EVIDENCE_ROOT / "spinq-diagnostics/spinq-diagnostics-report.json",
            "/evidence/quantum-riscv-gpu-result.json": EVIDENCE_ROOT / "quantum-riscv-gpu/loomq-quantum-riscv-gpu-evidence.json",
            "/evidence/quantum-riscv-gpu.log": EVIDENCE_ROOT / "quantum-riscv-gpu/loomq-lq-q32-gpu-validation.log",
            "/evidence/quantum-riscv-gpu.py": EVIDENCE_ROOT / "quantum-riscv-gpu/loomq_gpu_validation.py",
        }
        path = files.get(route)
        if path is None:
            self.send_error(404)
            return
        self._serve_file(path)

    def _backend_health(self) -> None:
        handler_type = type(self)
        now = time.monotonic()
        if (
            handler_type.backend_health_cache
            and now - handler_type.backend_health_checked_at
            < BACKEND_HEALTH_CACHE_SECONDS
        ):
            self._json(
                200,
                {
                    "scope": "local_simulators",
                    "backends": handler_type.backend_health_cache,
                },
            )
            return
        with handler_type.backend_health_lock:
            now = time.monotonic()
            if (
                not handler_type.backend_health_cache
                or now - handler_type.backend_health_checked_at
                >= BACKEND_HEALTH_CACHE_SECONDS
            ):
                statuses: Dict[str, Dict[str, Any]] = {}
                for target in SIMULATOR_TARGETS:
                    if not _backend_runtime_available(target):
                        statuses[target] = {"ok": False, "state": "missing"}
                        continue
                    try:
                        run_circuit(BACKEND_HEALTH_QASM, target, 1)
                    except Exception as exc:
                        statuses[target] = {
                            "ok": False,
                            "state": (
                                "missing"
                                if "ModuleNotFoundError" in str(exc)
                                else "unavailable"
                            ),
                        }
                    else:
                        statuses[target] = {"ok": True}
                handler_type.backend_health_cache = statuses
                handler_type.backend_health_checked_at = time.monotonic()
        self._json(
            200,
            {
                "scope": "local_simulators",
                "backends": handler_type.backend_health_cache,
            },
        )

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route not in {
            "/api/chat",
            "/api/run",
            "/api/transpile",
            "/api/compile-hybrid",
        }:
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
        if route == "/api/transpile":
            self._transpile()
            return
        if route == "/api/compile-hybrid":
            self._compile_hybrid()
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

    def _transpile(self) -> None:
        payload = self._read_payload()
        if payload is None:
            return
        try:
            qasm = payload.get("qasm")
            target = payload.get("target")
            if not isinstance(qasm, str) or not qasm.strip():
                raise ValueError("Paste an OpenQASM 2.0 program before translating it.")
            qasm = qasm.strip()
            if len(qasm) > MAX_PROMPT_CHARACTERS:
                raise ValueError("The QASM program is too long; keep it under 24,000 characters.")
            if target not in TRANSLATION_TARGETS:
                raise ValueError("Choose SpinQ, Origin Quantum, or Amazon Braket.")
            started = time.monotonic()
            circuit = parse_qasm2(qasm)
            translated = emit_target(circuit, target)
        except Exception as exc:
            self._json(400, {"error": _safe_error(exc)})
            return
        self._json(
            200,
            {
                "target": target,
                "target_name": TRANSLATION_TARGETS[target],
                "ir": _canonical_ir(circuit),
                "translated": translated,
                "elapsed_ms": round((time.monotonic() - started) * 1000),
            },
        )

    def _compile_hybrid(self) -> None:
        payload = self._read_payload()
        if payload is None:
            return
        try:
            source = payload.get("source")
            if not isinstance(source, str) or not source.strip():
                raise ValueError("Paste a Hybrid-QASM program before compiling it.")
            source = source.strip()
            if len(source) > MAX_PROMPT_CHARACTERS:
                raise ValueError("The Hybrid-QASM program is too long; keep it under 24,000 characters.")
            started = time.monotonic()
            quantum_operations, assembly = compile_hybrid(source)
            machine_words = encode_program(quantum_operations)
            decoded_trace = [instruction.to_operation() for instruction in decode_program(machine_words)]
        except Exception as exc:
            self._json(400, {"error": _safe_error(exc)})
            return
        self._json(
            200,
            {
                "quantum_operations": quantum_operations,
                "assembly": assembly,
                "machine_code": format_machine_code(machine_words),
                "machine_words": ["0x%08x" % word for word in machine_words],
                "decoded_trace": decoded_trace,
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
    parser = argparse.ArgumentParser(description="Run the local LoomQ web workspace")
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
    print("LoomQ workspace: " + url, flush=True)
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
