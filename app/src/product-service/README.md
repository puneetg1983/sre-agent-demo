# product-service

This Rust REST API serves the product catalog used by [store-front](../store-front) and [store-admin](../store-admin/).

This app is a simple REST API that allows you to get a list of products, get a single product, update a product, and add a product.

Azure SQL is the default storage backend. Product creates, edits, categories, and deletions persist across process restarts. Database failures produce non-success responses (503 for storage unavailability); the service never silently falls back to seed data.

The canonical [`catalog.json`](catalog.json) contains 210 initial products, including the original IDs 1–10. SQL stores image paths, not image binaries; the frontend serves the corresponding assets.

## Azure SQL configuration

The runtime requires:

| Variable | Value |
| --- | --- |
| `SQL_SERVER` | Azure SQL DNS hostname, without `tcp:` or a port |
| `SQL_DATABASE` | Existing catalog/pickup database name |
| `AZURE_CLIENT_ID` | Product-service managed identity client ID |
| `AZURE_TENANT_ID` | Microsoft Entra tenant ID |
| `AZURE_FEDERATED_TOKEN_FILE` | Projected workload-identity token file |

AKS injects the `AZURE_*` values for the `product-service` service account. SQL access uses an Entra token and validated TLS, not a connection password. The deployment reads SQL settings from the `store/sql-settings` ConfigMap.

`GET /health` checks process health. `GET /ready` checks catalog access and is used by the deployment readiness probe. CRUD, `/import`, `/metrics`, and the AI tuning dataset read or modify the same SQL catalog.

### Bootstrap and permissions

The inventory-service image provides the `bootstrap` command. The `store/sql-bootstrap` Job runs it as the existing `sql-operator` service account; product-service never performs DDL.

Kustomize generates `store/catalog-seed-<content-hash>` from this directory's `catalog.json` and rewrites the Job volume reference. The Job mounts it at `/catalog/catalog.json` and sets `CATALOG_SEED_PATH` to that path. Its SQL configuration also requires `INVENTORY_SERVICE_CLIENT_ID` and `PRODUCT_SERVICE_CLIENT_ID`, the runtime identities being granted access. The Job's injected `AZURE_CLIENT_ID` belongs to **sql-operator**, not product-service.

Bootstrap creates or maintains:

- `dbo.Products`: catalog fields including `Category`; explicit seed IDs 1–210 advance its identity so the first generated ID is 211 on a fresh catalog.
- `dbo.CatalogSeedHistory`: seed-ID ledger so later bootstrap runs do not resurrect intentionally deleted catalog products.
- `dbo.PickupInventory`: pickup availability, with missing seed-product rows added without resetting existing stock or store settings.
- `dbo.GetPickupAvailability @ProductId int`: existing pickup-read procedure.

Existing product edits and unrelated rows are preserved. Catalog seeding, the seed ledger, new pickup rows, and product grants are committed together under the transaction-owned `Contoso.CatalogBootstrap` application lock.

`[product-service]` receives `SELECT, INSERT, UPDATE, DELETE` only on `dbo.Products`. It is explicitly denied those operations on `dbo.PickupInventory` and `dbo.CatalogSeedHistory`, and denied `CREATE TABLE` and `ALTER ANY SCHEMA`. `[inventory-service]` receives `EXECUTE` on `dbo.GetPickupAvailability`, not table mutation rights. Bootstrap rejects identity/client-ID mismatches. It does not change `sql-mcp-reader` or grant database-owner roles.

### Safe bootstrap-before-release order

1. Build the new inventory-service and product-service images (and matching frontend/admin images) under the same new source-tree tag. Do not update Flux's common `IMAGE_TAG` yet.
2. Render `app` with Kustomize. For a bootstrap-only payload, select the generated catalog ConfigMap, `sql-settings`, and `sql-bootstrap` Job—**not** the application Deployments. Resolve `SQL_SERVER`, `SQL_DATABASE`, `INVENTORY_SERVICE_CLIENT_ID`, `PRODUCT_SERVICE_CLIENT_ID`, `ACR_LOGIN_SERVER`, and `IMAGE_TAG` using the intended release values.
3. Keep the generated catalog ConfigMap name and volume reference paired. Copy `sql-settings` to a unique `catalog-bootstrap-settings-<release>` ConfigMap and point the copied Job's `envFrom` at it. Rename the copied Job to `catalog-bootstrap-<release>`. This avoids editing the currently Flux-managed settings/Job before release. Both copies remain in namespace `store`; the Job retains `serviceAccountName: sql-operator`, the workload-identity pod label, mount, and user-pool node selector.
4. Apply only those two ConfigMaps, then create the uniquely named Job. Wait for `Complete` and inspect its logs for both `CATALOG_BOOTSTRAP_COMPLETE` and `SQL_BOOTSTRAP_COMPLETE`. Stop the release on any failure. Do not replace a completed Job's pod template in place: Kubernetes makes it immutable. Use a fresh release name for a retry, or delete/recreate only the dedicated one-off Job after checking its state.
5. After successful bootstrap, publish/reconcile the application source and new common Flux `IMAGE_TAG`. The source-managed Job remains named `sql-bootstrap`; its existing `kustomize.toolkit.fluxcd.io/force: enabled` annotation allows Flux to recreate it when its immutable template changes. This second, idempotent bootstrap is safe.
6. Validate catalog count/categories, pickup for added IDs, product-service readiness, and CRUD/restart persistence. Preserve the intentionally zero traffic-generator replica counts. Once Flux has adopted the generated catalog ConfigMap, remove only the dedicated bootstrap Job/settings ConfigMap; do not remove its now-shared catalog ConfigMap.

If service accounts also need rendering, their annotations require `TENANT_ID` and `SQL_OPERATOR_CLIENT_ID` (and the relevant runtime client IDs). On the existing cluster, reuse the existing federated service accounts instead. Never apply the entire rendered application as a bootstrap-only operation.

## Running the app locally

For isolated development, explicitly select `CATALOG_STORE=memory`. This mode loads the canonical catalog and resets edits on every restart. It is opt-in and is not enabled in the AKS deployment.

### Prerequisites

- [Rust](https://www.rust-lang.org/tools/install)

### Running the app

To run the app, clone the repo, open a terminal, and navigate to the `product-service` directory.

Run the API without Azure dependencies using PowerShell:

```powershell
$env:CATALOG_STORE = "memory"
cargo run --locked
```

Or in a POSIX shell:

```bash
CATALOG_STORE=memory cargo run --locked
```

AI proxy endpoints additionally require ai-service. When running it with this directory's Docker Compose file and running Rust on the host, use `AI_SERVICE_URL=http://127.0.0.1:5001`. Optional settings include `AI_REQUEST_TIMEOUT_SECS=300`, `PRODUCT_MAX_SIZE_BYTES=10485760`, and `AI_MAX_PAYLOAD_BYTES=52428800`.

When the app is running, you should see output similar to the following:

```text
    Finished dev [unoptimized + debuginfo] target(s) in 0.16s
     Running `target/debug/product-service`
Listening on http://0.0.0.0:3002
[2023-06-28T02:44:47Z INFO  actix_server::builder] starting 16 workers
[2023-06-28T02:44:47Z INFO  actix_server::server] Actix runtime found; starting in Actix runtime
```

Using the [`test-product-service.http`](./test-product-service.http) file in the root of the repo, you can test the API. However, you will need to use VS Code and have the [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) extension installed.

## Validation

```powershell
cargo test --locked
cargo clippy --all-targets --locked -- -D warnings
cargo fmt -- --check
```

Default tests explicitly use the in-memory fixture store and verify SQL-failure behavior without changing a live database. The ignored SQL CRUD integration test requires federated identity and a separately provisioned database whose name ends in `_test`; run it with `cargo test --locked --test sql -- --ignored`. Never point mutation tests at the business database. The adjacent `inventory-service-tests` console project validates canonical seed input and offers separately gated SQL bootstrap/grant checks against an isolated `_test` database.
