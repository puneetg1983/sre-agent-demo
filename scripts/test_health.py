import unittest
from unittest.mock import patch
from health import pickup_healthy, ready_pods


class HealthTests(unittest.TestCase):
    @patch("health.kubectl")
    def test_completed_jobs_are_not_mistaken_for_unready_services(self, kubectl):
        kubectl.return_value = {"items": [
            {"metadata": {}, "status": {"phase": "Running", "conditions": [{"type": "Ready", "status": "True"}]}},
            {"metadata": {"ownerReferences": [{"kind": "Job"}]}, "status": {"phase": "Succeeded"}},
        ]}
        self.assertTrue(ready_pods())
        kubectl.return_value["items"][0]["status"]["conditions"][0]["status"] = "False"
        self.assertFalse(ready_pods())

    @patch("health.kubectl", return_value={"items": []})
    def test_empty_namespace_is_not_healthy(self, kubectl):
        self.assertFalse(ready_pods())

    @patch("health.http", return_value=(200, {"productId": 3, "availableQuantity": 13}))
    @patch("health.time.monotonic", side_effect=[100, 103])
    def test_pickup_must_meet_the_response_time_limit(self, clock, http):
        self.assertFalse(pickup_healthy("http://demo", 3))


if __name__ == "__main__":
    unittest.main()
