#!/usr/bin/env python3
import aws_cdk as cdk

from templates.infrastructure.infrastructure_stack import InfrastructureStack
from utilities.utility import load_config

config = load_config()

AWS_REGION = config["region"]
ACCOUNT = str(config["account_id"])

app = cdk.App()
env = cdk.Environment(account=ACCOUNT, region=AWS_REGION)

# ------------------------------------------------------- Stacks -------------------------------------------------------

InfrastructureStack(
    app,
    f"{config['project_name']}-infrastructure",
    env=env
)

app.synth()
