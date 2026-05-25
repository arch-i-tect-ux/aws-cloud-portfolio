"""
Get Submissions — AWS Lambda Function
======================================
Retrieves all contact form submissions from DynamoDB.
Services used: DynamoDB, CloudWatch (auto-logging)
"""

import json
import boto3
import logging
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = "portfolio-contacts"


def lambda_handler(event, context):
    logger.info("Fetching all submissions")

    table = dynamodb.Table(TABLE_NAME)

    try:
        response = table.scan()
        items = response.get("Items", [])

        # Sort newest first
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        logger.info(f"Retrieved {len(items)} submissions")
        return cors_response(200, {"submissions": items, "count": len(items)})

    except Exception as e:
        logger.error(f"DynamoDB scan failed: {e}")
        return cors_response(500, {"error": "Failed to retrieve submissions"})


def cors_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, default=str)
    }
