import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
os.environ["MSYS_NO_PATHCONV"] = "1"
tools = ROOT / ".tools"
os.environ["PATH"] = str(tools) + os.pathsep + os.environ["PATH"]


def run(*args, json_output=False, check=True, quiet=False, env=None):
    command = [str(arg) for arg in args]
    command[0] = shutil.which(command[0]) or command[0]
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", env=env,
        cwd=ROOT,
    )
    if check and result.returncode:
        raise RuntimeError(f"{args[0]} {args[1]} failed:\n{result.stderr or result.stdout}")
    if not quiet and result.stderr and result.returncode == 0:
        print(result.stderr.strip())
    if json_output and result.returncode == 0:
        return json.loads(result.stdout)
    return result


def az(*args, json_output=True, check=True, quiet=False):
    return run("az", *args, "--only-show-errors", "-o",
               "json" if json_output else "tsv", json_output=json_output,
               check=check, quiet=quiet)


def github_env():
    env = os.environ.copy()
    env.pop("GH_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    token = run("gh", "auth", "token", "--hostname", "github.com",
                "--user", "puneetg1983", env=env, quiet=True).stdout.strip()
    env["GH_TOKEN"] = token
    return env


def state_dir(rg):
    if not rg or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in rg):
        raise ValueError("Resource-group base must contain only letters, numbers, hyphens, or underscores")
    path = ROOT / ".state" / rg
    path.mkdir(parents=True, exist_ok=True)
    return path


def retire_activity_export(rg, subscription):
    if az("group", "exists", "--name", rg + "-app"):
        raise RuntimeError("Do not retire the Activity Log export while its app RG exists")
    name = rg + "-activity"
    settings = az("monitor", "diagnostic-settings", "subscription", "list")["value"]
    setting = next((item for item in settings if item["name"] == name), None)
    if setting:
        expected = (f"/subscriptions/{subscription}/resourceGroups/{rg}-app"
                    "/providers/Microsoft.OperationalInsights/workspaces/store-logs")
        if setting.get("workspaceId", "").casefold() != expected.casefold():
            raise RuntimeError("Refusing to delete an Activity Log export with a different destination")
        az("monitor", "diagnostic-settings", "subscription", "delete", "--name", name, "--yes", json_output=False)
        print("Removed retired demo Activity Log export:", name, flush=True)


def outputs(rg):
    return {name: value["value"] for name, value in az(
        "deployment", "sub", "show", "--name", rg, "--query", "properties.outputs"
    ).items()}


def kube(rg):
    if not shutil.which("kubelogin"):
        tools.mkdir(exist_ok=True)
        az("aks", "install-cli", "--install-location", str(tools / ("kubectl.exe" if os.name == "nt" else "kubectl")),
           "--kubelogin-install-location", str(tools / ("kubelogin.exe" if os.name == "nt" else "kubelogin")),
           json_output=False)
    config = state_dir(rg) / "kubeconfig"
    az("aks", "get-credentials", "-g", rg + "-app", "-n", "store-aks",
       "--file", str(config), "--overwrite-existing", json_output=False)
    run("kubelogin", "convert-kubeconfig", "-l", "azurecli", "--kubeconfig", config, quiet=True)
    os.environ["KUBECONFIG"] = str(config)


def kubectl(*args, json_output=False, check=True):
    return run("kubectl", *args, json_output=json_output, check=check, quiet=True)
