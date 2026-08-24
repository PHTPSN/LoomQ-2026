import http.client
import json
import os
import re
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from starter_kit.loomq_l2 import ui_server


class LocalUIServer:
    def __enter__(self):
        ui_server.LoomQUIHandler.session_token = "test-session"
        ui_server.LoomQUIHandler.agent_lock = threading.Lock()
        ui_server.LoomQUIHandler.simulator_lock = threading.Lock()
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), ui_server.LoomQUIHandler
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=2
        )
        request_headers = {"Host": "127.0.0.1:%d" % self.server.server_port}
        request_headers.update(headers or {})
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        payload = response.read()
        response_headers = dict(response.getheaders())
        connection.close()
        return response.status, response_headers, payload


class Level2UIHelpersTest(unittest.TestCase):
    def test_env_file_fills_missing_values_without_overriding_process(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "# local settings\nexport LOOMQ_UI_NEW='from file'\n"
                "LOOMQ_UI_KEEP=from-file\nINVALID\n",
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ, {"LOOMQ_UI_KEEP": "injected"}, clear=True
            ):
                ui_server._load_env_file(path)
                self.assertEqual(os.environ["LOOMQ_UI_NEW"], "from file")
                self.assertEqual(os.environ["LOOMQ_UI_KEEP"], "injected")

    def test_history_is_limited_and_added_as_context(self):
        history = [
            {"role": "user", "content": "old-%d" % index} for index in range(8)
        ]
        normalized = ui_server._normalized_history(history)
        self.assertEqual(len(normalized), ui_server.MAX_HISTORY_MESSAGES)
        contextual = ui_server._contextual_prompt("current", normalized)
        self.assertNotIn("old-0", contextual)
        self.assertIn("old-7", contextual)
        self.assertTrue(contextual.endswith("Current user request:\ncurrent"))

    def test_model_errors_redact_api_key(self):
        with mock.patch.dict(
            os.environ, {"LOOMQ_LLM_API_KEY": "private-test-key"}, clear=True
        ):
            message = ui_server._safe_error(RuntimeError("bad private-test-key"))
        self.assertEqual(message, "bad [redacted]")

    def test_non_loopback_bind_is_rejected(self):
        with self.assertRaises(Exception):
            ui_server._loopback_host("0.0.0.0")

    def test_simulation_insight_is_stable_and_beginner_friendly(self):
        insight = ui_server._simulation_insight(
            {"counts": {"11": 63, "00": 65, "01": 0}}
        )
        self.assertEqual(insight["top_states"], ["00", "11"])
        self.assertEqual(insight["top_share"], 1.0)
        self.assertEqual(insight["observed_states"], 3)


class Level2UIServerTest(unittest.TestCase):
    def test_health_and_static_page_have_security_headers(self):
        with LocalUIServer() as local:
            status, headers, body = local.request("GET", "/")
            self.assertEqual(status, 200)
            self.assertIn(b"Ask LoomQ", body)
            self.assertIn(b'class="assistant-dock"', body)
            self.assertIn(b'id="rail-toggle"', body)
            self.assertIn(b'aria-controls="side-rail"', body)
            self.assertIn(b'id="composer-resize-handle"', body)
            self.assertIn(b'id="assistant-hide-button"', body)
            self.assertIn(b'id="assistant-launcher"', body)
            self.assertIn(b'aria-controls="assistant-dock"', body)
            self.assertIn(b'aria-valuemin="60"', body)
            self.assertNotIn(b'The assistant stays here while you browse lessons and tools.', body)
            self.assertIn(b'role="separator"', body)
            self.assertIn(b"Vendor simulators", body)
            self.assertEqual(body.count(b'class="vendor-card '), 3)
            self.assertIn(b">SpinQ</strong><small>SpinQit SDK</small>", body)
            self.assertIn(
                b">Origin Quantum</strong><small>pyQPanda SDK</small>", body
            )
            self.assertIn(
                b">Amazon Web Services</strong><small>Amazon Braket SDK</small>",
                body,
            )
            self.assertNotIn(b"<small>Basic Simulator</small>", body)
            self.assertNotIn(b"<small>LocalSimulator</small>", body)
            self.assertEqual(
                re.findall(rb'data-view="([^"]+)"', body),
                [b"overview", b"learn", b"gates", b"simulator"],
            )
            self.assertEqual(
                re.findall(rb'data-view-panel="([^"]+)"', body),
                [b"overview", b"learn", b"gates", b"simulator"],
            )
            gate_examples = re.findall(rb'data-gate-example="([^"]+)"', body)
            gate_spec = json.loads(
                (ui_server.UI_ROOT.parents[1] / "knowledge/spec/gates.json").read_text(
                    encoding="utf-8"
                )
            )
            expected_gates = [item["name"].encode() for item in gate_spec["gates"]]
            self.assertEqual(gate_examples, expected_gates)
            script = (ui_server.UI_ROOT / "app.js").read_text(encoding="utf-8")
            styles = (ui_server.UI_ROOT / "styles.css").read_text(encoding="utf-8")
            self.assertIn('localStorage.setItem("loomq-rail"', script)
            self.assertIn('localStorage.setItem("loomq-assistant"', script)
            self.assertIn("button.title = navigationLabel", script)
            self.assertIn('button.removeAttribute("title")', script)
            self.assertIn('promptResizeHandle.addEventListener("pointerdown"', script)
            self.assertIn('promptResizeHandle.addEventListener("keydown"', script)
            self.assertIn("position:fixed", styles)
            self.assertIn("top:auto;right:16px;bottom:16px", styles)
            self.assertIn("height:min(564px,calc(100vh - 32px))", styles)
            self.assertIn("padding-bottom:600px", styles)
            self.assertIn("cursor:ns-resize", styles)
            self.assertIn("resize:none", styles)
            self.assertIn("height:60px;min-height:60px;max-height:220px", styles)
            self.assertIn(".assistant-dock{overflow:hidden}", styles)
            self.assertIn("overflow-y:auto;overscroll-behavior:contain", styles)
            self.assertIn("margin-bottom:14px", styles)
            self.assertIn("margin:clamp(42px,5vw,70px) 0 8px", styles)
            self.assertIn(".workspace.assistant-hidden .assistant-dock{display:none}", styles)
            self.assertIn(
                'conversation.scrollTo({ top: conversation.scrollHeight', script
            )
            self.assertIn("height:39px;min-height:39px", styles)
            self.assertIn("padding-right:0", styles)
            self.assertIn(".workspace.rail-collapsed", styles)
            i18n_keys = set(
                re.findall(
                    rb'data-i18n(?:-placeholder|-aria)?="([^"]+)"', body
                )
            )
            for key in i18n_keys:
                self.assertIn('"%s":' % key.decode(), script)
            self.assertEqual(body.count(b"data-prompt-en="), 3)
            self.assertEqual(body.count(b"data-prompt-zh="), 3)
            self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
            self.assertEqual(headers["X-Frame-Options"], "DENY")

            status, headers, body = local.request("GET", "/assets/spinq-logo.png")
            self.assertEqual(status, 200)
            self.assertEqual(headers["Content-Type"], "image/png")
            self.assertTrue(body.startswith(b"\x89PNG"))

            status, headers, body = local.request(
                "GET", "/assets/origin-quantum-logo.svg"
            )
            self.assertEqual(status, 200)
            self.assertEqual(headers["Content-Type"], "image/svg+xml")
            self.assertIn(b"<svg", body)

            status, headers, body = local.request("GET", "/assets/aws-logo.svg")
            self.assertEqual(status, 200)
            self.assertEqual(headers["Content-Type"], "image/svg+xml")
            self.assertIn(b"<svg", body)

            status, _, body = local.request("GET", "/api/health")
            health = json.loads(body)
            self.assertEqual(status, 200)
            self.assertTrue(health["ok"])
            self.assertEqual(health["session_token"], "test-session")

    def test_chat_calls_agent_with_context_and_classifies_qasm(self):
        qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
        payload = json.dumps(
            {
                "prompt": "Now measure it",
                "history": [{"role": "user", "content": "Create one qubit"}],
            }
        )
        with LocalUIServer() as local, mock.patch.object(
            ui_server, "agent_chat", return_value=qasm
        ) as agent:
            status, _, body = local.request(
                "POST",
                "/api/chat",
                body=payload,
                headers={
                    "Content-Type": "application/json",
                    "Origin": "http://127.0.0.1:%d" % local.server.server_port,
                    "X-LoomQ-Session": "test-session",
                },
            )
        result = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(result["kind"], "qasm")
        self.assertEqual(result["answer"], qasm)
        self.assertIn("Previous user:\nCreate one qubit", agent.call_args.args[0])
        self.assertTrue(agent.call_args.args[0].endswith("Now measure it"))

    def test_chat_rejects_cross_origin_and_expired_sessions(self):
        payload = json.dumps({"prompt": "Create a Bell state"})
        with LocalUIServer() as local:
            status, _, _ = local.request(
                "POST",
                "/api/chat",
                body=payload,
                headers={
                    "Origin": "https://example.com",
                    "X-LoomQ-Session": "test-session",
                },
            )
            self.assertEqual(status, 403)
            status, _, body = local.request(
                "POST",
                "/api/chat",
                body=payload,
                headers={"X-LoomQ-Session": "expired"},
            )
            self.assertEqual(status, 403)
            self.assertIn(b"expired", body)

    def test_run_executes_selected_vendor_simulator(self):
        qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
        vendor_result = {
            "backend": "spinq_basic_simulator",
            "job_id": "local-job",
            "shots": 128,
            "counts": {"0": 65, "1": 63},
            "bit_order": "little",
            "timestamp": "2026-08-24T00:00:00Z",
            "meta": {"sdk": "spinqit"},
        }
        payload = json.dumps({"qasm": qasm, "target": "spinq", "shots": 128})
        with LocalUIServer() as local, mock.patch.object(
            ui_server, "run_circuit", return_value=vendor_result
        ) as runner:
            status, _, body = local.request(
                "POST",
                "/api/run",
                body=payload,
                headers={"X-LoomQ-Session": "test-session"},
            )
        result = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(result["target_name"], "SpinQit Basic Simulator")
        self.assertEqual(result["result"]["counts"], {"0": 65, "1": 63})
        self.assertEqual(result["insight"]["top_states"], ["0", "1"])
        self.assertEqual(result["insight"]["top_share"], 1.0)
        runner.assert_called_once_with(qasm.strip(), "spinq", 128)

    def test_run_rejects_unknown_target_and_excessive_shots(self):
        qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
        with LocalUIServer() as local:
            for target, shots in (("hardware", 128), ("spinq", 8193)):
                status, _, _ = local.request(
                    "POST",
                    "/api/run",
                    body=json.dumps(
                        {"qasm": qasm, "target": target, "shots": shots}
                    ),
                    headers={"X-LoomQ-Session": "test-session"},
                )
                self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
