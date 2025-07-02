# Leave Management API Configuration

This document provides configuration details for connecting to your leave management system.

## API Endpoints

The system expects a leave management server with the following endpoints:

| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/api/sickleave/apply` | POST | Submit a new sick leave request | Implemented |
| `/api/sickleave/balance` | GET | Get leave balance for an employee | Implemented |
| `/api/sickleave/{request_id}` | GET | Get details of a specific sick leave request | Not implemented |
| `/api/sickleave/{request_id}` | DELETE | Cancel a sick leave request | Not implemented |

## Configuration Options

### Environment Variables

The following environment variables should be set:

- `SICK_LEAVE_API_URL` (Required): The URL to submit sick leave requests (https://pacific-mock.azurewebsites.net/api/sickleave/apply)
- `SICK_LEAVE_BALANCE_API_URL` (Optional): The URL to check leave balances (https://pacific-mock.azurewebsites.net/api/sickleave/balance)
- `LEAVE_API_TIMEOUT` (Optional): Timeout in seconds for API requests (default: 30)
- `LEAVE_API_AUTH_TOKEN` (Optional): Authentication token if required by your API

### Authentication

The current implementation doesn't include authentication. If your API requires authentication, 
you'll need to modify the `sick_leave_tool.py` file to include appropriate headers in the request.

## Sample Configuration

For local development, create a `.env` file in the `src/app` directory with:

```
SICK_LEAVE_API_URL=https://pacific-mock.azurewebsites.net/api/sickleave/apply
SICK_LEAVE_BALANCE_API_URL=https://pacific-mock.azurewebsites.net/api/sickleave/balance
LEAVE_API_TIMEOUT=30
LEAVE_API_AUTH_TOKEN=your-auth-token
```

For deployment to Azure, update the environment variables in your Container App service.

## Testing the Integration

You can test the integration with a mock server using:

```bash
# Start a mock server
npx json-server --watch mock-leave-api.json --port 3000

# Set the environment variable to point to the mock server
export SICK_LEAVE_API_URL=http://localhost:3000/sick-leave
```
