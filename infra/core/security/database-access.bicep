metadata description = 'Assigns access to cosmosdb account.'
param databaseAccountName string
param principalIds array

resource roleDefinition 'Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions@2022-08-15' = {
  parent: database
  name: guid(database.id, databaseAccountName, 'sql-role')
  properties: {
    assignableScopes: [
      database.id
    ]
    permissions: [
      {
        dataActions: [
          'Microsoft.DocumentDB/databaseAccounts/readMetadata'
          'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*'
          'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*'
          'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/write'
        ]
        notDataActions: []
      }
    ]
    roleName: 'Data Reader Writer'
    type: 'CustomRole'
  }
}

// We need batchSize(1) here because sql role assignments have to be done sequentially
@batchSize(1)
resource role 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = [for principalId in principalIds: if(principalId != '') {
  parent: database
  name: guid(roleDefinition.id, principalId, database.id)
  properties: {
    principalId: principalId
    roleDefinitionId: roleDefinition.id
    scope: database.id
  }
}]

resource database 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: databaseAccountName
}
