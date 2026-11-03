import json
import shutil
import subprocess
import sys
import time
from common import ROOT, az, kube, kubectl, outputs, run, state_dir
from preflight import preflight


def build_images(registry, source_sha, image_tag, state):
    repositories = az("acr", "repository", "list", "--name", registry)
    images = {}
    for service in ["checkout-api", "order-service", "makeline-service", "demo-traffic",
                    "store-front", "store-admin", "product-service", "inventory-service"]:
        tags = az("acr", "repository", "show-tags", "--name", registry,
                  "--repository", service) if service in repositories else []
        if image_tag not in tags:
            print("Building with Azure-native ACR Tasks:", service, flush=True)
            context = f"https://github.com/puneetg1983/sre-agent-demo.git#{source_sha}:app/src/{service}"
            build = run("az", "acr", "build", "--registry", registry,
                        "--image", f"{service}:{image_tag}", "--file", "Dockerfile",
                        "--timeout", "1800", context, "--no-logs", "-o", "json",
                        "--only-show-errors", check=False)
            log = state / f"build-{service}.log"
            log.write_text(build.stdout + build.stderr, encoding="utf-8")
            if build.returncode:
                raise RuntimeError(f"Azure-native image build failed for {service}; see {log}")
            metadata = json.loads(build.stdout)
            if metadata.get("status") != "Succeeded":
                raise RuntimeError(f"Azure-native image build did not succeed for {service}; see {log}")
        else:
            print("Preserving existing immutable image:", service + ":" + image_tag, flush=True)
        image = az("acr", "repository", "show", "--name", registry,
                   "--image", service + ":" + image_tag)
        images[service] = {"tag": image_tag, "digest": image["digest"]}
        print("Image available:", service, image["digest"], flush=True)
    (state / "images.json").write_text(json.dumps(images, indent=2), encoding="utf-8")


def existing_action_group(rg):
    if not az("group", "exists", "--name", rg + "-app"):
        return None
    groups = az("monitor", "action-group", "list", "-g", rg + "-app")
    group = next((g for g in groups if g["name"] == "store-incidents"), None)
    if group and ((group.get("tags") or {}).get("demo") != "sreagent"
                  or (group.get("tags") or {}).get("rgName") != rg):
        raise RuntimeError("Action-group ownership tags do not match; refusing to replace notification settings")
    if group and not group["enabled"]:
        raise RuntimeError("Existing store-incidents action group is disabled; enable it before deploying")
    return group


def receiver_configuration(group):
    return {key: value for key, value in group.items()
            if key.endswith("Receivers") or key in ("enabled", "groupShortName")}


def deploy(rg):
    started = time.monotonic()
    account, region = preflight(rg)
    state = state_dir(rg)
    dirty = run("git", "status", "--porcelain").stdout.strip()
    if dirty:
        raise RuntimeError("Commit and push the source before deploying: Flux must read exactly the checked-in app")
    local_sha = run("git", "rev-parse", "HEAD").stdout.strip()
    image_tag = run("git", "rev-parse", "HEAD:app/src").stdout.strip()
    remote_sha = run("git", "ls-remote", "origin", "refs/heads/main").stdout.split()[0]
    if local_sha != remote_sha:
        raise RuntimeError("HEAD must match origin/main; push the source before deploying")
    existing_nsgs = az("network", "nsg", "list", "-g", rg + "-app") if az(
        "group", "exists", "--name", rg + "-app") else []
    reuse_nsgs = bool(existing_nsgs)
    action_group = existing_action_group(rg)
    if reuse_nsgs and (
        {nsg["name"] for nsg in existing_nsgs} != {"hub-nsg", "aks-nsg", "appgw-nsg", "pe-nsg"}
        or any((nsg.get("tags") or {}).get("demo") != "sreagent"
               or (nsg.get("tags") or {}).get("rgName") != rg for nsg in existing_nsgs)
    ):
        raise RuntimeError("Existing NSGs are incomplete or ownership tags do not match; refusing unsafe replacement")
    run("az", "bicep", "build", "--file", ROOT / "infra" / "main.bicep", "--stdout", quiet=True)
    images_built = False
    if existing_nsgs:
        registries = az("acr", "list", "-g", rg + "-app")
        if registries:
            build_images(registries[0]["name"], local_sha, image_tag, state)
            images_built = True
    print("Starting one subscription deployment:", rg, flush=True)
    command = [
        shutil.which("az"), "deployment", "sub", "create", "--name", rg, "-l", region,
        "-f", str(ROOT / "infra" / "main.bicep"), "-p", str(ROOT / "infra" / "main.bicepparam"),
        "-p", f"rgName={rg}", f"imageTag={image_tag}", f"location={region}",
        f"reuseExistingNsgs={str(reuse_nsgs).lower()}", "--only-show-errors", "-o", "json",
    ]
    command.extend(["-p", f"reuseExistingActionGroup={str(action_group is not None).lower()}"])
    with (state / "deployment.json").open("w", encoding="utf-8") as out, (state / "deployment-error.log").open("w", encoding="utf-8") as err:
        process = subprocess.Popen(command, stdout=out, stderr=err, cwd=ROOT)
        try:
            deadline = time.monotonic() + 3600
            while process.poll() is None:
                if time.monotonic() > deadline:
                    raise RuntimeError("Deployment exceeded 60 minutes; inspect its operations before retrying")
                if not images_built:
                    registries = az("acr", "list", "-g", rg + "-app", check=False, quiet=True)
                    acr = registries[0] if isinstance(registries, list) and registries else None
                    if acr and acr["provisioningState"] == "Succeeded":
                        build_images(acr["name"], local_sha, image_tag, state)
                        images_built = True
                time.sleep(10)
            if process.returncode:
                error = (state / "deployment-error.log").read_text(encoding="utf-8")
                print(error, file=sys.stderr)
                failed = az("deployment", "operation", "sub", "list", "--name", rg, check=False)
                (state / "failed-operations.json").write_text(json.dumps(failed if isinstance(failed, list) else failed.stdout, indent=2))
                raise RuntimeError("ARM deployment failed; inspect operations and fix the template before retrying. Do not delete an existing app environment.")
        finally:
            if process.poll() is None:
                # Only the local CLI is stopped; Azure deployment remains inspectable.
                process.terminate()
                process.wait()
    result = outputs(rg)
    if action_group is not None:
        current_group = existing_action_group(rg)
        if current_group is None or receiver_configuration(current_group) != receiver_configuration(action_group):
            raise RuntimeError("Action-group notification settings changed during deployment; inspect before proceeding")
        print("Existing notification receivers preserved without updating the action group.", flush=True)
    if not images_built:
        build_images(result["acrName"], local_sha, image_tag, state)
    kube(rg)
    print("Waiting for Flux and application readiness (read-only kubectl)...", flush=True)
    kubectl("-n", "store", "wait", "deployment", "--all", "--for=condition=Available", "--timeout=1200s")
    kubectl("-n", "flux-system", "wait", "kustomization", "--all", "--for=condition=Ready", "--timeout=1200s")
    run("python", ROOT / "scripts" / "health.py", rg)
    print(json.dumps(result, indent=2))
    print("Deploy elapsed seconds:", round(time.monotonic() - started), flush=True)


if __name__ == "__main__":
    deploy(sys.argv[1] if len(sys.argv) > 1 else "rg-sreagent-demo")
