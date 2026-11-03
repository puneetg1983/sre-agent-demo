param location string
param tags object
param vmSize string
param subnetId string
param workspaceId string
param monitorWorkspaceId string
param deployerObjectId string
param acrId string

resource controlIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'aks-control'
  location: location
  tags: tags
}
resource networkRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, controlIdentity.id, 'network')
  properties: {
    principalId: controlIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4d97b98b-1d4f-4787-a291-c67834d212e7')
  }
}
resource cluster 'Microsoft.ContainerService/managedClusters@2025-02-01' = {
  name: 'store-aks'
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${controlIdentity.id}': {} } }
  dependsOn: [networkRole]
  properties: {
    dnsPrefix: 'store-${uniqueString(resourceGroup().id)}'
    disableLocalAccounts: true
    aadProfile: { managed: true, enableAzureRBAC: true, tenantID: tenant().tenantId }
    oidcIssuerProfile: { enabled: true }
    securityProfile: { workloadIdentity: { enabled: true } }
    azureMonitorProfile: { metrics: { enabled: true } }
    addonProfiles: { omsagent: { enabled: true, config: { logAnalyticsWorkspaceResourceID: workspaceId, useAADAuth: 'true' } } }
    ingressProfile: { webAppRouting: { enabled: true, nginx: { defaultIngressControllerType: 'None' } } }
    networkProfile: {
      networkPlugin: 'azure'
      networkPluginMode: 'overlay'
      networkDataplane: 'cilium'
      networkPolicy: 'cilium'
      podCidr: '10.244.0.0/16'
      serviceCidr: '10.2.0.0/16'
      dnsServiceIP: '10.2.0.10'
      loadBalancerSku: 'standard'
      outboundType: 'loadBalancer'
    }
    agentPoolProfiles: [
      {
        name: 'system'
        count: 2
        vmSize: vmSize
        osType: 'Linux'
        osSKU: 'Ubuntu'
        mode: 'System'
        type: 'VirtualMachineScaleSets'
        vnetSubnetID: subnetId
        maxPods: 60
        tags: tags
        upgradeSettings: { maxSurge: '1' }
      }
      {
        name: 'user'
        count: 2
        vmSize: vmSize
        osType: 'Linux'
        osSKU: 'Ubuntu'
        mode: 'User'
        type: 'VirtualMachineScaleSets'
        vnetSubnetID: subnetId
        maxPods: 60
        tags: tags
        upgradeSettings: { maxSurge: '1' }
      }
    ]
  }
}
resource clusterAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: cluster
  name: guid(cluster.id, deployerObjectId, 'cluster-admin')
  properties: {
    principalId: deployerObjectId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b1ff04bb-8a4e-4dc4-8eb5-8693973ce19b')
  }
}
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = { name: last(split(acrId, '/')) }
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acrId, cluster.id, 'pull')
  properties: {
    principalId: cluster.properties.identityProfile.kubeletidentity.objectId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}
resource logs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: cluster
  name: 'logs'
  properties: { workspaceId: workspaceId, logs: [{ categoryGroup: 'allLogs', enabled: true }] }
}
resource dce 'Microsoft.Insights/dataCollectionEndpoints@2023-03-11' = {
  name: 'store-prometheus-dce'
  location: location
  tags: tags
  kind: 'Linux'
  properties: { networkAcls: { publicNetworkAccess: 'Enabled' } }
}
resource dcr 'Microsoft.Insights/dataCollectionRules@2023-03-11' = {
  name: 'store-prometheus-dcr'
  location: location
  tags: tags
  kind: 'Linux'
  properties: {
    dataCollectionEndpointId: dce.id
    dataSources: { prometheusForwarder: [{ name: 'prometheus', streams: ['Microsoft-PrometheusMetrics'] }] }
    destinations: { monitoringAccounts: [{ name: 'prometheus', accountResourceId: monitorWorkspaceId }] }
    dataFlows: [{ streams: ['Microsoft-PrometheusMetrics'], destinations: ['prometheus'] }]
  }
}
resource association 'Microsoft.Insights/dataCollectionRuleAssociations@2023-03-11' = {
  scope: cluster
  name: 'prometheus'
  properties: { dataCollectionRuleId: dcr.id }
}
resource containerLogs 'Microsoft.Insights/dataCollectionRules@2023-03-11' = {
  name: 'store-container-insights-dcr'
  location: location
  tags: tags
  kind: 'Linux'
  properties: {
    dataSources: {
      extensions: [{
        name: 'ContainerInsightsExtension'
        extensionName: 'ContainerInsights'
        streams: ['Microsoft-ContainerInsights-Group-Default']
        extensionSettings: {
          dataCollectionSettings: {
            interval: '1m'
            namespaceFilteringMode: 'Off'
            namespaces: []
            enableContainerLogV2: true
          }
        }
      }]
    }
    destinations: { logAnalytics: [{ name: 'logs', workspaceResourceId: workspaceId }] }
    dataFlows: [{ streams: ['Microsoft-ContainerInsights-Group-Default'], destinations: ['logs'] }]
  }
}
resource containerLogsAssociation 'Microsoft.Insights/dataCollectionRuleAssociations@2023-03-11' = {
  scope: cluster
  name: 'ContainerInsightsExtension'
  properties: { dataCollectionRuleId: containerLogs.id }
}
output name string = cluster.name
output oidcIssuer string = cluster.properties.oidcIssuerProfile.issuerURL
