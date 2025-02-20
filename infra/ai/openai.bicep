param name string
param location string
param tags object = {}
param kind string = 'OpenAI'
// Public network access of the Azure OpenAI service
param publicNetworkAccess string = 'Enabled'
// SKU of the Azure OpenAI service
param sku object = {
  name: 'S0'
}

param customDomainName string

param deployments array

resource account 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: name  
  location: location
  tags: tags
  kind: kind
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: customDomainName
    publicNetworkAccess: publicNetworkAccess
  }
  sku: sku
}

// Deployments for the Azure OpenAI service
@batchSize(1)
resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = [for deployment in deployments: {
  parent: account
  name: deployment.name
  sku: {
    name: deployment.sku.name
    capacity: deployment.sku.capacity
  }
  properties: {
    model: deployment.model
  }
}]

output openaiEndpoint string = account.properties.endpoint
output openaiKey string = listKeys(account.id, '2022-10-01').key1
output openaiName string = account.name
output location string = account.location
