import json
import logging
import os
import time
import urllib.error
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
mode = os.environ["MODE"]
if mode not in ("customer", "worker", "pickup"):
    raise ValueError("MODE must be customer, worker or pickup")
product_index = 0


def request(url, data=None, method=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "ContosoStoreDemo/1.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        result = response.read()
        return json.loads(result) if result else None


while True:
    try:
        if mode in ("customer", "pickup"):
            store = os.environ["STORE_URL"].rstrip("/")
            products = request(store + "/api/products")
            if not isinstance(products, list) or not products:
                raise ValueError("Sports catalog is empty or invalid")
            product = products[product_index % len(products)]
            product_index += 1
        if mode == "customer":
            order_id = str(time.time_ns() // 1000)
            request(
                store + "/api/orders",
                {
                    "orderId": order_id,
                    "customerId": "demo-customer",
                    "items": [{"productId": product["id"], "quantity": 1, "price": product["price"]}],
                    "status": 0,
                },
            )
            logging.info("Accepted sports order %s: %s", order_id, product["name"])
        elif mode == "pickup":
            pickup = request(store + "/api/pickup/" + str(product["id"]))
            if not isinstance(pickup, dict) or pickup.get("productId") != product["id"]:
                raise ValueError("Invalid pickup availability response")
            logging.info("SQL pickup availability: %s", pickup)
        else:
            makeline = os.environ["MAKELINE_SERVICE_URL"].rstrip("/")
            for order in request(makeline + "/order/fetch") or []:
                order["status"] = 2
                request(makeline + "/order", order, "PUT")
                logging.info("Fulfilled order %s", order["orderId"])
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as error:
        logging.error("%s failed: %s", mode, error)
    time.sleep(5 if mode == "pickup" else 3 if mode == "customer" else 2)
