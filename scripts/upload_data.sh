#!/bin/bash

set -e

# Function to load the Azure Developer CLI environment
load_azd_env() {
    echo "Loading Azure Developer CLI environment..."
    AZD_ENV_JSON=$(azd env list -o json)
    if [ $? -ne 0 ]; then
        echo "Error loading azd environment."
        exit 1
    fi

    ENV_FILE_PATH=$(echo "$AZD_ENV_JSON" | jq -r '.[] | select(.IsDefault == true) | .DotEnvPath')
    if [ -z "$ENV_FILE_PATH" ]; then
        echo "No default azd environment file found."
        exit 1
    fi

    echo "Loading environment variables from $ENV_FILE_PATH"
    set -o allexport
    source "$ENV_FILE_PATH"
    set +o allexport
}



upload_documents() {
    # Check for Azure CLI authentication
    if ! az account show &>/dev/null; then
        echo "Azure CLI is not authenticated. Please run 'az login' to authenticate."
        exit 1
    fi

    # Define the data folder at the root of the project
    SCRIPT_DIR=$(dirname "$(realpath "$0")")
    PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")
    DATA_FOLDER="$PROJECT_ROOT/data"

    # Check if the data folder exists
    if [ ! -d "$DATA_FOLDER" ]; then
        echo "Data folder not found: $DATA_FOLDER"
        exit 1
    fi

    # Iterate over all files in the data folder
    for FILE in "$DATA_FOLDER"/*; do
        # Check if the file exists and is a regular file
        if [ ! -f "$FILE" ]; then
            echo "Skipping non-file: $FILE"
            continue
        fi

        # Use the file name as the BLOB name
        BLOB_NAME=$(basename "$FILE")

        # Check if 'pv' is installed
        if command -v pv &>/dev/null; then
            USE_PV=true
        else
            USE_PV=false
            echo "'pv' is not installed. Falling back to native upload method."
        fi

        # Upload the file to Azure Blob Storage
        if [ "$USE_PV" = true ]; then
            pv "$FILE" | az storage blob upload --account-name "$AZURE_STORAGE_ACCOUNT" --container-name "$AZURE_STORAGE_CONTAINER" --name "$BLOB_NAME" --file "$FILE" --auth-mode login  --overwrite
        else
            az storage blob upload --account-name "$AZURE_STORAGE_ACCOUNT" --container-name "$AZURE_STORAGE_CONTAINER" --name "$BLOB_NAME" --file "$FILE" --auth-mode login --overwrite
        fi

        # Check for the upload status
        if [ $? -eq 0 ]; then
            echo "File '$FILE' uploaded successfully as '$BLOB_NAME'."
        else
            echo "Error uploading the file '$FILE'."
        fi
    done
}

load_azd_env
upload_documents