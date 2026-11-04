targetScope = 'subscription'

param rgName string = 'rg-sreagent-demo'
param location string = 'canadacentral'
param vmSize string = 'Standard_D4s_v5'
param githubRepoUrl string = 'https://github.com/puneetg1983/sre-agent-demo'
param githubBranch string = 'main'
param imageTag string = 'demo-v1'
param sreAgentName string = ''
param sreAgentRg string = 'rg-sreagent-demo-sreagent'
param enableSreAgent bool = false
param reuseExistingNsgs bool = false
param reuseExistingActionGroup bool = false

var tags = { demo: 'sreagent', rgName: rgName }
var suffix = uniqueString(subscription().subscriptionId, rgName)
resource appRg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: '${rgName}-app'
  location: location
  tags: tags
}
module managedIdentities 'modules/managed-identities.bicep' = {
  name: '${rgName}-managed-identities'
  scope: appRg
  params: { location: location, tags: tags }
}
module network 'modules/network.bicep' = {
  name: '${rgName}-network'
  scope: appRg
  params: { location: location, tags: tags, reuseExistingNsgs: reuseExistingNsgs }
}
module monitoring 'modules/monitoring.bicep' = {
  name: '${rgName}-monitoring'
  scope: appRg
  params: { location: location, tags: tags }
}
module data 'modules/data.bicep' = {
  name: '${rgName}-data'
  scope: appRg
  params: {
    location: location
    tags: tags
    suffix: suffix
    peSubnetId: network.outputs.peSubnetId
    dnsZoneIds: network.outputs.dnsZoneIds
    workspaceId: monitoring.outputs.workspaceId
  }
}
module sql 'modules/sql.bicep' = {
  name: '${rgName}-sql'
  scope: appRg
  params: {
    location: location
    tags: tags
    suffix: suffix
    peSubnetId: network.outputs.peSubnetId
    dnsZoneId: network.outputs.dnsZoneIds[3]
    workspaceId: monitoring.outputs.workspaceId
    operatorPrincipalId: managedIdentities.outputs.sqlOperatorPrincipalId
  }
}
module aks 'modules/aks.bicep' = {
  name: '${rgName}-aks'
  scope: appRg
  params: {
    location: location
    tags: tags
    vmSize: vmSize
    subnetId: network.outputs.aksSubnetId
    workspaceId: monitoring.outputs.workspaceId
    monitorWorkspaceId: monitoring.outputs.monitorWorkspaceId
    deployerObjectId: deployer().objectId
    acrId: data.outputs.acrId
  }
}
module identity 'modules/identity.bicep' = {
  name: '${rgName}-identity'
  scope: appRg
  params: {
    issuer: aks.outputs.oidcIssuer
    cosmosName: data.outputs.cosmosName
    sbName: data.outputs.sbName
    orderPrincipalId: managedIdentities.outputs.orderPrincipalId
    makelinePrincipalId: managedIdentities.outputs.makelinePrincipalId
    clientIds: managedIdentities.outputs.clientIds
    insightsName: monitoring.outputs.insightsName
    inventoryPrincipalId: managedIdentities.outputs.inventoryPrincipalId
  }
}
module appgw 'modules/appgw.bicep' = {
  name: '${rgName}-appgw'
  scope: appRg
  params: {
    location: location
    tags: tags
    suffix: suffix
    subnetId: network.outputs.appgwSubnetId
    ingressIp: network.outputs.ingressIp
    workspaceId: monitoring.outputs.workspaceId
  }
}
module gitops 'modules/gitops.bicep' = {
  name: '${rgName}-gitops'
  scope: appRg
  params: {
    aksName: aks.outputs.name
    githubRepoUrl: githubRepoUrl
    githubBranch: githubBranch
    substitutes: union(identity.outputs.resolvedClientIds, {
      TENANT_ID: tenant().tenantId
      COSMOS_ENDPOINT: data.outputs.cosmosEndpoint
      SB_FQDN: data.outputs.sbFqdn
      ACR_LOGIN_SERVER: data.outputs.acrLoginServer
      INGRESS_IP: network.outputs.ingressIp
      DEMO_HOST: appgw.outputs.fqdn
      APPINSIGHTS_CONNECTION_STRING: monitoring.outputs.appInsightsConnectionString
      IMAGE_TAG: imageTag
      SQL_SERVER: sql.outputs.fqdn
      SQL_DATABASE: sql.outputs.databaseName
    })
  }
}
module alerts 'modules/alerts.bicep' = {
  name: '${rgName}-alerts'
  scope: appRg
  params: {
    location: location
    tags: tags
    appgwId: appgw.outputs.id
    insightsName: monitoring.outputs.insightsName
    appUrl: appgw.outputs.url
    workspaceId: monitoring.outputs.workspaceId
    reuseExistingActionGroup: reuseExistingActionGroup
  }
}
resource activityLog 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: '${rgName}-activity'
  properties: {
    workspaceId: monitoring.outputs.workspaceId
    logs: [
      { category: 'Administrative', enabled: true }
      { category: 'Policy', enabled: true }
      { category: 'Security', enabled: true }
      { category: 'Alert', enabled: true }
      { category: 'ServiceHealth', enabled: true }
      { category: 'ResourceHealth', enabled: true }
    ]
  }
}
module sreagent 'modules/sreagent-config.bicep' = if (enableSreAgent) {
  name: '${rgName}-sreagent'
  scope: resourceGroup(sreAgentRg)
  params: { sreAgentName: sreAgentName, appRgName: appRg.name }
}

output appResourceGroup string = appRg.name
output appUrl string = appgw.outputs.url
output adminUrl string = '${appgw.outputs.url}:8081'
output aksName string = aks.outputs.name
output acrName string = data.outputs.acrName
output tenantId string = tenant().tenantId
output subscriptionId string = subscription().subscriptionId
output serviceBusName string = data.outputs.sbName
output cosmosName string = data.outputs.cosmosName
output spokeVnetId string = network.outputs.spokeVnetId
output workspaceId string = monitoring.outputs.workspaceId
output sreAgentEnabled bool = enableSreAgent
output sqlServerName string = sql.outputs.name
output sqlServerFqdn string = sql.outputs.fqdn
output sqlDatabaseName string = sql.outputs.databaseName
output sqlDatabaseId string = sql.outputs.databaseId
