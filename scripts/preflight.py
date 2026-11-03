import concurrent.futures
import json
from pathlib import Path
import re
import sys
from common import ROOT, az, github_env, retire_activity_export, run, state_dir

PROVIDERS = [
    "ContainerService", "KubernetesConfiguration", "App", "DocumentDB", "ServiceBus",
    "Network", "Insights", "AlertsManagement", "Monitor", "OperationalInsights",
    "ManagedIdentity", "KeyVault", "ContainerRegistry", "Sql",
]
REGIONS = ["canadacentral", "polandcentral", "italynorth", "francecentral"]


def preflight(rg):
    state = state_dir(rg)
    accounts = az("account", "list")
    matches = [a for a in accounts if a["name"].casefold() == "Private Test Sub PuneetG".casefold()]
    if len(matches) != 1:
        raise RuntimeError("The required Private Test Sub PUNEETG subscription is missing or ambiguous")
    az("account", "set", "--subscription", matches[0]["id"], json_output=False)
    account = az("account", "show")
    env = github_env()
    run("gh", "repo", "view", "puneetg1983/sre-agent-demo", "--json", "url", env=env)
    params = (ROOT / "infra" / "main.bicepparam").read_text()
    if re.search(r"param enableSreAgent\s*=\s*true", params):
        raise RuntimeError("SRE Agent configuration is deferred and not implemented; do not enable the placeholder module")
    # Subscription exports survive RG deletion and otherwise exhaust the five-setting limit.
    for previous in (ROOT / ".state").iterdir():
        marker = previous / "preflight.json"
        if previous.is_dir() and previous.name != rg and marker.exists():
            old = json.loads(marker.read_text())
            if (old["subscription"] == account["id"]
                    and not az("group", "exists", "--name", previous.name + "-app")):
                retire_activity_export(previous.name, account["id"])
    print("Subscription:", account["name"], flush=True)
    registrations = az("provider", "list")
    pending = [p["namespace"] for p in registrations
               if p["namespace"] in ["Microsoft." + p for p in PROVIDERS]
               and p["registrationState"] != "Registered"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda ns: az("provider", "register", "--namespace", ns, "--wait", json_output=False), pending))
    assignments = az("policy", "assignment", "list", "--disable-scope-strict-match")
    policies = []
    for assignment in assignments:
        definition = az("rest", "--method", "get", "--url",
                        assignment["policyDefinitionId"] + "?api-version=2023-04-01")
        policies.append({"assignment": assignment, "definition": definition})
    (state / "policies.json").write_text(json.dumps(policies, indent=2), encoding="utf-8")
    print("Policies inspected:", ", ".join(a["name"] for a in assignments), flush=True)
    availability = {}
    for namespace, resource in [
        ("ContainerService", "managedClusters"), ("Network", "applicationGateways"),
        ("DocumentDB", "databaseAccounts"), ("ServiceBus", "namespaces"),
        ("Monitor", "accounts"), ("Insights", "components"),
        ("Sql", "servers"),
    ]:
        provider = az("provider", "show", "--namespace", "Microsoft." + namespace)
        types = [t for t in provider["resourceTypes"] if t["resourceType"].casefold() == resource.casefold()]
        availability[namespace] = {loc.replace(" ", "").lower() for t in types for loc in t.get("locations", [])}
    chosen = None
    unavailable_file = ROOT / ".state" / "region-unavailable.json"
    unavailable = json.loads(unavailable_file.read_text()) if unavailable_file.exists() else {}
    existing = az("group", "exists", "--name", rg + "-app")
    existing_location = az("group", "show", "--name", rg + "-app")["location"] if existing else None
    for region in REGIONS:
        if existing_location and region != existing_location:
            continue
        if region in unavailable and not existing_location:
            print("Skipping", region, "-", unavailable[region], flush=True)
            continue
        if not all(region in locations for locations in availability.values()):
            print("Skipping", region, "- required service not advertised", flush=True)
            continue
        skus = az("vm", "list-skus", "--location", region, "--resource-type",
                  "virtualMachines", "--size", "Standard_D4s_v5", "--all")
        sku = next((s for s in skus if s["name"] == "Standard_D4s_v5" and not s["restrictions"]), None)
        if not sku:
            continue
        usages = az("vm", "list-usage", "--location", region)
        quota = {u["name"]["value"].lower(): int(u["limit"]) - int(u["currentValue"]) for u in usages}
        # Four 4-vCPU nodes plus one surge node per pool.
        if min(quota.get("cores", 0), quota.get(sku["family"].lower(), 0)) < 24:
            print("Skipping", region, "- fewer than 24 free vCPUs", flush=True)
            continue
        editions = az("sql", "db", "list-editions", "--location", region)
        if not any(e["name"] == "Basic" and e["status"] in ("Available", "Default") for e in editions):
            print("Skipping", region, "- Azure SQL Basic is unavailable", flush=True)
            continue
        chosen = region
        break
    if not chosen:
        raise RuntimeError("HUMAN BLOCKER: no candidate has unrestricted SKU, service availability, and sufficient quota")
    (state / "preflight.json").write_text(json.dumps({"region": chosen, "subscription": account["id"]}), encoding="utf-8")
    print("Selected", chosen, "Standard_D4s_v5; SRE Agent integration deferred by user", flush=True)
    return account, chosen


if __name__ == "__main__":
    preflight(sys.argv[1] if len(sys.argv) > 1 else "rg-sreagent-demo")
