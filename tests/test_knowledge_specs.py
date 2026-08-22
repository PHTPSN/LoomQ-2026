import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "starter_kit" / "knowledge"
SPEC = KNOWLEDGE / "spec"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class KnowledgeSpecificationTests(unittest.TestCase):
    def test_required_knowledge_documents_exist(self):
        required = {
            "README.md",
            "qasm2_subset.md",
            "translation_method.md",
            "sdk_spinq.md",
            "sdk_originq.md",
            "sdk_braket.md",
            "WEB_LINKS.md",
            "sources.lock.json",
        }
        self.assertTrue(required.issubset({path.name for path in KNOWLEDGE.iterdir()}))

    def test_gate_whitelist_is_complete_and_unique(self):
        gate_spec = load_json(SPEC / "gates.json")
        names = [gate["name"] for gate in gate_spec["gates"]]
        expected = [
            "h", "x", "s", "sdg", "t", "tdg",
            "rz", "ry", "cx", "cu1", "swap", "ccx",
        ]
        self.assertEqual(names, expected)
        self.assertEqual(gate_spec["gate_count"], len(expected))
        self.assertEqual(len(names), len(set(names)))
        for gate in gate_spec["gates"]:
            self.assertGreaterEqual(gate["parameter_count"], 0)
            self.assertIn(gate["qubit_count"], (1, 2, 3))

    def test_every_target_profile_covers_every_source_gate(self):
        mapping_spec = load_json(SPEC / "target_mappings.json")
        expected = set(mapping_spec["source_gates"])
        self.assertEqual(set(mapping_spec["targets"]), {"spinq", "originq", "braket"})

        for target_name, target in mapping_spec["targets"].items():
            self.assertIn(target["default_profile"], target["profiles"])
            for profile_name, profile in target["profiles"].items():
                mapping = profile.get("gate_map") or profile.get("gate_templates")
                self.assertEqual(
                    set(mapping),
                    expected,
                    f"{target_name}/{profile_name} does not cover the whitelist",
                )

    def test_pinned_sdk_versions_match_direct_requirements(self):
        expected = {
            "spinq": "spinqit==0.2.4",
            "originq": "pyqpanda==3.8.5",
            "braket": "amazon-braket-sdk==1.110.1",
        }
        for backend, requirement in expected.items():
            actual = (ROOT / "requirements" / f"{backend}.txt").read_text(
                encoding="utf-8"
            ).strip()
            self.assertEqual(actual, requirement)

    def test_result_schema_preserves_competition_bit_order(self):
        schema = load_json(SPEC / "result_schema.json")
        self.assertEqual(schema["properties"]["bit_order"]["const"], "little")
        self.assertEqual(
            set(schema["required"]),
            {"backend", "job_id", "shots", "counts", "bit_order", "timestamp", "meta"},
        )
        self.assertEqual(
            schema["properties"]["counts"]["propertyNames"]["pattern"],
            "^[01]+$",
        )
        self.assertIn("rightmost bit", schema["$comment"])

    def test_source_registry_contains_only_https_web_links(self):
        source_lock = load_json(KNOWLEDGE / "sources.lock.json")
        ids = [source["id"] for source in source_lock["sources"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 10)
        for source in source_lock["sources"]:
            self.assertTrue(source["url"].startswith("https://"), source["id"])
            self.assertTrue(source["authority"])
            self.assertTrue(source["used_for"])

    def test_machine_grammar_declares_required_constructs(self):
        grammar = (SPEC / "qasm2_subset.ebnf").read_text(encoding="utf-8")
        for token in (
            '"OPENQASM"',
            '"2.0"',
            '"qelib1.inc"',
            '"qreg"',
            '"creg"',
            '"measure"',
            '"pi"',
        ):
            self.assertIn(token, grammar)

    def test_relative_markdown_links_resolve(self):
        link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        for document in KNOWLEDGE.glob("*.md"):
            for target in link_pattern.findall(document.read_text(encoding="utf-8")):
                if target.startswith(("https://", "http://", "#")):
                    continue
                path_text = target.split("#", 1)[0]
                resolved = (document.parent / path_text).resolve()
                self.assertTrue(
                    resolved.exists(),
                    f"Broken relative link in {document.name}: {target}",
                )


if __name__ == "__main__":
    unittest.main()
