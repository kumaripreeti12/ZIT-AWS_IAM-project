import json
import boto3
import os
import uuid
from datetime import datetime

sns = boto3.client("sns")
dynamodb = boto3.resource("dynamodb")

TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
API_URL = os.environ["API_URL"]
TABLE_NAME = os.environ["REQUEST_TABLE"]

table = dynamodb.Table(TABLE_NAME)


def handler(event, context):

    try:
        body = json.loads(event.get("body", "{}"))

        user_email = body.get("user_email")
        duration_hours = int(body.get("duration_hours", 1))
        justification = body.get("justification", "")

        if not user_email:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "User email is required"})
            }

        request_id = str(uuid.uuid4())

        table.put_item(
            Item={
                "RequestId": request_id,
                "UserEmail": user_email,
                "DurationHours": duration_hours,
                "Justification": justification,
                "Status": "PENDING",
                "CreatedAt": datetime.utcnow().isoformat()
            }
        )

        approve_url = (
            f"{API_URL}/approve"
            f"?request_id={request_id}"
        )

        reject_url = (
            f"{API_URL}/reject"
            f"?request_id={request_id}"
        )

        message = f"""
AWS Just-In-Time Access Request

Request ID:
{request_id}

User:
{user_email}

Duration:
{duration_hours} Hour(s)

Reason:
{justification}

Approve:
{approve_url}

Reject:
{reject_url}
"""

        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject="AWS JIT Access Request",
            Message=message
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "Request submitted successfully",
                "request_id": request_id
            })
        }

    except Exception as e:

        print(str(e))

        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": str(e)
            })
        }