import aiohttp
import asyncio
import json
from typing import Any, Optional
from aiohttp import ClientWebSocketResponse, web
from azure.identity import DefaultAzureCredential, AzureDeveloperCliCredential, get_bearer_token_provider
from azure.core.credentials import AzureKeyCredential
from backend.tools.tools import RTToolCall, Tool, ToolResultDirection
from backend.helpers import transform_acs_to_openai_format, transform_openai_to_acs_format

class RTMiddleTier:
    endpoint: str
    deployment: str
    key: Optional[str] = None
    selected_voice: str = "alloy"

    # Tools are server-side only for now, though the case could be made for client-side tools
    # in addition to server-side tools that are invisible to the client
    tools: dict[str, Tool] = {}

    # Server-enforced configuration, if set, these will override the client's configuration
    # Typically at least the model name and system message will be set by the server
    model: Optional[str] = None
    system_message: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    disable_audio: Optional[bool] = None

    _tools_pending: dict[str, RTToolCall] = {}
    _token_provider = None

    def __init__(self, endpoint: str, deployment: str, credentials: AzureKeyCredential | AzureDeveloperCliCredential | DefaultAzureCredential):
        self.endpoint = endpoint
        self.deployment = deployment
        if isinstance(credentials, AzureKeyCredential):
            self.key = credentials.key
        else:
            self._token_provider = get_bearer_token_provider(credentials, "https://cognitiveservices.azure.com/.default")
            self._token_provider() # Warm up during startup so we have a token cached when the first request arrives

    async def _process_message_to_client(self, message: Any, client_ws: web.WebSocketResponse, server_ws: ClientWebSocketResponse, is_acs_audio_stream: bool):
        # This method basically follows a 3-step process:
        # 1. Check if we need to react to the message (e.g. a function call needs to me made)
        # 2. Check if we need to transform the message to a different format (e.g. when we use Azure Communication Services)
        # 3. Send the transformed message to the client (Web App or Phone via ACS), if required

        if message is not None:
            match message["type"]:
                case "session.created":
                    session = message["session"]
                    # Hide the instructions, tools and max tokens from clients, if we ever allow client-side
                    # tools, this will need updating
                    session["instructions"] = ""
                    session["tools"] = []
                    session["tool_choice"] = "none"
                    session["max_response_output_tokens"] = None

                case "session.updated":
                    # Prompt the model to take over the conversation and talk whenever a session was updated
                    # This is also the case, when the client connects for the first time
                    # This ensures, that the model starts the conversation the moment the client connects
                    await server_ws.send_json({
                        "type": "response.create"
                    })

                case "response.output_item.added":
                    if "item" in message and message["item"]["type"] == "function_call":
                        message = None

                case "conversation.item.created":
                    if "item" in message and message["item"]["type"] == "function_call":
                        item = message["item"]
                        if item["call_id"] not in self._tools_pending:
                            self._tools_pending[item["call_id"]] = RTToolCall(item["call_id"], message["previous_item_id"])
                        message = None
                    elif "item" in message and message["item"]["type"] == "function_call_output":
                        message = None

                case "response.function_call_arguments.delta":
                    message = None

                case "response.function_call_arguments.done":
                    message = None

                case "response.output_item.done":
                    if "item" in message and message["item"]["type"] == "function_call":
                        item = message["item"]
                        tool_call = self._tools_pending[message["item"]["call_id"]]
                        tool = self.tools[item["name"]]
                        args = item["arguments"]
                        result = await tool.target(json.loads(args))

                        await server_ws.send_json({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": item["call_id"],
                                "output": result.to_text() if result.destination == ToolResultDirection.TO_SERVER else ""
                            }
                        })

                        if result.destination == ToolResultDirection.TO_CLIENT:
                            # Only send extra messages to clients that are not ACS audio streams
                            if is_acs_audio_stream == False:
                                # TODO: this will break clients that don't know about this extra message, rewrite
                                # this to be a regular text message with a special marker of some sort
                                await client_ws.send_json({
                                    "type": "extension.middle_tier_tool_response",
                                    "previous_item_id": tool_call.previous_id,
                                    "tool_name": item["name"],
                                    "tool_result": result.to_text()
                                })
                        message = None

                case "response.done":
                    if len(self._tools_pending) > 0:
                        self._tools_pending.clear() # Any chance tool calls could be interleaved across different outstanding responses?
                        await server_ws.send_json({
                            "type": "response.create"
                        })

                    if "response" in message:
                        replace = False
                        outputs = message["response"]["output"]
                        for output in reversed(outputs):
                            if output["type"] == "function_call":
                                outputs.remove(output)
                                replace = True
                        if replace:
                            message = json.loads(json.dumps(message)) # TODO: This is a hack to make the message a dict again. Find out, what 'replace' does

                # This happens when OpenAI detects, that the user starts speaking and won't continue to speak and send audio.
                # In this case, we don't want to send the unplayed audio buffer to the client anymore.
                # For the web app, we pass this message to the client, so it can clear the audio buffer.
                # For Azure Communication Services, we don't need to do anything here. The transform_openai_to_acs_format function
                # will handle this message and clear the audio buffer.
                case "input_audio_buffer.speech_started":
                    # TODO: Add Truncation
                    # if message["item_id"]:
                    #     await server_ws.send_json({
                    #         "type": "conversation.item.truncate",
                    #         "item_id": message['item_id'],
                    #         "audio_end_ms": ??? # Set this to let the model know, how much audio has been played (https://platform.openai.com/docs/api-reference/realtime-client-events/conversation/item/truncate)
                    #     })
                    pass

        # Transform the message to the Azure Communication Services format,
        # if it comes from the OpenAI realtime stream.
        if is_acs_audio_stream and message is not None:
            message = transform_openai_to_acs_format(message)

        if message is not None:
            await client_ws.send_str(json.dumps(message))

    async def _process_message_to_server(self, data: Any, ws: web.WebSocketResponse, server_ws: ClientWebSocketResponse, is_acs_audio_stream: bool):
        # If the message comes from the Azure Communication Services audio stream, transform it to the OpenAI Realtime API format first
        if (is_acs_audio_stream):
            data = transform_acs_to_openai_format(data, self.model, self.tools, self.system_message, self.temperature, self.max_tokens, self.disable_audio, self.selected_voice)

        if data is not None:
            match data["type"]:
                case "session.update":
                    session = data["session"]
                    session["voice"] = self.selected_voice
                    if self.system_message is not None:
                        session["instructions"] = self.system_message
                    if self.temperature is not None:
                        session["temperature"] = self.temperature
                    if self.max_tokens is not None:
                        session["max_response_output_tokens"] = self.max_tokens
                    if self.disable_audio is not None:
                        session["disable_audio"] = self.disable_audio
                    session["tool_choice"] = "auto" if len(self.tools) > 0 else "none"
                    session["tools"] = [tool.schema for tool in self.tools.values()]
                    data["session"] = session

            await server_ws.send_str(json.dumps(data))

    async def forward_messages(self, ws: web.WebSocketResponse, is_acs_audio_stream: bool):
        async with aiohttp.ClientSession(base_url=self.endpoint) as session:
            params = { "api-version": "2024-10-01-preview", "deployment": self.deployment }

            headers = {}
            if "x-ms-client-request-id" in ws.headers:
                headers["x-ms-client-request-id"] = ws.headers["x-ms-client-request-id"]

            # Setup authentication headers for the OpenAI Realtime API WebSocket connection
            if self.key is not None:
                headers = { "api-key": self.key }
            else:
                if self._token_provider is not None:
                    headers = { "Authorization": f"Bearer {self._token_provider()}" } # NOTE: no async version of token provider, maybe refresh token on a timer?
                else:
                    raise ValueError("No token provider available")

            # Connect to the OpenAI Realtime API WebSocket
            async with session.ws_connect("/openai/realtime", headers=headers, params=params) as target_ws:
                async def from_client_to_server():
                    # Messages from Azure Communication Services or the Web Frontend are forwarded to the OpenAI Realtime API
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            await self._process_message_to_server(data, ws, target_ws, is_acs_audio_stream)
                        else:
                            print("Error: unexpected message type:", msg.type)

                async def from_server_to_client():
                    # Messages from the OpenAI Realtime API are forwarded to the Azure Communication Services or the Web Frontend
                    async for msg in target_ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            await self._process_message_to_client(data, ws, target_ws, is_acs_audio_stream)
                        else:
                            print("Error: unexpected message type:", msg.type)

                try:
                    await asyncio.gather(from_client_to_server(), from_server_to_client())
                except ConnectionResetError:
                    # Ignore the errors resulting from the client disconnecting the socket
                    pass
