import sys
from common import az, retire_activity_export, state_dir

rg = sys.argv[1] if len(sys.argv) > 1 else "rg-sreagent-demo"
state_dir(rg)
if rg.endswith("-sreagent"):
    raise ValueError("Refusing to target an agent resource group")
accounts = az("account", "list")
subscription = next(a["id"] for a in accounts if a["name"].casefold() == "Private Test Sub PuneetG".casefold())
az("account", "set", "--subscription", subscription, json_output=False)
app_rg = rg + "-app"
if not az("group", "exists", "--name", app_rg):
    retire_activity_export(rg, subscription)
    print("App resource group does not exist:", app_rg)
    sys.exit(0)
group = az("group", "show", "--name", app_rg)
if group.get("tags", {}).get("demo") != "sreagent" or group["tags"].get("rgName") != rg:
    raise RuntimeError("Refusing to delete an app resource group without matching demo ownership tags")
vaults = az("keyvault", "list", "-g", app_rg)
az("group", "delete", "--name", app_rg, "--yes", json_output=False)
retire_activity_export(rg, subscription)
for vault in vaults:
    az("keyvault", "purge", "--name", vault["name"], "--location", vault["location"], json_output=False)
print("Deleted only", app_rg, "and purged its soft-deleted vaults; the agent RG was untouched.")
