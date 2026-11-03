param location string
param tags object
param suffix string
param peSubnetId string
param dnsZoneIds array
param workspaceId string

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'acr${suffix}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false, publicNetworkAccess: 'Enabled' }
}
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: 'cos${suffix}'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    disableLocalAuth: true
    publicNetworkAccess: 'Disabled'
    enableAutomaticFailover: false
    locations: [{ locationName: location, failoverPriority: 0, isZoneRedundant: false }]
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
  }
}
resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'orderdb'
  properties: { resource: { id: 'orderdb' }, options: { throughput: 400 } }
}
resource orders 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'orders'
  properties: {
    resource: {
      id: 'orders'
      partitionKey: { paths: ['/storeId'], kind: 'Hash', version: 2 }
    }
  }
}
resource sb 'Microsoft.ServiceBus/namespaces@2024-01-01' = {
  name: 'sb${suffix}'
  location: location
  tags: tags
  sku: { name: 'Premium', tier: 'Premium', capacity: 1 }
  properties: { disableLocalAuth: true, publicNetworkAccess: 'Disabled', minimumTlsVersion: '1.2' }
}
resource queue 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = {
  parent: sb
  name: 'orders'
  properties: {
    lockDuration: 'PT1M'
    maxDeliveryCount: 100
    defaultMessageTimeToLive: 'P1D'
    enablePartitioning: false
    requiresDuplicateDetection: false
  }
}
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv${suffix}'
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Disabled'
    networkAcls: { bypass: 'None', defaultAction: 'Deny' }
    accessPolicies: []
  }
}
var targets = [
  { name: 'cosmos', id: cosmos.id, groupId: 'Sql' }
  { name: 'servicebus', id: sb.id, groupId: 'namespace' }
  { name: 'keyvault', id: kv.id, groupId: 'vault' }
]
resource endpoints 'Microsoft.Network/privateEndpoints@2024-05-01' = [for target in targets: {
  name: '${target.name}-pe'
  location: location
  tags: tags
  properties: {
    subnet: { id: peSubnetId }
    privateLinkServiceConnections: [{
      name: target.name
      properties: { privateLinkServiceId: target.id, groupIds: [target.groupId] }
    }]
  }
}]
resource groups 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = [for (target, i) in targets: {
  parent: endpoints[i]
  name: 'default'
  properties: { privateDnsZoneConfigs: [{ name: target.name, properties: { privateDnsZoneId: dnsZoneIds[i] } }] }
}]
resource cosmosLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: cosmos
  name: 'logs'
  properties: { workspaceId: workspaceId, logs: [{ categoryGroup: 'allLogs', enabled: true }], metrics: [{ category: 'Requests', enabled: true }] }
}
resource sbLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: sb
  name: 'logs'
  properties: { workspaceId: workspaceId, logs: [{ categoryGroup: 'allLogs', enabled: true }], metrics: [{ category: 'AllMetrics', enabled: true }] }
}
resource kvLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: kv
  name: 'logs'
  properties: { workspaceId: workspaceId, logs: [{ categoryGroup: 'allLogs', enabled: true }], metrics: [{ category: 'AllMetrics', enabled: true }] }
}
output acrId string = acr.id
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output cosmosName string = cosmos.name
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output sbName string = sb.name
output sbId string = sb.id
output sbFqdn string = '${sb.name}.servicebus.windows.net'
