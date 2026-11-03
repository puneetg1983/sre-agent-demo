param issuer string
param cosmosName string
param sbName string
param orderPrincipalId string
param makelinePrincipalId string
param clientIds object
param insightsName string
param inventoryPrincipalId string

var services = ['store-front', 'store-admin', 'order-service', 'product-service', 'makeline-service', 'virtual-customer', 'virtual-worker', 'checkout-api', 'inventory-service', 'sql-operator']
resource identities 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = [for name in services: {
  name: name
}]
resource federations 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = [for (name, i) in services: {
  parent: identities[i]
  name: 'aks'
  properties: { issuer: issuer, subject: 'system:serviceaccount:store:${name}', audiences: ['api://AzureADTokenExchange'] }
}]
resource sb 'Microsoft.ServiceBus/namespaces@2024-01-01' existing = { name: sbName }
resource sender 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: sb
  name: guid(sb.id, identities[2].id, 'sender')
  properties: {
    principalId: orderPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '69a216fc-b8fb-44d8-bc22-1f3c2cd27a39')
  }
}
resource receiver 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: sb
  name: guid(sb.id, identities[4].id, 'receiver')
  properties: {
    principalId: makelinePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0')
  }
}
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = { name: cosmosName }
resource contributor 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmos
  name: guid(cosmos.id, identities[4].id, 'data-contributor')
  properties: {
    principalId: makelinePrincipalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    scope: cosmos.id
  }
}
output resolvedClientIds object = clientIds

resource insights 'Microsoft.Insights/components@2020-02-02' existing = { name: insightsName }
resource inventoryTelemetry 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: insights
  name: guid(insights.id, inventoryPrincipalId, 'telemetry-publisher')
  properties: {
    principalId: inventoryPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')
  }
}
