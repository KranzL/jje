data "aws_iam_policy_document" "processor_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "processor" {
  name               = "${local.name}-processor"
  assume_role_policy = data.aws_iam_policy_document.processor_assume.json
}

resource "aws_iam_role_policy_attachment" "processor_vpc" {
  role       = aws_iam_role.processor.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

data "aws_iam_policy_document" "processor_logs" {
  statement {
    sid    = "WriteFunctionLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.processor.arn}:*"]
  }
}

resource "aws_iam_role_policy" "processor_logs" {
  name   = "logs"
  role   = aws_iam_role.processor.id
  policy = data.aws_iam_policy_document.processor_logs.json
}

data "aws_iam_policy_document" "processor_queue" {
  statement {
    sid    = "ConsumeIngestQueue"
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [
      aws_sqs_queue.ingest.arn,
      aws_sqs_queue.dlq.arn,
    ]
  }
}

resource "aws_iam_role_policy" "processor_queue" {
  name   = "queue"
  role   = aws_iam_role.processor.id
  policy = data.aws_iam_policy_document.processor_queue.json
}

data "aws_iam_policy_document" "processor_storage" {
  statement {
    sid       = "ReadUploads"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.uploads.arn}/*"]
  }

  statement {
    sid       = "ListUploadsBucket"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.uploads.arn]
  }

  statement {
    sid    = "WriteDocumentRecords"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.documents.arn,
      "${aws_dynamodb_table.documents.arn}/index/*",
    ]
  }

  statement {
    sid    = "IdempotencyGuard"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
    ]
    resources = [
      "arn:aws:dynamodb:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/*",
    ]
  }
}

resource "aws_iam_role_policy" "processor_storage" {
  name   = "storage"
  role   = aws_iam_role.processor.id
  policy = data.aws_iam_policy_document.processor_storage.json
}

data "aws_iam_policy_document" "processor_crypto" {
  statement {
    sid    = "UsePipelineKey"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey",
    ]
    resources = [aws_kms_key.pipeline.arn]
  }
}

resource "aws_iam_role_policy" "processor_crypto" {
  name   = "crypto"
  role   = aws_iam_role.processor.id
  policy = data.aws_iam_policy_document.processor_crypto.json
}
