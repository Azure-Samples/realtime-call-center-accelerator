param(
    [string] [Parameter(Mandatory = $true)] $index,
    [string] [Parameter(Mandatory = $true)] $indexer,
    [string] [Parameter(Mandatory = $true)] $datasource,
    [string] [Parameter(Mandatory = $true)] $skillset,
    [string] [Parameter(Mandatory = $true)] $searchServiceName,
    [string] [Parameter(Mandatory = $true)] $dataSourceContainerName,
    [string] [Parameter(Mandatory = $true)] $dataSourceConnectionString,
    [string] [Parameter(Mandatory = $true)] $indexName,
    [string] [Parameter(Mandatory = $true)] $AzureOpenAIResourceUri,
    [string] [Parameter(Mandatory = $true)] $indexerEmbeddingModelId,
    [string] [Parameter(Mandatory = $true)] $embeddingModelName,
    [string] [Parameter(Mandatory = $true)] $searchEmbeddingModelId
)

$DeploymentScriptOutputs = @{}
$ErrorActionPreference = 'Stop'

$placeholderMap = @{
    "{DATA_SOURCE_CONNECTION_STRING}" = $dataSourceConnectionString
    "{DATA_SOURCE_CONTAINER_NAME}"    = $dataSourceContainerName
    "{INDEX_NAME}"                    = $indexName
    "{AZURE_OPENAI_RESOURCE_URI}"     = $AzureOpenAIResourceUri
    "{INDEXER_EMBEDDING_MODEL_ID}"    = $indexerEmbeddingModelId
    "{EMBEDDING_MODEL_NAME}"          = $embeddingModelName
    "{SEARCH_INSTANCE_NAME}"          = $searchServiceName
    "{SEARCH_EMBEDDING_MODEL_ID}"     = $searchEmbeddingModelId
}

# Function to replace tokens and create the request body for the API call.
function Create-RequestBody {
    param (
        [Parameter(Mandatory = $true)]
        [string]$inputString,
        [Parameter(Mandatory = $true)]
        [hashtable]$placeholderMap
    )

    $inputBytes = [System.Convert]::FromBase64String($inputString)
    $decodedString = [System.Text.Encoding]::UTF8.GetString($inputBytes)

    foreach ($key in $placeholderMap.Keys) {
        $decodedString = $decodedString -replace $key, $placeholderMap[$key]
    }

    return $decodedString
}

# Process inputs.
$indexBody = Create-RequestBody -inputString $index -placeholderMap $placeholderMap
$indexerBody = Create-RequestBody -inputString $indexer -placeholderMap $placeholderMap
$datasourceBody = Create-RequestBody -inputString $datasource -placeholderMap $placeholderMap
$skillsetBody = Create-RequestBody -inputString $skillset -placeholderMap $placeholderMap

# Call APIs to create the index.
$apiversion = '2024-07-01'
$secureToken = (Get-AzAccessToken -AsSecureString -ResourceUrl https://search.azure.com).Token
$ssPtr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
try {

    $token = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($ssPtr)
    $headers = @{ 'Authorization' = "Bearer $token"; 'Content-Type' = 'application/json'; }
    $uri = "https://$searchServiceName.search.windows.net"

    $dataSourceResponse = Invoke-WebRequest `
        -Method 'PUT' `
        -Uri "$uri/datasources('$($indexName)-datasource')?api-version=$apiversion" `
        -Headers $headers `
        -Body $datasourceBody

    $indexResponse = Invoke-WebRequest `
        -Method 'PUT' `
        -Uri "$uri/indexes('$($indexName)')?api-version=$apiversion" `
        -Headers $headers `
        -Body $indexBody


    $skillsetResponse = Invoke-WebRequest `
        -Method 'PUT' `
        -Uri "$uri/skillsets('$($indexName)-skillset')?api-version=$apiversion" `
        -Headers $headers `
        -Body $skillsetBody

    $indexerResponse = Invoke-WebRequest `
        -Method 'PUT' `
        -Uri "$uri/indexers('$($indexName)-indexer')?api-version=$apiversion" `
        -Headers $headers `
        -Body $indexerBody


    Write-Output "Data source response: $($dataSourceResponse.StatusCode)"
    Write-Output "Index response: $($indexResponse.StatusCode)"
    Write-Output "Skillset response: $($skillsetResponse.StatusCode)"
    Write-Output "Indexer response: $($indexerResponse.StatusCode)"
}
catch {
    throw
}
finally {
    # The following line ensures that sensitive data is not left in memory.
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ssPtr)
}