import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from common import az, kube, kubectl, outputs, state_dir


def http(url, data=None):
    request = urllib.request.Request(
        url, data=json.dumps(data).encode() if data else None,
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "ContosoStoreDemo/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read()
        return response.status, json.loads(body) if body and "json" in response.headers.get("Content-Type", "") else body


def sender_roles(args, result):
    principal = az("identity", "show", "-g", args.rg + "-app", "-n", "order-service")["principalId"]
    scope = (f"/subscriptions/{result['subscriptionId']}/resourceGroups/{args.rg}-app"
             f"/providers/Microsoft.ServiceBus/namespaces/{result['serviceBusName']}")
    roles = az("role", "assignment", "list", "--scope", scope)
    roles = [role for role in roles if role["principalId"].lower() == principal.lower()
             and role["roleDefinitionId"].endswith("69a216fc-b8fb-44d8-bc22-1f3c2cd27a39")]
    return principal, scope, roles


def ready_pods():
    pods = kubectl("-n", "store", "get", "pods", "-o", "json", json_output=True)["items"]
    active = [pod for pod in pods if not (
        pod.get("status", {}).get("phase") == "Succeeded"
        and any(owner["kind"] == "Job" for owner in pod["metadata"].get("ownerReferences", [])))]
    return bool(active) and all(any(condition["type"] == "Ready" and condition["status"] == "True"
                                   for condition in pod["status"].get("conditions", [])) for pod in active)


def pickup_healthy(url, product_id):
    started = time.monotonic()
    code, body = http(url + "/api/pickup/" + str(product_id))
    elapsed = time.monotonic() - started
    print(f"  Pickup product {product_id}: HTTP {code}, {elapsed:.3f}s", flush=True)
    return code == 200 and body["productId"] == product_id and body["availableQuantity"] >= 0 and elapsed < 2


def status(args, result):
    failures = 0

    def check(label, operation):
        nonlocal failures
        try:
            passed = bool(operation())
            print(("PASS" if passed else "FAIL") + " " + label, flush=True)
            failures += not passed
        except (RuntimeError, urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
            print("FAIL " + label + ": " + str(error), flush=True)
            failures += 1

    check("AppGw URL 200", lambda: http(result["appUrl"])[0] == 200)
    check("Active price book", lambda: http(result["appUrl"] + "/api/orders/pricing/active")[1]["active"])
    check("All pods Ready", ready_pods)
    for product_id in range(1, 11):
        check(f"SQL pickup product {product_id} under 2s",
              lambda product_id=product_id: pickup_healthy(result["appUrl"], product_id))
    check("Cosmos spoke DNS link", lambda: any(link["name"] == "spoke-link" for link in az(
        "network", "private-dns", "link", "vnet", "list", "-g", args.rg + "-app",
        "-z", "privatelink.documents.azure.com")))
    check("Service Bus sender role", lambda: bool(sender_roles(args, result)[2]))

    def queue_depth():
        queue = az("servicebus", "queue", "show", "-g", args.rg + "-app",
                   "--namespace-name", result["serviceBusName"], "-n", "orders")
        count = queue["countDetails"]["activeMessageCount"]
        print("  ActiveMessages:", count, flush=True)
        return count <= 5

    check("Service Bus queue depth <= 5", queue_depth)

    def end_to_end():
        order_id = str(time.time_ns() // 1000)
        code, _ = http(result["appUrl"] + "/api/orders", {
            "orderId": order_id, "customerId": "acceptance",
            "items": [{"productId": 1, "quantity": 1, "price": 10.0}], "status": 0})
        if code != 201:
            return False
        print("  Checkout accepted test order", order_id, "(HTTP 201)", flush=True)
        for _ in range(15):
            time.sleep(2)
            try:
                _, order = http(result["adminUrl"] + "/api/makeline/order/" + order_id)
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                continue
            if order.get("status") == 2 and order.get("orderId") == order_id:
                return True
        return False

    check("End-to-end order fulfilled in Cosmos via admin API", end_to_end)
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check application health and submit one synthetic order.")
    parser.add_argument("rg", nargs="?", default="rg-sreagent-demo")
    args = parser.parse_args()
    account = json.loads((state_dir(args.rg) / "preflight.json").read_text())
    az("account", "set", "--subscription", account["subscription"], json_output=False)
    kube(args.rg)
    sys.exit(1 if status(args, outputs(args.rg)) else 0)
