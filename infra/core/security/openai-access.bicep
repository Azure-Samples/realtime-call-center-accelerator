param openAiName string
param principalIds array

// https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles
// Cognitive Services OpenAI User
var openAiUserRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')

// We need batchSize(1) here because sql role assignments have to be done sequentially
@batchSize(1)
resource openaiuser 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in principalIds: if(principalId != ''){
  scope: openai // Use when specifying a scope that is different than the deployment scope
  name: guid(subscription().id, resourceGroup().id, principalId, openAiUserRole)
  properties: {
    roleDefinitionId: openAiUserRole
    principalId: principalId
  }
}]

resource openai 'Microsoft.CognitiveServices/accounts@2022-10-01' existing = {
  name: openAiName
}
