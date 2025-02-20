param openaiName string
param containerRegistryName string
param principalIds array

module openaiAccess './openai-access.bicep' = {
  name: '${deployment().name}-openai-access'
  params: {
    openAiName: openaiName
    principalIds: principalIds
  }
}

module containerRegistryAccess './registry-access.bicep' = {
  name: '${deployment().name}-registry-access'
  params: {
    containerRegistryName: containerRegistryName
    principalIds: principalIds
  }
}
