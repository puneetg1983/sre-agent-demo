param location string
param tags object
param reuseExistingNsgs bool = false

var subnetNames = ['hub', 'aks', 'appgw', 'pe']
resource nsgs 'Microsoft.Network/networkSecurityGroups@2024-05-01' existing = [for name in subnetNames: {
  name: '${name}-nsg'
}]
resource newNsgs 'Microsoft.Network/networkSecurityGroups@2024-05-01' = [for name in subnetNames: if (!reuseExistingNsgs) {
  name: '${name}-nsg'
  location: location
  tags: tags
  properties: {}
}]
var appgwSecurityRules = [
  {
    name: 'GatewayManager'
    properties: {
      priority: 100
      direction: 'Inbound'
      access: 'Allow'
      protocol: 'Tcp'
      sourcePortRange: '*'
      destinationPortRange: '65200-65535'
      sourceAddressPrefix: 'GatewayManager'
      destinationAddressPrefix: '*'
    }
  }
  {
    name: 'PublicHttp'
    properties: {
      priority: 110
      direction: 'Inbound'
      access: 'Allow'
      protocol: 'Tcp'
      sourcePortRange: '*'
      destinationPortRanges: ['80', '8081']
      sourceAddressPrefix: 'Internet'
      destinationAddressPrefix: '*'
    }
  }
]
// Child rules preserve security rules injected and owned by subscription policy.
resource appgwRules 'Microsoft.Network/networkSecurityGroups/securityRules@2024-05-01' = [for rule in appgwSecurityRules: {
  parent: nsgs[2]
  name: rule.name
  properties: rule.properties
  dependsOn: [newNsgs]
}]
resource hub 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: 'hub-vnet'
  location: location
  tags: tags
  dependsOn: [newNsgs]
  properties: {
    addressSpace: { addressPrefixes: ['10.0.0.0/16'] }
    subnets: [{
      name: 'hub'
      properties: {
        addressPrefix: '10.0.0.0/24'
        networkSecurityGroup: { id: nsgs[0].id }
      }
    }]
  }
}
resource spoke 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: 'spoke-vnet'
  location: location
  tags: tags
  dependsOn: [newNsgs, appgwRules]
  properties: {
    addressSpace: { addressPrefixes: ['10.1.0.0/16'] }
    subnets: [
      {
        name: 'aks'
        properties: {
          addressPrefix: '10.1.0.0/22'
          networkSecurityGroup: { id: nsgs[1].id }
        }
      }
      {
        name: 'appgw'
        properties: {
          addressPrefix: '10.1.4.0/24'
          networkSecurityGroup: { id: nsgs[2].id }
        }
      }
      {
        name: 'pe'
        properties: {
          addressPrefix: '10.1.5.0/24'
          networkSecurityGroup: { id: nsgs[3].id }
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}
resource hubToSpoke 'Microsoft.Network/virtualNetworks/virtualNetworkPeerings@2024-05-01' = {
  parent: hub
  name: 'to-spoke'
  properties: { remoteVirtualNetwork: { id: spoke.id }, allowVirtualNetworkAccess: true, allowForwardedTraffic: true }
}
resource spokeToHub 'Microsoft.Network/virtualNetworks/virtualNetworkPeerings@2024-05-01' = {
  parent: spoke
  name: 'to-hub'
  properties: { remoteVirtualNetwork: { id: hub.id }, allowVirtualNetworkAccess: true, allowForwardedTraffic: true }
}
var zones = ['privatelink.documents.azure.com', 'privatelink.servicebus.windows.net', 'privatelink.vaultcore.azure.net', 'privatelink.database.windows.net']
resource dns 'Microsoft.Network/privateDnsZones@2024-06-01' = [for zone in zones: {
  name: zone
  location: 'global'
  tags: tags
}]
resource hubLinks 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [for (zone, i) in zones: {
  parent: dns[i]
  name: 'hub-link'
  location: 'global'
  tags: tags
  properties: { virtualNetwork: { id: hub.id }, registrationEnabled: false }
}]
resource spokeLinks 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [for (zone, i) in zones: {
  parent: dns[i]
  name: 'spoke-link'
  location: 'global'
  tags: tags
  properties: { virtualNetwork: { id: spoke.id }, registrationEnabled: false }
}]
output aksSubnetId string = '${spoke.id}/subnets/aks'
output appgwSubnetId string = '${spoke.id}/subnets/appgw'
output peSubnetId string = '${spoke.id}/subnets/pe'
output ingressIp string = '10.1.0.100'
output spokeVnetId string = spoke.id
output dnsZoneIds array = [for (zone, i) in zones: dns[i].id]
