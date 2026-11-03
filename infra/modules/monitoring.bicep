param location string
param tags object

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'store-logs'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    features: { enableLogAccessUsingOnlyResourcePermissions: true }
  }
}
resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'store-insights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    DisableLocalAuth: true
  }
}
resource monitor 'Microsoft.Monitor/accounts@2023-04-03' = {
  name: 'store-prometheus'
  location: location
  tags: tags
  properties: {}
}
output workspaceId string = workspace.id
output monitorWorkspaceId string = monitor.id
output insightsName string = insights.name
output appInsightsConnectionString string = insights.properties.ConnectionString
