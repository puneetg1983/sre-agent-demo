import http.server
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class Orders(http.server.BaseHTTPRequestHandler):
    status = 201
    received = None

    def do_POST(self):
        Orders.received = self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(Orders.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"accepted":true}')

    def log_message(self, *_):
        pass


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class CheckoutTests(unittest.TestCase):
    def start_app(self, dates):
        server = http.server.HTTPServer(("127.0.0.1", 0), Orders)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = free_port()
        env = os.environ.copy()
        env.update(
            ASPNETCORE_URLS=f"http://127.0.0.1:{port}",
            PRICEBOOK_EFFECTIVE_FROM=dates,
            ORDER_SERVICE_URL=f"http://127.0.0.1:{server.server_port}/",
        )
        process = subprocess.Popen(
            ["dotnet", str(ROOT / "app" / "src" / "checkout-api" / "bin" / "Release" / "net8.0" / "checkout-api.dll")],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
        )
        def stop():
            process.terminate()
            process.communicate(timeout=10)
        self.addCleanup(stop)
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                    self.assertEqual(response.status, 200)
                    return process, port
            except urllib.error.URLError:
                if process.poll() is not None:
                    self.fail(process.stdout.read())
                time.sleep(0.1)
        self.fail("Checkout failed to start")

    def test_future_book_stays_ready_but_returns_503_without_date_leak(self):
        process, port = self.start_app("2099-01-01T00:00:00Z")
        request = urllib.request.Request(f"http://127.0.0.1:{port}/", data=b"{}", headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request)
        self.assertEqual(raised.exception.code, 503)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/pricing/active") as response:
            self.assertFalse(json.load(response)["active"])
        process.terminate()
        log, _ = process.communicate(timeout=10)
        self.assertIn("No active price book for", log)
        self.assertNotIn("2099", log)

    def test_active_book_forwards_order_unchanged(self):
        Orders.status = 201
        _, port = self.start_app("2099-01-01T00:00:00Z;2020-01-01T00:00:00Z")
        body = b'{"orderId":"123","status":0}'
        request = urllib.request.Request(f"http://127.0.0.1:{port}/", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 201)
        self.assertEqual(Orders.received, body)

    def test_order_authorization_failure_is_not_success(self):
        Orders.status = 500
        _, port = self.start_app("2020-01-01T00:00:00Z")
        request = urllib.request.Request(f"http://127.0.0.1:{port}/", data=b"{}", headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request)
        self.assertEqual(raised.exception.code, 500)


if __name__ == "__main__":
    unittest.main()
