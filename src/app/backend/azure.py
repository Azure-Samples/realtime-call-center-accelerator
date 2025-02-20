from azure.identity import AzureDeveloperCliCredential, DefaultAzureCredential
import os
from azure.storage.blob.aio import BlobServiceClient

def get_azure_credentials(tenant_id: str | None = None) -> AzureDeveloperCliCredential | DefaultAzureCredential:
    credentials: AzureDeveloperCliCredential | DefaultAzureCredential | None = None

    if tenant_id is not None:
        print("Using AzureDeveloperCliCredential with tenant_id %s", tenant_id)                
        credentials =  AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
    else:
        print("Using DefaultAzureCredential")
        credentials = DefaultAzureCredential()
    
    # Warm up before we start getting requests
    credentials.get_token("https://search.azure.com/.default")
    return credentials



async def fetch_prompt_from_azure_storage(container_name: str, file_name: str) -> str:
    """
    Fetches a prompt as text from the specified container in Azure Storage.
    """
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        raise ValueError("Missing 'AZURE_STORAGE_CONNECTION_STRING' environment variable.")

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(file_name)

    blob_data = await blob_client.download_blob()
    content = await blob_data.readall()
    return content.decode("utf-8")