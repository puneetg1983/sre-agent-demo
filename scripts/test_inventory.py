import json
import os
from pathlib import Path
import socket
import subprocess
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DLL = ROOT / "app" / "src" / "inventory-service" / "bin" / "Release" / "net8.0" / "inventory-service.dll"


class InventoryTests(unittest.TestCase):
    def test_unknown_command_fails_without_starting_a_server(self):
        result = subprocess.run(["dotnet", str(DLL), "unsupported-command"],
                                capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Expected 'bootstrap' or web host options.", result.stderr)

    def test_web_health_does_not_require_a_database_connection(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = os.environ.copy()
        env.pop("APPINSIGHTS_CONNECTION_STRING", None)
        env.pop("SQL_SERVER", None)
        env.pop("SQL_DATABASE", None)
        env.update(AZURE_TENANT_ID="00000000-0000-0000-0000-000000000001",
                   AZURE_CLIENT_ID="00000000-0000-0000-0000-000000000002",
                   AZURE_FEDERATED_TOKEN_FILE=str(Path(__file__)))
        process = subprocess.Popen(
            ["dotnet", str(DLL), "--urls", f"http://127.0.0.1:{port}"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            for _ in range(100):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(json.load(response), {"status": "ok"})
                        return
                except urllib.error.URLError:
                    if process.poll() is not None:
                        self.fail(process.stdout.read())
                    time.sleep(0.1)
            self.fail("Inventory service did not start")
        finally:
            if process.poll() is None:
                process.terminate()
            process.communicate(timeout=10)


if __name__ == "__main__":
    unittest.main()
