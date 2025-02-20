param containerRegistryName string
param principalIds array

var acrPullRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')

// We need batchSize(1) here because sql role assignments have to be done sequentially
@batchSize(1)
resource acrPullPermissions 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in principalIds: if(principalId != ''){
  scope: containerRegistry // Use when specifying a scope that is different than the deployment scope
  name: guid(subscription().id, resourceGroup().id, principalId, acrPullRole)
  properties: {
    roleDefinitionId: acrPullRole
    principalId: principalId
  }
}]

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2022-02-01-preview' existing = {
  name: containerRegistryName
}
