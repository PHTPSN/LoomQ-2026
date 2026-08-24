import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CloneSetupWorkflowTests(unittest.TestCase):
    def test_main_setup_includes_backends_and_repairs_empty_directories(self):
        setup = (ROOT / "scripts/setup.ps1").read_text(encoding="utf-8-sig")
        backends = (ROOT / "scripts/setup-backends.ps1").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn('setup-backends.ps1") -Backend all', setup)
        self.assertIn("Test-Path -LiteralPath $EnvironmentPython -PathType Leaf", setup)
        self.assertIn("-m venv --clear", setup)
        self.assertIn('Scripts\\python.exe"', backends)
        self.assertIn(
            "Test-Path -LiteralPath $EnvironmentPython -PathType Leaf", backends
        )
        self.assertIn("-m venv --clear", backends)
        self.assertIn('"check-backends.py"', backends)

    def test_single_start_command_bootstraps_before_serving(self):
        start = (ROOT / "scripts/start-ui.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('"setup.ps1"', start)
        self.assertIn('"check-backends.py"', start)
        self.assertIn("starter_kit.loomq_l2.ui_server", start)

    def test_backend_smoke_check_runs_current_installed_sdks(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/check-backends.py"),
                "spinq",
                "originq",
                "braket",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Backend ready: spinq", completed.stdout)
        self.assertIn("Backend ready: originq", completed.stdout)
        self.assertIn("Backend ready: braket", completed.stdout)


if __name__ == "__main__":
    unittest.main()
