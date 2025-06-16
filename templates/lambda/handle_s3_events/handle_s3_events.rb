# frozen_string_literal: true

require "aws-sdk"
require "aws-sdk-s3"
require "aws-sdk-lambda"
require "httparty"
require "json"

FIXED_FOLDER = "public"
DESTINATION_FOLDER = ENV["DESTINATION_FOLDER"]
S3_CLIENT = Aws::S3::Client.new(region: ENV["AWS_REGION"])

def lambda_handler(event:, context:)

  event_name = event&.dig("Records", 0, "eventName")
  source_bucket_name = event&.dig("Records", 0, "s3", "bucket", "name")
  source_object_key = event&.dig("Records", 0, "s3", "object", "key")

  

end
