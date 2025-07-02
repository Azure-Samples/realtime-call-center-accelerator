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
            "employee_id": {
                "type": "string",
                "description": "Employee ID of the person requesting sick leave (defaults to 'default' if not provided)"
            },
            "date": {
                "type": "string",
                "description": "Date of the sick leave in YYYY-MM-DD format"
            }
        },
        "required": ["date"],
        "additionalProperties": False
    }
}

# Define the schema for checking sick leave balance
_sick_leave_balance_schema = {
    "type": "function",
    "name": "check_sick_leave_balance",
    "description": "Check the remaining sick leave balance for an employee. Use this when a user wants to know how many sick days they have remaining.",
    "parameters": {
        "type": "object",
        "properties": {
            "employee_id": {
                "type": "string",
                "description": "Employee ID of the person checking their sick leave balance (defaults to 'default' if not provided)"
            }
        },
        "required": [],
        "additionalProperties": False
    }
}

# Define the schema for checking leave balance
_check_leave_balance_schema = {
    "type": "function",
    "name": "check_leave_balance",
    "description": "Check the available leave balance for an employee. Use this tool when a user wants to know their remaining sick leave days.",
    "parameters": {
        "type": "object",
        "properties": {
            "employee_name": {
                "type": "string",
                "description": "Full name of the employee to check leave balance for"
            },
            "employee_id": {
                "type": "string",
                "description": "Employee ID if provided (optional)"
            }
        },
        "required": ["employee_name"],
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
    employee_id = args.get('employee_id', 'default')
    date_str = args.get('date')
    
    logger.info(f"Processing sick leave request for employee ID {employee_id} for date {date_str}")
    
    # Validate date
    try:
        if date_str:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            error_message = "Date is required"
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
    
    # Prepare the request payload according to API specification
    payload = {
        "date": date_str,
        "employeeId": employee_id
    }
    
    # Submit the request to the API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Sick leave request submitted successfully: {result}")
                    
                    # Return success response to the client based on API response format
                    return ToolResult({
                        "success": result.get('success', True),
                        "message": result.get('message', 'Your sick leave request has been submitted successfully'),
                        "remainingBalance": result.get('remainingBalance', 0),
                        "date": date_str
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

async def _check_leave_balance(args: Dict[str, Any]) -> ToolResult:
    """
    Check the available leave balance for an employee.
    
    Args:
        args: Dictionary containing the employee information
        
    Returns:
        ToolResult: Result of the operation to be sent to the client
    """
    logger.info(f"Checking leave balance for {args.get('employee_name')}")
    
    # Validate required fields
    if not args.get('employee_name'):
        error_message = "Employee name is required"
        logger.error(error_message)
        return ToolResult({"success": False, "error": error_message}, ToolResultDirection.TO_CLIENT)
    
    # Get the API URL from environment variables
    api_url = os.environ.get("SICK_LEAVE_BALANCE_API_URL")
    if not api_url:
        error_message = "Sick leave balance API URL is not configured"
        logger.error(error_message)
        return ToolResult({"success": False, "error": error_message, "alternative": "Please contact HR directly to check your leave balance"}, ToolResultDirection.TO_CLIENT)
    
    # Construct the query parameters
    params = {
        "name": args.get('employee_name')
    }
    
    if args.get('employee_id'):
        params["id"] = args.get('employee_id')
    
    # Request the leave balance from the API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Leave balance retrieved successfully for {args.get('employee_name')}")
                    
                    # Return success response to the client
                    return ToolResult({
                        "success": True,
                        "employee_name": args.get('employee_name'),
                        "sick_days_available": result.get('sickDaysAvailable', 0),
                        "vacation_days_available": result.get('vacationDaysAvailable', 0),
                        "personal_days_available": result.get('personalDaysAvailable', 0),
                        "message": "Leave balance retrieved successfully"
                    }, ToolResultDirection.TO_CLIENT)
                else:
                    error_text = await response.text()
                    logger.error(f"API error: {response.status} - {error_text}")
                    return ToolResult({
                        "success": False, 
                        "error": f"Failed to retrieve leave balance. Error: {response.status}",
                        "alternative": "Please contact HR directly to check your leave balance"
                    }, ToolResultDirection.TO_CLIENT)
    except aiohttp.ClientError as e:
        logger.error(f"API connection error: {str(e)}")
        return ToolResult({
            "success": False, 
            "error": "Connection error when retrieving leave balance",
            "alternative": "Please contact HR directly to check your leave balance"
        }, ToolResultDirection.TO_CLIENT)
    except Exception as e:
        logger.error(f"Unexpected error checking leave balance: {str(e)}")
        return ToolResult({
            "success": False, 
            "error": "An unexpected error occurred",
            "alternative": "Please contact HR directly to check your leave balance"
        }, ToolResultDirection.TO_CLIENT)

async def _check_sick_leave_balance(args: Dict[str, Any]) -> ToolResult:
    """
    Check the sick leave balance for an employee.
    
    Args:
        args: Dictionary containing the employee details
        
    Returns:
        ToolResult: Result of the operation to be sent to the client
    """
    employee_id = args.get('employee_id', 'default')
    logger.info(f"Checking sick leave balance for employee ID {employee_id}")
    
    # Get the API URL from environment variables
    api_url = os.environ.get("SICK_LEAVE_BALANCE_API_URL")
    if not api_url:
        error_message = "Sick leave balance API URL is not configured"
        logger.error(error_message)
        return ToolResult({"success": False, "error": error_message}, ToolResultDirection.TO_CLIENT)
    
    # If employee ID is provided, append it as a query parameter
    if employee_id != 'default':
        api_url = f"{api_url}?employeeId={employee_id}"
    
    # Fetch the balance from the API
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    balance = result.get('balance', 0)
                    updated_at = result.get('updatedAt', datetime.datetime.now().isoformat())
                    
                    logger.info(f"Sick leave balance retrieved successfully: {balance} days")
                    
                    # Format the date for display
                    try:
                        updated_date = datetime.datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        formatted_date = updated_date.strftime('%B %d, %Y')
                    except:
                        formatted_date = "Unknown"
                    
                    # Return success response to the client
                    return ToolResult({
                        "success": True,
                        "balance": balance,
                        "updatedAt": formatted_date,
                        "message": f"Your current sick leave balance is {balance} days (as of {formatted_date})"
                    }, ToolResultDirection.TO_CLIENT)
                else:
                    error_text = await response.text()
                    logger.error(f"API error: {response.status} - {error_text}")
                    return ToolResult({
                        "success": False, 
                        "error": f"Failed to retrieve sick leave balance. Error: {response.status}",
                    }, ToolResultDirection.TO_CLIENT)
    except aiohttp.ClientError as e:
        logger.error(f"API connection error: {str(e)}")
        return ToolResult({
            "success": False, 
            "error": "Connection error when checking sick leave balance",
        }, ToolResultDirection.TO_CLIENT)
    except Exception as e:
        logger.error(f"Unexpected error checking sick leave balance: {str(e)}")
        return ToolResult({
            "success": False, 
            "error": "An unexpected error occurred while checking your sick leave balance",
        }, ToolResultDirection.TO_CLIENT)

def sick_leave_request_tool() -> Tool:
    """
    Create and return a Tool instance for handling sick leave requests.
    
    Returns:
        Tool: A tool that can be registered with the RTMiddleTier
    """
    return Tool(schema=_sick_leave_request_schema, target=_submit_sick_leave_request)

def sick_leave_balance_tool() -> Tool:
    """
    Create and return a Tool instance for checking sick leave balance.
    
    Returns:
        Tool: A tool that can be registered with the RTMiddleTier
    """
    return Tool(schema=_sick_leave_balance_schema, target=_check_sick_leave_balance)

def check_leave_balance_tool() -> Tool:
    """
    Create and return a Tool instance for checking leave balances.
    
    Returns:
        Tool: A tool that can be registered with the RTMiddleTier
    """
    return Tool(schema=_check_leave_balance_schema, target=_check_leave_balance)
