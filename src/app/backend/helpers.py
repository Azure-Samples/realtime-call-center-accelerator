import json
from openai.types.beta.realtime import (InputAudioBufferAppendEvent, SessionUpdateEvent)
from openai.types.beta.realtime.session_update_event import Session, SessionTurnDetection
from typing import Any, Literal, Optional
from backend.tools.tools import Tool

def transform_acs_to_openai_format(msg_data: Any, model: Optional[str], tools: dict[str, Tool], system_message: Optional[str], temperature: Optional[float], max_tokens: Optional[int], disable_audio: Optional[bool], voice: str) -> InputAudioBufferAppendEvent | SessionUpdateEvent | Any | None:
    """
    Transforms websocket message data from Azure Communication Services (ACS) to the OpenAI Realtime API format.
    Args:
        msg_data_json (str): The JSON string containing the ACS message data.
    Returns:
        Optional[str]: The transformed message in the OpenAI Realtime API format
    This is needed to plug the Azure Communication Services audio stream into the OpenAI Realtime API.
    Both APIs have different message formats, so this function acts as a bridge between them.
    This method decides, if the given message is relevant for the OpenAI Realtime API, and if so, it is transformed to the OpenAI Realtime API format.
    """
    oai_message: Any = None

    # Initial message from Azure Communication Services.
    # Set the initial configuration for the OpenAI Realtime API by sending a session.update message.
    if msg_data["kind"] == "AudioMetadata":
        oai_message = {
            "type": "session.update",
            "session": {
                "voice": voice,
                "tool_choice": "auto" if len(tools) > 0 else "none",
                "tools": [tool.schema for tool in tools.values()],
                "turn_detection": {
                    "type": 'server_vad',
                    "threshold": 0.7, # Adjust if necessary
                    "prefix_padding_ms": 300, # Adjust if necessary
                    "silence_duration_ms": 500 # Adjust if necessary
                },
            }
        }

        if system_message is not None:
            oai_message["session"]["instructions"] = system_message
        if temperature is not None:
            oai_message["session"]["temperature"] = temperature
        if max_tokens is not None:
            oai_message["session"]["max_response_output_tokens"] = max_tokens
        if disable_audio is not None:
            oai_message["session"]["disable_audio"] = disable_audio

    # Message from Azure Communication Services with audio data.
    # Transform the message to the OpenAI Realtime API format.
    elif msg_data["kind"] == "AudioData":
        oai_message = {
            "type": "input_audio_buffer.append",
            "audio": msg_data["audioData"]["data"]
        }

    return oai_message

def transform_openai_to_acs_format(msg_data: Any) -> Optional[Any]:
    """
    Transforms websocket message data from the OpenAI Realtime API format into the Azure Communication Services (ACS) format.
    Args:
        msg_data_json (str): The JSON string containing the message data from the OpenAI Realtime API.
    Returns:
        Optional[str]: A JSON string containing the transformed message in ACS format, or None if the message type is not handled.
    This is needed to plug the OpenAI Realtime API audio stream into Azure Communication Services.
    Both APIs have different message formats, so this function acts as a bridge between them.
    This method decides, if the given message is relevant for the ACS, and if so, it is transformed to the ACS format.
    """
    acs_message = None

    # Message from the OpenAI Realtime API with audio data.
    # Transform the message to the Azure Communication Services format.
    if msg_data["type"] == "response.audio.delta":
        acs_message = {
            "kind": "AudioData",
            "audioData": {
                "data": msg_data["delta"]
            }
        }

    # Message from the OpenAI Realtime API detecting, that the user starts speaking and interrupted the AI.
    # In this case, we don't want to send the unplayed audio buffer to the client anymore and clear the buffer audio.
    # Buffered audio is audio data that has been sent to Azure Communication Services, but not yet played by the client.
    if msg_data["type"] == "input_audio_buffer.speech_started":
        acs_message = {
            "kind": "StopAudio",
            "audioData": None,
            "stopAudio": {}
        }

    return acs_message

async def load_prompt_from_markdown(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        prompt = file.read()
    return prompt
