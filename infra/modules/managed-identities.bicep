param location string
param tags object

var services = ['store-front', 'store-admin', 'order-service', 'product-service', 'makeline-service', 'virtual-customer', 'virtual-worker', 'checkout-api', 'inventory-service', 'sql-operator']
resource identities 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = [for name in services: {
  name: name
  location: location
  tags: tags
}]
output orderPrincipalId string = identities[2].properties.principalId
output makelinePrincipalId string = identities[4].properties.principalId
output sqlOperatorPrincipalId string = identities[9].properties.principalId
output inventoryPrincipalId string = identities[8].properties.principalId
output clientIds object = {
  STORE_FRONT_CLIENT_ID: identities[0].properties.clientId
  STORE_ADMIN_CLIENT_ID: identities[1].properties.clientId
  ORDER_SERVICE_CLIENT_ID: identities[2].properties.clientId
  PRODUCT_SERVICE_CLIENT_ID: identities[3].properties.clientId
  MAKELINE_SERVICE_CLIENT_ID: identities[4].properties.clientId
  VIRTUAL_CUSTOMER_CLIENT_ID: identities[5].properties.clientId
  VIRTUAL_WORKER_CLIENT_ID: identities[6].properties.clientId
  CHECKOUT_API_CLIENT_ID: identities[7].properties.clientId
  INVENTORY_SERVICE_CLIENT_ID: identities[8].properties.clientId
  SQL_OPERATOR_CLIENT_ID: identities[9].properties.clientId
}
