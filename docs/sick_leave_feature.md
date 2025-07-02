# Sick Leave Request Feature

This document describes the sick leave request handling feature implemented in the realtime call center accelerator.

## Overview

The sick leave feature allows employees to report sick leave through the voice assistant. The assistant collects relevant information from the caller and submits it to a configured API endpoint for processing.

## Configuration

To use this feature, you need to set the following environment variables:

```
# For submitting sick leave requests
SICK_LEAVE_API_URL=https://pacific-mock.azurewebsites.net/api/sickleave/apply

# For checking leave balances (optional)
SICK_LEAVE_BALANCE_API_URL=https://pacific-mock.azurewebsites.net/api/sickleave/balance
```

These can be set in your `.env` file for local development or in the Azure environment configuration for production. The deployment script automatically configures these variables in the Azure Container App.

## API Integration

### Server Requirements

The leave management server should expose a RESTful API with the following endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sick-leave` | POST | Submit a new sick leave request |
| `/api/sick-leave/{request_id}` | GET | Get details of a specific sick leave request |
| `/api/sick-leave/{request_id}` | DELETE | Cancel a sick leave request |
| `/api/sick-leave/employee/{employee_id}` | GET | Get all sick leave requests for an employee |

Currently, the system is only integrated with the POST endpoint for creating sick leave requests.

### Sick Leave Application

#### Request Format

The system sends POST requests to the apply endpoint with the following JSON structure:

```json
{
  "date": "2025-07-01",
  "employeeId": "default"
}
```

#### Response Format

The API returns the following response for sick leave applications:

```json
{
  "success": true,
  "message": "Your sick leave request has been processed successfully",
  "remainingBalance": 10.5
}
```

### Sick Leave Balance Check

#### Request Format

The system sends GET requests to the balance endpoint, optionally with an employee ID as a query parameter:

```
GET /api/sickleave/balance?employeeId=default
```

#### Response Format

The API returns the following response for balance checks:

```json
{
  "balance": 10.5,
  "updatedAt": "2025-07-01T12:34:56Z"
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
