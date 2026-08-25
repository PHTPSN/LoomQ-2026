import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from starter_kit import adapter
from starter_kit import evaluator
from starter_kit.loomq_l2.backend import format_recommendation, select_backends
from starter_kit.loomq_l2.qasm import (
    canonical_qasm,
    synthesize_target_state_qasm,
    target_state_fidelity,
)


GHZ_QASM = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
measure q -> c;
'''

BELL_QASM = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
'''


class AgentAPIHandler(BaseHTTPRequestHandler):
    response_contents = []
    request_payloads = []

    def log_message(self, *_args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        type(self).request_payloads.append(json.loads(self.rfile.read(length)))
        if type(self).response_contents:
            content = type(self).response_contents.pop(0)
        else:
            content = "{}"
        body = json.dumps(
            {"choices": [{"message": {"role": "assistant", "content": content}}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class LocalAgentEndpoint:
    def __init__(self, documents, model="deepseek-v4-flash"):
        AgentAPIHandler.response_contents = [
            value if isinstance(value, str) else json.dumps(value) for value in documents
        ]
        AgentAPIHandler.request_payloads = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), AgentAPIHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.environment = {
            "LOOMQ_LLM_BASE_URL": "http://127.0.0.1:%d" % self.server.server_port,
            "LOOMQ_LLM_API_KEY": "local-test-key",
            "LOOMQ_LLM_MODEL": model,
            "LOOMQ_LLM_TIMEOUT_SECONDS": "5",
        }

    def __enter__(self):
        self.thread.start()
        self.patch = mock.patch.dict(os.environ, self.environment, clear=True)
        self.patch.start()
        return self

    def __exit__(self, *_args):
        self.patch.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def qasm_document(qasm, task="generate_qasm", distribution=None, target_state=None):
    return {
        "task": task,
        "qasm": qasm,
        "expected_distribution": distribution,
        "target_state": target_state,
        "backend_constraints": None,
    }


def backend_document(**constraints):
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
    return {
        "task": "select_backend",
        "qasm": None,
        "expected_distribution": None,
        "backend_constraints": defaults,
    }


def explain_document(answer):
    return {
        "task": "explain",
        "answer": answer,
        "qasm": None,
        "expected_distribution": None,
        "target_state": None,
        "backend_constraints": None,
    }


class L2AgentModelFlowTests(unittest.TestCase):
    def test_conceptual_question_returns_plain_text_without_qasm_coercion(self):
        explanation = "Bell 态是两个量子比特形成的纠缠态；测量结果彼此相关。"
        with LocalAgentEndpoint([explain_document(explanation)]):
            answer = adapter.agent_chat("什么是 Bell 态？请给新手解释。")

        self.assertEqual(answer, explanation)
        self.assertEqual(len(AgentAPIHandler.request_payloads), 1)
        system_prompt = AgentAPIHandler.request_payloads[0]["messages"][0]["content"]
        self.assertIn("conceptual, learning, capability, greeting", system_prompt)

    def test_empty_explanation_requires_one_correction(self):
        with LocalAgentEndpoint(
            [explain_document(""), explain_document("LoomQ can explain, build, and verify circuits.")]
        ):
            answer = adapter.agent_chat("What can you do?")

        self.assertEqual(answer, "LoomQ can explain, build, and verify circuits.")
        self.assertEqual(len(AgentAPIHandler.request_payloads), 2)

    def test_generation_makes_one_genuine_call_and_returns_canonical_qasm(self):
        document = qasm_document(GHZ_QASM, distribution={"000": 0.5, "111": 0.5})
        with LocalAgentEndpoint([document]):
            answer = adapter.agent_chat("生成一个三比特最大纠缠态，并测量全部量子比特")

        self.assertEqual(answer, canonical_qasm(GHZ_QASM))
        self.assertEqual(len(AgentAPIHandler.request_payloads), 1)
        payload = AgentAPIHandler.request_payloads[0]
        self.assertEqual(payload["model"], "deepseek-v4-flash")
        self.assertEqual(payload["temperature"], 0)
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["messages"][-1]["role"], "user")

    def test_public_evaluator_accepts_the_verified_qasm(self):
        document = qasm_document(GHZ_QASM, distribution={"000": 0.5, "111": 0.5})
        with LocalAgentEndpoint([document]):
            cases = evaluator.evaluate_l2()

        self.assertEqual(cases[0]["status"], "PASS")
        self.assertEqual(len(AgentAPIHandler.request_payloads), 1)

    def test_invalid_qasm_gets_exactly_one_model_correction_call(self):
        broken = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
H q[0];
CX q[0] q[1];
'''
        documents = [
            qasm_document(broken, task="repair_qasm"),
            qasm_document(BELL_QASM, task="repair_qasm", distribution={"00": 0.5, "11": 0.5}),
        ]
        with LocalAgentEndpoint(documents):
            answer = adapter.agent_chat(
                "I want a Bell state, but this code is malformed: H q[0]; CX q[0] q[1]"
            )

        self.assertEqual(answer, canonical_qasm(BELL_QASM))
        self.assertEqual(len(AgentAPIHandler.request_payloads), 2)
        correction = AgentAPIHandler.request_payloads[1]["messages"][-1]["content"]
        self.assertIn("could not be accepted", correction)
        self.assertNotIn("local-test-key", correction)

    def test_parser_skips_an_unrelated_json_object_before_the_valid_schema(self):
        content = '{"note":"draft"}\n' + json.dumps(
            qasm_document(BELL_QASM, distribution={"00": 0.5, "11": 0.5})
        )
        with LocalAgentEndpoint([content]):
            answer = adapter.agent_chat("Prepare and measure a Bell state")

        self.assertEqual(answer, canonical_qasm(BELL_QASM))
        self.assertEqual(len(AgentAPIHandler.request_payloads), 1)

    def test_valid_qasm_without_semantic_metadata_requires_correction(self):
        documents = [
            qasm_document(BELL_QASM),
            qasm_document(BELL_QASM, distribution={"00": 0.5, "11": 0.5}),
        ]
        with LocalAgentEndpoint(documents):
            answer = adapter.agent_chat("Prepare and measure a Bell state")

        self.assertEqual(answer, canonical_qasm(BELL_QASM))
        self.assertEqual(len(AgentAPIHandler.request_payloads), 2)
        correction = AgentAPIHandler.request_payloads[1]["messages"][-1]["content"]
        self.assertIn("semantic verification requires", correction)

    def test_two_semantically_unannotated_answers_are_rejected(self):
        with LocalAgentEndpoint([qasm_document(BELL_QASM), qasm_document(BELL_QASM)]):
            with self.assertRaisesRegex(ValueError, "semantic verification"):
                adapter.agent_chat("Prepare and measure a Bell state")
        self.assertEqual(len(AgentAPIHandler.request_payloads), 2)

    def test_target_state_without_measurements_requires_correction(self):
        no_measurement = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
'''
        target = {"00": 2 ** -0.5, "11": 2 ** -0.5}
        documents = [
            qasm_document(no_measurement, target_state=target),
            qasm_document(BELL_QASM, target_state=target),
        ]
        with LocalAgentEndpoint(documents):
            answer = adapter.agent_chat("Prepare and measure a Bell state")

        self.assertEqual(answer, canonical_qasm(BELL_QASM))
        self.assertEqual(len(AgentAPIHandler.request_payloads), 2)

    def test_second_failure_can_use_semantically_valid_mechanical_sanitizer(self):
        broken = '''OPENQASM 2.0
include "qelib1.inc"
qreg q[2]
creg c[2]
H q[0]
CX q[0] q[1]
measure q -> c
'''
        documents = [
            qasm_document(broken, task="repair_qasm", distribution={"00": 0.5, "11": 0.5}),
            qasm_document(broken, task="repair_qasm", distribution={"00": 0.5, "11": 0.5}),
        ]
        with LocalAgentEndpoint(documents):
            answer = adapter.agent_chat("Repair this Bell circuit without changing its state")

        self.assertEqual(answer, canonical_qasm(BELL_QASM))
        self.assertEqual(len(AgentAPIHandler.request_payloads), 2)

    def test_semantic_distribution_mismatch_triggers_one_correction(self):
        wrong = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
measure q -> c;
'''
        documents = [
            qasm_document(wrong, distribution={"000": 0.5, "111": 0.5}),
            qasm_document(GHZ_QASM, distribution={"000": 0.5, "111": 0.5}),
        ]
        with LocalAgentEndpoint(documents):
            answer = adapter.agent_chat("Prepare and measure a three-qubit GHZ state")

        self.assertEqual(answer, canonical_qasm(GHZ_QASM))
        self.assertEqual(len(AgentAPIHandler.request_payloads), 2)
        correction = AgentAPIHandler.request_payloads[1]["messages"][-1]["content"]
        self.assertIn('expected={"000": 0.5, "111": 0.5}', correction)
        self.assertIn('observed={"000": 1.0}', correction)

    def test_two_bad_candidates_fall_back_to_generic_state_synthesis(self):
        wrong = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
measure q -> c;
'''
        w_state = {
            "001": 0.5773502691896258,
            "010": 0.5773502691896258,
            "100": 0.5773502691896258,
        }
        distribution = {"001": 1 / 3, "010": 1 / 3, "100": 1 / 3}
        documents = [
            qasm_document(wrong, distribution=distribution, target_state=w_state),
            qasm_document(wrong, distribution=distribution, target_state=w_state),
        ]
        with LocalAgentEndpoint(documents):
            answer = adapter.agent_chat("Prepare and measure a three-qubit W state")

        self.assertGreater(target_state_fidelity(answer, w_state), 0.999999)
        self.assertEqual(len(AgentAPIHandler.request_payloads), 2)

    def test_backend_selection_still_makes_the_required_model_call(self):
        document = backend_document(min_qubits=15, queue_policy="none")
        with LocalAgentEndpoint([document]):
            answer = adapter.agent_chat("15 比特电路，不能排队，应该使用哪个后端？")

        self.assertIn("spinq_taurus_simulator", answer)
        self.assertEqual(len(AgentAPIHandler.request_payloads), 1)

    def test_model_is_never_called_more_than_twice(self):
        with LocalAgentEndpoint(["not json", "still not json"]):
            with self.assertRaisesRegex(ValueError, "JSON"):
                adapter.agent_chat("Please create a circuit")
        self.assertEqual(len(AgentAPIHandler.request_payloads), 2)

    def test_empty_prompt_fails_without_contacting_a_model(self):
        with LocalAgentEndpoint([qasm_document(GHZ_QASM)]):
            with self.assertRaisesRegex(ValueError, "non-empty"):
                adapter.agent_chat("  ")
        self.assertEqual(AgentAPIHandler.request_payloads, [])


class L2BackendSelectionTests(unittest.TestCase):
    def test_zero_queue_26_qubits_selects_originq_local(self):
        answer = format_recommendation(
            backend_document(min_qubits=26, queue_policy="none")["backend_constraints"]
        )
        self.assertIn("originq_local_simulator", answer)

    def test_real_hardware_and_not_paid_selects_spinq_cloud(self):
        answer = format_recommendation(
            backend_document(
                min_qubits=5,
                allowed_kinds=["qpu"],
                cost_policy="not_paid",
            )["backend_constraints"]
        )
        self.assertIn("spinq_cloud_qpu", answer)

    def test_ten_qubit_qpu_selects_wukong(self):
        answer = format_recommendation(
            backend_document(min_qubits=10, allowed_kinds=["qpu"])["backend_constraints"]
        )
        self.assertIn("originq_wukong", answer)

    def test_braket_without_account_selects_local_simulator(self):
        answer = format_recommendation(
            backend_document(
                min_qubits=20,
                allowed_platforms=["braket"],
                account_policy="no_account",
            )["backend_constraints"]
        )
        self.assertIn("braket_local_simulator", answer)

    def test_conflicting_qpu_and_no_account_reports_no_exact_match(self):
        answer = format_recommendation(
            backend_document(
                min_qubits=5,
                allowed_kinds=["qpu"],
                account_policy="no_account",
            )["backend_constraints"]
        )
        self.assertTrue(answer.startswith("No backend"))
        self.assertIn("Closest alternative:", answer)

    def test_every_selected_id_comes_from_the_static_snapshot(self):
        _constraints, matches = select_backends(
            backend_document(cost_policy="free_only")["backend_constraints"]
        )
        self.assertEqual(
            {backend["id"] for backend in matches},
            {
                "spinq_taurus_simulator",
                "originq_local_simulator",
                "braket_local_simulator",
            },
        )


class L2GenericStateSynthesisTests(unittest.TestCase):
    def test_sparse_complex_state_uses_only_the_l1_gate_subset(self):
        target = {"00": [1.0, 0.0], "11": [0.0, 1.0]}
        qasm = synthesize_target_state_qasm(target)

        self.assertGreater(target_state_fidelity(qasm, target), 0.999999)
        self.assertNotIn("u(", qasm)
        self.assertIn("ry(", qasm)
        self.assertIn("rz(", qasm)


if __name__ == "__main__":
    unittest.main()
