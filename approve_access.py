import json
import os
from datetime import datetime, timedelta

import boto3

# AWS Clients
dynamodb = boto3.resource("dynamodb")
identitystore = boto3.client("identitystore")
sso_admin = boto3.client("sso-admin")
scheduler = boto3.client("scheduler")

# Environment Variables
TABLE = dynamodb.Table(os.environ["REQUEST_TABLE"])

INSTANCE_ARN = os.environ["SSO_INSTANCE_ARN"]
ACCOUNT_ID = os.environ["ACCOUNT_ID"]
PERMISSION_SET_ARN = os.environ["PERMISSION_SET_ARN"]
IDENTITY_STORE_ID = os.environ["IDENTITY_STORE_ID"]
REVOKE_FUNCTION_ARN = os.environ["REVOKE_FUNCTION_ARN"]
SCHEDULER_ROLE_ARN = os.environ["SCHEDULER_ROLE_ARN"]


def handler(event, context):

    try:

        # ----------------------------
        # Read Request ID
        # ----------------------------
        params = event.get("queryStringParameters") or {}

        request_id = params.get("request_id")

        if not request_id:
            return {
                "statusCode": 400,
                "body": "Missing request_id"
            }

        # ----------------------------
        # Get Request From DynamoDB
        # ----------------------------
        response = TABLE.get_item(
            Key={
                "RequestId": request_id
            }
        )

        if "Item" not in response:
            return {
                "statusCode": 404,
                "body": "Request not found"
            }

        request = response["Item"]

        if request["Status"] != "PENDING":
            return {
                "statusCode": 400,
                "body": "Request already processed"
            }

        user_email = request["UserEmail"]
        duration_hours = int(request["DurationHours"])

        # ----------------------------
        # Find Identity Center User
        # ----------------------------
        users = identitystore.list_users(
            IdentityStoreId=IDENTITY_STORE_ID
        )

        matched_user = None

        for user in users["Users"]:

            for email in user.get("Emails", []):

                if email["Value"].lower() == user_email.lower():
                    matched_user = user
                    break

            if matched_user:
                break

        if matched_user is None:
            return {
                "statusCode": 404,
                "body": "IAM Identity Center user not found"
            }

        user_id = matched_user["UserId"]

        # ----------------------------
        # Assign Permission Set
        # ----------------------------
        sso_admin.create_account_assignment(
            InstanceArn=INSTANCE_ARN,
            TargetId=ACCOUNT_ID,
            TargetType="AWS_ACCOUNT",
            PermissionSetArn=PERMISSION_SET_ARN,
            PrincipalType="USER",
            PrincipalId=user_id
        )

        # ----------------------------
        # Update DynamoDB
        # ----------------------------
        TABLE.update_item(
            Key={
                "RequestId": request_id
            },
            UpdateExpression="SET #S=:s, ApprovedAt=:t",
            ExpressionAttributeNames={
                "#S": "Status"
            },
            ExpressionAttributeValues={
                ":s": "APPROVED",
                ":t": datetime.utcnow().isoformat()
            }
        )

        # ----------------------------
        # Schedule Auto Revoke
        # ----------------------------
        revoke_time = datetime.utcnow() + timedelta(hours=duration_hours)

        scheduler.create_schedule(
            Name=f"revoke-{request_id}",
            ScheduleExpression=f"at({revoke_time.strftime('%Y-%m-%dT%H:%M:%S')})",
            FlexibleTimeWindow={
                "Mode": "OFF"
            },
            Target={
                "Arn": REVOKE_FUNCTION_ARN,
                "RoleArn": SCHEDULER_ROLE_ARN,
                "Input": json.dumps({
                    "user_id": user_id,
                    "user_email": user_email,
                    "request_id": request_id
                })
            }
        )

        # ----------------------------
        # Success Page
        # ----------------------------
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/html"
            },
            "body": f"""
<!DOCTYPE html>
<html>

<head>
<title>JIT Access Approved</title>
</head>

<body style="font-family:Arial;background:#f5f5f5;padding:40px;">

<div style="background:white;padding:30px;border-radius:10px;max-width:600px;margin:auto;box-shadow:0 0 10px #ccc;">

<h1 style="color:green;">
✅ Access Approved
</h1>

<hr>

<p><b>User</b></p>
<p>{user_email}</p>

<p><b>Duration</b></p>
<p>{duration_hours} Hour(s)</p>

<p><b>Request ID</b></p>
<p>{request_id}</p>

<p><b>Status</b></p>
<p style="color:green;">
APPROVED
</p>

</div>

</body>

</html>
"""
        }

    except Exception as e:

        print(str(e))

        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }