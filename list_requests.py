import json
import boto3
import os
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ["REQUEST_TABLE"]
table = dynamodb.Table(TABLE_NAME)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


def handler(event, context):

    response = table.scan()

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(response["Items"], cls=DecimalEncoder)
    }