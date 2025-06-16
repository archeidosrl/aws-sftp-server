import os
import json
import time
import boto3
import urllib.request
import datetime

# Environment variables
S3_BUCKET = os.environ["S3_BUCKET"]
USER_ROLE_ARN = os.environ["USER_ROLE_ARN"]
VPC_ID = os.environ["VPC_ID"]
SUBNET_ID = os.environ["SUBNET_ID"]
SUBNET_CIDR = os.environ["SUBNET_CIDR"]
IP_ALLOCATION_ID = os.environ["IP_ALLOCATION_ID"]
IP_ADDRESS = os.environ["IP_ADDRESS"]
# SFTP_KEY = os.environ["SFTP_KEY"]
PROJECT_NAME = os.environ["PROJECT_NAME"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SECRET_NAME = os.environ["SECRET_NAME"]

STACK_NAME = f"{PROJECT_NAME}-sftp-server"
DEF_WAIT_SECONDS = 10

def lambda_handler(event, context):

    action = event.get("action", "").strip().lower()
    if action not in ["start", "stop", "test"]:
        return {
            "statusCode": 400,
            "body": "Missing or wrong action (available actions are: start and stop)"
        }

    cloudformation_client = boto3.client("cloudformation")
    transfer_client = boto3.client("transfer")

    template_bucket_name = os.environ.get("TEMPLATE_BUCKET_NAME", "sftp-cloudformation-template-bucket")
    project_name = os.environ.get("PROJECT_NAME", "test-project")

    try:
        if action == "test":
            print("TEST")
            send_notification("just testing")
            return

        elif action == "start":
            print("START")
            template_url = f"https://{template_bucket_name}.s3.eu-west-1.amazonaws.com/sftp-server.yaml"

            cloudformation_client.create_stack(
                StackName=STACK_NAME,
                TemplateURL=template_url,
                Parameters=[
                    {"ParameterKey": "ProjectName", "ParameterValue": project_name},
                    {"ParameterKey": "S3Bucket", "ParameterValue": S3_BUCKET},
                    {"ParameterKey": "UserRoleArn", "ParameterValue": USER_ROLE_ARN},
                    {"ParameterKey": "VpcId", "ParameterValue": VPC_ID},
                    {"ParameterKey": "SubnetId", "ParameterValue": SUBNET_ID},
                    {"ParameterKey": "SubnetCidr", "ParameterValue": SUBNET_CIDR},
                    {"ParameterKey": "EIPAllocationId", "ParameterValue": IP_ALLOCATION_ID},
                    {"ParameterKey": "EIPAddress", "ParameterValue": IP_ADDRESS},
                    {"ParameterKey": "TemplateBucket", "ParameterValue": template_bucket_name},
                    {"ParameterKey": "SecretName", "ParameterValue": SECRET_NAME},
                    {"ParameterKey": "Test", "ParameterValue": "test"}
                ],
                TimeoutInMinutes=10,
                Capabilities=["CAPABILITY_NAMED_IAM"]
            )

            # Wait for stack creation
            create_in_progress = True
            while create_in_progress:
                time.sleep(DEF_WAIT_SECONDS)
                resp = cloudformation_client.describe_stacks(StackName=STACK_NAME)
                stack_status = resp["Stacks"][0]["StackStatus"]
                create_in_progress = stack_status == "CREATE_IN_PROGRESS"

            # Get outputs
            resp = cloudformation_client.describe_stacks(StackName=STACK_NAME)
            stack_status = resp["Stacks"][0]["StackStatus"]

            if stack_status != "CREATE_COMPLETE":
                send_notification(":rotating_light: *SFTP Server* creation *FAILED*")
                return {"statusCode": 500, "body": "Stack creation failed"}

            outputs = resp["Stacks"][0]["Outputs"]
            server_id_output = next((o for o in outputs if o["OutputKey"] == "SFTPServerId"), None)
            server_id = server_id_output["OutputValue"] if server_id_output else None

            # transfer_client.update_server(
            #     ServerId=server_id,
            #     HostKey=SFTP_KEY
            # )

            send_notification(":sunny: *SFTP Server* is *STARTED* ")

        elif action == "stop":
            print("STOP")
            resp = cloudformation_client.delete_stack(StackName=STACK_NAME)
            send_notification(":zzz: *SFTP Server* is *STOPPED* ")

        return {"statusCode": 200, "body": json.dumps(resp, default=safe_json)}

    except Exception as error:
        send_notification(f":rotating_light: ERROR during SFTPStartStop Lambda, error: {error}")
        return {"statusCode": 500, "body": json.dumps(str(error))}

def safe_json(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.decode()
    return str(obj)


def send_notification(message):
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
