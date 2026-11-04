param location string
param tags object
param appgwId string
param insightsName string
param appUrl string
param workspaceId string
param reuseExistingActionGroup bool = false

resource ag 'Microsoft.Insights/actionGroups@2023-01-01' existing = {
  name: 'store-incidents'
}
// Portal-managed receivers must never be serialized into public deployment parameters or overwritten.
resource newAg 'Microsoft.Insights/actionGroups@2023-01-01' = if (!reuseExistingActionGroup) {
  name: 'store-incidents'
  location: 'global'
  tags: tags
  properties: { groupShortName: 'StoreDemo', enabled: true }
}
module orderServiceAuthorization 'order-service-alert.bicep' = {
  name: 'order-service-authorization-alert'
  dependsOn: [newAg]
  params: {
    location: location
    tags: tags
    workspaceId: workspaceId
  }
}
var definitions = [
  { name: 'appgw-5xx', resourceId: appgwId, ns: 'Microsoft.Network/applicationGateways', metric: 'ResponseStatus', aggregation: 'Total', threshold: 2, dimension: [{ name: 'HttpStatusGroup', operator: 'Include', values: ['5xx'] }] }
]
resource metrics 'Microsoft.Insights/metricAlerts@2018-03-01' = [for def in definitions: {
  name: def.name
  location: 'global'
  tags: tags
  dependsOn: [newAg]
  properties: {
    description: 'Customer-facing HTTP availability: more than two gateway 5xx responses in one minute. Investigate the affected requests and dependencies.'
    severity: 2
    enabled: true
    autoMitigate: true
    scopes: [def.resourceId]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT1M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [{
        name: def.name
        criterionType: 'StaticThresholdCriterion'
        metricNamespace: def.ns
        metricName: def.metric
        operator: 'GreaterThan'
        threshold: def.threshold
        timeAggregation: def.aggregation
        dimensions: def.dimension
      }]
    }
    actions: [{ actionGroupId: ag.id }]
  }
}]
resource insights 'Microsoft.Insights/components@2020-02-02' existing = { name: insightsName }
resource webtest 'Microsoft.Insights/webtests@2022-06-15' = {
  name: 'store-availability'
  location: location
  tags: union(tags, { 'hidden-link:${insights.id}': 'Resource' })
  kind: 'standard'
  properties: {
    SyntheticMonitorId: 'store-availability'
    Name: 'Contoso Sports Store'
    Enabled: true
    Frequency: 300
    Timeout: 30
    Kind: 'standard'
    RetryEnabled: false
    Locations: [{ Id: 'us-va-ash-azr' }, { Id: 'emea-nl-ams-azr' }, { Id: 'us-fl-mia-edge' }]
    Request: { RequestUrl: '${appUrl}/health', HttpVerb: 'GET', ParseDependentRequests: false }
    ValidationRules: { ExpectedHttpStatusCode: 200, SSLCheck: false }
  }
}
resource availability 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'availability-failures'
  location: 'global'
  tags: tags
  dependsOn: [newAg]
  properties: {
    description: 'External service availability: the public health endpoint fails from at least two probe locations.'
    severity: 3
    enabled: true
    autoMitigate: true
    scopes: [webtest.id, insights.id]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.WebtestLocationAvailabilityCriteria'
      webTestId: webtest.id
      componentId: insights.id
      failedLocationCount: 2
    }
    actions: [{ actionGroupId: ag.id }]
  }
}
