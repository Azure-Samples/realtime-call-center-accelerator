import json
import logging
import os
import subprocess

from azure.core.exceptions import ResourceExistsError
from azure.identity import AzureDeveloperCliCredential
from azure.search.documents.indexes import SearchIndexerClient
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from rich.logging import RichHandler


def load_azd_env():
    """Get path to current azd env file and load file using python-dotenv"""
    result = subprocess.run("azd env list -o json", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception("Error loading azd env")
    env_json = json.loads(result.stdout)
    env_file_path = None
    for entry in env_json:
        if entry["IsDefault"]:
            env_file_path = entry["DotEnvPath"]
    if not env_file_path:
        raise Exception("No default azd env file found")
    logger.info(f"Loading azd env from {env_file_path}")
    load_dotenv(env_file_path, override=True)

def upload_documents(azure_credential, indexer_name, azure_search_endpoint, azure_storage_endpoint, azure_storage_container):
    indexer_client = SearchIndexerClient(azure_search_endpoint, azure_credential)
    # Upload the documents in /data folder to the blob storage container
    blob_client = BlobServiceClient(
        account_url=azure_storage_endpoint, credential=azure_credential,
        max_single_put_size=4 * 1024 * 1024
    )
    container_client = blob_client.get_container_client(azure_storage_container)
    if not container_client.exists():
        container_client.create_container()
    existing_blobs = [blob.name for blob in container_client.list_blobs()]

    # Open each file in /data folder
    for file in os.scandir("data"):
        with open(file.path, "rb") as opened_file:
            filename = os.path.basename(file.path)
            # Check if blob already exists
            if filename in existing_blobs:
                logger.info("Blob already exists, skipping file: %s", filename)
            else:
                logger.info("Uploading blob for file: %s", filename)
                blob_client = container_client.upload_blob(filename, opened_file, overwrite=True)

    # Start the indexer
    try:
        indexer_client.run_indexer(indexer_name)
        logger.info("Indexer started. Any unindexed blobs should be indexed in a few minutes, check the Azure Portal for status.")
    except ResourceExistsError:
        logger.info("Indexer already running, not starting again")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)])
    logger = logging.getLogger("voicerag")
    logger.setLevel(logging.INFO)

    logger = logging.getLogger("voicerag")

    load_azd_env()

    AZURE_SEARCH_INDEX = os.environ["AZURE_SEARCH_INDEX"]
    AZURE_SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
    AZURE_STORAGE_ENDPOINT = os.environ["AZURE_STORAGE_ENDPOINT"]
    AZURE_STORAGE_CONTAINER = os.environ["AZURE_STORAGE_CONTAINER"]

    azure_credential = AzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"], process_timeout=60)

    upload_documents(azure_credential,
        indexer_name=f"{AZURE_SEARCH_INDEX}-indexer",
        azure_search_endpoint=AZURE_SEARCH_ENDPOINT,
        azure_storage_endpoint=AZURE_STORAGE_ENDPOINT,
        azure_storage_container=AZURE_STORAGE_CONTAINER)