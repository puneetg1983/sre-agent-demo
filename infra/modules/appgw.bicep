param location string
param tags object
param suffix string
param subnetId string
param ingressIp string
param workspaceId string

resource pip 'Microsoft.Network/publicIPAddresses@2024-05-01' = {
  name: 'appgw-pip'
  location: location
  tags: tags
  sku: { name: 'Standard' }
  properties: { publicIPAllocationMethod: 'Static', dnsSettings: { domainNameLabel: 'store${suffix}' } }
}
resource waf 'Microsoft.Network/ApplicationGatewayWebApplicationFirewallPolicies@2024-05-01' = {
  name: 'store-waf'
  location: location
  tags: tags
  properties: {
    policySettings: { state: 'Enabled', mode: 'Prevention', requestBodyCheck: true }
    managedRules: { managedRuleSets: [{ ruleSetType: 'OWASP', ruleSetVersion: '3.2' }] }
  }
}
var gwId = resourceId('Microsoft.Network/applicationGateways', 'store-appgw')
resource gw 'Microsoft.Network/applicationGateways@2024-05-01' = {
  name: 'store-appgw'
  location: location
  tags: tags
  properties: {
    sku: { name: 'WAF_v2', tier: 'WAF_v2' }
    autoscaleConfiguration: { minCapacity: 1, maxCapacity: 2 }
    firewallPolicy: { id: waf.id }
    sslPolicy: { policyType: 'Predefined', policyName: 'AppGwSslPolicy20220101S' }
    gatewayIPConfigurations: [{ name: 'gateway', properties: { subnet: { id: subnetId } } }]
    frontendIPConfigurations: [{ name: 'public', properties: { publicIPAddress: { id: pip.id } } }]
    frontendPorts: [{ name: 'http', properties: { port: 80 } }, { name: 'admin', properties: { port: 8081 } }]
    backendAddressPools: [{ name: 'ingress', properties: { backendAddresses: [{ ipAddress: ingressIp }] } }]
    probes: [{
      name: 'health'
      properties: {
        protocol: 'Http'
        host: pip.properties.dnsSettings.fqdn
        path: '/health'
        interval: 30
        timeout: 20
        unhealthyThreshold: 3
        match: { statusCodes: ['200-399'] }
      }
    }]
    backendHttpSettingsCollection: [
      {
        name: 'http'
        properties: {
          port: 80
          protocol: 'Http'
          cookieBasedAffinity: 'Disabled'
          requestTimeout: 30
          probe: { id: '${gwId}/probes/health' }
        }
      }
      {
        name: 'admin'
        properties: {
          port: 80
          protocol: 'Http'
          hostName: 'admin.${pip.properties.dnsSettings.fqdn}'
          cookieBasedAffinity: 'Disabled'
          requestTimeout: 30
          probe: { id: '${gwId}/probes/health' }
        }
      }
    ]
    httpListeners: [
      {
        name: 'public-http'
        properties: {
          frontendIPConfiguration: { id: '${gwId}/frontendIPConfigurations/public' }
          frontendPort: { id: '${gwId}/frontendPorts/http' }
          protocol: 'Http'
        }
      }
      {
        name: 'admin'
        properties: {
          frontendIPConfiguration: { id: '${gwId}/frontendIPConfigurations/public' }
          frontendPort: { id: '${gwId}/frontendPorts/admin' }
          protocol: 'Http'
        }
      }
    ]
    requestRoutingRules: [
      {
        name: 'store'
        properties: {
          priority: 100
          ruleType: 'Basic'
          httpListener: { id: '${gwId}/httpListeners/public-http' }
          backendAddressPool: { id: '${gwId}/backendAddressPools/ingress' }
          backendHttpSettings: { id: '${gwId}/backendHttpSettingsCollection/http' }
        }
      }
      {
        name: 'admin'
        properties: {
          priority: 200
          ruleType: 'Basic'
          httpListener: { id: '${gwId}/httpListeners/admin' }
          backendAddressPool: { id: '${gwId}/backendAddressPools/ingress' }
          backendHttpSettings: { id: '${gwId}/backendHttpSettingsCollection/admin' }
        }
      }
    ]
  }
}
resource logs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: gw
  name: 'logs'
  properties: { workspaceId: workspaceId, logs: [{ categoryGroup: 'allLogs', enabled: true }], metrics: [{ category: 'AllMetrics', enabled: true }] }
}
output id string = gw.id
output fqdn string = pip.properties.dnsSettings.fqdn
output url string = 'http://${pip.properties.dnsSettings.fqdn}'
