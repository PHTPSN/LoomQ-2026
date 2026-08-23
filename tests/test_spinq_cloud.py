import unittest

from starter_kit.hardware.spinq_cloud import (
    SpinQCloudValidationError,
    prepare_from_discovery,
)


HEADER = 'OPENQASM 2.0;\ninclude "qelib1.inc";\n'


def discovery(*, online=1, gates=None, coupling=None):
    return {
        "status": 200,
        "msg": "",
        "items": [
            {
                "pcode": "gemini_vp",
                "pname": "2Qubit NMR",
                "simu": False,
                "maxBitNum": 2,
                "pstatus": "ACTIVE",
                "countOnlineMachine": online,
                "system": "nmr",
                "supportGateName": gates or ["H", "X", "Ry", "Rz", "CNOT"],
                "couplingMap": coupling or [[1, 2], [2, 1]],
            }
        ],
    }


class SpinQCloudPreparationTests(unittest.TestCase):
    def test_bell_is_measurement_free_and_mcp_compatible(self):
        source = HEADER + """qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
"""
        prepared = prepare_from_discovery(source, discovery(), "gemini_vp")
        self.assertEqual(
            prepared,
            HEADER + "qreg q[2];\nh q[0];\ncx q[0], q[1];\n",
        )
        self.assertNotIn("measure", prepared)
        self.assertNotIn("creg", prepared)

    def test_rejects_unsupported_gate(self):
        source = HEADER + "qreg q[1];\ncreg c[1];\ns q[0];\nmeasure q -> c;\n"
        with self.assertRaisesRegex(SpinQCloudValidationError, "does not advertise"):
            prepare_from_discovery(source, discovery(), "gemini_vp")

    def test_rejects_offline_platform(self):
        source = HEADER + "qreg q[1];\ncreg c[1];\nh q[0];\nmeasure q -> c;\n"
        with self.assertRaisesRegex(SpinQCloudValidationError, "no online machine"):
            prepare_from_discovery(source, discovery(online=0), "gemini_vp")

    def test_rejects_missing_directed_coupling(self):
        source = HEADER + """qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
"""
        with self.assertRaisesRegex(SpinQCloudValidationError, "directed coupling"):
            prepare_from_discovery(
                source,
                discovery(coupling=[[2, 1]]),
                "gemini_vp",
            )

    def test_rejects_nonidentity_measurement_mapping(self):
        source = HEADER + """qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q[0] -> c[1];
measure q[1] -> c[0];
"""
        with self.assertRaisesRegex(SpinQCloudValidationError, "q\[i\] -> c\[i\]"):
            prepare_from_discovery(source, discovery(), "gemini_vp")

    def test_rejects_gate_after_measurement(self):
        source = HEADER + """qreg q[1];
creg c[1];
h q[0];
measure q[0] -> c[0];
x q[0];
"""
        with self.assertRaisesRegex(SpinQCloudValidationError, "after measurement"):
            prepare_from_discovery(source, discovery(), "gemini_vp")


if __name__ == "__main__":
    unittest.main()
