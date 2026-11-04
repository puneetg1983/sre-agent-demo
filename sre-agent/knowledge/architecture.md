# Sports Store: resource knowledge

Nonproduction Azure demo. Resource details verified on 2026-11-03.

## Azure resources

- Subscription: `6b6db65f-680e-4650-b97d-e82ed6a0f583`
- Resource group: `rg-sreagent-demo-r13-app`
- Region: `polandcentral`

| Resource | Name / details |
| --- | --- |
| AKS | `store-aks`; application namespace: `store` |
| AKS node resource group | `MC_rg-sreagent-demo-r13-app_store-aks_polandcentral` |
| Application Gateway | `store-appgw`; public IP: `appgw-pip`; WAF: `store-waf` |
| Container registry | `acrqavgkg7xkz7cq.azurecr.io` |
| Service Bus | `sbqavgkg7xkz7cq`; queue: `orders` |
| Cosmos DB | `cosqavgkg7xkz7cq`; database/container: `orderdb/orders`; partition: `/storeId`, value `contoso` |
| Azure SQL | `sqlqavgkg7xkz7cq.database.windows.net`; database `sportsstore`; Basic 5 DTUs / 2 GB; pickup inventory |
| Log Analytics | `store-logs`: container logs, pod inventory, diagnostics, Activity Logs |
| Application Insights | `store-insights`: availability checks and pickup API/SQL dependency traces, not full order-pipeline tracing |
| Managed Prometheus | `store-prometheus` |
| Virtual networks | Peered `hub-vnet` and `spoke-vnet`; app resources are in the spoke |

## Application components

- `store-front` and `store-admin`: customer and admin websites.
- `product-service`: in-memory sports catalog; edits reset on restart.
- `checkout-api`: checks active pricing configuration and forwards orders.
- `order-service`: publishes orders to Service Bus.
- `makeline-service`: consumes queued orders and persists/manages them in Cosmos.
- `virtual-customer` and `virtual-worker`: optional synthetic order actors, currently scaled to zero. Orders are placed and completed manually.
- `inventory-service`: SQL-backed pickup availability; `pickup-monitor` cycles through the catalog independently of checkout.

Flow: **Browser -> Gateway -> private ingress -> storefront -> checkout -> order-service -> Service Bus -> makeline -> Cosmos.**
Pickup: **Product detail -> /api/pickup/{id} -> inventory-service -> SQL dbo.GetPickupAvailability / PickupInventory.**

HTTP 201 means queued, not fulfilled. Orders retain their original ID; Cosmos
status `0` is pending, `1` is manually completed and `2` is automatically
completed. The Admin Portal retains the latest 50 orders across all statuses,
ordered by their last database update, and refreshes every five seconds.
Read failures are displayed explicitly, with previously loaded history marked
stale rather than presented as live. The shopping cart lives in browser localStorage.

## Access and dependencies

- Customer: http://storeqavgkg7xkz7cq.polandcentral.cloudapp.azure.com/
- Admin: http://storeqavgkg7xkz7cq.polandcentral.cloudapp.azure.com:8081/
- Gateway forwards to private ingress `10.1.0.100`. The admin-prefixed hostname
  is an internal routing name; use the public URL above.
- Cosmos, Service Bus, SQL, and Key Vault use private endpoints and private DNS.
  Their public access is disabled. Key Vault is intentionally empty.
- Pods use Entra Workload Identity. Order-service has Service Bus Sender;
  makeline has Receiver and Cosmos data-contributor access. No shared keys.
- Inventory has SQL procedure EXECUTE only. Separate `sql-operator` runs schema
  bootstrap; SQL is Entra-only.
- `flux-system` runs GitOps; `app-routing-system` runs ingress;
  `gatekeeper-system` belongs to the Azure Policy add-on.

## Source and monitoring

Repository: https://github.com/puneetg1983/sre-agent-demo

Flux syncs `main`, folder `app`, approximately every minute.
Images are built through Azure ACR Tasks; source pushes alone do not release images.

Alerts: `availability-failures` (external availability) and `appgw-5xx`
(customer-facing HTTP failures). These are service-health signals, not a
contractual SLA or percentage error-budget calculation.
SQL logs include connection/query duration and session/trace IDs; native Azure SQL
diagnostics and Query Store feed the workspace. Ready pods and passing frontend health checks do not
guarantee working checkout or fulfillment.
