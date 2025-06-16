require "httparty"
require "json"
require "tempfile"

require "aws-sdk-s3"
require "aws-sdk-cloudformation"
require "aws-sdk-transfer"
require "aws-sdk-lambda"


S3_BUCKET = ENV["S3_BUCKET"]
USER_ROLE_ARN = ENV["USER_ROLE_ARN"]
VPC_ID = ENV["VPC_ID"]
SUBNET_ID = ENV["SUBNET_ID"]
SUBNET_CIDR = ENV["SUBNET_CIDR"]
IP_ALLOCATION_ID = ENV["IP_ALLOCATION_ID"]
IP_ADDRESS = ENV["IP_ADDRESS"]
SFTP_KEY = ENV["SFTP_KEY"]
PROJECT_NAME = ENV["PROJECT_NAME"]
SLACK_ALERT_NAME = ENV["SLACK_ALERT_NAME"]
SECRET_NAME = ENV["SECRET_NAME"]



STACK_NAME = "#{PROJECT_NAME}-sftp-server"
DEF_WAIT_SECONDS = 10


def lambda_handler(event:, context:)

    p SECRET_NAME

  action = event.dig("action")&.strip&.downcase
  if action.nil? && action != "start" && action != "stop" && action != "test"
    return {statusCode: 400, body: "Missing or wrong action (available actions are: start and stop"}
  end

  cloudformation_client = Aws::CloudFormation::Client.new


  template_bucket_name = ENV["TEMPLATE_BUCKET_NAME"] || "sftp-cloudformation-template-bucket"
  project_name = ENV["PROJECT_NAME"] || "test-project"

  case action
   when "test"
      p "TEST"
      send_notification("just testing")
      return

    when "start"
      p "START"
      template_url = "https://#{template_bucket_name}.s3.eu-west-1.amazonaws.com/sftp-server.yaml"

      cloudformation_client.create_stack({
        stack_name: STACK_NAME,
        template_url: template_url,
        parameters: [
          {parameter_key: "ProjectName", parameter_value: project_name},
          {parameter_key: "S3Bucket", parameter_value: S3_BUCKET},
          {parameter_key: "UserRoleArn", parameter_value: USER_ROLE_ARN},
          {parameter_key: "VpcId", parameter_value: VPC_ID},
          {parameter_key: "SubnetId", parameter_value: SUBNET_ID},
          {parameter_key: "SubnetCidr", parameter_value: SUBNET_CIDR},
          {parameter_key: "EIPAllocationId", parameter_value: IP_ALLOCATION_ID},
          {parameter_key: "EIPAddress", parameter_value: IP_ADDRESS},
          {parameter_key: "TemplateBucket", parameter_value: template_bucket_name},
          {parameter_key: "SecretName", parameter_value: SECRET_NAME},
          # Add user defined parameters
          {parameter_key: "Test", parameter_value: "test"},
        ],
        timeout_in_minutes: 10,
        capabilities: ["CAPABILITY_NAMED_IAM"], # accepts CAPABILITY_IAM, CAPABILITY_NAMED_IAM, CAPABILITY_AUTO_EXPAND
      })

      # Wait until CloudFormation creation process is completed
      create_in_progress = true
      while create_in_progress
        sleep(DEF_WAIT_SECONDS)
        resp = cloudformation_client.describe_stacks({
          stack_name: STACK_NAME,
        })
        stack_status = resp.stacks[0]&.stack_status
        create_in_progress = stack_status == "CREATE_IN_PROGRESS"
      end

      # get stack information and get server_id from outputs
      resp = cloudformation_client.describe_stacks({
        stack_name: STACK_NAME,
      })
      stack_status = resp.stacks[0]&.stack_status

      if stack_status != "CREATE_COMPLETE"
        send_notification(":rotating_light: *SFTP Server* creation *FAILED*")
        return {statusCode: 500, body: "Stack creation failed"}
      end

      outputs = resp.stacks[0]&.outputs
      server_id_output = outputs.detect { |output| output.output_key == "SFTPServerId" }
      server_id = server_id_output&.output_value


      transfer_client = Aws::Transfer::Client.new
      resp = transfer_client.update_server({
        server_id: server_id, # required
        host_key: SFTP_KEY,
      })

      send_notification(":sunny: *SFTP Server* is *STARTED* ")

    when "stop"
      p "STOP"
      cloudformation_client.delete_stack({
        stack_name: STACK_NAME,
      })
      send_notification(":zzz: *SFTP Server* is *STOPPED* ")

  end

  {statusCode: 200, body: resp.to_json}

rescue => error
  send_notification(":rotating_light: ERROR during SFTPStartStop Lambda, error: #{error}")
  {statusCode: 500, body: error.to_json}
end

def send_notification(message)
    p 'message', message
#   lambda_client = Aws::Lambda::Client.new
#   payload = JSON.generate(message)
#
#   lambda_client.invoke({
#     function_name: SLACK_ALERT_NAME,
#     invocation_type: "RequestResponse",
#     log_type: "None",
#     payload: payload,
#   })
end