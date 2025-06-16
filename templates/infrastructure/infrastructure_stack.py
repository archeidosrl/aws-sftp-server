from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as lambdafn,
    aws_secretsmanager as secretsmanager,
    aws_s3_notifications as s3n
)
from constructs import Construct
import sys


sys.path.append("../..")
# ignore following highlighted import error
from utilities.utility import load_config


config = load_config()


class InfrastructureStack(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ------------------------------------------------- Constants --------------------------------------------------

        PROJECT_NAME = config["project_name"]
        VPC_ID = config["vpc"]["id"]
        SUBNET_CIDR = str(config["vpc"]["subnet_cidr"])
        EIP_ALLOCATION_ID = config["vpc"]["eip_allocation_id"]
        EIP_ADDRESS = config["vpc"]["eip_address"]
        SLACK_WEBHOOK_URL = config["slack_webhook_url"]

        # ----------------------------------------------------- Vpc ----------------------------------------------------

        vpc = ec2.Vpc.from_lookup(
            self,
            f"{PROJECT_NAME}-vpc",
            vpc_id=VPC_ID
        )

        # ----------------------------------------------- Secret Manager -----------------------------------------------

        secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            f"{PROJECT_NAME}-project-secrets",
            secret_name=f"{PROJECT_NAME}-project-secrets"
        )

        # ------------------------------------------- S3 Storage Buckets -----------------------------------------------

        # Cloudformation template storaging bucket
        sftp_cloudformation_template_storaging_bucket = s3.Bucket(
            self,
            f"{PROJECT_NAME}-sftp-cloudformation-template-bucket",
            bucket_name=f"{PROJECT_NAME}-sftp-cloudformation-template-bucket",
            block_public_access=s3.BlockPublicAccess(
                restrict_public_buckets=True
            ),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # File upload destiantion bucket
        sftp_storage_bucket = s3.Bucket(
            self,
            f"{PROJECT_NAME}-sftp-storage-bucket",
            bucket_name=f"{PROJECT_NAME}-sftp-storage-bucket",
            block_public_access=s3.BlockPublicAccess(
                restrict_public_buckets=False
            ),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # -------------------------------------------------- IAM Roles -------------------------------------------------

        sftp_user_role = iam.Role(
            self,
            f"{PROJECT_NAME}-sftp-user-role",
            role_name=f"{PROJECT_NAME}-sftp-user-role",
            assumed_by=iam.ServicePrincipal("transfer.amazonaws.com")
        )

        sftp_user_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:*"],
                resources=[
                    f"arn:aws:s3:::{PROJECT_NAME}-sftp-storage-bucket",
                    f"arn:aws:s3:::{PROJECT_NAME}-sftp-storage-bucket/*"
                ]

            )
        )

        sftp_lambda_role = iam.Role(
            self,
            f"{PROJECT_NAME}-sftp-lambda-role",
            role_name=f"{PROJECT_NAME}-sftp-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        sftp_lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    # CloudFormation permissions
                    "cloudformation:CreateStack",
                    "cloudformation:DeleteStack",
                    "cloudformation:UpdateStack",
                    "cloudformation:DescribeStacks",
                    "cloudformation:DescribeStackEvents",
                    "cloudformation:GetTemplate",
                    "cloudformation:ValidateTemplate",

                    # IAM permissions
                    "iam:CreateRole",
                    "iam:DeleteRole",
                    "iam:PassRole",
                    "iam:GetRole",
                    "iam:AttachRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:PutRolePolicy",
                    "iam:DeleteRolePolicy",

                    "secretsmanager:GetSecretValue",

                    # SFTP fetch user key lambda permissions
                    "lambda:CreateFunction",
                    "lambda:GetFunction",
                    "lambda:DeleteFunction",

                    # ELB permissions – creation, modification, and deletion
                    "elasticloadbalancing:*",

                    # Lambda invocation
                    "lambda:InvokeFunction",

                    # S3 access
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",

                    # SFTP Transfer permissions
                    "transfer:*",
                ],
                resources=["*"]  # Consider scoping down for production
            )
        )

        sftp_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:*"
                ],
                resources=["*"]
            )
        )

        # ---------------------------------------------- Lambda Functions ----------------------------------------------

        start_stop_sftp_server_lambda = lambdafn.Function(
            self,
            f"{PROJECT_NAME}-sftp-start-stop-lambda",
            function_name=f"{PROJECT_NAME}-sftp-start-stop-lambda",
            runtime=lambdafn.Runtime.PYTHON_3_12,
            role=sftp_lambda_role,
            code=lambdafn.Code.from_asset("templates/lambda/start_stop_sftp_server/function.zip"),
            handler="sftp_start_stop_aws_lambda.lambda_handler",
            timeout=Duration.minutes(15),
            environment={
                "S3_BUCKET": str(sftp_storage_bucket.bucket_name),
                "USER_ROLE_ARN": str(sftp_user_role.role_arn),
                "SUBNET_CIDR": str(SUBNET_CIDR),
                "IP_ADDRESS": str(EIP_ADDRESS),
                "IP_ALLOCATION_ID": str(EIP_ALLOCATION_ID),
                "SUBNET_ID": str(vpc.public_subnets[0].subnet_id),
                "VPC_ID": str(vpc.vpc_id),
                "TEMPLATE_BUCKET_NAME": str(sftp_cloudformation_template_storaging_bucket.bucket_name),
                "PROJECT_NAME": str(PROJECT_NAME),
                "SECRET_NAME": str(secret.secret_name),
                "SLACK_WEBHOOK_URL": str(SLACK_WEBHOOK_URL)
            }
        )

        handle_s3_event_lambda = lambdafn.Function(
            self,
            f"{PROJECT_NAME}-handle-s3-event-lambda",
            function_name=f"{PROJECT_NAME}-handle-s3-event-lambda",
            runtime=lambdafn.Runtime.PYTHON_3_12,
            code=lambdafn.Code.from_asset("templates/lambda/handle_s3_events"),
            handler="handle_s3_events.lambda_handler",
            environment={
                "SLACK_WEBHOOK_URL": str(SLACK_WEBHOOK_URL),
            }
        )

        sftp_storage_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT,
            s3n.LambdaDestination(handle_s3_event_lambda)
        )

        # --------------------------------------------- Lambda Permissions ---------------------------------------------

        handle_s3_event_lambda.add_permission(
            "AllowS3Invoke",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=sftp_storage_bucket.bucket_arn,
        )


