import logging
import os
from pathlib import Path
from typing import Optional
from aiohttp import web
from dotenv import load_dotenv
from backend.tools.rag.ai_search import report_grounding_tool, search_tool
from backend.tools.reportstore.cosmos import CosmosDBStore
from backend.helpers import load_prompt_from_markdown
from backend.rtmt import RTMiddleTier
from backend.azure import get_azure_credentials, fetch_prompt_from_azure_storage
from backend.rtmt import RTMiddleTier
from backend.acs import AcsCaller
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("voicerag")

async def create_app():
    load_dotenv()

    azure_credentials = get_azure_credentials(os.environ.get("AZURE_TENANT_ID"))
    cosmos: Optional[CosmosDBStore] = None
    search_client: Optional[SearchClient] = None
    caller: Optional[AcsCaller] = None

    # Load LLM connection and authentication
    llm_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    llm_deployment = os.environ.get("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME")
    llm_key = os.environ.get("AZURE_OPENAI_API_KEY")
    llm_credential = azure_credentials if not llm_key else AzureKeyCredential(llm_key)
    if not llm_endpoint or not llm_deployment or not llm_credential:
        raise ValueError("LLM connection or authentication error. Check environment variables.")

    # Load Azure AI Search connection and authentication
    search_key = os.environ.get("AZURE_SEARCH_API_KEY")
    search_endpoint=os.environ.get("AZURE_SEARCH_ENDPOINT")
    search_index=os.environ.get("AZURE_SEARCH_INDEX")
    search_semantic_configuration=os.environ.get("AZURE_SEARCH_SEMANTIC_CONFIGURATION")
    if (search_endpoint is not None and search_index is not None and search_key is not None and search_semantic_configuration is not None):
        search_credential = AzureKeyCredential(search_key)
        search_client = SearchClient(search_endpoint, search_index, search_credential, user_agent="RTMiddleTier")
    else:
        logger.warning("Azure AI Search is not configured")

    # Load Cosmos DB connection and authentication
    cosmos_endpoint = os.environ.get("COSMOSDB_ACCOUNT_ENDPOINT")
    cosmos_db_name = os.environ.get("COSMOSDB_DATABASE_NAME")
    cosmos_container_name = os.environ.get("COSMOSDB_CONTAINER_NAME")
    if (cosmos_endpoint is not None and
        cosmos_db_name is not None and
        cosmos_container_name is not None):
        cosmos = CosmosDBStore(
            cosmos_endpoint,
            cosmos_db_name,
            cosmos_container_name
        )
    else:
        logger.warning("CosmosDB is not configured")
    
    # Register the Azure Communication Services
    acs_source_number = os.environ.get("ACS_SOURCE_NUMBER")
    acs_connection_string = os.environ.get("ACS_CONNECTION_STRING")
    acs_callback_path = os.environ.get("ACS_CALLBACK_PATH")
    acs_media_streaming_websocket_path = os.environ.get("ACS_MEDIA_STREAMING_WEBSOCKET_PATH")
    if (acs_source_number is not None and
        acs_connection_string is not None and
        acs_callback_path is not None and
        acs_media_streaming_websocket_path is not None):
        caller = AcsCaller(
            acs_source_number,
            acs_connection_string,
            acs_callback_path,
            acs_media_streaming_websocket_path
        )
    else:
        logger.warning("Azure Communication Services is not configured")

    # Create the OpenAI Realtime API handler
    rtmt = RTMiddleTier(llm_endpoint, llm_deployment, llm_credential)

    # Set the system prompt
    system_prompt = None

    # Attempt to fetch from Azure Storage
    try:
        system_prompt = await fetch_prompt_from_azure_storage(
            container_name='prompt',
            file_name='system_prompt.md'
        )
    except Exception as e:
        logger.warning(f"Could not fetch system prompt from Azure Storage: {e}")
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(BASE_DIR, 'system_prompt.md')  # Ensure the file is in the same folder
        system_prompt = await load_prompt_from_markdown(file_path)

    rtmt.system_message = system_prompt

    # Register the tools for function calling
    if search_client is not None and search_semantic_configuration is not None:
        rtmt.tools["search"] = search_tool(search_client, search_semantic_configuration)
        rtmt.tools["report_grounding"] = report_grounding_tool(search_client)

    # Define the WebSocket handler for the Web Frontend
    async def websocket_handler(request: web.Request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await rtmt.forward_messages(ws, False)
        return ws

    # Define the WebSocket handler for the Azure Communication Services Audio Stream
    async def websocket_handler_acs(request: web.Request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await rtmt.forward_messages(ws, True)
        return ws

    # Serve static files and index.html
    current_directory = Path(__file__).parent  # Points to 'app' directory
    static_directory = current_directory / 'static'
    if not static_directory.exists():
        raise FileNotFoundError("Static directory not found at expected path: {}".format(static_directory))

    # Serve index.html at root
    async def index(request):
        return web.FileResponse(static_directory / 'index.html')
    
    async def update_voice(request):
        data = await request.json()
        rtmt.selected_voice = data.get('voice', 'alloy')
        return web.Response(text="Voice selected successfully")

    async def call(request):
        body = await request.json()
        if (caller is not None):
            await caller.initiate_call(body['number'])
            return web.Response(text="Created outbound call")
        else:
            return web.Response(text="Outbound calling is not configured")

    # Register the routes
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_static('/static/', path=str(static_directory), name='static')
    app.router.add_post('/call', call)
    app.router.add_get("/realtime", websocket_handler)
    app.router.add_get("/realtime-acs", websocket_handler_acs)
    app.router.add_post('/update-voice', update_voice)
    
    if (caller is not None):
        app.router.add_post("/acs", caller.outbound_call_handler)

    return app

if __name__ == "__main__":
    host = os.environ.get("HOST", "localhost")
    port = int(os.environ.get("PORT", 8765))
    web.run_app(create_app(), host=host, port=port, access_log=None)
