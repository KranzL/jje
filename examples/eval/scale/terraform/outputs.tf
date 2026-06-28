output "upload_bucket_name" {
  description = "Name of the upload bucket S3 events originate from."
  value       = aws_s3_bucket.uploads.id
}

output "ingest_queue_url" {
  description = "URL of the primary ingest queue."
  value       = aws_sqs_queue.ingest.url
}

output "dlq_arn" {
  description = "ARN of the dead-letter queue."
  value       = aws_sqs_queue.dlq.arn
}

output "documents_table_name" {
  description = "DynamoDB table holding processed document records."
  value       = aws_dynamodb_table.documents.name
}

output "processor_function_name" {
  description = "Name of the processing Lambda."
  value       = aws_lambda_function.processor.function_name
}

output "processor_role_arn" {
  description = "Execution role ARN for the processing Lambda."
  value       = aws_iam_role.processor.arn
}
