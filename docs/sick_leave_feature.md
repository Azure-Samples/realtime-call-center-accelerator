# Sick Leave Request Feature

This document describes the sick leave request handling feature implemented in the realtime call center accelerator.

## Overview

The sick leave feature allows employees to report sick leave through the voice assistant. The assistant collects relevant information from the caller and submits it to a configured API endpoint for processing.

## Configuration

To use this feature, you need to set the following environment variable:

```
SICK_LEAVE_API_URL=https://your-api-endpoint.com/sick-leave
```

This can be set in your `.env` file for local development or in the Azure environment configuration for production.

## API Integration

The system expects the external API to accept POST requests with the following JSON structure:

```json
{
  "employee_name": "John Doe",
  "employee_id": "EMP12345",
  "start_date": "2025-07-01",
  "end_date": "2025-07-03",
  "reason": "Flu symptoms",
  "contact_phone": "+1234567890",
  "contact_email": "john.doe@example.com",
  "notes": "Doctor's appointment scheduled for tomorrow",
  "timestamp": "2025-07-01T06:52:14.123456",
  "source": "voice_call_center"
}
```

The API is expected to return a response in the following format:

```json
{
  "success": true,
  "request_id": "SL-12345",
  "message": "Request processed successfully"
}
```

## Error Handling

The feature includes robust error handling for:

- API configuration issues
- Network errors
- Invalid date formats
- API response errors

In all error cases, the caller will be informed of the issue and provided with alternative steps to report their sick leave.

## Conversation Flow

The AI assistant is trained to recognize phrases related to sick leave requests and will guide the caller through providing the necessary information. The system prompt includes examples of how these conversations should flow.

## Logging

All sick leave requests and errors are logged for monitoring and troubleshooting purposes. Sensitive information is handled appropriately.
