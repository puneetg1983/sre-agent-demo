# Contoso Sports Store

An Azure-hosted sports store with customer and admin websites, SQL-backed pickup
availability, and asynchronous order fulfillment.

## Architecture

Application Gateway WAF forwards customer and admin requests to private AKS
ingress. The storefront uses the product catalog, pickup API, and checkout API.
Orders flow through order-service, Service Bus, makeline-service, and Cosmos DB.
Pickup availability is stored separately in Azure SQL Database Basic (5 DTUs,
2 GB). Each feature uses Entra Workload Identity; application secrets and shared
data-service keys are not required.

Cosmos DB, Service Bus, SQL, and Key Vault use private endpoints and private DNS,
with public data access disabled. Application Insights records pickup requests
and SQL dependencies; Log Analytics collects container logs and diagnostics.

The [resource knowledge file](sre-agent/knowledge/architecture.md) lists the
deployed resources, service dependencies, and endpoints. Agent integration is
external to the application deployment.

## Existing environment

Resource group: `rg-sreagent-demo-r13-app`, Poland Central.

- [Customer store](http://storeqavgkg7xkz7cq.polandcentral.cloudapp.azure.com/)
- [Admin](http://storeqavgkg7xkz7cq.polandcentral.cloudapp.azure.com:8081/)

This is an isolated HTTP demonstration environment. Use synthetic data only.

## Manual orders and history

Background customer and fulfillment-worker deployments are scaled to zero.
Place orders through the storefront, then open the Admin Portal to complete
pending orders manually. The queue consumer still persists accepted orders
to Cosmos DB; the independent SQL pickup monitor remains enabled.

The Admin Orders page uses a light-only theme and shows the latest 15 orders
across all statuses, ordered by their last database update, and refreshes every
five seconds. Completed
orders remain visible. Manual completion is reflected only after the backend
accepts it. Database failures display an error, retaining clearly marked stale
history if any was previously loaded; they are not presented as an empty list.
The administrative history endpoint is `/order/recent`; `/order/fetch`
continues to return pending work for integrations.

## Deployment

Prerequisites: Python 3.10+, Azure CLI with Bicep, Git, GitHub CLI signed in as
`puneetg1983`, and kubectl. Missing kubelogin is installed into the ignored
`.tools` directory. Fixed deployment inputs are in `infra/main.bicepparam`.
Commit and push application changes to `main` before deployment.

```powershell
python scripts\deploy.py rg-sreagent-demo-r13
python scripts\health.py rg-sreagent-demo-r13
```

Health checks include stock lookups and one synthetic order persisted to Cosmos.
The deployment uses native ACR Tasks builds pinned to the source commit; image
tags identify the `app/src` tree. Flux reconciles `main/app` approximately every
minute. Source pushes alone do not release new images. GitHub Actions provides
manually triggered build validation, not Azure publishing.

Use the deployment script for existing environments: it preserves policy-owned
NSG configuration and the existing action group's notification receivers.
Do not invoke raw ARM with fresh-install defaults against configured resources.

## Monitoring

Three alert rules use the existing `store-incidents` action group:

| Alert | Signal |
| --- | --- |
| `availability-failures` | Public health endpoint fails from at least two external probe locations |
| `appgw-5xx` | More than two gateway HTTP 5xx responses in one minute |
| `order-service-send-authorization-failure` | At least one `order-service` log reporting Service Bus denied Send authorization in five minutes; evaluated every minute, severity 2 |

These are service-health signals, not contractual SLA or percentage error-budget
calculations. Infrastructure metrics, queue telemetry, native Azure SQL metrics/diagnostics,
and request/dependency traces remain available for investigation. The dedicated
order-service alert detects authorization failures rather than unrelated
pricing, Cosmos connectivity, or general queue errors.

## Source and licenses

The store adapts [Azure-Samples/aks-store-demo](https://github.com/Azure-Samples/aks-store-demo).
The upstream MIT license is retained in `app/src/UPSTREAM-LICENSE.md`.
Locally served product photographs retain their authors, source URLs, licenses,
and modification notices in each website's `/image-credits.txt`.

The environment incurs ongoing charges for AKS, Application Gateway, private
data services, private endpoints, and monitoring. To remove an environment:

```powershell
python scripts\teardown.py rg-sreagent-demo-r13
```
