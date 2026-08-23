import json
import unittest

from scripts.backend_observations import collect_aws_braket, collect_originq


class FakeOriginQService:
    def __init__(self, *, api_key):
        self.api_key = api_key

    def backends(self):
        return {"WK_C180": True, "WK_C102_400": False}


class FakeBraketClient:
    def __init__(self, region):
        self.region = region
        self.search_calls = 0

    def search_devices(self, **request):
        self.search_calls += 1
        if self.search_calls == 1:
            return {
                "devices": [
                    {
                        "deviceArn": "arn:aws:braket:us-east-1::device/qpu/test/QPU",
                        "deviceName": "QPU",
                        "deviceStatus": "ONLINE",
                        "deviceType": "QPU",
                        "providerName": "Test",
                    }
                ],
                "nextToken": "page-2",
            }
        self.last_request = request
        return {"devices": []}

    def get_device(self, *, deviceArn):
        return {
            "deviceArn": deviceArn,
            "deviceName": "QPU",
            "deviceStatus": "ONLINE",
            "deviceType": "QPU",
            "providerName": "Test",
            "deviceCapabilities": json.dumps({"paradigm": {"qubitCount": 42}}),
            "deviceQueueInfo": [
                {"queue": "QUANTUM_TASKS_QUEUE", "queueSize": "3"}
            ],
        }


class BackendObservationTests(unittest.TestCase):
    def test_originq_reports_authentication_requirement_without_key(self):
        observation = collect_originq(api_key=None, service_factory=FakeOriginQService)
        self.assertEqual(observation["status"], "authentication_required")
        self.assertEqual(observation["devices"], [])

    def test_originq_reads_backend_map_without_exposing_key(self):
        observation = collect_originq(
            api_key="secret", service_factory=FakeOriginQService
        )
        self.assertEqual(observation["status"], "ok")
        self.assertEqual(
            observation["devices"],
            [
                {"id": "WK_C102_400", "online": False},
                {"id": "WK_C180", "online": True},
            ],
        )
        self.assertNotIn("secret", json.dumps(observation))

    def test_aws_collects_status_queue_and_qubits_with_read_calls(self):
        clients = {}

        def factory(region):
            clients[region] = FakeBraketClient(region)
            return clients[region]

        observation = collect_aws_braket(
            regions=["us-east-1"], client_factory=factory
        )

        self.assertEqual(observation["status"], "ok")
        self.assertEqual(observation["devices"][0]["qubits"], 42)
        self.assertEqual(observation["devices"][0]["queues"][0]["queueSize"], "3")
        self.assertEqual(
            clients["us-east-1"].last_request["nextToken"], "page-2"
        )
        self.assertEqual(
            observation["required_permissions"],
            ["braket:SearchDevices", "braket:GetDevice"],
        )


if __name__ == "__main__":
    unittest.main()
