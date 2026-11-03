import io
import json
import os
from pathlib import Path
import runpy
import unittest
import urllib.error
from unittest.mock import patch


TRAFFIC = Path(__file__).resolve().parents[1] / "app" / "src" / "demo-traffic" / "traffic.py"


class PickupMonitorTests(unittest.TestCase):
    def test_rotates_all_products_even_when_every_pickup_request_times_out(self):
        products = [{"id": product_id} for product_id in range(1, 11)]

        def response(request, **kwargs):
            if request.full_url == "http://demo/api/products":
                return io.BytesIO(json.dumps(products).encode())
            raise urllib.error.HTTPError(request.full_url, 503, "Unavailable", {},
                                         io.BytesIO(b'{"code":"sql_timeout"}'))

        with patch.dict(os.environ, {"MODE": "pickup", "STORE_URL": "http://demo"}), \
                patch("urllib.request.urlopen", side_effect=response) as urlopen, \
                patch("time.sleep", side_effect=[None] * 9 + [StopIteration]), \
                patch("logging.basicConfig"), patch("logging.error") as error:
            with self.assertRaises(StopIteration):
                runpy.run_path(str(TRAFFIC), run_name="__main__")
        pickup_urls = [args[0].full_url for args, _ in urlopen.call_args_list
                       if "/api/pickup/" in args[0].full_url]
        self.assertEqual(pickup_urls, ["http://demo/api/pickup/" + str(product_id)
                                      for product_id in range(1, 11)])
        self.assertEqual(error.call_count, 10)

    def test_rejects_pickup_data_for_the_wrong_product(self):
        replies = [io.BytesIO(b'[{"id":3}]'), io.BytesIO(b'{"productId":2}')]
        with patch.dict(os.environ, {"MODE": "pickup", "STORE_URL": "http://demo"}), \
                patch("urllib.request.urlopen", side_effect=replies), \
                patch("time.sleep", side_effect=StopIteration), \
                patch("logging.basicConfig"), patch("logging.error") as error:
            with self.assertRaises(StopIteration):
                runpy.run_path(str(TRAFFIC), run_name="__main__")
        self.assertEqual(error.call_count, 1)
        self.assertIn("Invalid pickup availability response", str(error.call_args))

    def test_customer_orders_still_use_the_catalog_product_and_price(self):
        replies = [io.BytesIO(b'[{"id":2,"price":89.99,"name":"Tennis Racket"}]'),
                   io.BytesIO(b'')]
        with patch.dict(os.environ, {"MODE": "customer", "STORE_URL": "http://demo"}), \
                patch("urllib.request.urlopen", side_effect=replies) as urlopen, \
                patch("time.sleep", side_effect=StopIteration), \
                patch("logging.basicConfig"), patch("logging.error") as error:
            with self.assertRaises(StopIteration):
                runpy.run_path(str(TRAFFIC), run_name="__main__")
        order_request = urlopen.call_args_list[1].args[0]
        self.assertEqual(order_request.full_url, "http://demo/api/orders")
        self.assertEqual(json.loads(order_request.data)["items"],
                         [{"productId": 2, "quantity": 1, "price": 89.99}])
        error.assert_not_called()


if __name__ == "__main__":
    unittest.main()
