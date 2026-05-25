"""
Contact Form Handler — AWS Lambda Function
==========================================
Services used: DynamoDB, SES, Secrets Manager, CloudWatch (auto-logging)
Author: Portfolio Owner
"""

import json
import boto3
import uuid
import logging
from datetime import datetime, timezone

# CloudWatch logging auto-configured by Lambda runtime
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
ses = boto3.client("ses", region_name="us-east-1")

TABLE_NAME = "portfolio-contacts"
FROM_EMAIL = "your-verified-email@gmail.com"   # <-- replace with your SES-verified email


def lambda_handler(event, context):
    """
    Handles POST requests from the contact form.
    1. Validates input
    2. Saves to DynamoDB
    3. Sends confirmation email via SES
    4. Returns CORS-safe JSON response
    """

    # --- CORS preflight ---
    if event.get("httpMethod") == "OPTIONS":
        return cors_response(200, {"message": "ok"})

    logger.info("Contact form submission received")

    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        logger.error("Invalid JSON body")
        return cors_response(400, {"error": "Invalid request body"})

    # --- Validate required fields ---
    required = ["name", "email", "message"]
    missing = [f for f in required if not body.get(f, "").strip()]
    if missing:
        return cors_response(400, {"error": f"Missing fields: {', '.join(missing)}"})

    name    = body["name"].strip()
    email   = body["email"].strip()
    message = body["message"].strip()

    # --- Save to DynamoDB ---
    submission_id = str(uuid.uuid4())
    timestamp     = datetime.now(timezone.utc).isoformat()

    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item={
        "submission_id": submission_id,
        "timestamp":     timestamp,
        "name":          name,
        "email":         email,
        "message":       message,
        "status":        "new"
    })
    logger.info(f"Saved submission {submission_id} to DynamoDB")

    # --- Send confirmation email via SES ---
    try:
        ses.send_email(
            Source=FROM_EMAIL,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": "Thanks for reaching out!"},
                "Body": {
                    "Text": {
                        "Data": (
                            f"Hi {name},\n\n"
                            "Thank you for your message. I've received it and will get back to you soon.\n\n"
                            f"Your message:\n{message}\n\n"
                            "Best regards"
                        )
                    }
                }
            }
        )
        logger.info(f"Confirmation email sent to {email}")
    except Exception as e:
        # Non-fatal — submission is saved; email is best-effort
        logger.warning(f"SES email failed (submission still saved): {e}")

    return cors_response(200, {
        "message": "Submission received successfully",
        "submission_id": submission_id
    })


def cors_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type":                "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps(body)
    }
