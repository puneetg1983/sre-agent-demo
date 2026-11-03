import os
import subprocess
import time
import unittest
import urllib.error
import urllib.request
from test_checkout import ROOT, free_port


class OrderTests(unittest.TestCase):
    def setUp(self):
        self.port = free_port()
        env = os.environ.copy()
        env.update(ASPNETCORE_URLS=f"http://127.0.0.1:{self.port}",
                   ORDER_QUEUE_HOSTNAME="unavailable.servicebus.windows.net",
                   ORDER_QUEUE_NAME="orders")
        self.process = subprocess.Popen(
            ["dotnet", str(ROOT / "app" / "src" / "order-service" / "bin" / "Release" / "net8.0" / "order-service.dll")],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        self.addCleanup(self.stop)
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=1) as response:
                    self.assertEqual(response.status, 200)
                    return
            except urllib.error.URLError:
                if self.process.poll() is not None:
                    self.fail(self.process.stdout.read())
                time.sleep(0.1)
        self.fail("Order service did not start without a reachable queue")

    def stop(self):
        self.process.terminate()
        self.process.communicate(timeout=10)

    def test_invalid_orders_fail_before_queue_access_and_health_stays_ready(self):
        for body in [b"{", b"{}", b'{"orderId":""}', b'{"orderId":123}']:
            request = urllib.request.Request(f"http://127.0.0.1:{self.port}/", data=body,
                                             headers={"Content-Type": "application/json"})
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=3)
            self.assertEqual(raised.exception.code, 400)
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=3) as response:
            self.assertEqual(response.status, 200)


if __name__ == "__main__":
    unittest.main()
