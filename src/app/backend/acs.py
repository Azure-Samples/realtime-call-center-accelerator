from aiohttp import web
from azure.core.messaging import CloudEvent
from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
    MediaStreamingOptions,
    MediaStreamingTransportType,
    MediaStreamingContentType,
    MediaStreamingAudioChannelType,
    AudioFormat)

class AcsCaller:
    source_number: str
    acs_connection_string: str
    acs_callback_path: str
    websocket_url: str
    media_streaming_configuration: MediaStreamingOptions

    def __init__(self, source_number:str, acs_connection_string: str, acs_callback_path: str, acs_media_streaming_websocket_path: str):
        self.source_number = source_number
        self.acs_connection_string = acs_connection_string
        self.acs_callback_path = acs_callback_path
        self.media_streaming_configuration = MediaStreamingOptions(
            transport_url=acs_media_streaming_websocket_path,
            transport_type=MediaStreamingTransportType.WEBSOCKET,
            content_type=MediaStreamingContentType.AUDIO,
            audio_channel_type=MediaStreamingAudioChannelType.MIXED,
            start_media_streaming=True,
            enable_bidirectional=True,
            audio_format=AudioFormat.PCM24_K_MONO
        )
    
    async def initiate_call(self, target_number: str):
        self.call_automation_client = CallAutomationClient.from_connection_string(self.acs_connection_string)
        self.target_participant = PhoneNumberIdentifier(target_number)
        self.source_caller = PhoneNumberIdentifier(self.source_number)
        self.call_automation_client.create_call(
            self.target_participant, 
            self.acs_callback_path,
            media_streaming=self.media_streaming_configuration,
            source_caller_id_number=self.source_caller
        )

    async def outbound_call_handler(self, request):
        cloudevent = await request.json() 
        for event_dict in cloudevent:
            event = CloudEvent.from_dict(event_dict)
            if event.data is None:
                continue
                
            call_connection_id = event.data['callConnectionId']
            print(f"{event.type} event received for call connection id: {call_connection_id}")

            if event.type == "Microsoft.Communication.CallConnected":
                print("Call connected")            

        return web.Response(status=200)
