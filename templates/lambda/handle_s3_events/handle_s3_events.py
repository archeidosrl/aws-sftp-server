import os
import json
import urllib.request

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def lambda_handler(event, context):
    try:
        records = event.get("Records", [])
        if not records:
            print("No records found in event")
            return {"statusCode": 400, "body": "No records in event"}

        for record in records:
            s3_info = record["s3"]
            bucket_name = s3_info["bucket"]["name"]
            object_key = s3_info["object"]["key"]
            object_size = s3_info["object"].get("size", "unknown")

            # Extract username and filename
            key_parts = object_key.split("/")
            username = key_parts[0] if len(key_parts) > 1 else "unknown"
            filename = key_parts[-1]

            message = (
                f":inbox_tray: *New file uploaded to S3*\n"
                f"*Bucket:* `{bucket_name}`\n"
                f"*User:* `{username}`\n"
                f"*File:* `{filename}`\n"
                f"*Size:* `{object_size}` bytes"
            )

            send_notification(message)

        return {"statusCode": 200, "body": "Notification(s) sent"}

    except Exception as e:
        error_message = f":rotating_light: Error processing S3 event: {e}"
        send_notification(error_message)
        return {"statusCode": 500, "body": str(e)}

def send_notification(message):
    if not SLACK_WEBHOOK_URL:
        print("SLACK_WEBHOOK_URL is not set")
        return

    slack_message = json.dumps({"text": message}).encode("utf-8")

    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=slack_message,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            response_body = response.read()
            print(f"Slack response: {response.status}, {response_body}")
    except Exception as e:
        print(f"Error sending Slack notification: {e}")
