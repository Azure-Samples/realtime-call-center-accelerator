#!/bin/bash
# This script tests the sick leave API integration

# Set default values
SICK_LEAVE_API_URL=${SICK_LEAVE_API_URL:-"https://pacific-mock.azurewebsites.net/api/sickleave/apply"}
SICK_LEAVE_BALANCE_API_URL=${SICK_LEAVE_BALANCE_API_URL:-"https://pacific-mock.azurewebsites.net/api/sickleave/balance"}
EMPLOYEE_ID=${1:-"default"}
DATE=${2:-$(date +%Y-%m-%d)}

echo "Testing sick leave API integration"
echo "=================================="

# Test 1: Submit sick leave
echo "Test 1: Submitting sick leave request"
echo "API URL: $SICK_LEAVE_API_URL"
echo "Employee ID: $EMPLOYEE_ID"
echo "Date: $DATE"
echo ""

# Create the request payload for submission
PAYLOAD=$(cat <<END_OF_PAYLOAD
{
  "date": "$DATE",
  "employeeId": "$EMPLOYEE_ID"
}
END_OF_PAYLOAD
)

# Send the submit request
echo "Sending sick leave application..."
curl -X POST \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "$SICK_LEAVE_API_URL"

echo ""
echo ""

# Test 2: Check sick leave balance
echo "Test 2: Checking sick leave balance"
echo "API URL: $SICK_LEAVE_BALANCE_API_URL"
echo "Employee ID: $EMPLOYEE_ID"
echo ""

# Send the balance check request
echo "Checking sick leave balance..."
curl -X GET \
  -H "Content-Type: application/json" \
  "${SICK_LEAVE_BALANCE_API_URL}?employeeId=${EMPLOYEE_ID}"

echo ""
echo ""
echo "Tests complete."
