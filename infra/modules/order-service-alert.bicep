param location string
param tags object
param workspaceId string

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' existing = {
  name: 'store-incidents'
}

resource authorizationFailure 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: 'order-service-send-authorization-failure'
  location: location
  tags: tags
  kind: 'LogAlert'
  properties: {
    displayName: 'order-service - Service Bus send authorization failure'
    description: 'order-service cannot publish orders because Service Bus denied Send authorization.'
    severity: 2
    enabled: true
    autoMitigate: true
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    scopes: [workspaceId]
    criteria: {
      allOf: [{
        query: '''
          ContainerLogV2
          | where PodNamespace == "store"
          | where PodName startswith "order-service-"
          | where tostring(LogMessage) contains_cs "Service Bus denied Send authorization"
          '''
        timeAggregation: 'Count'
        operator: 'GreaterThan'
        threshold: 0
        failingPeriods: {
          numberOfEvaluationPeriods: 1
          minFailingPeriodsToAlert: 1
        }
      }]
    }
    actions: { actionGroups: [actionGroup.id] }
  }
}

output alertId string = authorizationFailure.id
