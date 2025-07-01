import json
import os
import logging
import re
import datetime
import aiohttp
from typing import Any, Dict
from backend.tools.tools import Tool, ToolResult, ToolResultDirection

# Set up logging
logger = logging.getLogger("sick_leave_tool")

# Define the schema for the sick leave request tool
_sick_leave_request_schema = {
    "type": "function",
    "name": "submit_sick_leave",
    "description": "Submit a sick leave request for an employee. Use this tool when a user wants to report sick leave.",
    "parameters": {
        "type": "object",
        "properties": {
            "employee_name": {
                "type": "string",
                "description": "Full name of the employee requesting sick leave"
            },
            "employee_id": {
                "type": "string",
                "description": "Employee ID if provided (optional)"
            },
            "start_date": {
                "type": "string",
                "description": "Start date of the sick leave in YYYY-MM-DD format"
            },
            "end_date": {
                "type": "string",
                "description": "End date of the sick leave in YYYY-MM-DD format (can be the same as start_date)"
            },
            "reason": {
                "type": "string",
                "description": "Brief reason for sick leave (optional)"
            },
            "contact_phone": {
                "type": "string",
                "description": "Contact phone number during leave period (optional)"
            },
            "contact_email": {
                "type": "string",
                "description": "Contact email during leave period (optional)"
            },
            "notes": {
                "type": "string",
                "description": "Additional notes or information about the sick leave request (optional)"
            }
        },
        "required": ["employee_name", "start_date", "end_date"],
        "additionalProperties": False
    }
}

async def _submit_sick_leave_request(args: Dict[str, Any]) -> ToolResult:
    """
    Process a sick leave request and submit it to the configured API endpoint.
    
    Args:
        args: Dictionary containing the sick leave request details
        
    Returns:
        ToolResult: Result of the operation to be sent to the client or server
    """
    logger.info(f"Processing sick leave request for {args.get('employee_name')}")
    
    # Validate required fields
    if not args.get('employee_name'):
        error_message = "Employee name is required"
        logger.error(error_message)
        return ToolResult({"success": False, "error": error_message}, ToolResultDirection.TO_CLIENT)
    
    # Validate dates
    try:
        start_date = datetime.datetime.strptime(args.get('start_date', ''), '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(args.get('end_date', ''), '%Y-%m-%d').date()
        
        # Ensure end date is not before start date
        if end_date < start_date:
            error_message = "End date cannot be before start date"
            logger.error(error_message)
            return ToolResult({"success": False, "error": error_message}, ToolResultDirection.TO_CLIENT)
            
    except ValueError:
        error_message = "Invalid date format. Please use YYYY-MM-DD format"
        logger.error(error_message)
        return ToolResult({"success": False, "error": error_message}, ToolResultDirection.TO_CLIENT)
    
    # Get the API URL from environment variables
    api_url = os.environ.get("SICK_LEAVE_API_URL")
    if not api_url:
        error_message = "Sick leave API URL is not configured"
        logger.error(error_message)
        return ToolResult({"success": False, "error": error_message, "alternative": "Please contact HR directly to report sick leave"}, ToolResultDirection.TO_CLIENT)
    
    # Prepare the request payload
    payload = {
        "employee_name": args.get('employee_name'),
        "employee_id": args.get('employee_id', ''),
        "start_date": args.get('start_date'),
        "end_date": args.get('end_date'),
        "reason": args.get('reason', ''),
        "contact_phone": args.get('contact_phone', ''),
        "contact_email": args.get('contact_email', ''),
        "notes": args.get('notes', ''),
        "timestamp": datetime.datetime.now().isoformat(),
        "source": "voice_call_center"
    }
    
    # Submit the request to the API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Sick leave request submitted successfully: {result.get('request_id')}")
                    
                    # Return success response to the client
                    return ToolResult({
                        "success": True,
                        "request_id": result.get('request_id', ''),
                        "message": result.get('message', 'Your sick leave request has been submitted successfully'),
                        "start_date": args.get('start_date'),
                        "end_date": args.get('end_date')
                    }, ToolResultDirection.TO_CLIENT)
                else:
                    error_text = await response.text()
                    logger.error(f"API error: {response.status} - {error_text}")
                    return ToolResult({
                        "success": False, 
                        "error": f"Failed to submit sick leave request. Error: {response.status}",
                        "alternative": "Please contact HR directly to report sick leave"
                    }, ToolResultDirection.TO_CLIENT)
    except aiohttp.ClientError as e:
        logger.error(f"API connection error: {str(e)}")
        return ToolResult({
            "success": False, 
            "error": "Connection error when submitting sick leave request",
            "alternative": "Please contact HR directly to report sick leave"
        }, ToolResultDirection.TO_CLIENT)
    except Exception as e:
        logger.error(f"Unexpected error processing sick leave request: {str(e)}")
        return ToolResult({
            "success": False, 
            "error": "An unexpected error occurred",
            "alternative": "Please contact HR directly to report sick leave"
        }, ToolResultDirection.TO_CLIENT)

def sick_leave_request_tool() -> Tool:
    """
    Create and return a Tool instance for handling sick leave requests.
    
    Returns:
        Tool: A tool that can be registered with the RTMiddleTier
    """
    return Tool(schema=_sick_leave_request_schema, target=_submit_sick_leave_request)
