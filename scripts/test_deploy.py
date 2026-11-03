import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from deploy import build_images, existing_action_group, receiver_configuration


class NativeBuildTests(unittest.TestCase):
    @patch("deploy.az")
    @patch("deploy.run")
    def test_non_streaming_builds_require_success_and_cover_all_images(self, run, az):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({"status": "Succeeded"}), "")
        az.side_effect = lambda *args: [] if args[2] == "list" else {"digest": "sha256:test"}
        with tempfile.TemporaryDirectory() as directory:
            build_images("registry", "source", "tag", Path(directory))
            images = json.loads((Path(directory) / "images.json").read_text())
        self.assertEqual(set(images), {
            "checkout-api", "order-service", "makeline-service", "demo-traffic",
            "store-front", "store-admin", "product-service", "inventory-service",
        })
        self.assertEqual(run.call_count, 8)
        for call in run.call_args_list:
            self.assertIn("--no-logs", call.args)
            self.assertNotIn("--no-wait", call.args)

    @patch("deploy.az", return_value=[])
    @patch("deploy.run")
    def test_failed_remote_status_is_not_accepted_even_with_zero_cli_exit(self, run, az):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({"status": "Failed"}), "")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "did not succeed"):
                build_images("registry", "source", "tag", Path(directory))
            self.assertFalse((Path(directory) / "images.json").exists())


class ActionGroupTests(unittest.TestCase):
    @patch("deploy.az")
    def test_existing_receivers_are_referenced_without_writes(self, az):
        group = {"name": "store-incidents", "enabled": True,
                 "tags": {"demo": "sreagent", "rgName": "demo"},
                 "emailReceivers": [{"name": "test-notification", "emailAddress": "demo@example.invalid"}]}
        az.side_effect = [True, [group]]
        self.assertEqual(existing_action_group("demo"), group)
        self.assertEqual([call.args[:3] for call in az.call_args_list],
                         [("group", "exists", "--name"), ("monitor", "action-group", "list")])
        self.assertEqual(receiver_configuration(group)["emailReceivers"], group["emailReceivers"])

    @patch("deploy.az")
    def test_unowned_action_group_is_never_replaced(self, az):
        az.side_effect = [True, [{"name": "store-incidents", "enabled": True, "tags": {}}]]
        with self.assertRaisesRegex(RuntimeError, "ownership"):
            existing_action_group("demo")

    @patch("deploy.az")
    def test_fresh_group_can_be_created(self, az):
        az.return_value = False
        self.assertIsNone(existing_action_group("demo"))

    def test_receiver_comparison_includes_webhooks_and_role_receivers(self):
        original = {"enabled": True, "groupShortName": "StoreDemo", "webhookReceivers": [{"name": "hook"}],
                    "armRoleReceivers": [{"name": "role"}]}
        self.assertNotEqual(receiver_configuration(original),
                            receiver_configuration({**original, "webhookReceivers": []}))


if __name__ == "__main__":
    unittest.main()
