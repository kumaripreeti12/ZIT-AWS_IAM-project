import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
sso_admin = boto3.client("sso-admin")

TABLE = dynamodb.Table(os.environ["REQUEST_TABLE"])

INSTANCE_ARN = os.environ["SSO_INSTANCE_ARN"]
ACCOUNT_ID = os.environ["ACCOUNT_ID"]
PERMISSION_SET_ARN = os.environ["PERMISSION_SET_ARN"]


def handler(event, context):

    try:

        user_id = event["user_id"]
        user_email = event["user_email"]
        request_id = event["request_id"]

        sso_admin.delete_account_assignment(
            InstanceArn=INSTANCE_ARN,
            TargetId=ACCOUNT_ID,
            TargetType="AWS_ACCOUNT",
            PermissionSetArn=PERMISSION_SET_ARN,
            PrincipalType="USER",
            PrincipalId=user_id
        )

        TABLE.update_item(
            Key={
                "RequestId": request_id
            },
            UpdateExpression="SET #S=:s, RevokedAt=:t",
            ExpressionAttributeNames={
                "#S": "Status"
            },
            ExpressionAttributeValues={
                ":s": "REVOKED",
                ":t": datetime.utcnow().isoformat()
            }
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Access revoked successfully"
            })
        }

    except Exception as e:

        print(str(e))

        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }