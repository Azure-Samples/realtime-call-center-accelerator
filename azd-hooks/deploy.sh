#!/bin/bash

# set -e

SERVICE_NAME="$1"

if [ "$SERVICE_NAME" == "" ]; then
echo "No phase name provided - aborting"
exit 0;
fi

AZURE_ENV_NAME="$2"

if [ "$AZURE_ENV_NAME" == "" ]; then
echo "No environment name provided - aborting"
exit 0;
fi

if [[ $SERVICE_NAME =~ ^[a-z0-9]{3,12}$ ]]; then
    echo "service name $SERVICE_NAME is valid"
else
    echo "service name $SERVICE_NAME is invalid - only numbers and lower case min 5 and max 12 characters allowed - aborting"
    exit 0;
fi

RESOURCE_GROUP="rg-$AZURE_ENV_NAME"

if [ $(az group exists --name $RESOURCE_GROUP) = false ]; then
    echo "resource group $RESOURCE_GROUP does not exist"
    error=1
else   
    echo "resource group $RESOURCE_GROUP already exists"
    LOCATION=$(az group show -n $RESOURCE_GROUP --query location -o tsv)
fi
# Get the name of the Azure application insights instance
APPINSIGHTS_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.Insights/components" --query "[0].name" -o tsv)
# Get the name of the Azure container registry
AZURE_CONTAINER_REGISTRY_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.ContainerRegistry/registries" --query "[0].name" -o tsv)
# Get the name of the Azure Open AI Services instance
OPENAI_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.CognitiveServices/accounts" --query "[0].name" -o tsv)
# Get the name of the Azure environment
ENVIRONMENT_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.App/managedEnvironments" --query "[0].name" -o tsv)
# Get the name of the Azure user managed identity
IDENTITY_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.ManagedIdentity/userAssignedIdentities" --query "[0].name" -o tsv)
# Get the Azure subscription ID
AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
# Get Azure Search service name
AZURE_SEARCH_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.Search/searchServices" --query "[0].name" -o tsv)
# Get the first index name from the Azure Search service
AZURE_SEARCH_INDEX_NAME="voicerag-intvect"
# Get the semantic configuration setting
AZURE_SEARCH_SEMANTIC_CONFIGURATION="default"
# Get Azure Search API key
AZURE_SEARCH_API_KEY=$(az search admin-key show --service-name $AZURE_SEARCH_NAME --resource-group $RESOURCE_GROUP --query "primaryKey" -o tsv)
# Get Azure Storage account name
STORAGE_ACCOUNT_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.Storage/storageAccounts" --query "[0].name" -o tsv)
# Get the name of the Azure Communication Services instance
AZURE_COMMUNICATION_SERVICES_NAME=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.Communication/communicationServices" --query "[0].name" -o tsv)
# Get the connection string of the Azure Communication Services instance
ACS_CONNECTION_STRING=$(az communication list-key --name $AZURE_COMMUNICATION_SERVICES_NAME --resource-group $RESOURCE_GROUP --query "primaryConnectionString" -o tsv)
# Get the phone number of the Azure Communication Services instance
AZURE_COMMUNICATION_SERVICES_PHONE_NUMBER=$(az communication phonenumber list --connection-string $ACS_CONNECTION_STRING --query "[0].phoneNumber" -o tsv)

# Check if phone number is empty and set default value if it is
if [ -z "$AZURE_COMMUNICATION_SERVICES_PHONE_NUMBER" ]; then
    AZURE_COMMUNICATION_SERVICES_PHONE_NUMBER="Manualupdate"
    echo "Phone number is empty, the number needs to be acquired manually"
fi

echo "container registry name: $AZURE_CONTAINER_REGISTRY_NAME"
echo "application insights name: $APPINSIGHTS_NAME"
echo "openai name: $OPENAI_NAME"
echo "identity name: $IDENTITY_NAME"
echo "service name: $SERVICE_NAME"
echo "environment name: $ENVIRONMENT_NAME"
echo "communication service name: $AZURE_COMMUNICATION_SERVICES_NAME"
echo "communication service phone number: $AZURE_COMMUNICATION_SERVICES_PHONE_NUMBER"
echo "storage account name: $STORAGE_ACCOUNT_NAME"
echo "azure search name: $AZURE_SEARCH_NAME"
echo "azure search index name: $AZURE_SEARCH_INDEX_NAME"

# Check if the container app already exists
CONTAINER_APP_EXISTS=$(az resource list -g $RESOURCE_GROUP --resource-type "Microsoft.App/containerApps" --query "[?contains(name, '$SERVICE_NAME')].id" -o tsv)
EXISTS="false"

if [ "$CONTAINER_APP_EXISTS" == "" ]; then
    echo "container app $SERVICE_NAME does not exist"
else
    echo "container app $SERVICE_NAME already exists"
    EXISTS="true"
fi

# Build the container image
IMAGE_TAG=$(date '+%m%d%H%M%S')
az acr build --subscription ${AZURE_SUBSCRIPTION_ID} --registry ${AZURE_CONTAINER_REGISTRY_NAME} --image $SERVICE_NAME:$IMAGE_TAG ./src/$SERVICE_NAME --no-logs
IMAGE_NAME="${AZURE_CONTAINER_REGISTRY_NAME}.azurecr.io/$SERVICE_NAME:$IMAGE_TAG"

echo "deploying image: $IMAGE_NAME"

# Deploy the container app
ACA_NAME=callcenter$SERVICE_NAME
URI=$(az deployment group create -g $RESOURCE_GROUP -f ./infra/core/app/web.bicep \
          -p aiSearchName=$AZURE_SEARCH_NAME  -p storageAccountName=$STORAGE_ACCOUNT_NAME -p name=$ACA_NAME \
          -p location=$LOCATION -p containerAppsEnvironmentName=$ENVIRONMENT_NAME \
          -p containerRegistryName=$AZURE_CONTAINER_REGISTRY_NAME -p applicationInsightsName=$APPINSIGHTS_NAME \
          -p communicationServiceName=$AZURE_COMMUNICATION_SERVICES_NAME -p serviceName=$SERVICE_NAME  \
          -p communicationServicePhoneNumber=$AZURE_COMMUNICATION_SERVICES_PHONE_NUMBER \
          -p openaiName=$OPENAI_NAME -p identityName=$IDENTITY_NAME -p imageName=$IMAGE_NAME \
          --query properties.outputs.uri.value)

echo "updating container app settings"

# Fetch the container app hostname
CONTAINER_APP_HOSTNAME=$(az containerapp show --name $ACA_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)

# Update the container app settings
az containerapp update --name $ACA_NAME --resource-group $RESOURCE_GROUP \
--set-env-vars ACS_CALLBACK_PATH="https://$CONTAINER_APP_HOSTNAME/acs" \
               ACS_MEDIA_STREAMING_WEBSOCKET_PATH="wss://$CONTAINER_APP_HOSTNAME/realtime-acs" \
               AZURE_SEARCH_API_KEY="$AZURE_SEARCH_API_KEY" AZURE_SEARCH_INDEX="$AZURE_SEARCH_INDEX_NAME"  \
               AZURE_SEARCH_SEMANTIC_CONFIGURATION="$AZURE_SEARCH_SEMANTIC_CONFIGURATION"

echo "Application uri: $URI"

# Configuration of Azure AI search index
echo "Executing upload_data.sh to upload documents to Azure blob storage"
SCRIPT_DIR=$(dirname "$0")
PROJECT_ROOT="$SCRIPT_DIR/../"
cd "$PROJECT_ROOT"
echo "Current directory after changing to project root: $(pwd)"
sh scripts/upload_data.sh