param sreAgentName string
param appRgName string

// Agent integration is deliberately deferred until an existing agent is supplied.
// Do not enable this module before exporting and validating its live child schemas.
resource agent 'Microsoft.SreAgent/agents@2025-05-01-preview' existing = { name: sreAgentName }
output agentId string = agent.id
output appResourceGroup string = appRgName
